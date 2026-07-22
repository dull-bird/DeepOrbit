"""Dashboard server API + ACP bridge tests (fixture vault, ephemeral ports)."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deeporbit.config import load_config
from deeporbit.profile import set_field
from deeporbit.server import AgentSession, make_handler
from deeporbit.vault import initialize
from fixture_vault import build_messy_vault


def get(port: int, path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post(port: int, path: str, payload: dict):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.vault = build_messy_vault(Path(cls.temp.name) / "vault")
        initialize(cls.vault)
        cls.config = load_config(cls.vault)
        cls.session = AgentSession(cls.vault)
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.config, cls.session))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.temp.cleanup()

    def test_dashboard_html_served(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=10) as resp:
            html = resp.read().decode("utf-8")
        self.assertIn("DeepOrbit", html)
        self.assertIn("/api/overview", html)

    def test_overview_shape(self):
        data = get(self.port, "/api/overview")
        self.assertGreaterEqual(data["counts"]["active"], 4)  # shared vault: earlier tests may resume paused items
        self.assertIn("suggestions", data)
        self.assertEqual(len(data["activity"]), 99)
        self.assertEqual(data["recipes"][0]["name"], "Weekly Review")

    def test_items_filter_and_lifecycle_roundtrip(self):
        items = get(self.port, "/api/items?status=active&author=ai")
        self.assertEqual([item["title"] for item in items], ["Agent Digest"])
        result = post(self.port, "/api/lifecycle", {"path": "20_Projects/PausedProject.md", "action": "resume"})
        self.assertEqual(result["status"], "active")
        items = get(self.port, "/api/items?status=paused")
        self.assertFalse(any(item["path"] == "20_Projects/PausedProject.md" for item in items))

    def test_lifecycle_refuses_readonly_via_api(self):
        result = post(self.port, "/api/lifecycle", {"path": "60_Notes/微信读书/测试书A.md", "action": "done"})
        self.assertEqual(result["error"], "WORK_ERROR")
        self.assertIn("Read-only", result["message"])

    def test_privacy_mode_redacts_overview_payload(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        vault = Path(temp.name) / "vault"
        initialize(vault)
        set_field(load_config(vault), "email", "jane.doe@example.com")
        config = load_config(vault)
        session = AgentSession(vault)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(config, session, privacy_mode="redact"))
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            data = get(port, "/api/overview")
            raw = json.dumps(data)
            self.assertNotIn("jane.doe@example.com", raw)
            self.assertIn("<EMAIL>", raw)
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_rag_endpoint(self):
        from deeporbit.search import SearchIndex

        SearchIndex(self.config).ensure()
        hits = get(self.port, "/api/rag?q=lexical%20baselines")
        self.assertTrue(any(hit["path"] == "30_Research/RAG-Survey.md" for hit in hits))

    def test_agent_status_without_agent(self):
        status = get(self.port, "/api/agent/status")
        self.assertIn("available", status)


if __name__ == "__main__":
    unittest.main()
