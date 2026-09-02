#!/usr/bin/env python3
"""Resolve built-in and user-local A-share watchlist settings."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


CONFIG_ENV = "GOODLUCK_STOCK_REVIEW_CN_WATCHLIST"
CONFIG_DIRNAME = ".goodluck-stock-review"
CONFIG_FILENAME = "cn-watchlist.json"
SCHEMA_VERSION = 1
MAX_SECTORS = 8
MAX_STOCKS = 20

DEFAULT_SECTORS = ("电子", "计算机", "通信", "传媒")
DEFAULT_STOCKS = (
    {"symbol": "sz002371", "name": "北方华创", "sector": "电子"},
    {"symbol": "sh688012", "name": "中微公司", "sector": "电子"},
    {"symbol": "sh688347", "name": "华虹宏力", "sector": "电子"},
    {"symbol": "sz002415", "name": "海康威视", "sector": "计算机"},
    {"symbol": "sz000938", "name": "紫光股份", "sector": "计算机"},
    {"symbol": "sz000977", "name": "浪潮信息", "sector": "计算机"},
    {"symbol": "sh601728", "name": "中国电信", "sector": "通信"},
    {"symbol": "sz301165", "name": "锐捷网络", "sector": "通信"},
    {"symbol": "sz002558", "name": "巨人网络", "sector": "传媒"},
    {"symbol": "sz002517", "name": "恺英网络", "sector": "传媒"},
)

SYMBOL_RE = re.compile(r"(?:sh(?:60|68)\d{4}|sz(?:00|30)\d{4})", re.I)
EXCLUDED_NAME_RE = re.compile(r"(?:\*?ST|退市|退\b)", re.I)


def user_config_path() -> Path:
    """Return the update-safe per-user config path."""
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / CONFIG_DIRNAME / CONFIG_FILENAME


def normalize_symbol(value: str) -> str:
    symbol = re.sub(r"[.\s_-]", "", str(value or "")).lower()
    if re.fullmatch(r"\d{6}", symbol):
        if symbol.startswith(("60", "68")):
            symbol = f"sh{symbol}"
        elif symbol.startswith(("00", "30")):
            symbol = f"sz{symbol}"
    if not SYMBOL_RE.fullmatch(symbol):
        raise ValueError(f"unsupported A-share symbol: {value}")
    return symbol


def _unique_text(values: Any, field: str, maximum: int) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field} must be a list")
    cleaned: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"{field} contains an empty value")
        if text not in cleaned:
            cleaned.append(text)
    if not 1 <= len(cleaned) <= maximum:
        raise ValueError(f"{field} must contain 1-{maximum} unique values")
    return cleaned


def validate_watchlist(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a watchlist without doing network I/O."""
    if not isinstance(data, dict):
        raise ValueError("watchlist must be a JSON object")
    sectors = _unique_text(data.get("sectors"), "sectors", MAX_SECTORS)
    raw_stocks = data.get("stocks")
    if not isinstance(raw_stocks, list) or not 1 <= len(raw_stocks) <= MAX_STOCKS:
        raise ValueError(f"stocks must contain 1-{MAX_STOCKS} entries")
    stocks: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, row in enumerate(raw_stocks, 1):
        if not isinstance(row, dict):
            raise ValueError(f"stock {index} must be an object")
        symbol = normalize_symbol(str(row.get("symbol") or row.get("code") or ""))
        name = str(row.get("name") or "").strip()
        sector = str(row.get("sector") or "").strip()
        if not name or not sector:
            raise ValueError(f"stock {index} requires name and sector")
        if EXCLUDED_NAME_RE.search(name):
            raise ValueError(f"excluded ST/delisting stock: {name}")
        if symbol in seen:
            raise ValueError(f"duplicate stock symbol: {symbol}")
        seen.add(symbol)
        stocks.append({"symbol": symbol, "name": name, "sector": sector})
    return {"schema_version": SCHEMA_VERSION, "sectors": sectors, "stocks": stocks}


def builtin_watchlist() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "builtin_default",
        "sectors": list(DEFAULT_SECTORS),
        "stocks": [dict(row) for row in DEFAULT_STOCKS],
    }


def load_watchlist(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load an explicit config, user-local config, or the built-in fallback."""
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
    """Atomically save a validated user-local watchlist."""
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
    """Return auditable metadata without exposing the user's home path."""
    return {
        "schema_version": SCHEMA_VERSION,
        "source": str(config.get("source") or "builtin_default"),
        "sectors": list(config.get("sectors") or []),
        "stocks": [dict(row) for row in config.get("stocks") or [] if isinstance(row, dict)],
    }

