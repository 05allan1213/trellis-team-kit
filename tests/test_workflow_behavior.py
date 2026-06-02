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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
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


if __name__ == "__main__":
    unittest.main()
