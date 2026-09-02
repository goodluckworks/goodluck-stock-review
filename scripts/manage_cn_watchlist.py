#!/usr/bin/env python3
"""Show, save, or reset the user's persistent A-share watchlist."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from cn_watchlist import load_watchlist, reset_watchlist, save_watchlist, user_config_path


def stock_value(value: str) -> dict[str, str]:
    parts = [part.strip() for part in re.split(r"[|,，]", value) if part.strip()]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("stock must be CODE|NAME|SECTOR")
    return {"symbol": parts[0], "name": parts[1], "sector": parts[2]}


def sector_values(values: list[str]) -> list[str]:
    sectors: list[str] = []
    for value in values:
        for item in re.split(r"[,，]", value):
            text = item.strip()
            if text and text not in sectors:
                sectors.append(text)
    return sectors


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage persistent A-share watchlist defaults")
    parser.add_argument("--config", help="Optional config path; default is the per-user update-safe path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show")
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("--sectors", nargs="+", required=True, help="1-8 exact Sina Shenwan level-one names")
    set_parser.add_argument("--stock", action="append", type=stock_value, required=True, help="CODE|NAME|SECTOR; repeat 1-20 times")
    subparsers.add_parser("reset")
    args = parser.parse_args()
    config_path = Path(args.config).expanduser() if args.config else None

    if args.command == "set":
        path, config = save_watchlist({"sectors": sector_values(args.sectors), "stocks": args.stock}, config_path)
        result = {"status": "saved", "path": str(path), "watchlist": config}
    elif args.command == "reset":
        path, existed = reset_watchlist(config_path)
        result = {"status": "reset", "path": str(path), "removed_local_override": existed, "watchlist": load_watchlist() if not config_path else None}
    else:
        path = config_path or user_config_path()
        result = {"status": "ok", "path": str(path), "local_override_exists": path.exists(), "watchlist": load_watchlist(config_path)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
