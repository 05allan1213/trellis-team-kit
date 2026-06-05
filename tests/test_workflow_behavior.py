import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INJECT_HOOK = REPO_ROOT / "claude" / "hooks" / "inject-workflow-state.py"
PROTECT_HOOK = REPO_ROOT / "claude" / "hooks" / "protect-dangerous-actions.py"
STOP_GUARD_HOOK = REPO_ROOT / "claude" / "hooks" / "stop-guard.py"
VALIDATE_TASK = REPO_ROOT / "trellis" / "scripts" / "validate_task.py"
VALIDATE_REVIEW_GATES = REPO_ROOT / "trellis" / "scripts" / "validate_review_gates.py"
VALIDATE_WORKFLOW_STATE = REPO_ROOT / "trellis" / "scripts" / "validate_workflow_state.py"
VALIDATE_DELIVERY_SYNC = REPO_ROOT / "trellis" / "scripts" / "validate_delivery_sync.py"
VALIDATE_RUNTIME_HARDENING = REPO_ROOT / "trellis" / "scripts" / "validate_runtime_hardening.py"
VALIDATE_TRELLIS_CONFIG = REPO_ROOT / "trellis" / "scripts" / "validate_trellis_config.py"
VALIDATE_SPEC_INDEX = REPO_ROOT / "trellis" / "scripts" / "validate_spec_index.py"
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
        self.assertIn("minimal implement.md", context)

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
        for src in (VALIDATE_TASK, VALIDATE_REVIEW_GATES, VALIDATE_DELIVERY_SYNC):
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
        self.assertTrue((root / ".trellis" / "workspace" / "alice" / "journal-1.md").is_file())
        self.assertFalse((root / ".trellis" / "scripts" / "__pycache__").exists())


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


if __name__ == "__main__":
    unittest.main()
