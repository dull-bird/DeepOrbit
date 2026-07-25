#!/usr/bin/env python3
"""Render the DeepOrbit skill graph into DeepOrbitPrompt.md.

Spec source: 99_System/DeepOrbit/skills_graph.yaml (its header documents the
supported YAML subset). This script is stdlib-only by design: it parses that
subset with a small line parser instead of importing PyYAML.

Usage:
    python3 scripts/render_skill_graph.py          # regenerate + inject
    python3 scripts/render_skill_graph.py --check  # verify only; exit 1 + diff if stale
"""
from __future__ import annotations

import difflib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "99_System" / "DeepOrbit" / "skills_graph.yaml"
PROMPT_PATH = ROOT / "DeepOrbitPrompt.md"

START_MARK = "<!-- skills-graph:start -->"
END_MARK = "<!-- skills-graph:end -->"
SECTION_TITLE = "## Skill graph / 技能关系图"
AFTER_SECTION = "## Intent routing"

LAYER_ORDER = ["rhythm", "perception", "judgment", "action"]

NOTE = (
    "> 图的规范源是 `99_System/DeepOrbit/skills_graph.yaml`；修改技能后运行\n"
    "> `python3 scripts/render_skill_graph.py` 重新生成，`scripts/validate_repo.py` 校验一致性。"
)

# Full-width punctuation is banned inside mermaid code blocks (do.mermaid rules).
FULL_WIDTH = "，。！（）：；"


class SpecError(Exception):
    """Raised for any skills_graph.yaml structure violation."""


def _fail(lineno: int, message: str) -> None:
    raise SpecError(f"{SPEC_PATH.relative_to(ROOT)}:{lineno}: {message}")


