"""Validate Whistle recipes: the JSON Schema, plus checks a schema can't express."""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

SCHEMA_VERSION = 1
RECIPE_SUFFIXES = (".yaml", ".yml")


@cache
def schema() -> dict[str, Any]:
    text = resources.files("whistle_recipes").joinpath("recipe.schema.json").read_text()
    return json.loads(text)


@cache
def _validator() -> Draft202012Validator:
    Draft202012Validator.check_schema(schema())
    return Draft202012Validator(schema())


def validate(spec: Any, *, path: str | Path | None = None) -> list[str]:
    """Return a list of human-readable errors; empty means the recipe is valid."""
    if not isinstance(spec, dict):
        return ["<root>: a recipe must be a mapping"]
    raw = list(_validator().iter_errors(spec))
    # A failed if/then branch leaves its properties "unevaluated", which adds a
    # misleading second error next to the real one. Drop it when that happens.
    real = {p for e in raw if e.validator != "unevaluatedProperties"
            for p in (tuple(e.absolute_path), tuple(e.absolute_path)[:-1])}
    errors = sorted(
        f"{_where(e.absolute_path)}: {e.message}" for e in raw
        if not (e.validator == "unevaluatedProperties" and tuple(e.absolute_path) in real)
    )
    if errors:
        # The semantic checks assume the shape is already right.
        return errors
    return _semantic_errors(spec, Path(path) if path is not None else None)


def load(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_file(path: str | Path) -> list[str]:
    try:
        spec = load(path)
    except yaml.YAMLError as exc:
        return [f"<root>: invalid YAML ({exc})"]
    return validate(spec, path=path)


def _where(path) -> str:
    return "/".join(str(p) for p in path) or "<root>"


def _semantic_errors(spec: dict[str, Any], path: Path | None) -> list[str]:
    errors = []

    if path is not None and path.stem != spec["id"]:
        errors.append(f"id: must match the file name ({path.stem!r})")

    names = [launcher["name"] for launcher in spec.get("launchers", [])]
    if spec["runtime"] in ("wsl", "vm") and not names:
        errors.append(f"launchers: {spec['runtime']} recipes must list their launchers")
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        errors.append(f"launchers: duplicate names {dupes}")

    check = spec.get("health_check")
    if check:
        if check["launcher"] not in names:
            errors.append(f"health_check/launcher: no launcher named {check['launcher']!r}")
        if "window_title" in check:
            try:
                re.compile(check["window_title"])
            except re.error as exc:
                errors.append(f"health_check/window_title: invalid regex ({exc})")

    actions = [next(iter(step)) for step in spec.get("steps", [])]
    if actions.count("run_installer") > 1:
        errors.append("steps: run_installer may appear at most once")
    if spec["runtime"] != "wsl" and not {"run_installer", "copy"} & set(actions):
        errors.append("steps: the installer is never used; add a run_installer or copy step")

    return errors


def _recipe_files(paths: list[str]) -> list[Path]:
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files.extend(sorted(f for f in p.rglob("*") if f.suffix in RECIPE_SUFFIXES))
        else:
            files.append(p)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Whistle recipe files.")
    parser.add_argument("paths", nargs="+", help="recipe files or directories")
    args = parser.parse_args(argv)

    files = _recipe_files(args.paths)
    failed = 0
    seen: dict[str, Path] = {}
    for f in files:
        errors = validate_file(f)
        spec = load(f) if not errors else None
        if spec and spec["id"] in seen:
            errors.append(f"id: duplicate of {seen[spec['id']]}")
        elif spec:
            seen[spec["id"]] = f
        for err in errors:
            print(f"{f}: {err}", file=sys.stderr)
        failed += bool(errors)

    print(f"{len(files) - failed}/{len(files)} recipes valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
