from __future__ import annotations

from typing import Any

import httpx

from radio_notifier.selector import Pick

WEEKDAY_LABEL = {
    "mon": "月", "tue": "火", "wed": "水", "thu": "木",
    "fri": "金", "sat": "土", "sun": "日",
}

DEFAULT_TIMEOUT = 15.0


def post(
    webhook_url: str,
    picks: list[Pick],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> None:
    if not picks:
        return
    payload = build_payload(picks)
    if client is None:
        with httpx.Client(timeout=timeout) as c:
            resp = c.post(webhook_url, json=payload)
    else:
        resp = client.post(webhook_url, json=payload)
    resp.raise_for_status()


def build_payload(picks: list[Pick]) -> dict[str, Any]:
    embeds: list[dict[str, Any]] = []
    for pick in picks:
        prefix = f"[{WEEKDAY_LABEL.get(pick.show.weekday, pick.show.weekday)}]"
        for entry in pick.entries:
            embed: dict[str, Any] = {
                "title": f"{prefix} {pick.show.name}",
                "url": entry.url,
                "description": entry.title,
            }
            if entry.thumbnail:
                embed["thumbnail"] = {"url": entry.thumbnail}
            if entry.published.timestamp() > 0:
                embed["timestamp"] = entry.published.isoformat()
            if entry.label and entry.label != pick.show.name:
                embed["footer"] = {"text": entry.label}
            embeds.append(embed)
    # Discord caps embeds at 10 per message
    return {"username": "radio-notifier", "embeds": embeds[:10]}
