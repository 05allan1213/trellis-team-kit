"""
Prompt Routing Engine — scorer-based routing for trellis-team-kit.

Replaces the old hardcoded first-match heuristic in inject-workflow-state.py.
This module is responsible for:

- Rule loading (workspace override + default fallback)
- Prompt normalization
- Intent gate (question vs change request)
- Level scoring (L1 / L2 / L3 / L4 / L5)
- Negative rule application
- Conflict handling and UNCERTAIN determination
- Confidence calculation

Exposes a single public entry point: `classify_no_task_prompt()`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NormalizedPrompt:
    """A prompt after basic normalization."""
    original: str
    lowered: str
    cleaned: str  # whitespace-normalized lowercase text


@dataclass
class RuleHit:
    """A single rule that matched the prompt."""
    rule_id: str
    rule_type: str
    level: str
    weight: int
    risk: str = ""
    detail: str = ""


@dataclass
class RoutingDecision:
    """Structured result from the routing scorer."""
    route: str           # L0 | L1 | L2 | L3 | L4 | L5 | UNCERTAIN | generic
    confidence: str      # high | medium | low
    scores: dict = field(default_factory=dict)   # {"L1": 2, "L2": 5, "L3": 0, "L4": 0, "L5": 0}
    reasons: list = field(default_factory=list)   # human-readable hit descriptions


# ---------------------------------------------------------------------------
# Rule loading
# ---------------------------------------------------------------------------

_DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "trellis" / "config" / "routing_rules.json"
ROUTABLE_LEVELS = ("L1", "L2", "L3", "L4", "L5")


def _find_default_rules_path() -> Path:
    """Return the path to the bundled default routing_rules.json."""
    # Walk up from this file to find the repo root, then look for trellis/config/
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        candidate = parent / "trellis" / "config" / "routing_rules.json"
        if candidate.is_file():
            return candidate
    # Fallback: the constant computed at import time
    return _DEFAULT_RULES_PATH


def _load_json(path: Path) -> Optional[dict]:
    """Safely load a JSON file, returning None on any failure."""
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def load_routing_rules(root: Optional[Path] = None) -> dict:
    """Load routing rules with workspace-override semantics.

    Load order:
    1. <workspace-root>/.trellis/config/routing_rules.json  (override)
    2. trellis/config/routing_rules.json                     (default)

    If the override exists but is invalid JSON, falls back to default.
    If both are missing/invalid, raises RuntimeError.
    """
    default_path = _find_default_rules_path()

    if root is not None:
        override_path = root / ".trellis" / "config" / "routing_rules.json"
        if override_path.is_file():
            data = _load_json(override_path)
            if data is not None:
                return data
            # Override is invalid — fall through to default

    data = _load_json(default_path)
    if data is not None:
        return data

    raise RuntimeError(
        f"No valid routing rules found. "
        f"Default path: {default_path}"
    )


# ---------------------------------------------------------------------------
# Prompt normalization
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")


def normalize_prompt(prompt: str) -> NormalizedPrompt:
    """Normalize a prompt for matching purposes."""
    cleaned = _WS_RE.sub(" ", prompt.strip())
    lowered = cleaned.lower()
    return NormalizedPrompt(
        original=prompt,
        lowered=lowered,
        cleaned=cleaned,
    )


# ---------------------------------------------------------------------------
# Intent gate — L0 vs change request
# ---------------------------------------------------------------------------

def _classify_intent(np: NormalizedPrompt, intent_gate: dict) -> bool:
    """Return True if the prompt looks like a question or analysis request (L0).

    Uses four signals:
    - question_keywords: direct keyword matches
    - analysis_keywords: analysis/explanation/review signals
    - question_patterns: regex pattern matches
    - change_keywords: if strong change verbs are present, suppress L0
    """
    # Defensive check: if intent_gate is malformed, treat as non-question
    if not isinstance(intent_gate, dict):
        return False

    text = np.lowered
    original = np.original

    q_keywords = intent_gate.get("question_keywords", [])
    a_keywords = intent_gate.get("analysis_keywords", [])
    q_patterns = intent_gate.get("question_patterns", [])
    c_keywords = intent_gate.get("change_keywords", [])

    # Ensure these are lists, default to empty if not
    if not isinstance(q_keywords, list):
        q_keywords = []
    if not isinstance(a_keywords, list):
        a_keywords = []
    if not isinstance(q_patterns, list):
        q_patterns = []
    if not isinstance(c_keywords, list):
        c_keywords = []

    question_score = 0
    change_score = 0

    # Question keywords
    for kw in q_keywords:
        if isinstance(kw, str) and kw.lower() in text:
            question_score += 1

    # Analysis keywords (analyze, review, evaluate, etc.)
    for kw in a_keywords:
        if isinstance(kw, str) and kw.lower() in text:
            question_score += 1

    # Question patterns (regex)
    for pat in q_patterns:
        if isinstance(pat, str):
            try:
                if re.search(pat, original, re.IGNORECASE):
                    question_score += 1
            except re.error:
                # Skip malformed regex patterns
                pass

    # Change keywords
    for kw in c_keywords:
        if isinstance(kw, str) and kw.lower() in text:
            change_score += 1

    # If change signals are strong, this is not a question
    if change_score >= 2:
        return False

    # If question signals outweigh change signals, treat as L0
    return question_score > change_score


# ---------------------------------------------------------------------------
# Level scoring
# ---------------------------------------------------------------------------

def _match_keyword_rule(np: NormalizedPrompt, rule: dict) -> Optional[RuleHit]:
    """Check a keyword-type rule."""
    terms = rule.get("terms", [])
    if not isinstance(terms, list):
        return None
    for term in terms:
        if isinstance(term, str) and term.lower() in np.lowered:
            return RuleHit(
                rule_id=rule.get("id", ""),
                rule_type="keyword",
                level="",  # filled by caller
                weight=rule.get("weight", 1),
                risk=rule.get("risk", ""),
                detail=f"keyword match: '{term}'",
            )
    return None


def _match_phrase_rule(np: NormalizedPrompt, rule: dict) -> Optional[RuleHit]:
    """Check a phrase-type rule."""
    patterns = rule.get("patterns", [])
    if not isinstance(patterns, list):
        return None
    for pat in patterns:
        if isinstance(pat, str) and pat.lower() in np.lowered:
            return RuleHit(
                rule_id=rule.get("id", ""),
                rule_type="phrase",
                level="",
                weight=rule.get("weight", 2),
                risk=rule.get("risk", ""),
                detail=f"phrase match: '{pat}'",
            )
    return None


def _match_regex_rule(np: NormalizedPrompt, rule: dict) -> Optional[RuleHit]:
    """Check a regex-type rule."""
    patterns = rule.get("patterns", [])
    if not isinstance(patterns, list):
        return None
    for pat in patterns:
        if isinstance(pat, str):
            try:
                if re.search(pat, np.original, re.IGNORECASE):
                    return RuleHit(
                        rule_id=rule.get("id", ""),
                        rule_type="regex",
                        level="",
                        weight=rule.get("weight", 2),
                        risk=rule.get("risk", ""),
                        detail=f"regex match: '{pat}'",
                    )
            except re.error:
                # Skip malformed regex patterns gracefully
                continue
    return None


def _match_pair_rule(np: NormalizedPrompt, rule: dict) -> Optional[RuleHit]:
    """Check a pair-type rule (verb + object)."""
    verbs = rule.get("verbs", [])
    objects = rule.get("objects", [])
    if not isinstance(verbs, list):
        verbs = []
    if not isinstance(objects, list):
        objects = []
    text = np.lowered

    matched_verb = None
    matched_object = None

    for v in verbs:
        if isinstance(v, str) and v.lower() in text:
            matched_verb = v
            break

    for o in objects:
        if isinstance(o, str) and o.lower() in text:
            matched_object = o
            break

    if matched_verb and matched_object:
        return RuleHit(
            rule_id=rule.get("id", ""),
            rule_type="pair",
            level="",
            weight=rule.get("weight", 3),
            risk=rule.get("risk", ""),
            detail=f"pair match: verb='{matched_verb}' + object='{matched_object}'",
        )
    return None


def _match_triple_rule(np: NormalizedPrompt, rule: dict) -> Optional[RuleHit]:
    """Check a triple-type rule (subject + verb + object)."""
    subjects = rule.get("subjects", [])
    verbs = rule.get("verbs", [])
    objects = rule.get("objects", [])
    if not isinstance(subjects, list):
        subjects = []
    if not isinstance(verbs, list):
        verbs = []
    if not isinstance(objects, list):
        objects = []
    text = np.lowered

    matched_subject = None
    matched_verb = None
    matched_object = None

    for s in subjects:
        if isinstance(s, str) and s.lower() in text:
            matched_subject = s
            break

    for v in verbs:
        if isinstance(v, str) and v.lower() in text:
            matched_verb = v
            break

    for o in objects:
        if isinstance(o, str) and o.lower() in text:
            matched_object = o
            break

    if matched_subject and matched_verb and matched_object:
        return RuleHit(
            rule_id=rule.get("id", ""),
            rule_type="triple",
            level="",
            weight=rule.get("weight", 4),
            risk=rule.get("risk", ""),
            detail=f"triple match: subject='{matched_subject}' + verb='{matched_verb}' + object='{matched_object}'",
        )
    return None


_MATCHERS = {
    "keyword": _match_keyword_rule,
    "phrase": _match_phrase_rule,
    "regex": _match_regex_rule,
    "pair": _match_pair_rule,
    "triple": _match_triple_rule,
}


def _score_levels(np: NormalizedPrompt, levels: dict) -> tuple[dict[str, int], list[RuleHit]]:
    """Score all levels against the normalized prompt.

    Returns:
        scores: {"L1": int, "L2": int, "L3": int, "L4": int, "L5": int}
        hits: list of RuleHit
    """
    scores: dict[str, int] = {
        level: 0
        for level in ROUTABLE_LEVELS
        if isinstance(levels, dict) and level in levels
    }
    if not scores:
        scores = {level: 0 for level in ROUTABLE_LEVELS}
    hits: list[RuleHit] = []

    if not isinstance(levels, dict):
        return scores, hits

    for level_name, rules in levels.items():
        if level_name not in scores:
            continue
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            rule_type = rule.get("type", "")
            # Guard against unhashable types (e.g. list) that crash dict.get()
            if not isinstance(rule_type, str):
                continue
            matcher = _MATCHERS.get(rule_type)
            if matcher is None:
                continue
            hit = matcher(np, rule)
            if hit is not None:
                hit.level = level_name
                # Normalize weight: must be numeric, default to 1 if not
                if not isinstance(hit.weight, (int, float)) or isinstance(hit.weight, bool):
                    hit.weight = 1
                scores[level_name] += hit.weight
                hits.append(hit)

    return scores, hits


# ---------------------------------------------------------------------------
# Negative rules
# ---------------------------------------------------------------------------

def _apply_negative_rules(
    np: NormalizedPrompt,
    negative_rules: list[dict],
    scores: dict[str, int],
    hits: list[RuleHit],
) -> None:
    """Apply negative rules: deduct from specific levels in-place."""
    # Defensive check: ensure negative_rules is a list
    if not isinstance(negative_rules, list):
        return

    for rule in negative_rules:
        if not isinstance(rule, dict):
            continue

        apply_against = rule.get("apply_against", [])
        patterns = rule.get("patterns", [])
        weight = rule.get("weight", -2)

        # Ensure weight is numeric, default to -2 if not
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            weight = -2

        # Ensure apply_against and patterns are lists
        if not isinstance(apply_against, list):
            apply_against = []
        if not isinstance(patterns, list):
            patterns = []

        matched = False
        for pat in patterns:
            if isinstance(pat, str) and pat.lower() in np.lowered:
                matched = True
                break

        if matched:
            for level in apply_against:
                if isinstance(level, str) and level in scores:
                    scores[level] = max(0, scores[level] + weight)
            hits.append(RuleHit(
                rule_id=rule.get("id", "unknown"),
                rule_type="negative",
                level=",".join(str(lvl) for lvl in apply_against if isinstance(lvl, str)),
                weight=weight,
                detail=f"negative match suppressed: {patterns}",
            ))


# ---------------------------------------------------------------------------
# Finalization — pick the winner or declare UNCERTAIN
# ---------------------------------------------------------------------------

def _finalize_decision(
    scores: dict[str, int],
    hits: list[RuleHit],
    uncertainty: dict,
) -> tuple[str, str]:
    """Determine the final route and confidence from scores.

    Returns (route, confidence).
    """
    raw_min_score = uncertainty.get("min_score", 2)
    raw_min_gap = uncertainty.get("min_gap", 2)
    prefer_escalation = uncertainty.get("prefer_escalation_for_high_risk", True)

    # Normalize: must be numeric, fall back to safe defaults if not
    min_score = raw_min_score if isinstance(raw_min_score, (int, float)) and not isinstance(raw_min_score, bool) else 2
    min_gap = raw_min_gap if isinstance(raw_min_gap, (int, float)) and not isinstance(raw_min_gap, bool) else 2

    # Sort levels by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_level, top_score = ranked[0]
    second_level, second_score = ranked[1] if len(ranked) > 1 else ("", 0)

    gap = top_score - second_score

    # Check for high-risk hits at any routable level. If scores are close,
    # prefer the highest-scored high-risk level instead of flattening complex tasks into one bucket.
    high_risk_levels = {
        h.level
        for h in hits
        if h.risk == "high" and h.level in scores and h.weight > 0
    }

    # --- Decision logic ---

    # Case 1: No score meets minimum threshold
    if top_score < min_score:
        return "UNCERTAIN", "low"

    # Case 2: Top two scores are too close
    if gap < min_gap:
        # If high risk signal present and prefer escalation, choose the
        # strongest high-risk level rather than asking the model to guess.
        if prefer_escalation and high_risk_levels:
            best_high_risk = max(high_risk_levels, key=lambda level: scores.get(level, 0))
            if scores.get(best_high_risk, 0) > 0:
                return best_high_risk, "medium"
        return "UNCERTAIN", "low"

    # Case 3: Clear winner
    if top_score >= min_score + 1:
        confidence = "high"
    else:
        confidence = "medium"

    return top_level, confidence


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_no_task_prompt(
    prompt: str,
    root: Optional[Path] = None,
) -> RoutingDecision:
    """Classify a prompt into a routing decision when no active task exists.

    This is the single entry point used by inject-workflow-state.py.

    Args:
        prompt: The raw user prompt text.
        root: Optional workspace root for rule override loading.

    Returns:
        RoutingDecision with route, confidence, scores, and reasons.
    """
    if not prompt or not prompt.strip():
        return RoutingDecision(
            route="generic",
            confidence="low",
            scores={level: 0 for level in ROUTABLE_LEVELS},
            reasons=["empty prompt"],
        )

    # Load rules
    rules = load_routing_rules(root)

    # Normalize
    np = normalize_prompt(prompt)

    # Phase 1: Intent gate
    raw_intent_gate = rules.get("intent_gate", {})
    # Defensive: ensure intent_gate is a dict for all downstream usage
    intent_gate = raw_intent_gate if isinstance(raw_intent_gate, dict) else {}

    if _classify_intent(np, intent_gate):
        return RoutingDecision(
            route="L0",
            confidence="high",
            scores={level: 0 for level in ROUTABLE_LEVELS},
            reasons=["intent gate: question/explanation detected"],
        )

    # Phase 2: Level scoring
    raw_levels = rules.get("levels", {})
    levels = raw_levels if isinstance(raw_levels, dict) else {}
    scores, hits = _score_levels(np, levels)

    # Apply negative rules
    raw_negative_rules = rules.get("negative_rules", [])
    negative_rules = raw_negative_rules if isinstance(raw_negative_rules, list) else []
    _apply_negative_rules(np, negative_rules, scores, hits)

    # Build reasons from positive hits
    reasons = [f"{h.level}/{h.rule_id}: {h.detail}" for h in hits if h.weight > 0]
    neg_reasons = [f"negative/{h.rule_id}: {h.detail}" for h in hits if h.weight < 0]
    reasons.extend(neg_reasons)

    # Finalize
    raw_uncertainty = rules.get("uncertainty", {})
    uncertainty = raw_uncertainty if isinstance(raw_uncertainty, dict) else {}
    route, confidence = _finalize_decision(scores, hits, uncertainty)

    return RoutingDecision(
        route=route,
        confidence=confidence,
        scores=dict(scores),
        reasons=reasons,
    )
