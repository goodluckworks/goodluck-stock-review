#!/usr/bin/env python3
"""Resolve the preliminary China A-share report date and close-state branch.

The weekday/time result is only a candidate. Final automation runs must still
verify the date against official SSE and SZSE holiday/closure notices.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo


CST = ZoneInfo("Asia/Shanghai")


def parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now().astimezone()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--now must include a UTC offset or Z")
    return parsed


def resolve(now: datetime, close_buffer_minutes: int) -> dict[str, object]:
    cst = now.astimezone(CST)
    complete_at = 15 * 60 + close_buffer_minutes
    minutes = cst.hour * 60 + cst.minute
    if cst.weekday() >= 5:
        preliminary = "weekend_closed"
        branch = "closed_cn"
    elif minutes >= complete_at:
        preliminary = "weekday_complete_candidate"
        branch = "full_cn_candidate"
    else:
        preliminary = "weekday_session_incomplete_or_preopen"
        branch = "closed_cn"
    return {
        "market": "cn",
        "execution_time_local": now.isoformat(),
        "execution_time_cst": cst.isoformat(),
        "candidate_report_date": cst.date().isoformat(),
        "candidate_weekday": cst.strftime("%A"),
        "preliminary_status": preliminary,
        "preliminary_branch": branch,
        "requires_official_sse_check": True,
        "requires_official_szse_check": True,
        "session_window_cst": "09:30-11:30,13:00-15:00",
        "note": "Confirm the branch with official SSE/SZSE calendars before research.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", help="ISO-8601 instant with timezone; defaults to current time")
    parser.add_argument("--close-buffer-minutes", type=int, default=35)
    args = parser.parse_args()
    if not 0 <= args.close_buffer_minutes <= 120:
        parser.error("--close-buffer-minutes must be between 0 and 120")
    print(json.dumps(resolve(parse_now(args.now), args.close_buffer_minutes), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
