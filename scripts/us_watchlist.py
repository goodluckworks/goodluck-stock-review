#!/usr/bin/env python3
"""Resolve built-in and user-local U.S. stock/sector watchlists."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


CONFIG_ENV = "GOODLUCK_STOCK_REVIEW_US_WATCHLIST"
CONFIG_DIRNAME = ".goodluck-stock-review"
CONFIG_FILENAME = "us-watchlist.json"
SCHEMA_VERSION = 1
MAX_SECTORS = 20
MAX_STOCKS = 20
RESERVED_BENCHMARKS = {"SPX", "NDX", "SPY", "QQQ"}
TICKER_RE = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,14}")
TV_SYMBOL_RE = re.compile(r"[A-Z0-9_]+:[A-Z0-9.!\-]+")

DEFAULT_STOCKS = (
    {"ticker": "INTC", "name": "Intel", "tradingview_symbol": "NASDAQ:INTC"},
    {"ticker": "NVDA", "name": "NVIDIA", "tradingview_symbol": "NASDAQ:NVDA"},
    {"ticker": "GOOG", "name": "Alphabet Class C", "tradingview_symbol": "NASDAQ:GOOG"},
    {"ticker": "MSFT", "name": "Microsoft", "tradingview_symbol": "NASDAQ:MSFT"},
    {"ticker": "AAPL", "name": "Apple", "tradingview_symbol": "NASDAQ:AAPL"},
    {"ticker": "SKHY", "name": "SK hynix ADR", "tradingview_symbol": "NASDAQ:SKHY"},
    {"ticker": "TSM", "name": "Taiwan Semiconductor ADR", "tradingview_symbol": "NYSE:TSM"},
    {"ticker": "SPCX", "name": "SpaceX", "tradingview_symbol": "NASDAQ:SPCX"},
)

DEFAULT_SECTORS = (
    {"ticker": "DIA", "name": "Dow ETF", "tradingview_symbol": "AMEX:DIA"},
    {"ticker": "IWM", "name": "Russell 2000 ETF", "tradingview_symbol": "AMEX:IWM"},
    {"ticker": "XLK", "name": "科技", "tradingview_symbol": "AMEX:XLK"},
    {"ticker": "SOXX", "name": "半导体", "tradingview_symbol": "NASDAQ:SOXX"},
    {"ticker": "SMH", "name": "半导体", "tradingview_symbol": "NASDAQ:SMH"},
    {"ticker": "XLF", "name": "金融", "tradingview_symbol": "AMEX:XLF"},
    {"ticker": "XLE", "name": "能源", "tradingview_symbol": "AMEX:XLE"},
    {"ticker": "XLV", "name": "医疗", "tradingview_symbol": "AMEX:XLV"},
    {"ticker": "XLY", "name": "可选消费", "tradingview_symbol": "AMEX:XLY"},
    {"ticker": "XLP", "name": "必需消费", "tradingview_symbol": "AMEX:XLP"},
    {"ticker": "XLI", "name": "工业", "tradingview_symbol": "AMEX:XLI"},
    {"ticker": "XLU", "name": "公用事业", "tradingview_symbol": "AMEX:XLU"},
    {"ticker": "XLC", "name": "通信服务", "tradingview_symbol": "AMEX:XLC"},
    {"ticker": "XLB", "name": "材料", "tradingview_symbol": "AMEX:XLB"},
    {"ticker": "XLRE", "name": "房地产", "tradingview_symbol": "AMEX:XLRE"},
)


def user_config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / CONFIG_DIRNAME / CONFIG_FILENAME


def _normalize_items(values: Any, field: str, maximum: int) -> list[dict[str, str]]:
    if not isinstance(values, list) or not 1 <= len(values) <= maximum:
        raise ValueError(f"{field} must contain 1-{maximum} entries")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, row in enumerate(values, 1):
        if not isinstance(row, dict):
            raise ValueError(f"{field} item {index} must be an object")
        ticker = str(row.get("ticker") or "").strip().upper()
        name = str(row.get("name") or "").strip()
        tv_symbol = str(row.get("tradingview_symbol") or row.get("symbol") or "").strip().upper()
        if not TICKER_RE.fullmatch(ticker) or not name or not TV_SYMBOL_RE.fullmatch(tv_symbol):
            raise ValueError(f"invalid {field} item {index}: ticker, name, and EXCHANGE:SYMBOL are required")
        if ticker in seen:
            raise ValueError(f"duplicate {field} ticker: {ticker}")
        if field == "stocks" and ticker in RESERVED_BENCHMARKS:
            raise ValueError(f"fixed benchmark cannot be a custom stock: {ticker}")
        seen.add(ticker)
        result.append({"ticker": ticker, "name": name, "tradingview_symbol": tv_symbol})
    return result


def validate_watchlist(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("watchlist must be a JSON object")
    stocks = _normalize_items(data.get("stocks"), "stocks", MAX_STOCKS)
    sectors = _normalize_items(data.get("sectors"), "sectors", MAX_SECTORS)
    overlap = {row["ticker"] for row in stocks} & {row["ticker"] for row in sectors}
    if overlap:
        raise ValueError("tickers cannot appear in both stocks and sectors: " + ", ".join(sorted(overlap)))
    return {"schema_version": SCHEMA_VERSION, "stocks": stocks, "sectors": sectors}


def builtin_watchlist() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "builtin_default",
        "stocks": [dict(row) for row in DEFAULT_STOCKS],
        "sectors": [dict(row) for row in DEFAULT_SECTORS],
    }


def load_watchlist(config_path: str | Path | None = None) -> dict[str, Any]:
    explicit = config_path is not None
    path = Path(config_path).expanduser() if explicit else user_config_path()
    if not path.exists():
        if explicit or os.environ.get(CONFIG_ENV):
            raise ValueError(f"watchlist config does not exist: {path}")
        return builtin_watchlist()
    data = json.loads(path.read_text(encoding="utf-8"))
    result = validate_watchlist(data)
    result["source"] = "explicit_file" if explicit or os.environ.get(CONFIG_ENV) else "local_override"
    return result


def save_watchlist(data: dict[str, Any], config_path: str | Path | None = None) -> tuple[Path, dict[str, Any]]:
    path = Path(config_path).expanduser() if config_path is not None else user_config_path()
    normalized = validate_watchlist(data)
    stored = dict(normalized)
    stored["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    result = dict(normalized)
    result["source"] = "local_override"
    return path, result


def reset_watchlist(config_path: str | Path | None = None) -> tuple[Path, bool]:
    path = Path(config_path).expanduser() if config_path is not None else user_config_path()
    existed = path.exists()
    if existed:
        path.unlink()
    return path, existed


def public_metadata(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": str(config.get("source") or "builtin_default"),
        "stocks": [dict(row) for row in config.get("stocks") or [] if isinstance(row, dict)],
        "sectors": [dict(row) for row in config.get("sectors") or [] if isinstance(row, dict)],
    }

