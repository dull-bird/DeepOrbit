import json
import tempfile
import unittest
from pathlib import Path

from deeporbit.config import load_config
from deeporbit.vault import initialize


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_initialize_creates_complete_vault(self):
        result = initialize(self.root)
        self.assertFalse(result.conflicts)
        self.assertTrue((self.root / "15_Writings").is_dir())
        self.assertTrue((self.root / "99_System" / "Bases").is_dir())
        config = load_config(self.root)
        self.assertTrue(config.vault_id)
        self.assertTrue(config.cache_dir.is_absolute())
        self.assertFalse(str(config.cache_dir).startswith(str(self.root)))

    def test_initialize_merges_legacy_without_nesting(self):
        legacy = self.root / "50_Resources" / "产品发布"
        target = self.root / "50_Resources" / "Product_Launches"
        legacy.mkdir(parents=True)
        target.mkdir(parents=True)
        (legacy / "old.md").write_text("old", encoding="utf-8")
        (target / "new.md").write_text("new", encoding="utf-8")
        result = initialize(self.root)
        self.assertFalse(result.conflicts)
        self.assertEqual((target / "old.md").read_text(encoding="utf-8"), "old")
        self.assertFalse((target / "产品发布").exists())

    def test_initialize_preserves_conflicting_files(self):
        legacy = self.root / "50_Resources" / "新闻"
        target = self.root / "50_Resources" / "News"
        legacy.mkdir(parents=True)
        target.mkdir(parents=True)
        (legacy / "same.md").write_text("legacy", encoding="utf-8")
        (target / "same.md").write_text("canonical", encoding="utf-8")
        result = initialize(self.root)
        self.assertEqual(result.conflicts, ["50_Resources/新闻/same.md"])
        self.assertEqual((legacy / "same.md").read_text(encoding="utf-8"), "legacy")
        self.assertEqual((target / "same.md").read_text(encoding="utf-8"), "canonical")

    def test_initialize_materializes_workflows(self):
        result = initialize(self.root)
        self.assertIn("do.init", result.workflows)
        index = self.root / "99_System" / "DeepOrbit" / "skills-index.json"
        self.assertTrue(index.is_file())
        entries = json.loads(index.read_text(encoding="utf-8"))
        names = {entry["name"] for entry in entries}
        self.assertIn("do.link", names)
        self.assertTrue(all(entry["description"] for entry in entries))
        self.assertTrue((self.root / "99_System" / "DeepOrbit" / "skills" / "do.init" / "SKILL.md").is_file())

    def test_initialize_materializes_runtime_bundle(self):
        result = initialize(self.root)
        bundle = self.root / "99_System" / "DeepOrbit" / "repo"
        self.assertIn("99_System/DeepOrbit/repo/DeepOrbitPrompt.md", result.runtime_bundle)
        self.assertTrue((bundle / "skills" / "do.link" / "SKILL.md").is_file())
        self.assertTrue((bundle / "src" / "deeporbit" / "cli.py").is_file())
        self.assertTrue((bundle / ".codex" / "hooks" / "hooks.json").is_file())
        self.assertTrue((bundle / ".omp" / "hooks" / "pre" / "deeporbit.ts").is_file())
        self.assertFalse((bundle / ".git").exists())
        self.assertFalse((bundle / ".venv").exists())

    def test_initialize_refreshes_stale_workflows(self):
        initialize(self.root)
        stale = self.root / "99_System" / "DeepOrbit" / "skills" / "do.ghost" / "SKILL.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale", encoding="utf-8")
        initialize(self.root)
        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
