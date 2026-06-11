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


def is_unaired_premiere(views: int | None) -> bool:
    """True if the YouTube RSS entry's view count is exactly 0. Premiere videos
    sit at 0 views until their scheduled air time; once they go live, even a
    handful of preview hits push the counter to ≥1 within minutes.

    The trade-off is that a freshly-uploaded normal video may briefly read 0
    views too. In practice the bot fires at 11:30 JST on weekdays and the
    target radio shows are uploaded hours-to-days in advance, so a real 0 is
    overwhelmingly a premiere. Worst case is one day's pick is delayed."""
    return views == 0
