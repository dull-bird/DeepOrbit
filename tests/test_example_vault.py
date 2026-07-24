"""End-to-end tests against the checked-in example vault.

Copies examples/example-vault into a temp dir (tests must never mutate the
checked-in copy) and exercises the CLI surface a new user would touch:
status, todo lifecycle, agenda, suggest, teach-me export, agent config.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deeporbit.cli import main
from deeporbit.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_VAULT = REPO_ROOT / "examples" / "example-vault"

FAKE_TEACH_ME = """#!/usr/bin/env python3
import json
print(json.dumps({
    "import_id": "import-test",
    "status": "ok",
    "origin": {"kind": "import", "source_type": "obsidian",
               "source_path": "staging", "vault_name": "x", "import_id": "import-test"},
    "prompt_for_ai": "staging",
}))
"""


def run_cli(*argv: str) -> tuple[int, object]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(list(argv))
    text = buf.getvalue().strip()
    try:
        return code, json.loads(text) if text else None
    except json.JSONDecodeError:
        return code, text


class ExampleVaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp.name) / "example-vault"
        shutil.copytree(EXAMPLE_VAULT, self.vault)
        self.addCleanup(self.temp.cleanup)

    def cli(self, *argv: str) -> tuple[int, object]:
        return run_cli("--vault", str(self.vault), *argv)

    def test_config_loads(self) -> None:
        config = load_config(self.vault)
        self.assertEqual(config.vault_id, "example-vault")
        self.assertIn("60_Notes/微信读书", config.readonly_dirs)
        self.assertEqual(config.agent.get("name"), "omp")

    def test_status_lists_work_items(self) -> None:
        code, data = self.cli("status")
        self.assertEqual(code, 0)
        paths = {item["path"] for item in data["items"]}
        self.assertIn("20_Projects/学习Rust/学习Rust.md", paths)
        self.assertIn("30_Research/向量数据库调研.md", paths)
        # The readonly weread book is marked, not treated as lifecycle work.
        readonly = [item for item in data["items"] if item["path"].startswith("60_Notes/微信读书")]
        self.assertTrue(all(item.get("readonly") for item in readonly))

    def test_todo_add_list_done_roundtrip(self) -> None:
        code, added = self.cli("todo", "add", "写 example vault 的文档", "--today")
        self.assertEqual(code, 0)
        task_id = added["id"]
        code, tasks = self.cli("todo", "list")
        self.assertTrue(any(t["id"] == task_id for t in tasks))
        code, done = self.cli("todo", "done", task_id)
        self.assertEqual(code, 0)
        self.assertTrue(done["done"])

    def test_agenda_buckets(self) -> None:
        code, data = self.cli("agenda")
        self.assertEqual(code, 0)
        self.assertIn("unscheduled", data)
        self.assertIn("upcoming", data)

    def test_suggest_runs(self) -> None:
        code, data = self.cli("suggest")
        self.assertEqual(code, 0)
        self.assertIsInstance(data, list)

    def test_lifecycle_pause_resume(self) -> None:
        path = "30_Research/向量数据库调研.md"
        code, data = self.cli("pause", path)
        self.assertEqual((code, data["status"]), (0, "paused"))
        code, data = self.cli("resume", path)
        self.assertEqual((code, data["status"]), (0, "active"))

    def test_lifecycle_refuses_readonly_zone(self) -> None:
        code, data = self.cli("done", "60_Notes/微信读书/示例书：卡片笔记写作法.md")
        self.assertEqual(code, 1)

    def test_teach_me_export(self) -> None:
        script = Path(self.temp.name) / "teach_me.py"
        script.write_text(FAKE_TEACH_ME, encoding="utf-8")
        code, data = self.cli("teach-me", "export", "--script", str(script))
        self.assertEqual(code, 0)
        # Default dirs: 40_Wiki + 30_Research (+60_Notes root); readonly skipped.
        self.assertEqual(data["deeporbit"]["exported_notes"], 3)
        self.assertEqual(data["origin"]["source_path"], str(self.vault))

    def test_agent_status_and_configure(self) -> None:
        code, data = self.cli("agent", "status")
        self.assertEqual(code, 0)
        self.assertTrue(data["configured"])
        self.assertEqual(data["name"], "omp")
        # Reconfigure with an installed fake binary.
        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            code, data = self.cli("agent", "configure", "codex")
        self.assertEqual(code, 0)
        self.assertEqual(data["saved"]["mode"], "print")
        code, data = self.cli("agent", "clear")
        self.assertEqual(data["saved"], {})

    def test_index_and_rag(self) -> None:
        code, _ = self.cli("index")
        self.assertEqual(code, 0)
        code, hits = self.cli("rag", "所有权")
        self.assertEqual(code, 0)
        self.assertTrue(any("学习Rust" in hit["path"] for hit in hits))


if __name__ == "__main__":
    unittest.main()
