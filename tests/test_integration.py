"""End-to-end flows against the messy fixture vault.

Covers the objective list: initialization, deletion (trash), archive, pause,
todo list, index sync, user profile, link routing, command interplay, and the
LaTeX translation pipeline's deterministic core (section splitting + xeCJK
injection; actual xelatex compilation is environment-dependent and stays in
the skill workflow).
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "do.arxiv-translator" / "scripts"))

from deeporbit.cli import main
from deeporbit.config import load_config
from deeporbit.frontmatter import read_fields
from deeporbit.links import list_links
from deeporbit.search import SearchIndex
from deeporbit.vault import initialize
from deeporbit.work import WorkError
from fixture_vault import build_messy_vault

import split_tex


def cli(*argv: str) -> tuple[int, dict | list]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(list(argv))
    return code, json.loads(buffer.getvalue())


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.vault = build_messy_vault(Path(self.temp.name) / "vault")
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(Path(self.temp.name) / "config")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    # --- initialization -------------------------------------------------

    def test_init_migrates_materializes_and_preserves(self):
        result = initialize(self.vault)
        self.assertFalse(result.conflicts)
        self.assertFalse((self.vault / "50_Resources" / "产品发布").exists())
        self.assertTrue((self.vault / "50_Resources" / "Product_Launches" / "legacy-note.md").is_file())
        self.assertIn("do.link", result.workflows)
        self.assertTrue((self.vault / "99_System" / "DeepOrbit" / "skills-index.json").is_file())
        self.assertTrue((self.vault / "99_System" / "Profile.md").is_file())
        self.assertIn("99_System/Bases/Work Status.base", result.system_files)
        self.assertTrue((self.vault / "99_System" / "Templates" / "Project.md").is_file())
        # user content untouched
        self.assertIn("Just a thought", (self.vault / "00_Inbox" / "raw-thought.md").read_text(encoding="utf-8"))

    def test_init_overlay_never_overwrites_user_edits(self):
        initialize(self.vault)
        base = self.vault / "99_System" / "Bases" / "Projects.base"
        base.write_text("user customized\n", encoding="utf-8")
        initialize(self.vault)
        self.assertEqual(base.read_text(encoding="utf-8"), "user customized\n")

    # --- lifecycle flows --------------------------------------------------

    def test_status_overview_spans_all_managed_dirs(self):
        initialize(self.vault)
        code, payload = cli("--vault", str(self.vault), "status")
        self.assertEqual(code, 0)
        counts = payload["counts"]
        self.assertEqual(counts.get("active"), 4)  # ActiveProject + RAG-Survey + Agent-Digest + ActiveConcept(wiki)
        self.assertEqual(counts.get("done"), 1)
        self.assertEqual(counts.get("paused"), 1)
        self.assertEqual(counts.get("processed"), 1)
        self.assertEqual(counts.get("draft"), 1)
        paths = {item["path"] for item in payload["items"]}
        self.assertIn("30_Research/RAG-Survey.md", paths)  # 广义项目, not just 20_Projects
        authors = {item["path"]: item["author"] for item in payload["items"]}
        self.assertEqual(authors["30_Research/Agent-Digest.md"], "ai")
        self.assertEqual(authors["30_Research/RAG-Survey.md"], "human")  # unmarked = human
        self.assertEqual(authors["60_Notes/微信读书/测试书A.md"], "external")  # book author ≠ note authorship

    def test_pause_resume_done_flow(self):
        initialize(self.vault)
        note = "30_Research/RAG-Survey.md"
        code, payload = cli("--vault", str(self.vault), "pause", note)
        self.assertEqual((code, payload["status"]), (0, "paused"))
        fields = read_fields((self.vault / note).read_text(encoding="utf-8"))
        self.assertEqual(fields["updated"], date.today().isoformat())
        code, payload = cli("--vault", str(self.vault), "resume", note)
        self.assertEqual(payload["status"], "active")
        code, payload = cli("--vault", str(self.vault), "done", note)
        self.assertEqual(payload["status"], "done")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["--vault", str(self.vault), "pause", "no/such/note.md"])
        self.assertEqual(code, 1)
        self.assertIn("WORK_ERROR", stderr.getvalue())

    def test_archive_folder_project_and_inbox_item(self):
        initialize(self.vault)
        extra = self.vault / "20_Projects" / "ActiveProject" / "notes.md"
        extra.write_text("---\nstatus: active\n---\n# notes\n", encoding="utf-8")
        code, payload = cli("--vault", str(self.vault), "archive", "20_Projects/ActiveProject")
        self.assertEqual(code, 0)
        moved = self.vault / payload["to"]
        self.assertEqual(moved.parent.parent.name, "Projects")
        self.assertEqual(moved.parent.name, f"{date.today():%Y}")
        self.assertTrue((moved / "ActiveProject.md").is_file())
        self.assertTrue((moved / "assets" / "spec.txt").is_file())  # assets travel with the folder
        fields = read_fields((moved / "ActiveProject.md").read_text(encoding="utf-8"))
        self.assertEqual(fields["status"], "archived")
        self.assertEqual(fields["archived"], date.today().isoformat())
        # every note in the folder is stamped, even non-eponymous ones
        self.assertEqual(read_fields((moved / "notes.md").read_text(encoding="utf-8"))["status"], "archived")

        code, payload = cli("--vault", str(self.vault), "archive", "00_Inbox/processed-idea.md")
        self.assertTrue(payload["to"].startswith("99_System/Archive/Inbox/"))
        self.assertFalse((self.vault / "00_Inbox" / "processed-idea.md").exists())

    def test_archive_never_overwrites(self):
        initialize(self.vault)
        config = load_config(self.vault)
        dest = self.vault / "99_System" / "Archive" / "Projects" / f"{date.today():%Y}" / "DoneProject.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("pre-existing\n", encoding="utf-8")
        from deeporbit.work import archive as work_archive

        with self.assertRaises(WorkError):
            work_archive(config, "20_Projects/DoneProject.md")
        self.assertEqual(dest.read_text(encoding="utf-8"), "pre-existing\n")
        self.assertTrue((self.vault / "20_Projects" / "DoneProject.md").is_file())

    def test_trash_moves_and_protects(self):
        initialize(self.vault)
        code, payload = cli("--vault", str(self.vault), "trash", "00_Inbox/raw-thought.md")
        self.assertEqual(code, 0)
        self.assertTrue((self.vault / ".trash" / "00_Inbox" / "raw-thought.md").is_file())
        from deeporbit.work import trash as work_trash

        config = load_config(self.vault)
        (self.vault / ".obsidian").mkdir(exist_ok=True)
        for protected in ("deeporbit.json", ".obsidian", "99_System/Bases"):
            with self.assertRaises(WorkError, msg=protected):
                work_trash(config, protected)

    # --- tasks, agenda, calendar chain -------------------------------------

    def test_todo_agenda_calendar_chain(self):
        initialize(self.vault)
        code, added = cli("--vault", str(self.vault), "todo", "add", "Prepare the review", "--today", "--scheduled", date.today().isoformat())
        self.assertEqual(code, 0)
        code, listing = cli("--vault", str(self.vault), "todo", "list")
        ids = [task["id"] for task in listing]
        self.assertIn(added["id"], ids)
        code, agenda_payload = cli("--vault", str(self.vault), "agenda")
        self.assertTrue(any(task["id"] == added["id"] for task in agenda_payload["today"]))
        code, cal = cli("--vault", str(self.vault), "calendar", "export")
        self.assertGreaterEqual(cal["events"], 1)
        self.assertTrue(Path(cal["path"]).is_file())
        code, done_payload = cli("--vault", str(self.vault), "todo", "done", added["id"])
        self.assertTrue(done_payload["done"])

    # --- index synchronization ---------------------------------------------

    def test_index_sync_tracks_add_modify_trash(self):
        initialize(self.vault)
        config = load_config(self.vault)
        index = SearchIndex(config)
        first = index.ensure()
        self.assertGreater(first.added, 0)
        self.assertEqual(index.ensure().unchanged, first.added)

        new_note = self.vault / "40_Wiki" / "Fresh.md"
        new_note.write_text("# Fresh\nA brand new concept.\n", encoding="utf-8")
        self.assertEqual(index.ensure().added, 1)

        new_note.write_text("# Fresh\nUpdated contents.\n", encoding="utf-8")
        self.assertEqual(index.ensure().updated, 1)

        cli("--vault", str(self.vault), "trash", "40_Wiki/Fresh.md")
        self.assertEqual(index.ensure().deleted, 1)

        hits = index.query("lexical baselines")
        self.assertTrue(any(hit["path"] == "30_Research/RAG-Survey.md" for hit in hits))

    # --- link routing + user profile ----------------------------------------

    def test_link_describe_and_vault_resolution(self):
        initialize(self.vault)
        code, link = cli("link", "add", "main", str(self.vault), "--description", "个人研究库")
        self.assertTrue(link["deeporbit"])
        code, added = cli("--vault", "@main", "todo", "add", "routed task")
        self.assertEqual(code, 0)
        code, refined = cli("link", "describe", "main", "个人研究库:RAG 与 Agent 方向", "--source", "agent")
        self.assertEqual(refined["description_source"], "agent")
        self.assertEqual(list_links()[0].description, "个人研究库:RAG 与 Agent 方向")

    def test_profile_set_observe_show(self):
        initialize(self.vault)
        code, payload = cli("--vault", str(self.vault), "profile", "set", "role", "独立开发者")
        self.assertEqual(payload["fields"]["role"], "独立开发者")
        cli("--vault", str(self.vault), "profile", "observe", "关注 RAG 与 Agent 工程化")
        code, shown = cli("--vault", str(self.vault), "profile", "show")
        self.assertEqual(shown["fields"]["language"], "zh-CN")
        self.assertTrue(any("RAG" in entry for entry in shown["observations"]))

    def test_profile_focus_and_compact(self):
        initialize(self.vault)
        cli("--vault", str(self.vault), "profile", "observe", "偏好短句")
        cli("--vault", str(self.vault), "profile", "observe", "机器人方向")
        code, _ = cli("--vault", str(self.vault), "profile", "focus", "机器人工程师，表达直接，偏好短句。")
        text = (self.vault / "99_System" / "Profile.md").read_text(encoding="utf-8")
        self.assertIn("机器人工程师，表达直接，偏好短句。", text)
        code, result = cli("--vault", str(self.vault), "profile", "compact")
        self.assertEqual(result["archived"], 2)
        text = (self.vault / "99_System" / "Profile.md").read_text(encoding="utf-8")
        self.assertNotIn("偏好短句\n", text.split("## Observations")[-1])
        archive = self.vault / result["archive"]
        self.assertIn("机器人方向", archive.read_text(encoding="utf-8"))
        code, again = cli("--vault", str(self.vault), "profile", "compact")
        self.assertEqual(again["archived"], 0)  # idempotent

    # --- suggestions, cron, recipes -------------------------------------------

    def test_suggest_flags_done_dormant_and_missing_daily(self):
        initialize(self.vault)
        code, suggestions = cli("--vault", str(self.vault), "suggest")
        self.assertEqual(code, 0)
        ids = [item["id"] for item in suggestions]
        self.assertEqual(ids[0], "archive-done")  # high priority sorts first
        self.assertIn("pause-dormant", ids)  # fixture updated dates are weeks old
        self.assertIn("start-daily", ids)
        self.assertIn("complete-profile", ids)
        archive = next(item for item in suggestions if item["id"] == "archive-done")
        self.assertIn("Done Project", archive["detail"])

    def test_cron_add_due_and_disable(self):
        initialize(self.vault)
        code, job = cli("--vault", str(self.vault), "cron", "add", "dream", "Run do.dream consolidation", "--every", "daily")
        self.assertEqual((code, job["every_hours"]), (0, 24))
        code, due = cli("cron", "run-due")
        self.assertEqual([j["name"] for j in due], ["dream"])
        code, again = cli("cron", "run-due")
        self.assertEqual(again, [])  # at most once per interval
        cli("cron", "disable", "dream")
        from deeporbit.cron import run_due as cron_run_due
        from datetime import datetime, timedelta, timezone

        future = datetime.now(timezone.utc) + timedelta(days=2)
        self.assertEqual(cron_run_due(future), [])  # disabled stays quiet

    def test_recipe_list_and_run_plan(self):
        initialize(self.vault)
        code, recipes = cli("--vault", str(self.vault), "recipe", "list")
        names = [r["name"] for r in recipes]
        self.assertIn("Weekly Review", names)
        code, plan = cli("--vault", str(self.vault), "recipe", "run", "Weekly Review")
        self.assertEqual(plan["schedule"], "weekly")
        kinds = [step["kind"] for step in plan["steps"]]
        self.assertEqual(kinds[:2], ["cli", "cli"])
        self.assertIn("skill", kinds)
        self.assertEqual(plan["warnings"], [])

    # --- read-only zones (weread-vault managed) ----------------------------

    def test_init_detects_weread_zone_and_persists(self):
        result = initialize(self.vault)
        self.assertIn("60_Notes/微信读书", result.readonly_dirs)
        self.assertNotIn("20_Projects/微信读书记录", result.readonly_dirs)  # name alone is not enough
        config = load_config(self.vault)
        self.assertIn("60_Notes/微信读书", config.readonly_dirs)
        code, payload = cli("--vault", str(self.vault), "status")
        readonly = {item["path"]: item["readonly"] for item in payload["items"]}
        self.assertTrue(readonly["60_Notes/微信读书/测试书A.md"])
        self.assertFalse(readonly["30_Research/RAG-Survey.md"])

    def test_lifecycle_refuses_readonly_zone(self):
        initialize(self.vault)
        config = load_config(self.vault)
        from deeporbit.work import archive as work_archive
        from deeporbit.work import set_status as work_set_status
        from deeporbit.work import trash as work_trash

        note = "60_Notes/微信读书/测试书A.md"
        for mutate in (
            lambda: work_set_status(config, note, "done"),
            lambda: work_archive(config, note),
            lambda: work_trash(config, note),
        ):
            with self.assertRaises(WorkError, msg=mutate):
                mutate()
        self.assertTrue((self.vault / note).is_file())  # untouched
        # writable paths still work
        work_set_status(config, "30_Research/RAG-Survey.md", "paused")

    def test_suggest_ignores_readonly_items(self):
        initialize(self.vault)
        from deeporbit.suggest import suggest as build_suggestions

        suggestions = build_suggestions(load_config(self.vault))
        details = " ".join(item.detail for item in suggestions)
        self.assertNotIn("测试书", details)

    def test_suggest_dormancy_mtime_fallback_and_wiki_exclusion(self):
        import os
        import time

        initialize(self.vault)
        old = time.time() - 40 * 86400
        no_date = self.vault / "20_Projects" / "NoDate.md"
        no_date.write_text("---\ntype: project\nstatus: active\n---\n# No Date Project\n", encoding="utf-8")
        os.utime(no_date, (old, old))
        wiki = self.vault / "40_Wiki" / "ActiveConcept.md"
        os.utime(wiki, (old, old))
        quoted = self.vault / "15_Writings" / "essay.md"
        quoted.write_text('---\nstatus: active\nupdated: "2026-06-01"\n---\n# Essay\n', encoding="utf-8")

        from deeporbit.suggest import suggest as build_suggestions

        suggestions = build_suggestions(load_config(self.vault))
        dormant = next(item for item in suggestions if item.id == "pause-dormant")
        self.assertIn("No Date Project", dormant.detail)  # mtime fallback
        self.assertIn("Essay", dormant.detail)  # quoted date parses
        self.assertNotIn("Active Concept", dormant.detail)  # wiki is not lifecycle work

    # --- hygiene: attachments & code-in-vault ----------------------------------

    def test_hygiene_detects_violations(self):
        initialize(self.vault)
        (self.vault / "screenshot.png").write_bytes(b"png")
        (self.vault / "20_Projects" / "loose.jpg").write_bytes(b"jpg")
        code_dir = self.vault / "30_Research"
        code_dir.mkdir(exist_ok=True)
        (code_dir / "tool.py").write_text("print('x')\n", encoding="utf-8")
        from deeporbit.hygiene import scan_hygiene

        findings = {(f.kind, f.path) for f in scan_hygiene(load_config(self.vault))}
        self.assertIn(("orphan-attachment", "screenshot.png"), findings)
        self.assertIn(("orphan-attachment", "20_Projects/loose.jpg"), findings)
        self.assertIn(("code-file", "30_Research/tool.py"), findings)
        from deeporbit.suggest import suggest as build_suggestions

        suggestion_ids = {item.id for item in build_suggestions(load_config(self.vault))}
        self.assertIn("vault-cleanup-reminder", suggestion_ids)
        self.assertIn("attachments-messy", suggestion_ids)
        self.assertIn("code-in-vault", suggestion_ids)

    def test_sweep_pauses_idle_and_respects_exclusions(self):
        import os
        import time

        initialize(self.vault)
        old = time.time() - 80 * 86400
        stale = self.vault / "20_Projects" / "Stale.md"
        stale.write_text("---\ntype: project\nstatus: active\n---\n# Stale\n", encoding="utf-8")
        os.utime(stale, (old, old))
        config = load_config(self.vault)

        from deeporbit.work import sweep as work_sweep

        dry = work_sweep(config, days=60, dry_run=True)
        self.assertIn("20_Projects/Stale.md", dry["matched"])
        self.assertEqual(dry["paused"], [])  # dry run writes nothing

        result = work_sweep(config, days=60)
        self.assertIn("20_Projects/Stale.md", result["paused"])
        self.assertNotIn("40_Wiki/ActiveConcept.md", result["paused"])  # wiki excluded
        self.assertNotIn("60_Notes/微信读书/测试书A.md", result["paused"])  # readonly excluded
        self.assertEqual(work_sweep(config, days=60)["matched"], [])  # idempotent

    # --- LaTeX translation pipeline (deterministic core) ---------------------

    def test_split_tex_modularizes_and_injects_cjk(self):
        workdir = Path(self.temp.name) / "paper"
        workdir.mkdir()
        fixture = Path(__file__).resolve().parent / "fixtures" / "main.tex"
        main_tex = workdir / "main.tex"
        shutil.copy2(fixture, main_tex)

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = split_tex.main([str(main_tex), "--cjk-font", "Noto Sans CJK SC"])
        self.assertEqual(code, 0)
        report = json.loads(buffer.getvalue())
        self.assertEqual(len(report["sections"]), 3)
        self.assertTrue(report["cjk_injected"])

        rewritten = main_tex.read_text(encoding="utf-8")
        self.assertIn("\\usepackage{xeCJK}", rewritten)
        self.assertIn("\\setCJKmainfont{Noto Sans CJK SC}", rewritten)
        self.assertIn("\\input{sections/01_introduction}", rewritten)
        self.assertNotIn("\\section{Introduction}", rewritten)
        method = (workdir / "sections" / "02_method.tex").read_text(encoding="utf-8")
        self.assertIn("\\subsection{Setup}", method)  # subsection stays inside its section file

        # translation overwrite, then re-split must be a no-op that preserves work
        intro = workdir / "sections" / "01_introduction.tex"
        intro.write_text("\\section{引言}\n已翻译的内容。\n", encoding="utf-8")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            split_tex.main([str(main_tex), "--cjk-font", "Noto Sans CJK SC"])
        rerun = json.loads(buffer.getvalue())
        self.assertEqual(rerun["sections"], [])
        self.assertEqual(intro.read_text(encoding="utf-8"), "\\section{引言}\n已翻译的内容。\n")


if __name__ == "__main__":
    unittest.main()
