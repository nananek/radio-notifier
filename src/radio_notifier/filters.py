from __future__ import annotations

from datetime import UTC, datetime

# Defensive keyword filter for YouTube members-only videos.
# The public RSS feed normally hides member-only content, but channels sometimes
# leak preview / unlisted member videos; we err on the side of skipping these.
_MEMBERS_KEYWORDS = (
    "メンバー限定",
    "メンバーシップ限定",
    "会員限定",
    "【会員限定】",
    "members only",
    "member-only",
    "for members",
    "members-first",
)


def is_members_only(title: str, description: str = "") -> bool:
    haystack = f"{title}\n{description}".lower()
    return any(k.lower() in haystack for k in _MEMBERS_KEYWORDS)


def matches_title(title: str, needle: str | None) -> bool:
    if not needle:
        return True
    return needle in title


def is_upcoming(published: datetime, now: datetime | None = None) -> bool:
    """True if `published` is in the future — i.e. a scheduled premiere or upcoming
    live broadcast. YouTube RSS lists these entries before they air, with
    `published` set to the scheduled start time. We don't want to notify a URL
    that's not yet playable."""
    if now is None:
        now = datetime.now(UTC)
    return published > now
