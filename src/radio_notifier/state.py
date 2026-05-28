from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

EPOCH = datetime.fromtimestamp(0, tz=UTC)


@dataclass
class ShowState:
    last_video_id: str | None = None
    last_notified_at: datetime | None = None


@dataclass
class State:
    path: Path
    shows: dict[str, ShowState] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> State:
        if not path.exists():
            return cls(path=path, shows={})
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        shows: dict[str, ShowState] = {}
        for sid, raw in (data.get("shows") or {}).items():
            shows[sid] = ShowState(
                last_video_id=raw.get("last_video_id"),
                last_notified_at=_parse_dt(raw.get("last_notified_at")),
            )
        return cls(path=path, shows=shows)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "shows": {
                sid: {
                    "last_video_id": s.last_video_id,
                    "last_notified_at": (
                        s.last_notified_at.isoformat() if s.last_notified_at else None
                    ),
                }
                for sid, s in self.shows.items()
            }
        }
        # atomic write
        fd, tmp_path = tempfile.mkstemp(
            prefix=".state.", suffix=".json.tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(tmp_path, self.path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def last_video_id(self, show_id: str) -> str | None:
        s = self.shows.get(show_id)
        return s.last_video_id if s else None

    def last_notified_at(self, show_id: str) -> datetime:
        s = self.shows.get(show_id)
        if s and s.last_notified_at:
            return s.last_notified_at
        return EPOCH

    def mark_notified(self, show_id: str, video_id: str, when: datetime) -> None:
        self.shows[show_id] = ShowState(last_video_id=video_id, last_notified_at=when)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)
