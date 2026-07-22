import datetime as dt
import tempfile
import unittest
from pathlib import Path
from deeporbit.calendar import export_ics
from deeporbit.config import load_config
from deeporbit.errors import PrivacyError, TaskNotFoundError
from deeporbit.tasks import add_task, agenda, complete_task, parse_tasks
from deeporbit.vault import initialize


class TaskCalendarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        initialize(self.root)
        self.config = load_config(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_task_lifecycle_and_agenda(self):
        today = dt.date(2026, 7, 13)
        task = add_task(self.config, "Ship DeepOrbit", due="2026-07-13")
        self.assertTrue(task.id.startswith("202"))
        self.assertEqual(parse_tasks(self.config)[0].id, task.id)
        self.assertEqual(agenda(self.config, today=today)["today"][0].id, task.id)
        self.assertTrue(complete_task(self.config, task.id).done)
        self.assertEqual(agenda(self.config, today=today)["done"][0].id, task.id)

    def test_missing_task_is_explicit(self):
        with self.assertRaises(TaskNotFoundError):
            complete_task(self.config, "missing")

    def test_ics_is_idempotent_and_has_alarm(self):
        task = add_task(self.config, "Review architecture", scheduled="2026-07-14")
        output, count = export_ics(self.config)
        first = output.read_text(encoding="utf-8")
        export_ics(self.config)
        self.assertEqual(first, output.read_text(encoding="utf-8"))
        self.assertEqual(count, 1)
        self.assertIn(f"UID:{task.id}@deeporbit.local", first)
        self.assertIn("BEGIN:VALARM", first)
        self.assertIn("TRIGGER;RELATED=START:PT9H", first)

    def test_ics_privacy_mode_redacts_sensitive_fields(self):
        add_task(self.config, "Email jane.doe@example.com about 555-123-4567", due="2026-07-14")
        output, count = export_ics(self.config, privacy_mode="redact")
        text = output.read_text(encoding="utf-8")
        self.assertEqual(count, 1)
        self.assertNotIn("jane.doe@example.com", text)
        self.assertNotIn("555-123-4567", text)
        self.assertIn("<EMAIL>", text)
        self.assertIn("<PHONE>", text)
        self.assertIn("<VAULT_PATH>", text)

    def test_ics_privacy_mode_blocks_sensitive_fields(self):
        add_task(self.config, "Email jane.doe@example.com", scheduled="2026-07-14")
        with self.assertRaises(PrivacyError):
            export_ics(self.config, privacy_mode="block")


if __name__ == "__main__":
    unittest.main()
