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


if __name__ == "__main__":
    unittest.main()
