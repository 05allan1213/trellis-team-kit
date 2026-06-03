import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INJECT_HOOK = REPO_ROOT / "claude" / "hooks" / "inject-workflow-state.py"
VALIDATE_TASK = REPO_ROOT / "trellis" / "scripts" / "validate_task.py"
ROUTING_MODULE = REPO_ROOT / "claude" / "hooks" / "lib" / "prompt_routing.py"
VALIDATE_RULES = REPO_ROOT / "trellis" / "scripts" / "validate_routing_rules.py"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class InjectWorkflowStateTests(unittest.TestCase):
    def run_hook(self, prompt: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".trellis").mkdir()
            (root / ".trellis" / "workflow.md").write_text("", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(INJECT_HOOK)],
                input=json.dumps({"cwd": str(root), "prompt": prompt}),
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)
            return payload["hookSpecificOutput"]["additionalContext"]

    def test_l1_prompt_gets_inline_recommendation(self):
        context = self.run_hook("把按钮文案从提交改成保存")

        self.assertIn("Suggested route: L1", context)
        self.assertIn("Recommended next step: direct inline edit without creating a task", context)

    def test_l2_prompt_gets_light_task_recommendation(self):
        context = self.run_hook("给 util 增一个日期格式化函数")

        self.assertIn("Suggested route: L2", context)
        self.assertIn("ask for task-creation consent", context)
        self.assertIn("keep planning light", context)

    def test_chinese_l1_prompt_gets_inline_recommendation(self):
        context = self.run_hook("顺手把登录页的错误提示文案改一下")

        self.assertIn("Suggested route: L1", context)
        self.assertIn("direct inline edit without creating a task", context)

    def test_chinese_l2_prompt_gets_light_task_recommendation(self):
        context = self.run_hook("补一个手机号格式化工具函数")

        self.assertIn("Suggested route: L2", context)
        self.assertIn("keep planning light", context)

    def test_chinese_l3_prompt_gets_standard_task_recommendation(self):
        context = self.run_hook("把用户列表接口返回字段改一下")

        self.assertIn("Suggested route: L3+", context)
        self.assertIn("create a Trellis task", context)

    def test_chinese_ui_tweak_stays_l1(self):
        context = self.run_hook("把支付页按钮间距调一下")

        self.assertIn("Suggested route: L1", context)
        self.assertIn("direct inline edit without creating a task", context)

    def test_chinese_schema_change_goes_l3(self):
        context = self.run_hook("给订单表加一个 status 字段")

        self.assertIn("Suggested route: L3+", context)
        self.assertIn("create a Trellis task", context)

    def test_color_conversion_function_stays_l2(self):
        context = self.run_hook("补一个颜色转换函数")

        self.assertIn("Suggested route: L2", context)
        self.assertIn("keep planning light", context)

    def test_form_field_placeholder_tweak_stays_l1(self):
        context = self.run_hook("调整表单字段占位符")

        self.assertIn("Suggested route: L1", context)
        self.assertIn("direct inline edit without creating a task", context)


class ValidateTaskTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(VALIDATE_TASK, "validate_task_module")

    def make_task_dir(self, finish_md: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        task_dir = Path(tmpdir.name) / "T001-example"
        (task_dir / "research").mkdir(parents=True)

        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L2", "status": "done"}),
            encoding="utf-8",
        )
        (task_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
        (task_dir / "research" / "grill-me.md").write_text("# Grill\n", encoding="utf-8")
        (task_dir / "implement.jsonl").write_text('{"event":"implement"}\n', encoding="utf-8")
        (task_dir / "check.jsonl").write_text('{"event":"check"}\n', encoding="utf-8")
        (task_dir / "finish.md").write_text(finish_md, encoding="utf-8")
        return task_dir

    def test_done_task_requires_observable_outcomes_section(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Task Summary

                done

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("Observable Outcomes" in issue for issue in issues))

    def test_done_task_accepts_observable_outcomes_section(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Task Summary

                done

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: manual verification on local environment

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_done_task_accepts_prose_observable_outcomes(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Task Summary

                done

                ## Observable Outcomes

                用户现在可以在保存后立即看到最新状态，验证方式是本地手动走通保存流程。

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")


class PromptRoutingScorerTests(unittest.TestCase):
    """Unit tests for the scoring-based routing engine (prompt_routing.py)."""

    @classmethod
    def setUpClass(cls):
        cls.routing = load_module(ROUTING_MODULE, "prompt_routing_module")

    def classify(self, prompt: str, root=None):
        return self.routing.classify_no_task_prompt(prompt, root=root)

    def test_empty_prompt_returns_generic(self):
        d = self.classify("")
        self.assertEqual(d.route, "generic")

    def test_decision_has_required_fields(self):
        d = self.classify("补一个工具函数")
        self.assertIsInstance(d.route, str)
        self.assertIsInstance(d.confidence, str)
        self.assertIsInstance(d.scores, dict)
        self.assertIsInstance(d.reasons, list)

    def test_l1_ui_copy(self):
        d = self.classify("把按钮文案从提交改成保存")
        self.assertEqual(d.route, "L1")

    def test_l2_utility(self):
        d = self.classify("给 util 增一个日期格式化函数")
        self.assertEqual(d.route, "L2")

    def test_l3_api(self):
        d = self.classify("把用户列表接口返回字段改一下")
        self.assertEqual(d.route, "L3+")

    def test_l0_question(self):
        d = self.classify("这个函数是什么意思?")
        self.assertEqual(d.route, "L0")

    def test_uncertain_ambiguous(self):
        d = self.classify("顺手改一下字段展示方式")
        self.assertEqual(d.route, "UNCERTAIN")

    def test_color_conversion_stays_l2(self):
        d = self.classify("补一个颜色转换函数")
        self.assertEqual(d.route, "L2")

    def test_form_field_placeholder_stays_l1(self):
        d = self.classify("调整表单字段占位符")
        self.assertEqual(d.route, "L1")

    def test_scores_populated(self):
        d = self.classify("补一个颜色转换函数")
        self.assertIn("L1", d.scores)
        self.assertIn("L2", d.scores)
        self.assertIn("L3+", d.scores)
        self.assertGreater(d.scores["L2"], 0)

    def test_reasons_populated(self):
        d = self.classify("补一个颜色转换函数")
        self.assertTrue(len(d.reasons) > 0)

    def test_normalize_prompt(self):
        np = self.routing.normalize_prompt("  Hello   World  ")
        self.assertEqual(np.cleaned, "Hello World")
        self.assertEqual(np.lowered, "hello world")


class FixtureDrivenRoutingTests(unittest.TestCase):
    """Data-driven tests using tests/fixtures/routing_cases.json."""

    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(
            (FIXTURES_DIR / "routing_cases.json").read_text(encoding="utf-8")
        )

    def run_hook(self, prompt: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".trellis").mkdir()
            (root / ".trellis" / "workflow.md").write_text("", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(INJECT_HOOK)],
                input=json.dumps({"cwd": str(root), "prompt": prompt}),
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)
            return payload["hookSpecificOutput"]["additionalContext"]

    def test_all_fixture_cases(self):
        for case in self.cases:
            with self.subTest(prompt=case["prompt"]):
                context = self.run_hook(case["prompt"])
                expected = case["expected_route"]
                if expected == "UNCERTAIN":
                    self.assertIn(
                        "UNCERTAIN",
                        context,
                        f"Expected UNCERTAIN for '{case['prompt']}', got: {context}",
                    )
                    # P3: Lock in the three-phase UNCERTAIN interaction contract
                    # 1. AI gives a suggested level before asking the user
                    self.assertIn(
                        "suggested level",
                        context,
                        f"UNCERTAIN breadcrumb must instruct AI to give a suggested level "
                        f"for '{case['prompt']}', got: {context}",
                    )
                    # 2. User can accept the suggestion or choose a different level
                    self.assertIn(
                        "choose a different level",
                        context,
                        f"UNCERTAIN breadcrumb must allow user to choose a different level "
                        f"for '{case['prompt']}', got: {context}",
                    )
                    # 3. No implementation before user confirmation
                    self.assertIn(
                        "Do NOT start implementing",
                        context,
                        f"UNCERTAIN breadcrumb must forbid implementation before user confirmation "
                        f"for '{case['prompt']}', got: {context}",
                    )
                elif expected.startswith("NOT "):
                    # Assert route is NOT the specified value
                    not_route = expected[4:]  # Remove "NOT " prefix
                    self.assertNotIn(
                        f"Suggested route: {not_route}",
                        context,
                        f"Expected NOT {not_route} for '{case['prompt']}', but got it: {context}",
                    )
                else:
                    self.assertIn(
                        f"Suggested route: {expected}",
                        context,
                        f"Expected {expected} for '{case['prompt']}', got: {context}",
                    )


class FixtureDrivenScorerTests(unittest.TestCase):
    """Scorer-level data-driven tests using tests/fixtures/routing_cases.json.

    Unlike FixtureDrivenRoutingTests (which runs the full hook subprocess),
    this class calls the scorer directly, so it can validate both route and
    confidence — the hook breadcrumb does not expose confidence."""

    @classmethod
    def setUpClass(cls):
        cls.routing = load_module(ROUTING_MODULE, "prompt_routing_module")
        cls.cases = json.loads(
            (FIXTURES_DIR / "routing_cases.json").read_text(encoding="utf-8")
        )

    def test_all_fixture_confidence(self):
        for case in self.cases:
            if "expected_confidence" not in case:
                continue
            # Skip "NOT X" cases — they only test route exclusion, not exact match
            if case["expected_route"].startswith("NOT "):
                continue
            with self.subTest(prompt=case["prompt"]):
                decision = self.routing.classify_no_task_prompt(case["prompt"])
                self.assertEqual(
                    decision.route,
                    case["expected_route"],
                    f"Route mismatch for '{case['prompt']}': "
                    f"expected {case['expected_route']}, got {decision.route}",
                )
                self.assertEqual(
                    decision.confidence,
                    case["expected_confidence"],
                    f"Confidence mismatch for '{case['prompt']}': "
                    f"expected {case['expected_confidence']}, got {decision.confidence}",
                )


class WorkspaceOverrideTests(unittest.TestCase):
    """Test workspace-level rule override loading."""

    @classmethod
    def setUpClass(cls):
        cls.routing = load_module(ROUTING_MODULE, "prompt_routing_module")

    def test_default_rules_load_when_no_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".trellis").mkdir()
            # No override file — should use default rules
            d = self.routing.classify_no_task_prompt("补一个工具函数", root=root)
            self.assertIn(d.route, ("L1", "L2", "L3+", "UNCERTAIN", "L0"))

    def test_workspace_override_replaces_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_dir = root / ".trellis" / "config"
            config_dir.mkdir(parents=True)

            # Create a custom override that forces everything to L1
            override = {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": ["改"],
                },
                "levels": {
                    "L1": [
                        {
                            "id": "force_l1",
                            "type": "keyword",
                            "terms": ["函数"],
                            "weight": 10,
                        }
                    ],
                    "L2": [],
                    "L3+": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 2},
            }
            (config_dir / "routing_rules.json").write_text(
                json.dumps(override), encoding="utf-8"
            )

            d = self.routing.classify_no_task_prompt("补一个工具函数", root=root)
            self.assertEqual(d.route, "L1")

    def test_invalid_override_falls_back_to_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_dir = root / ".trellis" / "config"
            config_dir.mkdir(parents=True)

            # Write invalid JSON
            (config_dir / "routing_rules.json").write_text(
                "{invalid json", encoding="utf-8"
            )

            # Should fall back to default rules without error
            d = self.routing.classify_no_task_prompt("补一个颜色转换函数", root=root)
            self.assertEqual(d.route, "L2")


