"""Triage classification, managed-block prompt sync, and the no-API-key guard."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from deeporbit.cli import main
from deeporbit.config import load_config
from deeporbit.sync import authored_by_deeporbit, sync_block, sync_file
from deeporbit.triage import classify, triage
from deeporbit.vault import initialize


class TriageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        initialize(self.root)
        self.config = load_config(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, rel: str, content: str = "x") -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_note_goes_to_inbox(self):
        target = self._write("粗糙想法.md", "# 想法\n一些记录\n")
        self.assertEqual(classify(self.config, target)["action"], "inbox")

    def test_status_note_flagged_as_work_item(self):
        target = self._write("项目草稿.md", "---\nstatus: active\n---\n# P\n")
        result = classify(self.config, target)
        self.assertEqual(result["action"], "inbox")
        self.assertIn("status", result["reason"])

    def test_obsidian_welcome_is_trash(self):
        target = self._write("欢迎.md", "这是你的新*仓库*。\n\n写点笔记。\n")
        self.assertEqual(classify(self.config, target)["action"], "trash")

    def test_code_goes_out_of_vault(self):
        self.assertEqual(classify(self.config, self._write("analyze.py"))["action"], "out-of-vault")
        self.assertEqual(classify(self.config, self._write("paper.tex"))["action"], "out-of-vault")

    def test_env_secret_goes_out_of_vault(self):
        target = self._write(".env.production", "SUPERMEMORY_API_KEY=abc123\n")
        result = classify(self.config, target)
        self.assertEqual(result["action"], "out-of-vault")
        self.assertIn("密钥", result["reason"])

    def test_junk_extensions_are_trash(self):
        self.assertEqual(classify(self.config, self._write("texput.log"))["action"], "trash")
        self.assertEqual(classify(self.config, self._write("de421.bsp"))["action"], "trash")

    def test_media_goes_to_resources(self):
        self.assertEqual(classify(self.config, self._write("recording.m4a"))["action"], "resources")

    def test_empty_dir_is_trash(self):
        (self.root / "emptydir").mkdir()
        self.assertEqual(classify(self.config, self.root / "emptydir")["action"], "trash")

    def test_duplicate_skill_pack_is_trash(self):
        pack = self.root / "skills" / "do.demo"
        pack.mkdir(parents=True)
        (pack / "SKILL.md").write_text("---\nname: do.demo\n---\n", encoding="utf-8")
        self.assertEqual(classify(self.config, self.root / "skills")["action"], "trash")

    def test_dated_agent_logs_leave_vault(self):
        logs = self.root / "memory"
        logs.mkdir()
        for day in ("2026-07-01", "2026-07-02", "2026-07-03"):
            (logs / f"{day}.md").write_text("# log\n", encoding="utf-8")
        self.assertEqual(classify(self.config, logs)["action"], "out-of-vault")

    def test_skeleton_content_kept(self):
        target = self._write("00_Inbox/Todos.md", "# Todos\n")
        self.assertEqual(classify(self.config, target)["action"], "keep")

    def test_default_triage_scans_only_strays(self):
        self._write("stray.md", "# stray\n")
        paths = [item["path"] for item in triage(self.config)]
        self.assertIn("stray.md", paths)
        self.assertNotIn("deeporbit.json", paths)


class SyncProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_block_insert_then_replace(self):
        text, action = sync_block("# user content\n", "intent-routing", "v1 body")
        self.assertEqual(action, "appended-block")
        self.assertIn("v1 body", text)
        text2, action2 = sync_block(text, "intent-routing", "v2 body")
        self.assertEqual(action2, "updated-block")
        self.assertIn("v2 body", text2)
        self.assertNotIn("v1 body", text2)
        self.assertIn("# user content", text2)

    def test_legacy_dated_marker_is_replaced(self):
        legacy = "# prompt\n\n<!-- deeporbit-managed:intent-routing:2026-07-25 -->\nold\n<!-- /deeporbit-managed:intent-routing -->\n"
        text, action = sync_block(legacy, "intent-routing", "fresh")
        self.assertEqual(action, "updated-block")
        self.assertIn("fresh", text)
        self.assertNotIn("2026-07-25", text)

    def test_user_text_never_touched(self):
        path = self.root / "DeepOrbitPrompt.md"
        path.write_text("# my own rules\n\ncustom line\n", encoding="utf-8")
        result = sync_file(path, name="intent-routing", block_content="block body")
        self.assertEqual(result.action, "appended-block")
        self.assertTrue(path.read_text(encoding="utf-8").startswith("# my own rules\n\ncustom line\n"))

    def test_authored_detection(self):
        self.assertTrue(authored_by_deeporbit("# DeepOrbit on OpenClaw\n..."))
        self.assertFalse(authored_by_deeporbit("text <!-- deeporbit-managed:x -->"))
        self.assertFalse(authored_by_deeporbit("# CLAUDE.md\n\n## 搜索优先级\n"))

    def test_managed_block_presence_never_triggers_full_replace(self):
        """Regression for the 2026-07 wipe: a user file that already carries a
        managed block must stay block-merged, never full-replaced."""
        path = self.root / "CLAUDE.md"
        original = "# CLAUDE.md\n\n## 搜索优先级\n\nuser rules here\n"
        path.write_text(original, encoding="utf-8")
        sync_file(path, name="deeporbit-context", block_content="pointer v1", full_content="# stub\n")
        sync_file(path, name="deeporbit-context", block_content="pointer v2", full_content="# stub v2\n")
        text = path.read_text(encoding="utf-8")
        self.assertIn("user rules here", text)
        self.assertIn("pointer v2", text)
        self.assertNotIn("pointer v1", text)

    def test_authored_file_full_replace(self):
        path = self.root / "AGENTS.md"
        path.write_text("# DeepOrbit on OpenClaw\nold and stale\n", encoding="utf-8")
        result = sync_file(path, name="ctx", block_content="b", full_content="# fresh stub\n")
        self.assertEqual(result.action, "replaced")
        self.assertEqual(path.read_text(encoding="utf-8"), "# fresh stub\n")

    def test_dry_run_writes_nothing(self):
        path = self.root / "AGENTS.md"
        path.write_text("# DeepOrbit on OpenClaw\nstale\n", encoding="utf-8")
        sync_file(path, name="ctx", block_content="b", full_content="# fresh\n", dry_run=True)
        self.assertIn("stale", path.read_text(encoding="utf-8"))


class NoApiKeyGuardTests(unittest.TestCase):
    """DeepOrbit talks JSON via CLI schema; the agent is the model. Any direct
    LLM/API-key integration in src/ is a design violation and must fail CI."""

    def test_src_has_no_api_clients_or_keys(self):
        import re

        src = Path(__file__).resolve().parents[1] / "src" / "deeporbit"
        forbidden = re.compile(r"^\s*(import|from)\s+(openai|anthropic|httpx|requests)\b|urllib\.request|os\.environ.*API_KEY", re.I)
        offenders = []
        for path in src.rglob("*.py"):
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if forbidden.search(line):
                    offenders.append(f"{path.name}:{line_no}: {line.strip()}")
        self.assertEqual(offenders, [])


class VersionTagTests(unittest.TestCase):
    def test_cli_version_flag(self):
        from deeporbit import __version__

        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                main(["--version"])
        except SystemExit as exc:
            self.assertEqual(exc.code, 0)
        self.assertIn(__version__, buffer.getvalue())

    def test_init_stamps_deeporbit_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            initialize(root)
            payload = json.loads((root / "deeporbit.json").read_text(encoding="utf-8"))
            from deeporbit import __version__

            self.assertEqual(payload["deeporbit_version"], __version__)


if __name__ == "__main__":
    unittest.main()
