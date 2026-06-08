import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRELLIS_DOCTOR = REPO_ROOT / "trellis" / "scripts" / "trellis_doctor.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WorkflowDoctorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(TRELLIS_DOCTOR, "trellis_doctor_module")

    def make_repo(self) -> tuple[Path, Path]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        root = Path(tmpdir.name)
        task_dir = root / ".trellis" / "tasks" / "T004-workflow-doctor"
        (task_dir / "research").mkdir(parents=True)
        (root / ".trellis" / "active-task").write_text(
            ".trellis/tasks/T004-workflow-doctor",
            encoding="utf-8",
        )
        return root, task_dir

    def write_base_task(self, task_dir: Path, *, level: str, status: str) -> None:
        (task_dir / "task.json").write_text(
            json.dumps({"id": "T004", "title": "Workflow Doctor", "level": level, "status": status}),
            encoding="utf-8",
        )
        (task_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
        (task_dir / "research" / "grill-me.md").write_text("# Grill\n", encoding="utf-8")
        (task_dir / "design.md").write_text("# Design\n", encoding="utf-8")
        (task_dir / "implement.jsonl").write_text(
            json.dumps({"file": ".trellis/spec/index.md", "reason": "spec"}) + "\n",
            encoding="utf-8",
        )
        (task_dir / "check.jsonl").write_text(
            json.dumps({"file": ".trellis/spec/index.md", "reason": "spec"}) + "\n",
            encoding="utf-8",
        )

    def write_implement(self, task_dir: Path, *, mode_line: str, approval_line: str, merge_review: bool) -> None:
        merge_line = "- [x] trellis-merge-review" if merge_review else "- [ ] trellis-merge-review"
        (task_dir / "implement.md").write_text(
            textwrap.dedent(
                f"""\
                # Implement

                ## Execution Mode Decision

                Recommended mode:
                - [ ] main session
                - [ ] single Trellis subagent
                - [ ] Trellis subagents
                {mode_line}

                OMC approval:
                - [x] not applicable
                {approval_line}

                ## Review Gate Contract

                - [x] trellis-check
                - [x] trellis-spec-review
                - [x] trellis-code-review
                - [x] trellis-code-architecture-review
                - [x] trellis-improve-codebase-architecture deep-review
                {merge_line}
                """
            ),
            encoding="utf-8",
        )

    def test_workflow_doctor_reports_phase_mismatch_and_missing_scope_manifest(self):
        root, task_dir = self.make_repo()
        self.write_base_task(task_dir, level="L4", status="planning")
        self.write_implement(
            task_dir,
            mode_line="- [x] main session",
            approval_line="- [ ] user explicitly approved OMC",
            merge_review=False,
        )
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: api\n- Files likely touched: src/api\n",
            encoding="utf-8",
        )

        ok, report = self.module.diagnose_workflow(root, task_dir)

        self.assertFalse(ok)
        self.assertIn("Trellis Workflow Doctor", report)
        self.assertIn("phase mismatch", report)
        self.assertIn("missing scope-manifest.json", report)
        self.assertIn("To fix:", report)

    def test_workflow_doctor_reports_omc_without_approval_and_missing_merge_review(self):
        root, task_dir = self.make_repo()
        self.write_base_task(task_dir, level="L5", status="in_progress")
        self.write_implement(
            task_dir,
            mode_line="- [x] OMC ulw/ultrawork + worktree + parent/child",
            approval_line="- [ ] user explicitly approved OMC",
            merge_review=False,
        )
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
                    "declared_globs": [],
                    "high_risk_allowed": False,
                    "out_of_scope": [],
                }
            ),
            encoding="utf-8",
        )

        ok, report = self.module.diagnose_workflow(root, task_dir)

        self.assertFalse(ok)
        self.assertIn("OMC execution requires explicit user approval", report)
        self.assertIn("parallel or OMC execution requires trellis-merge-review", report)

    def test_workflow_doctor_reports_explicit_phase_status_mismatch(self):
        root, task_dir = self.make_repo()
        self.write_base_task(task_dir, level="L4", status="PLANNING_PRD")
        self.write_implement(
            task_dir,
            mode_line="- [x] main session",
            approval_line="- [ ] user explicitly approved OMC",
            merge_review=False,
        )

        ok, report = self.module.diagnose_workflow(root, task_dir)

        self.assertFalse(ok)
        self.assertIn("phase mismatch", report)
        self.assertIn("expected PLANNING_PRD", report)
        self.assertIn("inferred WAITING_IMPLEMENTATION_APPROVAL", report)

    def test_workflow_doctor_reports_l4_omc_missing_merge_review(self):
        root, task_dir = self.make_repo()
        self.write_base_task(task_dir, level="L4", status="in_progress")
        self.write_implement(
            task_dir,
            mode_line="- [x] OMC ulw/ultrawork + worktree + parent/child",
            approval_line="- [x] user explicitly approved OMC",
            merge_review=False,
        )
        (task_dir / "before-dev.md").write_text(
            "# Before Dev\n- Scope: orders\n- Files likely touched: src/orders\n",
            encoding="utf-8",
        )
        (task_dir / "scope-manifest.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "level": "L4",
                    "profile": "strict",
                    "declared_paths": ["src/orders"],
                    "declared_globs": [],
                    "high_risk_allowed": False,
                    "out_of_scope": [],
                }
            ),
            encoding="utf-8",
        )

        ok, report = self.module.diagnose_workflow(root, task_dir)

        self.assertFalse(ok)
        self.assertIn("parallel or OMC execution requires trellis-merge-review", report)

    def test_cli_distinguishes_setup_and_workflow_modes(self):
        root, task_dir = self.make_repo()
        self.write_base_task(task_dir, level="L2", status="in_progress")
        self.write_implement(
            task_dir,
            mode_line="- [x] main session",
            approval_line="- [ ] user explicitly approved OMC",
            merge_review=False,
        )

        result = subprocess.run(
            [sys.executable, str(TRELLIS_DOCTOR), "workflow", str(task_dir)],
            cwd=root,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("Trellis Workflow Doctor", result.stdout)

        setup_result = subprocess.run(
            [sys.executable, str(TRELLIS_DOCTOR), "setup", "--dry-run"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(setup_result.returncode, 0, msg=setup_result.stderr)
        self.assertIn("Trellis Setup Doctor", setup_result.stdout)

    def test_setup_doctor_fails_when_phase_four_scripts_are_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scripts_dir = root / ".trellis" / "scripts"
            scripts_dir.mkdir(parents=True)
            for name in (
                "validate_task.py",
                "validate_review_gates.py",
                "validate_runtime_hardening.py",
                "validate_scope_manifest.py",
                "validate_guardrail_overrides.py",
                "validate_agent_results.py",
                "trellis_doctor.py",
            ):
                (scripts_dir / name).write_text("# placeholder\n", encoding="utf-8")

            ok, report = self.module.diagnose_setup(root)

        self.assertFalse(ok)
        self.assertIn("Scripts:", report)
        self.assertIn("replay_workflow_cases.py", report)
        self.assertIn("detect_spec_update_candidates.py", report)
        self.assertIn("Overall: FAIL", report)

    def test_setup_doctor_checks_installation_health_beyond_scripts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scripts_dir = root / ".trellis" / "scripts"
            scripts_dir.mkdir(parents=True)
            for name in (
                "validate_task.py",
                "validate_review_gates.py",
                "validate_runtime_hardening.py",
                "validate_scope_manifest.py",
                "validate_guardrail_overrides.py",
                "validate_agent_results.py",
                "replay_workflow_cases.py",
                "detect_spec_update_candidates.py",
                "trellis_doctor.py",
            ):
                (scripts_dir / name).write_text("# placeholder\n", encoding="utf-8")

            ok, report = self.module.diagnose_setup(root)

        self.assertFalse(ok)
        self.assertIn("Hooks:", report)
        self.assertIn("Skills:", report)
        self.assertIn("Task templates:", report)
        self.assertIn("Config:", report)
        self.assertIn("Overall: FAIL", report)


if __name__ == "__main__":
    unittest.main()
