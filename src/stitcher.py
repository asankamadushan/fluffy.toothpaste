"""Compose per-monitor images into a single stitched wallpaper."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from monitors import Monitor, virtual_size

CACHE_FILE = Path.home() / ".cache" / "desktop-bg-app" / "wallpaper.png"


def build(assignments: dict[str, Path], monitors: list[Monitor]) -> Path:
    """
    Scale each assigned image to fill its monitor (cover, no stretch),
    paste it at the monitor's virtual-desktop offset, save as PNG.
    Returns the path to the stitched file.
    """
    vw, vh = virtual_size(monitors)
    canvas = Image.new("RGB", (vw, vh))

    for monitor in monitors:
        img_path = assignments.get(monitor.name)
        if img_path is None:
            continue
        img = Image.open(img_path).convert("RGB")
        img = _cover(img, monitor.width, monitor.height)
        canvas.paste(img, (monitor.x, monitor.y))

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(CACHE_FILE, format="PNG")
    return CACHE_FILE


def thumbnail(img_path: Path, width: int, height: int) -> Image.Image:
    """Return a cover-scaled thumbnail for GUI preview."""
    return _cover(Image.open(img_path).convert("RGB"), width, height)


def _cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale to fill target dimensions (CSS background-size: cover)."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))
