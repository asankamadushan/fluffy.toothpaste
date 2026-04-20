"""Paths to application resources (development vs PyInstaller bundle)."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_dir() -> Path:
    """Directory containing ``icon.png`` and other packaged assets."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent
