"""Meaningful safety checks use isolated temp vaults, never the user's vault."""
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("human_loop", Path(__file__).with_name("human_loop.py"))
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)

FIELDS = ["Main question:", "Action and result:", "What I can explain or still do not understand:",
          "First step tomorrow:", "Life and energy:"]
HOST = "sha256:test-host-a"
DEVICE = "test-device-a"


class HumanLoopTests(unittest.TestCase):
    def setUp(self):
        try:
            self.zone = loop.ZoneInfo("Asia/Hong_Kong")
        except KeyError:
            self.skipTest("IANA timezone database unavailable; install tzdata to run optional Human Loop tests")
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.config = self.root / "local.json"
        self.write_json(self.vault / "deeporbit.json", {"vault_id": "test-vault",
                                                       "directories": {"system": "99_System"}})
        self.settings = {
            "schema_version": 1, "vault_id": "test-vault", "enabled": True,
            "scheduler_owner": DEVICE,
            "timezone": "Asia/Hong_Kong", "trial": {"start": "2026-01-05", "end": "2026-01-18"},
            "paths": {"daily_template": "99_System/Templates/HumanLoopTemplate.md",
                      "daily_dir": "10_Diary/HumanLoop", "agent_dir": "10_Diary/HumanLoop/Agent",
                      "protocol": "99_System/DeepOrbit/HumanLoopProtocol.md"},
            "required_fields": FIELDS,
            "schedule": {
                "morning": {"time": "09:00", "weekdays": list(range(7)), "window_minutes": 25},
                "evening": {"time": "20:00", "weekdays": list(range(6)), "window_minutes": 30},
                "weekly": {"time": "20:00", "weekdays": [6], "window_minutes": 30}}}
        self.shared = self.vault / "99_System/DeepOrbit/human-loop.json"
        self.write_json(self.shared, self.settings)
        self.local = {"schema_version": 1, "vault_id": "test-vault", "vault_path": str(self.vault),
                      "role": "primary", "host_id": HOST, "device_id": DEVICE}
        self.write_json(self.config, self.local)
        self.template = self.vault / self.settings["paths"]["daily_template"]
        self.template.parent.mkdir(parents=True)
        self.template.write_text("---\nauthor: ai\ncreated: {{date}}\n---\n# {{date}} 周{{weekday}}\n"
                                 + self.block(), encoding="utf-8")
        self.day = dt.date(2026, 1, 5)
        self.now = dt.datetime(2026, 1, 5, 9, 5, tzinfo=self.zone)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def block(values=None, state="待反馈"):
        values = values or [""] * 5
        return loop.START + "\n- 本人状态：" + state + "\n" + "\n".join(
            "- " + field + value for field, value in zip(FIELDS, values)) + "\n" + loop.END + "\n"

    def ctx(self, host=HOST):
        return loop.context(self.config, current_host=host)

    def write_daily(self, content):
        path = loop.daily_path(self.ctx(), self.day)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_only_bound_primary_runs(self):
        self.assertEqual(loop.guard(self.ctx("different-host"), "morning", self.now)["reason"], "host_mismatch")
        self.local["role"] = "secondary"
        self.write_json(self.config, self.local)
        self.assertEqual(loop.prepare(self.ctx(), "morning", self.now)["reason"], "not_primary")
        self.assertFalse((self.vault / "10_Diary").exists())

    def test_relocated_vault_same_id_works_but_wrong_id_refused(self):
        relocated = self.root / "relocated-vault"
        shutil.move(self.vault, relocated)
        self.local["vault_path"] = str(relocated)
        self.write_json(self.config, self.local)
        self.assertTrue(loop.guard(self.ctx(), "morning", self.now)["allowed"])
        self.write_json(relocated / "deeporbit.json", {"vault_id": "other"})
        with self.assertRaises(loop.LoopError) as caught:
            self.ctx()
        self.assertEqual(caught.exception.code, "vault_id_mismatch")

    def test_schema_v3_resolves_mapped_system_directory(self):
        renamed = self.vault / "SystemNotes"
        shutil.move(self.vault / "99_System", renamed)
        for key in ("daily_template", "protocol"):
            self.settings["paths"][key] = self.settings["paths"][key].replace("99_System/", "SystemNotes/")
        self.shared = renamed / "DeepOrbit/human-loop.json"
        self.write_json(self.shared, self.settings)
        self.write_json(self.vault / "deeporbit.json", {
            "schema_version": 3, "vault_id": "test-vault",
            "directories": {"system": {"path": "SystemNotes", "title": "System notes"}}})
        ctx = self.ctx()
        self.assertTrue(loop.guard(ctx, "morning", self.now)["allowed"])
        self.assertTrue(loop.prepare(ctx, "morning", self.now)["created"])

    def test_malformed_system_mapping_returns_structured_error(self):
        invalid = [None, [], "SystemNotes", {"system": 17}, {"system": None},
                   {"system": ""}, {"system": {}}, {"system": {"path": 17}}]
        for directories in invalid:
            with self.subTest(directories=directories):
                self.write_json(self.vault / "deeporbit.json", {
                    "vault_id": "test-vault", "directories": directories})
                with self.assertRaises(loop.LoopError) as caught:
                    self.ctx()
                self.assertEqual(caught.exception.code, "vault_config_invalid")
                with patch.object(sys, "argv", ["helper", "--config", str(self.config), "status"]):
                    with patch("builtins.print") as output:
                        self.assertEqual(loop.main(), 2)
                self.assertEqual(json.loads(output.call_args.args[0])["error"], "vault_config_invalid")

    def test_all_schedules_require_minute_precision_even_when_not_current_mode(self):
        for clock in ("09:00:30", "9:00", "09:00+08:00", "24:00", "09:60"):
            with self.subTest(clock=clock):
                self.settings["schedule"]["weekly"]["time"] = clock
                self.write_json(self.shared, self.settings)
                with self.assertRaises(loop.LoopError) as caught:
                    self.ctx()
                self.assertEqual(caught.exception.code, "schedule_invalid")

    def test_weekdays_require_nonempty_list_of_integers(self):
        for weekdays in ([3.0], [True], [-1], [7], [], 3, "3"):
            with self.subTest(weekdays=weekdays):
                self.settings["schedule"]["morning"]["weekdays"] = weekdays
                self.write_json(self.shared, self.settings)
                with self.assertRaises(loop.LoopError) as caught:
                    self.ctx()
                self.assertEqual(caught.exception.code, "schedule_invalid")

    def test_windows_require_finite_numeric_duration_and_exclude_booleans(self):
        for minutes in (True, "25", 0, -1, 181, float("nan"), float("inf"), 10 ** 1000):
            with self.subTest(minutes=minutes):
                self.settings["schedule"]["evening"]["window_minutes"] = minutes
                self.write_json(self.shared, self.settings)
                with self.assertRaises(loop.LoopError) as caught:
                    self.ctx()
                self.assertEqual(caught.exception.code, "schedule_invalid")

    def test_two_locally_primary_devices_have_one_synced_owner(self):
        self.assertTrue(loop.guard(self.ctx(), "morning", self.now)["allowed"])
        self.local["device_id"] = "test-device-b"
        self.write_json(self.config, self.local)
        self.assertEqual(loop.prepare(self.ctx(), "morning", self.now)["reason"], "not_owner")
        self.assertFalse((self.vault / "10_Diary").exists())

    def test_trial_end_inclusive_and_expiration_no_catchup(self):
        ctx = self.ctx()
        last = self.now.replace(day=18)
        self.assertTrue(loop.guard(ctx, "morning", last)["allowed"])
        expired = self.now.replace(day=19)
        self.assertEqual(loop.guard(ctx, "morning", expired)["reason"], "outside_trial")
        early = self.now.replace(hour=8, minute=59)
        self.assertEqual(loop.guard(ctx, "morning", early)["reason"], "outside_window")
        late = self.now.replace(minute=25)
        self.assertEqual(loop.guard(ctx, "morning", late)["reason"], "outside_window")

    def test_sunday_weekly_replaces_evening(self):
        sunday = self.now.replace(day=11, hour=20, minute=0)
        self.assertEqual(loop.guard(self.ctx(), "evening", sunday)["reason"], "wrong_weekday")
        self.assertTrue(loop.guard(self.ctx(), "weekly", sunday)["allowed"])
        self.assertEqual(loop.guard(self.ctx(), "weekly", sunday.replace(hour=20, minute=30))["reason"], "outside_window")

    def test_morning_exclusive_creation_and_all_existing_bytes_preserved(self):
        ctx = self.ctx()
        result = loop.prepare(ctx, "morning", self.now)
        self.assertTrue(result["created"])
        self.assertEqual(result["feedback"]["state"], "awaiting")
        path = loop.daily_path(ctx, self.day)
        self.assertIn("2026-01-05", path.read_text())
        human_bytes = b"\xef\xbb\xbfHuman original\r\nwith exact bytes\x00\n"
        path.write_bytes(human_bytes)
        self.assertFalse(loop.prepare(ctx, "morning", self.now)["created"])
        self.assertEqual(path.read_bytes(), human_bytes)
        self.assertFalse((path.parent / "Agent").exists())

    def test_new_daily_metadata_uses_current_day_and_keeps_template_unchanged(self):
        original = ("---\ntype: template\nauthor: mixed\ncreated: 2026-01-04\n"
                    "updated: 2026-01-04\nprivacy_level: public\ntags: [HumanLoop]\n---\n\n"
                    "# {{date}}\n" + self.block()).encode("utf-8")
        self.template.write_bytes(original)
        ctx = self.ctx()
        self.assertTrue(loop.prepare(ctx, "morning", self.now)["created"])
        content = loop.daily_path(ctx, self.day).read_text()
        front = content.split("---", 2)[1]
        for property in ("type: daily-feedback", "author: ai", "date: 2026-01-05",
                         "created: 2026-01-05", "updated: 2026-01-05", "privacy_level: critical"):
            self.assertIn(property, front)
        self.assertNotIn("2026-01-04", front)
        self.assertNotIn("author: mixed", front)
        self.assertIn("tags: [HumanLoop]", front)
        self.assertNotIn("---\n\n", content)
        self.assertEqual(self.template.read_bytes(), original)

    def test_template_links_follow_configured_daily_and_agent_directories(self):
        self.settings["paths"]["daily_dir"] = "Journal/DailyPractice"
        self.settings["paths"]["agent_dir"] = "Journal/DailyPractice/Reviews"
        self.write_json(self.shared, self.settings)
        content = ("---\ntype: template\n---\n# {{date}}\n"
                   "Daily: [[{{daily_dir}}/{{date}}]]\n"
                   "Review: [[{{agent_dir}}/{{date}}-morning]]\n" + self.block())
        self.template.write_text(content, encoding="utf-8")
        ctx = self.ctx()
        self.assertTrue(loop.prepare(ctx, "morning", self.now)["created"])
        rendered = loop.daily_path(ctx, self.day).read_text()
        self.assertIn("[[Journal/DailyPractice/2026-01-05]]", rendered)
        self.assertIn("[[Journal/DailyPractice/Reviews/2026-01-05-morning]]", rendered)
        self.assertNotIn("{{", rendered)
        self.assertEqual(self.template.read_text(), content)

    def test_concurrent_creator_not_overwritten(self):
        ctx = self.ctx()
        path = loop.daily_path(ctx, self.day)
        real_open = os.open
        def competing_open(file, flags, mode):
            Path(file).write_text("competing human content", encoding="utf-8")
            return real_open(file, flags, mode)
        with patch.object(loop.os, "open", side_effect=competing_open):
            self.assertFalse(loop.prepare(ctx, "morning", self.now)["created"])
        self.assertEqual(path.read_text(), "competing human content")

    def test_evening_does_not_create_diary(self):
        now = self.now.replace(hour=20, minute=5)
        result = loop.prepare(self.ctx(), "evening", now)
        self.assertEqual(result["feedback"]["state"], "missing")
        self.assertFalse((self.vault / "10_Diary").exists())

    def test_template_and_ai_text_do_not_count_as_human_feedback(self):
        path = self.write_daily(self.block(["待填写", "尚未收到反馈。", "{{answer}}", "[填写这里]", "..."])
                                + "\nAI报告：今天全部完成，睡了八小时。\n")
        result = loop.feedback(path, FIELDS)
        self.assertEqual(result["state"], "awaiting")
        self.assertEqual(result["filled_count"], 0)
        path.write_text("Agent summary\n- " + FIELDS[0] + "这是AI的内容", encoding="utf-8")
        self.assertEqual(loop.feedback(path, FIELDS)["reason"], "malformed_user_block")

    def test_legitimate_obsidian_links_count_as_human_input(self):
        values = ["[[Main Question]]", "[[Result Note|Observed result]]", "[[Learning#My explanation]]",
                  "[[Next Step]]", "[An actual observation]"]
        path = self.write_daily(self.block(values))
        result = loop.feedback(path, FIELDS)
        self.assertEqual(result["state"], "recorded")
        self.assertEqual(result["filled_count"], 5)
        self.assertNotIn("Observed result", json.dumps(result))
        for placeholder in ("[填写这里]", "[fill in here]", "[Pending]", "{{answer}}"):
            with self.subTest(placeholder=placeholder):
                self.assertFalse(loop.substantive(placeholder))

    def test_partial_feedback_unknown_life_and_explicit_state_not_completion(self):
        path = self.write_daily(self.block(["读完一页", "", "", "", "未知"], state="休息"))
        result = loop.feedback(path, FIELDS)
        self.assertEqual(result["state"], "partial")
        self.assertEqual(result["filled_count"], 2)
        self.assertEqual(result["explicit_user_state"], "休息")
        path.write_text(self.block(["问题", "没有推进", "仍不懂", "读一页", "未知"], state="部分"), encoding="utf-8")
        result = loop.feedback(path, FIELDS)
        self.assertEqual(result["state"], "recorded")
        self.assertEqual(result["explicit_user_state"], "部分")
        self.assertNotIn("没有推进", json.dumps(result, ensure_ascii=False))

    def test_duplicate_fields_and_markers_fail_closed(self):
        path = self.write_daily(self.block(["真实输入"] * 5).replace(loop.END, "- " + FIELDS[0] + "重复\n" + loop.END))
        self.assertEqual(loop.feedback(path, FIELDS)["reason"], "duplicate_user_fields")
        path.write_text(loop.START + self.block(["真实输入"] * 5), encoding="utf-8")
        self.assertEqual(loop.feedback(path, FIELDS)["state"], "awaiting")

    def test_multiline_human_fields_count_until_next_prefix_or_heading(self):
        path = self.write_daily(self.block(["\n用自己的话写的问题", "\n- 实际推进：一页\n  留下一个问题",
                                            "\n仍不懂这个概念", "\n明天复述一次", "\n未知"]))
        result = loop.feedback(path, FIELDS)
        self.assertEqual(result["state"], "recorded")
        self.assertNotIn("实际推进", json.dumps(result, ensure_ascii=False))
        path.write_text(self.block(["", "", "", "", "\n## Agent整理\n不能计作本人输入"]), encoding="utf-8")
        self.assertEqual(loop.feedback(path, FIELDS)["state"], "awaiting")

    def test_dry_run_reads_metadata_without_writes_or_records_in_output(self):
        result = loop.prepare(self.ctx(), "morning", self.now.replace(hour=15), dry_run=True)
        self.assertTrue(result["would_create"])
        self.assertFalse(result["created"])
        self.assertFalse((self.vault / "10_Diary").exists())
        self.assertEqual(len(result["recent_days"]), 7)
        self.assertIn("protocol", result["reference_paths"])
        self.assertEqual(result["agent_path"], "10_Diary/HumanLoop/Agent/2026-01-05-morning.md")

    def test_disabled_and_unavailable_vault_fail_closed(self):
        self.settings["enabled"] = False
        self.write_json(self.shared, self.settings)
        self.assertEqual(loop.prepare(self.ctx(), "morning", self.now)["reason"], "disabled")
        shutil.rmtree(self.vault)
        with self.assertRaises(loop.LoopError) as caught:
            self.ctx()
        self.assertEqual(caught.exception.code, "vault_unavailable")

    def test_escaped_path_refused(self):
        self.settings["paths"]["daily_dir"] = "../../outside"
        self.write_json(self.shared, self.settings)
        with self.assertRaises(loop.LoopError) as caught:
            self.ctx()
        self.assertEqual(caught.exception.code, "unsafe_path")

    def test_symlink_to_directory_outside_vault_is_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.vault / "10_Diary").symlink_to(outside, target_is_directory=True)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) in (5, 1314):
                self.skipTest("Windows requires symlink privileges for this containment check")
            raise
        with self.assertRaises(loop.LoopError) as caught:
            self.ctx()
        self.assertEqual(caught.exception.code, "unsafe_path")
        self.assertEqual(list(outside.iterdir()), [])

    def test_dated_agent_report_symlink_outside_vault_is_refused_before_prepare(self):
        ctx = self.ctx()
        outside = self.root / "outside-note.md"
        original = b"An unrelated note must remain unchanged.\n"
        outside.write_bytes(original)
        report = self.vault / self.settings["paths"]["agent_dir"] / (self.day.isoformat() + "-morning.md")
        report.parent.mkdir(parents=True)
        try:
            report.symlink_to(outside)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) in (5, 1314):
                self.skipTest("Windows requires symlink privileges for this containment check")
            raise
        with self.assertRaises(loop.LoopError) as caught:
            loop.prepare(ctx, "morning", self.now)
        self.assertEqual(caught.exception.code, "unsafe_path")
        self.assertFalse(loop.daily_path(ctx, self.day).exists())
        self.assertEqual(outside.read_bytes(), original)

    def test_unsafe_reference_paths_refused(self):
        for key in ("protocol", "plan", "source"):
            with self.subTest(key=key):
                self.settings["paths"][key] = "/outside/private.md"
                self.write_json(self.shared, self.settings)
                with self.assertRaises(loop.LoopError) as caught:
                    self.ctx()
                self.assertEqual(caught.exception.code, "unsafe_path")
                self.settings["paths"][key] = "99_System/safe.md"

    def test_agent_directory_must_not_alias_daily_or_dated_note(self):
        for relative in ("10_Diary/HumanLoop", "10_Diary/HumanLoop/2026-01-05.md",
                         "10_Diary/HumanLoop/2026-01-05.md/Agent"):
            with self.subTest(path=relative):
                self.settings["paths"]["agent_dir"] = relative
                self.write_json(self.shared, self.settings)
                with self.assertRaises(loop.LoopError) as caught:
                    self.ctx()
                self.assertEqual(caught.exception.code, "agent_directory_overlaps_daily")

    def test_real_cli_date_override_rejected(self):
        with patch.object(loop, "host_id", return_value=HOST):
            with patch.object(sys, "argv", ["helper", "--config", str(self.config), "prepare", "--mode", "morning", "--date", "2026-01-05"]):
                with patch("builtins.print") as output:
                    self.assertEqual(loop.main(), 2)
        self.assertIn("date_override_requires_dry_run", output.call_args.args[0])
        self.assertFalse((self.vault / "10_Diary").exists())

    def test_binding_config_cannot_sync_and_existing_binding_cannot_overwrite(self):
        with patch.object(loop, "host_id", return_value=HOST):
            with self.assertRaises(loop.LoopError) as caught:
                loop.bind(self.vault, "primary", self.vault / "local.json")
            self.assertEqual(caught.exception.code, "local_config_must_be_outside_vault")
            original = self.config.read_bytes()
            with self.assertRaises(loop.LoopError) as caught:
                loop.bind(self.vault, "primary", self.config)
            self.assertEqual(caught.exception.code, "local_config_exists")
            self.assertEqual(self.config.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
