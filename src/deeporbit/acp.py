"""Minimal ACP (Agent Client Protocol) client over stdio NDJSON.

Speaks JSON-RPC 2.0, one message per line, to an agent subprocess
(`omp acp`, `claude --acp`, `gemini --acp`, …). Implements the client side of
the baseline flow: initialize → session/new → session/prompt, streaming
session/update notifications back to the caller. Agent requests for file
reads are served from the vault only; permission requests auto-pick an
allow-once option when offered.
"""

from __future__ import annotations

import itertools
import json
import shutil
import subprocess
import threading
from pathlib import Path
from queue import Empty, Queue

PROTOCOL_VERSION = 1

AGENT_CANDIDATES: list[tuple[str, list[str]]] = [
    ("omp", ["omp", "acp"]),
    ("claude", ["claude", "--acp"]),
    ("gemini", ["gemini", "--acp"]),
]


def detect_agent(preference: str = "auto") -> tuple[str, list[str]] | None:
    candidates = AGENT_CANDIDATES if preference == "auto" else [(preference, preference.split())]
    for name, argv in candidates:
        if shutil.which(argv[0]):
            return name, argv
    return None


class AcpError(RuntimeError):
    pass


class AcpAgent:
    def __init__(self, argv: list[str], cwd: Path):
        self.cwd = cwd.resolve()
        self.proc = subprocess.Popen(
            argv,
            cwd=str(self.cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._ids = itertools.count(1)
        self._pending: dict[int, Queue] = {}
        self._notifications: Queue = Queue()
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    # -- transport ---------------------------------------------------------

    def _read_loop(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "id" in message and message["id"] in self._pending:
                self._pending.pop(message["id"]).put(message)
            elif "method" in message and "id" in message:
                self._handle_agent_request(message)
            else:
                self._notifications.put(message)

    def _write(self, payload: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _call(self, method: str, params: dict, timeout: float = 120.0) -> dict:
        request_id = next(self._ids)
        queue: Queue = Queue()
        self._pending[request_id] = queue
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        try:
            response = queue.get(timeout=timeout)
        except Empty as exc:
            raise AcpError(f"timeout waiting for {method}") from exc
        if "error" in response:
            raise AcpError(f"{method}: {response['error'].get('message', response['error'])}")
        return response.get("result", {})

    def _handle_agent_request(self, message: dict) -> None:
        method, request_id = message["method"], message["id"]
        params = message.get("params", {})
        try:
            if method == "fs/read_text_file":
                result = {"content": self._read_vault_file(params.get("path", ""))}
            elif method == "session/request_permission":
                result = self._pick_permission(params)
            elif method == "fs/write_text_file":
                raise AcpError("writes are disabled in the dashboard bridge")
            else:
                raise AcpError(f"unsupported agent request: {method}")
            self._write({"jsonrpc": "2.0", "id": request_id, "result": result})
        except AcpError as exc:
            self._write({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(exc)}})

    def _read_vault_file(self, raw_path: str) -> str:
        path = Path(raw_path).resolve()
        if not path.is_relative_to(self.cwd):
            raise AcpError(f"path escapes the vault: {raw_path}")
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _pick_permission(params: dict) -> dict:
        options = params.get("options", [])
        chosen = next((o for o in options if o.get("kind") == "allow_once"), None)
        chosen = chosen or next((o for o in options if "allow" in str(o.get("kind", ""))), None)
        if chosen is None:
            return {"outcome": {"outcome": "cancelled"}}
        return {"outcome": {"outcome": "selected", "optionId": chosen.get("optionId", "")}}

    # -- protocol -----------------------------------------------------------

    def initialize(self) -> dict:
        return self._call(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "clientCapabilities": {"fs": {"readTextFile": True, "writeTextFile": False}, "terminal": False},
                "clientInfo": {"name": "deeporbit-dashboard", "version": "2.0.0"},
            },
        )

    def new_session(self) -> str:
        result = self._call("session/new", {"cwd": str(self.cwd), "mcpServers": []})
        return result["sessionId"]

    def prompt(self, session_id: str, text: str, timeout: float = 600.0):
        """Send a prompt; yields session/update payloads, then the stop reason."""
        request_id = next(self._ids)
        queue: Queue = Queue()
        self._pending[request_id] = queue
        self._write(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "session/prompt",
                "params": {"sessionId": session_id, "prompt": [{"type": "text", "text": text}]},
            }
        )
        while True:
            try:
                message = queue.get(timeout=timeout)
            except Empty as exc:
                raise AcpError("timeout during prompt turn") from exc
            if "error" in message:
                raise AcpError(message["error"].get("message", "prompt failed"))
            yield {"type": "done", "stopReason": message.get("result", {}).get("stopReason", "end_turn")}
            return

    def updates(self, timeout: float = 0.5) -> dict | None:
        try:
            return self._notifications.get(timeout=timeout)
        except Empty:
            return None

    def prompt_stream(self, session_id: str, text: str):
        """Yield every event of a prompt turn: updates first, then the final result.

        Holds the turn lock so concurrent prompts on one agent process cannot
        interleave. Notifications are consumed only within the turn, so no
        stale-event draining is needed.
        """
        with self._lock:
            result_holder: list[dict] = []
            error_holder: list[Exception] = []
            prompt_done = threading.Event()

            def run_prompt():
                try:
                    for event in self.prompt(session_id, text):
                        result_holder.append(event)
                except Exception as exc:  # noqa: BLE001 - surfaced to SSE
                    error_holder.append(exc)
                finally:
                    prompt_done.set()

            threading.Thread(target=run_prompt, daemon=True).start()
            while not prompt_done.is_set():
                update = self.updates(timeout=0.5)
                if update is not None:
                    yield {"type": "update", "params": update.get("params", update)}
            if error_holder:
                raise error_holder[0]
            yield result_holder[0] if result_holder else {"type": "done", "stopReason": "end_turn"}

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
