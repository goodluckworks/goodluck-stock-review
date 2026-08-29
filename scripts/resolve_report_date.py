#!/usr/bin/env python3
"""Resolve the preliminary U.S. report date and close-state branch.

This script deliberately does not hardcode exchange holidays or early closes.
Its output always requires official NYSE and Nasdaq calendar verification.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")


def parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now().astimezone()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--now must include a UTC offset or Z")
    return parsed


def resolve(now: datetime, close_buffer_minutes: int) -> dict[str, object]:
    et = now.astimezone(ET)
    weekday = et.weekday()
    minutes = et.hour * 60 + et.minute
    complete_at = 16 * 60 + close_buffer_minutes
    if weekday >= 5:
        preliminary = "weekend_closed"
        branch = "closed_market"
    elif minutes >= complete_at:
        preliminary = "weekday_complete_candidate"
        branch = "full_rth_candidate"
    else:
        preliminary = "weekday_rth_incomplete_or_preopen"
        branch = "closed_market"
    return {
        "execution_time_local": now.isoformat(),
        "execution_time_et": et.isoformat(),
        "candidate_report_date": et.date().isoformat(),
        "candidate_weekday": et.strftime("%A"),
        "preliminary_status": preliminary,
        "preliminary_branch": branch,
        "requires_official_nyse_check": True,
        "requires_official_nasdaq_check": True,
        "early_close_not_resolved": True,
        "rth_window_et": "09:30-16:00",
        "note": "Confirm the branch with official exchange calendars before market-data research.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", help="ISO-8601 instant with timezone; defaults to current time")
    parser.add_argument("--close-buffer-minutes", type=int, default=10)
    args = parser.parse_args()
    if args.close_buffer_minutes < 0 or args.close_buffer_minutes > 120:
        parser.error("--close-buffer-minutes must be between 0 and 120")
    print(json.dumps(resolve(parse_now(args.now), args.close_buffer_minutes), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
