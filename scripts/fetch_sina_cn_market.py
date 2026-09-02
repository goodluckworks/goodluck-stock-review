#!/usr/bin/env python3
"""Fetch auditable China A-share post-close data from public Sina endpoints.

This adapter intentionally excludes Beijing Stock Exchange securities. Current
day mover ranking is accepted only when the requested date equals the latest
date returned by the cash-index K-line data. Historical backfills can still use
index/leader K-lines and saved snapshots, but must supply researched mover
candidates when a same-day ranking snapshot is unavailable.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from cn_watchlist import load_watchlist, public_metadata


CST = ZoneInfo("Asia/Shanghai")
KLINE_URL = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
RANK_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
SW_URL = "https://vip.stock.finance.sina.com.cn/q/view/SwHy.php"
CONCEPT_URL = "https://vip.stock.finance.sina.com.cn/q/view/newFLJK.php?param=class"

INDEXES = {
    "SSE": ("sh000001", "上证综指"),
    "CHINEXT": ("sz399006", "创业板指"),
    "STAR50": ("sh000688", "科创50"),
}

TECH_CONCEPT_TERMS = (
    "AI", "人工智能", "半导体", "芯片", "算力", "机器人", "服务器", "存储",
    "光模块", "光通信", "云计算", "软件", "数据", "鸿蒙", "通信", "消费电子",
    "PCB", "先进封装", "机器视觉", "物联网", "量子", "低空经济",
)
ST_RE = re.compile(r"(?:\*?ST|退市|退\b)", re.I)


def get_bytes(url: str, timeout: float, referer: str | None = None) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0"}
    if referer:
        headers["Referer"] = referer
    with urlopen(Request(url, headers=headers), timeout=timeout) as response:
        return response.read()


def get_json(url: str, timeout: float, referer: str | None = None) -> Any:
    raw = get_bytes(url, timeout, referer)
    for encoding in ("utf-8", "gb18030", "gbk"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"Unable to decode JSON response: {url}")


def kline(symbol: str, scale: int, datalen: int, timeout: float) -> list[dict[str, Any]]:
    query = urlencode({"symbol": symbol, "scale": scale, "ma": "no", "datalen": datalen})
    data = get_json(f"{KLINE_URL}?{query}", timeout)
    return data if isinstance(data, list) else []


def daily_context(symbol: str, target_date: str, timeout: float) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, Any] | None]:
    rows = [row for row in kline(symbol, 240, 240, timeout) if str(row.get("day", ""))[:10] <= target_date]
    target_index = next((index for index, row in enumerate(rows) if str(row.get("day", ""))[:10] == target_date), None)
    if target_index is None:
        return rows, None, None
    current = rows[target_index]
    previous = rows[target_index - 1] if target_index > 0 else None
    return rows, current, previous


def normalize_bars(rows: list[dict[str, Any]], target_date: str) -> list[dict[str, Any]]:
    bars: list[dict[str, Any]] = []
    for row in rows:
        day = str(row.get("day") or "")
        if not day.startswith(target_date) or len(day) < 19:
            continue
        stamp = datetime.fromisoformat(day).replace(tzinfo=CST)
        clock = stamp.time()
        if not ((clock.hour == 9 and clock.minute >= 30) or 10 <= clock.hour < 11 or (clock.hour == 11 and clock.minute <= 30) or 13 <= clock.hour < 15 or (clock.hour == 15 and clock.minute == 0)):
            continue
        bars.append({
            "time_local": stamp.isoformat(),
            "open": float(row["open"]), "high": float(row["high"]),
            "low": float(row["low"]), "close": float(row["close"]),
            "volume": float(row["volume"]) if row.get("volume") not in (None, "") else None,
            "amount": float(row["amount"]) if row.get("amount") not in (None, "") else None,
        })
    return sorted(bars, key=lambda row: row["time_local"])


def summarize(symbol: str, target_date: str, timeout: float) -> tuple[dict[str, Any] | None, list[dict[str, Any]], int]:
    daily_rows, daily, previous = daily_context(symbol, target_date, timeout)
    bars = normalize_bars(kline(symbol, 5, 1023, timeout), target_date)
    if bars:
        open_ = float(bars[0]["open"])
        close = float(bars[-1]["close"])
        volume = sum(float(row["volume"]) for row in bars if isinstance(row.get("volume"), (int, float)))
        amount = sum(float(row["amount"]) for row in bars if isinstance(row.get("amount"), (int, float)))
        first_time, last_time = bars[0]["time_local"], bars[-1]["time_local"]
    elif daily:
        open_, close = float(daily["open"]), float(daily["close"])
        volume = float(daily["volume"]) if daily.get("volume") not in (None, "") else None
        amount = float(daily["amount"]) if daily.get("amount") not in (None, "") else None
        first_time = last_time = None
    else:
        return None, [], len(daily_rows)
    high = max(float(row["high"]) for row in bars) if bars else float(daily["high"])
    low = min(float(row["low"]) for row in bars) if bars else float(daily["low"])
    previous_close = float(previous["close"]) if previous else None
    summary = {
        "bars": len(bars), "open": open_, "high": high, "low": low, "close": close,
        "change": close - open_, "change_pct": (close / open_ - 1) * 100 if open_ else None,
        "previous_close": previous_close,
        "day_change": close - previous_close if previous_close is not None else None,
        "day_change_pct": (close / previous_close - 1) * 100 if previous_close else None,
        "volume": volume, "amount": amount,
        "first_time_local": first_time, "last_time_local": last_time,
        "data_granularity": "5m" if bars else "daily_only",
    }
    return summary, bars, len(daily_rows)


def parse_js_object(url: str, timeout: float) -> dict[str, str]:
    raw = get_bytes(url, timeout, "https://vip.stock.finance.sina.com.cn/")
    text = raw.decode("gb18030", errors="replace")
    body = text.split("=", 1)[1].strip().rstrip(";")
    value = json.loads(body)
    return value if isinstance(value, dict) else {}


def parse_sector_rows(raw: dict[str, str], prefix: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in raw.items():
        if prefix and not key.startswith(prefix):
            continue
        fields = str(value).split(",")
        if len(fields) < 13:
            continue
        try:
            rows.append({
                "key": fields[0], "ticker": fields[0], "name": fields[1],
                "constituent_count": int(float(fields[2])), "day_pct": float(fields[5]),
                "volume": float(fields[6]), "amount": float(fields[7]),
                "leader_symbol": fields[8], "leader_pct": float(fields[9]),
                "leader_name": fields[12],
                "source": SW_URL if key.startswith("sw") else CONCEPT_URL,
            })
        except ValueError:
            continue
    return rows


def rank_rows(node: str, ascending: bool, timeout: float) -> list[dict[str, Any]]:
    query = urlencode({
        "page": 1, "num": 100, "sort": "changepercent", "asc": 1 if ascending else 0,
        "node": node, "symbol": "", "_s_r_a": "page",
    })
    data = get_json(f"{RANK_URL}?{query}", timeout, "https://vip.stock.finance.sina.com.cn/")
    return data if isinstance(data, list) else []


def eligible_market_symbol(symbol: str) -> bool:
    return bool(re.fullmatch(r"sh(?:60|68)\d{4}|sz(?:00|30)\d{4}", symbol))


def choose_movers(target_date: str, timeout: float, min_amount: float, min_listing_days: int, per_side: int) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ascending, direction in ((False, "up"), (True, "down")):
        candidates = rank_rows("sh_a", ascending, timeout) + rank_rows("sz_a", ascending, timeout)
        candidates.sort(key=lambda row: float(row.get("changepercent") or 0), reverse=not ascending)
        side: list[dict[str, Any]] = []
        for row in candidates:
            symbol, name = str(row.get("symbol") or ""), str(row.get("name") or "")
            if symbol in seen or not eligible_market_symbol(symbol) or ST_RE.search(name):
                continue
            if float(row.get("amount") or 0) < min_amount:
                continue
            summary, bars, listing_days = summarize(symbol, target_date, timeout)
            if not summary or listing_days < min_listing_days or summary.get("day_change_pct") is None:
                continue
            side.append({
                "key": symbol, "ticker": symbol[2:], "symbol": symbol, "name": name,
                "direction": direction, "listing_days_observed": listing_days,
                "rank_snapshot_pct": float(row.get("changepercent") or 0),
                "summary": summary, "bars": bars,
                "market_cap": float(row.get("mktcap") or 0),
                "turnover_ratio": float(row.get("turnoverratio") or 0),
                "source": RANK_URL,
            })
            seen.add(symbol)
            if len(side) >= per_side:
                break
            time.sleep(0.03)
        if len(side) < per_side:
            warnings.append(f"{direction} movers only {len(side)}/{per_side} after filters")
        selected.extend(side)
    return selected, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="China market date, YYYY-MM-DD")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--min-listing-days", type=int, default=20)
    parser.add_argument("--min-amount", type=float, default=500_000_000)
    parser.add_argument("--movers-per-side", type=int, default=5)
    parser.add_argument("--watchlist-config", help="Optional one-run watchlist JSON; otherwise use the user-local default")
    args = parser.parse_args()
    if args.min_listing_days < 1 or args.movers_per_side < 1:
        parser.error("listing days and movers per side must be positive")
    try:
        watchlist = load_watchlist(args.watchlist_config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    leaders = {
        str(row["symbol"]): (str(row["name"]), str(row["sector"]))
        for row in watchlist["stocks"]
    }
    watched_sectors = set(str(value) for value in watchlist["sectors"])

    result: dict[str, Any] = {
        "market": "cn", "report_date": args.date,
        "source": "Sina Finance public market endpoints",
        "source_status": "public aggregated data; internal endpoints without a published SLA",
        "generated_at": datetime.now(CST).isoformat(),
        "session_window_cst": "09:30-11:30,13:00-15:00",
        "symbols": {}, "sectors": {}, "movers": [], "warnings": [],
        "watchlist": public_metadata(watchlist),
        "mover_filter": {
            "markets": ["沪深主板", "创业板", "科创板"], "exclude_bse": True,
            "exclude_name_patterns": ["ST", "*ST", "退市整理"],
            "min_listing_days": args.min_listing_days, "min_amount_cny": args.min_amount,
        },
    }

    latest_dates: list[str] = []
    for key, (symbol, name) in INDEXES.items():
        summary, bars, _ = summarize(symbol, args.date, args.timeout)
        result["symbols"][key] = {
            "sina_symbol": symbol, "name": name, "summary": summary, "bars": bars,
            "source_url": f"{KLINE_URL}?symbol={symbol}&scale=5&ma=no&datalen=1023",
        }
        recent = kline(symbol, 240, 5, args.timeout)
        if recent:
            latest_dates.append(str(recent[-1].get("day", ""))[:10])

    for symbol, (name, sector) in leaders.items():
        summary, bars, _ = summarize(symbol, args.date, args.timeout)
        result["symbols"][symbol] = {
            "sina_symbol": symbol, "name": name, "sector": sector,
            "summary": summary, "bars": bars,
            "source_url": f"{KLINE_URL}?symbol={symbol}&scale=5&ma=no&datalen=1023",
        }

    latest_market_date = max(latest_dates) if latest_dates else None
    result["latest_market_date_seen"] = latest_market_date
    if latest_market_date == args.date:
        sw_rows = parse_sector_rows(parse_js_object(SW_URL, args.timeout), "sw1_")
        sw_sorted = sorted(sw_rows, key=lambda row: row["day_pct"])
        fixed_tech = [row for row in sw_rows if row["name"] in watched_sectors]
        missing_sectors = sorted(watched_sectors - {str(row["name"]) for row in fixed_tech})
        if missing_sectors:
            result["warnings"].append("configured sectors missing from Sina Shenwan snapshot: " + "、".join(missing_sectors))
        concepts = parse_sector_rows(parse_js_object(CONCEPT_URL, args.timeout))
        tech_concepts = [row for row in concepts if any(term.lower() in row["name"].lower() for term in TECH_CONCEPT_TERMS)]
        significant = sorted(tech_concepts, key=lambda row: abs(row["day_pct"]), reverse=True)
        significant = [row for row in significant if abs(row["day_pct"]) >= 2][:5] or significant[:3]
        result["sectors"] = {
            "fixed_tech": fixed_tech,
            "top5": list(reversed(sw_sorted[-5:])),
            "bottom5": sw_sorted[:5],
            "significant_tech_concepts": significant,
            "classification": "新浪接口标示的申万一级行业；涨跌幅按接口口径展示",
        }
        movers, warnings = choose_movers(args.date, args.timeout, args.min_amount, args.min_listing_days, args.movers_per_side)
        result["movers"] = movers
        result["warnings"].extend(warnings)
    else:
        result["warnings"].append(
            "Requested date is not the latest Sina ranking/sector snapshot; use a saved same-day snapshot or sourced historical mover candidates."
        )

    for key, obj in result["symbols"].items():
        if not obj.get("summary"):
            result["warnings"].append(f"missing price summary: {key}")
        elif not obj.get("bars"):
            result["warnings"].append(f"5-minute history unavailable for {key}; daily-only summary retained")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output), "date": args.date, "latest_market_date": latest_market_date,
        "symbol_count": len(result["symbols"]), "mover_count": len(result["movers"]),
        "watchlist_source": watchlist["source"],
        "warnings": result["warnings"],
    }, ensure_ascii=False, indent=2))
    return 0 if all(result["symbols"][key].get("summary") for key in INDEXES) else 2


if __name__ == "__main__":
    raise SystemExit(main())
