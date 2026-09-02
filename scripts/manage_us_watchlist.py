#!/usr/bin/env python3
"""Show, save, or reset the user's persistent U.S. watchlist."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from us_watchlist import load_watchlist, reset_watchlist, save_watchlist, user_config_path


def item_value(value: str) -> dict[str, str]:
    parts = [part.strip() for part in re.split(r"[|,，]", value) if part.strip()]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("item must be TICKER|NAME|EXCHANGE:SYMBOL")
    return {"ticker": parts[0], "name": parts[1], "tradingview_symbol": parts[2]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage persistent U.S. stock and sector defaults")
    parser.add_argument("--config", help="Optional config path; default is the per-user update-safe path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show")
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("--stock", action="append", type=item_value, required=True, help="TICKER|NAME|EXCHANGE:SYMBOL; repeat 1-20 times")
    set_parser.add_argument("--sector", action="append", type=item_value, required=True, help="TICKER|NAME|EXCHANGE:SYMBOL; repeat 1-20 times")
    subparsers.add_parser("reset")
    args = parser.parse_args()
    config_path = Path(args.config).expanduser() if args.config else None

    if args.command == "set":
        path, config = save_watchlist({"stocks": args.stock, "sectors": args.sector}, config_path)
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
