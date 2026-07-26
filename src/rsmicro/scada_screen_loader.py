"""Canonical, confined loading for project-declared SCADA screens.

This module is shared by the operator runtime and repository validator so a
screen cannot pass release validation through a different parser than the one
which renders it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rsmicro.scada_screen import Screen, validate_screen


class ScreenLoadError(ValueError):
    """A declared screen cannot be resolved or violates the screen contract."""


def _controller_tags(project: Any) -> dict[str, set[str]]:
    return {
        controller.controller_id: {tag.tag_id for tag in controller.tags}
        for controller in project.controllers
    }


def load_screen_reference(project: Any, project_path: str | Path, reference: Any) -> Screen:
    """Resolve and validate one canonical ``{screen_id, name, path}`` reference."""
    if not isinstance(reference, dict):
        raise ScreenLoadError("screen reference must be an object")
    required = ("screen_id", "name", "path")
    if any(not isinstance(reference.get(field), str) or not reference[field] for field in required):
        raise ScreenLoadError("screen reference requires non-empty screen_id, name and path strings")

    root = Path(project_path).resolve().parent
    candidate = (root / reference["path"]).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ScreenLoadError(f"screen path escapes project directory: {reference['path']}") from exc
    if not candidate.is_file():
        raise ScreenLoadError(f"screen file does not exist: {reference['path']}")

    try:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScreenLoadError(f"cannot parse screen {reference['path']}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ScreenLoadError(f"screen JSON must be an object: {reference['path']}")
    if raw.get("format") != "rsmicro-scada-screen" or raw.get("format_version") != 1:
        raise ScreenLoadError(f"unsupported screen format/version: {reference['path']}")
    if raw.get("executable_code") is not False:
        raise ScreenLoadError(f"screen must explicitly disable executable code: {reference['path']}")
    if raw.get("screen_id") != reference["screen_id"]:
        raise ScreenLoadError(f"screen ID does not match project declaration: {reference['path']}")
    if raw.get("name") != reference["name"]:
        raise ScreenLoadError(f"screen name does not match project declaration: {reference['path']}")
    if not isinstance(raw.get("objects"), list):
        raise ScreenLoadError(f"screen objects must be a list: {reference['path']}")

    try:
        screen = Screen.from_dict(raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise ScreenLoadError(f"invalid screen object shape in {reference['path']}: {exc}") from exc
    ownership = _controller_tags(project)
    diagnostics = validate_screen(screen, set().union(*ownership.values()), ownership)
    if diagnostics:
        raise ScreenLoadError(f"invalid screen {reference['path']}: " + "; ".join(diagnostics))
    return screen


def load_project_screens(project: Any, project_path: str | Path) -> list[Screen]:
    """Load every declared screen through the exact production parser."""
    return [load_screen_reference(project, project_path, reference) for reference in project.scada.screens]
