from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from radio_notifier.feeds import Entry
from radio_notifier.shows import Show

JST = timezone(timedelta(hours=9))


def entries_for(show: Show, today: date, *, radiko_template: str) -> list[Entry]:
    """Expand a static-source show's URL list into Entry objects pinned to `today`.

    Each entry's `video_id` is deterministic for the date so re-running on the
    same day is a no-op for the state.
    """
    out: list[Entry] = []
    for i, u in enumerate(show.urls):
        if u.type == "literal":
            assert u.url is not None
            out.append(
                Entry(
                    video_id=_static_id(show.id, today, i),
                    title=u.label or show.name,
                    url=u.url,
                    published=_jst_midnight(today),
                    description=u.label or "",
                    label=u.label,
                )
            )
        elif u.type == "radiko_timefree":
            broadcast = today + timedelta(days=u.offset_days)
            t = time.fromisoformat(u.program_start)
            url = radiko_template.format(
                ymd=broadcast.strftime("%Y%m%d"),
                hms=t.strftime("%H%M%S"),
            )
            out.append(
                Entry(
                    video_id=_static_id(show.id, broadcast, i),
                    title=u.label or f"{show.name} (radiko タイムフリー)",
                    url=url,
                    published=_jst_at(broadcast, t),
                    description=u.label or "radiko タイムフリー",
                    label=u.label,
                )
            )
    return out


def _jst_midnight(d: date) -> datetime:
    return datetime.combine(d, time(0, 0), tzinfo=JST)


def _jst_at(d: date, t: time) -> datetime:
    return datetime.combine(d, t, tzinfo=JST)


def _static_id(show_id: str, d: date, index: int) -> str:
    return f"{show_id}:{d.strftime('%Y%m%d')}:{index}"
