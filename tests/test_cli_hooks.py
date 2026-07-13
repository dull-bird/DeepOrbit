import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from deeporbit.cli import main
from deeporbit.semantic import chunk_markdown
from deeporbit.vault import initialize

ROOT = Path(__file__).resolve().parents[1]


class CliHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp.name)
        initialize(self.vault)

    def tearDown(self):
        self.temp.cleanup()

    def test_cli_outputs_json(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--vault", str(self.vault), "doctor"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["vault"], str(self.vault))

    def test_hook_gemini_context_shape(self):
        env = {**os.environ, "DEEPORBIT_VAULT": str(self.vault), "PYTHONPATH": str(ROOT / "src")}
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "hooks" / "deeporbit_hook.py"), "--runtime", "gemini", "--event", "session-start"],
            input="{}",
            text=True,
            capture_output=True,
            env=env,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertIn("additionalContext", payload["hookSpecificOutput"])

    def test_long_paragraph_is_split(self):
        chunks = chunk_markdown("x" * 3500, max_chars=1000)
        self.assertEqual([len(chunk) for chunk in chunks], [1000, 1000, 1000, 500])


if __name__ == "__main__":
    unittest.main()
