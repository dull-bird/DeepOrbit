import datetime as dt
import tempfile
import unittest
from pathlib import Path

from deeporbit.config import load_config
from deeporbit.nltime import parse as nl_parse
from deeporbit.tasks import add_task, complete_task, parse_tasks, progress, update_task
from deeporbit.vault import initialize

NOW = dt.datetime(2026, 7, 24, 12, 0)  # Friday


class NlTimeTests(unittest.TestCase):
    def test_tonight_with_chinese_hour(self):
        r = nl_parse("今晚七点跟丽丽吃饭", now=NOW)
        self.assertEqual((r["date"], r["time"], r["text"]), ("2026-07-24", "19:00", "跟丽丽吃饭"))

    def test_tomorrow_morning(self):
        r = nl_parse("明天上午10点看医生", now=NOW)
        self.assertEqual((r["date"], r["time"], r["text"]), ("2026-07-25", "10:00", "看医生"))

    def test_weekly_recurrence(self):
        r = nl_parse("每周五写周报", now=NOW)
        self.assertEqual(r["recurrence"], "every week on friday")
        self.assertEqual(r["date"], "2026-07-24")
        self.assertEqual(r["text"], "写周报")

    def test_days_later_chinese_numeral(self):
        r = nl_parse("三天后交报告", now=NOW)
        self.assertEqual((r["date"], r["text"]), ("2026-07-27", "交报告"))

    def test_hours_later(self):
        r = nl_parse("两小时后喝水", now=NOW)
        self.assertEqual((r["date"], r["time"]), ("2026-07-24", "14:00"))

    def test_afternoon_clock_only(self):
        r = nl_parse("下午3点开会", now=NOW)
        self.assertEqual((r["date"], r["time"]), ("2026-07-24", "15:00"))

    def test_month_day_rolls_to_next_year(self):
        r = nl_parse("5月3日领证", now=NOW)
        self.assertEqual(r["date"], "2027-05-03")

    def test_evening_half_hour(self):
        r = nl_parse("明晚8点半看电影", now=NOW)
        self.assertEqual((r["date"], r["time"]), ("2026-07-25", "20:30"))

    def test_english_tomorrow_pm(self):
        r = nl_parse("Buy milk tomorrow at 7pm", now=NOW)
        self.assertEqual((r["date"], r["time"]), ("2026-07-25", "19:00"))
        self.assertEqual(r["text"], "Buy milk")

    def test_english_weekly(self):
        r = nl_parse("gym every friday", now=NOW)
        self.assertEqual(r["recurrence"], "every week on friday")

    def test_priority_shorthand(self):
        r = nl_parse("!1 重要任务", now=NOW)
        self.assertEqual((r["priority"], r["text"]), ("high", "重要任务"))

    def test_plain_text_untouched(self):
        r = nl_parse("随便记一个想法", now=NOW)
        self.assertEqual((r["date"], r["time"], r["text"]), (None, None, "随便记一个想法"))


class ExtendedTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        initialize(self.root)
        self.config = load_config(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_full_marker_round_trip(self):
        task = add_task(
            self.config,
            "准备季度评审 #project/工作 ![[90_Attachments/data.pdf]]",
            due="2026-07-28",
            time="19:00",
            priority="high",
            recurrence="every week on Friday",
        )
        parsed = parse_tasks(self.config)[0]
        self.assertEqual(parsed.id, task.id)
        self.assertEqual(parsed.due, "2026-07-28")
        self.assertEqual(parsed.time, "19:00")
        self.assertEqual(parsed.priority, "high")
        self.assertEqual(parsed.recurrence, "every week on Friday")
        self.assertEqual(parsed.created, dt.date.today().isoformat())
        self.assertIn("project/工作", parsed.tags)
        self.assertEqual(parsed.attachments, ["90_Attachments/data.pdf"])
        # render(parse) must be byte-stable on re-parse (no marker loss)
        line = self.root.joinpath("00_Inbox", "Todos.md").read_text(encoding="utf-8").splitlines()[-1]
        for marker in ("⏫", "🔁 every week on Friday", "📅 2026-07-28", "⏰ 19:00", "➕", "^do-"):
            self.assertIn(marker, line)

    def test_complete_writes_done_date(self):
        task = add_task(self.config, "finish", due="2026-07-24")
        done = complete_task(self.config, task.id)
        self.assertEqual(done.done_date, dt.date.today().isoformat())
        parsed = parse_tasks(self.config)[0]
        self.assertEqual(parsed.status, "done")
        self.assertEqual(parsed.done_date, dt.date.today().isoformat())

    def test_update_task_snooze(self):
        task = add_task(self.config, "call", due="2026-07-24", time="19:00")
        update_task(self.config, task.id, time="19:30")
        self.assertEqual(parse_tasks(self.config)[0].time, "19:30")

    def test_subtasks_and_progress(self):
        parent = add_task(self.config, "大任务", due="2026-07-30")
        child1 = add_task(self.config, "子任务1", parent_line=parent.line)
        child2 = add_task(self.config, "子任务2", parent_line=parent.line)
        complete_task(self.config, child1.id)
        tasks = parse_tasks(self.config)
        by_id = {t.id: t for t in tasks}
        self.assertEqual(by_id[child1.id].parent, parent.id)
        self.assertEqual(by_id[child2.id].parent, parent.id)
        stats = progress(tasks)
        self.assertEqual(stats["subtasks"][parent.id], {"done": 1, "total": 2})

    def test_bare_checkbox_zero_migration(self):
        inbox = self.root / "00_Inbox" / "todo.md"
        inbox.write_text("# todo\n\n- [ ] 手写裸任务\n- [x] 已完成的事\n", encoding="utf-8")
        tasks = {t.text: t for t in parse_tasks(self.config)}
        self.assertIn("手写裸任务", tasks)
        self.assertTrue(tasks["手写裸任务"].id.startswith("legacy-"))
        self.assertTrue(tasks["已完成的事"].done)


if __name__ == "__main__":
    unittest.main()
