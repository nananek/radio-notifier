from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
Source = Literal["youtube", "static"]

WEEKDAYS: tuple[Weekday, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class StaticUrl:
    type: Literal["literal", "radiko_timefree"]
    url: str | None = None
    label: str | None = None
    offset_days: int = 0
    program_start: str = "00:00:00"


@dataclass(frozen=True)
class Show:
    id: str
    weekday: Weekday
    name: str
    source: Source
    channel_id: str | None = None
    title_filter: str | None = None
    rotation_group: str | None = None
    urls: tuple[StaticUrl, ...] = field(default_factory=tuple)


def weekday_of(day_index: int) -> Weekday:
    return WEEKDAYS[day_index]
