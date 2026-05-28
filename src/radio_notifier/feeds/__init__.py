from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Entry:
    """A single notifiable item (a video, a radiko link, etc)."""

    video_id: str
    title: str
    url: str
    published: datetime
    description: str = ""
    thumbnail: str | None = None
    label: str | None = None  # optional extra annotation for static URLs
