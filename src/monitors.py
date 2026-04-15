"""Monitor detection — Linux (xrandr) and Windows (ctypes)."""

from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Monitor:
    name: str
    x: int
    y: int
    width: int
    height: int
    primary: bool


# xrandr line example:
#   HDMI-1 connected 1440x2560+2560+0 right (normal ...) 527mm x 296mm
#   eDP-1 connected primary 2560x1440+0+0 (normal ...) 344mm x 193mm
# xrandr already reports post-rotation dimensions, so no rotation math needed.
_XRANDR_RE = re.compile(
    r"^(\S+) connected (primary )?(\d+)x(\d+)\+(\d+)\+(\d+)"
)


def get_monitors() -> list[Monitor]:
    match platform.system():
        case "Linux":
            return _from_xrandr()
        case "Windows":
            return _from_windows()
        case other:
            raise NotImplementedError(f"Unsupported platform: {other}")


def _from_xrandr() -> list[Monitor]:
    out = subprocess.run(
        ["xrandr"], capture_output=True, text=True, check=True
    ).stdout
    monitors = []
    for line in out.splitlines():
        m = _XRANDR_RE.match(line)
        if m:
            name, primary, w, h, x, y = m.groups()
            monitors.append(
                Monitor(
                    name=name,
                    x=int(x),
                    y=int(y),
                    width=int(w),
                    height=int(h),
                    primary=bool(primary),
                )
            )
    return monitors


def _from_windows() -> list[Monitor]:
    import ctypes
    from ctypes import wintypes

    monitors: list[Monitor] = []

    def _callback(hmonitor, hdc, lprect, lparam):  # noqa: ANN001
        r = lprect.contents
        monitors.append(
            Monitor(
                name=f"Monitor{len(monitors) + 1}",
                x=r.left,
                y=r.top,
                width=r.right - r.left,
                height=r.bottom - r.top,
                primary=(r.left == 0 and r.top == 0),
            )
        )
        return True

    _proc_t = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(wintypes.RECT),
        ctypes.c_double,
    )
    ctypes.windll.user32.EnumDisplayMonitors(None, None, _proc_t(_callback), 0)
    return monitors


def virtual_size(monitors: list[Monitor]) -> tuple[int, int]:
    """Total pixel dimensions of the virtual desktop."""
    w = max(m.x + m.width for m in monitors)
    h = max(m.y + m.height for m in monitors)
    return w, h
