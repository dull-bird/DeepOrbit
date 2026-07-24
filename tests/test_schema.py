import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deeporbit.cli import main, parser
from deeporbit.schema import build_schema


def _namespace(doc, segment):
    return next(ns for ns in doc["namespaces"] if ns["segment"] == segment)


def _command(commands, name):
    return next(cmd for cmd in commands if cmd["name"] == name)


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = build_schema(parser(), version="0.0.0-test")

    def test_root_required_fields(self):
        self.assertEqual(self.doc["schemaVersion"], 1)
        self.assertEqual(self.doc["name"], "deeporbit")
        self.assertEqual(self.doc["version"], "0.0.0-test")
        self.assertIn("__schema", self.doc["reservedMetaCommands"])

    def test_meta_command_emits_document_and_exits_zero(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["__schema"])
        self.assertEqual(code, 0)
        emitted = json.loads(buffer.getvalue())
        self.assertEqual(emitted["schemaVersion"], 1)
        self.assertEqual(emitted["name"], "deeporbit")

    def test_flat_commands_present_with_intent(self):
        names = {cmd["name"] for cmd in self.doc["commands"]}
        self.assertEqual(
            names,
            {"init", "doctor", "open", "index", "rag", "agenda", "calendar", "status", "suggest", "sync", "sweep", "pause", "resume", "done", "archive", "trash", "serve", "hygiene", "repo-link"},
        )
        init = _command(self.doc["commands"], "init")
        self.assertEqual(init["intent"], {"destructive": False, "idempotent": True, "scope": "directory"})
        self.assertEqual(init["output"]["formats"], ["json"])
        self.assertIn("read", _command(self.doc["commands"], "rag")["tags"])
        trash = _command(self.doc["commands"], "trash")
        self.assertTrue(trash["intent"]["destructive"])

    def test_namespaces_contain_subcommands(self):
        todo = _namespace(self.doc, "todo")
        self.assertEqual({cmd["name"] for cmd in todo["commands"]}, {"add", "list", "done"})
        link = _namespace(self.doc, "link")
        self.assertEqual({cmd["name"] for cmd in link["commands"]}, {"add", "list", "route", "remove", "default", "describe"})
        remove = _command(link["commands"], "remove")
        self.assertTrue(remove["intent"]["destructive"])
        self.assertEqual(remove["path"], ["link"])
        profile = _namespace(self.doc, "profile")
        self.assertEqual({cmd["name"] for cmd in profile["commands"]}, {"show", "set", "observe", "focus", "compact"})
        cron = _namespace(self.doc, "cron")
        self.assertEqual({cmd["name"] for cmd in cron["commands"]}, {"add", "list", "remove", "run-due", "enable", "disable"})

    def test_parameter_roles_and_enums(self):
        open_cmd = _command(self.doc["commands"], "open")
        params = {param["name"]: param for param in open_cmd["parameters"]}
        self.assertEqual(params["path"]["role"], "positional")
        self.assertTrue(params["path"]["required"])
        self.assertEqual(params["dry-run"]["role"], "dryRun")
        index_cmd = _command(self.doc["commands"], "index")
        action = next(param for param in index_cmd["parameters"] if param["name"] == "action")
        self.assertEqual(action["type"], "enum")
        self.assertEqual(action["enumValues"], ["ensure", "status"])
        self.assertFalse(action["required"])

    def test_global_vault_option(self):
        vault = self.doc["globalOptions"][0]
        self.assertEqual(vault["name"], "vault")
        self.assertEqual(vault["defaultValue"], ".")

    def test_environment_declared(self):
        config_files = {entry["path"] for entry in self.doc["environment"]["configFiles"]}
        self.assertIn("deeporbit.json", config_files)
        self.assertIn("~/.config/deeporbit/links.json", config_files)


if __name__ == "__main__":
    unittest.main()
