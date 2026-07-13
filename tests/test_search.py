import json
import tempfile
import unittest
from pathlib import Path

from deeporbit.config import load_config
from deeporbit.search import SearchIndex
from deeporbit.vault import initialize


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        initialize(self.root)
        self.index = SearchIndex(load_config(self.root))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.index.cache, ignore_errors=True)
        self.temp.cleanup()

    def test_index_add_update_delete(self):
        note = self.root / "40_Wiki" / "Orbit.md"
        note.write_text("Deep orbit retrieval alpha", encoding="utf-8")
        self.assertEqual(self.index.ensure().added, 1)
        self.assertEqual(self.index.query("alpha")[0]["path"], "40_Wiki/Orbit.md")
        note.write_text("Deep orbit retrieval beta and more", encoding="utf-8")
        self.assertEqual(self.index.ensure().updated, 1)
        self.assertTrue(self.index.query("beta"))
        note.unlink()
        self.assertEqual(self.index.ensure().deleted, 1)
        self.assertEqual(self.index.query("beta"), [])

    def test_identical_notes_do_not_collide(self):
        for name in ("One.md", "Two.md"):
            (self.root / "40_Wiki" / name).write_text("shared unique phrase", encoding="utf-8")
        self.index.ensure()
        results = self.index.query("shared", limit=5)
        self.assertEqual({item["path"] for item in results}, {"40_Wiki/One.md", "40_Wiki/Two.md"})

    def test_corrupt_manifest_is_rebuilt(self):
        (self.root / "40_Wiki" / "Note.md").write_text("rebuildable content", encoding="utf-8")
        self.index.ensure()
        self.index.manifest_path.write_text("not-json", encoding="utf-8")
        self.assertEqual(self.index.ensure().added, 1)
        self.assertEqual(json.loads(self.index.manifest_path.read_text(encoding="utf-8"))["version"], 2)

    def test_dead_index_lock_is_reclaimed(self):
        note = self.root / "40_Wiki" / "Note.md"
        note.write_text("a recoverable lock", encoding="utf-8")
        self.index.cache.mkdir(parents=True, exist_ok=True)
        (self.index.cache / "index.lock").write_text("999999999", encoding="utf-8")
        self.assertEqual(self.index.ensure().added, 1)
        self.assertFalse((self.index.cache / "index.lock").exists())


if __name__ == "__main__":
    unittest.main()
