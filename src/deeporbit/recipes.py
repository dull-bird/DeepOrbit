"""Recipes — declarative, composable workflow bundles.

A recipe is a plain Markdown file in `99_System/Recipes/` with frontmatter and
a numbered list of steps. Each step is one of:

- `cli: deeporbit --vault . <command …>` — a deterministic CLI call
- `skill: do.<name> [args]` — an Agent Skill invocation (DeepOrbit or any other)
- `note: <text>` — an instruction for the executing agent/user

Recipes are data, not code: the core only parses, validates, and resolves them
into an execution plan. Agents (or `cron` jobs) do the executing. This keeps
DeepOrbit small while letting users compose it with any other skill.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .cron import add_job, list_jobs, parse_every
from .errors import DeepOrbitError
from .frontmatter import read_fields

RECIPES_DIR = "99_System/Recipes"
STEP_RE = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+(cli|skill|note):\s*(.+?)\s*$")


class RecipeError(DeepOrbitError):
    code = "RECIPE_ERROR"


@dataclass(slots=True)
class Step:
    kind: str  # "cli" | "skill" | "note"
    text: str


@dataclass(slots=True)
class Recipe:
    name: str
    path: str
    description: str
    schedule: str
    author: str
    steps: list[Step]


def _parse_recipe(path: Path, config: Config) -> Recipe:
    text = path.read_text(encoding="utf-8")
    fields = read_fields(text)
    steps = [Step(kind=m.group(1), text=m.group(2)) for m in (STEP_RE.match(line) for line in text.splitlines()) if m]
    return Recipe(
        name=fields.get("name") or path.stem,
        path=str(path.relative_to(config.vault)),
        description=fields.get("description", ""),
        schedule=fields.get("schedule", ""),
        author=fields.get("author", "human"),
        steps=steps,
    )


def _recipes_root(config: Config) -> Path:
    return config.vault / RECIPES_DIR


def list_recipes(config: Config) -> list[Recipe]:
    root = _recipes_root(config)
    if not root.is_dir():
        return []
    return [_parse_recipe(path, config) for path in sorted(root.glob("*.md"))]


def load_recipe(config: Config, name: str) -> Recipe:
    for recipe in list_recipes(config):
        if recipe.name == name or Path(recipe.path).stem == name:
            return recipe
    known = ", ".join(recipe.name for recipe in list_recipes(config)) or "none"
    raise RecipeError(f"Unknown recipe: {name} (available: {known})")


def _validate_step(step: Step, config: Config) -> str | None:
    if step.kind == "cli":
        tokens = step.text.split()
        if not tokens or tokens[0] not in ("deeporbit", "bash", "powershell", "sh"):
            return f"cli step must start with 'deeporbit' (or a shell script call): {step.text}"
    elif step.kind == "skill":
        skill = step.text.split()[0] if step.text.split() else ""
        if skill.startswith("do."):
            materialized = config.vault / "99_System" / "DeepOrbit" / "skills" / skill / "SKILL.md"
            repo = Path(__file__).resolve().parents[2] / "skills" / skill / "SKILL.md"
            if not materialized.is_file() and not repo.is_file():
                return f"unknown DeepOrbit skill: {skill}"
    return None


def run_plan(config: Config, name: str) -> dict:
    """Resolve a recipe into an execution plan with validation warnings."""
    recipe = load_recipe(config, name)
    warnings = [w for w in (_validate_step(step, config) for step in recipe.steps) if w]
    return {
        "name": recipe.name,
        "path": recipe.path,
        "schedule": recipe.schedule,
        "steps": [{"kind": step.kind, "text": step.text} for step in recipe.steps],
        "warnings": warnings,
    }


def schedule_recipe(config: Config, name: str) -> dict:
    """Idempotently register a cron job from the recipe's `schedule:` frontmatter.

    Job name is `recipe-<name>`; an existing job with that name is reported
    and left untouched. The instruction points the executing agent at
    `deeporbit recipe run` so the recipe file stays the single source of truth.
    """
    recipe = load_recipe(config, name)
    if not recipe.schedule:
        raise RecipeError(
            f"Recipe '{recipe.name}' has no `schedule:` frontmatter; "
            "add e.g. `schedule: daily` or `schedule: weekly` to schedule it"
        )
    every = recipe.schedule.strip().lower()
    parse_every(every)  # validates (daily/weekly/hourly/<N>h/<N>d); raises CronError with guidance
    job_name = f"recipe-{recipe.name}"
    for job in list_jobs():
        if job.name == job_name:
            return {
                "job": job_name,
                "recipe": recipe.name,
                "every": every,
                "created": False,
                "note": "cron job already exists; skipped",
            }
    job = add_job(
        job_name,
        config.vault,
        instruction=(
            f'Run recipe "{recipe.name}": resolve it with '
            f'`deeporbit recipe run "{recipe.name}"` and execute the plan'
        ),
        every=every,
    )
    return {"job": job.name, "recipe": recipe.name, "every": every, "created": True}
