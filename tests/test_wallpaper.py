"""Tests for wallpaper.py."""

from __future__ import annotations

import sys
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock

import pytest

import wallpaper
from wallpaper import _apply_linux, _feh, _gnome, _kde, _xfce, apply

_PATH = Path("/tmp/wallpaper.png")


# ── apply — OS dispatch ───────────────────────────────────────────────────

def test_apply_linux_dispatches(mocker):
    mocker.patch("wallpaper.platform.system", return_value="Linux")
    mock = mocker.patch("wallpaper._apply_linux")
    apply(_PATH)
    mock.assert_called_once_with(_PATH)


def test_apply_windows_dispatches(mocker):
    mocker.patch("wallpaper.platform.system", return_value="Windows")
    mock = mocker.patch("wallpaper._apply_windows")
    apply(_PATH)
    mock.assert_called_once_with(_PATH)


def test_apply_unsupported_platform_raises(mocker):
    mocker.patch("wallpaper.platform.system", return_value="Darwin")
    with pytest.raises(NotImplementedError, match="Darwin"):
        apply(_PATH)


# ── _apply_linux — DE detection ───────────────────────────────────────────

@pytest.mark.parametrize("xdg,expected_fn", [
    ("GNOME",        "_gnome"),
    ("ubuntu:GNOME", "_gnome"),
    ("Unity",        "_gnome"),
    ("ubuntu",       "_gnome"),
    ("KDE",          "_kde"),
    ("kde",          "_kde"),
    ("XFCE",         "_xfce"),
    ("xfce",         "_xfce"),
    ("",             "_feh"),
    ("i3",           "_feh"),
    ("openbox",      "_feh"),
])
def test_apply_linux_de_dispatch(mocker, xdg, expected_fn):
    backends = ["_gnome", "_kde", "_xfce", "_feh"]
    mocks = {fn: mocker.patch(f"wallpaper.{fn}") for fn in backends}

    mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": xdg})
    _apply_linux(_PATH)

    mocks[expected_fn].assert_called_once_with(_PATH)
    for fn, m in mocks.items():
        if fn != expected_fn:
            m.assert_not_called()


def test_apply_linux_xdg_not_set_falls_back_to_feh(mocker, monkeypatch):
    monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
    mock = mocker.patch("wallpaper._feh")
    mocker.patch("wallpaper._gnome")
    mocker.patch("wallpaper._kde")
    mocker.patch("wallpaper._xfce")
    _apply_linux(_PATH)
    mock.assert_called_once_with(_PATH)


# ── _gnome ────────────────────────────────────────────────────────────────

def test_gnome_calls_gsettings_three_times(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _gnome(_PATH)
    assert run.call_count == 3


def test_gnome_sets_picture_options_spanned(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _gnome(_PATH)
    first_call_args = run.call_args_list[0][0][0]
    assert first_call_args == [
        "gsettings", "set",
        "org.gnome.desktop.background", "picture-options", "spanned",
    ]


def test_gnome_sets_picture_uri_and_dark(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _gnome(_PATH)
    uri = _PATH.as_uri()
    calls = [c[0][0] for c in run.call_args_list]
    assert any("picture-uri" == c[3] and uri == c[4] for c in calls)
    assert any("picture-uri-dark" == c[3] and uri == c[4] for c in calls)


def test_gnome_all_subprocess_calls_have_check_true(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _gnome(_PATH)
    for c in run.call_args_list:
        assert c[1].get("check") is True


def test_gnome_uri_encodes_spaces(mocker, tmp_path):
    run = mocker.patch("wallpaper.subprocess.run")
    spaced = tmp_path / "my wallpaper.png"
    spaced.touch()
    _gnome(spaced)
    uri = spaced.as_uri()
    assert "%20" in uri
    calls = [c[0][0] for c in run.call_args_list]
    assert any(uri in c for c in calls)


# ── _kde ──────────────────────────────────────────────────────────────────

def test_kde_calls_qdbus_once(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _kde(_PATH)
    run.assert_called_once()


def test_kde_uses_correct_qdbus_target(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _kde(_PATH)
    argv = run.call_args[0][0]
    assert argv[0] == "qdbus"
    assert argv[1] == "org.kde.plasmashell"
    assert argv[2] == "/PlasmaShell"
    assert argv[3] == "org.kde.PlasmaShell.evaluateScript"


def test_kde_script_contains_file_path(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _kde(_PATH)
    script = run.call_args[0][0][-1]
    assert f"file://{_PATH}" in script


def test_kde_check_true(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _kde(_PATH)
    assert run.call_args[1].get("check") is True


# ── _xfce ─────────────────────────────────────────────────────────────────

def _xfce_run(mocker, props: list[str]):
    """Helper: mock xfconf-query list returning `props`, run _xfce."""
    stdout = "\n".join(props) + ("\n" if props else "")
    run = mocker.patch(
        "wallpaper.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=stdout),
    )
    _xfce(_PATH)
    return run


def test_xfce_sets_each_last_image_property(mocker):
    props = [
        "/backdrop/screen0/monitor0/workspace0/last-image",
        "/backdrop/screen0/monitor1/workspace0/last-image",
        "/backdrop/screen0/monitor0/workspace0/image-style",  # must be ignored
    ]
    run = _xfce_run(mocker, props)
    # 1 list call + 2 set calls (not 3)
    assert run.call_count == 3
    set_calls = run.call_args_list[1:]
    for c, prop in zip(set_calls, props[:2]):
        argv = c[0][0]
        assert "-p" in argv
        assert prop in argv
        assert "-s" in argv
        assert str(_PATH) in argv


def test_xfce_no_last_image_props_makes_only_list_call(mocker):
    run = _xfce_run(mocker, ["/backdrop/screen0/monitor0/workspace0/image-style"])
    assert run.call_count == 1


def test_xfce_empty_output_makes_only_list_call(mocker):
    run = _xfce_run(mocker, [])
    assert run.call_count == 1


def test_xfce_set_calls_have_check_true(mocker):
    props = ["/backdrop/screen0/monitor0/workspace0/last-image"]
    run = _xfce_run(mocker, props)
    set_call = run.call_args_list[1]
    assert set_call[1].get("check") is True


# ── _feh ──────────────────────────────────────────────────────────────────

def test_feh_correct_argv(mocker):
    run = mocker.patch("wallpaper.subprocess.run")
    _feh(_PATH)
    run.assert_called_once_with(
        ["feh", "--bg-fill", str(_PATH)], check=True
    )


# ── _apply_windows ────────────────────────────────────────────────────────

def test_apply_windows(monkeypatch):
    mock_ctypes = MagicMock()
    mock_winreg = MagicMock()
    monkeypatch.setitem(sys.modules, "ctypes", mock_ctypes)
    monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

    wallpaper._apply_windows(_PATH)

    mock_winreg.OpenKey.assert_called_once_with(
        mock_winreg.HKEY_CURRENT_USER,
        r"Control Panel\Desktop",
        0, mock_winreg.KEY_SET_VALUE,
    )
    key = mock_winreg.OpenKey.return_value
    mock_winreg.SetValueEx.assert_any_call(
        key, "WallpaperStyle", 0, mock_winreg.REG_SZ, "22"
    )
    mock_winreg.SetValueEx.assert_any_call(
        key, "TileWallpaper", 0, mock_winreg.REG_SZ, "0"
    )
    mock_winreg.CloseKey.assert_called_once_with(key)
    mock_ctypes.windll.user32.SystemParametersInfoW.assert_called_once_with(
        20, 0, str(_PATH), 0x01 | 0x02
    )
