"""Tests for monitors.py."""

from __future__ import annotations

from subprocess import CompletedProcess

import pytest

from monitors import _XRANDR_RE, Monitor, _from_xrandr, get_monitors, virtual_size

# ── xrandr regex ──────────────────────────────────────────────────────────

XRANDR_LANDSCAPE_PRIMARY = (
    "eDP-1 connected primary 2560x1440+0+0 "
    "(normal left inverted right x axis y axis) 344mm x 193mm"
)
XRANDR_LANDSCAPE_SECONDARY = (
    "HDMI-1 connected 1920x1080+2560+0 "
    "(normal left inverted right x axis y axis) 527mm x 296mm"
)
XRANDR_PORTRAIT = (
    "HDMI-1 connected 1440x2560+2560+0 right "
    "(normal left inverted right x axis y axis) 527mm x 296mm"
)


def test_regex_landscape_primary():
    m = _XRANDR_RE.match(XRANDR_LANDSCAPE_PRIMARY)
    assert m is not None
    assert m.group(1) == "eDP-1"
    assert m.group(2) == "primary "
    assert m.group(3) == "2560"
    assert m.group(4) == "1440"
    assert m.group(5) == "0"
    assert m.group(6) == "0"


def test_regex_landscape_secondary():
    m = _XRANDR_RE.match(XRANDR_LANDSCAPE_SECONDARY)
    assert m is not None
    assert m.group(1) == "HDMI-1"
    assert m.group(2) is None  # no "primary"
    assert m.group(3) == "1920"
    assert m.group(5) == "2560"
    assert m.group(6) == "0"


def test_regex_portrait_xrandr_reports_post_rotation_dims():
    """xrandr reports effective rotated dims — regex must parse them as-is."""
    m = _XRANDR_RE.match(XRANDR_PORTRAIT)
    assert m is not None
    assert m.group(3) == "1440"  # width
    assert m.group(4) == "2560"  # height (tall = portrait)


@pytest.mark.parametrize("line", [
    "VGA-1 disconnected (normal left inverted right x axis y axis)",
    "Screen 0: minimum 8 x 8, current 5120 x 1440, maximum 32767 x 32767",
    "   1920x1080     60.00*+  50.00",
    "",
    "   connected 1920x1080+0+0",  # no monitor name
])
def test_regex_non_monitor_lines_do_not_match(line):
    assert _XRANDR_RE.match(line) is None


# ── _from_xrandr ──────────────────────────────────────────────────────────

XRANDR_OUTPUT_TWO_CONNECTED = "\n".join([
    "Screen 0: minimum 8 x 8, current 4480 x 1440",
    XRANDR_LANDSCAPE_PRIMARY,
    "   2560x1440     60.00*+",
    XRANDR_LANDSCAPE_SECONDARY,
    "   1920x1080     60.00*+",
    "VGA-1 disconnected (normal left inverted right x axis y axis)",
])


def test_from_xrandr_parses_two_connected_monitors(mocker):
    mocker.patch(
        "monitors.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=XRANDR_OUTPUT_TWO_CONNECTED),
    )
    monitors = _from_xrandr()
    assert len(monitors) == 2


def test_from_xrandr_primary_flag_set_correctly(mocker):
    mocker.patch(
        "monitors.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=XRANDR_OUTPUT_TWO_CONNECTED),
    )
    monitors = _from_xrandr()
    primary = [m for m in monitors if m.primary]
    non_primary = [m for m in monitors if not m.primary]
    assert len(primary) == 1
    assert primary[0].name == "eDP-1"
    assert len(non_primary) == 1
    assert non_primary[0].name == "HDMI-1"


def test_from_xrandr_monitor_fields(mocker):
    mocker.patch(
        "monitors.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=XRANDR_OUTPUT_TWO_CONNECTED),
    )
    monitors = {m.name: m for m in _from_xrandr()}
    edp = monitors["eDP-1"]
    assert edp.x == 0 and edp.y == 0
    assert edp.width == 2560 and edp.height == 1440

    hdmi = monitors["HDMI-1"]
    assert hdmi.x == 2560 and hdmi.y == 0
    assert hdmi.width == 1920 and hdmi.height == 1080


def test_from_xrandr_single_monitor(mocker):
    output = XRANDR_LANDSCAPE_PRIMARY + "\n   2560x1440     60.00*+"
    mocker.patch(
        "monitors.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=output),
    )
    monitors = _from_xrandr()
    assert len(monitors) == 1
    assert monitors[0].primary is True


def test_from_xrandr_no_connected_monitors(mocker):
    output = (
        "Screen 0: minimum 8 x 8\n"
        "VGA-1 disconnected (normal left inverted right x axis y axis)\n"
    )
    mocker.patch(
        "monitors.subprocess.run",
        return_value=CompletedProcess([], 0, stdout=output),
    )
    assert _from_xrandr() == []


# ── get_monitors dispatch ─────────────────────────────────────────────────


def test_get_monitors_linux_calls_from_xrandr(mocker):
    mocker.patch("monitors.platform.system", return_value="Linux")
    mock = mocker.patch("monitors._from_xrandr", return_value=[])
    get_monitors()
    mock.assert_called_once()


def test_get_monitors_windows_calls_from_windows(mocker):
    mocker.patch("monitors.platform.system", return_value="Windows")
    mock = mocker.patch("monitors._from_windows", return_value=[])
    get_monitors()
    mock.assert_called_once()


def test_get_monitors_unsupported_platform_raises(mocker):
    mocker.patch("monitors.platform.system", return_value="Darwin")
    with pytest.raises(NotImplementedError, match="Darwin"):
        get_monitors()


# ── virtual_size ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("monitors,expected", [
    # Single monitor at origin
    (
        [Monitor("eDP-1", 0, 0, 1920, 1080, True)],
        (1920, 1080),
    ),
    # Side-by-side (width = sum, height = max)
    (
        [
            Monitor("A", 0, 0, 1920, 1080, True),
            Monitor("B", 1920, 0, 2560, 1440, False),
        ],
        (4480, 1440),
    ),
    # Stacked vertically
    (
        [
            Monitor("A", 0, 0, 1920, 1080, True),
            Monitor("B", 0, 1080, 1920, 1080, False),
        ],
        (1920, 2160),
    ),
    # Primary not at origin
    (
        [
            Monitor("A", 1920, 1080, 1920, 1080, True),
            Monitor("B", 0, 0, 1920, 1080, False),
        ],
        (3840, 2160),
    ),
    # Portrait monitor
    (
        [Monitor("HDMI-1", 0, 0, 1080, 1920, True)],
        (1080, 1920),
    ),
    # L-shape (three monitors)
    (
        [
            Monitor("A", 0,    0,    1920, 1080, False),
            Monitor("B", 1920, 0,    1920, 1080, False),
            Monitor("C", 0,    1080, 1920, 1080, True),
        ],
        (3840, 2160),
    ),
    # Portrait beside landscape
    (
        [
            Monitor("A", 0, 0, 1920, 1080, True),
            Monitor("B", 1920, 0, 1080, 1920, False),
        ],
        (3000, 1920),
    ),
])
def test_virtual_size(monitors, expected):
    assert virtual_size(monitors) == expected
