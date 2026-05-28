from __future__ import annotations

import pytest

from radio_notifier.config import ConfigError, parse_config


def _base() -> dict:
    return {
        "discord": {"webhook_url": "https://discord.com/api/webhooks/test"},
        "settings": {},
        "shows": [],
    }


def test_parse_minimum_youtube_show() -> None:
    raw = _base()
    raw["shows"] = [
        {
            "id": "mon-x",
            "weekday": "mon",
            "name": "Show X",
            "source": "youtube",
            "channel_id": "UCabc",
            "title_filter": "X",
        }
    ]
    cfg = parse_config(raw)
    assert cfg.webhook_url.endswith("/test")
    (show,) = cfg.shows
    assert show.id == "mon-x"
    assert show.source == "youtube"
    assert show.channel_id == "UCabc"


def test_parse_static_show_with_urls() -> None:
    raw = _base()
    raw["shows"] = [
        {
            "id": "tue-x",
            "weekday": "tue",
            "name": "Show Tue",
            "source": "static",
            "urls": [
                {"type": "radiko_timefree", "offset_days": 0, "program_start": "13:00:00"},
                {"type": "literal", "url": "https://example.com/x", "label": "QloveR"},
            ],
        }
    ]
    cfg = parse_config(raw)
    (show,) = cfg.shows
    assert show.source == "static"
    assert len(show.urls) == 2
    assert show.urls[0].type == "radiko_timefree"
    assert show.urls[1].url == "https://example.com/x"


def test_missing_webhook_url() -> None:
    raw = _base()
    raw["discord"] = {}
    with pytest.raises(ConfigError, match="webhook_url"):
        parse_config(raw)


def test_rejects_youtube_without_channel_id() -> None:
    raw = _base()
    raw["shows"] = [
        {"id": "x", "weekday": "mon", "name": "x", "source": "youtube"}
    ]
    with pytest.raises(ConfigError, match="channel_id"):
        parse_config(raw)


def test_rejects_static_without_urls() -> None:
    raw = _base()
    raw["shows"] = [{"id": "x", "weekday": "tue", "name": "x", "source": "static"}]
    with pytest.raises(ConfigError, match="urls"):
        parse_config(raw)


def test_duplicate_show_ids() -> None:
    raw = _base()
    raw["shows"] = [
        {"id": "x", "weekday": "mon", "name": "x", "source": "youtube", "channel_id": "UC1"},
        {"id": "x", "weekday": "tue", "name": "x", "source": "youtube", "channel_id": "UC2"},
    ]
    with pytest.raises(ConfigError, match="duplicate"):
        parse_config(raw)


def test_example_config_file_parses() -> None:
    import tomllib
    from pathlib import Path

    example = Path(__file__).parent.parent / "config.example.toml"
    raw = tomllib.loads(example.read_text())
    raw["discord"]["webhook_url"] = "https://discord.com/api/webhooks/test"
    cfg = parse_config(raw)
    assert len(cfg.shows) >= 5
    weekdays = {s.weekday for s in cfg.shows}
    assert {"mon", "tue", "wed", "thu", "fri"} <= weekdays
