"""Compose per-monitor images into a single stitched wallpaper."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from monitors import Monitor, virtual_size

CACHE_FILE = Path.home() / ".cache" / "fluffy.toothpaste" / "wallpaper.png"

# Internal keys; user-facing labels are set in the GUI.
FIT_ZOOM = "zoom"
FIT_SCALED = "scaled"
FIT_STRETCHED = "stretched"
FIT_CENTERED = "centered"
FIT_WALLPAPER = "wallpaper"

VALID_FIT_MODES: frozenset[str] = frozenset(
    {FIT_ZOOM, FIT_SCALED, FIT_STRETCHED, FIT_CENTERED, FIT_WALLPAPER}
)
DEFAULT_FIT_MODE = FIT_ZOOM


def build(
    assignments: dict[str, Path],
    monitors: list[Monitor],
    fit_modes: dict[str, str] | None = None,
) -> Path:
    """
    Scale each assigned image per fit mode for its monitor,
    paste it at the monitor's virtual-desktop offset, save as PNG.
    Returns the path to the stitched file.
    """
    vw, vh = virtual_size(monitors)
    canvas = Image.new("RGB", (vw, vh))

    for monitor in monitors:
        img_path = assignments.get(monitor.name)
        if img_path is None:
            continue
        mode = _mode_for(monitor.name, fit_modes)
        img = Image.open(img_path).convert("RGB")
        img = _fit(img, monitor.width, monitor.height, mode)
        canvas.paste(img, (monitor.x, monitor.y))

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(CACHE_FILE, format="PNG")
    return CACHE_FILE


def _mode_for(name: str, fit_modes: dict[str, str] | None) -> str:
    if not fit_modes:
        return DEFAULT_FIT_MODE
    m = fit_modes.get(name, DEFAULT_FIT_MODE)
    return m if m in VALID_FIT_MODES else DEFAULT_FIT_MODE


def thumbnail(
    img_path: Path, width: int, height: int, mode: str = DEFAULT_FIT_MODE,
) -> Image.Image:
    """Return a scaled thumbnail for GUI preview using the given fit mode."""
    m = mode if mode in VALID_FIT_MODES else DEFAULT_FIT_MODE
    return _fit(Image.open(img_path).convert("RGB"), width, height, m)


def _fit(img: Image.Image, target_w: int, target_h: int, mode: str) -> Image.Image:
    if mode == FIT_ZOOM:
        return _cover(img, target_w, target_h)
    if mode == FIT_SCALED:
        return _contain(img, target_w, target_h)
    if mode == FIT_STRETCHED:
        return _stretch(img, target_w, target_h)
    if mode == FIT_CENTERED:
        return _centered(img, target_w, target_h)
    if mode == FIT_WALLPAPER:
        return _tile(img, target_w, target_h)
    return _cover(img, target_w, target_h)


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


def _contain(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Aspect-preserving fit inside target; letterbox with black."""
    src_w, src_h = img.size
    scale = min(target_w / src_w, target_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    out = Image.new("RGB", (target_w, target_h))
    ox = (target_w - new_w) // 2
    oy = (target_h - new_h) // 2
    out.paste(resized, (ox, oy))
    return out


def _stretch(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Stretch to exact target (may distort aspect ratio)."""
    return img.resize((target_w, target_h), Image.LANCZOS)


def _centered(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Native pixel size centered; crop overflow; black elsewhere; no upscale."""
    tw, th = target_w, target_h
    canvas = Image.new("RGB", (tw, th))

    cur = img
    cw, ch = cur.size
    if cw > tw:
        left = (cw - tw) // 2
        cur = cur.crop((left, 0, left + tw, ch))
        cw, ch = cur.size
    if ch > th:
        t = (ch - th) // 2
        cur = cur.crop((0, t, cw, t + th))

    ox = (tw - cur.size[0]) // 2
    oy = (th - cur.size[1]) // 2
    canvas.paste(cur, (ox, oy))
    return canvas


def _tile(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Tile the source image to fill the target rectangle."""
    sw, sh = img.size
    if sw < 1 or sh < 1:
        return Image.new("RGB", (target_w, target_h))
    out = Image.new("RGB", (target_w, target_h))
    y = 0
    while y < target_h:
        x = 0
        while x < target_w:
            out.paste(img, (x, y))
            x += sw
        y += sh
    return out
