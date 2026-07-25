import datetime as dt
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deeporbit import remind
from deeporbit.config import load_config
from deeporbit.tasks import add_task, complete_task, parse_tasks
from deeporbit.vault import initialize

NOW = dt.datetime(2026, 7, 25, 12, 0)


class RemindCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(Path(self.temp.name) / "config")})
        self.env.start()
        self.root = Path(self.temp.name) / "vault"
        initialize(self.root)
        self.config = load_config(self.root)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_due_judgement(self):
        morning = add_task(self.config, "晨会", due="2026-07-25", time="08:00")
        evening = add_task(self.config, "晚饭", due="2026-07-25", time="20:00")
        overdue = add_task(self.config, "补作业", due="2026-07-20")
        add_task(self.config, "随便想想")  # no due date
        done = add_task(self.config, "已完成", due="2026-07-25", time="08:00")
        complete_task(self.config, done.id)
        ids = [task.id for task in remind.check(self.config, NOW)]
        self.assertEqual(ids, [morning.id, overdue.id])  # future time and done excluded
        self.assertNotIn(evening.id, ids)

    def test_mark_reminded_is_idempotent(self):
        task = add_task(self.config, "晨会", due="2026-07-25", time="08:00")
        remind.mark_reminded(task.id, NOW)
        self.assertEqual(remind.check(self.config, NOW), [])

    def test_snooze_suppresses_then_expires(self):
        task = add_task(self.config, "晨会", due="2026-07-25", time="08:00")
        remind.snooze(task.id, minutes=10, now=NOW)
        self.assertEqual(remind.check(self.config, NOW), [])
        later = NOW + dt.timedelta(minutes=11)
        self.assertEqual([t.id for t in remind.check(self.config, later)], [task.id])

    def test_corrupt_state_file_is_treated_as_empty(self):
        task = add_task(self.config, "晨会", due="2026-07-25", time="08:00")
        path = remind.state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json {{{", encoding="utf-8")
        self.assertEqual([t.id for t in remind.check(self.config, NOW)], [task.id])


class RemindDeliverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(Path(self.temp.name) / "config")})
        self.env.start()
        self.root = Path(self.temp.name) / "vault"
        initialize(self.root)
        self.config = load_config(self.root)
        self.task = add_task(self.config, "跟丽丽吃饭", due="2026-07-25", time="19:00")

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def _proc(self, stdout="", returncode=0):
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")

    def test_osascript_fallback_uses_argv_list_and_marks_reminded(self):
        with mock.patch("shutil.which", return_value=None), \
                mock.patch("deeporbit.remind.subprocess.run", return_value=self._proc()) as run:
            result = remind.deliver(self.config, self.task)
        self.assertEqual(result["channel"], "osascript")
        self.assertEqual(result["action"], "notified")
        argv = run.call_args.args[0]
        self.assertEqual(argv[:2], ["osascript", "-e"])
        self.assertIn("跟丽丽吃饭", argv[2])
        self.assertEqual(remind.check(self.config, NOW), [])  # idempotent after delivery

    def test_alerter_done_action_completes_task(self):
        payload = json.dumps({"activationType": "actionClicked", "activationValue": "完成"})
        with mock.patch("shutil.which", return_value="/usr/local/bin/alerter"), \
                mock.patch("deeporbit.remind.subprocess.run", return_value=self._proc(stdout=payload)):
            result = remind.deliver(self.config, self.task)
        self.assertEqual((result["channel"], result["action"]), ("alerter", "done"))
        self.assertEqual(parse_tasks(self.config)[0].status, "done")

    def test_alerter_snooze_action_snoozes_ten_minutes(self):
        payload = json.dumps({"activationType": "actionClicked", "activationValue": "稍后"})
        with mock.patch("shutil.which", return_value="/usr/local/bin/alerter"), \
                mock.patch("deeporbit.remind.subprocess.run", return_value=self._proc(stdout=payload)):
            result = remind.deliver(self.config, self.task)
        self.assertEqual(result["action"], "snoozed")
        self.assertEqual(remind.check(self.config, dt.datetime.now()), [])
        task = parse_tasks(self.config)[0]
        self.assertEqual(task.status, "todo")  # snooze does not complete


class RemindInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "vault"
        initialize(self.root)
        self.config = load_config(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_install_writes_plist_and_loads(self):
        agents = Path(self.temp.name) / "LaunchAgents"
        ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with mock.patch("shutil.which", return_value="/usr/local/bin/deeporbit"), \
                mock.patch("deeporbit.remind.subprocess.run", return_value=ok) as run:
            result = remind.install(self.config, base_dir=agents)
        self.assertTrue(result["installed"])
        self.assertTrue(result["loaded"])
        self.assertEqual(result["start_interval"], 60)
        plist = (agents / "com.deeporbit.remind.plist").read_text(encoding="utf-8")
        self.assertIn("<integer>60</integer>", plist)
        self.assertIn("/usr/local/bin/deeporbit", plist)
        self.assertIn(str(self.config.vault), plist)
        self.assertIn("launchctl unload -w", result["uninstall"])
        self.assertEqual(run.call_args.args[0][:2], ["launchctl", "load"])

    def test_install_survives_unwritable_path(self):
        blocked = Path(self.temp.name) / "missing" / "deep" / "LaunchAgents"
        with mock.patch.object(Path, "mkdir", side_effect=OSError("permission denied")):
            result = remind.install(self.config, base_dir=blocked)
        self.assertFalse(result["installed"])
        self.assertIn("manual", result)  # guidance instead of a crash


if __name__ == "__main__":
    unittest.main()
