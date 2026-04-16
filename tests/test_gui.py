"""Tests for gui.py — headless, no display required."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gui import DIAGRAM_H, DIAGRAM_PAD, DIAGRAM_W, App
from monitors import virtual_size

# ── Headless App fixture ───────────────────────────────────────────────────

@pytest.fixture()
def app(mocker, two_monitors):
    """
    Instantiate App without touching tkinter or a display.
    Bypass __init__ entirely; inject state manually.
    """
    mocker.patch("tkinter.Tk.__init__", return_value=None)
    mocker.patch("tkinter.Tk.title")
    mocker.patch("tkinter.Tk.resizable")
    mocker.patch("tkinter.Tk.configure")

    a = App.__new__(App)
    a.monitors = two_monitors
    a.assignments = {}
    a.selected = None
    a._thumbs = {}
    a._label_vars = {m.name: MagicMock() for m in two_monitors}
    a.canvas = MagicMock()
    a.status = MagicMock()
    a.prefs = {"pictures_dir": str(Path.home() / "Pictures")}
    return a


@pytest.fixture()
def app_single(mocker, single_monitor):
    mocker.patch("tkinter.Tk.__init__", return_value=None)
    a = App.__new__(App)
    a.monitors = [single_monitor]
    a.assignments = {}
    a.selected = None
    a._thumbs = {}
    a.canvas = MagicMock()
    a.status = MagicMock()
    return a


@pytest.fixture()
def app_portrait(mocker, portrait_monitor):
    mocker.patch("tkinter.Tk.__init__", return_value=None)
    a = App.__new__(App)
    a.monitors = [portrait_monitor]
    a.assignments = {}
    a.selected = None
    a._thumbs = {}
    a.canvas = MagicMock()
    a.status = MagicMock()
    return a


# ── _scale ────────────────────────────────────────────────────────────────

def test_scale_returns_three_values(app):
    result = app._scale()
    assert len(result) == 3


def test_scale_width_governs_for_wide_virtual_desktop(app, two_monitors):
    """
    two_monitors virtual = 4480×1440;
    width governs when usable_w/vw < usable_h/vh.
    """
    scale, ox, oy = app._scale()
    vw, vh = virtual_size(two_monitors)
    usable_w = DIAGRAM_W - DIAGRAM_PAD * 2
    usable_h = DIAGRAM_H - DIAGRAM_PAD * 2
    expected_scale = min(usable_w / vw, usable_h / vh)
    assert abs(scale - expected_scale) < 1e-9


def test_scale_height_governs_for_portrait_monitor(app_portrait, portrait_monitor):
    scale, _, _ = app_portrait._scale()
    vw, vh = virtual_size([portrait_monitor])
    usable_w = DIAGRAM_W - DIAGRAM_PAD * 2
    usable_h = DIAGRAM_H - DIAGRAM_PAD * 2
    expected_scale = min(usable_w / vw, usable_h / vh)
    assert abs(scale - expected_scale) < 1e-9
    # height dimension should drive the scale (smaller ratio)
    assert expected_scale == pytest.approx(usable_h / vh)


def test_scale_offsets_are_integers(app):
    scale, ox, oy = app._scale()
    assert isinstance(ox, int)
    assert isinstance(oy, int)


def test_scale_origin_monitor_rect_starts_at_offset(app_single, single_monitor):
    """Monitor at (0,0) in virtual space → x1,y1 equal to ox,oy."""
    scale, ox, oy = app_single._scale()
    x1, y1, x2, y2 = app_single._monitor_rect(single_monitor)
    assert x1 == ox
    assert y1 == oy


# ── _monitor_rect ─────────────────────────────────────────────────────────

def test_monitor_rect_returns_four_ints(app, two_monitors):
    rect = app._monitor_rect(two_monitors[0])
    assert len(rect) == 4
    assert all(isinstance(v, int) for v in rect)


def test_monitor_rect_x2_gt_x1_and_y2_gt_y1(app, two_monitors):
    for m in two_monitors:
        x1, y1, x2, y2 = app._monitor_rect(m)
        assert x2 > x1
        assert y2 > y1


def test_monitor_rects_do_not_overlap(app, two_monitors):
    """Side-by-side monitors: right edge of first ≤ left edge of second."""
    _, _, x2_first, _ = app._monitor_rect(two_monitors[0])
    x1_second, _, _, _ = app._monitor_rect(two_monitors[1])
    assert x2_first <= x1_second


def test_portrait_monitor_rect_is_taller_than_wide(app_portrait, portrait_monitor):
    x1, y1, x2, y2 = app_portrait._monitor_rect(portrait_monitor)
    assert (y2 - y1) > (x2 - x1)


def test_offset_monitor_rect_displaced_right(app, two_monitors):
    """HDMI-1 at x=1920 must produce x1 > 0 on the canvas."""
    x1, _, _, _ = app._monitor_rect(two_monitors[1])
    assert x1 > 0


def test_monitor_rect_width_proportional_to_scale(app, two_monitors):
    scale, _, _ = app._scale()
    for m in two_monitors:
        x1, _, x2, _ = app._monitor_rect(m)
        assert (x2 - x1) == int(m.width * scale)


# ── _on_canvas_click ──────────────────────────────────────────────────────

def _make_event(x, y):
    e = MagicMock()
    e.x = x
    e.y = y
    return e


def test_canvas_click_inside_first_monitor_selects_it(app, two_monitors, mocker):
    mocker.patch.object(app, "_draw_diagram")
    x1, y1, x2, y2 = app._monitor_rect(two_monitors[0])
    app._on_canvas_click(_make_event((x1 + x2) // 2, (y1 + y2) // 2))
    assert app.selected == two_monitors[0].name


def test_canvas_click_inside_second_monitor_selects_it(app, two_monitors, mocker):
    mocker.patch.object(app, "_draw_diagram")
    x1, y1, x2, y2 = app._monitor_rect(two_monitors[1])
    app._on_canvas_click(_make_event((x1 + x2) // 2, (y1 + y2) // 2))
    assert app.selected == two_monitors[1].name


def test_canvas_click_outside_all_rects_does_not_change_selection(app, mocker):
    mocker.patch.object(app, "_draw_diagram")
    app.selected = "eDP-1"
    app._on_canvas_click(_make_event(-5, -5))
    assert app.selected == "eDP-1"


def test_canvas_click_calls_draw_diagram_on_hit(app, two_monitors, mocker):
    draw = mocker.patch.object(app, "_draw_diagram")
    x1, y1, x2, y2 = app._monitor_rect(two_monitors[0])
    app._on_canvas_click(_make_event((x1 + x2) // 2, (y1 + y2) // 2))
    draw.assert_called_once()


# ── _on_canvas_double_click ───────────────────────────────────────────────

def test_double_click_opens_browse_for_hit_monitor(app, two_monitors, mocker):
    browse = mocker.patch.object(app, "_browse")
    x1, y1, x2, y2 = app._monitor_rect(two_monitors[0])
    app._on_canvas_double_click(_make_event((x1 + x2) // 2, (y1 + y2) // 2))
    browse.assert_called_once_with(
        two_monitors[0], app._label_vars[two_monitors[0].name]
    )


def test_double_click_second_monitor_opens_browse_for_it(app, two_monitors, mocker):
    browse = mocker.patch.object(app, "_browse")
    x1, y1, x2, y2 = app._monitor_rect(two_monitors[1])
    app._on_canvas_double_click(_make_event((x1 + x2) // 2, (y1 + y2) // 2))
    browse.assert_called_once_with(
        two_monitors[1], app._label_vars[two_monitors[1].name]
    )


def test_double_click_outside_all_rects_does_nothing(app, two_monitors, mocker):
    browse = mocker.patch.object(app, "_browse")
    app._on_canvas_double_click(_make_event(-5, -5))
    browse.assert_not_called()


def test_double_click_passes_correct_label_var(app, two_monitors, mocker):
    """label_var passed must be the one keyed to the clicked monitor."""
    browse = mocker.patch.object(app, "_browse")
    x1, y1, x2, y2 = app._monitor_rect(two_monitors[1])
    app._on_canvas_double_click(_make_event((x1 + x2) // 2, (y1 + y2) // 2))
    _, passed_var = browse.call_args[0]
    assert passed_var is app._label_vars[two_monitors[1].name]


# ── _browse ───────────────────────────────────────────────────────────────

def test_browse_updates_assignment_and_selected(app, two_monitors, mocker):
    mocker.patch("gui.filedialog.askopenfilename", return_value="/home/user/sunset.png")
    mocker.patch.object(app, "_draw_diagram")
    mocker.patch.object(app, "_set_status")
    label_var = MagicMock()

    app._browse(two_monitors[0], label_var)

    assert app.assignments[two_monitors[0].name] == Path("/home/user/sunset.png")
    assert app.selected == two_monitors[0].name
    label_var.set.assert_called_once_with("sunset.png")


def test_browse_cancelled_is_noop(app, two_monitors, mocker):
    mocker.patch("gui.filedialog.askopenfilename", return_value="")
    draw = mocker.patch.object(app, "_draw_diagram")
    label_var = MagicMock()

    app._browse(two_monitors[0], label_var)

    assert two_monitors[0].name not in app.assignments
    draw.assert_not_called()
    label_var.set.assert_not_called()


def test_browse_calls_draw_diagram_on_selection(app, two_monitors, mocker):
    mocker.patch("gui.filedialog.askopenfilename", return_value="/img.png")
    draw = mocker.patch.object(app, "_draw_diagram")
    mocker.patch.object(app, "_set_status")
    app._browse(two_monitors[0], MagicMock())
    draw.assert_called_once()


# ── _clear ────────────────────────────────────────────────────────────────

def test_clear_removes_assignment(app, two_monitors, mocker):
    mocker.patch.object(app, "_draw_diagram")
    app.assignments["eDP-1"] = Path("/img.png")
    label_var = MagicMock()
    app._clear(two_monitors[0], label_var)
    assert "eDP-1" not in app.assignments
    label_var.set.assert_called_once_with("—")


def test_clear_on_unassigned_monitor_does_not_raise(app, two_monitors, mocker):
    mocker.patch.object(app, "_draw_diagram")
    app._clear(two_monitors[0], MagicMock())  # must not raise


def test_clear_calls_draw_diagram(app, two_monitors, mocker):
    draw = mocker.patch.object(app, "_draw_diagram")
    app._clear(two_monitors[0], MagicMock())
    draw.assert_called_once()


# ── _apply ────────────────────────────────────────────────────────────────

def test_apply_empty_assignments_sets_status_and_returns_early(app, mocker):
    build = mocker.patch("gui.stitcher.build")
    set_status = mocker.patch.object(app, "_set_status")
    app.assignments = {}
    app._apply()
    set_status.assert_called_once_with("No images assigned.")
    build.assert_not_called()


def test_apply_calls_stitcher_and_wallpaper(app, mocker):
    fake_path = Path("/tmp/wallpaper.png")
    build = mocker.patch("gui.stitcher.build", return_value=fake_path)
    # wallpaper is imported locally inside _apply, so patch it in its own module
    wp_apply = mocker.patch("wallpaper.apply")
    mocker.patch.object(app, "_set_status")
    mocker.patch.object(app, "update")

    app.assignments = {"eDP-1": Path("/img.png")}
    app._apply()

    build.assert_called_once_with(app.assignments, app.monitors)
    wp_apply.assert_called_once_with(fake_path)


def test_apply_success_sets_status(app, mocker):
    mocker.patch("gui.stitcher.build", return_value=Path("/tmp/x.png"))
    mocker.patch("wallpaper.apply")  # local import — patch in wallpaper module
    set_status = mocker.patch.object(app, "_set_status")
    mocker.patch.object(app, "update")

    app.assignments = {"eDP-1": Path("/img.png")}
    app._apply()

    set_status.assert_called_with("Applied successfully.")


def test_apply_exception_shows_error_dialog(app, mocker):
    mocker.patch("gui.stitcher.build", side_effect=RuntimeError("disk full"))
    showerror = mocker.patch("gui.messagebox.showerror")
    mocker.patch("wallpaper.apply")
    mocker.patch.object(app, "_set_status")
    mocker.patch.object(app, "update")

    app.assignments = {"eDP-1": Path("/img.png")}
    app._apply()

    showerror.assert_called_once_with("Error", "disk full")


def test_apply_exception_sets_failed_status(app, mocker):
    mocker.patch("gui.stitcher.build", side_effect=RuntimeError("oops"))
    mocker.patch("gui.messagebox.showerror")
    mocker.patch("wallpaper.apply")
    set_status = mocker.patch.object(app, "_set_status")
    mocker.patch.object(app, "update")

    app.assignments = {"eDP-1": Path("/img.png")}
    app._apply()

    set_status.assert_called_with("Failed — see error dialog.")


def test_apply_saves_session_on_success(app, mocker):
    mocker.patch("gui.stitcher.build", return_value=Path("/tmp/x.png"))
    mocker.patch("wallpaper.apply")
    save = mocker.patch("gui.session.save")
    mocker.patch.object(app, "_set_status")
    mocker.patch.object(app, "update")

    app.assignments = {"eDP-1": Path("/img.png")}
    app._apply()

    save.assert_called_once_with(app.assignments)


def test_apply_does_not_save_session_on_failure(app, mocker):
    mocker.patch("gui.stitcher.build", side_effect=RuntimeError("oops"))
    mocker.patch("gui.messagebox.showerror")
    save = mocker.patch("gui.session.save")
    mocker.patch.object(app, "_set_status")
    mocker.patch.object(app, "update")

    app.assignments = {"eDP-1": Path("/img.png")}
    app._apply()

    save.assert_not_called()
