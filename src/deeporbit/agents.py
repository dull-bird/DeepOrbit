"""Detection and configuration of local agent CLIs.

DeepOrbit prepares context (prompts, vault state, cron instructions) and can
hand execution to an agent CLI installed on the machine. Each agent supports
one or more modes:

- `acp`   — Agent Client Protocol over stdio (interactive, streaming)
- `rpc`   — NDJSON RPC mode (omp only)
- `print` — one-shot non-interactive prompt (`-p` / `exec`)

The user's choice is stored in `deeporbit.json` under `agent:` — it is a
preference, not machine state; detection always runs live.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from .errors import DeepOrbitError


class AgentError(DeepOrbitError):
    code = "AGENT_ERROR"


@dataclass(frozen=True, slots=True)
class AgentSpec:
    name: str
    binary: str
    modes: dict[str, list[str]]  # mode -> argv prefix
    description: str


AGENTS: dict[str, AgentSpec] = {
    "omp": AgentSpec(
        "omp",
        "omp",
        {
            "acp": ["omp", "acp"],
            "rpc": ["omp", "--mode", "rpc"],
            "print": ["omp", "-p"],
        },
        "Oh My Pi — ACP server, NDJSON RPC, and one-shot print mode",
    ),
    "claude": AgentSpec(
        "claude",
        "claude",
        {
            "acp": ["claude", "--acp"],
            "print": ["claude", "-p"],
        },
        "Claude Code — ACP via --acp, one-shot via -p",
    ),
    "gemini": AgentSpec(
        "gemini",
        "gemini",
        {
            "acp": ["gemini", "--acp"],
            "print": ["gemini", "-p"],
        },
        "Gemini CLI — ACP via --acp, one-shot via -p",
    ),
    "codex": AgentSpec(
        "codex",
        "codex",
        {
            "print": ["codex", "exec"],
        },
        "Codex CLI — one-shot via exec (no ACP)",
    ),
}

DEFAULT_MODE_ORDER = ("acp", "rpc", "print")


@dataclass(slots=True)
class DetectedAgent:
    name: str
    binary: str
    installed: bool
    path: str = ""
    version: str = ""
    modes: list[str] = field(default_factory=list)
    description: str = ""


def _probe_version(binary: str) -> str:
    try:
        proc = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=5
        )
        line = (proc.stdout or proc.stderr).strip().splitlines()
        return line[0].strip() if line else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def detect(with_version: bool = False) -> list[DetectedAgent]:
    """Probe every known agent CLI on this machine."""
    found: list[DetectedAgent] = []
    for name, spec in AGENTS.items():
        path = shutil.which(spec.binary)
        installed = path is not None
        found.append(
            DetectedAgent(
                name=name,
                binary=spec.binary,
                installed=installed,
                path=path or "",
                version=_probe_version(spec.binary) if installed and with_version else "",
                modes=sorted(spec.modes) if installed else [],
                description=spec.description,
            )
        )
    return found


def default_mode(name: str) -> str:
    """Pick the preferred mode for an agent: acp > rpc > print."""
    spec = AGENTS.get(name)
    if spec is None:
        raise AgentError(f"unknown agent: {name}")
    for mode in DEFAULT_MODE_ORDER:
        if mode in spec.modes:
            return mode
    raise AgentError(f"agent {name} has no supported modes")


def resolve(name: str, mode: str | None = None) -> tuple[str, str, list[str]]:
    """Validate a choice and return (name, mode, argv prefix)."""
    spec = AGENTS.get(name)
    if spec is None:
        raise AgentError(
            f"unknown agent: {name} (known: {', '.join(sorted(AGENTS))})"
        )
    if shutil.which(spec.binary) is None:
        raise AgentError(f"agent '{name}' is not installed (binary '{spec.binary}' not found on PATH)")
    chosen = mode or default_mode(name)
    argv = spec.modes.get(chosen)
    if argv is None:
        raise AgentError(
            f"agent '{name}' does not support mode '{chosen}' "
            f"(supported: {', '.join(sorted(spec.modes))})"
        )
    return name, chosen, argv


def status_payload(configured: dict | None) -> dict:
    """Combined view: what is configured vs what is actually available."""
    configured = configured or {}
    detected = detect()
    available = {agent.name for agent in detected if agent.installed}
    name = configured.get("name", "")
    mode = configured.get("mode", "")
    entry: dict = {
        "configured": bool(name),
        "name": name,
        "mode": mode,
        "updated": configured.get("updated", ""),
        "available": name in available if name else False,
        "detected": [
            {
                "name": agent.name,
                "installed": agent.installed,
                "path": agent.path,
                "modes": agent.modes,
                "description": agent.description,
            }
            for agent in detected
        ],
    }
    if name and name in available:
        spec = AGENTS.get(name)
        if spec and mode in spec.modes:
            entry["argv"] = spec.modes[mode]
    return entry
