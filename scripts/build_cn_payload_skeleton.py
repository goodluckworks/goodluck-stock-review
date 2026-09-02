#!/usr/bin/env python3
"""Build an A-share report payload skeleton from a verified Sina snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from cn_watchlist import load_watchlist, public_metadata


CST = ZoneInfo("Asia/Shanghai")
INDEX_LABELS = {"SSE": "上证综指", "CHINEXT": "创业板指", "STAR50": "科创50"}


def market_row(key: str, obj: dict[str, Any]) -> dict[str, Any]:
    summary = obj.get("summary") or {}
    return {
        "key": key,
        "ticker": key if key in INDEX_LABELS else key[2:] if key.startswith(("sh", "sz")) else key,
        "name": obj.get("name") or INDEX_LABELS.get(key) or key,
        "sector": obj.get("sector"),
        "open": summary.get("open"), "high": summary.get("high"), "low": summary.get("low"),
        "close": summary.get("close"), "session_change": summary.get("change"),
        "session_pct": summary.get("change_pct"), "previous_close": summary.get("previous_close"),
        "day_change": summary.get("day_change"), "day_pct": summary.get("day_change_pct"),
        "volume": summary.get("volume"), "amount": summary.get("amount"),
        "bar_count": summary.get("bars"), "first_time_local": summary.get("first_time_local"),
        "last_time_local": summary.get("last_time_local"),
        "comment": "TODO: 根据真实日内走势与可核验消息填写。",
        "source": obj.get("source_url") or "https://finance.sina.com.cn/",
    }


def mover_row(obj: dict[str, Any]) -> dict[str, Any]:
    summary = obj.get("summary") or {}
    return {
        "key": obj.get("key"), "ticker": obj.get("ticker"), "name": obj.get("name"),
        "open": summary.get("open"), "high": summary.get("high"), "low": summary.get("low"),
        "close": summary.get("close"), "session_change": summary.get("change"),
        "session_pct": summary.get("change_pct"), "previous_close": summary.get("previous_close"),
        "day_change": summary.get("day_change"), "day_pct": summary.get("day_change_pct"),
        "volume": summary.get("volume"), "amount": summary.get("amount"),
        "bar_count": summary.get("bars"), "first_time_local": summary.get("first_time_local"),
        "last_time_local": summary.get("last_time_local"),
        "listing_days_observed": obj.get("listing_days_observed"),
        "turnover_ratio": obj.get("turnover_ratio"),
        "driver": "TODO: 填写可核验的异动原因；无法确认时明确写暂无可靠来源确认。",
        "category": "TODO", "source": obj.get("source") or "https://finance.sina.com.cn/",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--input", help="Verified Sina snapshot; required for full_cn and optional for closed_cn")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report-type", choices=["full_cn", "closed_cn"], default="full_cn")
    args = parser.parse_args()
    if args.report_type == "full_cn" and not args.input:
        raise SystemExit("--input is required for full_cn")
    raw_path = Path(args.input) if args.input else None
    data = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path else {"market": "cn"}
    if data.get("market") != "cn":
        raise SystemExit("input market must be cn")
    if args.report_type == "full_cn" and data.get("report_date") != args.date:
        raise SystemExit("input date does not match requested China report")

    symbols = data.get("symbols") or {}
    cn_watchlist = data.get("watchlist") or public_metadata(load_watchlist())
    payload: dict[str, Any] = {
        "market": "cn", "report_date": args.date, "report_type": args.report_type,
        "generated_at": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S CST"),
        "overview_lead": "TODO: 先概括申万一级领涨/领跌行业和科技板块表现，再说明三大指数方向。",
        "overview": "TODO: 用3–5句总结指数、成交、风格、科技主线与风险偏好。",
        "data_notes": [
            "A股日内窗口为北京时间09:30–11:30、13:00–15:00；午间休市不连接或插值。",
            "新浪财经为公开聚合行情源，非交易所认证数据；板块涨跌按新浪接口标示口径展示。",
        ],
        "data_gaps": list(data.get("warnings") or []),
        "market_news": [], "global_news": [], "voices": [], "next_watch": [],
        "sources": {
            "新浪财经行情": "https://finance.sina.com.cn/stock/",
            "上海证券交易所": "https://www.sse.com.cn/",
            "深圳证券交易所": "https://www.szse.cn/",
        },
        "mover_filter": data.get("mover_filter") or {},
        "cn_watchlist": cn_watchlist,
    }
    if args.report_type == "full_cn":
        payload.update({
            "series_files": {"cn_market": str(raw_path)},
            "benchmark_kpis": [market_row(key, symbols.get(key) or {}) for key in ("SSE", "CHINEXT", "STAR50")],
            "key_stocks": [market_row(key, obj) for key, obj in symbols.items() if key not in INDEX_LABELS],
            "movers": [mover_row(obj) for obj in data.get("movers") or []],
            "cn_sectors": data.get("sectors") or {},
            "benchmark_analysis": "TODO: 比较上证综指、创业板指和科创50的早盘、午后与收盘相对强弱。",
            "structure_analysis": "TODO: 解释申万一级涨跌前五、固定科技行业及显著科技概念的分化；事实和推断分开。",
        })
    else:
        payload["overview_lead"] = ""
        payload["overview"] = "今日A股休市，无需生成完整A股复盘；本页仅保留可核验的新闻、人物发言与下一交易日关注。"
        payload["data_gaps"].extend([
            "市场新闻：未提供可核验条目时保持为空，不生成填充内容。",
            "国际新闻：未提供可核验条目时保持为空，不生成填充内容。",
            "人物：未提供可核验原话或可靠转述时保持为空。",
            "日程：未提供可靠公开日程时明确标注暂无来源确认。",
        ])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
