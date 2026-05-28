from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from radio_notifier.config import Config, Settings
from radio_notifier.feeds import Entry
from radio_notifier.selector import pick_for_today
from radio_notifier.shows import Show, StaticUrl
from radio_notifier.state import State


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        state_path=tmp_path / "state.json",
        youtube_feed_template="https://example.invalid/{channel_id}",
        radiko_timefree_template="https://radiko.jp/#!/ts/QRR/{ymd}{hms}",
    )


def _config(tmp_path: Path, shows: tuple[Show, ...]) -> Config:
    return Config(
        webhook_url="https://discord/test",
        settings=_settings(tmp_path),
        shows=shows,
    )


def _yt_entry(vid: str, when: datetime) -> Entry:
    return Entry(
        video_id=vid,
        title=f"Title {vid}",
        url=f"https://www.youtube.com/watch?v={vid}",
        published=when,
        description="",
        thumbnail=None,
    )


def test_thursday_rotation_picks_channel_with_oldest_last_notification(tmp_path: Path) -> None:
    a = Show(id="thu-a", weekday="thu", name="A", source="youtube",
             channel_id="UCa", rotation_group="thu")
    b = Show(id="thu-b", weekday="thu", name="B", source="youtube",
             channel_id="UCb", rotation_group="thu")
    c = Show(id="thu-c", weekday="thu", name="C", source="youtube",
             channel_id="UCc", rotation_group="thu")
    cfg = _config(tmp_path, (a, b, c))

    state = State.load(tmp_path / "state.json")
    # All 3 have un-notified new videos.
    feeds = {
        "thu-a": [_yt_entry("a-new", datetime(2026, 5, 28, tzinfo=UTC))],
        "thu-b": [_yt_entry("b-new", datetime(2026, 5, 27, tzinfo=UTC))],
        "thu-c": [_yt_entry("c-new", datetime(2026, 5, 26, tzinfo=UTC))],
    }
    # B was last notified longest ago.
    state.mark_notified("thu-a", "a-old", datetime(2026, 5, 21, tzinfo=UTC))
    state.mark_notified("thu-b", "b-old", datetime(2026, 5, 7, tzinfo=UTC))
    state.mark_notified("thu-c", "c-old", datetime(2026, 5, 14, tzinfo=UTC))

    picks = pick_for_today(date(2026, 5, 28), cfg, state, lambda s: feeds[s.id])
    assert len(picks) == 1
    assert picks[0].show.id == "thu-b"
    assert picks[0].entries[0].video_id == "b-new"


def test_thursday_rotation_skips_channels_without_new(tmp_path: Path) -> None:
    a = Show(id="thu-a", weekday="thu", name="A", source="youtube",
             channel_id="UCa", rotation_group="thu")
    b = Show(id="thu-b", weekday="thu", name="B", source="youtube",
             channel_id="UCb", rotation_group="thu")
    cfg = _config(tmp_path, (a, b))

    state = State.load(tmp_path / "state.json")
    feeds = {
        "thu-a": [_yt_entry("a-old", datetime(2026, 5, 1, tzinfo=UTC))],
        "thu-b": [_yt_entry("b-new", datetime(2026, 5, 27, tzinfo=UTC))],
    }
    # A already notified for its latest; B has nothing notified.
    state.mark_notified("thu-a", "a-old", datetime(2026, 5, 1, tzinfo=UTC))

    picks = pick_for_today(date(2026, 5, 28), cfg, state, lambda s: feeds[s.id])
    assert len(picks) == 1
    assert picks[0].show.id == "thu-b"


def test_thursday_rotation_returns_nothing_when_all_caught_up(tmp_path: Path) -> None:
    a = Show(id="thu-a", weekday="thu", name="A", source="youtube",
             channel_id="UCa", rotation_group="thu")
    cfg = _config(tmp_path, (a,))

    state = State.load(tmp_path / "state.json")
    feeds = {"thu-a": [_yt_entry("a-old", datetime(2026, 5, 1, tzinfo=UTC))]}
    state.mark_notified("thu-a", "a-old", datetime(2026, 5, 1, tzinfo=UTC))

    picks = pick_for_today(date(2026, 5, 28), cfg, state, lambda s: feeds[s.id])
    assert picks == []


def test_monday_youtube_singleton(tmp_path: Path) -> None:
    show = Show(id="mon", weekday="mon", name="X", source="youtube",
                channel_id="UCx", title_filter=None)
    cfg = _config(tmp_path, (show,))
    state = State.load(tmp_path / "state.json")
    feeds = {"mon": [
        _yt_entry("v1", datetime(2026, 5, 25, tzinfo=UTC)),
        _yt_entry("v2", datetime(2026, 5, 18, tzinfo=UTC)),
    ]}
    picks = pick_for_today(date(2026, 5, 25), cfg, state, lambda s: feeds[s.id])
    assert len(picks) == 1
    assert picks[0].entries[0].video_id == "v1"


def test_tuesday_static_emits_both_urls(tmp_path: Path) -> None:
    show = Show(
        id="tue", weekday="tue", name="Hayami", source="static",
        urls=(
            StaticUrl(type="radiko_timefree", offset_days=0, program_start="13:00:00"),
            StaticUrl(type="literal", url="https://qlover.jp/programs/x", label="QloveR"),
        ),
    )
    cfg = _config(tmp_path, (show,))
    state = State.load(tmp_path / "state.json")
    picks = pick_for_today(date(2026, 5, 26), cfg, state,
                           lambda s: pytest.fail("youtube fetch unexpected"))
    assert len(picks) == 1
    assert len(picks[0].entries) == 2
    urls = {e.url for e in picks[0].entries}
    assert "https://radiko.jp/#!/ts/QRR/20260526130000" in urls
    assert "https://qlover.jp/programs/x" in urls


def test_static_idempotent_within_a_day(tmp_path: Path) -> None:
    show = Show(
        id="tue", weekday="tue", name="x", source="static",
        urls=(StaticUrl(type="literal", url="https://example/a"),),
    )
    cfg = _config(tmp_path, (show,))
    state = State.load(tmp_path / "state.json")
    today = date(2026, 5, 26)
    first = pick_for_today(today, cfg, state, lambda s: [])
    assert first
    # simulate that the run marked the bundle as notified
    state.mark_notified(
        show.id, first[0].entries[-1].video_id,
        datetime(2026, 5, 26, 11, 30, tzinfo=UTC),
    )
    second = pick_for_today(today, cfg, state, lambda s: [])
    assert second == []
