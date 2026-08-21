"""Contract tests for the shipped Obsidian Bases (99_System/Bases/*.base).

These files are the vault's dashboards. They must stay valid YAML and keep
the view contract agents and docs rely on: Projects.base offers a
grouped all-status table and the Kanban Bases View plugin board.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

BASES_DIR = Path(__file__).resolve().parents[1] / "99_System" / "Bases"


def _load(name: str) -> dict:
    return yaml.safe_load((BASES_DIR / name).read_text(encoding="utf-8"))


class BasesFileTests(unittest.TestCase):
    def test_all_base_files_parse_as_yaml(self):
        files = sorted(BASES_DIR.glob("*.base"))
        self.assertGreater(len(files), 0)
        for path in files:
            with self.subTest(file=path.name):
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIsInstance(payload, dict)
                self.assertIn("views", payload)
                self.assertIsInstance(payload["views"], list)
                for view in payload["views"]:
                    self.assertIn("type", view)
                    self.assertIn("name", view)

    def test_projects_has_grouped_all_status_table(self):
        views = _load("Projects.base")["views"]
        tables = [v for v in views if v["type"] == "table" and v.get("group_by") == "status"]
        self.assertEqual(len(tables), 1)
        # The grouped table must not filter any status away.
        self.assertNotIn("filters", tables[0])

    def test_projects_kanban_view_groups_by_status(self):
        views = _load("Projects.base")["views"]
        kanban = [v for v in views if v["type"] == "kanban-view"]
        self.assertEqual(len(kanban), 1)
        self.assertEqual(kanban[0].get("groupByProperty"), "note.status")

    def test_projects_keeps_per_status_tables(self):
        views = _load("Projects.base")["views"]
        filtered = {
            tuple(v.get("filters", {}).get("and", []))
            for v in views
            if v["type"] == "table" and "filters" in v
        }
        self.assertIn(('status == "active"',), filtered)
        self.assertIn(('status == "paused"',), filtered)
        self.assertIn(('status == "done"',), filtered)

    def test_projects_scopes_to_configured_folder(self):
        payload = _load("Projects.base")
        global_filter = str(payload.get("filters", {}))
        self.assertIn('file.inFolder("20_Projects")', global_filter)

    def test_research_scopes_to_configured_folder(self):
        payload = _load("Research.base")
        global_filter = str(payload.get("filters", {}))
        self.assertIn('file.inFolder("30_Research")', global_filter)

    def test_work_status_covers_full_lifecycle(self):
        payload = _load("Work Status.base")
        statuses = set(payload.get("filters", {}).get("or", []))
        for status in ("active", "paused", "done", "archived"):
            self.assertIn(f'status == "{status}"', statuses)


if __name__ == "__main__":
    unittest.main()
