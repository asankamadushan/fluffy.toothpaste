"""Apply a wallpaper image — dispatches by OS and desktop environment."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def apply(path: Path) -> None:
    match platform.system():
        case "Linux":
            _apply_linux(path)
        case "Windows":
            _apply_windows(path)
        case other:
            raise NotImplementedError(f"Unsupported platform: {other}")


# ── Linux ──────────────────────────────────────────────────────────────────

def _apply_linux(path: Path) -> None:
    de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "gnome" in de or "unity" in de or "ubuntu" in de:
        _gnome(path)
    elif "kde" in de:
        _kde(path)
    elif "xfce" in de:
        _xfce(path)
    else:
        _feh(path)


def _gnome(path: Path) -> None:
    uri = path.as_uri()
    base = "org.gnome.desktop.background"
    _gs(base, "picture-options", "spanned")
    _gs(base, "picture-uri", uri)
    _gs(base, "picture-uri-dark", uri)


def _gs(*args: str) -> None:
    subprocess.run(["gsettings", "set", *args], check=True)


def _kde(path: Path) -> None:
    script = (
        "var desktops = desktops();"
        "for (var i = 0; i < desktops.length; i++) {"
        "  var d = desktops[i];"
        "  d.wallpaperPlugin = 'org.kde.image';"
        "  d.currentConfigGroup = ['Wallpaper','org.kde.image','General'];"
        f"  d.writeConfig('Image','file://{path}');"
        "}"
    )
    subprocess.run(
        ["qdbus", "org.kde.plasmashell", "/PlasmaShell",
         "org.kde.PlasmaShell.evaluateScript", script],
        check=True,
    )


def _xfce(path: Path) -> None:
    result = subprocess.run(
        ["xfconf-query", "-c", "xfce4-desktop", "-l"],
        capture_output=True, text=True,
    )
    for prop in result.stdout.splitlines():
        if "last-image" in prop:
            subprocess.run(
                ["xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", str(path)],
                check=True,
            )


def _feh(path: Path) -> None:
    subprocess.run(["feh", "--bg-fill", str(path)], check=True)


# ── Windows ────────────────────────────────────────────────────────────────

def _apply_windows(path: Path) -> None:
    import ctypes
    import winreg  # type: ignore[import]

    # Style 22 = "Span" (Windows 8+), needed for multi-monitor stitched image
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Control Panel\Desktop",
        0, winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "22")
    winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
    winreg.CloseKey(key)

    SPI_SETDESKWALLPAPER = 20
    ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, str(path), 0x01 | 0x02
    )
