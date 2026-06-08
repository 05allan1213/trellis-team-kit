import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INJECT_HOOK = REPO_ROOT / "claude" / "hooks" / "inject-workflow-state.py"
PROTECT_HOOK = REPO_ROOT / "claude" / "hooks" / "protect-dangerous-actions.py"
STOP_GUARD_HOOK = REPO_ROOT / "claude" / "hooks" / "stop-guard.py"
NOTIFY_HOOK = REPO_ROOT / "claude" / "hooks" / "trellis-notify.sh"
VALIDATE_TASK = REPO_ROOT / "trellis" / "scripts" / "validate_task.py"
VALIDATE_REVIEW_GATES = REPO_ROOT / "trellis" / "scripts" / "validate_review_gates.py"
VALIDATE_WORKFLOW_STATE = REPO_ROOT / "trellis" / "scripts" / "validate_workflow_state.py"
VALIDATE_DELIVERY_SYNC = REPO_ROOT / "trellis" / "scripts" / "validate_delivery_sync.py"
VALIDATE_RUNTIME_HARDENING = REPO_ROOT / "trellis" / "scripts" / "validate_runtime_hardening.py"
VALIDATE_TRELLIS_CONFIG = REPO_ROOT / "trellis" / "scripts" / "validate_trellis_config.py"
VALIDATE_SCOPE_MANIFEST = REPO_ROOT / "trellis" / "scripts" / "validate_scope_manifest.py"
VALIDATE_GUARDRAIL_OVERRIDES = REPO_ROOT / "trellis" / "scripts" / "validate_guardrail_overrides.py"
VALIDATE_AGENT_RESULTS = REPO_ROOT / "trellis" / "scripts" / "validate_agent_results.py"
VALIDATE_SPEC_INDEX = REPO_ROOT / "trellis" / "scripts" / "validate_spec_index.py"
REPLAY_WORKFLOW_CASES = REPO_ROOT / "trellis" / "scripts" / "replay_workflow_cases.py"
DETECT_SPEC_UPDATE_CANDIDATES = (
    REPO_ROOT / "trellis" / "scripts" / "detect_spec_update_candidates.py"
)
PREPARE_FINISH_WORKSPACE = REPO_ROOT / "trellis" / "scripts" / "prepare_finish_workspace.py"
FINALIZE_TASK_ARCHIVE = REPO_ROOT / "trellis" / "scripts" / "finalize_task_archive.py"
INIT_SH = REPO_ROOT / "bootstrap" / "init.sh"
PERSONALIZE_LOCAL = REPO_ROOT / "bootstrap" / "personalize-local.sh"
INIT_LOCAL = REPO_ROOT / "bootstrap" / "init-local.sh"
SMOKE_INSTALL = REPO_ROOT / "bootstrap" / "smoke-test-install.sh"
ROUTING_MODULE = REPO_ROOT / "claude" / "hooks" / "lib" / "prompt_routing.py"
VALIDATE_RULES = REPO_ROOT / "trellis" / "scripts" / "validate_routing_rules.py"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
SPEC_TEMPLATE_ROOT = REPO_ROOT / "marketplace" / "specs" / "web-app"
SPEC_MANIFEST = REPO_ROOT / "trellis" / "spec-manifest.txt"
COMMON_MISTAKES_REL = "guides/ai-behavior/common-mistakes.md"
COMMON_MISTAKES_INSTALLED = ".trellis/spec/guides/ai-behavior/common-mistakes.md"
COMMON_MISTAKES_TEMPLATE = (
    REPO_ROOT / "trellis" / "spec-templates" / "guides" / "ai-behavior" / "common-mistakes.md"
)


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
        self.assertIn("Workflow profile: quick.", context)
        self.assertIn("Friction budget: minimal", context)
        self.assertIn("Recommended next step: direct inline edit without creating a task", context)

    def test_l2_prompt_gets_light_task_recommendation(self):
        context = self.run_hook("给 util 增一个日期格式化函数")

        self.assertIn("Suggested route: L2", context)
        self.assertIn("Workflow profile: light.", context)
        self.assertIn("Friction budget: low", context)
        self.assertIn("ask for task-creation consent", context)
        self.assertIn("keep planning light", context)
        self.assertIn("minimal implement.md", context)

    def test_chinese_l1_prompt_gets_inline_recommendation(self):
        context = self.run_hook("顺手把登录页的错误提示文案改一下")

        self.assertIn("Suggested route: L1", context)
        self.assertIn("direct inline edit without creating a task", context)

    def test_chinese_l2_prompt_gets_light_task_recommendation(self):
        context = self.run_hook("补一个手机号格式化工具函数")

        self.assertIn("Suggested route: L2", context)
        self.assertIn("keep planning light", context)

    def test_chinese_api_contract_prompt_gets_l4_recommendation(self):
        context = self.run_hook("把用户列表接口返回字段改一下")

        self.assertIn("Suggested route: L4", context)
        self.assertIn("Workflow profile: strict.", context)
        self.assertIn("Required: design.md + Review Gate Contract + architecture-review.", context)
        self.assertIn("strict cross-layer task", context)
        self.assertIn("architecture-review", context)

    def test_chinese_ui_tweak_stays_l1(self):
        context = self.run_hook("把支付页按钮间距调一下")

        self.assertIn("Suggested route: L1", context)
        self.assertIn("direct inline edit without creating a task", context)

    def test_chinese_schema_change_routes_l4(self):
        context = self.run_hook("给订单表加一个 status 字段")

        self.assertIn("Suggested route: L4", context)
        self.assertIn("create a Trellis task", context)

    def test_standard_feature_routes_l3(self):
        context = self.run_hook("新增用户管理 CRUD 功能")

        self.assertIn("Suggested route: L3", context)
        self.assertIn("Workflow profile: standard.", context)
        self.assertIn("Friction budget: normal", context)
        self.assertIn("standard task", context)
        self.assertIn("code-review", context)

    def test_large_refactor_routes_l5(self):
        context = self.run_hook("重构整个订单模块，拆成多个子 agent 并行做")

        self.assertIn("Suggested route: L5", context)
        self.assertIn("Workflow profile: orchestrated.", context)
        self.assertIn("Friction budget: very high", context)
        self.assertIn("Trellis-native parallel", context)
        self.assertIn("merge-review", context)

    def test_omc_requires_explicit_approval(self):
        context = self.run_hook("用 OMC ultrawork 并行重构整个订单模块")

        self.assertIn("Suggested route: L5", context)
        self.assertIn("explicit user approval", context)
        self.assertNotIn("start OMC", context)

    def test_color_conversion_function_stays_l2(self):
        context = self.run_hook("补一个颜色转换函数")

        self.assertIn("Suggested route: L2", context)
        self.assertIn("keep planning light", context)

    def test_form_field_placeholder_tweak_stays_l1(self):
        context = self.run_hook("调整表单字段占位符")

        self.assertIn("Suggested route: L1", context)
        self.assertIn("direct inline edit without creating a task", context)


