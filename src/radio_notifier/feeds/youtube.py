from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx

from radio_notifier.feeds import Entry
from radio_notifier.filters import is_members_only, matches_title

DEFAULT_TIMEOUT = 15.0


def fetch_url(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> str:
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def parse(xml: str) -> list[Entry]:
    parsed = feedparser.parse(xml)
    entries: list[Entry] = []
    for raw in parsed.entries:
        entry = _to_entry(raw)
        if entry is not None:
            entries.append(entry)
    return entries


def fetch(
    channel_id: str,
    *,
    template: str,
    title_filter: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[Entry]:
    url = template.format(channel_id=channel_id)
    xml = fetch_url(url, timeout=timeout)
    entries = parse(xml)
    return [
        e
        for e in entries
        if matches_title(e.title, title_filter) and not is_members_only(e.title, e.description)
    ]


def _to_entry(raw: Any) -> Entry | None:
    yt_video_id = raw.get("yt_videoid") or _extract_video_id(raw.get("id", ""))
    if not yt_video_id:
        return None
    link = raw.get("link") or f"https://www.youtube.com/watch?v={yt_video_id}"
    published = _to_datetime(raw.get("published_parsed"))
    thumbnail = None
    media_thumb = raw.get("media_thumbnail")
    if isinstance(media_thumb, list) and media_thumb:
        thumbnail = media_thumb[0].get("url")
    description = ""
    if isinstance(raw.get("media_description"), str):
        description = raw["media_description"]
    elif isinstance(raw.get("summary"), str):
        description = raw["summary"]
    return Entry(
        video_id=yt_video_id,
        title=raw.get("title", ""),
        url=link,
        published=published,
        description=description,
        thumbnail=thumbnail,
    )


def _extract_video_id(entry_id: str) -> str | None:
    # entry id form: "yt:video:VIDEOID"
    if entry_id.startswith("yt:video:"):
        return entry_id.split(":", 2)[2]
    return None


def _to_datetime(time_tuple: Any) -> datetime:
    if not time_tuple:
        return datetime.fromtimestamp(0, tz=UTC)
    import calendar

    epoch = calendar.timegm(time_tuple)
    return datetime.fromtimestamp(epoch, tz=UTC)
