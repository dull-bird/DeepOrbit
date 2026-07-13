import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deeporbit.openers import open_note


class OpenerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.note = Path(self.temp.name) / "A note.md"
        self.note.write_text("# note", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    @patch("deeporbit.openers.shutil.which", return_value="/usr/bin/obsidian")
    @patch("deeporbit.openers.subprocess.Popen")
    def test_prefers_official_cli(self, popen, _which):
        result = open_note(self.note)
        self.assertEqual(result["method"], "cli")
        popen.assert_called_once()

    @patch("deeporbit.openers.shutil.which", return_value=None)
    @patch("deeporbit.openers.webbrowser.open", return_value=True)
    def test_falls_back_to_obsidian_uri(self, _web, _which):
        result = open_note(self.note)
        self.assertEqual(result["method"], "uri")
        self.assertTrue(result["target"].startswith("obsidian://open?path="))

    @patch("deeporbit.openers.shutil.which", return_value=None)
    @patch("deeporbit.openers.webbrowser.open", return_value=False)
    def test_reports_path_when_no_opener_works(self, _web, _which):
        result = open_note(self.note)
        self.assertEqual(result["method"], "path")
        self.assertEqual(result["target"], str(self.note))


if __name__ == "__main__":
    unittest.main()