class RoutingRulesValidatorTests(unittest.TestCase):
    """Tests for validate_routing_rules.py."""

    @classmethod
    def setUpClass(cls):
        cls.validator = load_module(VALIDATE_RULES, "validate_routing_rules_module")

    def test_default_rules_pass(self):
        default_path = REPO_ROOT / "trellis" / "config" / "routing_rules.json"
        passed, issues = self.validator.validate_rules_file(default_path)
        self.assertTrue(passed, msg=f"Default rules failed: {issues}")

    def test_missing_file_fails(self):
        passed, issues = self.validator.validate_rules_file(Path("/nonexistent.json"))
        self.assertFalse(passed)

    def test_invalid_json_fails(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("{bad json")
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
        finally:
            path.unlink()

    def test_duplicate_rule_id_fails(self):
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {
                "L1": [
                    {"id": "dup", "type": "keyword", "terms": ["a"], "weight": 1},
                    {"id": "dup", "type": "keyword", "terms": ["b"], "weight": 1},
                ],
                "L2": [],
                "L3+": [],
            },
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("Duplicate" in i for i in issues))
        finally:
            path.unlink()

    def test_missing_required_field_fails(self):
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {
                "L1": [
                    {"id": "no_terms", "type": "keyword", "weight": 1},
                ],
                "L2": [],
                "L3+": [],
            },
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("terms" in i for i in issues))
        finally:
            path.unlink()

    def test_invalid_apply_against_fails(self):
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {"L1": [], "L2": [], "L3+": []},
            "negative_rules": [
                {
                    "id": "bad_neg",
                    "type": "phrase",
                    "patterns": ["x"],
                    "apply_against": ["L9"],
                    "weight": -2,
                },
            ],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("L9" in i for i in issues))
        finally:
            path.unlink()

    def test_missing_top_level_field_fails(self):
        bad_rules = {"version": 1}  # missing intent_gate, levels, etc.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("Missing top-level" in i for i in issues))
        finally:
            path.unlink()

    def test_malformed_regex_in_level_rule_fails(self):
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {
                "L1": [
                    {"id": "bad_re", "type": "regex", "patterns": ["("], "weight": 1},
                ],
                "L2": [],
                "L3+": [],
            },
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("invalid regex" in i for i in issues))
        finally:
            path.unlink()

    def test_non_string_element_in_terms_fails(self):
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {
                "L1": [
                    {"id": "bad_elem", "type": "keyword", "terms": [123], "weight": 1},
                ],
                "L2": [],
                "L3+": [],
            },
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("must be a string" in i for i in issues))
        finally:
            path.unlink()

    def test_negative_type_in_level_rule_fails(self):
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {
                "L1": [
                    {
                        "id": "neg_in_level",
                        "type": "negative",
                        "patterns": ["x"],
                        "apply_against": ["L2"],
                        "weight": -2,
                    },
                ],
                "L2": [],
                "L3+": [],
            },
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("invalid type" in i and "negative" in i for i in issues))
        finally:
            path.unlink()

    def test_malformed_regex_in_intent_gate_fails(self):
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": ["[bad"],
                "change_keywords": [],
            },
            "levels": {"L1": [], "L2": [], "L3+": []},
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("invalid regex" in i for i in issues))
        finally:
            path.unlink()

    def test_non_dict_levels_with_negative_rules_does_not_crash(self):
        """seen_ids must be defined even when levels is not a dict."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": "bad",
            "negative_rules": [
                {
                    "id": "neg1",
                    "patterns": ["x"],
                    "apply_against": ["L1"],
                    "weight": -2,
                },
            ],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("dict" in i for i in issues))
        finally:
            path.unlink()

    def test_negative_rule_non_string_id_fails(self):
        """negative_rules[*].id must be a string, not a list."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {"L1": [], "L2": [], "L3+": []},
            "negative_rules": [
                {
                    "id": [1, 2],
                    "patterns": ["x"],
                    "apply_against": ["L1"],
                    "weight": -2,
                },
            ],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("string" in i for i in issues))
        finally:
            path.unlink()

    def test_negative_rule_missing_id_fails(self):
        """negative_rules[*].id must be present."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {"L1": [], "L2": [], "L3+": []},
            "negative_rules": [
                {
                    "patterns": ["x"],
                    "apply_against": ["L1"],
                    "weight": -2,
                },
            ],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("id" in i for i in issues))
        finally:
            path.unlink()

    def test_level_rule_missing_id_fails(self):
        """Level rules must have an 'id' field."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {
                "L1": [
                    {"type": "keyword", "terms": ["test"], "weight": 1},
                ],
                "L2": [],
                "L3+": [],
            },
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("id" in i for i in issues))
        finally:
            path.unlink()

    def test_level_rule_string_weight_fails(self):
        """Level rule weight must be numeric."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {
                "L1": [
                    {"id": "r1", "type": "keyword", "terms": ["test"], "weight": "3"},
                ],
                "L2": [],
                "L3+": [],
            },
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("weight" in i for i in issues))
        finally:
            path.unlink()

    def test_uncertainty_string_values_fail(self):
        """uncertainty.min_score and min_gap must be numeric."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {"L1": [], "L2": [], "L3+": []},
            "negative_rules": [],
            "uncertainty": {"min_score": "2", "min_gap": "1"},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("number" in i for i in issues))
        finally:
            path.unlink()

    def test_bool_weight_in_level_rule_fails(self):
        """Boolean weight is not a valid number."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {
                "L1": [{"id": "r1", "type": "keyword", "terms": ["x"], "weight": True}],
                "L2": [],
                "L3+": [],
            },
            "negative_rules": [],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("weight" in i and "bool" in i for i in issues))
        finally:
            path.unlink()

    def test_bool_weight_in_negative_rule_fails(self):
        """Boolean weight in negative rule is not valid."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {"L1": [], "L2": [], "L3+": []},
            "negative_rules": [
                {"id": "neg1", "patterns": ["x"], "apply_against": ["L1"], "weight": False}
            ],
            "uncertainty": {"min_score": 2, "min_gap": 2},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("weight" in i and "bool" in i for i in issues))
        finally:
            path.unlink()

    def test_bool_uncertainty_values_fail(self):
        """Boolean min_score/min_gap are not valid numbers."""
        bad_rules = {
            "version": 1,
            "intent_gate": {
                "question_keywords": [],
                "question_patterns": [],
                "change_keywords": [],
            },
            "levels": {"L1": [], "L2": [], "L3+": []},
            "negative_rules": [],
            "uncertainty": {"min_score": True, "min_gap": False},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(bad_rules, f)
            path = Path(f.name)
        try:
            passed, issues = self.validator.validate_rules_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("number" in i for i in issues))
        finally:
            path.unlink()


