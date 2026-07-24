"""Tests for agent CLI detection and configuration."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deeporbit import agents
from deeporbit.config import load_config, save_agent


class DetectTests(unittest.TestCase):
    def test_detect_marks_uninstalled(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            found = agents.detect()
        self.assertEqual({a.name for a in found}, set(agents.AGENTS))
        self.assertTrue(all(not a.installed for a in found))
        self.assertTrue(all(a.modes == [] for a in found))

    def test_detect_lists_modes_when_installed(self) -> None:
        with mock.patch("shutil.which", side_effect=lambda b: f"/usr/bin/{b}"):
            found = agents.detect()
        omp = next(a for a in found if a.name == "omp")
        self.assertTrue(omp.installed)
        self.assertEqual(omp.modes, ["acp", "print", "rpc"])
        codex = next(a for a in found if a.name == "codex")
        self.assertEqual(codex.modes, ["print"])


class ResolveTests(unittest.TestCase):
    def test_unknown_agent_rejected(self) -> None:
        with self.assertRaises(agents.AgentError):
            agents.resolve("nonexistent")

    def test_uninstalled_agent_rejected(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(agents.AgentError):
                agents.resolve("omp")

    def test_default_mode_prefers_acp(self) -> None:
        with mock.patch("shutil.which", return_value="/usr/bin/omp"):
            name, mode, argv = agents.resolve("omp")
        self.assertEqual(mode, "acp")
        self.assertEqual(argv, ["omp", "acp"])

    def test_unsupported_mode_rejected(self) -> None:
        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with self.assertRaises(agents.AgentError):
                agents.resolve("codex", "acp")

    def test_codex_print_mode(self) -> None:
        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            _, mode, argv = agents.resolve("codex")
        self.assertEqual(mode, "print")
        self.assertEqual(argv, ["codex", "exec"])


class ConfigPersistenceTests(unittest.TestCase):
    def make_vault(self, tmp: str) -> Path:
        vault = Path(tmp) / "vault"
        vault.mkdir()
        (vault / "deeporbit.json").write_text(
            json.dumps({"version": 2, "vault_id": "v1", "language": "zh-CN"}),
            encoding="utf-8",
        )
        return vault

    def test_save_and_load_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(tmp)
            save_agent(vault, {"name": "omp", "mode": "acp", "updated": "2026-07-24T00:00:00+00:00"})
            config = load_config(vault)
            self.assertEqual(config.agent["name"], "omp")
            self.assertEqual(config.agent["mode"], "acp")
            # Other sections survive.
            self.assertEqual(config.vault_id, "v1")

    def test_clear_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(tmp)
            save_agent(vault, {"name": "omp", "mode": "acp"})
            save_agent(vault, None)
            self.assertEqual(load_config(vault).agent, {})

    def test_status_payload_marks_unavailable(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            payload = agents.status_payload({"name": "omp", "mode": "acp"})
        self.assertTrue(payload["configured"])
        self.assertFalse(payload["available"])

    def test_status_payload_unconfigured(self) -> None:
        payload = agents.status_payload({})
        self.assertFalse(payload["configured"])
        self.assertEqual(len(payload["detected"]), len(agents.AGENTS))


if __name__ == "__main__":
    unittest.main()
