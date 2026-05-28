from __future__ import annotations

from datetime import UTC, datetime

from radio_notifier.discord import build_payload
from radio_notifier.feeds import Entry
from radio_notifier.selector import Pick
from radio_notifier.shows import Show


def _pick(show_id: str, weekday: str, name: str, entries: list[Entry]) -> Pick:
    return Pick(
        show=Show(id=show_id, weekday=weekday, name=name, source="youtube",
                  channel_id="UC1"),
        entries=entries,
    )


def test_payload_embeds_per_entry() -> None:
    entries = [
        Entry(
            video_id="v1",
            title="第99回",
            url="https://www.youtube.com/watch?v=v1",
            published=datetime(2026, 5, 25, tzinfo=UTC),
            thumbnail="https://i.ytimg.com/vi/v1/hqdefault.jpg",
        )
    ]
    payload = build_payload([_pick("mon", "mon", "鈴原希実", entries)])
    embed = payload["embeds"][0]
    assert embed["title"].startswith("[月]")
    assert "鈴原希実" in embed["title"]
    assert embed["url"].endswith("v1")
    assert embed["description"] == "第99回"
    assert embed["thumbnail"]["url"].startswith("https://")


def test_payload_caps_at_ten_embeds() -> None:
    entries = [
        Entry(video_id=f"v{i}", title="x", url=f"https://e/v{i}",
              published=datetime(2026, 1, 1, tzinfo=UTC))
        for i in range(15)
    ]
    payload = build_payload([_pick("mon", "mon", "x", entries)])
    assert len(payload["embeds"]) == 10
