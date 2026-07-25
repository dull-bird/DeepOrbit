"""Proactive-companion core: stalled rule, snapshots, heartbeat, recipe
schedule, and suggestion feedback.

Covers the deterministic half of the proactive companion (design doc
docs/proactive-companion.md): per-item stalled-project suggestions layered
under pause-dormant, idempotent daily snapshots with deltas, the heartbeat
context pack, cron registration from recipe frontmatter, and device-local
feedback counters with corruption tolerance.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deeporbit.cli import main
from deeporbit.config import load_config
from deeporbit.cron import list_jobs
from deeporbit.heartbeat import build_context, load_rules
from deeporbit.recipes import RecipeError, schedule_recipe
from deeporbit.suggest import acceptance_rates, feedback_path, record_feedback, suggest
from deeporbit.work import write_snapshot

TODAY = date(2026, 7, 25)


def _note(status: str = "active", updated: str = "", extra: str = "") -> str:
    fields = f"status: {status}\n"
    if updated:
        fields += f"updated: {updated}\n"
    return f"---\n{fields}---\n\n{extra}"


def _days_ago(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


class ProactiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.vault = self.root / "vault"
        self.vault.mkdir()
        (self.vault / "00_Inbox").mkdir()
        (self.vault / "20_Projects").mkdir()
        (self.vault / "10_Diary").mkdir()
        self.env = mock.patch.dict(
            os.environ,
            {
                "XDG_CONFIG_HOME": str(self.root / "config"),
                "XDG_CACHE_HOME": str(self.root / "cache"),
            },
        )
        self.env.start()
        self.config = load_config(self.vault, create=True)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def _write(self, rel: str, content: str) -> None:
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _suggestions(self):
        return suggest(self.config, today=TODAY)

    def _stalled_paths(self):
        return [s.detail.split(":")[0] for s in self._suggestions() if s.id == "stalled-project"]

    # --- stalled-project rule -------------------------------------------

    def test_stalled_by_inactivity(self):
        self._write(
            "20_Projects/Old.md",
            _note(updated=_days_ago(8), extra="- [ ] next step ^do-a1\n"),
        )
        stalled = self._stalled_paths()
        self.assertIn("20_Projects/Old.md", stalled)
        entry = next(s for s in self._suggestions() if s.id == "stalled-project")
        self.assertEqual(entry.priority, "medium")
        self.assertIn("do:todo", entry.action)

    def test_stalled_by_missing_open_todo(self):
        # Fresh activity but no open checkbox: the project has no next action.
        self._write("20_Projects/Fresh.md", _note(updated=_days_ago(0), extra="- [x] shipped ^do-b1\n"))
        self.assertIn("20_Projects/Fresh.md", self._stalled_paths())

    def test_not_stalled_when_recent_with_open_todo(self):
        self._write(
            "20_Projects/Healthy.md",
            _note(updated=_days_ago(1), extra="- [ ] keep going ^do-c1\n"),
        )
        self.assertNotIn("20_Projects/Healthy.md", self._stalled_paths())

    def test_stalled_skips_dormant_items(self):
        # 21d+ dormant items are reported by pause-dormant, never duplicated
        # by stalled-project (layering: 7d -> next action, 21d -> pause).
        self._write("20_Projects/Dormant.md", _note(updated=_days_ago(30), extra="- [ ] todo ^do-d1\n"))
        suggestions = self._suggestions()
        self.assertNotIn("20_Projects/Dormant.md", [s.detail.split(":")[0] for s in suggestions if s.id == "stalled-project"])
        dormant = next(s for s in suggestions if s.id == "pause-dormant")
        self.assertIn("Dormant", dormant.detail)

    def test_stalled_ignores_wiki_and_non_active(self):
        self._write("40_Wiki/Concept.md", _note(updated=_days_ago(30)))
        self._write("20_Projects/Paused.md", _note(status="paused", updated=_days_ago(10)))
        stalled = self._stalled_paths()
        self.assertNotIn("40_Wiki/Concept.md", stalled)
        self.assertNotIn("20_Projects/Paused.md", stalled)

    # --- status --snapshot ------------------------------------------------

    def test_snapshot_idempotent_same_day(self):
        self._write("20_Projects/A.md", _note(updated=_days_ago(0)))
        first = write_snapshot(self.config, today=TODAY)
        second = write_snapshot(self.config, today=TODAY)
        self.assertEqual(first["snapshot"], f"99_System/snapshots/{TODAY.isoformat()}.json")
        self.assertEqual(first["counts"], second["counts"])
        snapshots = list((self.vault / "99_System" / "snapshots").glob("*.json"))
        self.assertEqual(len(snapshots), 1)
        self.assertIsNone(first["delta"])  # no previous snapshot
        self.assertEqual(first["counts"]["active"], 1)
        self.assertEqual(first["todos"], {"total": 0, "open": 0, "done": 0})

    def test_snapshot_delta_against_previous_day(self):
        self._write("20_Projects/A.md", _note(updated=_days_ago(1)))
        self._write("20_Projects/B.md", _note(status="paused", updated=_days_ago(1)))
        write_snapshot(self.config, today=TODAY - timedelta(days=1))
        # Next day: B is done, a new active project appears, one todo completed.
        self._write("20_Projects/B.md", _note(status="done", updated=_days_ago(0)))
        self._write("20_Projects/C.md", _note(updated=_days_ago(0)))
        self._write("00_Inbox/Todos.md", "# Todos\n\n- [x] finished thing ✅ 2026-07-25 ^do-e1\n- [ ] open thing ^do-e2\n")
        result = write_snapshot(self.config, today=TODAY)
        delta = result["delta"]
        self.assertEqual(delta["since"], (TODAY - timedelta(days=1)).isoformat())
        self.assertEqual(delta["activated"], ["20_Projects/C.md"])
        self.assertEqual(delta["completed"], ["20_Projects/B.md"])
        self.assertEqual(delta["done_todos"], 1)
        self.assertEqual(result["todos"], {"total": 2, "open": 1, "done": 1})

    def test_status_snapshot_cli(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--vault", str(self.vault), "status", "--snapshot"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue((self.vault / payload["snapshot"]).is_file())
        self.assertIn("delta", payload)

    # --- heartbeat context pack -------------------------------------------

    def test_heartbeat_context_structure(self):
        self._write("20_Projects/Stalled.md", _note(updated=_days_ago(9)))
        self._write("10_Diary/2026-07-24.md", "# yesterday\n")
        self._write("10_Diary/2026-07-23.md", "# day before\n")
        self._write("00_Inbox/idea.md", "capture\n")
        self._write(
            "99_System/Rules/stalled-project.md",
            "---\nname: stalled-project\nwhen: active 项目 7 天无新活动\nthen: 建议设下一步行动\n---\n\n# body\n",
        )
        write_snapshot(self.config, today=TODAY - timedelta(days=1))
        record_feedback("stalled-project", "accepted")
        context = build_context(self.config, now=datetime(2026, 7, 25, 9, 0))
        self.assertEqual(
            set(context),
            {"generated_at", "suggest", "status", "reminders_due", "snapshot_delta", "facts", "rules", "feedback"},
        )
        self.assertIsInstance(context["suggest"], list)
        self.assertIsInstance(context["status"], dict)
        self.assertIsInstance(context["reminders_due"], list)
        self.assertIsNotNone(context["snapshot_delta"])
        self.assertEqual(context["facts"]["stalled_projects"], 1)
        self.assertEqual(context["facts"]["inbox_note_count"], 1)
        self.assertEqual(context["facts"]["diary_streak_days"], 2)
        self.assertEqual(
            context["rules"],
            [
                {
                    "name": "stalled-project",
                    "when": "active 项目 7 天无新活动",
                    "then": "建议设下一步行动",
                    "path": "99_System/Rules/stalled-project.md",
                }
            ],
        )
        self.assertEqual(context["feedback"]["stalled-project"]["acceptance_rate"], 1.0)

    def test_heartbeat_rules_tolerant(self):
        self.assertEqual(load_rules(self.config), [])  # no Rules dir at all
        self._write("99_System/Rules/broken.md", "no frontmatter here\n")
        self.assertEqual(load_rules(self.config), [])  # unparseable -> skipped

    def test_heartbeat_reminders_due_not_delivered(self):
        self._write("00_Inbox/Todos.md", "# Todos\n\n- [ ] call bank 📅 2026-07-25 ⏰ 08:00 ^do-f1\n")
        context = build_context(self.config, now=datetime(2026, 7, 25, 9, 0))
        self.assertEqual([t["id"] for t in context["reminders_due"]], ["f1"])
        # check-only: no reminded state was recorded
        state = Path(os.environ["XDG_CONFIG_HOME"]) / "deeporbit" / "reminders.json"
        self.assertFalse(state.exists())

    def test_heartbeat_cli(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--vault", str(self.vault), "heartbeat"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertIn("rules", payload)
        self.assertIn("facts", payload)

    # --- recipe schedule ----------------------------------------------------

    def _recipe(self, name: str, schedule: str = "") -> None:
        fields = f"name: {name}\ndescription: test recipe\n"
        if schedule:
            fields += f"schedule: {schedule}\n"
        self._write(f"99_System/Recipes/{name}.md", f"---\n{fields}---\n\n1. cli: deeporbit --vault . status\n")

    def test_recipe_schedule_registers_cron_job(self):
        self._recipe("weekly-review", "weekly")
        result = schedule_recipe(self.config, "weekly-review")
        self.assertTrue(result["created"])
        self.assertEqual(result["job"], "recipe-weekly-review")
        job = next(j for j in list_jobs() if j.name == "recipe-weekly-review")
        self.assertEqual(job.every_hours, 168)
        self.assertIn('deeporbit recipe run "weekly-review"', job.instruction)

    def test_recipe_schedule_idempotent(self):
        self._recipe("daily-news", "daily")
        first = schedule_recipe(self.config, "daily-news")
        second = schedule_recipe(self.config, "daily-news")
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertIn("skipped", second["note"])
        self.assertEqual(len([j for j in list_jobs() if j.name == "recipe-daily-news"]), 1)

    def test_recipe_schedule_requires_frontmatter(self):
        self._recipe("no-schedule")
        with self.assertRaises(RecipeError):
            schedule_recipe(self.config, "no-schedule")

    # --- suggest feedback ---------------------------------------------------

    def test_feedback_accumulates(self):
        record_feedback("stalled-project", "accepted")
        record_feedback("stalled-project", "accepted")
        entry = record_feedback("stalled-project", "dismissed")
        self.assertEqual(entry, {"rule_id": "stalled-project", "accepted": 2, "dismissed": 1})
        rates = acceptance_rates()
        self.assertEqual(rates["stalled-project"]["acceptance_rate"], round(2 / 3, 3))

    def test_feedback_tolerates_corrupt_file(self):
        path = feedback_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json", encoding="utf-8")
        self.assertEqual(acceptance_rates(), {})
        entry = record_feedback("triage-inbox", "dismissed")
        self.assertEqual(entry["dismissed"], 1)

    def test_feedback_cli(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--vault", str(self.vault), "suggest", "feedback", "archive-done", "accepted"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["accepted"], 1)
        # bare suggest still lists suggestions
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--vault", str(self.vault), "suggest"])
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(buffer.getvalue()), list)
    # --- zero-token gate -------------------------------------------------

    def _gate(self, **kwargs):
        from deeporbit.heartbeat import evaluate_gate

        return evaluate_gate(build_context(self.config, now=datetime(2026, 7, 25, 12, 0)), **kwargs)

    def test_gate_silent_on_fresh_vault(self):
        verdict = self._gate()
        self.assertFalse(verdict["notify"])
        self.assertEqual(verdict["reasons"], [])

    def test_gate_fires_on_stalled_project(self):
        self._write("20_Projects/Old.md", _note(updated=_days_ago(10)))
        verdict = self._gate()
        self.assertTrue(verdict["notify"])
        self.assertIn("stalled-project", [r["rule"] for r in verdict["reasons"]])

    def test_gate_fires_on_due_reminder(self):
        from deeporbit.tasks import add_task

        add_task(self.config, "晨练", due=str(TODAY), time="00:01")
        verdict = self._gate()
        self.assertIn("due-reminders", [r["rule"] for r in verdict["reasons"]])

    def test_gate_diary_requires_established_habit(self):
        # 2 old notes: below habit threshold → no diary reason
        for day in ("2026-07-20", "2026-07-21"):
            self._write(f"10_Diary/{day}.md", "# diary\n")
        self.assertNotIn("diary-streak", [r["rule"] for r in self._gate()["reasons"]])
        # third note crosses the habit threshold and the streak is broken → fires
        self._write("10_Diary/2026-07-22.md", "# diary\n")
        self.assertIn("diary-streak", [r["rule"] for r in self._gate()["reasons"]])

    def test_gate_suppresses_dismissed_rules(self):
        self._write("20_Projects/Old.md", _note(updated=_days_ago(10)))
        record_feedback("stalled-project", "dismissed")
        verdict = self._gate()
        self.assertNotIn("stalled-project", [r["rule"] for r in verdict["reasons"]])
        self.assertFalse(verdict["notify"])

    def test_gate_cli_exit_codes(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--vault", str(self.vault), "heartbeat", "--gate"])
        self.assertEqual(code, 1)  # silent → exit 1 so shells short-circuit
        self.assertFalse(json.loads(buffer.getvalue())["notify"])
        self._write("20_Projects/Old.md", _note(updated=_days_ago(10)))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--vault", str(self.vault), "heartbeat", "--gate"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(buffer.getvalue())["notify"])


if __name__ == "__main__":
    unittest.main()
