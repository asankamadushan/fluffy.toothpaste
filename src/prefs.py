"""User preferences — persisted alongside session data."""

from __future__ import annotations

import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

_PREFS_FILE = Path.home() / ".config" / "desktop-bg-app" / "prefs.json"
_DEFAULTS: dict = {
    "pictures_dir": str(Path.home() / "Pictures"),
}


def load() -> dict:
    if not _PREFS_FILE.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(_PREFS_FILE.read_text())
        return {**_DEFAULTS, **data}
    except (json.JSONDecodeError, TypeError):
        _log.warning("Prefs file unreadable, using defaults: %s", _PREFS_FILE)
        return dict(_DEFAULTS)


def save(prefs: dict) -> None:
    _PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PREFS_FILE.write_text(json.dumps(prefs, indent=2))
