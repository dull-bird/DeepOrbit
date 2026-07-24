"""Local dashboard server for DeepOrbit vaults.

`deeporbit --vault . serve [--port 8765] [--open] [--agent omp]`

Zero-dependency (stdlib only): JSON API for vault state, deterministic
lifecycle actions, and an SSE bridge that proxies chat prompts to an ACP
agent (`omp acp`, `claude --acp`, `gemini --acp`). Binds to 127.0.0.1 only.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from collections import Counter
from dataclasses import asdict
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .acp import AcpAgent, AcpError, detect_agent
from .config import Config
from .cron import list_jobs
from .errors import DeepOrbitError
from .links import list_links
from .privacy import sanitize_value
from .profile import show as profile_show
from .recipes import list_recipes, run_plan
from .search import SearchIndex
from .suggest import suggest as build_suggestions
from .work import archive as work_archive
from .work import overview as work_overview
from .work import scan, set_status, trash

DASHBOARD_HTML = Path(__file__).with_name("dashboard.html")
ACTIONS = {"pause": "paused", "resume": "active", "done": "done"}


def _activity_histogram(items, days: int = 98) -> list[dict]:
    today = date.today()
    buckets: Counter[str] = Counter()
    for item in items:
        raw = item.updated or item.mtime
        try:
            day = date.fromisoformat(str(raw).strip().strip('"')[:10])
        except ValueError:
            continue
        if today - timedelta(days=days) <= day <= today:
            buckets[day.isoformat()] += 1
    return [{"day": (today - timedelta(days=i)).isoformat(), "count": buckets.get((today - timedelta(days=i)).isoformat(), 0)} for i in range(days, -1, -1)]


def build_overview(config: Config) -> dict:
    items = scan(config)
    status_counts = Counter(item.status for item in items)
    author_counts = Counter(item.author for item in items)
    dir_counts = Counter(item.path.split("/", 1)[0] for item in items)
    today = date.today()
    dormant = 0
    for item in items:
        if item.readonly or item.status != "active" or item.path.startswith("40_Wiki/"):
            continue
        raw = item.updated or item.mtime
        try:
            if (today - date.fromisoformat(str(raw).strip().strip('"')[:10])).days > 21:
                dormant += 1
        except ValueError:
            continue
    return {
        "vault": str(config.vault),
        "language": config.language,
        "counts": dict(status_counts),
        "authors": dict(author_counts),
        "dirs": dict(dir_counts.most_common(12)),
        "dormant": dormant,
        "readonly": sum(1 for item in items if item.readonly),
        "total": len(items),
        "activity": _activity_histogram(items),
        "suggestions": [asdict(s) for s in build_suggestions(config)],
        "profile": profile_show(config)["fields"],
        "links": [{"name": l.name, "path": str(l.path), "is_default": l.is_default, "description": l.description} for l in list_links()],
        "cron": [asdict(j) for j in list_jobs()],
        "recipes": [{"name": r.name, "schedule": r.schedule, "steps": len(r.steps)} for r in list_recipes(config)],
    }


class AgentSession:
    """One lazily started ACP agent process per server."""

    def __init__(self, vault: Path, preference: str = "auto"):
        self.vault = vault
        self.preference = preference
        self.agent: AcpAgent | None = None
        self.agent_name = ""
        self.session_id = ""
        self.error = ""
        self._start_lock = threading.Lock()

    def ensure(self) -> None:
        with self._start_lock:
            if self.agent is not None:
                return
            detected = detect_agent(self.preference)
            if detected is None:
                raise AcpError("no ACP agent found (tried omp, claude, gemini)")
            self.agent_name, argv = detected
            self.agent = AcpAgent(argv, self.vault)
            self.agent.initialize()
            self.session_id = self.agent.new_session()

    def reset(self) -> None:
        with self._start_lock:
            if self.agent is not None:
                self.agent.close()
            self.agent = None
            self.session_id = ""

    def status(self) -> dict:
        return {
            "available": detect_agent(self.preference) is not None if self.agent is None else True,
            "agent": self.agent_name or (self.preference if self.preference != "auto" else ""),
            "session": bool(self.session_id),
            "error": self.error,
        }

def make_handler(config: Config, session: AgentSession, *, privacy_mode: str = "allow"):
    index = SearchIndex(config)
    privacy_rules = config.privacy.get("rules") if privacy_mode != "allow" else None

    def json_bytes(payload) -> bytes:
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        server_version = "DeepOrbitDashboard/2.0"

        def log_message(self, *args):  # quiet
            pass

        def _send_json(self, payload, status: int = 200) -> None:
            if privacy_mode != "allow":
                payload = sanitize_value(payload, mode=privacy_mode, rules=privacy_rules).value
            body = json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, exc: Exception, status: int = 400) -> None:
            code = getattr(exc, "code", exc.__class__.__name__)
            self._send_json({"error": code, "message": str(exc)}, status=status)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            if not length:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        # -- GET ------------------------------------------------------------

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            route, query = parsed.path, parse_qs(parsed.query)
            try:
                if route == "/" or route == "/index.html":
                    body = DASHBOARD_HTML.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif route == "/api/overview":
                    self._send_json(build_overview(config))
                elif route == "/api/items":
                    items = scan(config)
                    status_f = query.get("status", [""])[0]
                    author_f = query.get("author", [""])[0]
                    dir_f = query.get("dir", [""])[0]
                    text = query.get("q", [""])[0].lower()
                    out = []
                    for item in items:
                        if status_f and item.status != status_f:
                            continue
                        if author_f and item.author != author_f:
                            continue
                        if dir_f and not item.path.startswith(dir_f):
                            continue
                        if text and text not in (item.title + item.path).lower():
                            continue
                        out.append(asdict(item))
                    self._send_json(out[:500])
                elif route == "/api/rag":
                    q = query.get("q", [""])[0]
                    self._send_json(index.query(q, limit=10) if q else [])
                elif route == "/api/recipe/run":
                    self._send_json(run_plan(config, query.get("name", [""])[0]))
                elif route == "/api/agent/status":
                    self._send_json(session.status())
                elif route == "/api/agent/config":
                    from .agents import status_payload

                    self._send_json(status_payload(config.agent))
                else:
                    self._send_json({"error": "not found"}, status=404)
            except (DeepOrbitError, RuntimeError, ValueError) as exc:
                self._send_error(exc)

        # -- POST -----------------------------------------------------------

        def do_POST(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            try:
                if route == "/api/lifecycle":
                    payload = self._body()
                    path, action = payload.get("path", ""), payload.get("action", "")
                    if action in ACTIONS:
                        result = asdict(set_status(config, path, ACTIONS[action]))
                    elif action == "archive":
                        result = work_archive(config, path)
                    elif action == "trash":
                        result = trash(config, path)
                    else:
                        raise DeepOrbitError(f"unknown action: {action}")
                    self._send_json(result)
                elif route == "/api/agent/reset":
                    session.reset()
                    self._send_json(session.status())
                elif route == "/api/agent/config":
                    from datetime import datetime, timezone

                    from .agents import resolve, status_payload
                    from .config import save_agent

                    payload = self._body()
                    name = str(payload.get("name", "")).strip()
                    if not name:
                        save_agent(config.vault, None)
                        config.agent.clear()
                        session.preference = "auto"
                        session.reset()
                    else:
                        mode = payload.get("mode") or None
                        resolved_name, resolved_mode, _argv = resolve(name, mode)
                        entry = {
                            "name": resolved_name,
                            "mode": resolved_mode,
                            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        }
                        save_agent(config.vault, entry)
                        config.agent.clear()
                        config.agent.update(entry)
                        session.preference = resolved_name
                        session.reset()
                    self._send_json(status_payload(config.agent))
                elif route == "/api/agent/prompt":
                    self._stream_agent(self._body().get("text", ""))
                else:
                    self._send_json({"error": "not found"}, status=404)
            except (DeepOrbitError, RuntimeError, ValueError) as exc:
                self._send_error(exc)

        def _stream_agent(self, text: str) -> None:
            if privacy_mode != "allow":
                text = sanitize_value(text, mode=privacy_mode, rules=privacy_rules).value
            if not text.strip():
                self._send_json({"error": "empty prompt"}, status=400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            def emit(event: dict) -> bool:
                try:
                    self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    return True
                except (BrokenPipeError, ConnectionResetError):
                    return False

            try:
                session.ensure()
            except AcpError as exc:
                session.error = str(exc)
                emit({"type": "error", "message": str(exc)})
                return
            emit({"type": "agent", "agent": session.agent_name})
            try:
                for event in session.agent.prompt_stream(session.session_id, text):
                    if not emit(event):
                        break
            except AcpError as exc:
                session.error = str(exc)
                emit({"type": "error", "message": str(exc)})

    return Handler


def serve(
    config: Config,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
    agent: str = "auto",
    privacy_mode: str | None = None,
) -> int:
    effective_mode = privacy_mode or config.privacy.get("outbound_mode", "allow")
    session = AgentSession(config.vault, agent)
    httpd = ThreadingHTTPServer((host, port), make_handler(config, session, privacy_mode=effective_mode))
    url = f"http://{host}:{httpd.server_address[1]}"
    print(json.dumps({"url": url, "vault": str(config.vault)}, ensure_ascii=False))
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        session.reset()
        httpd.server_close()
    return 0
