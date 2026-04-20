"""Persist monitor→image assignments between sessions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import stitcher
from monitors import Monitor

_log = logging.getLogger(__name__)

SESSION_FILE = Path.home() / ".config" / "fluffy.toothpaste" / "session.json"


def _default_fit_modes(monitors: list[Monitor]) -> dict[str, str]:
    return {m.name: stitcher.DEFAULT_FIT_MODE for m in monitors}


def save(
    assignments: dict[str, Path],
    fit_modes: dict[str, str] | None = None,
) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    fm: dict[str, str] = dict(fit_modes) if fit_modes is not None else {}
    data = {
        "assignments": {name: str(path) for name, path in assignments.items()},
        "fit_modes": fm,
    }
    SESSION_FILE.write_text(json.dumps(data, indent=2))


def load(monitors: list[Monitor]) -> tuple[dict[str, Path], dict[str, str]]:
    """
    Return saved assignments that are still valid, and fit modes per monitor.

    Assignments:
    - image file must exist on disk
    - monitor name must be in the currently connected monitor list

    Fit modes: one entry per connected monitor; invalid or missing keys use
    the default fit mode.
    """
    defaults = _default_fit_modes(monitors)
    if not SESSION_FILE.exists():
        return {}, defaults

    try:
        data = json.loads(SESSION_FILE.read_text())
        raw: dict[str, str] = data["assignments"]
    except (json.JSONDecodeError, KeyError, TypeError):
        _log.warning("Session file unreadable, starting fresh: %s", SESSION_FILE)
        return {}, defaults

    raw_fit = data.get("fit_modes", {})
    if not isinstance(raw_fit, dict):
        raw_fit = {}

    live_names = {m.name for m in monitors}
    result: dict[str, Path] = {}

    for name, path_str in raw.items():
        path = Path(path_str)
        if name not in live_names:
            _log.debug("Skipping session entry %r — monitor not connected", name)
            continue
        if not path.exists():
            _log.debug("Skipping session entry %r — file not found: %s", name, path)
            continue
        result[name] = path

    result_fit: dict[str, str] = {}
    for m in monitors:
        v = raw_fit.get(m.name, stitcher.DEFAULT_FIT_MODE)
        if isinstance(v, str) and v in stitcher.VALID_FIT_MODES:
            result_fit[m.name] = v
        else:
            result_fit[m.name] = stitcher.DEFAULT_FIT_MODE

    return result, result_fit
