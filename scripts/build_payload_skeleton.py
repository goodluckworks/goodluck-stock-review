#!/usr/bin/env python3
"""Build a content payload skeleton from verified TradingView JSON files."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


CORE = {
    "SPX": ("SPX", "S&P 500 cash index"),
    "NDX": ("NDX", "Nasdaq-100 cash index"),
    "ES": ("ES", "E-mini S&P 500 futures"),
    "NQ": ("NQ", "E-mini Nasdaq 100 futures"),
    "INTC": ("INTC", "Intel"),
    "NVDA": ("NVDA", "NVIDIA"),
    "GOOG": ("GOOG", "Alphabet Class C"),
    "MSFT": ("MSFT", "Microsoft"),
    "AAPL": ("AAPL", "Apple"),
    "SKHY": ("SKHY", "SK hynix ADR"),
    "TSM": ("TSM", "Taiwan Semiconductor ADR"),
    "SPCX": ("SPCX", "SpaceX"),
}

NAMES = {
    "AMEX:SPY": ("SPY", "S&P 500 ETF"), "NASDAQ:QQQ": ("QQQ", "Nasdaq 100 ETF"),
    "AMEX:DIA": ("DIA", "Dow ETF"), "AMEX:IWM": ("IWM", "Russell 2000 ETF"),
    "AMEX:XLK": ("XLK", "科技"), "NASDAQ:SOXX": ("SOXX", "半导体"),
    "NASDAQ:SMH": ("SMH", "半导体"), "AMEX:XLF": ("XLF", "金融"),
    "AMEX:XLE": ("XLE", "能源"), "AMEX:XLV": ("XLV", "医疗"),
    "AMEX:XLY": ("XLY", "可选消费"), "AMEX:XLP": ("XLP", "必需消费"),
    "AMEX:XLI": ("XLI", "工业"), "AMEX:XLU": ("XLU", "公用事业"),
    "AMEX:XLC": ("XLC", "通信服务"), "AMEX:XLB": ("XLB", "材料"),
    "AMEX:XLRE": ("XLRE", "房地产"), "CBOE:VIX": ("VIX", "Cboe波动率指数"),
    "TVC:US10Y": ("US10Y", "美国10年期收益率"), "TVC:DXY": ("DXY", "美元指数"),
    "NYMEX:CL1!": ("WTI", "WTI原油连续合约"), "COMEX:GC1!": ("Gold", "黄金连续合约"),
}


def load(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def symbol_rows(dataset: dict[str, Any], only: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, obj in (dataset.get("symbols") or {}).items():
        if only is not None and key not in only:
            continue
        summary = (obj or {}).get("summary") or {}
        tv_symbol = (obj or {}).get("tradingview_symbol", key)
        ticker, name = CORE.get(key) or NAMES.get(key) or NAMES.get(tv_symbol) or (key.split(":")[-1], key)
        rows.append({
            "key": key, "ticker": ticker, "name": name,
            "open": summary.get("open"), "high": summary.get("high"), "low": summary.get("low"),
            "close": summary.get("close"), "rth_change": summary.get("change"),
            "rth_pct": summary.get("change_pct"), "previous_close": summary.get("previous_close"),
            "day_change": summary.get("day_change"), "day_pct": summary.get("day_change_pct"),
            "volume": summary.get("volume"), "bar_count": summary.get("bars"),
            "first_time_et": summary.get("first_time_et"), "last_time_et": summary.get("last_time_et"),
            "comment": "TODO: 根据真实日内走势与可核验消息填写。",
            "source": "https://www.tradingview.com/",
        })
    return rows


def merge_movers(paths: list[str]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for path in paths:
        for row in symbol_rows(load(path)):
            if row.get("close") is not None:
                row.update({"driver": "TODO: 可核验驱动因素。", "category": "TODO", "source": "TODO"})
                merged[row["ticker"]] = row
    return sorted(merged.values(), key=lambda item: abs(float(item.get("day_pct") or 0)), reverse=True)[:15]


def benchmark_rows(benchmark: dict[str, Any], sector: dict[str, Any]) -> list[dict[str, Any]]:
    exact = {row["ticker"]: row for row in symbol_rows(benchmark, {"SPX", "NDX"}) if row.get("day_pct") is not None}
    proxies = {
        row["ticker"]: row
        for dataset in (sector, benchmark)
        for row in symbol_rows(dataset, {"SPY", "QQQ"})
        if row.get("day_pct") is not None
    }
    specs = [
        ("SPX", "SPY", "标普500"),
        ("NDX", "QQQ", "纳斯达克100"),
    ]
    rows: list[dict[str, Any]] = []
    for exact_ticker, proxy_ticker, label in specs:
        source = exact.get(exact_ticker)
        is_proxy = False
        if source is None:
            source = proxies.get(proxy_ticker)
            is_proxy = True
        if source is None:
            continue
        row = dict(source)
        row.update({
            "kpi_label": label,
            "kpi_basis": f"{proxy_ticker} ETF代理 · 前收至收盘" if is_proxy else "现金指数 · 前收至收盘",
            "is_proxy": is_proxy,
        })
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report-type", choices=["full_rth", "closed_market"], default="full_rth")
    parser.add_argument("--core")
    parser.add_argument("--benchmark")
    parser.add_argument("--sector")
    parser.add_argument("--macro")
    parser.add_argument("--movers", action="append", default=[])
    args = parser.parse_args()

    generated_at = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S CST")
    payload: dict[str, Any] = {
        "report_date": args.date,
        "report_type": args.report_type,
        "generated_at": generated_at,
        "overview_lead": "TODO: 先用一句话概括已核验的领涨/领跌行业，再说明整体盘面方向。",
        "overview": "TODO: 用3–5句总结指数、风格、主线、核心变量与风险偏好。",
        "data_notes": ["TODO: 说明交易日、RTH口径、数据源、频率、延迟和缺失。"],
        "data_gaps": [],
        "market_news": [], "global_news": [], "voices": [], "next_watch": [],
        "sources": {
            "TradingView": "https://www.tradingview.com/",
            "NYSE trading calendar": "https://www.nyse.com/trade/hours-calendars",
            "Nasdaq Trader calendar": "https://www.nasdaqtrader.com/Trader.aspx?id=Calendar",
        },
    }
    if args.report_type == "full_rth":
        if not args.core:
            parser.error("--core is required for full_rth")
        core = load(args.core)
        sector = load(args.sector)
        payload.update({
            "series_files": {"core": args.core, "benchmark": args.benchmark, "sector": args.sector, "macro": args.macro, "movers": args.movers},
            "benchmark_kpis": benchmark_rows(load(args.benchmark), sector),
            "futures": symbol_rows(core, {"ES", "NQ"}),
            "key_stocks": symbol_rows(core, {"INTC", "NVDA", "GOOG", "MSFT", "AAPL", "SKHY", "TSM", "SPCX"}),
            "sectors": symbol_rows(sector),
            "macro": symbol_rows(load(args.macro)),
            "movers": merge_movers(args.movers),
        })
    else:
        payload["overview_lead"] = ""
        payload["overview"] = "今日美股休市，无需生成完整美股复盘。TODO: 补充可核验的市场新闻与国际新闻概览。"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
