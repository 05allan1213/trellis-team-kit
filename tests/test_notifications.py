import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = REPO_ROOT / "claude" / "settings.json"
NOTIFY_SCRIPT = REPO_ROOT / "claude" / "hooks" / "trellis-notify.sh"


class ClaudeSettingsNotificationTests(unittest.TestCase):
    def test_notification_hook_only_matches_user_action_prompts(self):
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))

        entries = data["hooks"]["Notification"]

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["matcher"], "permission_prompt|elicitation_dialog")


class TrellisNotifyScriptTests(unittest.TestCase):
    def make_fake_bin(self, root: Path, log_path: Path, sound_log_path: Path) -> Path:
        fake_bin = root / "fake-bin"
        fake_bin.mkdir()

        (fake_bin / "uname").write_text(
            "#!/usr/bin/env bash\n"
            "printf 'Linux\\n'\n",
            encoding="utf-8",
        )
        (fake_bin / "notify-send").write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s|%s\\n' \"$1\" \"$2\" >> \"$LOG_FILE\"\n",
            encoding="utf-8",
        )
        (fake_bin / "canberra-gtk-play").write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$2\" >> \"$SOUND_LOG_FILE\"\n",
            encoding="utf-8",
        )
        (fake_bin / "paplay").write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$1\" >> \"$SOUND_LOG_FILE\"\n",
            encoding="utf-8",
        )

        os.chmod(fake_bin / "uname", 0o755)
        os.chmod(fake_bin / "notify-send", 0o755)
        os.chmod(fake_bin / "canberra-gtk-play", 0o755)
        os.chmod(fake_bin / "paplay", 0o755)
        return fake_bin

    def make_runtime(self, project_root: Path | None = None) -> dict[str, object]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        temp_root = Path(tmpdir.name)
        project_dir = project_root or (temp_root / "demo-project")
        project_dir.mkdir(parents=True, exist_ok=True)
        log_path = temp_root / "notify.log"
        sound_log_path = temp_root / "sound.log"
        fake_bin = self.make_fake_bin(temp_root, log_path, sound_log_path)

        env = os.environ.copy()
        env.update(
            {
                "CLAUDE_PROJECT_DIR": str(project_dir),
                "LOG_FILE": str(log_path),
                "SOUND_LOG_FILE": str(sound_log_path),
                "PATH": f"{fake_bin}{os.pathsep}{env.get('PATH', '')}",
                "TRELLIS_NOTIFY": "1",
                "TRELLIS_NOTIFY_SOUND": "0",
                "TRELLIS_NOTIFY_DESKTOP": "1",
            }
        )

        return {
            "project_dir": project_dir,
            "log_path": log_path,
            "sound_log_path": sound_log_path,
            "env": env,
        }

    def run_notify_in_runtime(
        self,
        runtime: dict[str, object],
        *,
        event: str,
        hook_input: dict,
        extra_env: dict[str, str] | None = None,
        message: str = "需要你的处理",
    ) -> tuple[str, str]:
        env = dict(runtime["env"])
        if extra_env:
            env.update(extra_env)

        log_path = runtime["log_path"]
        sound_log_path = runtime["sound_log_path"]

        before_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        before_sound = sound_log_path.read_text(encoding="utf-8") if sound_log_path.exists() else ""

        subprocess.run(
            ["bash", str(NOTIFY_SCRIPT), event, "Claude Code", message],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
            check=True,
            env=env,
        )

        for _ in range(10):
            if sound_log_path.exists() and sound_log_path.read_text(encoding="utf-8"):
                break
            time.sleep(0.02)

        after_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        after_sound = sound_log_path.read_text(encoding="utf-8") if sound_log_path.exists() else ""
        return after_log[len(before_log):], after_sound[len(before_sound):]

    def run_notify(
        self,
        *,
        event: str,
        hook_input: dict,
        extra_env: dict[str, str] | None = None,
        project_root: Path | None = None,
        message: str = "需要你的处理",
    ) -> tuple[str, str]:
        runtime = self.make_runtime(project_root)
        return self.run_notify_in_runtime(
            runtime,
            event=event,
            hook_input=hook_input,
            extra_env=extra_env,
            message=message,
        )

    def test_done_notification_is_suppressed_in_auto_mode(self):
        output, _ = self.run_notify(
            event="done",
            hook_input={"permission_mode": "auto", "message": "任务已完成，可以回来看结果"},
            message="本轮已完成，等你继续",
        )

        self.assertEqual(output, "")

    def test_done_notification_is_suppressed_when_omc_mode_is_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "demo-project"
            state_dir = project_dir / ".omc" / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "autopilot-state.json").write_text(
                json.dumps({"active": True}),
                encoding="utf-8",
            )

            output, _ = self.run_notify(
                event="done",
                hook_input={"permission_mode": "default", "message": "任务已完成，可以回来看结果"},
                project_root=project_dir,
                message="本轮已完成，等你继续",
            )

        self.assertEqual(output, "")

    def test_done_notification_is_suppressed_without_completion_intent(self):
        output, _ = self.run_notify(
            event="done",
            hook_input={"permission_mode": "default", "message": "我继续排查，还没结束"},
            message="本轮已完成，等你继续",
        )

        self.assertEqual(output, "")

    def test_done_notification_fires_once_when_assistant_claims_completion(self):
        runtime = self.make_runtime()

        first_output, _ = self.run_notify_in_runtime(
            runtime,
            event="done",
            hook_input={"permission_mode": "default", "message": "修改已完成，测试通过，可以回来看结果"},
            message="本轮已完成，等你继续",
        )
        second_output, _ = self.run_notify_in_runtime(
            runtime,
            event="done",
            hook_input={"permission_mode": "default", "message": "修改已完成，测试通过，可以回来看结果"},
            message="本轮已完成，等你继续",
        )

        self.assertIn("Claude Code · demo-project|主任务已完成，可回来看结果", first_output)
        self.assertEqual(second_output, "")

    def test_done_notification_can_be_reenabled_in_auto_mode(self):
        output, _ = self.run_notify(
            event="done",
            hook_input={"permission_mode": "auto", "message": "任务已完成，可以回来看结果"},
            extra_env={"TRELLIS_NOTIFY_IN_AUTO": "1"},
            message="本轮已完成，等你继续",
        )

        self.assertIn("Claude Code · demo-project|主任务已完成，可回来看结果", output)

    def test_attention_notification_uses_action_required_copy_and_sound(self):
        output, sound = self.run_notify(
            event="attention",
            hook_input={"notification_type": "permission_prompt", "tool_name": "Bash"},
            extra_env={"TRELLIS_NOTIFY_SOUND": "1"},
            message="需要你的处理",
        )

        self.assertIn("Claude Code · demo-project|需要授权执行 Bash", output)
        self.assertTrue(sound.strip())

    def test_duplicate_action_required_notification_is_suppressed(self):
        runtime = self.make_runtime()

        first_output, _ = self.run_notify_in_runtime(
            runtime,
            event="attention",
            hook_input={"notification_type": "permission_prompt", "tool_name": "Bash"},
            message="需要你的处理",
        )
        second_output, _ = self.run_notify_in_runtime(
            runtime,
            event="attention",
            hook_input={"notification_type": "permission_prompt", "tool_name": "Bash"},
            message="需要你的处理",
        )

        self.assertIn("需要授权执行 Bash", first_output)
        self.assertEqual(second_output, "")

    def test_idle_prompt_stays_suppressed(self):
        output, _ = self.run_notify(
            event="attention",
            hook_input={"notification_type": "idle_prompt"},
            message="需要你的处理",
        )

        self.assertEqual(output, "")

    def test_blocked_notification_requires_repeated_same_reason(self):
        runtime = self.make_runtime()

        first_output, _ = self.run_notify_in_runtime(
            runtime,
            event="done",
            hook_input={"permission_mode": "default", "message": "我无法继续，需要你提供 API key"},
            message="本轮已完成，等你继续",
        )
        second_output, _ = self.run_notify_in_runtime(
            runtime,
            event="done",
            hook_input={"permission_mode": "default", "message": "我无法继续，需要你提供 API key"},
            message="本轮已完成，等你继续",
        )
        third_output, _ = self.run_notify_in_runtime(
            runtime,
            event="done",
            hook_input={"permission_mode": "default", "message": "我无法继续，需要你提供 API key"},
            message="本轮已完成，等你继续",
        )

        self.assertEqual(first_output, "")
        self.assertEqual(second_output, "")
        self.assertIn("Claude Code · demo-project|连续失败 3 次", third_output)


if __name__ == "__main__":
    unittest.main()
