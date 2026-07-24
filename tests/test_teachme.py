"""Tests for the DeepOrbit → Teach Me export bridge."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deeporbit import teachme
from deeporbit.config import load_config
from fixture_vault import build_messy_vault

FAKE_TEACH_ME = """#!/usr/bin/env python3
import json, sys

def main():
    args = sys.argv[1:]
    record = {"argv": args}
    with open(os.environ["CAPTURE_FILE"], "w") as f:
        json.dump(record, f)
    print(json.dumps({
        "import_id": "import-20260724-120000",
        "status": "ok",
        "origin": {
            "kind": "import",
            "source_type": "obsidian",
            "source_path": args[args.index("--path") + 1],
            "vault_name": args[args.index("--project") + 1],
            "import_id": "import-20260724-120000",
        },
        "prompt_for_ai": "distill " + args[args.index("--path") + 1] + " and pass origin through",
    }))

import os
main()
"""


def make_config(tmp: Path):
    vault = build_messy_vault(tmp / "vault")
    (vault / "70_Family").mkdir(exist_ok=True)
    (vault / "70_Family" / "health.md").write_text("# Private\n", encoding="utf-8")
    (vault / "deeporbit.json").write_text(
        json.dumps(
            {
                "version": 2,
                "vault_id": "test-vault-id",
                "language": "zh-CN",
                "readonly": {"directories": ["60_Notes/微信读书"]},
            }
        ),
        encoding="utf-8",
    )
    return load_config(vault)


class SelectExportNotesTests(unittest.TestCase):
    def test_defaults_include_knowledge_dirs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = make_config(Path(tmp))
            rels = {p.relative_to(config.vault).as_posix() for p in teachme.select_export_notes(config)}
            self.assertIn("40_Wiki/RAG.md", rels)
            self.assertIn("30_Research/RAG-Survey.md", rels)
            # Read-only zone is never exported.
            self.assertNotIn("60_Notes/微信读书/测试书A.md", rels)
            # Projects, writings, and family are opt-in only.
            self.assertFalse(any(rel.startswith("20_Projects/") for rel in rels))
            self.assertFalse(any(rel.startswith("15_Writings/") for rel in rels))
            self.assertFalse(any(rel.startswith("70_Family/") for rel in rels))

    def test_explicit_dirs_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = make_config(Path(tmp))
            rels = {
                p.relative_to(config.vault).as_posix()
                for p in teachme.select_export_notes(config, ["15_Writings"])
            }
            self.assertEqual(rels, {"15_Writings/essay.md"})


class FindScriptTests(unittest.TestCase):
    def test_explicit_missing_script_raises(self) -> None:
        with self.assertRaises(teachme.TeachMeError):
            teachme.find_teach_me_script("/nonexistent/teach_me.py")

    def test_env_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "teach_me.py"
            script.write_text("# stub\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {teachme.SCRIPT_ENV: str(script)}):
                self.assertEqual(teachme.find_teach_me_script(), script)


class ExportTests(unittest.TestCase):
    def test_export_invokes_teach_me_and_rewrites_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = make_config(Path(tmp))
            script = Path(tmp) / "teach_me.py"
            script.write_text(FAKE_TEACH_ME, encoding="utf-8")
            capture_file = Path(tmp) / "argv.json"
            with mock.patch.dict(os.environ, {"CAPTURE_FILE": str(capture_file)}):
                result = teachme.export_to_teach_me(config, script=str(script))

            argv = json.loads(capture_file.read_text())["argv"]
            self.assertIn("--source", argv)
            self.assertIn("obsidian", argv)
            self.assertIn("--project", argv)
            self.assertIn(config.vault.name, argv)
            self.assertIn("--json", argv)

            # Origin must name the real vault, not the staging copy.
            origin = result["origin"]
            self.assertEqual(origin["source_path"], str(config.vault))
            self.assertEqual(origin["vault_name"], config.vault.name)
            self.assertEqual(origin["import_id"], "import-20260724-120000")

            bridge = result["deeporbit"]
            self.assertEqual(bridge["vault_id"], "test-vault-id")
            # 2 wiki + 2 research notes; 微信读书 is read-only.
            self.assertEqual(bridge["exported_notes"], 4)
            self.assertEqual(bridge["dirs"], ["30_Research", "40_Wiki"])
            # The prompt must reference the real vault, never the staging copy.
            self.assertIn(str(config.vault), result["prompt_for_ai"])
            self.assertNotIn("deeporbit-teachme-", result["prompt_for_ai"])
            self.assertEqual(result["path"], str(config.vault))

    def test_export_without_notes_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            (vault / "deeporbit.json").write_text(
                json.dumps({"version": 2, "vault_id": "x", "language": "zh-CN"}), encoding="utf-8"
            )
            config = load_config(vault)
            with self.assertRaises(teachme.TeachMeError):
                teachme.export_to_teach_me(config, script="unused", dirs=None)


if __name__ == "__main__":
    unittest.main()
