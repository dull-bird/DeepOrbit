from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_skill_frontmatter_names_match_directories(self):
        for directory in sorted((ROOT / "skills").glob("do.*")):
            text = (directory / "SKILL.md").read_text(encoding="utf-8")
            name = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
            self.assertTrue(name and name.group(1) == directory.name)

    def test_command_formats_are_paired(self):
        command_dir = ROOT / "commands" / "do"
        self.assertEqual({p.stem for p in command_dir.glob("*.md")}, {p.stem for p in command_dir.glob("*.toml")})

    def test_every_skill_has_a_command(self):
        skills = {path.name.removeprefix("do.") for path in (ROOT / "skills").glob("do.*")}
        commands = {path.stem for path in (ROOT / "commands" / "do").glob("*.md")}
        self.assertEqual(skills, commands)

    def test_no_generated_installer_artifacts_are_tracked(self):
        forbidden = {".agents", ".cursor", ".roo", "skills-lock.json"}
        self.assertFalse(any(path.name in forbidden for path in ROOT.iterdir()))


if __name__ == "__main__":
    unittest.main()