class RuntimeBoolHandlingTests(unittest.TestCase):
    """Test that runtime normalizes bool values to defaults."""

    @classmethod
    def setUpClass(cls):
        cls.routing = load_module(ROUTING_MODULE, "prompt_routing_module")

    def test_bool_weight_in_level_rule_normalized(self):
        """Bool weight in level rule should be normalized to 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / ".trellis" / "config" / "routing_rules.json"
            rules_path.parent.mkdir(parents=True)
            rules_path.write_text(json.dumps({
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": []
                },
                "levels": {
                    "L1": [
                        {"id": "r1", "type": "keyword", "terms": ["test"], "weight": True}
                    ],
                    "L2": [],
                    "L3+": []
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 1}
            }))
            decision = self.routing.classify_no_task_prompt("test", root=Path(tmpdir))
            # Bool weight normalized to 1, score too low for L1
            self.assertEqual(decision.scores["L1"], 1)

    def test_bool_weight_in_negative_rule_normalized(self):
        """Bool weight in negative rule should be normalized to -2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / ".trellis" / "config" / "routing_rules.json"
            rules_path.parent.mkdir(parents=True)
            rules_path.write_text(json.dumps({
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": []
                },
                "levels": {
                    "L1": [
                        {"id": "r1", "type": "keyword", "terms": ["test"], "weight": 5}
                    ],
                    "L2": [],
                    "L3+": []
                },
                "negative_rules": [
                    {
                        "id": "neg1",
                        "patterns": ["test"],
                        "apply_against": ["L1"],
                        "weight": False  # Should normalize to -2
                    }
                ],
                "uncertainty": {"min_score": 2, "min_gap": 1}
            }))
            decision = self.routing.classify_no_task_prompt("test", root=Path(tmpdir))
            # L1 starts at 5, negative rule with weight=-2 brings it to 3
            self.assertEqual(decision.scores["L1"], 3)

    def test_bool_uncertainty_values_use_defaults(self):
        """Bool min_score/min_gap should use default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / ".trellis" / "config" / "routing_rules.json"
            rules_path.parent.mkdir(parents=True)
            rules_path.write_text(json.dumps({
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": []
                },
                "levels": {
                    "L1": [
                        {"id": "r1", "type": "keyword", "terms": ["test"], "weight": 1}
                    ],
                    "L2": [],
                    "L3+": []
                },
                "negative_rules": [],
                "uncertainty": {
                    "min_score": True,  # Should use default 2
                    "min_gap": False     # Should use default 1
                }
            }))
            decision = self.routing.classify_no_task_prompt("test", root=Path(tmpdir))
            # With min_score=2 (default), score of 1 is below threshold → UNCERTAIN
            self.assertEqual(decision.route, "UNCERTAIN")


class MalformedOverrideRuntimeTests(unittest.TestCase):
    """Test that runtime degrades gracefully on malformed overrides that
    bypass validation (or when validation is skipped)."""

    @classmethod
    def setUpClass(cls):
        cls.routing = load_module(ROUTING_MODULE, "prompt_routing_module")

    def _write_override(self, root: Path, override: dict) -> None:
        config_dir = root / ".trellis" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "routing_rules.json").write_text(
            json.dumps(override), encoding="utf-8"
        )

    def test_malformed_regex_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_override(root, {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": ["add"],
                },
                "levels": {
                    "L1": [
                        {"id": "bad_re", "type": "regex", "patterns": ["("], "weight": 1}
                    ],
                    "L2": [],
                    "L3+": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 2},
            })
            # Must not raise re.error
            d = self.routing.classify_no_task_prompt("add feature", root=root)
            self.assertIsInstance(d.route, str)

    def test_non_string_elements_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_override(root, {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": [],
                },
                "levels": {
                    "L1": [
                        {
                            "id": "bad_terms",
                            "type": "keyword",
                            "terms": [123, None],
                            "weight": 1,
                        }
                    ],
                    "L2": [],
                    "L3+": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 2},
            })
            # Must not raise AttributeError
            d = self.routing.classify_no_task_prompt("test prompt", root=root)
            self.assertIsInstance(d.route, str)

    def test_negative_type_in_levels_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_override(root, {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": [],
                },
                "levels": {
                    "L1": [
                        {
                            "id": "neg_in_level",
                            "type": "negative",
                            "patterns": ["x"],
                            "apply_against": ["L2"],
                            "weight": -2,
                        }
                    ],
                    "L2": [],
                    "L3+": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 2},
            })
            # Must not crash; rule is silently ignored
            d = self.routing.classify_no_task_prompt("test prompt", root=root)
            self.assertIsInstance(d.route, str)

    def test_non_string_elements_in_pair_rule_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_override(root, {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": [],
                },
                "levels": {
                    "L1": [
                        {
                            "id": "bad_pair",
                            "type": "pair",
                            "verbs": [456],
                            "objects": [None],
                            "weight": 1,
                        }
                    ],
                    "L2": [],
                    "L3+": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 2},
            })
            d = self.routing.classify_no_task_prompt("test prompt", root=root)
            self.assertIsInstance(d.route, str)

    def test_non_string_elements_in_triple_rule_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_override(root, {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": [],
                },
                "levels": {
                    "L1": [],
                    "L2": [],
                    "L3+": [
                        {
                            "id": "bad_triple",
                            "type": "triple",
                            "subjects": [123],
                            "verbs": [None],
                            "objects": [True],
                            "weight": 4,
                        }
                    ],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 2},
            })
            d = self.routing.classify_no_task_prompt("test prompt", root=root)
            self.assertIsInstance(d.route, str)

    def test_string_weight_does_not_crash(self):
        """String weight in level rules should not crash runtime."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_override(root, {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": [],
                },
                "levels": {
                    "L1": [
                        {"id": "r1", "type": "keyword", "terms": ["test"], "weight": "3"}
                    ],
                    "L2": [],
                    "L3+": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 2},
            })
            d = self.routing.classify_no_task_prompt("test prompt", root=root)
            self.assertIsInstance(d.route, str)

    def test_unhashable_rule_type_does_not_crash(self):
        """Unhashable type (list, dict) should not crash _MATCHERS lookup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_override(root, {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": [],
                },
                "levels": {
                    "L1": [
                        {"id": "r1", "type": [], "terms": ["test"], "weight": 1}
                    ],
                    "L2": [],
                    "L3+": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": 2, "min_gap": 2},
            })
            d = self.routing.classify_no_task_prompt("test prompt", root=root)
            self.assertIsInstance(d.route, str)

    def test_string_min_score_min_gap_does_not_crash(self):
        """String min_score/min_gap should not crash comparison operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_override(root, {
                "version": 1,
                "intent_gate": {
                    "question_keywords": [],
                    "question_patterns": [],
                    "change_keywords": [],
                },
                "levels": {
                    "L1": [
                        {"id": "r1", "type": "keyword", "terms": ["test"], "weight": 1}
                    ],
                    "L2": [],
                    "L3+": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": "2", "min_gap": "1"},
            })
            d = self.routing.classify_no_task_prompt("test prompt", root=root)
            self.assertIsInstance(d.route, str)


if __name__ == "__main__":
    unittest.main()
