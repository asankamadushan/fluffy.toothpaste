"""Shared fixtures and factories."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from monitors import Monitor

# ── Monitor factory ────────────────────────────────────────────────────────


@pytest.fixture()
def make_monitor():
    """Callable factory for Monitor with sensible defaults."""

    def _factory(
        name: str = "eDP-1",
        x: int = 0,
        y: int = 0,
        width: int = 1920,
        height: int = 1080,
        primary: bool = True,
    ) -> Monitor:
        return Monitor(name=name, x=x, y=y, width=width, height=height, primary=primary)

    return _factory


@pytest.fixture()
def single_monitor(make_monitor) -> Monitor:
    return make_monitor()


@pytest.fixture()
def two_monitors(make_monitor) -> list[Monitor]:
    """Side-by-side: eDP-1 left (1920×1080), HDMI-1 right (2560×1440)."""
    return [
        make_monitor("eDP-1",  x=0,    width=1920, height=1080, primary=True),
        make_monitor("HDMI-1", x=1920, width=2560, height=1440, primary=False),
    ]


@pytest.fixture()
def portrait_monitor(make_monitor) -> Monitor:
    """Single portrait (rotated) monitor."""
    return make_monitor("HDMI-1", x=0, width=1080, height=1920, primary=True)


@pytest.fixture()
def three_monitors_l_shape(make_monitor) -> list[Monitor]:
    """L-shape: two side-by-side on top row, one below-left."""
    return [
        make_monitor("DP-1",   x=0,    y=0,    width=1920, height=1080, primary=False),
        make_monitor("HDMI-1", x=1920, y=0,    width=1920, height=1080, primary=False),
        make_monitor("eDP-1",  x=0,    y=1080, width=1920, height=1080, primary=True),
    ]


# ── Image helpers ──────────────────────────────────────────────────────────


def solid_image(
    width: int, height: int, color: tuple[int, int, int] = (100, 149, 237)
) -> Image.Image:
    """In-memory solid-colour RGB image — no filesystem access."""
    return Image.new("RGB", (width, height), color)


@pytest.fixture()
def tmp_image_file(tmp_path) -> Path:
    """800×600 PNG written to pytest's temp dir."""
    p = tmp_path / "test.png"
    solid_image(800, 600).save(p)
    return p


@pytest.fixture()
def tmp_tall_image_file(tmp_path) -> Path:
    """Portrait source image (400×800)."""
    p = tmp_path / "tall.png"
    solid_image(400, 800, color=(50, 200, 50)).save(p)
    return p


@pytest.fixture()
def tmp_wide_image_file(tmp_path) -> Path:
    """Very wide source image (1600×400)."""
    p = tmp_path / "wide.png"
    solid_image(1600, 400, color=(200, 50, 200)).save(p)
    return p
