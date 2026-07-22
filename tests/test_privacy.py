from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from deeporbit.config import load_config
from deeporbit.errors import PrivacyError
from deeporbit.privacy import sanitize_value
from deeporbit.vault import initialize


class PrivacySanitizeTests(unittest.TestCase):
    def test_allow_mode_leaves_text_unchanged(self):
        text = "Contact jane.doe@example.com or 555-123-4567"
        result = sanitize_value(text, mode="allow")
        self.assertEqual(result.value, text)
        self.assertFalse(result.changed)

    def test_redact_mode_masks_email_and_phone(self):
        text = "Email jane.doe@example.com or call 555-123-4567"
        result = sanitize_value(text, mode="redact")
        self.assertNotIn("jane.doe@example.com", result.value)
        self.assertNotIn("555-123-4567", result.value)
        self.assertIn("<EMAIL>", result.value)
        self.assertIn("<PHONE>", result.value)
        self.assertTrue(result.changed)

    def test_block_mode_raises_on_sensitive_content(self):
        with self.assertRaises(PrivacyError):
            sanitize_value("Email jane.doe@example.com", mode="block")

    def test_redact_mode_recursively_handles_dict_and_list(self):
        payload = {
            "user": "alice@example.com",
            "items": [{"note": "call 555-123-4567"}],
            "count": 3,
        }
        result = sanitize_value(payload, mode="redact")
        raw = json.dumps(result.value)
        self.assertNotIn("alice@example.com", raw)
        self.assertNotIn("555-123-4567", raw)
        self.assertEqual(result.value["count"], 3)
        self.assertTrue(result.changed)

    def test_disabled_rule_is_skipped(self):
        rules = [
            {"name": "email", "enabled": False, "severity": "high"},
            {"name": "phone", "enabled": True, "severity": "high"},
        ]
        text = "Email jane.doe@example.com call 555-123-4567"
        result = sanitize_value(text, mode="redact", rules=rules)
        self.assertIn("jane.doe@example.com", result.value)
        self.assertNotIn("555-123-4567", result.value)


class PrivacyConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        initialize(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_privacy_policy_is_strict(self):
        config = load_config(self.root)
        self.assertEqual(config.privacy.get("outbound_mode"), "redact")
        rules = {r["name"]: r for r in config.privacy.get("rules", [])}
        for name in ("email", "phone", "secret", "card", "id_number"):
            self.assertIn(name, rules)
            self.assertTrue(rules[name]["enabled"])
            self.assertEqual(rules[name]["severity"], "high")

    def test_custom_rule_overrides_default(self):
        path = self.root / "deeporbit.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["privacy"] = {"outbound_mode": "block", "rules": [{"name": "email", "enabled": False}]}
        path.write_text(json.dumps(raw), encoding="utf-8")
        config = load_config(self.root)
        self.assertEqual(config.privacy["outbound_mode"], "block")
        rules = {r["name"]: r for r in config.privacy["rules"]}
        self.assertFalse(rules["email"]["enabled"])
        self.assertTrue(rules["phone"]["enabled"])


if __name__ == "__main__":
    unittest.main()
