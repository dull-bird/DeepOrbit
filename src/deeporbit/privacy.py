from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

from .errors import PrivacyError

PrivacyMode = str


@dataclass(slots=True)
class SanitizedValue:
    value: Any
    changed: bool


DEFAULT_RULES: list[dict[str, Any]] = [
    {"name": "email", "enabled": True, "severity": "high"},
    {"name": "phone", "enabled": True, "severity": "high"},
    {"name": "secret", "enabled": True, "severity": "high"},
    {"name": "card", "enabled": True, "severity": "high"},
    {"name": "id_number", "enabled": True, "severity": "high"},
]

_BUILTIN_PATTERNS: dict[str, tuple[re.Pattern[str], str]] = {
    "email": (re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<EMAIL>"),
    "phone": (
        re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}\b"),
        "<PHONE>",
    ),
    "secret": (
        re.compile(
            r"\b(?:sk-[A-Za-z0-9]{16,}|"
            r"ghp_[A-Za-z0-9]{20,}|"
            r"xox[baprs]-[A-Za-z0-9-]{10,}|"
            r"AKIA[0-9A-Z]{16})\b"
        ),
        "<SECRET>",
    ),
    "card": (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "<CARD>"),
    "id_number": (re.compile(r"\b\d{17}[\dXx]\b"), "<ID>"),
}


_ALLOWED_MODES = {"allow", "redact", "block"}


def _lookup_rule(name: str, rules: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    for rule in rules or []:
        if rule.get("name") == name:
            return rule
    return None


def _active_patterns(rules: list[dict[str, Any]] | None) -> list[tuple[re.Pattern[str], str, str]]:
    out = []
    for name, (pattern, replacement) in _BUILTIN_PATTERNS.items():
        rule = _lookup_rule(name, rules)
        if rule is None:
            rule = {"enabled": True, "severity": "medium"}
        if rule.get("enabled", True):
            out.append((pattern, replacement, rule.get("severity", "medium")))
    return out


def _sanitize_string(text: str, *, mode: PrivacyMode, rules: list[dict[str, Any]] | None = None) -> SanitizedValue:
    changed = False
    value = text
    for pattern, replacement, severity in _active_patterns(rules):
        if pattern.search(value):
            if mode == "block":
                raise PrivacyError(f"Outbound privacy block: {pattern.pattern}")
            value = pattern.sub(replacement, value)
            changed = True
    return SanitizedValue(value=value, changed=changed)


def sanitize_value(
    value: Any,
    *,
    mode: PrivacyMode = "allow",
    rules: list[dict[str, Any]] | None = None,
) -> SanitizedValue:
    if mode not in _ALLOWED_MODES:
        raise PrivacyError(f"Unknown privacy mode: {mode}")
    if mode == "allow":
        return SanitizedValue(value=value, changed=False)
    if isinstance(value, str):
        return _sanitize_string(value, mode=mode, rules=rules)
    if isinstance(value, list):
        changed = False
        out = []
        for item in value:
            result = sanitize_value(item, mode=mode, rules=rules)
            out.append(result.value)
            changed = changed or result.changed
        return SanitizedValue(value=out, changed=changed)
    if isinstance(value, tuple):
        changed = False
        out = []
        for item in value:
            result = sanitize_value(item, mode=mode, rules=rules)
            out.append(result.value)
            changed = changed or result.changed
        return SanitizedValue(value=tuple(out), changed=changed)
    if isinstance(value, dict):
        changed = False
        out: dict[Any, Any] = {}
        for key, item in value.items():
            result = sanitize_value(item, mode=mode, rules=rules)
            out[key] = result.value
            changed = changed or result.changed
        return SanitizedValue(value=out, changed=changed)
    return SanitizedValue(value=value, changed=False)
