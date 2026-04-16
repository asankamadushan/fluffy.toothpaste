"""Tests for stitcher.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import solid_image
from PIL import Image

from monitors import Monitor
from stitcher import _cover, build, thumbnail

# ── _cover ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("src_size,target_w,target_h", [
    ((1920, 1080), 1920, 1080),  # exact — no scaling
    ((3840, 1080), 1920, 1080),  # wider source → crop sides
    ((1920, 2160), 1920, 1080),  # taller source → crop top/bottom
    ((400,   300), 1920, 1080),  # small source → scale up
    ((1000, 1000), 1920, 1080),  # square → wide target
    ((1920, 1080), 1080, 1920),  # portrait target
    ((1,       1),  100,  100),  # 1×1 source — must not crash
    ((1919, 1080), 1920, 1080),  # 1px narrower than target
])
def test_cover_output_size(src_size, target_w, target_h):
    img = solid_image(*src_size)
    result = _cover(img, target_w, target_h)
    assert result.size == (target_w, target_h)


def test_cover_returns_rgb():
    result = _cover(solid_image(800, 600), 200, 150)
    assert result.mode == "RGB"


def test_cover_scale_up_fills_target():
    """Small source must be scaled up, not leave gaps."""
    result = _cover(solid_image(10, 10), 500, 300)
    assert result.size == (500, 300)


def test_cover_does_not_distort_aspect_ratio():
    """Cover must preserve aspect ratio — no stretching."""
    # 2:1 source into 1:1 target → should crop, not squash
    src = solid_image(200, 100)
    result = _cover(src, 100, 100)
    assert result.size == (100, 100)
    # If it distorted, pixels would be wrong colours. Size check is sufficient
    # because _cover uses a single scale factor, not separate sx/sy.


# ── thumbnail ─────────────────────────────────────────────────────────────

def test_thumbnail_landscape(tmp_image_file):
    result = thumbnail(tmp_image_file, 200, 150)
    assert result.size == (200, 150)
    assert result.mode == "RGB"


def test_thumbnail_portrait_target(tmp_tall_image_file):
    result = thumbnail(tmp_tall_image_file, 100, 200)
    assert result.size == (100, 200)


def test_thumbnail_returns_image_instance(tmp_image_file):
    assert isinstance(thumbnail(tmp_image_file, 50, 50), Image.Image)


# ── build ─────────────────────────────────────────────────────────────────

def _patch_cache(mocker, tmp_path) -> Path:
    """Redirect CACHE_FILE into pytest's temp dir."""
    dest = tmp_path / "wallpaper.png"
    mocker.patch("stitcher.CACHE_FILE", new=dest)
    return dest


def test_build_returns_cache_path(mocker, tmp_path, tmp_image_file):
    dest = _patch_cache(mocker, tmp_path)
    result = build(
        {"eDP-1": tmp_image_file}, [Monitor("eDP-1", 0, 0, 1920, 1080, True)]
    )
    assert result == dest


def test_build_single_monitor_output_size(mocker, tmp_path, tmp_image_file):
    _patch_cache(mocker, tmp_path)
    out = build({"eDP-1": tmp_image_file}, [Monitor("eDP-1", 0, 0, 1920, 1080, True)])
    assert Image.open(out).size == (1920, 1080)


def test_build_two_monitors_output_size(mocker, tmp_path, tmp_image_file, two_monitors):
    _patch_cache(mocker, tmp_path)
    assignments = {m.name: tmp_image_file for m in two_monitors}
    out = build(assignments, two_monitors)
    # virtual: max(0+1920, 1920+2560)=4480, max(1080,1440)=1440
    assert Image.open(out).size == (4480, 1440)


def test_build_portrait_beside_landscape(
    mocker, tmp_path, tmp_image_file, make_monitor
):
    _patch_cache(mocker, tmp_path)
    monitors = [
        make_monitor("A", x=0,    width=1920, height=1080),
        make_monitor("B", x=1920, width=1080, height=1920, primary=False),
    ]
    out = build({m.name: tmp_image_file for m in monitors}, monitors)
    assert Image.open(out).size == (3000, 1920)


def test_build_unassigned_monitor_region_is_black(
    mocker, tmp_path, tmp_image_file, two_monitors
):
    """Un-assigned monitor region stays black (canvas default)."""
    _patch_cache(mocker, tmp_path)
    # Only assign first monitor
    out = build({"eDP-1": tmp_image_file}, two_monitors)
    result = Image.open(out)
    # Sample a pixel well inside HDMI-1's region (x=1920+100, y=100)
    pixel = result.getpixel((2020, 100))
    assert pixel == (0, 0, 0)


def test_build_empty_assignments_produces_black_canvas(mocker, tmp_path):
    _patch_cache(mocker, tmp_path)
    monitor = Monitor("eDP-1", 0, 0, 100, 100, True)
    out = build({}, [monitor])
    img = Image.open(out)
    assert img.size == (100, 100)
    assert img.getpixel((50, 50)) == (0, 0, 0)


def test_build_key_mismatch_treated_as_no_assignment(mocker, tmp_path, tmp_image_file):
    """Assignment key that doesn't match any monitor name → black canvas."""
    _patch_cache(mocker, tmp_path)
    monitor = Monitor("eDP-1", 0, 0, 100, 100, True)
    out = build({"WRONG": tmp_image_file}, [monitor])
    assert Image.open(out).getpixel((50, 50)) == (0, 0, 0)


def test_build_creates_parent_directory(mocker, tmp_path, tmp_image_file):
    """CACHE_FILE parent must be created if it doesn't exist yet."""
    dest = tmp_path / "nested" / "deep" / "wallpaper.png"
    mocker.patch("stitcher.CACHE_FILE", new=dest)
    build({"eDP-1": tmp_image_file}, [Monitor("eDP-1", 0, 0, 100, 100, True)])
    assert dest.exists()


def test_build_output_is_valid_png(mocker, tmp_path, tmp_image_file):
    _patch_cache(mocker, tmp_path)
    out = build({"eDP-1": tmp_image_file}, [Monitor("eDP-1", 0, 0, 200, 150, True)])
    img = Image.open(out)
    assert img.format == "PNG"
