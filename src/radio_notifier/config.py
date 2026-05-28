from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from radio_notifier.shows import WEEKDAYS, Show, StaticUrl, Weekday

DEFAULT_CONFIG_PATH = Path(
    os.environ.get("RADIO_NOTIFIER_CONFIG")
    or Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    / "radio-notifier"
    / "config.toml"
)

DEFAULT_STATE_PATH = (
    Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    / "radio-notifier"
    / "state.json"
)

DEFAULT_YOUTUBE_FEED_TEMPLATE = (
    "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
)
DEFAULT_RADIKO_TIMEFREE_TEMPLATE = "https://radiko.jp/#!/ts/QRR/{ymd}{hms}"


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    state_path: Path
    youtube_feed_template: str
    radiko_timefree_template: str


@dataclass(frozen=True)
class Config:
    webhook_url: str
    settings: Settings
    shows: tuple[Show, ...]


def load_config(path: Path | None = None) -> Config:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise ConfigError(f"config file not found: {cfg_path}")
    with cfg_path.open("rb") as f:
        raw = tomllib.load(f)
    return parse_config(raw)


def parse_config(raw: dict[str, Any]) -> Config:
    discord_raw = raw.get("discord") or {}
    webhook = discord_raw.get("webhook_url")
    if not webhook or not isinstance(webhook, str):
        raise ConfigError("discord.webhook_url is required")

    settings_raw = raw.get("settings") or {}
    state_path_value = settings_raw.get("state_path")
    state_path = (
        Path(os.path.expanduser(state_path_value)) if state_path_value else DEFAULT_STATE_PATH
    )
    settings = Settings(
        state_path=state_path,
        youtube_feed_template=settings_raw.get(
            "youtube_feed_template", DEFAULT_YOUTUBE_FEED_TEMPLATE
        ),
        radiko_timefree_template=settings_raw.get(
            "radiko_timefree_template", DEFAULT_RADIKO_TIMEFREE_TEMPLATE
        ),
    )

    shows_raw = raw.get("shows") or []
    if not isinstance(shows_raw, list):
        raise ConfigError("shows must be an array of tables")
    shows = tuple(_parse_show(s, i) for i, s in enumerate(shows_raw))
    _check_unique_show_ids(shows)
    return Config(webhook_url=webhook, settings=settings, shows=shows)


def _parse_show(raw: dict[str, Any], index: int) -> Show:
    sid = raw.get("id")
    if not isinstance(sid, str) or not sid:
        raise ConfigError(f"shows[{index}].id is required")
    weekday = raw.get("weekday")
    if weekday not in WEEKDAYS:
        raise ConfigError(f"shows[{sid}].weekday must be one of {WEEKDAYS}")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise ConfigError(f"shows[{sid}].name is required")
    source = raw.get("source")
    if source not in ("youtube", "static"):
        raise ConfigError(f"shows[{sid}].source must be 'youtube' or 'static'")

    rotation_group = raw.get("rotation_group")
    if rotation_group is not None and not isinstance(rotation_group, str):
        raise ConfigError(f"shows[{sid}].rotation_group must be a string")

    channel_id = raw.get("channel_id")
    title_filter = raw.get("title_filter")
    urls_raw = raw.get("urls") or []

    if source == "youtube":
        if not isinstance(channel_id, str) or not channel_id:
            raise ConfigError(f"shows[{sid}].channel_id is required when source = 'youtube'")
        if urls_raw:
            raise ConfigError(f"shows[{sid}].urls is only valid when source = 'static'")
        urls: tuple[StaticUrl, ...] = ()
    else:
        if not urls_raw:
            raise ConfigError(f"shows[{sid}].urls is required when source = 'static'")
        urls = tuple(_parse_static_url(sid, u, i) for i, u in enumerate(urls_raw))
        if channel_id:
            raise ConfigError(f"shows[{sid}].channel_id only valid when source = 'youtube'")
        if title_filter:
            raise ConfigError(f"shows[{sid}].title_filter only valid when source = 'youtube'")

    return Show(
        id=sid,
        weekday=weekday,
        name=name,
        source=source,
        channel_id=channel_id if isinstance(channel_id, str) else None,
        title_filter=title_filter if isinstance(title_filter, str) else None,
        rotation_group=rotation_group,
        urls=urls,
    )


def _parse_static_url(sid: str, raw: dict[str, Any], index: int) -> StaticUrl:
    t = raw.get("type")
    if t not in ("literal", "radiko_timefree"):
        raise ConfigError(
            f"shows[{sid}].urls[{index}].type must be 'literal' or 'radiko_timefree'"
        )
    if t == "literal":
        url = raw.get("url")
        if not isinstance(url, str) or not url:
            raise ConfigError(f"shows[{sid}].urls[{index}].url is required for literal")
        return StaticUrl(type="literal", url=url, label=raw.get("label"))
    # radiko_timefree
    return StaticUrl(
        type="radiko_timefree",
        offset_days=int(raw.get("offset_days", 0)),
        program_start=str(raw.get("program_start", "00:00:00")),
        label=raw.get("label"),
    )


def _check_unique_show_ids(shows: tuple[Show, ...]) -> None:
    seen: set[str] = set()
    for s in shows:
        if s.id in seen:
            raise ConfigError(f"duplicate show id: {s.id}")
        seen.add(s.id)


def shows_for_weekday(shows: tuple[Show, ...], weekday: Weekday) -> list[Show]:
    return [s for s in shows if s.weekday == weekday]
