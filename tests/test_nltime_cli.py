"""CLI-level tests: NL todo add echo, todo set/attach, list views, cron --at, timed ICS."""

import datetime as dt
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from deeporbit.calendar import export_ics
from deeporbit.cli import main
from deeporbit.config import load_config
from deeporbit.cron import run_due
from deeporbit.tasks import parse_tasks
from deeporbit.vault import initialize


def cli(*argv: str) -> tuple[int, dict | list]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(list(argv))
    return code, json.loads(buffer.getvalue())


def cli_text(*argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(list(argv))
    return code, buffer.getvalue()


class TodoCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(Path(self.temp.name) / "config")})
        self.env.start()
        self.vault = Path(self.temp.name) / "vault"
        initialize(self.vault)
        self.config = load_config(self.vault)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_nl_add_echoes_parse(self):
        code, out = cli("--vault", str(self.vault), "todo", "add", "今晚七点跟丽丽吃饭")
        today = dt.date.today().isoformat()
        self.assertEqual(code, 0)
        self.assertEqual(out["due"], today)
        self.assertEqual(out["time"], "19:00")
        self.assertTrue(out["text"].startswith("跟丽丽吃饭"))
        self.assertEqual(out["parsed"]["text"], "跟丽丽吃饭")
        self.assertEqual(out["parsed"]["date"], today)
        self.assertIn("今晚七点", out["parsed"]["matched"])
        line = (self.vault / "00_Inbox" / "Todos.md").read_text(encoding="utf-8")
        self.assertIn(f"📅 {today}", line)
        self.assertIn("⏰ 19:00", line)

    def test_explicit_flags_override_nl_parse(self):
        tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
        code, out = cli(
            "--vault", str(self.vault), "todo", "add", "明天开会",
            "--due", "2026-08-01", "--time", "09:30", "--priority", "high",
        )
        self.assertEqual(code, 0)
        self.assertEqual(out["due"], "2026-08-01")
        self.assertEqual(out["time"], "09:30")
        self.assertEqual(out["priority"], "high")
        self.assertEqual(out["parsed"]["date"], tomorrow)  # NL echo kept for confirmation

    def test_parent_by_id_creates_subtask(self):
        _, parent = cli("--vault", str(self.vault), "todo", "add", "写周报")
        code, child = cli("--vault", str(self.vault), "todo", "add", "整理数据", "--parent", parent["id"])
        self.assertEqual(code, 0)
        self.assertEqual(child["indent"], 1)
        stored = {t.id: t for t in parse_tasks(self.config)}
        self.assertEqual(stored[child["id"]].parent, parent["id"])

    def test_todo_set_updates_fields(self):
        _, task = cli("--vault", str(self.vault), "todo", "add", "写周报")
        code, out = cli(
            "--vault", str(self.vault), "todo", "set", task["id"],
            "--status", "doing", "--due", "2026-07-31", "--time", "10:00", "--priority", "low", "--recur", "every week on Friday",
        )
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "doing")
        self.assertEqual((out["due"], out["time"], out["priority"]), ("2026-07-31", "10:00", "low"))
        self.assertEqual(out["recurrence"], "every week on Friday")
        stored = parse_tasks(self.config)[0]
        self.assertEqual(stored.status, "doing")

    def test_todo_set_without_fields_fails(self):
        _, task = cli("--vault", str(self.vault), "todo", "add", "写周报")
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = main(["--vault", str(self.vault), "todo", "set", task["id"]])
        self.assertEqual(code, 1)

    def test_attach_copies_and_renames_conflicts(self):
        _, task = cli("--vault", str(self.vault), "todo", "add", "体检报告解读")
        source = Path(self.temp.name) / "体检报告.pdf"
        source.write_text("payload", encoding="utf-8")
        code, first = cli("--vault", str(self.vault), "todo", "attach", task["id"], str(source))
        self.assertEqual(code, 0)
        self.assertEqual(first["path"], "90_Attachments/体检报告.pdf")
        self.assertTrue((self.vault / "90_Attachments" / "体检报告.pdf").is_file())
        self.assertIn("![[90_Attachments/体检报告.pdf]]", first["task"]["text"])
        code, second = cli("--vault", str(self.vault), "todo", "attach", task["id"], str(source))
        self.assertEqual(code, 0)
        self.assertNotEqual(second["path"], first["path"])  # timestamp suffix on conflict
        self.assertTrue(second["path"].startswith("90_Attachments/体检报告-"))
        self.assertTrue((self.vault / second["path"]).is_file())

    def test_list_views(self):
        _, a = cli("--vault", str(self.vault), "todo", "add", "今天的事", "--due", dt.date.today().isoformat())
        _, b = cli("--vault", str(self.vault), "todo", "add", "项目任务 #project/工作", "--due", "2020-01-01")
        cli("--vault", str(self.vault), "todo", "set", b["id"], "--status", "doing")
        _, c = cli("--vault", str(self.vault), "todo", "add", "已完成的事")
        cli("--vault", str(self.vault), "todo", "done", c["id"])
        _, parent = cli("--vault", str(self.vault), "todo", "add", "写周报")
        cli("--vault", str(self.vault), "todo", "add", "整理数据", "--parent", parent["id"])

        code, flat = cli("--vault", str(self.vault), "todo", "list")
        self.assertIsInstance(flat, list)  # flat stays the backward-compatible default
        code, board = cli("--vault", str(self.vault), "todo", "list", "--view", "board")
        self.assertEqual(len(board["doing"]), 1)
        self.assertEqual(len(board["done"]), 1)
        code, timeline = cli("--vault", str(self.vault), "todo", "list", "--view", "timeline")
        self.assertEqual([t["id"] for t in timeline["today"]], [a["id"]])
        self.assertEqual([t["id"] for t in timeline["overdue"]], [b["id"]])
        self.assertTrue(timeline["unscheduled"])
        code, progress = cli("--vault", str(self.vault), "todo", "list", "--view", "progress")
        self.assertEqual(progress["projects"]["工作"], {"done": 0, "total": 1})
        self.assertEqual(progress["subtasks"][parent["id"]], {"done": 0, "total": 1})

    def test_list_markdown(self):
        cli("--vault", str(self.vault), "todo", "add", "项目任务 #project/工作")
        code, board_md = cli_text("--vault", str(self.vault), "todo", "list", "--view", "board", "--md")
        self.assertEqual(code, 0)
        self.assertIn("## todo", board_md)
        self.assertIn("| ID | 状态 | 内容 |", board_md)
        code, progress_md = cli_text("--vault", str(self.vault), "todo", "list", "--view", "progress", "--md")
        self.assertIn("## 项目进度", progress_md)
        self.assertIn("| 工作 |", progress_md)


class CronAtTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(Path(self.temp.name) / "config")})
        self.env.start()
        self.vault = Path(self.temp.name) / "vault"
        initialize(self.vault)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_at_job_fires_once_then_auto_disables(self):
        code, job = cli("--vault", str(self.vault), "cron", "add", "weekly-report", "提醒我写周报", "--at", "2026-07-25T19:00")
        self.assertEqual(code, 0)
        self.assertEqual(job["at"], "2026-07-25T19:00:00")
        self.assertIsNone(job["every_hours"])
        later = dt.datetime(2026, 7, 25, 20, 0, tzinfo=dt.timezone.utc)
        due = run_due(later)
        self.assertEqual([j.name for j in due], ["weekly-report"])
        self.assertEqual(run_due(later), [])  # one-shot: never fires again
        code, jobs = cli("--vault", str(self.vault), "cron", "list")
        self.assertEqual(jobs[0]["enabled"], False)  # record kept for audit
        self.assertEqual(jobs[0]["at"], "2026-07-25T19:00:00")

    def test_at_and_every_are_mutually_exclusive(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--vault", str(self.vault), "cron", "add", "x", "y", "--every", "daily", "--at", "2026-07-25T19:00"])


class TimedIcsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp.name) / "vault"
        initialize(self.vault)
        self.config = load_config(self.vault)

    def tearDown(self):
        self.temp.cleanup()

    def test_timed_task_exports_datetime_event_with_10min_alarm(self):
        cli("--vault", str(self.vault), "todo", "add", "跟丽丽吃饭", "--due", "2026-07-28", "--time", "19:00")
        output, count = export_ics(self.config)
        text = output.read_text(encoding="utf-8")
        self.assertEqual(count, 1)
        self.assertIn("DTSTART;VALUE=DATE-TIME:20260728T190000", text)
        self.assertIn("DTEND;VALUE=DATE-TIME:20260728T200000", text)  # +1h block
        self.assertIn("TRIGGER;RELATED=START:-PT10M", text)
        self.assertNotIn("PT9H", text)


if __name__ == "__main__":
    unittest.main()