def _flow_list(lineno: int, value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        _fail(lineno, f"expected flow list [a, b], got: {value!r}")
    inner = value[1:-1].strip()
    return [item.strip() for item in inner.split(",")] if inner else []


def _scalar(lineno: int, text: str, key: str) -> str:
    prefix = f"{key}:"
    if not text.startswith(prefix):
        _fail(lineno, f"expected {key!r} key, got: {text!r}")
    value = text[len(prefix):].strip()
    if not value:
        _fail(lineno, f"empty value for {key!r}")
    return value


def parse_spec(path: Path) -> dict:
    """Parse the documented YAML subset into {layers, systems, edges}."""
    layers: dict[str, dict] = {}
    systems: dict[str, str] = {}
    edges: list[dict] = []
    section = None
    layer = None
    item = None
    in_skills = False

    lines = path.read_text(encoding="utf-8").splitlines()
    for lineno, raw in enumerate(lines, 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.rstrip() != raw:
            _fail(lineno, "trailing whitespace")
        indent = len(raw) - len(raw.lstrip(" "))
        text = raw.strip()

        if indent == 0:
            if text in ("layers:", "systems:", "edges:"):
                section = text[:-1]
                layer = item = None
                in_skills = False
            else:
                _fail(lineno, f"expected top-level section layers:/systems:/edges:, got: {text!r}")
        elif section == "layers":
            if indent == 2 and text.endswith(":") and not text.startswith("- "):
                layer = text[:-1]
                if layer in layers:
                    _fail(lineno, f"duplicate layer {layer!r}")
                layers[layer] = {"label": None, "skills": []}
                item = None
                in_skills = False
            elif layer is None:
                _fail(lineno, "skill/label outside any layer")
            elif indent == 4 and text.startswith("label:"):
                layers[layer]["label"] = _scalar(lineno, text, "label")
            elif indent == 4 and text == "skills:":
                in_skills = True
            elif indent == 6 and in_skills and text.startswith("- name:"):
                item = {"name": _scalar(lineno, text[2:], "name"), "desc": None, "inputs": [], "outputs": []}
                layers[layer]["skills"].append(item)
            elif indent == 8 and item is not None:
                if text.startswith("desc:"):
                    item["desc"] = _scalar(lineno, text, "desc")
                elif text.startswith("inputs:"):
                    item["inputs"] = _flow_list(lineno, _scalar(lineno, text, "inputs"))
                elif text.startswith("outputs:"):
                    item["outputs"] = _flow_list(lineno, _scalar(lineno, text, "outputs"))
                else:
                    _fail(lineno, f"expected desc:/inputs:/outputs:, got: {text!r}")
            else:
                _fail(lineno, f"unexpected line in layers section: {raw!r}")
        elif section == "systems":
            if indent == 2 and ":" in text and not text.startswith("- "):
                key, _, value = text.partition(":")
                systems[key.strip()] = value.strip()
                if not systems[key.strip()]:
                    _fail(lineno, f"empty label for system node {key.strip()!r}")
            else:
                _fail(lineno, f"unexpected line in systems section: {raw!r}")
        elif section == "edges":
            if indent == 2 and text.startswith("- from:"):
                item = {"from": _scalar(lineno, text[2:], "from"), "to": None, "label": None}
                edges.append(item)
            elif indent == 4 and item is not None:
                if text.startswith("to:"):
                    item["to"] = _scalar(lineno, text, "to")
                elif text.startswith("label:"):
                    item["label"] = _scalar(lineno, text, "label")
                else:
                    _fail(lineno, f"expected to:/label:, got: {text!r}")
            else:
                _fail(lineno, f"unexpected line in edges section: {raw!r}")
        else:
            _fail(lineno, "content before any top-level section")

    _validate(layers, systems, edges)
    return {"layers": layers, "systems": systems, "edges": edges}


def _validate(layers: dict, systems: dict, edges: list) -> None:
    missing = [layer for layer in LAYER_ORDER if layer not in layers]
    if missing:
        raise SpecError(f"skills_graph.yaml: missing required layers: {missing}")
    for layer_id, layer in layers.items():
        if not layer["label"]:
            raise SpecError(f"skills_graph.yaml: layer {layer_id!r} has no label")
        if any(ch in layer["label"] for ch in FULL_WIDTH):
            raise SpecError(f"skills_graph.yaml: layer {layer_id!r} label contains full-width punctuation")
        seen: set[str] = set()
        for skill in layer["skills"]:
            name = skill["name"]
            if not name.startswith("do."):
                raise SpecError(f"skills_graph.yaml: skill {name!r} must be a do.* name")
            if name in seen:
                raise SpecError(f"skills_graph.yaml: duplicate skill {name!r} in layer {layer_id!r}")
            seen.add(name)
            if not skill["desc"]:
                raise SpecError(f"skills_graph.yaml: skill {name!r} has no desc")
            if any(ch in skill["desc"] for ch in FULL_WIDTH):
                raise SpecError(f"skills_graph.yaml: skill {name!r} desc contains full-width punctuation")
    all_skills = [s["name"] for layer in layers.values() for s in layer["skills"]]
    if len(all_skills) != len(set(all_skills)):
        raise SpecError("skills_graph.yaml: a skill appears in more than one layer")
    endpoints = set(all_skills) | set(systems) | set(layers)
    for edge in edges:
        for key in ("from", "to", "label"):
            if not edge.get(key):
                raise SpecError(f"skills_graph.yaml: edge {edge!r} missing {key!r}")
        for key in ("from", "to"):
            if edge[key] not in endpoints:
                raise SpecError(
                    f"skills_graph.yaml: edge {key} {edge[key]!r} is not a declared skill, system node, or layer"
                )
        if any(ch in edge["label"] for ch in FULL_WIDTH):
            raise SpecError(f"skills_graph.yaml: edge {edge!r} label contains full-width punctuation")


def _node_id(name: str) -> str:
    return name.replace(".", "_").replace("-", "_")


def render_mermaid(spec: dict) -> str:
    """Render the spec as a mermaid flowchart TD with Chinese layer subgraphs."""
    lines = ["flowchart TD"]
    for layer_id in LAYER_ORDER:
        layer = spec["layers"][layer_id]
        lines.append(f"  subgraph {layer_id}[{layer['label']}]")
        for skill in layer["skills"]:
            lines.append(f'    {_node_id(skill["name"])}["{skill["name"]} {skill["desc"]}"]')
        lines.append("  end")
    for sys_id, label in spec["systems"].items():
        lines.append(f'  {sys_id}["{label}"]')
    for edge in spec["edges"]:
        lines.append(f"  {_node_id(edge['from'])} -->|{edge['label']}| {_node_id(edge['to'])}")
    return "\n".join(lines)


def injected_block(spec: dict) -> str:
    return f"{START_MARK}\n```mermaid\n{render_mermaid(spec)}\n```\n\n{NOTE}\n{END_MARK}"


def inject(prompt: str, block: str) -> str:
    """Replace between markers, or insert a new section after `## Intent routing`."""
    if START_MARK in prompt and END_MARK in prompt:
        start = prompt.index(START_MARK)
        end = prompt.index(END_MARK) + len(END_MARK)
        return prompt[:start] + block + prompt[end:]
    if START_MARK in prompt or END_MARK in prompt:
        raise SpecError("DeepOrbitPrompt.md: only one skills-graph marker present; restore the pair")
    lines = prompt.splitlines()
    try:
        anchor = lines.index(AFTER_SECTION)
    except ValueError:
        raise SpecError(f"DeepOrbitPrompt.md: section {AFTER_SECTION!r} not found")
    insert_at = len(lines)
    for i in range(anchor + 1, len(lines)):
        if lines[i].startswith("## "):
            insert_at = i
            break
    section = [SECTION_TITLE, "", *block.splitlines(), ""]
    new_lines = lines[:insert_at]
    if new_lines and new_lines[-1] != "":
        new_lines.append("")
    new_lines += section
    new_lines += lines[insert_at:]
    return "\n".join(new_lines).rstrip("\n") + "\n"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    try:
        spec = parse_spec(SPEC_PATH)
    except SpecError as exc:
        print(f"skills-graph: spec error: {exc}", file=sys.stderr)
        return 1
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    try:
        updated = inject(prompt, injected_block(spec))
    except SpecError as exc:
        print(f"skills-graph: {exc}", file=sys.stderr)
        return 1
    if updated == prompt:
        print("skills-graph: DeepOrbitPrompt.md is up to date")
        return 0
    if check:
        print("skills-graph: DeepOrbitPrompt.md is stale; run scripts/render_skill_graph.py", file=sys.stderr)
        diff = difflib.unified_diff(
            prompt.splitlines(), updated.splitlines(),
            fromfile="DeepOrbitPrompt.md (current)", tofile="DeepOrbitPrompt.md (rendered)",
            lineterm="",
        )
        print("\n".join(diff), file=sys.stderr)
        return 1
    PROMPT_PATH.write_text(updated, encoding="utf-8")
    n_skills = sum(len(layer["skills"]) for layer in spec["layers"].values())
    print(f"skills-graph: injected {n_skills} skills, {len(spec['edges'])} edges into {PROMPT_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
