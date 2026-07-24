import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deeporbit.links import (
    LinkError,
    add_link,
    describe_link,
    list_links,
    registry_path,
    remove_link,
    resolve_vault,
    route_link,
    set_default,
)


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root / "config")})
        self.env.start()
        self.vault = self.root / "vault"
        (self.vault / ".obsidian").mkdir(parents=True)
        (self.vault / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")
        (self.vault / "deeporbit.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_add_registers_vault_with_markers(self):
        link = add_link("main", self.vault)
        self.assertEqual(link.path, self.vault.resolve())
        self.assertTrue(link.deeporbit)
        self.assertTrue(link.obsidian_opened)
        self.assertTrue(link.is_default)
        self.assertTrue(registry_path().is_file())

    def test_add_detects_plain_folder(self):
        plain = self.root / "plain"
        plain.mkdir()
        link = add_link("plain", plain)
        self.assertFalse(link.deeporbit)
        self.assertFalse(link.obsidian_opened)

    def test_add_rejects_missing_directory(self):
        with self.assertRaises(LinkError):
            add_link("ghost", self.root / "missing")

    def test_remove_promotes_next_default(self):
        add_link("main", self.vault)
        other = self.root / "other"
        other.mkdir()
        add_link("other", other)
        remove_link("main")
        links = list_links()
        self.assertEqual([link.name for link in links], ["other"])
        self.assertTrue(links[0].is_default)

    def test_set_default_and_resolve(self):
        add_link("main", self.vault)
        other = self.root / "other"
        other.mkdir()
        add_link("other", other)
        set_default("other")
        self.assertEqual(resolve_vault("@other"), other.resolve())
        self.assertEqual(resolve_vault("@"), other.resolve())
        self.assertEqual(resolve_vault(str(self.vault)), Path(str(self.vault)))

    def test_resolve_unknown_link_reports_registry(self):
        add_link("main", self.vault)
        with self.assertRaises(LinkError) as ctx:
            resolve_vault("@nope")
        self.assertIn("main", str(ctx.exception))

    def test_registry_roundtrip_is_valid_json(self):
        add_link("main", self.vault)
        data = json.loads(registry_path().read_text(encoding="utf-8"))
        self.assertEqual(data["default"], "main")
        self.assertIn("main", data["links"])

    def test_add_with_description_defaults_to_user_source(self):
        link = add_link("work", self.vault, description="Work projects and client research")
        self.assertEqual(link.description, "Work projects and client research")
        self.assertEqual(link.description_source, "user")
        self.assertTrue(link.description_updated_at)

    def test_describe_refines_agent_description(self):
        add_link("main", self.vault, description="draft", source="agent")
        link = describe_link("main", "Personal knowledge base for ML research", source="agent")
        self.assertEqual(link.description, "Personal knowledge base for ML research")
        self.assertEqual(link.description_source, "agent")
        persisted = list_links()[0]
        self.assertEqual(persisted.description, "Personal knowledge base for ML research")

    def test_route_prefers_description_match(self):
        work = self.root / "work"
        work.mkdir()
        add_link("main", self.vault, description="Personal research and writing")
        add_link("work", work, description="Work projects and client material")
        routed = route_link("prepare the client material for work")
        self.assertEqual(routed["selected"]["name"], "work")
        self.assertIn("description", routed["reason"])

    def test_route_falls_back_to_default(self):
        work = self.root / "work"
        work.mkdir()
        add_link("main", self.vault, description="Personal research and writing")
        add_link("work", work, description="Work projects and client material")
        routed = route_link("unrelated request")
        self.assertEqual(routed["selected"]["name"], "main")
        self.assertEqual(routed["reason"], "default")

    def test_route_updates_last_used_timestamp(self):
        work = self.root / "work"
        work.mkdir()
        add_link("main", self.vault, description="Personal research and writing")
        add_link("work", work, description="Work projects and client material")
        routed = route_link("prepare the client material for work")
        self.assertTrue(routed["selected"]["last_used_at"])
        persisted = [link for link in list_links() if link.name == "work"][0]
        self.assertEqual(persisted.last_used_at, routed["selected"]["last_used_at"])

    def test_describe_unknown_link_fails(self):
        with self.assertRaises(LinkError):
            describe_link("nope", "text")


if __name__ == "__main__":
    unittest.main()
