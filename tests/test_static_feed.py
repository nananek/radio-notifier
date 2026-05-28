from __future__ import annotations

from datetime import date

from radio_notifier.feeds.static import entries_for
from radio_notifier.shows import Show, StaticUrl

TEMPLATE = "https://radiko.jp/#!/ts/QRR/{ymd}{hms}"


def _show() -> Show:
    return Show(
        id="tue-hayami",
        weekday="tue",
        name="早見沙織のふり〜すたいる",
        source="static",
        urls=(
            StaticUrl(type="radiko_timefree", offset_days=0, program_start="13:00:00"),
            StaticUrl(type="literal", url="https://qlover.jp/programs/123", label="QloveR 動画"),
        ),
    )


def test_radiko_url_uses_broadcast_date() -> None:
    entries = entries_for(_show(), date(2026, 5, 26), radiko_template=TEMPLATE)
    radiko = next(e for e in entries if "radiko" in e.url)
    assert radiko.url == "https://radiko.jp/#!/ts/QRR/20260526130000"


def test_literal_url_passes_through() -> None:
    entries = entries_for(_show(), date(2026, 5, 26), radiko_template=TEMPLATE)
    literal = next(e for e in entries if "qlover" in e.url)
    assert literal.url == "https://qlover.jp/programs/123"
    assert literal.label == "QloveR 動画"


def test_static_video_ids_are_stable_per_day() -> None:
    today = date(2026, 5, 26)
    a = entries_for(_show(), today, radiko_template=TEMPLATE)
    b = entries_for(_show(), today, radiko_template=TEMPLATE)
    assert [e.video_id for e in a] == [e.video_id for e in b]


def test_offset_days_applied() -> None:
    show = Show(
        id="x",
        weekday="tue",
        name="x",
        source="static",
        urls=(StaticUrl(type="radiko_timefree", offset_days=-1, program_start="01:00:00"),),
    )
    entries = entries_for(show, date(2026, 5, 26), radiko_template=TEMPLATE)
    assert entries[0].url == "https://radiko.jp/#!/ts/QRR/20260525010000"
