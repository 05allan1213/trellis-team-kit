#!/usr/bin/env python3
"""
validate_routing_rules.py — Validate routing rule configuration files.

Checks:
- JSON is valid
- Top-level fields are present
- Rule types are in allowed set
- Rule IDs are unique
- Required fields per rule type are non-empty
- negative_rules.apply_against references valid levels

Usage:
    python3 validate_routing_rules.py              # validate default rules
    python3 validate_routing_rules.py path/to.json  # validate specific file
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# Types allowed inside levels.L1 / L2 / L3 / L4 / L5 rules
VALID_LEVEL_RULE_TYPES = {"keyword", "phrase", "regex", "pair", "triple"}
VALID_LEVELS = {"L1", "L2", "L3", "L4", "L5"}
REQUIRED_TOP_FIELDS = {"version", "intent_gate", "levels", "negative_rules", "uncertainty"}

# Required fields per rule type (all types require 'id')
REQUIRED_FIELDS_BY_TYPE = {
    "keyword": {"id", "terms"},
    "phrase": {"id", "patterns"},
    "regex": {"id", "patterns"},
    "pair": {"id", "verbs", "objects"},
    "triple": {"id", "subjects", "verbs", "objects"},
}


def validate_rules_file(path: Path) -> tuple[bool, list[str]]:
    """Validate a routing rules JSON file.

    Returns:
        (passed, issues): bool and list of problem descriptions.
    """
    issues: list[str] = []

    # 1. JSON validity
    if not path.is_file():
        return False, [f"File not found: {path}"]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except OSError as e:
        return False, [f"Cannot read file: {e}"]

    # 2. Top-level fields
    if not isinstance(data, dict):
        return False, ["Root element must be a JSON object"]

    for field_name in REQUIRED_TOP_FIELDS:
        if field_name not in data:
            issues.append(f"Missing top-level field: '{field_name}'")

    if issues:
        return False, issues

    # 2b. Top-level type shape — must match runtime expectations
    if not isinstance(data.get("intent_gate"), dict):
        issues.append("'intent_gate' must be a dict")

    if not isinstance(data.get("negative_rules"), list):
        issues.append("'negative_rules' must be a list")

    if not isinstance(data.get("uncertainty"), dict):
        issues.append("'uncertainty' must be a dict")

    # If intent_gate has wrong shape, bail early — runtime depends on .get()
    if isinstance(data.get("intent_gate"), dict):
        for key in ("question_keywords", "analysis_keywords", "question_patterns", "change_keywords"):
            val = data["intent_gate"].get(key)
            if val is not None and not isinstance(val, list):
                issues.append(f"intent_gate.{key} must be a list")
            elif isinstance(val, list):
                for j, elem in enumerate(val):
                    if not isinstance(elem, str):
                        issues.append(
                            f"intent_gate.{key}[{j}] must be a string, "
                            f"got {type(elem).__name__}"
                        )
                # question_patterns contains regex — validate syntax
                if key == "question_patterns":
                    for j, pat in enumerate(val):
                        if isinstance(pat, str):
                            try:
                                re.compile(pat)
                            except re.error as e:
                                issues.append(
                                    f"intent_gate.question_patterns[{j}] "
                                    f"has invalid regex: {e}"
                                )

    if issues:
        return False, issues

    # 3. Levels structure
    seen_ids: set[str] = set()
    levels = data.get("levels", {})
    if not isinstance(levels, dict):
        issues.append("'levels' must be a dict")
    else:
        for required_level in VALID_LEVELS:
            if required_level not in levels:
                issues.append(f"Missing level: '{required_level}' in 'levels'")

        # 4. Validate each rule within levels

        for level_name, rules in levels.items():
            if not isinstance(rules, list):
                issues.append(f"Level '{level_name}' must be a list of rules")
                continue

            for i, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    issues.append(f"levels.{level_name}[{i}]: must be a dict")
                    continue

                # Check 'id' field first — required and must be a non-empty string
                rule_id = rule.get("id")
                if not rule_id:
                    issues.append(
                        f"levels.{level_name}[{i}]: missing or empty required field 'id'"
                    )
                    rule_id = f"<missing-id-{i}>"
                elif not isinstance(rule_id, str):
                    issues.append(
                        f"levels.{level_name}[{i}]: 'id' must be a string, "
                        f"got {type(rule_id).__name__}"
                    )
                    rule_id = str(rule_id)

                # Check rule type — must be a string before set membership
                rule_type = rule.get("type", "")
                if not isinstance(rule_type, str):
                    issues.append(
                        f"Rule '{rule_id}' in {level_name}: "
                        f"'type' must be a string, got {type(rule_type).__name__}"
                    )
                    rule_type = ""
                elif rule_type not in VALID_LEVEL_RULE_TYPES:
                    issues.append(
                        f"Rule '{rule_id}' in {level_name}: "
                        f"invalid type '{rule_type}'. "
                        f"Allowed: {sorted(VALID_LEVEL_RULE_TYPES)}"
                    )

                # Check duplicate IDs
                if rule_id in seen_ids:
                    issues.append(f"Duplicate rule id: '{rule_id}'")
                seen_ids.add(rule_id)

                # Check required fields for rule type (id already checked above)
                required = REQUIRED_FIELDS_BY_TYPE.get(rule_type, set()) - {"id"}
                for field_name in required:
                    value = rule.get(field_name)
                    if not value:
                        issues.append(
                            f"Rule '{rule_id}' ({rule_type}): "
                            f"missing or empty required field '{field_name}'"
                        )
                    elif not isinstance(value, list):
                        issues.append(
                            f"Rule '{rule_id}' ({rule_type}): "
                            f"field '{field_name}' must be a list"
                        )
                    else:
                        # Check element types: all must be strings
                        for j, elem in enumerate(value):
                            if not isinstance(elem, str):
                                issues.append(
                                    f"Rule '{rule_id}' ({rule_type}): "
                                    f"field '{field_name}[{j}]' must be a string, "
                                    f"got {type(elem).__name__}"
                                )
                        # Check regex syntax for regex/phrase types
                        if rule_type == "regex":
                            for j, pat in enumerate(value):
                                if isinstance(pat, str):
                                    try:
                                        re.compile(pat)
                                    except re.error as e:
                                        issues.append(
                                            f"Rule '{rule_id}' ({rule_type}): "
                                            f"field '{field_name}[{j}]' has invalid regex: {e}"
                                        )

                # Check weight if present
                weight = rule.get("weight")
                if weight is not None and (isinstance(weight, bool) or not isinstance(weight, (int, float))):
                    issues.append(
                        f"Rule '{rule_id}': weight must be a number, got {type(weight).__name__}"
                    )

    # 5. Validate negative_rules
    negative_rules = data.get("negative_rules", [])
    if not isinstance(negative_rules, list):
        issues.append("'negative_rules' must be a list")
    else:
        for i, rule in enumerate(negative_rules):
            if not isinstance(rule, dict):
                issues.append(f"negative_rules[{i}]: must be a dict")
                continue

            rule_id = rule.get("id")
            if not rule_id:
                issues.append(
                    f"negative_rules[{i}]: missing or empty required field 'id'"
                )
                rule_id = f"<missing-id-neg-{i}>"
            elif not isinstance(rule_id, str):
                issues.append(
                    f"negative_rules[{i}]: 'id' must be a string, "
                    f"got {type(rule_id).__name__}"
                )
                rule_id = str(rule_id)

            # Check duplicate IDs
            if rule_id in seen_ids:
                issues.append(f"Duplicate rule id: '{rule_id}'")
            seen_ids.add(rule_id)

            # Check required fields
            if not rule.get("patterns"):
                issues.append(
                    f"Negative rule '{rule_id}': missing or empty 'patterns'"
                )
            elif not isinstance(rule.get("patterns"), list):
                issues.append(
                    f"Negative rule '{rule_id}': 'patterns' must be a list"
                )

            # Check weight type — runtime does integer arithmetic with it
            neg_weight = rule.get("weight")
            if neg_weight is not None and (isinstance(neg_weight, bool) or not isinstance(neg_weight, (int, float))):
                issues.append(
                    f"Negative rule '{rule_id}': weight must be a number, "
                    f"got {type(neg_weight).__name__}"
                )

            apply_against = rule.get("apply_against", [])
            if not apply_against:
                issues.append(
                    f"Negative rule '{rule_id}': missing or empty 'apply_against'"
                )
            elif not isinstance(apply_against, list):
                issues.append(
                    f"Negative rule '{rule_id}': 'apply_against' must be a list"
                )
            else:
                for level_ref in apply_against:
                    if not isinstance(level_ref, str):
                        issues.append(
                            f"Negative rule '{rule_id}': "
                            f"'apply_against' element must be a string, "
                            f"got {type(level_ref).__name__}"
                        )
                    elif level_ref not in VALID_LEVELS:
                        issues.append(
                            f"Negative rule '{rule_id}': "
                            f"'apply_against' references invalid level '{level_ref}'. "
                            f"Allowed: {sorted(VALID_LEVELS)}"
                        )

    # 6. Validate uncertainty config
    uncertainty = data.get("uncertainty", {})
    if not isinstance(uncertainty, dict):
        issues.append("'uncertainty' must be a dict")
    else:
        for key in ("min_score", "min_gap"):
            val = uncertainty.get(key)
            if val is not None and (isinstance(val, bool) or not isinstance(val, (int, float))):
                issues.append(f"uncertainty.{key} must be a number")

    passed = len(issues) == 0
    return passed, issues


def main() -> int:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        # Default: find the bundled routing_rules.json
        here = Path(__file__).resolve()
        for parent in [here] + list(here.parents):
            for suffix in (".trellis", "trellis"):
                candidate = parent / suffix / "config" / "routing_rules.json"
                if candidate.is_file():
                    path = candidate
                    break
            else:
                continue
            break
        else:
            print("FAIL: Cannot find routing_rules.json")
            return 1

    passed, issues = validate_rules_file(path)

    if passed:
        print(f"PASS: {path}")
        return 0
    else:
        print(f"FAIL: {path}")
        for issue in issues:
            print(f"  - {issue}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
