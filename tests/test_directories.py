"""Configurable-directory contract: renamed logical dirs, init adoption,
status subfolders (Paused/Archived), organize, and the doctor skeleton check.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deeporbit.cli import main
from deeporbit.config import load_config, skeleton_dirs
from deeporbit.frontmatter import read_fields
from deeporbit.heartbeat import build_context
from deeporbit.vault import initialize
from deeporbit.work import organize


def cli(*argv: str) -> tuple[int, dict | list]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(list(argv))
    return code, json.loads(buffer.getvalue())


def _note(status: str = "active", title: str = "Note") -> str:
    return f"---\nstatus: {status}\nupdated: {date.today().isoformat()}\n---\n# {title}\n"


class ConfigurableDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # resolve(): macOS tempdirs live under /private/var (symlink canonicalization)
        self.vault = (Path(self.temp.name) / "vault").resolve()
        self.vault.mkdir(parents=True)
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(Path(self.temp.name) / "config")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def _write_directories(self, mapping: dict) -> None:
        (self.vault / "deeporbit.json").write_text(
            json.dumps({"directories": mapping}, ensure_ascii=False), encoding="utf-8"
        )

    # --- skeleton --------------------------------------------------------

    def test_skeleton_dirs_include_status_subdirs(self):
        dirs = skeleton_dirs()
        for section in ("20_Projects", "30_Research"):
            self.assertIn(f"{section}/Paused", dirs)
            self.assertIn(f"{section}/Archived", dirs)
        renamed = skeleton_dirs({"projects": "项目"})
        self.assertIn("项目/Paused", renamed)
        self.assertIn("项目/Archived", renamed)
        self.assertNotIn("20_Projects", renamed)

    def test_init_creates_status_subdirs(self):
        initialize(self.vault)
        for section in ("20_Projects", "30_Research"):
            self.assertTrue((self.vault / section / "Paused").is_dir())
            self.assertTrue((self.vault / section / "Archived").is_dir())

    # --- renamed directories route everything ----------------------------

    def test_renamed_inbox_routes_todo_agenda_heartbeat(self):
        self._write_directories({"inbox": "00_收件箱"})
        initialize(self.vault)
        code, task = cli("--vault", str(self.vault), "todo", "add", "买牛奶")
        self.assertEqual(code, 0)
        self.assertEqual(task["path"], "00_收件箱/Todos.md")
        self.assertTrue((self.vault / "00_收件箱" / "Todos.md").is_file())
        self.assertFalse((self.vault / "00_Inbox").exists())

        code, agenda_payload = cli("--vault", str(self.vault), "agenda")
        self.assertEqual(code, 0)
        self.assertTrue(any(t["text"].startswith("买牛奶") for tasks in agenda_payload.values() for t in tasks))

        (self.vault / "00_收件箱" / "loose-note.md").write_text("# loose\n", encoding="utf-8")
        config = load_config(self.vault)
        facts = build_context(config)["facts"]
        self.assertEqual(facts["inbox_note_count"], 1)

    # --- init adoption ----------------------------------------------------

    def test_init_adopts_default_dir_with_content(self):
        (self.vault / "00_Inbox").mkdir(parents=True)
        (self.vault / "00_Inbox" / "idea.md").write_text("# idea\n", encoding="utf-8")
        self._write_directories({"inbox": "00_收件箱"})
        result = initialize(self.vault)
        self.assertIn("00_Inbox -> 00_收件箱", result.adopted)
        self.assertTrue((self.vault / "00_收件箱" / "idea.md").is_file())
        self.assertFalse((self.vault / "00_Inbox").exists())

    def test_init_reports_conflict_when_both_exist(self):
        (self.vault / "00_Inbox").mkdir(parents=True)
        (self.vault / "00_Inbox" / "old.md").write_text("# old\n", encoding="utf-8")
        (self.vault / "00_收件箱").mkdir(parents=True)
        (self.vault / "00_收件箱" / "new.md").write_text("# new\n", encoding="utf-8")
        self._write_directories({"inbox": "00_收件箱"})
        result = initialize(self.vault)
        self.assertEqual(result.adopted, [])
        self.assertTrue(any("00_Inbox" in entry for entry in result.conflicts))
        # never merged: both trees untouched
        self.assertTrue((self.vault / "00_Inbox" / "old.md").is_file())
        self.assertTrue((self.vault / "00_收件箱" / "new.md").is_file())

    # --- status subfolders -------------------------------------------------

    def test_pause_resume_moves_note_and_assets(self):
        initialize(self.vault)
        (self.vault / "20_Projects" / "P.md").write_text(_note(), encoding="utf-8")
        (self.vault / "20_Projects" / "P").mkdir()
        (self.vault / "20_Projects" / "P" / "spec.txt").write_text("asset\n", encoding="utf-8")

        code, payload = cli("--vault", str(self.vault), "pause", "20_Projects/P.md")
        self.assertEqual(code, 0)
        self.assertEqual(payload["path"], "20_Projects/Paused/P.md")
        self.assertTrue((self.vault / "20_Projects" / "Paused" / "P" / "spec.txt").is_file())
        self.assertFalse((self.vault / "20_Projects" / "P.md").exists())
        self.assertFalse((self.vault / "20_Projects" / "P").exists())

        code, payload = cli("--vault", str(self.vault), "resume", "20_Projects/Paused/P.md")
        self.assertEqual(payload["path"], "20_Projects/P.md")
        self.assertTrue((self.vault / "20_Projects" / "P.md").is_file())
        self.assertTrue((self.vault / "20_Projects" / "P" / "spec.txt").is_file())

    def test_archive_status_sections_vs_other_sections(self):
        initialize(self.vault)
        (self.vault / "20_Projects" / "P.md").write_text(_note(), encoding="utf-8")
        (self.vault / "30_Research" / "R.md").write_text(_note(title="R"), encoding="utf-8")
        (self.vault / "15_Writings" / "essay.md").write_text(_note("draft", "Essay"), encoding="utf-8")

        code, payload = cli("--vault", str(self.vault), "archive", "20_Projects/P.md")
        self.assertEqual(payload["to"], "20_Projects/Archived/P.md")
        code, payload = cli("--vault", str(self.vault), "archive", "30_Research/R.md")
        self.assertEqual(payload["to"], "30_Research/Archived/R.md")
        fields = read_fields((self.vault / "30_Research" / "Archived" / "R.md").read_text(encoding="utf-8"))
        self.assertEqual(fields["status"], "archived")

        # non-status sections keep the system Archive layout
        code, payload = cli("--vault", str(self.vault), "archive", "15_Writings/essay.md")
        self.assertTrue(payload["to"].startswith("99_System/Archive/Writings/"))

    # --- organize -----------------------------------------------------------

    def test_organize_dry_run_then_apply(self):
        initialize(self.vault)
        (self.vault / "20_Projects" / "A.md").write_text(_note("paused", "A"), encoding="utf-8")
        (self.vault / "20_Projects" / "Paused" / "B.md").write_text(_note("active", "B"), encoding="utf-8")
        (self.vault / "20_Projects" / "C.md").write_text(_note("archived", "C"), encoding="utf-8")
        (self.vault / "20_Projects" / "D.md").write_text(_note("done", "D"), encoding="utf-8")

        config = load_config(self.vault)
        plan = organize(config, dry_run=True)
        moves = {entry["from"]: entry["to"] for entry in plan["moves"]}
        self.assertEqual(moves["20_Projects/A.md"], "20_Projects/Paused/A.md")
        self.assertEqual(moves["20_Projects/Paused/B.md"], "20_Projects/B.md")
        self.assertEqual(moves["20_Projects/C.md"], "20_Projects/Archived/C.md")
        self.assertNotIn("20_Projects/D.md", moves)  # done has no filing rule
        # dry-run touched nothing
        self.assertTrue((self.vault / "20_Projects" / "A.md").is_file())
        self.assertTrue((self.vault / "20_Projects" / "Paused" / "B.md").is_file())

        code, applied = cli("--vault", str(self.vault), "organize", "--apply")
        self.assertEqual(code, 0)
        self.assertFalse(applied["dry_run"])
        self.assertTrue((self.vault / "20_Projects" / "Paused" / "A.md").is_file())
        self.assertTrue((self.vault / "20_Projects" / "B.md").is_file())
        self.assertTrue((self.vault / "20_Projects" / "Archived" / "C.md").is_file())
        # second run is a no-op (idempotent)
        again = organize(load_config(self.vault), dry_run=True)
        self.assertEqual(again["moves"], [])

    def test_organize_reports_conflicts_without_overwriting(self):
        initialize(self.vault)
        (self.vault / "20_Projects" / "A.md").write_text(_note("paused", "A-root"), encoding="utf-8")
        (self.vault / "20_Projects" / "Paused" / "A.md").write_text(_note("paused", "A-existing"), encoding="utf-8")
        plan = organize(load_config(self.vault), dry_run=False)
        self.assertEqual(plan["moves"], [])
        self.assertTrue(any("20_Projects/Paused/A.md" in entry for entry in plan["conflicts"]))
        self.assertEqual(
            (self.vault / "20_Projects" / "Paused" / "A.md").read_text(encoding="utf-8"),
            _note("paused", "A-existing"),
        )

    # --- doctor skeleton check ----------------------------------------------

    def test_doctor_strict_exit_codes(self):
        initialize(self.vault)
        code, payload = cli("--vault", str(self.vault), "doctor", "--strict")
        self.assertEqual(code, 0)
        self.assertEqual(payload["skeleton_missing"], [])
        self.assertEqual(payload["skeleton_violations"], [])

        (self.vault / "stray.md").write_text("stray\n", encoding="utf-8")
        code, payload = cli("--vault", str(self.vault), "doctor", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("stray.md", payload["skeleton_violations"])

        # non-strict doctor still exits 0 with violations present
        code, _ = cli("--vault", str(self.vault), "doctor")
        self.assertEqual(code, 0)

    def test_doctor_strict_flags_missing_skeleton(self):
        initialize(self.vault)
        (self.vault / "20_Projects" / "Paused").rmdir()
        code, payload = cli("--vault", str(self.vault), "doctor", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("20_Projects/Paused", payload["skeleton_missing"])

    def test_doctor_root_whitelist(self):
        initialize(self.vault)
        for allowed in (".obsidian/x", ".trash/y", "CLAUDE.md", "AGENTS.md", "DeepOrbitPrompt.md"):
            target = self.vault / allowed
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok\n", encoding="utf-8")
        code, payload = cli("--vault", str(self.vault), "doctor", "--strict")
        self.assertEqual(code, 0)
        self.assertEqual(payload["skeleton_violations"], [])


if __name__ == "__main__":
    unittest.main()