class InjectWorkflowTaskPhaseTests(unittest.TestCase):
    def run_hook(self, root: Path) -> str:
        result = subprocess.run(
            [sys.executable, str(INJECT_HOOK)],
            input=json.dumps({"cwd": str(root), "prompt": "继续"}),
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        return payload["hookSpecificOutput"]["additionalContext"]

    def make_repo(self, finish_md: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / ".trellis" / "tasks" / "T001-demo"
        task_dir.mkdir(parents=True)
        (root / ".trellis" / "active-task").write_text(
            ".trellis/tasks/T001-demo",
            encoding="utf-8",
        )
        (root / ".trellis" / "workflow.md").write_text("", encoding="utf-8")
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").write_text(finish_md, encoding="utf-8")
        return root

    def test_finishing_inference_requires_recorded_finish_approval(self):
        root = self.make_repo(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: done
                - Evidence: tests
                """
            )
        )

        context = self.run_hook(root)

        self.assertNotIn("Inferred phase: FINISHING", context)

    def test_finishing_inference_accepts_recorded_finish_approval(self):
        root = self.make_repo(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Finish Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 进入 Finish 阶段
                - timestamp: 2026-06-04T12:00:00Z
                - summary approved: enter finish

                Allowed to proceed with finish?
                - [x] yes
                - [ ] no
                """
            )
        )

        context = self.run_hook(root)

        self.assertIn("Inferred phase: FINISHING", context)


class ReplayWorkflowCasesTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(REPLAY_WORKFLOW_CASES, "replay_workflow_cases_module")

    def test_runner_api_replays_hook_case_and_checks_absence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cases_dir = root / "replay" / "routing"
            cases_dir.mkdir(parents=True)
            (cases_dir / "standard-feature.json").write_text(
                json.dumps(
                    {
                        "name": "standard feature routes L3",
                        "run": "inject-workflow-state",
                        "input": {"prompt": "implement CRUD feature"},
                        "expect": {
                            "contains": ["Suggested route: L3"],
                            "not_contains": ["Suggested route: L5"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            results = self.module.run_replay_cases(cases_dir)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed, msg=results[0].message)
        self.assertIn("Suggested route: L3", results[0].text)

    def test_runner_api_reports_contains_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cases_dir = root / "replay" / "routing"
            cases_dir.mkdir(parents=True)
            (cases_dir / "bad-expectation.json").write_text(
                json.dumps(
                    {
                        "name": "bad expectation",
                        "run": "inject-workflow-state",
                        "input": {"prompt": "implement CRUD feature"},
                        "expect": {"contains": ["Suggested route: L5"]},
                    }
                ),
                encoding="utf-8",
            )

            results = self.module.run_replay_cases(cases_dir)

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].passed)
        self.assertIn("missing expected text", results[0].message)

    def test_replay_lab_cli_runs_checked_in_fixtures(self):
        result = subprocess.run(
            [sys.executable, str(REPLAY_WORKFLOW_CASES), str(FIXTURES_DIR / "replay")],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("routing", result.stdout)
        self.assertIn("guardrails", result.stdout)
        self.assertIn("finish", result.stdout)
        self.assertIn("orchestration", result.stdout)

    def test_replay_lab_includes_documented_plan_fixtures(self):
        expected = {
            "routing/l1-inline-copy.json",
            "routing/l2-light-util.json",
            "routing/l3-standard-feature.json",
            "routing/l4-api-contract-change.json",
            "routing/l5-multi-agent-refactor.json",
            "routing/uncertain-scope.json",
            "guardrails/planning-edit-source-block.json",
            "guardrails/before-dev-missing-block.json",
            "guardrails/high-risk-undeclared-warning.json",
            "guardrails/override-ledger.json",
            "finish/finish-without-approval-block.json",
            "finish/finish-with-overrides-requires-review.json",
            "orchestration/trellis-native-parallel-default.json",
            "orchestration/omc-requires-explicit-approval.json",
        }
        replay_root = FIXTURES_DIR / "replay"
        actual = {
            path.relative_to(replay_root).as_posix()
            for path in replay_root.rglob("*.json")
        }

        self.assertTrue(expected.issubset(actual), msg=f"Missing replay fixtures: {sorted(expected - actual)}")


class ValidateTaskTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(VALIDATE_TASK, "validate_task_module")

    def make_task_dir(self, finish_md: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        (root / ".trellis" / "spec" / "guides").mkdir(parents=True)
        (root / ".trellis" / "spec" / "guides" / "index.md").write_text(
            "# Guides\n", encoding="utf-8"
        )

        task_dir = root / "T001-example"
        (task_dir / "research").mkdir(parents=True)
        (task_dir / "validation").mkdir(parents=True)

        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L2", "status": "done"}),
            encoding="utf-8",
        )
        (task_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "research" / "grill-me.md").write_text("# Grill\n", encoding="utf-8")
        (task_dir / "implement.jsonl").write_text(
            json.dumps(
                {
                    "file": ".trellis/spec/guides/index.md",
                    "reason": "Shared implementation guidance",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (task_dir / "check.jsonl").write_text(
            json.dumps(
                {
                    "file": "T001-example/research/grill-me.md",
                    "reason": "Review risks and edge cases during verification",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L2",
                    "profile": "light",
                    "declared_paths": ["src/settings.py"],
                    "declared_globs": [],
                    "high_risk_allowed": [],
                    "out_of_scope": ["auth flows"],
                }
            ),
            encoding="utf-8",
        )
        (task_dir / "validation" / "check-results.md").write_text(
            textwrap.dedent(
                """\
                ## Verdict: PASS
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "finish.md").write_text(finish_md, encoding="utf-8")
        return task_dir

    def standard_finish_suffix(self) -> str:
        return textwrap.dedent(
            """\

            ## Finish Approval

            Approval status:
            - [x] approved

            Approval source:
            - user message: 进入 Finish 阶段
            - timestamp: 2026-06-04T12:00:00Z
            - summary approved: enter finish

            Allowed to proceed with finish?
            - [x] yes
            - [ ] no

            ## Delivery Sync Check

            - [x] README / user docs reviewed
            - [x] Example commands / scripts reviewed
            - [x] Public API paths / contracts reviewed
            - [x] Implemented vs planned status reviewed

            Files checked:
            - README.md — reviewed
            """
        )

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
                + self.standard_finish_suffix()
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
                + self.standard_finish_suffix()
            )
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_l2_done_task_allows_minimal_artifacts_without_grill_or_jsonl(self):
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
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "research" / "grill-me.md").unlink()
        (task_dir / "implement.jsonl").unlink()
        (task_dir / "check.jsonl").unlink()

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_l3_done_task_still_requires_jsonl_context(self):
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
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "done"}),
            encoding="utf-8",
        )
        (task_dir / "implement.jsonl").unlink()
        (task_dir / "check.jsonl").unlink()

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("required 'implement.jsonl'" in issue for issue in issues))
        self.assertTrue(any("required 'check.jsonl'" in issue for issue in issues))

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
                + self.standard_finish_suffix()
            )
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_done_task_accepts_table_observable_outcomes(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Task Summary

                done

                ## Observable Outcomes

                | # | Outcome | Evidence |
                |---|---------|----------|
                | 1 | saving a record shows the updated state | manual verification on local environment |

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
                + self.standard_finish_suffix()
            )
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_missing_level_fails_when_task_has_artifacts(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "status": "done"}),
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("missing 'level' field" in issue for issue in issues))

    def test_jsonl_rejects_task_artifact_context(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "implement.jsonl").write_text(
            json.dumps(
                {
                    "file": "T001-example/prd.md",
                    "reason": "bad context",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("outside allowed spec/research context" in issue for issue in issues))

    def test_jsonl_accepts_task_dir_placeholder_for_research(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "check.jsonl").write_text(
            json.dumps(
                {
                    "file": "$TASK_DIR/research/grill-me.md",
                    "reason": "Review risks and edge cases during verification",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_relative_archived_task_path_resolves_task_dir_placeholders(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        archived_task = root / ".trellis" / "tasks" / "archive" / "2026-06" / "demo-task"
        (root / ".trellis" / "spec" / "guides").mkdir(parents=True)
        (archived_task / "research").mkdir(parents=True)
        (root / ".trellis" / "spec" / "guides" / "index.md").write_text("# Guides\n", encoding="utf-8")
        (archived_task / "research" / "grill-me.md").write_text("# Grill\n", encoding="utf-8")
        (archived_task / "task.json").write_text(
            json.dumps({"id": "demo-task", "level": "L2", "status": "completed"}),
            encoding="utf-8",
        )
        (archived_task / "prd.md").write_text("# PRD\n", encoding="utf-8")
        (archived_task / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Demo

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            ),
            encoding="utf-8",
        )
        (archived_task / "implement.jsonl").write_text(
            json.dumps(
                {
                    "file": "$TASK_DIR/research/grill-me.md",
                    "reason": "Task research context",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (archived_task / "check.jsonl").write_text(
            json.dumps(
                {
                    "file": "$TASK_DIR/research/grill-me.md",
                    "reason": "Verification context",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (archived_task / "validation").mkdir(parents=True, exist_ok=True)
        (archived_task / "validation" / "check-results.md").write_text(
            "## Verdict: PASS\n",
            encoding="utf-8",
        )
        (archived_task / "finish.md").write_text(
            textwrap.dedent(
                """\
                # Finish: Demo

                ## Observable Outcomes

                - Outcome: archived validation passes
                - Evidence: validate_task.py

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
            + self.standard_finish_suffix(),
            encoding="utf-8",
        )

        old_cwd = Path.cwd()
        try:
            os.chdir(root)
            ok, issues = self.module.validate_task(Path(".trellis/tasks/archive/2026-06/demo-task"))
        finally:
            os.chdir(old_cwd)

        self.assertTrue(ok, msg=f"Unexpected issues for relative archived task path: {issues}")

    def test_in_progress_requires_recorded_approval(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Review Gate Contract

                - [x] trellis-check

                ## Implementation Approval

                Approval status:
                - [ ] approved

                Approval source:
                - user message:
                - timestamp:
                - summary approved:

                Allowed to run task.py start?
                - [ ] yes
                - [x] no
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "validation" / "check-results.md").unlink()

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("Implementation Approval" in issue for issue in issues))

    def test_done_task_requires_finish_approval_and_delivery_sync(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "done"}),
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("Finish Approval" in issue for issue in issues))
        self.assertTrue(any("Delivery Sync Check" in issue for issue in issues))

    def test_check_gate_requires_validation_check_results(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Review Gate Contract

                - [x] trellis-check
                - [x] trellis-code-review

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "validation" / "check-results.md").unlink()

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("check-results.md is missing" in issue for issue in issues))

    def test_check_gate_requires_results_even_if_required_gate_checkbox_is_unchecked(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "done"}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Review Gate Contract

                ### Required gates (always run)

                - [ ] trellis-check

                ### Selected gates for this task

                - [x] trellis-code-review

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "validation" / "check-results.md").unlink()

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("trellis-check is required" in issue for issue in issues))

    def test_check_gate_passes_with_valid_check_results(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "validation").mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "done"}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Review Gate Contract

                - [x] trellis-check
                - [x] trellis-code-review

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "validation" / "check-results.md").write_text(
            textwrap.dedent(
                """\
                ## Build
                - [x] pass

                ## Test
                - [x] pass

                ## Ready for finish-work?
                - [x] yes
                """
            ),
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def make_l4_in_progress_task(self, implement_md: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        (root / ".trellis" / "spec" / "guides").mkdir(parents=True)
        (root / ".trellis" / "spec" / "guides" / "index.md").write_text(
            "# Guides\n", encoding="utf-8"
        )

        task_dir = root / "T004-cross-layer"
        (task_dir / "research").mkdir(parents=True)
        (task_dir / "validation").mkdir(parents=True)
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T004", "level": "L4", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
        (task_dir / "design.md").write_text("# Design\n", encoding="utf-8")
        (task_dir / "research" / "grill-me.md").write_text("# Grill\n", encoding="utf-8")
        (task_dir / "implement.md").write_text(implement_md, encoding="utf-8")
        (task_dir / "implement.jsonl").write_text(
            json.dumps({"file": ".trellis/spec/guides/index.md", "reason": "guidance"}) + "\n",
            encoding="utf-8",
        )
        (task_dir / "check.jsonl").write_text(
            json.dumps({"file": "$TASK_DIR/research/grill-me.md", "reason": "risks"}) + "\n",
            encoding="utf-8",
        )
        (task_dir / "validation" / "check-results.md").write_text(
            "## Verdict: PASS\n", encoding="utf-8"
        )
        return task_dir

    def test_l4_requires_execution_mode_decision(self):
        task_dir = self.make_l4_in_progress_task(
            textwrap.dedent(
                """\
                # Implement: Cross Layer

                ## Review Gate Contract

                - [x] trellis-check
                - [x] trellis-spec-review
                - [x] trellis-code-review
                - [x] trellis-code-architecture-review

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            )
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("Execution Mode Decision" in issue for issue in issues))

    def test_l4_accepts_trellis_native_execution_mode_decision(self):
        task_dir = self.make_l4_in_progress_task(
            textwrap.dedent(
                """\
                # Implement: Cross Layer

                ## Execution Mode Decision

                Recommended mode:
                - [ ] main session
                - [ ] single Trellis subagent
                - [x] Trellis subagents
                - [ ] Trellis-native parallel + worktree
                - [ ] OMC ulw/ultrawork + worktree + parent/child

                Reason:
                - API contract change needs strict review but not parallel execution.

                Why not heavier:
                - OMC is unnecessary because one workstream is enough.

                OMC approval:
                - [x] not applicable
                - [ ] user explicitly approved OMC
                - user message:
                - timestamp:

                ## Review Gate Contract

                - [x] trellis-check
                - [x] trellis-spec-review
                - [x] trellis-code-review
                - [x] trellis-code-architecture-review

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            )
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_l2_in_progress_requires_scope_manifest(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L2", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").unlink()
        (task_dir / "scope-manifest.json").unlink()
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: user settings\n- Files likely touched: src/settings.py\n",
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("scope-manifest.json" in issue for issue in issues))

    def test_scope_manifest_requires_declared_paths_or_globs(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L2", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").unlink()
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: user settings\n- Files likely touched: src/settings.py\n",
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L2",
                    "profile": "light",
                    "declared_paths": [],
                    "declared_globs": [],
                    "high_risk_allowed": [],
                    "out_of_scope": [],
                }
            ),
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("declared_paths or declared_globs" in issue for issue in issues))

    def test_scope_manifest_requires_high_risk_allowed_path_list(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L4", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").unlink()
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: api\n- Files likely touched: api/users.py\n",
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L4",
                    "profile": "strict",
                    "declared_paths": ["api/users.py"],
                    "declared_globs": [],
                    "high_risk_allowed": True,
                    "out_of_scope": ["auth policy changes"],
                }
            ),
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("high_risk_allowed must be a list of strings" in issue for issue in issues))

    def test_scope_manifest_requires_out_of_scope_boundaries(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").unlink()
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: settings\n- Files likely touched: src/settings.py\n",
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L3",
                    "profile": "standard",
                    "declared_paths": ["src/settings.py"],
                    "declared_globs": [],
                    "high_risk_allowed": [],
                    "out_of_scope": [],
                }
            ),
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("out_of_scope must be non-empty" in issue for issue in issues))

    def test_scope_manifest_requires_high_risk_scope_allowlist_coverage(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L4", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").unlink()
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: api\n- Files likely touched: api/users/*.py\n",
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L4",
                    "profile": "strict",
                    "declared_paths": [],
                    "declared_globs": ["api/users/*.py"],
                    "high_risk_allowed": [],
                    "out_of_scope": ["auth policy changes"],
                }
            ),
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("high-risk declared scope" in issue for issue in issues))

    def test_valid_scope_manifest_satisfies_in_progress_scope_contract(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L2", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").unlink()
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: user settings\n- Files likely touched: src/settings.py\n",
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L2",
                    "profile": "light",
                    "declared_paths": ["src/settings.py"],
                    "declared_globs": [],
                    "high_risk_allowed": [],
                    "out_of_scope": ["auth flows"],
                }
            ),
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_finish_requires_guardrail_override_review_when_ledger_exists(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "runtime").mkdir(exist_ok=True)
        (task_dir / "runtime" / "guardrail-overrides.jsonl").write_text(
            json.dumps(
                {
                    "timestamp": "2026-06-08T10:00:00Z",
                    "kind": "soft_warning",
                    "decision": "accepted",
                    "reason": "needed API compatibility shim",
                    "tool_name": "Edit",
                    "path": "api/users.py",
                    "message": "WARNING: Editing high-risk undeclared path",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("Guardrail Overrides" in issue for issue in issues))

    def test_finish_accepts_guardrail_override_review(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Guardrail Overrides

                - [x] override ledger reviewed
                - Ledger: runtime/guardrail-overrides.jsonl
                - Decision: accepted - API compatibility shim stayed within approved risk.

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
                + self.standard_finish_suffix()
            )
        )
        (task_dir / "runtime").mkdir(exist_ok=True)
        (task_dir / "runtime" / "guardrail-overrides.jsonl").write_text(
            json.dumps(
                {
                    "timestamp": "2026-06-08T10:00:00Z",
                    "kind": "soft_warning",
                    "decision": "accepted",
                    "reason": "needed API compatibility shim",
                    "tool_name": "Edit",
                    "path": "api/users.py",
                    "message": "WARNING: Editing high-risk undeclared path",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        ok, issues = self.module.validate_task(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_l5_parallel_task_requires_agent_results(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: saving a record shows the updated state
                - Evidence: local verification

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            )
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L5", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").unlink()
        (task_dir / "design.md").write_text("# Design\n", encoding="utf-8")
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: orders\n- Files likely touched: src/orders\n",
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L5",
                    "profile": "orchestrated",
                    "declared_paths": ["src/orders"],
                    "declared_globs": ["tests/orders/*.py"],
                    "high_risk_allowed": [],
                    "out_of_scope": ["billing"],
                }
            ),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Execution Mode Decision

                Recommended mode:
                - [ ] main session
                - [ ] single Trellis subagent
                - [ ] Trellis subagents
                - [x] Trellis-native parallel + worktree
                - [ ] OMC ulw/ultrawork + worktree + parent/child

                OMC approval:
                - [x] not applicable
                - [ ] user explicitly approved OMC
                - user message:
                - timestamp:

                ## Review Gate Contract

                - [x] trellis-check
                - [x] trellis-spec-review
                - [x] trellis-code-review
                - [x] trellis-code-architecture-review
                - [x] trellis-improve-codebase-architecture deep-review
                - [x] trellis-merge-review

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "review").mkdir(exist_ok=True)
        for name in (
            "spec-review.md",
            "code-review.md",
            "architecture-review.md",
            "architecture-deep-review.md",
            "merge-review.md",
        ):
            (task_dir / "review" / name).write_text("## Verdict\nPASS\n", encoding="utf-8")

        ok, issues = self.module.validate_task(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("agent-results" in issue for issue in issues))


class ProtectDangerousActionsTests(unittest.TestCase):
    def make_repo(
        self,
        *,
        status: str,
        implement_md: str,
        before_dev_md: str | None = None,
        finish_md: str | None = None,
    ) -> tuple[Path, Path]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / ".trellis" / "tasks" / "T001-demo"
        task_dir.mkdir(parents=True)

        (root / ".trellis" / "active-task").write_text(
            ".trellis/tasks/T001-demo",
            encoding="utf-8",
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": status}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(implement_md, encoding="utf-8")
        if before_dev_md is not None:
            (task_dir / "before-dev.md").write_text(before_dev_md, encoding="utf-8")
        if finish_md is not None:
            (task_dir / "finish.md").write_text(finish_md, encoding="utf-8")
        return root, task_dir

    def run_hook(self, root: Path, payload: dict) -> dict | None:
        result = subprocess.run(
            [sys.executable, str(PROTECT_HOOK)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)

    def approval_block(
        self,
        *,
        approved: bool,
        start_allowed: bool,
        user_message: str = "",
        timestamp: str = "",
        summary_approved: str = "",
    ) -> str:
        approved_mark = "x" if approved else " "
        not_requested_mark = " " if approved else "x"
        yes_mark = "x" if start_allowed else " "
        no_mark = " " if start_allowed else "x"
        return textwrap.dedent(
            f"""\
            # Implement: Example

            ## Review Gate Contract

            ### Selected gates for this task

            - [x] trellis-code-review

            ## Implementation Approval

            Approval status:
            - [{not_requested_mark}] requested
            - [{approved_mark}] approved

            Approval source:
            - user message: {user_message}
            - timestamp: {timestamp}
            - summary approved: {summary_approved}

            Allowed to run task.py start?
            - [{yes_mark}] yes
            - [{no_mark}] no
            """
        )

    def finish_md_with_approval(self, *, approved: bool) -> str:
        approved_mark = "x" if approved else " "
        no_mark = " " if approved else "x"
        return textwrap.dedent(
            f"""\
            # Finish: Example

            ## Finish Approval

            Approval status:
            - [{approved_mark}] approved

            Approval source:
            - user message: 进入 Finish 阶段
            - timestamp: 2026-06-04T12:00:00Z
            - summary approved: enter finish

            Allowed to proceed with finish?
            - [{approved_mark}] yes
            - [{no_mark}] no

            ## Observable Outcomes

            - Outcome: done
            - Evidence: test

            ## Delivery Sync Check

            - [x] README / user docs reviewed
            - [x] Example commands / scripts reviewed
            - [x] Public API paths / contracts reviewed
            - [x] Implemented vs planned status reviewed

            Files checked:
            - README.md — docs synchronized

            ## Spec Update Decision

            - **Need update?**: no
            - **Reason**: none
            """
        )

    def test_task_start_requires_full_implementation_approval_record(self):
        root, task_dir = self.make_repo(
            status="planning",
            implement_md=self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
            ),
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Bash",
            "tool_input": {
                "command": f"python3 ./.trellis/scripts/task.py start {task_dir}"
            },
            "prompt": "开始实现",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "summary approved",
            response["hookSpecificOutput"]["permissionDecisionReason"],
        )

    def test_source_edit_requires_full_implementation_approval_record(self):
        root, _ = self.make_repo(
            status="in_progress",
            implement_md=self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
            ),
            before_dev_md="# Before Dev\n- Scope: src\n- Files likely touched: src/app.py\n",
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Edit",
            "tool_input": {"file_path": "src/app.py"},
            "prompt": "继续实现",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "implementation approval",
            response["hookSpecificOutput"]["permissionDecisionReason"].lower(),
        )

    def test_high_risk_undeclared_path_is_soft_warning(self):
        implement_md = (
            self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
                timestamp="2026-06-04T10:00:00Z",
                summary_approved="start implementation",
            )
            + textwrap.dedent(
                """\

                ## Files / Areas Likely Touched

                - `src/app.py`
                """
            )
        )
        root, _ = self.make_repo(
            status="in_progress",
            implement_md=implement_md,
            before_dev_md="# Before Dev\n- Scope: src\n- Files likely touched: src/app.py\n",
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Edit",
            "tool_input": {"file_path": "api/users.py"},
            "prompt": "继续实现",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "allow",
        )
        self.assertIn(
            "WARNING: Editing high-risk undeclared path",
            response["hookSpecificOutput"]["permissionDecisionReason"],
        )

    def test_scope_manifest_glob_allows_declared_high_risk_path(self):
        implement_md = self.approval_block(
            approved=True,
            start_allowed=True,
            user_message="开始实现",
            timestamp="2026-06-04T10:00:00Z",
            summary_approved="start implementation",
        )
        root, task_dir = self.make_repo(
            status="in_progress",
            implement_md=implement_md,
            before_dev_md="# Before Dev\n- Scope: API users\n- Files likely touched: api/users/*.py\n",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L4",
                    "profile": "strict",
                    "declared_paths": [],
                    "declared_globs": ["api/users/*.py"],
                    "high_risk_allowed": ["api/users/*.py"],
                    "out_of_scope": ["auth policy changes"],
                }
            ),
            encoding="utf-8",
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Edit",
            "tool_input": {"file_path": "api/users/list.py"},
            "prompt": "继续实现",
        }
        response = self.run_hook(root, payload)

        self.assertIsNone(response)

    def test_declared_high_risk_path_without_high_risk_allowlist_warns(self):
        implement_md = self.approval_block(
            approved=True,
            start_allowed=True,
            user_message="开始实现",
            timestamp="2026-06-04T10:00:00Z",
            summary_approved="start implementation",
        )
        root, task_dir = self.make_repo(
            status="in_progress",
            implement_md=implement_md,
            before_dev_md="# Before Dev\n- Scope: API users\n- Files likely touched: api/users/*.py\n",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L4",
                    "profile": "strict",
                    "declared_paths": [],
                    "declared_globs": ["api/users/*.py"],
                    "high_risk_allowed": [],
                    "out_of_scope": ["auth policy changes"],
                }
            ),
            encoding="utf-8",
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Edit",
            "tool_input": {"file_path": "api/users/list.py"},
            "prompt": "继续实现",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "allow",
        )
        self.assertIn(
            "WARNING: Editing high-risk path without high_risk_allowed",
            response["hookSpecificOutput"]["permissionDecisionReason"],
        )

    def test_guardrail_override_writes_runtime_ledger(self):
        implement_md = (
            self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
                timestamp="2026-06-04T10:00:00Z",
                summary_approved="start implementation",
            )
            + textwrap.dedent(
                """\

                ## Files / Areas Likely Touched

                - `src/app.py`
                """
            )
        )
        root, task_dir = self.make_repo(
            status="in_progress",
            implement_md=implement_md,
            before_dev_md="# Before Dev\n- Scope: src\n- Files likely touched: src/app.py\n",
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Edit",
            "tool_input": {"file_path": "api/users.py"},
            "prompt": "override team-kit guardrail: needed API compatibility shim",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "allow",
        )
        ledger = task_dir / "runtime" / "guardrail-overrides.jsonl"
        self.assertTrue(ledger.is_file())
        entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["decision"], "accepted")
        self.assertEqual(entries[0]["reason"], "needed API compatibility shim")
        self.assertEqual(entries[0]["path"], "api/users.py")

    def test_hard_block_override_attempt_is_denied_and_recorded(self):
        root, task_dir = self.make_repo(
            status="in_progress",
            implement_md=self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
                timestamp="2026-06-04T10:00:00Z",
                summary_approved="start implementation",
            ),
            before_dev_md="# Before Dev\n- Scope: src\n- Files likely touched: src/app.py\n",
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf dist"},
            "prompt": "override team-kit guardrail: cleanup generated files",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "OVERRIDE DENIED",
            response["hookSpecificOutput"]["permissionDecisionReason"],
        )
        ledger = task_dir / "runtime" / "guardrail-overrides.jsonl"
        self.assertTrue(ledger.is_file())
        entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(entries[0]["decision"], "denied")
        self.assertEqual(entries[0]["command"], "rm -rf dist")

    def test_finish_file_write_requires_explicit_finish_consent(self):
        root, _ = self.make_repo(
            status="in_progress",
            implement_md=self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
                timestamp="2026-06-04T10:00:00Z",
                summary_approved="start implementation",
            ),
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Write",
            "tool_input": {"file_path": ".trellis/tasks/T001-demo/finish.md"},
            "prompt": "继续",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "finish",
            response["hookSpecificOutput"]["permissionDecisionReason"].lower(),
        )

    def test_git_commit_requires_recorded_finish_approval(self):
        root, _ = self.make_repo(
            status="in_progress",
            implement_md=self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
                timestamp="2026-06-04T10:00:00Z",
                summary_approved="start implementation",
            ),
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'done'"},
            "prompt": "继续",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "finish",
            response["hookSpecificOutput"]["permissionDecisionReason"].lower(),
        )

    def test_git_commit_allowed_after_finish_approval_is_recorded(self):
        root, _ = self.make_repo(
            status="in_progress",
            implement_md=self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
                timestamp="2026-06-04T10:00:00Z",
                summary_approved="start implementation",
            ),
            finish_md=self.finish_md_with_approval(approved=True),
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'done'"},
            "prompt": "继续",
        }
        response = self.run_hook(root, payload)

        self.assertIsNone(response)

    def test_raw_task_archive_requires_finalize_wrapper(self):
        root, task_dir = self.make_repo(
            status="in_progress",
            implement_md=self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
                timestamp="2026-06-04T10:00:00Z",
                summary_approved="start implementation",
            ),
            finish_md=self.finish_md_with_approval(approved=True),
        )

        payload = {
            "cwd": str(root),
            "tool_name": "Bash",
            "tool_input": {"command": f"python3 ./.trellis/scripts/task.py archive {task_dir}"},
            "prompt": "进入 Finish 阶段",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "finalize_task_archive.py",
            response["hookSpecificOutput"]["permissionDecisionReason"],
        )

    def test_git_commit_blocked_until_runtime_state_prepared(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True)

        task_dir = root / ".trellis" / "tasks" / "T001-demo"
        (task_dir / "review").mkdir(parents=True)
        (root / ".trellis" / "scripts").mkdir(parents=True)
        (root / ".trellis" / "active-task").write_text(".trellis/tasks/T001-demo", encoding="utf-8")
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(
            self.approval_block(
                approved=True,
                start_allowed=True,
                user_message="开始实现",
                timestamp="2026-06-04T10:00:00Z",
                summary_approved="start implementation",
            ),
            encoding="utf-8",
        )
        (task_dir / "finish.md").write_text(
            self.finish_md_with_approval(approved=True),
            encoding="utf-8",
        )
        (root / ".trellis" / "scripts" / "prepare_finish_workspace.py").write_text(
            PREPARE_FINISH_WORKSPACE.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        omc_state = root / ".omc" / "state"
        omc_state.mkdir(parents=True)
        (omc_state / "hud-stdin-cache.json").write_text("{}", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True, text=True)

        payload = {
            "cwd": str(root),
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'done'"},
            "prompt": "进入 Finish 阶段",
        }
        response = self.run_hook(root, payload)

        self.assertIsNotNone(response)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "prepare_finish_workspace.py",
            response["hookSpecificOutput"]["permissionDecisionReason"],
        )


class StopGuardTests(unittest.TestCase):
    def make_repo(self) -> tuple[Path, Path]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / ".trellis" / "tasks" / "T001-demo"
        (task_dir / "review").mkdir(parents=True)
        (task_dir / "validation").mkdir(parents=True)
        scripts_dir = root / ".trellis" / "scripts"
        scripts_dir.mkdir(parents=True)
        (root / ".trellis" / "active-task").write_text(
            ".trellis/tasks/T001-demo",
            encoding="utf-8",
        )
        for src in (
            VALIDATE_TASK,
            VALIDATE_SCOPE_MANIFEST,
            VALIDATE_GUARDRAIL_OVERRIDES,
            VALIDATE_AGENT_RESULTS,
            VALIDATE_REVIEW_GATES,
            VALIDATE_DELIVERY_SYNC,
        ):
            (scripts_dir / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L3", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Review Gate Contract

                ### Selected gates for this task

                - [x] trellis-code-review

                ## Implementation Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 开始实现
                - timestamp: 2026-06-04T10:00:00Z
                - summary approved: start implementation

                Allowed to run task.py start?
                - [x] yes
                - [ ] no
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "validation" / "check-results.md").write_text(
            "## Status\n- [x] pass\n",
            encoding="utf-8",
        )
        (task_dir / "validation" / "test-results.md").write_text(
            textwrap.dedent(
                """\
                ## Build
                - [x] pass

                ## Test
                - [x] pass

                ## Ready for finish-work?
                - [x] yes
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "review" / "code-review.md").write_text(
            textwrap.dedent(
                """\
                ## Status
                - [x] pass

                ## Scope reviewed
                - code

                ## Blocking issues
                - none
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "finish.md").write_text(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: done
                - Evidence: tests

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            ),
            encoding="utf-8",
        )
        return root, task_dir

    def run_hook(self, root: Path, payload: dict) -> dict:
        result = subprocess.run(
            [sys.executable, str(STOP_GUARD_HOOK)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_claiming_done_blocks_when_finish_artifact_is_incomplete(self):
        root, _ = self.make_repo()

        response = self.run_hook(
            root,
            {
                "cwd": str(root),
                "message": "任务完成了",
            },
        )

        self.assertEqual(response["decision"], "block")
        self.assertIn("Finish Approval", response["reason"])

    def test_claiming_done_accepts_canonical_gate_verdict_sections(self):
        root, task_dir = self.make_repo()
        (task_dir / "validation" / "check-results.md").write_text(
            textwrap.dedent(
                """\
                # Check Results: Example

                ## Verdict

                - PASS — all checks pass
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "review" / "code-review.md").write_text(
            textwrap.dedent(
                """\
                # Code Quality Review

                ## Verdict

                PASS

                ## Blocking Issues

                - none
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
        (task_dir / "research").mkdir(parents=True)
        (task_dir / "research" / "grill-me.md").write_text("# Grill\n", encoding="utf-8")
        (task_dir / "implement.jsonl").write_text(
            json.dumps({"file": "$TASK_DIR/research/grill-me.md", "reason": "context"}) + "\n",
            encoding="utf-8",
        )
        (task_dir / "check.jsonl").write_text(
            json.dumps({"file": "$TASK_DIR/research/grill-me.md", "reason": "verify"}) + "\n",
            encoding="utf-8",
        )
        (task_dir / "finish.md").write_text(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Finish Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 进入 Finish 阶段
                - timestamp: 2026-06-04T12:00:00Z
                - summary approved: enter finish

                Allowed to proceed with finish?
                - [x] yes
                - [ ] no

                ## Observable Outcomes

                - Outcome: done
                - Evidence: tests

                ## Delivery Sync Check

                - [x] README / user docs reviewed
                - [x] Example commands / scripts reviewed
                - [x] Public API paths / contracts reviewed
                - [x] Implemented vs planned status reviewed

                Files checked:
                - README.md — reviewed

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, str(STOP_GUARD_HOOK)],
            input=json.dumps({"cwd": str(root), "message": "任务完成了"}),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout.strip(), "")


class ValidateScopeManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(VALIDATE_SCOPE_MANIFEST, "validate_scope_manifest_module")

    def make_task_dir(self, manifest: dict | None) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / "T002-scope"
        task_dir.mkdir()
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T002", "level": "L2", "status": "in_progress"}),
            encoding="utf-8",
        )
        if manifest is not None:
            (task_dir / "scope-manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )
        return task_dir

    def test_missing_manifest_fails_for_l2_task(self):
        task_dir = self.make_task_dir(None)

        ok, issues = self.module.validate_scope_manifest(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("scope-manifest.json" in issue for issue in issues))

    def test_manifest_requires_path_or_glob(self):
        task_dir = self.make_task_dir(
            {
                "version": 1,
                "level": "L2",
                "profile": "light",
                "declared_paths": [],
                "declared_globs": [],
                "high_risk_allowed": [],
                "out_of_scope": [],
            }
        )

        ok, issues = self.module.validate_scope_manifest(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("declared_paths or declared_globs" in issue for issue in issues))

    def test_valid_manifest_passes(self):
        task_dir = self.make_task_dir(
            {
                "version": 1,
                "level": "L2",
                "profile": "light",
                "declared_paths": ["src/settings.py"],
                "declared_globs": ["tests/settings_*.py"],
                "high_risk_allowed": [],
                "out_of_scope": ["auth flows"],
            }
        )

        ok, issues = self.module.validate_scope_manifest(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")


class ValidateGuardrailOverridesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(VALIDATE_GUARDRAIL_OVERRIDES, "validate_guardrail_overrides_module")

    def make_task_dir(self, *, ledger: str, finish_md: str = "") -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / "T003-overrides"
        (task_dir / "runtime").mkdir(parents=True)
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T003", "level": "L3", "status": "done"}),
            encoding="utf-8",
        )
        (task_dir / "runtime" / "guardrail-overrides.jsonl").write_text(
            ledger,
            encoding="utf-8",
        )
        if finish_md:
            (task_dir / "finish.md").write_text(finish_md, encoding="utf-8")
        return task_dir

    def test_override_line_requires_reason_and_decision(self):
        task_dir = self.make_task_dir(
            ledger=json.dumps(
                {
                    "timestamp": "2026-06-08T10:00:00Z",
                    "tool_name": "Edit",
                    "path": "api/users.py",
                }
            )
            + "\n"
        )

        ok, issues = self.module.validate_guardrail_overrides(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("reason" in issue for issue in issues))
        self.assertTrue(any("decision" in issue for issue in issues))

    def test_override_requires_finish_review(self):
        task_dir = self.make_task_dir(
            ledger=json.dumps(
                {
                    "timestamp": "2026-06-08T10:00:00Z",
                    "kind": "soft_warning",
                    "decision": "accepted",
                    "reason": "needed API compatibility shim",
                    "tool_name": "Edit",
                    "path": "api/users.py",
                    "message": "WARNING",
                }
            )
            + "\n",
            finish_md="# Finish\n",
        )

        ok, issues = self.module.validate_guardrail_overrides(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("Guardrail Overrides" in issue for issue in issues))

    def test_override_review_passes_when_finish_records_decision(self):
        task_dir = self.make_task_dir(
            ledger=json.dumps(
                {
                    "timestamp": "2026-06-08T10:00:00Z",
                    "kind": "soft_warning",
                    "decision": "accepted",
                    "reason": "needed API compatibility shim",
                    "tool_name": "Edit",
                    "path": "api/users.py",
                    "message": "WARNING",
                }
            )
            + "\n",
            finish_md=textwrap.dedent(
                """\
                # Finish

                ## Guardrail Overrides

                - [x] override ledger reviewed
                - Ledger: runtime/guardrail-overrides.jsonl
                - Decision: accepted - API compatibility shim stayed within approved risk.
                """
            ),
        )

        ok, issues = self.module.validate_guardrail_overrides(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")


class ValidateAgentResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(VALIDATE_AGENT_RESULTS, "validate_agent_results_module")

    def make_task_dir(self) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / "T004-agents"
        (task_dir / "agent-results").mkdir(parents=True)
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T004", "level": "L5", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Agents

                ## Execution Mode Decision

                Recommended mode:
                - [ ] main session
                - [ ] single Trellis subagent
                - [ ] Trellis subagents
                - [x] Trellis-native parallel + worktree
                - [ ] OMC ulw/ultrawork + worktree + parent/child

                OMC approval:
                - [x] not applicable
                - [ ] user explicitly approved OMC
                - user message:
                - timestamp:

                ## Review Gate Contract

                - [x] trellis-check
                - [x] trellis-code-review
                - [x] trellis-merge-review
                """
            ),
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L5",
                    "profile": "orchestrated",
                    "declared_paths": ["src/orders"],
                    "declared_globs": ["tests/orders/*.py"],
                    "high_risk_allowed": [],
                    "out_of_scope": ["billing changes"],
                    "workstreams": [
                        {"name": "orders-api", "owner": "trellis-implementer"},
                        {"name": "orders-tests", "owner": "trellis-checker"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return task_dir

    def write_result(self, task_dir: Path, name: str, payload: dict) -> None:
        (task_dir / "agent-results" / name).write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def valid_result(self, *, agent: str = "trellis-implementer", changed_files: list[str] | None = None) -> dict:
        files = changed_files or ["src/orders/service.py"]
        return {
            "version": 1,
            "agent": agent,
            "status": "PASS",
            "workstream": "orders-api" if agent == "trellis-implementer" else "orders-tests",
            "changed_files": [
                {"path": file_path, "summary": "validated by replay test"}
                for file_path in files
            ],
            "validation": [
                {"command": "pytest tests/orders", "status": "PASS"}
            ],
            "blocking_issues": [],
            "non_blocking_issues": [],
            "risks": [],
            "scope_expansion": [],
        }

    def test_agent_result_requires_core_fields(self):
        task_dir = self.make_task_dir()
        self.write_result(
            task_dir,
            "trellis-implementer-20260608T100000Z.json",
            {"version": 1, "agent": "trellis-implementer"},
        )

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("status" in issue for issue in issues))
        self.assertTrue(any("changed_files" in issue for issue in issues))
        self.assertTrue(any("validation" in issue for issue in issues))
        self.assertTrue(any("blocking_issues" in issue for issue in issues))

    def test_agent_result_rejects_legacy_changed_files_string_list(self):
        task_dir = self.make_task_dir()
        payload = self.valid_result()
        payload["changed_files"] = ["src/orders/service.py"]
        self.write_result(task_dir, "trellis-implementer-a.json", payload)

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("changed_files must be a list of objects" in issue for issue in issues))

    def test_declared_workstream_without_agent_result_fails(self):
        task_dir = self.make_task_dir()
        self.write_result(
            task_dir,
            "trellis-implementer-a.json",
            self.valid_result(agent="trellis-implementer", changed_files=["src/orders/service.py"]),
        )

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("missing agent result for declared workstream 'orders-tests'" in issue for issue in issues))

    def test_agent_result_requires_workstream_when_declared(self):
        task_dir = self.make_task_dir()
        payload = self.valid_result(agent="trellis-implementer", changed_files=["src/orders/service.py"])
        payload.pop("workstream")
        self.write_result(task_dir, "trellis-implementer-a.json", payload)

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("missing required workstream" in issue for issue in issues))

    def test_agent_result_rejects_unknown_workstream(self):
        task_dir = self.make_task_dir()
        payload = self.valid_result(agent="trellis-implementer", changed_files=["src/orders/service.py"])
        payload["workstream"] = "billing"
        self.write_result(task_dir, "trellis-implementer-a.json", payload)

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("unknown workstream 'billing'" in issue for issue in issues))

    def test_duplicate_changed_files_fail_merge_review_readiness(self):
        task_dir = self.make_task_dir()
        self.write_result(
            task_dir,
            "trellis-implementer-a.json",
            self.valid_result(agent="trellis-implementer", changed_files=["src/orders/service.py"]),
        )
        self.write_result(
            task_dir,
            "trellis-checker-b.json",
            self.valid_result(agent="trellis-checker", changed_files=["src/orders/service.py"]),
        )

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("modified by multiple agents" in issue for issue in issues))

    def test_undeclared_changed_file_fails(self):
        task_dir = self.make_task_dir()
        self.write_result(
            task_dir,
            "trellis-implementer-a.json",
            self.valid_result(changed_files=["api/orders.py"]),
        )

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("not declared" in issue for issue in issues))

    def test_task_local_result_artifacts_do_not_require_scope_declaration(self):
        task_dir = self.make_task_dir()
        self.write_result(
            task_dir,
            "trellis-implementer-a.json",
            self.valid_result(agent="trellis-implementer", changed_files=["src/orders/service.py"]),
        )
        self.write_result(
            task_dir,
            "trellis-checker-b.json",
            self.valid_result(agent="trellis-checker", changed_files=["tests/orders/test_service.py"]),
        )
        self.write_result(
            task_dir,
            "trellis-merge-reviewer-a.json",
            self.valid_result(
                agent="trellis-merge-reviewer",
                changed_files=[
                    "review/merge-review.md",
                    "agent-results/trellis-merge-reviewer-a.json",
                ],
            ),
        )

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")

    def test_failed_validation_fails(self):
        task_dir = self.make_task_dir()
        payload = self.valid_result()
        payload["validation"] = [{"command": "pytest tests/orders", "status": "FAIL"}]
        self.write_result(task_dir, "trellis-checker-a.json", payload)

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("validation failed" in issue for issue in issues))

    def test_blocking_issues_fail(self):
        task_dir = self.make_task_dir()
        payload = self.valid_result(agent="trellis-code-reviewer")
        payload["blocking_issues"] = ["src/orders/service.py:42 misses idempotency"]
        self.write_result(task_dir, "trellis-code-reviewer-a.json", payload)

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("blocking issue" in issue for issue in issues))

    def test_omc_agent_result_requires_explicit_approval(self):
        task_dir = self.make_task_dir()
        payload = self.valid_result()
        payload["execution_mode"] = "omc"
        self.write_result(task_dir, "trellis-implementer-a.json", payload)

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("explicit OMC approval" in issue for issue in issues))

    def test_valid_agent_results_pass(self):
        task_dir = self.make_task_dir()
        self.write_result(
            task_dir,
            "trellis-implementer-a.json",
            self.valid_result(agent="trellis-implementer", changed_files=["src/orders/service.py"]),
        )
        self.write_result(
            task_dir,
            "trellis-checker-b.json",
            self.valid_result(agent="trellis-checker", changed_files=["tests/orders/test_service.py"]),
        )

        ok, issues = self.module.validate_agent_results(task_dir)

        self.assertTrue(ok, msg=f"Unexpected issues: {issues}")


class SubagentStopGuardAgentResultsTests(unittest.TestCase):
    def make_repo(self) -> tuple[Path, Path]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / ".trellis" / "tasks" / "T005-agent-stop"
        task_dir.mkdir(parents=True)
        (root / ".trellis" / "active-task").write_text(
            ".trellis/tasks/T005-agent-stop",
            encoding="utf-8",
        )
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T005", "level": "L5", "status": "in_progress"}),
            encoding="utf-8",
        )
        return root, task_dir

    def run_hook(self, root: Path, payload: dict) -> dict | None:
        result = subprocess.run(
            [sys.executable, str(STOP_GUARD_HOOK.parent / "subagent-stop-guard.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)

    def valid_implementer_output(self) -> str:
        return textwrap.dedent(
            """\
            ## Implementation Complete

            ### Files Modified

            - `src/orders/service.py` -- implemented workflow

            ### Implementation Summary

            Implemented order workflow.

            ### Validation Attempted

            - Tests: pass

            ### Unresolved Risks

            - None identified

            Did not commit.
            """
        )

    def test_blocks_when_agent_result_json_missing(self):
        root, _ = self.make_repo()

        response = self.run_hook(
            root,
            {
                "cwd": str(root),
                "agent_type": "trellis-implementer",
                "last_assistant_message": self.valid_implementer_output(),
            },
        )

        self.assertIsNotNone(response)
        self.assertEqual(response["decision"], "block")
        self.assertIn("agent-results", response["reason"])

    def test_accepts_when_agent_result_json_exists(self):
        root, task_dir = self.make_repo()
        (task_dir / "agent-results").mkdir()
        (task_dir / "agent-results" / "trellis-implementer-20260608T100000Z.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "agent": "trellis-implementer",
                    "status": "PASS",
                    "workstream": "orders-api",
                    "changed_files": [
                        {
                            "path": "src/orders/service.py",
                            "summary": "implemented workflow",
                        }
                    ],
                    "validation": [{"command": "pytest tests/orders", "status": "PASS"}],
                    "blocking_issues": [],
                    "non_blocking_issues": [],
                    "risks": [],
                    "scope_expansion": [],
                }
            ),
            encoding="utf-8",
        )

        response = self.run_hook(
            root,
            {
                "cwd": str(root),
                "agent_type": "trellis-implementer",
                "last_assistant_message": self.valid_implementer_output(),
            },
        )

        self.assertIsNone(response)


class ValidateDeliverySyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(VALIDATE_DELIVERY_SYNC, "validate_delivery_sync_module")

    def init_repo(self) -> tuple[Path, Path]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / ".trellis" / "tasks" / "T001-demo"
        task_dir.mkdir(parents=True)

        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        (root / "README.md").write_text(
            "Use `/api/events/export` to export data.\n",
            encoding="utf-8",
        )
        (root / "internal" / "handler").mkdir(parents=True)
        (root / "internal" / "handler" / "router.go").write_text(
            'router.GET("/api/events/export", exportCSV)\n',
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L4", "status": "in_progress"}),
            encoding="utf-8",
        )
        (task_dir / "finish.md").write_text(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Finish Approval

                Approval status:
                - [x] approved

                Approval source:
                - user message: 进入 Finish 阶段
                - timestamp: 2026-06-04T12:00:00Z
                - summary approved: enter finish

                Allowed to proceed with finish?
                - [x] yes
                - [ ] no

                ## Observable Outcomes

                - Outcome: export works
                - Evidence: api test

                ## Delivery Sync Check

                - [x] README / user docs reviewed
                - [x] Example commands / scripts reviewed
                - [x] Public API paths / contracts reviewed
                - [x] Implemented vs planned status reviewed

                Files checked:
                - README.md — reviewed

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none
                """
            ),
            encoding="utf-8",
        )
        return root, task_dir

    def test_removed_public_route_left_in_readme_fails(self):
        root, task_dir = self.init_repo()
        (root / "internal" / "handler" / "router.go").write_text(
            'router.GET("/api/events/export/csv", exportCSV)\n',
            encoding="utf-8",
        )

        ok, issues = self.module.validate_delivery_sync(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("/api/events/export" in issue for issue in issues))


class ValidateWorkflowStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(VALIDATE_WORKFLOW_STATE, "validate_workflow_state_module")

    def test_archived_task_fails_on_placeholder_workspace_records(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / ".trellis" / "tasks" / "archive" / "2026-06" / "demo-task"
        task_dir.mkdir(parents=True)
        workspace_dir = root / ".trellis" / "workspace" / "alice"
        workspace_dir.mkdir(parents=True)

        (task_dir / "task.json").write_text(
            json.dumps({"id": "demo-task", "title": "Demo Task", "status": "completed"}),
            encoding="utf-8",
        )
        (workspace_dir / "journal-1.md").write_text(
            "demo-task\n(No commits - planning session)\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "workspace" / "index.md").write_text(
            "(none yet)\n",
            encoding="utf-8",
        )
        (workspace_dir / "index.md").write_text(
            "| 1 | 2026-06-04 | demo-task | - | `master` |\n",
            encoding="utf-8",
        )

        ok = self.module.validate_workflow_state(str(task_dir))

        self.assertFalse(ok)

    def _init_git_repo(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    def _write_valid_completed_workspace(self, root: Path) -> Path:
        task_dir = root / ".trellis" / "tasks" / "archive" / "2026-06" / "demo-task"
        task_dir.mkdir(parents=True)
        workspace_dir = root / ".trellis" / "workspace" / "alice"
        workspace_dir.mkdir(parents=True)

        (task_dir / "task.json").write_text(
            json.dumps(
                {
                    "id": "demo-task",
                    "title": "Demo Task",
                    "status": "completed",
                }
            ),
            encoding="utf-8",
        )
        (root / ".trellis" / "workspace" / "index.md").write_text(
            textwrap.dedent(
                """\
                # Workspace Index

                | Developer | Last Active | Sessions | Active File |
                |-----------|-------------|----------|-------------|
                | alice | 2026-06-04 | 1 | `journal-1.md` |
                """
            ),
            encoding="utf-8",
        )
        (workspace_dir / "index.md").write_text(
            "| 1 | 2026-06-04 | demo-task: Demo Task | 1 | `master` |\n",
            encoding="utf-8",
        )
        (workspace_dir / "journal-1.md").write_text(
            "demo-task\n- `abc1234` archived task finalized\n",
            encoding="utf-8",
        )
        return task_dir

    def test_archived_task_ignores_deletion_only_runtime_state(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        self._init_git_repo(root)
        task_dir = self._write_valid_completed_workspace(root)
        (root / ".omc" / "state").mkdir(parents=True)
        (root / ".omc" / "state" / "hud.json").write_text("{}", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True, text=True)

        (root / ".gitignore").write_text(".omc/\n", encoding="utf-8")
        subprocess.run(
            ["git", "rm", "--cached", "-r", ".omc"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        ok = self.module.validate_workflow_state(str(task_dir))

        self.assertTrue(ok)

    def test_archived_task_still_fails_on_modified_runtime_state(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        self._init_git_repo(root)
        task_dir = self._write_valid_completed_workspace(root)
        (root / ".omc" / "state").mkdir(parents=True)
        runtime_file = root / ".omc" / "state" / "hud.json"
        runtime_file.write_text("{}", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True, text=True)

        runtime_file.write_text("{\"changed\": true}", encoding="utf-8")

        ok = self.module.validate_workflow_state(str(task_dir))

        self.assertFalse(ok)


class PrepareFinishWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(PREPARE_FINISH_WORKSPACE, "prepare_finish_workspace_module")

    def test_prepare_finish_workspace_ignores_and_untracks_local_state(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True)

        (root / ".omc" / "state").mkdir(parents=True)
        (root / ".omc" / "state" / "hud.json").write_text("{}", encoding="utf-8")
        (root / ".claude").mkdir()
        (root / ".claude" / "settings.local.json").write_text("{}", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True, text=True)

        changes, warnings = self.module.prepare_finish_workspace(root)

        self.assertTrue(any(".gitignore" in change for change in changes))
        tracked = subprocess.run(
            ["git", "ls-files", ".omc", ".claude/settings.local.json"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(tracked, "")
        gitignore = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".omc/", gitignore)
        self.assertFalse(warnings)

    def test_prepare_finish_workspace_removes_stale_trellis_worktree_residue(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True)

        stale = root / ".trellis" / "worktrees" / "stale-task" / ".trellis" / "tasks"
        stale.mkdir(parents=True)

        changes, warnings = self.module.prepare_finish_workspace(root)

        self.assertFalse(stale.parent.parent.exists())
        self.assertTrue(any("stale trellis worktree residue" in change for change in changes))
        gitignore = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".trellis/worktrees/", gitignore)
        self.assertFalse(warnings)


class InitLocalScriptTests(unittest.TestCase):
    def test_personalize_local_creates_workspace_scaffold(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        (root / ".trellis").mkdir(parents=True)
        (root / ".trellis" / ".team-kit-version").write_text("1\n", encoding="utf-8")

        subprocess.run(
            ["bash", str(PERSONALIZE_LOCAL), "alice"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        settings_local = (root / ".claude" / "settings.local.json").read_text(encoding="utf-8")
        self.assertIn("Bash(npm test *)", settings_local)
        self.assertEqual((root / ".trellis" / ".developer").read_text(encoding="utf-8").strip(), "alice")
        self.assertTrue((root / ".trellis" / "workspace" / "index.md").is_file())
        self.assertTrue((root / ".trellis" / "workspace" / "alice" / "index.md").is_file())
        self.assertTrue((root / ".trellis" / "workspace" / "alice" / "journal-1.md").is_file())
        self.assertFalse((root / ".trellis" / "workspace" / "alice" / "journal.md").exists())
        self.assertTrue((root / ".trellis" / "workspace" / "alice" / "preferences.md").is_file())

        workspace_index = (root / ".trellis" / "workspace" / "index.md").read_text(encoding="utf-8")
        self.assertIn("| (none yet) | - | - | - |", workspace_index)
        developer_index = (root / ".trellis" / "workspace" / "alice" / "index.md").read_text(encoding="utf-8")
        self.assertIn("<!-- @@@auto:current-status -->", developer_index)
        self.assertIn("`journal-1.md`", developer_index)

    def test_init_local_wrapper_delegates_to_personalize_local(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        (root / ".trellis").mkdir(parents=True)
        (root / ".trellis" / ".team-kit-version").write_text("1\n", encoding="utf-8")

        result = subprocess.run(
            ["bash", str(INIT_LOCAL), "alice"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("compatibility alias", result.stderr)
        self.assertTrue((root / ".trellis" / "workspace" / "alice" / "preferences.md").is_file())


class InitScriptTests(unittest.TestCase):
    def _init_git_repo(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True)

    def _write_fake_trellis(self, bin_dir: Path) -> None:
        script = bin_dir / "trellis"
        script.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail

                if [ "${1:-}" != "init" ]; then
                  echo "unexpected args: $*" >&2
                  exit 1
                fi

                mkdir -p .trellis/spec .trellis/tasks .trellis/config
                """
            ),
            encoding="utf-8",
        )
        script.chmod(0o755)

    def _write_fake_claude(self, bin_dir: Path) -> None:
        script = bin_dir / "claude"
        script.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail

                if [ "${1:-}" = "plugin" ] && [ "${2:-}" = "list" ]; then
                  cat <<'EOF'
                Installed plugins:

                  ❯ superpowers@claude-plugins-official
                    Version: 5.1.0
                    Scope: user
                    Status: ✘ disabled
                EOF
                  exit 0
                fi

                echo "unexpected args: $*" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        script.chmod(0o755)

    def _run_init(self, root: Path, env: dict[str, str], mode: str) -> subprocess.CompletedProcess[str]:
        if mode == "local":
            return subprocess.run(
                ["bash", str(INIT_SH), "alice"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
        if mode == "remote":
            raw_base = REPO_ROOT.resolve().as_uri()
            cmd = f"TTK_INIT_RAW_BASE='{raw_base}' bash <(cat '{INIT_SH}') alice"
            return subprocess.run(
                ["bash", "-lc", cmd],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
        raise ValueError(f"unsupported mode: {mode}")

    def test_init_installs_local_scaffold_and_runs_post_install_checks(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        self._init_git_repo(root)

        fake_bin = root / "fake-bin"
        fake_bin.mkdir()
        self._write_fake_trellis(fake_bin)
        self._write_fake_claude(fake_bin)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

        result = self._run_init(root, env, mode="local")

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertTrue((root / ".claude" / "settings.local.json").is_file())
        self.assertEqual((root / ".trellis" / ".developer").read_text(encoding="utf-8").strip(), "alice")
        self.assertTrue((root / ".trellis" / "workspace" / "index.md").is_file())
        self.assertTrue((root / ".trellis" / "workspace" / "alice" / "index.md").is_file())
        self.assertTrue((root / ".trellis" / "workspace" / "alice" / "journal-1.md").is_file())
        self.assertTrue((root / ".trellis" / "config" / "config.json").is_file())
        self.assertTrue((root / ".trellis" / "config" / "workflow_profiles.json").is_file())
        self.assertTrue((root / COMMON_MISTAKES_INSTALLED).is_file())
        self.assertTrue((root / ".trellis" / "scripts" / "validate_agent_results.py").is_file())
        self.assertIn("OVERALL: PASS — Runtime hardening checks passed", result.stdout)
        self.assertIn("superpowers@claude-plugins-official", result.stdout)
        self.assertIn("disabled", result.stdout)
        self.assertIn("oh-my-claudecode@omc", result.stdout)
        self.assertIn("not installed", result.stdout)
        self.assertIn("team-managed files are refreshed on rerun", result.stdout)
        self.assertIn("local personal files are preserved when already present", result.stdout)
        self.assertIn("personalize-local.sh", result.stdout)
        self.assertIn("team-kit managed", result.stdout)
        self.assertIn("Trellis scripts:", result.stdout)
        self.assertFalse((root / ".trellis" / "scripts" / "__pycache__").exists())

    def test_init_supports_remote_mode_via_local_raw_base_override(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        self._init_git_repo(root)

        fake_bin = root / "fake-bin"
        fake_bin.mkdir()
        self._write_fake_trellis(fake_bin)
        self._write_fake_claude(fake_bin)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

        result = self._run_init(root, env, mode="remote")

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertIn("Mode:       remote", result.stdout)
        self.assertTrue((root / ".trellis" / "config" / "config.json").is_file())
        self.assertTrue((root / COMMON_MISTAKES_INSTALLED).is_file())
        self.assertTrue((root / ".trellis" / "workspace" / "alice" / "journal-1.md").is_file())
        self.assertFalse((root / ".trellis" / "scripts" / "__pycache__").exists())

    def test_init_refreshes_existing_team_managed_specs(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        self._init_git_repo(root)

        fake_bin = root / "fake-bin"
        fake_bin.mkdir()
        self._write_fake_trellis(fake_bin)
        self._write_fake_claude(fake_bin)

        stale_spec = root / ".trellis" / "spec" / "guides" / "testing.md"
        stale_spec.parent.mkdir(parents=True)
        stale_spec.write_text("# stale registry copy\n", encoding="utf-8")

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

        result = self._run_init(root, env, mode="local")

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        expected = (
            REPO_ROOT / "marketplace" / "specs" / "web-app" / "guides" / "testing.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(stale_spec.read_text(encoding="utf-8"), expected)
        self.assertIn("refreshed", result.stdout)
        self.assertIn("team-managed spec files", result.stdout)


class SmokeInstallScriptTests(unittest.TestCase):
    def test_smoke_script_help_mentions_supported_modes(self):
        result = subprocess.run(
            ["bash", str(SMOKE_INSTALL), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--mode local|remote|all", result.stdout)
        self.assertIn("simulated-remote", result.stdout)


class FinalizeTaskArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(FINALIZE_TASK_ARCHIVE, "finalize_task_archive_module")

    def test_finalize_archived_task_repairs_context_and_workspace_records(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        archived_task = root / ".trellis" / "tasks" / "archive" / "2026-06" / "demo-task"
        (archived_task / "research").mkdir(parents=True)
        (root / ".trellis" / "spec" / "guides").mkdir(parents=True)
        (root / ".trellis" / "workspace" / "alice").mkdir(parents=True)

        (root / ".trellis" / "spec" / "guides" / "index.md").write_text("# Guides\n", encoding="utf-8")
        (archived_task / "research" / "grill-me.md").write_text("# Grill\n", encoding="utf-8")
        (archived_task / "task.json").write_text(
            json.dumps(
                {
                    "id": "demo-task",
                    "title": "Demo Task",
                    "status": "completed",
                    "creator": "alice",
                    "assignee": "alice",
                    "base_branch": "master",
                    "completedAt": "2026-06-04",
                }
            ),
            encoding="utf-8",
        )
        (archived_task / "prd.md").write_text("# PRD\n\n## Acceptance Criteria\n\n- AC1\n", encoding="utf-8")
        (archived_task / "design.md").write_text("# Design\n", encoding="utf-8")
        (archived_task / "validation").mkdir(parents=True, exist_ok=True)
        (archived_task / "validation" / "check-results.md").write_text(
            textwrap.dedent(
                """\
                ## Build
                - [x] pass

                ## Test
                - [x] pass

                ## Ready for finish-work?
                - [x] yes
                """
            ),
            encoding="utf-8",
        )
        (archived_task / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Task Level

                Selected level:
                - [x] L4 Architecture / Cross-layer Task

                ## Execution Mode Decision

                Recommended mode:
                - [ ] main session
                - [ ] single Trellis subagent
                - [x] Trellis subagents
                - [ ] Trellis-native parallel + worktree
                - [ ] OMC ulw/ultrawork + worktree + parent/child

                Reason:
                - Archived L4 fixture uses strict Trellis-native execution.

                Why not heavier:
                - Parallel execution and OMC are unnecessary for this fixture.

                OMC approval:
                - [x] not applicable
                - [ ] user explicitly approved OMC
                - user message:
                - timestamp:

                ## Review Gate Contract

                - [x] trellis-check
                """
            ),
            encoding="utf-8",
        )
        (archived_task / "finish.md").write_text(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: completed the demo task
                - Evidence: archived validation

                ## Commits

                - abc1234 feat: demo task

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none

                ## Summary

                Completed the demo task with archived evidence.
                """
            ),
            encoding="utf-8",
        )
        (archived_task / "implement.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"_example": "remove me"}),
                    json.dumps({"file": ".trellis/tasks/demo-task/prd.md", "reason": "bad"}),
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (archived_task / "check.jsonl").write_text(
            json.dumps({"file": ".trellis/tasks/demo-task/research/grill-me.md", "reason": "verify"}) + "\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "workspace" / "index.md").write_text(
            textwrap.dedent(
                """\
                # Workspace Index

                ## Active Developers

                | Developer | Last Active | Sessions | Active File |
                |-----------|-------------|----------|-------------|
                | (none yet) | - | - | - |
                """
            ),
            encoding="utf-8",
        )
        (root / ".trellis" / "workspace" / "alice" / "index.md").write_text(
            textwrap.dedent(
                """\
                # Workspace Index - alice

                <!-- @@@auto:current-status -->
                - **Active File**: `journal-1.md`
                - **Total Sessions**: 1
                - **Last Active**: 2026-06-04
                <!-- @@@/auto:current-status -->

                <!-- @@@auto:session-history -->
                | # | Date | Title | Commits | Branch |
                |---|------|-------|---------|--------|
                | 1 | 2026-06-04 | demo-task: old title | - | `master` |
                <!-- @@@/auto:session-history -->
                """
            ),
            encoding="utf-8",
        )
        (root / ".trellis" / "workspace" / "alice" / "journal-1.md").write_text(
            textwrap.dedent(
                """\
                ## Session 1: demo-task

                ### Main Changes

                (Add details)

                ### Git Commits

                (No commits - planning session)

                ### Testing

                - [OK] (Add test results)
                """
            ),
            encoding="utf-8",
        )

        changes = self.module.finalize_archived_task(archived_task, root)

        task_data = json.loads((archived_task / "task.json").read_text(encoding="utf-8"))
        self.assertEqual(task_data["level"], "L4")
        self.assertEqual(task_data["commit"], "abc1234")
        implement_md = (archived_task / "implement.md").read_text(encoding="utf-8")
        self.assertIn("## Implementation Approval", implement_md)
        implement_entries = [json.loads(line) for line in (archived_task / "implement.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(all(entry["file"].startswith((".trellis/spec/", "$TASK_DIR/")) for entry in implement_entries))
        self.assertFalse(any("_example" in entry for entry in implement_entries))
        finish_md = (archived_task / "finish.md").read_text(encoding="utf-8")
        self.assertIn("## Finish Approval", finish_md)
        self.assertIn("## Delivery Sync Check", finish_md)
        dev_index = (root / ".trellis" / "workspace" / "alice" / "index.md").read_text(encoding="utf-8")
        self.assertIn("| 1 | 2026-06-04 | demo-task: Demo Task | 1 | `master` |", dev_index)
        journal = (root / ".trellis" / "workspace" / "alice" / "journal-1.md").read_text(encoding="utf-8")
        self.assertNotIn("(Add details)", journal)
        self.assertNotIn("(No commits - planning session)", journal)
        validate_task_module = load_module(VALIDATE_TASK, "validate_task_module_finalize")
        ok, issues = validate_task_module.validate_task(archived_task)
        self.assertTrue(ok, msg=f"Unexpected archived task issues: {issues}")
        self.assertTrue(changes)

    def test_finalize_archived_task_repairs_legacy_journal_and_missing_indexes(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        archived_task = root / ".trellis" / "tasks" / "archive" / "2026-06" / "legacy-task"
        (archived_task / "research").mkdir(parents=True)
        (root / ".trellis" / "spec" / "guides").mkdir(parents=True)
        legacy_workspace = root / ".trellis" / "workspace" / "alice"
        legacy_workspace.mkdir(parents=True)

        (root / ".trellis" / "spec" / "guides" / "index.md").write_text("# Guides\n", encoding="utf-8")
        (archived_task / "research" / "grill-me.md").write_text("# Grill\n", encoding="utf-8")
        (archived_task / "task.json").write_text(
            json.dumps(
                {
                    "id": "legacy-task",
                    "title": "Legacy Task",
                    "status": "completed",
                    "creator": "alice",
                    "base_branch": "main",
                    "completedAt": "2026-06-04",
                }
            ),
            encoding="utf-8",
        )
        (archived_task / "prd.md").write_text("# PRD\n\n## Acceptance Criteria\n\n- AC1\n", encoding="utf-8")
        (archived_task / "implement.md").write_text(
            textwrap.dedent(
                """\
                # Implement: Example

                ## Task Level

                Selected level:
                - [x] L3 Complex Task

                ## Review Gate Contract

                - [x] trellis-check
                """
            ),
            encoding="utf-8",
        )
        (archived_task / "validation").mkdir(parents=True, exist_ok=True)
        (archived_task / "validation" / "check-results.md").write_text(
            textwrap.dedent(
                """\
                ## Build
                - [x] pass

                ## Test
                - [x] pass

                ## Ready for finish-work?
                - [x] yes
                """
            ),
            encoding="utf-8",
        )
        (archived_task / "finish.md").write_text(
            textwrap.dedent(
                """\
                # Finish: Example

                ## Observable Outcomes

                - Outcome: completed the legacy task
                - Evidence: archived validation

                ## Commits

                - abc1234 feat: legacy task

                ## Spec Update Decision

                - **Need update?**: no
                - **Reason**: none

                ## Summary

                Completed the legacy task with archived evidence.
                """
            ),
            encoding="utf-8",
        )
        (archived_task / "implement.jsonl").write_text(
            json.dumps({"file": "$TASK_DIR/research/grill-me.md", "reason": "context"}) + "\n",
            encoding="utf-8",
        )
        (archived_task / "check.jsonl").write_text(
            json.dumps({"file": "$TASK_DIR/research/grill-me.md", "reason": "verify"}) + "\n",
            encoding="utf-8",
        )
        (legacy_workspace / "journal.md").write_text(
            textwrap.dedent(
                """\
                ## Session 1: legacy-task

                ### Main Changes

                (Add details)

                ### Git Commits

                (No commits - planning session)

                ### Testing

                - [OK] (Add test results)
                """
            ),
            encoding="utf-8",
        )

        changes = self.module.finalize_archived_task(archived_task, root)

        self.assertTrue((root / ".trellis" / "workspace" / "index.md").is_file())
        self.assertTrue((legacy_workspace / "index.md").is_file())
        self.assertTrue((legacy_workspace / "journal-1.md").is_file())
        self.assertFalse((legacy_workspace / "journal.md").exists())
        journal = (legacy_workspace / "journal-1.md").read_text(encoding="utf-8")
        self.assertIn("legacy-task", journal)
        self.assertNotIn("(No commits - planning session)", journal)
        developer_index = (legacy_workspace / "index.md").read_text(encoding="utf-8")
        self.assertIn("| 1 | 2026-06-04 | legacy-task: Legacy Task | 1 | `main` |", developer_index)
        self.assertTrue(changes)


class ValidateReviewGatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(VALIDATE_REVIEW_GATES, "validate_review_gates_module")

    def make_task_dir(self, implement_md: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        task_dir = Path(tmpdir.name) / "T001-demo"
        (task_dir / "review").mkdir(parents=True)
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T001", "level": "L4", "status": "completed"}),
            encoding="utf-8",
        )
        (task_dir / "implement.md").write_text(implement_md, encoding="utf-8")
        for name in ("spec-review.md", "code-review.md", "architecture-review.md"):
            (task_dir / "review" / name).write_text(
                "## Verdict: PASS\n",
                encoding="utf-8",
            )
        return task_dir

    def test_accepts_template_selected_gates_heading(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Implement: Demo

                ## Review Gate Contract

                ### Selected gates for this task

                - [x] trellis-spec-review
                - [x] trellis-code-review
                - [x] trellis-code-architecture-review
                - [ ] trellis-improve-codebase-architecture deep-review
                """
            )
        )

        ok, errors = self.module.validate_review_gates(task_dir)

        self.assertTrue(ok, msg=f"Unexpected gate errors: {errors}")

    def test_unchecked_gate_does_not_satisfy_level_requirement(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Implement: Demo

                ## Review Gate Contract

                ### Selected gates for this task

                - [x] trellis-spec-review
                - [ ] trellis-code-review
                - [x] trellis-code-architecture-review
                """
            )
        )

        ok, errors = self.module.validate_review_gates(task_dir)

        self.assertFalse(ok)
        self.assertTrue(any("trellis-code-review" in err for err in errors))

    def test_accepts_canonical_verdict_section_body(self):
        task_dir = self.make_task_dir(
            textwrap.dedent(
                """\
                # Implement: Demo

                ## Review Gate Contract

                ### Selected gates for this task

                - [x] trellis-spec-review
                - [x] trellis-code-review
                - [x] trellis-code-architecture-review
                """
            )
        )
        (task_dir / "review" / "code-review.md").write_text(
            textwrap.dedent(
                """\
                # Code Quality Review

                ## Verdict

                PASS

                ## Blocking Issues

                - none
                """
            ),
            encoding="utf-8",
        )

        ok, errors = self.module.validate_review_gates(task_dir)

        self.assertTrue(ok, msg=f"Unexpected gate errors: {errors}")


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

    def test_l4_api_contract(self):
        d = self.classify("把用户列表接口返回字段改一下")
        self.assertEqual(d.route, "L4")

    def test_l3_standard_feature(self):
        d = self.classify("新增用户管理 CRUD 功能")
        self.assertEqual(d.route, "L3")

    def test_l4_schema_change(self):
        d = self.classify("给订单表新增 status 字段")
        self.assertEqual(d.route, "L4")

    def test_l5_large_refactor(self):
        d = self.classify("重构整个订单模块，拆成多个子 agent 并行做")
        self.assertEqual(d.route, "L5")

    def test_l5_omc_advanced_path(self):
        d = self.classify("用 OMC ultrawork 并行重构整个订单模块")
        self.assertEqual(d.route, "L5")

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
        self.assertIn("L3", d.scores)
        self.assertIn("L4", d.scores)
        self.assertIn("L5", d.scores)
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
            self.assertIn(d.route, ("L1", "L2", "L3", "L4", "L5", "UNCERTAIN", "L0"))

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
                    "L3": [], "L4": [], "L5": [],
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
                "L3": [], "L4": [], "L5": [],
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
                "L3": [], "L4": [], "L5": [],
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
            "levels": {"L1": [], "L2": [], "L3": [], "L4": [], "L5": []},
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
                "L3": [], "L4": [], "L5": [],
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
                "L3": [], "L4": [], "L5": [],
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
                "L3": [], "L4": [], "L5": [],
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
            "levels": {"L1": [], "L2": [], "L3": [], "L4": [], "L5": []},
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
            "levels": {"L1": [], "L2": [], "L3": [], "L4": [], "L5": []},
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
            "levels": {"L1": [], "L2": [], "L3": [], "L4": [], "L5": []},
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
                "L3": [], "L4": [], "L5": [],
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
                "L3": [], "L4": [], "L5": [],
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
            "levels": {"L1": [], "L2": [], "L3": [], "L4": [], "L5": []},
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
                "L3": [], "L4": [], "L5": [],
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
            "levels": {"L1": [], "L2": [], "L3": [], "L4": [], "L5": []},
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
            "levels": {"L1": [], "L2": [], "L3": [], "L4": [], "L5": []},
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


class WorkflowProfilesConfigTests(unittest.TestCase):
    def test_workflow_profiles_config_exists_and_maps_levels(self):
        path = REPO_ROOT / "trellis" / "config" / "workflow_profiles.json"
        self.assertTrue(path.is_file(), "workflow_profiles.json must exist")

        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("version"), 1)

        profiles = data.get("profiles")
        self.assertIsInstance(profiles, dict)
        expected = {
            "quick": ["L1"],
            "light": ["L2"],
            "standard": ["L3"],
            "strict": ["L4"],
            "orchestrated": ["L5"],
        }
        for name, levels in expected.items():
            with self.subTest(profile=name):
                self.assertIn(name, profiles)
                profile = profiles[name]
                self.assertEqual(profile.get("levels"), levels)
                self.assertIn("execution", profile)
                self.assertIn("required_gates", profile)


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
                    "L3": [], "L4": [], "L5": []
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
                    "L3": [], "L4": [], "L5": []
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
                    "L3": [], "L4": [], "L5": []
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
                    "L3": [], "L4": [], "L5": [],
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
                    "L3": [], "L4": [], "L5": [],
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
                    "L3": [], "L4": [], "L5": [],
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
                    "L3": [], "L4": [], "L5": [],
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
                    "L4": [
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
                    "L3": [], "L4": [], "L5": [],
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
                    "L3": [], "L4": [], "L5": [],
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
                    "L3": [], "L4": [], "L5": [],
                },
                "negative_rules": [],
                "uncertainty": {"min_score": "2", "min_gap": "1"},
            })
            d = self.routing.classify_no_task_prompt("test prompt", root=root)
            self.assertIsInstance(d.route, str)


class SpecTemplateIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module(VALIDATE_SPEC_INDEX, "validate_spec_index_module")

    def test_spec_manifest_matches_marketplace_template(self):
        manifest_entries = [
            line.strip()
            for line in SPEC_MANIFEST.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        template_entries = sorted(
            str(path.relative_to(SPEC_TEMPLATE_ROOT))
            for path in SPEC_TEMPLATE_ROOT.rglob("*.md")
        )
        self.assertEqual(manifest_entries, template_entries)

    def test_marketplace_template_passes_spec_index_validation(self):
        self.assertTrue(self.validator.validate_spec_index(str(SPEC_TEMPLATE_ROOT)))

    def test_common_mistakes_spec_is_installed_indexed_and_mirrored(self):
        marketplace_path = SPEC_TEMPLATE_ROOT / COMMON_MISTAKES_REL
        guides_index = SPEC_TEMPLATE_ROOT / "guides" / "index.md"

        self.assertTrue(marketplace_path.is_file())
        self.assertTrue(COMMON_MISTAKES_TEMPLATE.is_file())
        self.assertEqual(
            marketplace_path.read_text(encoding="utf-8"),
            COMMON_MISTAKES_TEMPLATE.read_text(encoding="utf-8"),
        )
        self.assertIn(
            COMMON_MISTAKES_REL,
            SPEC_MANIFEST.read_text(encoding="utf-8").splitlines(),
        )
        self.assertIn(
            "./ai-behavior/common-mistakes.md",
            guides_index.read_text(encoding="utf-8"),
        )

        content = marketplace_path.read_text(encoding="utf-8")
        for phrase in (
            "routing",
            "scope-manifest.json",
            "runtime/guardrail-overrides.jsonl",
            "agent-results",
            "Replay Lab",
            "doctor workflow",
            "explicit OMC approval",
            "Trellis-native parallel",
            "merge-review",
        ):
            self.assertIn(phrase, content)

    def test_missing_root_index_fails_spec_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_root = Path(tmpdir) / "spec"
            (spec_root / "guides").mkdir(parents=True)
            (spec_root / "guides" / "index.md").write_text("# Guides\n", encoding="utf-8")

            self.assertFalse(self.validator.validate_spec_index(str(spec_root)))


class TrellisConfigValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module(VALIDATE_TRELLIS_CONFIG, "validate_trellis_config_module")

    def test_default_config_passes(self):
        config_path = REPO_ROOT / "trellis" / "config" / "config.json"
        passed, issues = self.validator.validate_config_file(config_path)
        self.assertTrue(passed, msg=f"Default config failed: {issues}")

    def test_missing_dispatch_mode_fails(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            json.dump({"codex": {}}, handle)
            path = Path(handle.name)
        try:
            passed, issues = self.validator.validate_config_file(path)
            self.assertFalse(passed)
            self.assertTrue(any("dispatch_mode" in issue for issue in issues))
        finally:
            path.unlink()


class SpecUpdateCandidateDetectorTests(unittest.TestCase):
    def run_detector(self, *paths: str, cwd: Path = REPO_ROOT) -> dict:
        result = subprocess.run(
            [sys.executable, str(DETECT_SPEC_UPDATE_CANDIDATES), *paths],
            cwd=cwd,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        return json.loads(result.stdout)

    def candidate_targets(self, payload: dict) -> set[str]:
        return {candidate["target"] for candidate in payload["candidates"]}

    def test_detects_phase_four_spec_update_rules_from_cli_args(self):
        paths = [
            "claude/hooks/inject-workflow-state.py",
            "claude/skills/trellis-implement/SKILL.md",
            "trellis/config/routing_rules.json",
            "omc/orchestration.md",
            "tests/fixtures/replay/routing/l1-inline-copy.json",
        ]

        payload = self.run_detector(*paths)

        self.assertTrue(payload["need_spec_update"])
        self.assertEqual(payload["changed_files"], paths)
        self.assertEqual(
            self.candidate_targets(payload),
            {
                "spec/guides/ai-behavior/guardrails.md",
                "spec/guides/ai-behavior/skill-routing.md",
                "workflow/routing.md",
                "spec/guides/ai-behavior/orchestration.md",
                "spec/guides/ai-behavior/common-mistakes.md",
            },
        )
        self.assertTrue(all(candidate["reason"] for candidate in payload["candidates"]))

    def test_detects_agent_and_workflow_documentation_targets(self):
        payload = self.run_detector(
            "claude/agents/trellis-implementer.md",
            "workflow/workflow.md",
        )

        self.assertTrue(payload["need_spec_update"])
        self.assertEqual(
            self.candidate_targets(payload),
            {
                "spec/guides/ai-behavior/agent-results.md",
                "README.md",
            },
        )

    def test_detects_installed_layout_documentation_targets(self):
        payload = self.run_detector(
            ".claude/hooks/inject-workflow-state.py",
            ".claude/skills/trellis-implement/SKILL.md",
            ".trellis/config/routing_rules.json",
            ".trellis/workflow.md",
        )

        self.assertTrue(payload["need_spec_update"])
        self.assertEqual(
            self.candidate_targets(payload),
            {
                "spec/guides/ai-behavior/guardrails.md",
                "spec/guides/ai-behavior/skill-routing.md",
                "workflow/routing.md",
                "README.md",
            },
        )

    def test_detects_runtime_and_installation_documentation_targets(self):
        payload = self.run_detector(
            "trellis/scripts/trellis_doctor.py",
            "trellis/scripts/replay_workflow_cases.py",
            "claude/commands/trellis/doctor.md",
            "bootstrap/init.sh",
            "README.md",
            "docs/verify-workflow.md",
        )

        self.assertTrue(payload["need_spec_update"])
        self.assertEqual(
            self.candidate_targets(payload),
            {
                "docs/verify-workflow.md",
                "README.md",
                "claude/commands/trellis/doctor.md",
                "bootstrap/smoke-test-install.sh",
            },
        )

    def test_no_candidate_when_paths_do_not_match_rules(self):
        payload = self.run_detector("docs/examples/README.md")

        self.assertFalse(payload["need_spec_update"])
        self.assertEqual(payload["candidates"], [])
        self.assertEqual(payload["changed_files"], ["docs/examples/README.md"])

    def test_reads_changed_paths_from_git_diff_when_no_cli_args(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            hook_path = root / "claude" / "hooks" / "demo.py"
            hook_path.parent.mkdir(parents=True)
            hook_path.write_text("print('before')\n", encoding="utf-8")

            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            hook_path.write_text("print('after')\n", encoding="utf-8")

            payload = self.run_detector(cwd=root)

        self.assertTrue(payload["need_spec_update"])
        self.assertEqual(payload["changed_files"], ["claude/hooks/demo.py"])
        self.assertEqual(
            self.candidate_targets(payload),
            {"spec/guides/ai-behavior/guardrails.md"},
        )

    def test_reads_untracked_paths_from_git_when_no_cli_args(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)

            replay_path = root / "tests" / "fixtures" / "replay" / "routing" / "new-case.json"
            replay_path.parent.mkdir(parents=True)
            replay_path.write_text("{}", encoding="utf-8")

            payload = self.run_detector(cwd=root)

        self.assertTrue(payload["need_spec_update"])
        self.assertEqual(
            payload["changed_files"],
            ["tests/fixtures/replay/routing/new-case.json"],
        )
        self.assertEqual(
            self.candidate_targets(payload),
            {"spec/guides/ai-behavior/common-mistakes.md"},
        )


class RuntimeHardeningValidatorTests(unittest.TestCase):
    def test_runtime_hardening_runs_spec_index_validation(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATE_RUNTIME_HARDENING)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertIn("[PASS] validate_spec_index.py", result.stdout)
        self.assertIn("[PASS] validate_trellis_config.py", result.stdout)

    def test_runtime_hardening_runs_phase_two_static_validators(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATE_RUNTIME_HARDENING)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertIn("[PASS] validate_scope_manifest.py", result.stdout)
        self.assertIn("[PASS] validate_guardrail_overrides.py", result.stdout)
        self.assertIn("[PASS] validate_agent_results.py", result.stdout)


class PhaseTwoTemplateTests(unittest.TestCase):
    def test_before_dev_template_includes_scope_manifest_contract(self):
        content = (REPO_ROOT / "trellis" / "task-templates" / "before-dev.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("scope-manifest.json", content)
        self.assertIn("declared_paths", content)
        self.assertIn("declared_globs", content)

    def test_finish_template_includes_guardrail_override_review(self):
        content = (REPO_ROOT / "trellis" / "task-templates" / "finish.md.tmpl").read_text(
            encoding="utf-8"
        )

        self.assertIn("## Guardrail Overrides", content)
        self.assertIn("runtime/guardrail-overrides.jsonl", content)

    def test_before_dev_skill_requires_scope_manifest_output(self):
        content = (REPO_ROOT / "claude" / "skills" / "trellis-before-dev" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("scope-manifest.json", content)
        self.assertIn("declared_paths", content)
        self.assertIn("declared_globs", content)


class PhaseFiveWorkflowContractTests(unittest.TestCase):
    def test_before_dev_check_and_code_review_read_common_mistakes(self):
        paths = [
            REPO_ROOT / "claude" / "skills" / "trellis-before-dev" / "SKILL.md",
            REPO_ROOT / "claude" / "skills" / "trellis-check" / "SKILL.md",
            REPO_ROOT / "claude" / "skills" / "trellis-code-review" / "SKILL.md",
            REPO_ROOT / "claude" / "agents" / "trellis-checker.md",
            REPO_ROOT / "claude" / "agents" / "trellis-code-reviewer.md",
        ]

        for path in paths:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                content = path.read_text(encoding="utf-8")
                self.assertIn(COMMON_MISTAKES_INSTALLED, content)
                self.assertIn("common mistakes", content.lower())

    def test_verify_workflow_covers_phase_five_acceptance_scenarios(self):
        content = (REPO_ROOT / "docs" / "verify-workflow.md").read_text(encoding="utf-8")

        for phrase in (
            "L3/L4/L5",
            "Plan -> Execute -> Check -> Review -> Finish",
            "scope-manifest.json",
            "validate_scope_manifest.py",
            "runtime/guardrail-overrides.jsonl",
            "validate_guardrail_overrides.py",
            "agent-results",
            "validate_agent_results.py",
            "Replay Lab",
            "trellis_doctor.py workflow",
            "doctor workflow",
            "Trellis-native parallel + worktree",
            "explicit OMC approval",
            "merge-review",
        ):
            self.assertIn(phrase, content)

    def test_omc_positioning_is_optional_and_not_default_multi_agent_path(self):
        required = {
            "README.md": ("高级可选", "显式批准", "Trellis 原生"),
            "workflow/routing.md": (
                "Trellis-native parallel + worktree by default",
                "OMC",
                "explicit approval",
            ),
            "workflow/workflow.md": (
                "Trellis native execution comes first",
                "OMC",
                "explicit user approval",
            ),
            "omc/orchestration.md": (
                "Trellis-native parallel + worktree",
                "OMC `ulw/ultrawork`",
                "explicit user approval",
            ),
            "claude/commands/trellis/new.md": (
                "Trellis-native parallel",
                "OMC",
                "explicit approval",
            ),
        }

        for rel, phrases in required.items():
            with self.subTest(path=rel):
                content = (REPO_ROOT / rel).read_text(encoding="utf-8")
                for phrase in phrases:
                    self.assertIn(phrase, content)
                self.assertNotIn("recommend OMC parallel execution", content)

    def test_no_key_doc_describes_omc_as_default_execution(self):
        banned_phrases = (
            "recommend OMC parallel execution",
            "OMC is the default",
            "default to OMC",
            "默认使用 OMC",
            "OMC 默认多 agent",
        )
        paths = [
            "README.md",
            "workflow/routing.md",
            "workflow/workflow.md",
            "omc/orchestration.md",
            "claude/commands/trellis/new.md",
            "docs/verify-workflow.md",
        ]

        for rel in paths:
            with self.subTest(path=rel):
                content = (REPO_ROOT / rel).read_text(encoding="utf-8")
                for phrase in banned_phrases:
                    self.assertNotIn(phrase, content)


class TrellisNotifyTests(unittest.TestCase):
    def run_notify(
        self,
        event: str,
        payload: dict,
        message: str = "需要你的处理",
        reminder_seconds: str = "0",
        max_reminders: str = "5",
    ) -> str:
        env = os.environ.copy()
        env.update(
            {
                "TRELLIS_NOTIFY_DRY_RUN": "1",
                "TRELLIS_NOTIFY_TEST_SYNC": "1",
                "TRELLIS_NOTIFY_REMINDER_SECONDS": reminder_seconds,
                "TRELLIS_NOTIFY_MAX_REMINDERS": max_reminders,
            }
        )
        result = subprocess.run(
            [str(NOTIFY_HOOK), event, "Claude Code", message],
            input=json.dumps(payload),
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout

    def test_notification_ignores_auto_mode_status(self):
        output = self.run_notify(
            "notification",
            {"hook_event_name": "Notification", "message": "Auto mode on"},
        )

        self.assertEqual(output, "")

    def test_notification_ignores_subagent_completion(self):
        output = self.run_notify(
            "notification",
            {"hook_event_name": "Notification", "message": "Subagent completed successfully"},
        )

        self.assertEqual(output, "")

    def test_notification_prompts_for_permission(self):
        output = self.run_notify(
            "notification",
            {"hook_event_name": "Notification", "message": "Permission required: approve git commit?"},
        )

        self.assertIn("notify\tattention", output)
        self.assertIn("Claude Code 正在等你确认", output)

    def test_stop_question_prompts_after_idle(self):
        output = self.run_notify(
            "stop",
            {"hook_event_name": "Stop", "message": "是否允许提交？"},
            "Claude Code 已停下，等你继续",
        )

        self.assertIn("notify\tattention", output)
        self.assertIn("Claude Code 正在等你确认", output)

    def test_stop_plain_end_prompts_after_idle(self):
        output = self.run_notify(
            "stop",
            {"hook_event_name": "Stop", "message": "任务完成了"},
            "Claude Code 已停下，等你继续",
        )

        self.assertIn("notify\tdone", output)
        self.assertIn("Claude Code 已停下，等你继续", output)

    def test_stop_skips_when_user_replies_during_delay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "user", "message": {"content": "开始"}}),
                        json.dumps({"type": "assistant", "message": {"content": "是否允许提交？"}}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            def append_reply() -> None:
                time.sleep(0.2)
                with transcript.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"type": "user", "message": {"content": "允许"}}) + "\n")

            thread = threading.Thread(target=append_reply)
            thread.start()
            try:
                output = self.run_notify(
                    "stop",
                    {"hook_event_name": "Stop", "transcript_path": str(transcript)},
                    "Claude Code 已停下，等你继续",
                    reminder_seconds="1",
                )
            finally:
                thread.join()

        self.assertEqual(output, "")

    def test_stop_uses_reminder_schedule(self):
        output = self.run_notify(
            "stop",
            {"hook_event_name": "Stop", "message": "任务完成了"},
            "Claude Code 已停下，等你继续",
            reminder_seconds="0 0 0 0 0",
        )

        self.assertEqual(output.count("notify\tdone"), 5)

    def test_stop_caps_reminders_at_five(self):
        output = self.run_notify(
            "stop",
            {"hook_event_name": "Stop", "message": "任务完成了"},
            "Claude Code 已停下，等你继续",
            reminder_seconds="0 0 0 0 0 0",
            max_reminders="5",
        )

        self.assertEqual(output.count("notify\tdone"), 5)

    def test_stop_ignores_reminders_after_120_seconds(self):
        output = self.run_notify(
            "stop",
            {"hook_event_name": "Stop", "message": "任务完成了"},
            "Claude Code 已停下，等你继续",
            reminder_seconds="0 0 121",
            max_reminders="5",
        )

        self.assertEqual(output.count("notify\tdone"), 2)

    def test_stop_async_path_uses_desktop_notify_and_stops_after_user_reply(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            notify_log = tmp / "notify.log"
            fake_notify = bin_dir / "notify-send"
            fake_notify.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    printf '%s\\t%s\\n' "$1" "$2" >> "$TRELLIS_FAKE_NOTIFY_LOG"
                    """
                ),
                encoding="utf-8",
            )
            fake_notify.chmod(0o755)

            transcript = tmp / "transcript.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "user", "message": {"content": "开始"}}),
                        json.dumps({"type": "assistant", "message": {"content": "是否允许提交？"}}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}:{env.get('PATH', '')}",
                    "TRELLIS_FAKE_NOTIFY_LOG": str(notify_log),
                    "TRELLIS_NOTIFY_SOUND": "0",
                    "TRELLIS_NOTIFY_REMINDER_SECONDS": "1 2",
                    "TRELLIS_NOTIFY_MAX_REMINDERS": "5",
                }
            )
            subprocess.run(
                [str(NOTIFY_HOOK), "stop", "Claude Code", "Claude Code 已停下，等你继续"],
                input=json.dumps({"hook_event_name": "Stop", "transcript_path": str(transcript)}),
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            time.sleep(1.2)
            lines = notify_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertIn("Claude Code 正在等你确认", lines[0])

            with transcript.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"type": "user", "message": {"content": "允许"}}) + "\n")

            time.sleep(1.2)
            lines = notify_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()
