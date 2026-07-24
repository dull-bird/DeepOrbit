import json
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

    def test_runtime_hook_manifests_use_current_schema(self):
        for path in (ROOT / "hooks" / "hooks.json", ROOT / ".codex-plugin" / "hooks" / "hooks.json", ROOT / ".codex" / "hooks" / "hooks.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            for event in ("SessionStart", "PostToolUse"):
                groups = document["hooks"][event]
                self.assertTrue(groups)
                handlers = groups[0]["hooks"]
                self.assertEqual(handlers[0]["type"], "command")
                self.assertIn("deeporbit_hook.py", handlers[0]["command"])

    def test_claude_project_imports_shared_instructions(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("@AGENTS.md", text)
        self.assertIn("@DeepOrbitPrompt.md", text)


if __name__ == "__main__":
    unittest.main()
