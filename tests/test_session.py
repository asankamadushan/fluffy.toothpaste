"""Tests for session.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import session
from session import load, save


@pytest.fixture(autouse=True)
def patch_session_file(mocker, tmp_path):
    """Redirect SESSION_FILE into pytest's temp dir for every test."""
    mocker.patch("session.SESSION_FILE", new=tmp_path / "session.json")


# ── save ──────────────────────────────────────────────────────────────────

def test_save_creates_file(tmp_path, tmp_image_file, single_monitor):
    save({single_monitor.name: tmp_image_file})
    assert session.SESSION_FILE.exists()


def test_save_writes_valid_json(tmp_image_file, single_monitor):
    save({single_monitor.name: tmp_image_file})
    data = json.loads(session.SESSION_FILE.read_text())
    assert "assignments" in data
    assert data["assignments"][single_monitor.name] == str(tmp_image_file)


def test_save_creates_parent_directory(mocker, tmp_path, tmp_image_file, single_monitor):
    nested = tmp_path / "a" / "b" / "session.json"
    mocker.patch("session.SESSION_FILE", new=nested)
    save({single_monitor.name: tmp_image_file})
    assert nested.exists()


def test_save_multiple_monitors(tmp_image_file, two_monitors):
    assignments = {m.name: tmp_image_file for m in two_monitors}
    save(assignments)
    data = json.loads(session.SESSION_FILE.read_text())
    assert set(data["assignments"]) == {m.name for m in two_monitors}


def test_save_empty_assignments():
    save({})
    data = json.loads(session.SESSION_FILE.read_text())
    assert data["assignments"] == {}


# ── load ──────────────────────────────────────────────────────────────────

def test_load_missing_file_returns_empty(single_monitor):
    assert load([single_monitor]) == {}


def test_load_round_trips(tmp_image_file, single_monitor):
    save({single_monitor.name: tmp_image_file})
    result = load([single_monitor])
    assert result == {single_monitor.name: tmp_image_file}


def test_load_returns_path_objects(tmp_image_file, single_monitor):
    save({single_monitor.name: tmp_image_file})
    result = load([single_monitor])
    assert isinstance(result[single_monitor.name], Path)


def test_load_corrupted_json_returns_empty(single_monitor):
    session.SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    session.SESSION_FILE.write_text("{ not valid json }")
    assert load([single_monitor]) == {}


def test_load_wrong_structure_returns_empty(single_monitor):
    session.SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    session.SESSION_FILE.write_text(json.dumps({"wrong_key": {}}))
    assert load([single_monitor]) == {}


def test_load_filters_missing_image_file(tmp_path, single_monitor):
    gone = tmp_path / "deleted.png"
    save({single_monitor.name: gone})  # path does not exist
    assert load([single_monitor]) == {}


def test_load_filters_disconnected_monitor(tmp_image_file, single_monitor, make_monitor):
    save({single_monitor.name: tmp_image_file})
    other = make_monitor(name="DP-99")  # different monitor connected now
    assert load([other]) == {}


def test_load_partial_valid_returns_subset(tmp_image_file, tmp_path, two_monitors):
    gone = tmp_path / "gone.png"
    assignments = {
        two_monitors[0].name: tmp_image_file,  # valid
        two_monitors[1].name: gone,             # missing file
    }
    save(assignments)
    result = load(two_monitors)
    assert list(result) == [two_monitors[0].name]
    assert result[two_monitors[0].name] == tmp_image_file


def test_load_skips_disconnected_keeps_connected(tmp_image_file, two_monitors, make_monitor):
    assignments = {m.name: tmp_image_file for m in two_monitors}
    save(assignments)
    # Only first monitor is connected now
    result = load([two_monitors[0]])
    assert list(result) == [two_monitors[0].name]
