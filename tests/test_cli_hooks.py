import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from deeporbit.cli import main
from deeporbit.config import load_config
from deeporbit.links import add_link, set_default
from deeporbit.profile import set_field
from deeporbit.semantic import chunk_markdown
from deeporbit.vault import initialize

ROOT = Path(__file__).resolve().parents[1]


class CliHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(Path(self.temp.name) / "config")})
        self.env.start()
        self.vault = Path(self.temp.name)
        initialize(self.vault)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_cli_outputs_json(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--vault", str(self.vault), "doctor"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["vault"], str(self.vault))
        self.assertIn("links", payload)
        self.assertEqual(payload["links"]["count"], 0)
        self.assertIsNone(payload["links"]["default"])
    def _run_hook(
        self,
        runtime: str,
        event: str = "session-start",
        payload: dict | None = None,
        include_vault_env: bool = True,
        cwd: Path | None = None,
    ) -> str:
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        if include_vault_env:
            env["DEEPORBIT_VAULT"] = str(self.vault)
        else:
            env["DEEPORBIT_VAULT"] = ""
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "hooks" / "deeporbit_hook.py"), "--runtime", runtime, "--event", event],
            input=json.dumps(payload or {}),
            text=True,
            capture_output=True,
            env=env,
            cwd=str(cwd or ROOT),
            check=True,
        )
        return result.stdout

    def _git(self, *args: str, cwd: Path | None = None) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd or self.vault),
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def test_hook_file_change_summary_shape(self):
        baseline = self.vault / "00_Inbox" / "baseline.md"
        baseline.write_text("before\n", encoding="utf-8")
        self._run_hook("codex", "session-start")
        baseline.write_text("after\n", encoding="utf-8")
        created = self.vault / "00_Inbox" / "new-note.pdf"
        created.write_bytes(b"%PDF-1.4\n% DeepOrbit test PDF\n")
        payload = json.loads(self._run_hook("codex", "file-change"))
        hook_output = payload["hookSpecificOutput"]
        self.assertEqual(hook_output["hookEventName"], "PostToolUse")
        context = hook_output["additionalContext"]
        self.assertIn(f"[{self.vault.name}]", context)
        self.assertIn("[created]", context)
        self.assertIn("[modified]", context)
        self.assertIn("baseline.md", context)
        self.assertIn("new-note.pdf", context)

    def test_hook_file_change_triggers_git_sync(self):
        remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, text=True, capture_output=True)
        self._git("init")
        self._git("config", "user.name", "DeepOrbit Test")
        self._git("config", "user.email", "deeporbit@example.com")
        self._git("remote", "add", "origin", str(remote))
        note = self.vault / "00_Inbox" / "sync.md"
        note.write_text("before\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-m", "initial")
        self._run_hook("codex", "session-start", {"cwd": str(self.vault)})
        note.write_text("after\n", encoding="utf-8")
        self._run_hook("codex", "file-change", {"cwd": str(self.vault)})
        branch = self._git("branch", "--show-current")
        local_head = self._git("rev-parse", "HEAD")
        remote_head = subprocess.run(
            ["git", "ls-remote", "origin", f"refs/heads/{branch}"],
            cwd=str(self.vault),
            text=True,
            capture_output=True,
            check=True,
        ).stdout.split()[0]
        self.assertEqual(remote_head, local_head)
        self.assertIn("DeepOrbit sync", self._git("log", "-1", "--pretty=%s"))

    def test_hook_gemini_context_shape(self):
        payload = json.loads(self._run_hook("gemini"))
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("additionalContext", payload["hookSpecificOutput"])
        self.assertIn("# DeepOrbit Agent Context", context)

    def test_hook_codex_context_shape(self):
        payload = json.loads(self._run_hook("codex"))
        hook_output = payload["hookSpecificOutput"]
        self.assertEqual(hook_output["hookEventName"], "SessionStart")
        self.assertIn("additionalContext", hook_output)
        self.assertIn("DeepOrbit vault", hook_output["additionalContext"])
        self.assertIn("# DeepOrbit Agent Context", hook_output["additionalContext"])

    def test_hook_uses_default_link_when_not_in_vault(self):
        other_vault = Path(self.temp.name) / "linked-vault"
        initialize(other_vault)
        set_field(load_config(other_vault), "hook_marker", "linked-vault")
        add_link("linked", other_vault)
        set_default("linked")
        outside = Path(tempfile.mkdtemp()) / "elsewhere"
        outside.mkdir()
        payload = json.loads(
            self._run_hook(
                "codex",
                payload={"cwd": str(outside)},
                include_vault_env=False,
                cwd=outside,
            )
        )
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("DeepOrbit vault", context)
        self.assertIn("hook_marker=linked-vault", context)






    def test_hook_claude_runtime_shape(self):
        context = self._run_hook("claude")
        self.assertIn("# DeepOrbit Agent Context", context)
        self.assertIn("DeepOrbit vault", context)
        self.assertNotIn('"context"', context)

    def test_hook_omp_runtime_shape(self):
        payload = json.loads(self._run_hook("omp"))
        self.assertIn("context", payload)
        self.assertIn("# DeepOrbit Agent Context", payload["context"])
        self.assertIn("DeepOrbit vault", payload["context"])

    def test_long_paragraph_is_split(self):
        chunks = chunk_markdown("x" * 3500, max_chars=1000)
        self.assertEqual([len(chunk) for chunk in chunks], [1000, 1000, 1000, 500])


if __name__ == "__main__":
    unittest.main()
