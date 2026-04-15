"""Persist monitor→image assignments between sessions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from monitors import Monitor

_log = logging.getLogger(__name__)

SESSION_FILE = Path.home() / ".config" / "desktop-bg-app" / "session.json"


def save(assignments: dict[str, Path]) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"assignments": {name: str(path) for name, path in assignments.items()}}
    SESSION_FILE.write_text(json.dumps(data, indent=2))


def load(monitors: list[Monitor]) -> dict[str, Path]:
    """
    Return saved assignments that are still valid:
    - image file must exist on disk
    - monitor name must be in the currently connected monitor list
    """
    if not SESSION_FILE.exists():
        return {}

    try:
        data = json.loads(SESSION_FILE.read_text())
        raw: dict[str, str] = data["assignments"]
    except (json.JSONDecodeError, KeyError, TypeError):
        _log.warning("Session file unreadable, starting fresh: %s", SESSION_FILE)
        return {}

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

    return result
