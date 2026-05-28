from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from radio_notifier.config import Config
from radio_notifier.feeds import Entry
from radio_notifier.feeds import static as static_feed
from radio_notifier.shows import WEEKDAYS, Show
from radio_notifier.state import State


@dataclass(frozen=True)
class Pick:
    show: Show
    entries: list[Entry]


FetchYouTube = Callable[[Show], list[Entry]]


def pick_for_today(
    today: date,
    config: Config,
    state: State,
    fetch_youtube: FetchYouTube,
) -> list[Pick]:
    weekday = WEEKDAYS[today.weekday()]
    todays = [s for s in config.shows if s.weekday == weekday]

    rotation_groups: dict[str, list[Show]] = defaultdict(list)
    singletons: list[Show] = []
    for s in todays:
        if s.rotation_group:
            rotation_groups[s.rotation_group].append(s)
        else:
            singletons.append(s)

    picks: list[Pick] = []
    for s in singletons:
        p = _pick_singleton(s, today, config, state, fetch_youtube)
        if p is not None:
            picks.append(p)
    for members in rotation_groups.values():
        p = _pick_rotation(members, state, fetch_youtube)
        if p is not None:
            picks.append(p)
    return picks


def _pick_singleton(
    show: Show,
    today: date,
    config: Config,
    state: State,
    fetch_youtube: FetchYouTube,
) -> Pick | None:
    if show.source == "static":
        entries = static_feed.entries_for(
            show, today, radiko_template=config.settings.radiko_timefree_template
        )
        if not entries:
            return None
        # idempotent: if we already emitted today's bundle, skip
        if state.last_video_id(show.id) == entries[-1].video_id:
            return None
        return Pick(show=show, entries=entries)

    entries = fetch_youtube(show)
    latest = _latest(entries)
    if latest is None:
        return None
    if latest.video_id == state.last_video_id(show.id):
        return None
    return Pick(show=show, entries=[latest])


def _pick_rotation(
    members: list[Show], state: State, fetch_youtube: FetchYouTube
) -> Pick | None:
    """『未通知の新着がある中で、最終通知日が最も古いチャンネル』を選ぶ。"""
    candidates = []
    for s in members:
        entries = fetch_youtube(s)
        latest = _latest(entries)
        if latest is None or latest.video_id == state.last_video_id(s.id):
            continue
        candidates.append((state.last_notified_at(s.id), s, latest))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    _, show, latest = candidates[0]
    return Pick(show=show, entries=[latest])


def _latest(entries: list[Entry]) -> Entry | None:
    if not entries:
        return None
    return max(entries, key=lambda e: e.published)
