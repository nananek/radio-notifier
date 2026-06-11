from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from radio_notifier.feeds.youtube import parse
from radio_notifier.filters import (
    is_members_only,
    is_unaired_premiere,
    is_upcoming,
    matches_title,
)

FIXTURE = Path(__file__).parent / "fixtures" / "youtube_sample.xml"


def _entries():
    return parse(FIXTURE.read_text())


def test_parse_extracts_video_id_and_url() -> None:
    entries = _entries()
    by_id = {e.video_id: e for e in entries}
    assert "vid_newest" in by_id
    assert by_id["vid_newest"].url.endswith("vid_newest")
    assert by_id["vid_newest"].thumbnail is not None


def test_title_filter_drops_unrelated() -> None:
    entries = _entries()
    matched = [e for e in entries if matches_title(e.title, "明日はなんしちょっと")]
    # vid_member's title is "【メンバー限定】鈴原希実 おまけトーク" — doesn't match
    assert {e.video_id for e in matched} == {
        "vid_newest",
        "vid_premiere",
        "vid_scheduled",
        "vid_old",
    }


def test_members_only_filter() -> None:
    entries = _entries()
    public = [e for e in entries if not is_members_only(e.title, e.description)]
    assert "vid_member" not in {e.video_id for e in public}


def test_upcoming_filter_drops_premieres() -> None:
    entries = _entries()
    now = datetime(2026, 6, 1, tzinfo=UTC)
    aired = [e for e in entries if not is_upcoming(e.published, now)]
    assert "vid_premiere" not in {e.video_id for e in aired}
    # past entries pass through
    assert {"vid_newest", "vid_old"} <= {e.video_id for e in aired}


def test_views_extracted_from_media_statistics() -> None:
    entries = _entries()
    by_id = {e.video_id: e for e in entries}
    assert by_id["vid_premiere"].views == 0
    assert by_id["vid_scheduled"].views == 0


def test_unaired_premiere_filter_drops_zero_view_entries() -> None:
    """The realistic case: published date is in the past (entry was added to
    the feed days ago) but views = 0 because the premiere hasn't aired yet.
    This catches the bug we shipped to ayaka."""
    entries = _entries()
    aired = [e for e in entries if not is_unaired_premiere(e.views)]
    assert "vid_scheduled" not in {e.video_id for e in aired}
    assert "vid_premiere" not in {e.video_id for e in aired}


def test_published_is_parsed() -> None:
    entries = _entries()
    by_id = {e.video_id: e for e in entries}
    assert by_id["vid_newest"].published > by_id["vid_old"].published
