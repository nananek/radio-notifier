from __future__ import annotations

import argparse
import logging
from datetime import UTC, date, datetime, timezone
from pathlib import Path

from radio_notifier import discord
from radio_notifier.config import DEFAULT_CONFIG_PATH, Config, load_config
from radio_notifier.feeds import youtube as yt
from radio_notifier.selector import pick_for_today
from radio_notifier.shows import Show
from radio_notifier.state import State

log = logging.getLogger("radio_notifier")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="radio-notifier")
    p.add_argument("-c", "--config", type=Path, default=None,
                   help=f"path to config file (default: {DEFAULT_CONFIG_PATH})")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="show configured shows")

    p_run = sub.add_parser("run", help="fetch and notify (updates state)")
    p_run.add_argument("--date", type=_parse_date, default=None)

    p_dry = sub.add_parser("dry-run", help="show picks without notifying")
    p_dry.add_argument("--date", type=_parse_date, default=None)

    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        cfg = load_config(args.config)
    except Exception as e:
        log.error("config error: %s", e)
        return 2

    if args.cmd == "list":
        return _cmd_list(cfg)
    if args.cmd == "dry-run":
        return _cmd_dry_run(cfg, args.date or _today())
    if args.cmd == "run":
        return _cmd_run(cfg, args.date or _today())
    return 2


def _cmd_list(cfg: Config) -> int:
    for s in cfg.shows:
        rg = f" [rotation={s.rotation_group}]" if s.rotation_group else ""
        src = f"{s.source}({s.channel_id})" if s.source == "youtube" else "static"
        print(f"  {s.weekday}  {s.id:20s}  {s.name}  -- {src}{rg}")
    return 0


def _cmd_dry_run(cfg: Config, today: date) -> int:
    state = State.load(cfg.settings.state_path)
    picks = pick_for_today(today, cfg, state, _make_youtube_fetcher(cfg))
    if not picks:
        print(f"[{today.isoformat()}] no picks")
        return 0
    for pick in picks:
        print(f"[{today.isoformat()}] {pick.show.id}  {pick.show.name}")
        for entry in pick.entries:
            print(f"    {entry.url}")
            if entry.title and entry.title != pick.show.name:
                print(f"      title: {entry.title}")
    return 0


def _cmd_run(cfg: Config, today: date) -> int:
    state = State.load(cfg.settings.state_path)
    try:
        picks = pick_for_today(today, cfg, state, _make_youtube_fetcher(cfg))
    except Exception as e:
        log.error("failed to gather picks: %s", e)
        return 1

    if not picks:
        log.info("nothing to notify for %s", today.isoformat())
        return 0

    log.info("notifying %d show(s)", len(picks))
    try:
        discord.post(cfg.webhook_url, picks)
    except Exception as e:
        log.error("discord post failed: %s", e)
        return 1

    now = datetime.now(UTC)
    for pick in picks:
        # for static, mark with last entry's id (acts as "bundle done today" key)
        last = pick.entries[-1]
        state.mark_notified(pick.show.id, last.video_id, now)
    state.save()
    log.info("done")
    return 0


def _make_youtube_fetcher(cfg: Config):
    def fetch(show: Show):
        if not show.channel_id:
            return []
        try:
            return yt.fetch(
                show.channel_id,
                template=cfg.settings.youtube_feed_template,
                title_filter=show.title_filter,
            )
        except Exception as e:
            log.error("youtube fetch failed for %s: %s", show.id, e)
            return []
    return fetch


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _today() -> date:
    # use JST so the weekday matches the user's lived day
    from datetime import timedelta
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).date()


if __name__ == "__main__":
    raise SystemExit(main())
