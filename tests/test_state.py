from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from radio_notifier.state import EPOCH, State


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    s = State.load(tmp_path / "nope.json")
    assert s.shows == {}
    assert s.last_notified_at("anything") == EPOCH


def test_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    s = State.load(path)
    when = datetime(2026, 5, 28, 11, 30, tzinfo=UTC)
    s.mark_notified("mon-x", "vid-1", when)
    s.save()

    s2 = State.load(path)
    assert s2.last_video_id("mon-x") == "vid-1"
    assert s2.last_notified_at("mon-x") == when


def test_atomic_write_creates_no_temp_leftover(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    s = State.load(path)
    s.mark_notified("x", "v", datetime(2026, 1, 1, tzinfo=UTC))
    s.save()
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".state.")]
    assert leftovers == []


def test_creates_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "state.json"
    s = State.load(path)
    s.mark_notified("x", "v", datetime(2026, 1, 1, tzinfo=UTC))
    s.save()
    assert path.exists()
