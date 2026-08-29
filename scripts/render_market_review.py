#!/usr/bin/env python3
"""Render the standalone Chinese U.S. market review HTML and audit JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import date
from html import escape
from pathlib import Path
from typing import Any, Iterable


WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
COLORS = ["#2563eb", "#dc2626", "#16a34a", "#7c3aed", "#d97706", "#0891b2", "#db2777", "#4f46e5", "#65a30d"]
PLACEHOLDERS = re.compile(r"\b(?:TODO|TBD|PLACEHOLDER)\b|待补充", re.I)


def h(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def resolve_path(value: str, input_path: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, input_path.parent / path, input_path.parent.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def flatten_paths(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def load_series(payload: dict[str, Any], input_path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    merged: dict[str, dict[str, Any]] = {}
    used: list[str] = []
    for value in (payload.get("series_files") or {}).values():
        for raw_path in flatten_paths(value):
            path = resolve_path(raw_path, input_path)
            if not path.exists():
                continue
            data = load_json(path)
            used.append(str(path))
            for key, obj in (data.get("symbols") or {}).items():
                if not isinstance(obj, dict):
                    continue
                bars = obj.get("bars") or []
                if bars or key not in merged:
                    merged[key] = obj
    return merged, used


def row_series(series: dict[str, dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    key = str(row.get("key") or row.get("ticker") or "")
    candidates = [key, str(row.get("ticker") or "")]
    for candidate in candidates:
        bars = (series.get(candidate) or {}).get("bars")
        if isinstance(bars, list) and bars:
            return bars
    return []


def pct(value: Any) -> str:
    return "未核验" if value is None else f"{float(value):+.2f}%"


def number(value: Any, digits: int = 2) -> str:
    return "未核验" if value is None else f"{float(value):,.{digits}f}"


def volume(value: Any) -> str:
    if value is None:
        return "未提供"
    amount = float(value)
    if amount >= 1e9:
        return f"{amount / 1e9:.2f}B"
    if amount >= 1e6:
        return f"{amount / 1e6:.2f}M"
    if amount >= 1e3:
        return f"{amount / 1e3:.1f}K"
    return f"{amount:.0f}"


def cls(value: Any) -> str:
    if value is None or abs(float(value)) < 0.005:
        return "neutral"
    return "up" if float(value) > 0 else "down"


def move_text(row: dict[str, Any], period: str) -> str:
    if row.get("ticker") == "US10Y":
        value = row.get("rth_change" if period == "rth" else "day_change")
        return "未核验" if value is None else f"{float(value) * 100:+.1f}bp"
    return pct(row.get("rth_pct" if period == "rth" else "day_pct"))


def benchmark_kpi_rows(payload: dict[str, Any], sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    explicit: dict[str, dict[str, Any]] = {}
    for row in payload.get("benchmark_kpis", []) or []:
        if not isinstance(row, dict) or not isinstance(row.get("day_pct"), (int, float)):
            continue
        ticker = str(row.get("ticker") or "").upper()
        if ticker in {"SPX", "SPY"}:
            explicit["sp500"] = row
        elif ticker in {"NDX", "QQQ"}:
            explicit["nasdaq"] = row

    proxies = {
        str(row.get("ticker") or "").upper(): row
        for row in sectors
        if isinstance(row.get("day_pct"), (int, float)) and str(row.get("ticker") or "").upper() in {"SPY", "QQQ"}
    }
    specs = [
        ("sp500", "SPY", "标普500"),
        ("nasdaq", "QQQ", "纳斯达克100"),
    ]
    rows: list[dict[str, Any]] = []
    for slot, proxy_ticker, label in specs:
        source = explicit.get(slot)
        is_proxy = str((source or {}).get("ticker") or "").upper() in {"SPY", "QQQ"}
        if source is None:
            source = proxies.get(proxy_ticker)
            is_proxy = True
        if source is None:
            continue
        row = dict(source)
        row["kpi_label"] = label
        row["kpi_basis"] = f"{proxy_ticker} ETF代理 · 前收至收盘" if is_proxy else "现金指数 · 前收至收盘"
        row["is_proxy"] = is_proxy
        rows.append(row)
    return rows


def link(url: str | None, label: str) -> str:
    if not url:
        return '<span class="source">来源链接未核验</span>'
    return f'<a href="{h(url)}" target="_blank" rel="noopener noreferrer">{h(label)}</a>'


def section_head(number_: str, title: str, subtitle: str) -> str:
    return f'<div class="section-head"><div class="num">{h(number_)}</div><div><h2>{h(title)}</h2><p>{h(subtitle)}</p></div></div>'


def empty_chart(title: str, subtitle: str) -> str:
    return f'<figure class="chart-card" data-chart-slot="true" data-chart-status="missing"><figcaption><strong>{h(title)}</strong><span>{h(subtitle)}</span></figcaption><div class="empty-chart">该图因数据不足未生成</div></figure>'


def line_chart(series_rows: list[tuple[str, list[dict[str, Any]]]], title: str, subtitle: str) -> str:
    series_data: list[tuple[str, list[tuple[str, float]]]] = []
    for label, bars in series_rows:
        closes = [(str(bar.get("time_et", ""))[11:16], bar.get("close")) for bar in bars if isinstance(bar.get("close"), (int, float))]
        if not closes or not closes[0][1]:
            continue
        first = float(closes[0][1])
        series_data.append((label, [(stamp, (float(close) / first - 1) * 100) for stamp, close in closes]))
    if not series_data:
        return empty_chart(title, subtitle)

    width, height = 960, 390
    left, right, top, bottom = 70, 28, 72, 58
    values = [value for _, points in series_data for _, value in points]
    low, high = min(values), max(values)
    if math.isclose(low, high):
        low, high = low - 0.5, high + 0.5
    pad = max((high - low) * 0.12, 0.1)
    low, high = low - pad, high + pad

    def x(index: int, count: int) -> float:
        return left + (width - left - right) * (index / max(count - 1, 1))

    def y(value: float) -> float:
        return top + (height - top - bottom) * (high - value) / (high - low)

    svg: list[str] = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{h(title)}">']
    for tick in range(5):
        value = low + (high - low) * tick / 4
        ypos = y(value)
        svg.append(f'<line x1="{left}" y1="{ypos:.1f}" x2="{width-right}" y2="{ypos:.1f}" stroke="#e6ebf2"/>')
        svg.append(f'<text x="{left-10}" y="{ypos+4:.1f}" text-anchor="end" fill="#667085" font-size="11">{value:+.2f}%</text>')
    zero = y(0)
    if top <= zero <= height - bottom:
        svg.append(f'<line x1="{left}" y1="{zero:.1f}" x2="{width-right}" y2="{zero:.1f}" stroke="#94a3b8" stroke-dasharray="4 4"/>')
    sample_times = series_data[0][1]
    for index in sorted(set(round(i * (len(sample_times) - 1) / 5) for i in range(6))):
        xpos = x(index, len(sample_times))
        svg.append(f'<text x="{xpos:.1f}" y="{height-24}" text-anchor="middle" fill="#667085" font-size="11">{h(sample_times[index][0])}</text>')
    for idx, (label, points) in enumerate(series_data):
        color = COLORS[idx % len(COLORS)]
        path = " ".join(("M" if i == 0 else "L") + f"{x(i, len(points)):.1f},{y(value):.1f}" for i, (_, value) in enumerate(points))
        svg.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.4" vector-effect="non-scaling-stroke"/>')
        legend_x = left + (idx % 5) * 160
        legend_y = 28 + (idx // 5) * 24
        svg.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x+22}" y2="{legend_y}" stroke="{color}" stroke-width="4"/>')
        svg.append(f'<text x="{legend_x+29}" y="{legend_y+4}" fill="#344054" font-size="12">{h(label)}</text>')
    svg.append(f'<text x="18" y="{top-12}" fill="#667085" font-size="11">涨跌幅</text>')
    svg.append(f'<text x="{width-right}" y="{height-7}" text-anchor="end" fill="#667085" font-size="11">美东时间</text></svg>')
    return f'<figure class="chart-card" data-chart-slot="true" data-chart="line" data-series-count="{len(series_data)}"><figcaption><strong>{h(title)}</strong><span>{h(subtitle)}</span></figcaption>{"".join(svg)}</figure>'


def bar_chart(items: list[tuple[str, Any]], title: str, subtitle: str) -> str:
    data = [(label, float(value)) for label, value in items if value is not None]
    if not data:
        return empty_chart(title, subtitle)
    width = 960
    row_height, top, bottom, left, right = 30, 62, 30, 105, 72
    height = top + bottom + row_height * len(data)
    max_abs = max(max(abs(value) for _, value in data), 0.1)
    mid = left + (width - left - right) / 2
    half = (width - left - right) / 2
    svg = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{h(title)}">']
    svg.append(f'<line x1="{mid:.1f}" y1="{top-22}" x2="{mid:.1f}" y2="{height-bottom}" stroke="#94a3b8"/>')
    svg.append(f'<text x="{left}" y="28" fill="#667085" font-size="11">下跌</text><text x="{width-right}" y="28" text-anchor="end" fill="#667085" font-size="11">上涨</text>')
    for index, (label, value) in enumerate(data):
        ypos = top + index * row_height
        length = abs(value) / max_abs * (half - 14)
        xpos = mid if value >= 0 else mid - length
        color = "#15803d" if value >= 0 else "#c2413a"
        svg.append(f'<text x="{left-10}" y="{ypos+16}" text-anchor="end" fill="#344054" font-size="12" font-weight="600">{h(label)}</text>')
        svg.append(f'<rect x="{xpos:.1f}" y="{ypos+3}" width="{length:.1f}" height="18" rx="4" fill="{color}" opacity=".88"/>')
        if value < 0 and length >= 58:
            # Keep large negative labels inside the bar so they cannot collide
            # with the ticker labels reserved to the left of the plot.
            text_x, anchor, text_color = xpos + 7, "start", "#ffffff"
        else:
            text_x = xpos + length + 7 if value >= 0 else xpos - 7
            anchor = "start" if value >= 0 else "end"
            text_color = color
        svg.append(f'<text x="{text_x:.1f}" y="{ypos+17}" text-anchor="{anchor}" fill="{text_color}" font-size="11" font-weight="700">{value:+.2f}%</text>')
    svg.append("</svg>")
    return f'<figure class="chart-card" data-chart-slot="true" data-chart="bar"><figcaption><strong>{h(title)}</strong><span>{h(subtitle)}</span></figcaption>{"".join(svg)}</figure>'


def market_rows(rows: list[dict[str, Any]]) -> str:
    return "".join(
        f'<tr><td><strong>{h(row.get("ticker"))}</strong><small>{h(row.get("name"))}</small></td>'
        f'<td>{number(row.get("open"))}</td><td>{number(row.get("high"))}</td><td>{number(row.get("low"))}</td><td>{number(row.get("close"))}</td>'
        f'<td class="{cls(row.get("rth_pct"))}">{number(row.get("rth_change"))}<small>{pct(row.get("rth_pct"))}</small></td>'
        f'<td class="{cls(row.get("day_pct"))}">{pct(row.get("day_pct"))}</td><td>{volume(row.get("volume"))}</td><td>{h(row.get("bar_count") if row.get("bar_count") is not None else "缺失")}</td></tr>'
        for row in rows
    )


def compact_rows(rows: list[dict[str, Any]]) -> str:
    return "".join(
        f'<tr><td><strong>{h(row.get("ticker"))}</strong><small>{h(row.get("name"))}</small></td>'
        f'<td class="{cls(row.get("rth_pct"))}">{move_text(row, "rth")}</td><td class="{cls(row.get("day_pct"))}">{move_text(row, "day")}</td><td>{number(row.get("close"), 3 if row.get("ticker") == "US10Y" else 2)}</td></tr>'
        for row in rows
    )


def normalize_market_item(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    keys = ["title", "source_time", "fact", "inference", "url"]
    return dict(zip(keys, item)) if isinstance(item, list) else {}


def normalize_global_item(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    keys = ["title", "region", "source_time", "summary", "importance", "impact", "impact_score", "impact_type", "url"]
    return dict(zip(keys, item)) if isinstance(item, list) else {}


def normalize_voice(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    keys = ["person", "time_platform", "platform", "quote", "context", "comments", "url", "comment_url"]
    return dict(zip(keys, item)) if isinstance(item, list) else {}


def source_index(payload: dict[str, Any], groups: Iterable[list[dict[str, Any]]]) -> dict[str, str]:
    sources = {str(label): str(url) for label, url in (payload.get("sources") or {}).items() if url}
    for group in groups:
        for item in group:
            url = item.get("url") or item.get("source")
            if url:
                sources.setdefault(item.get("source_label") or item.get("title") or item.get("ticker") or "来源", str(url))
            if item.get("comment_url"):
                sources.setdefault((item.get("person") or "人物") + " 评论样本", str(item["comment_url"]))
    return sources


def build_html(payload: dict[str, Any], input_path: Path, css: str) -> tuple[str, dict[str, Any]]:
    report_date = date.fromisoformat(str(payload["report_date"]))
    title = f"美股每日盘后回顾 — {report_date.year}年{report_date.month}月{report_date.day}日（{WEEKDAYS[report_date.weekday()]}）"
    report_type = payload.get("report_type")
    series, used_series_files = load_series(payload, input_path)
    futures = [row for row in payload.get("futures", []) if isinstance(row, dict)]
    stocks = [row for row in payload.get("key_stocks", []) if isinstance(row, dict)]
    sectors = [row for row in payload.get("sectors", []) if isinstance(row, dict)]
    macro = [row for row in payload.get("macro", []) if isinstance(row, dict)]
    movers = [row for row in payload.get("movers", []) if isinstance(row, dict)]
    market_news = [normalize_market_item(item) for item in payload.get("market_news", [])]
    global_news = [normalize_global_item(item) for item in payload.get("global_news", [])]
    voices = [normalize_voice(item) for item in payload.get("voices", [])]
    watches = [item for item in payload.get("next_watch", []) if isinstance(item, dict)]
    data_notes = [str(item) for item in payload.get("data_notes", [])]
    data_gaps = [str(item) for item in payload.get("data_gaps", [])]
    generated_at = str(payload.get("generated_at", "未核验"))
    overview_lead = str(payload.get("overview_lead") or "").strip()
    rendered_benchmarks: list[dict[str, Any]] = []

    market_news_html = "".join(
        f'<article class="news-item"><div class="news-index">{index:02d}</div><div><h3>{h(item.get("title"))}</h3>'
        f'<div class="meta">{h(item.get("source_time"))}</div><p>{h(item.get("fact"))}</p><p class="impact">{h(item.get("inference"))}</p>'
        f'<div class="source">{link(item.get("url"), "原文来源")}</div></div></article>'
        for index, item in enumerate(market_news, 1)
    ) or '<div class="notice">未取得足够可核验的市场新闻，未生成填充内容。</div>'

    global_html = "".join(
        f'<article class="global-item"><div class="global-top"><div class="rank">{index}</div><div><h3>{h(item.get("title"))}</h3>'
        f'<div class="meta">{h(item.get("region"))} · {h(item.get("source_time"))} · <span class="tag">{h(item.get("impact_type"))}</span></div></div></div>'
        f'<p>{h(item.get("summary"))}</p><p><strong>为什么重要：</strong>{h(item.get("importance"))}</p>'
        f'<p class="impact"><strong>可能影响：</strong>{h(item.get("impact"))}</p><div class="source">{link(item.get("url"), "原文来源")}</div></article>'
        for index, item in enumerate(global_news, 1)
    ) or '<div class="notice">未取得足够可核验的国际新闻，未生成填充内容。</div>'

    voices_html = "".join(
        f'<article class="voice"><div class="voice-head"><h3>{h(item.get("person"))}</h3><span>{h(item.get("platform"))}</span></div>'
        f'<div class="meta">{h(item.get("time_platform"))}</div><blockquote>{h(item.get("quote"))}</blockquote><p>{h(item.get("context"))}</p>'
        f'<p class="comments"><strong>热门网友评论/样本边界：</strong>{h(item.get("comments"))}</p>'
        f'<div class="source">{link(item.get("url"), "原文来源")}{(" · " + link(item.get("comment_url"), "评论样本")) if item.get("comment_url") else ""}</div></article>'
        for item in voices
    ) or '<div class="notice">未找到足够可核验的人物原话/转述，未生成填充内容。</div>'

    watch_html = "".join(
        f'<article class="watch"><time>{h(item.get("time"))}</time><h3>{h(item.get("title"))}</h3><p>{h(item.get("detail"))}</p>'
        f'<div class="source">{link(item.get("url"), item.get("source_label") or "日程来源")}</div></article>'
        for item in watches
    ) or '<article class="watch"><time>日程边界</time><h3>暂无可靠来源确认</h3><p>未就下一交易日找到可核验的精确日程，不作猜测。</p></article>'

    all_sources = source_index(payload, [market_news, global_news, voices, watches, movers])
    source_list = "".join(f'<li>{link(url, label)}</li>' for label, url in all_sources.items())
    notes_html = "".join(f"<li>{h(note)}</li>" for note in data_notes)
    gaps_html = "" if not data_gaps else '<h3>数据缺口/人工复核</h3><ul class="data-gaps">' + "".join(f"<li>{h(gap)}</li>" for gap in data_gaps) + "</ul>"
    overview_lead_html = f'<p class="overview-lead"><strong>{h(overview_lead)}</strong></p>' if overview_lead else ""

    subtitle = payload.get("subtitle") or ("RTH 时段走势 · 重点期货 · 重点科技股 · 大幅波动股 · 市场新闻 · 国际要闻" if report_type == "full_rth" else "休市/未完成 RTH 分支 · 市场新闻 · 过去24小时国际要闻")
    parts = [
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'<title>{h(title)}</title><style>{css}</style></head><body><main class="page">',
        f'<header class="hero"><div class="eyebrow">U.S. MARKET · POST-CLOSE RESEARCH</div><h1>{h(title)}</h1><p>{h(subtitle)}</p>',
        '<div class="hero-disclaimer"><strong>免责声明：</strong>本报告仅用于个人市场复盘与研究，不构成任何投资建议。市场数据可能存在延迟或口径差异，请以交易所、经纪商及官方公告为准。</div></header>',
        f'<section class="section">{section_head("01", "一句话市场总览", "Answer first")}<div class="answer">{overview_lead_html}<p class="overview-body">{h(payload.get("overview"))}</p></div></section>',
    ]

    if report_type == "full_rth":
        rendered_benchmarks = benchmark_kpi_rows(payload, sectors)
        benchmark_cards = "".join(
            f'<article class="kpi benchmark-kpi {cls(row.get("day_pct"))}"><span>{h(row.get("kpi_label"))}</span>'
            f'<strong>{pct(row.get("day_pct"))}</strong><small>{h(row.get("kpi_basis"))}</small></article>'
            for row in rendered_benchmarks
        )
        kpi_rows = [row for row in stocks if isinstance(row.get("rth_pct"), (int, float))]
        macro_pick = next((row for row in macro if row.get("ticker") in {"VIX", "US10Y"} and (isinstance(row.get("rth_pct"), (int, float)) or isinstance(row.get("rth_change"), (int, float)))), None)
        if macro_pick:
            kpi_rows.append(macro_pick)
        kpis = benchmark_cards + "".join(
            f'<article class="kpi {cls(row.get("rth_pct"))}"><span>{h(row.get("ticker"))}</span><strong>{move_text(row, "rth")}</strong>'
            f'<small>RTH；前收至收盘 {move_text(row, "day")}</small></article>'
            for row in kpi_rows
        )
        benchmark_chart = line_chart(
            [(str(row.get("kpi_label")), row_series(series, row)) for row in rendered_benchmarks],
            "标普500 / 纳斯达克100 RTH 归一化走势",
            "现金指数优先；缺失时使用 SPY/QQQ ETF代理；首根5分钟收盘归一化为0%",
        )
        core_chart_rows = [row for row in stocks if row.get("ticker") in {"INTC", "NVDA", "GOOG", "MSFT", "AAPL"}]
        stock_chart = line_chart([(str(row.get("ticker")), row_series(series, row)) for row in core_chart_rows], "重点科技股 RTH 归一化走势", "INTC、NVDA、GOOG、MSFT、AAPL；真实日内收盘条")
        key_bar = bar_chart([(str(row.get("ticker")), row.get("rth_pct")) for row in stocks], "重点股票 RTH 涨跌幅", "严格 09:30 正式开盘至正常时段最后一根")
        mover_bar = bar_chart([(str(row.get("ticker")), row.get("day_pct")) for row in movers], "当日大幅波动股票涨跌幅", "前一交易日正式收盘至当日正常时段最后一根")
        mover_rows = "".join(
            f'<tr><td><strong>{h(row.get("ticker"))}</strong><small>{h(row.get("name"))}</small></td><td>{number(row.get("close"))}</td>'
            f'<td class="{cls(row.get("day_pct"))}">{pct(row.get("day_pct"))}</td><td class="{cls(row.get("rth_pct"))}">{pct(row.get("rth_pct"))}</td>'
            f'<td><span class="tag">{h(row.get("category"))}</span></td><td>{h(row.get("driver"))}<small>{link(row.get("source"), "驱动来源")}</small></td></tr>'
            for row in movers
        )
        stock_comments = "".join(f'<li><strong>{h(row.get("ticker"))}：</strong>{h(row.get("comment") or "日内走势描述待核验。")}</li>' for row in stocks)
        parts.extend([
            f'<section class="section">{section_head("02", "核心 KPI", "大盘基准显示当日涨跌；个股显示 RTH 与前收口径")}<div class="kpi-grid">{kpis}</div></section>',
            f'<section class="section">{section_head("03", "标普500 / 纳斯达克100 RTH 走势分析", "固定比较标普500与纳斯达克100；现金指数优先，缺失时使用 SPY/QQQ ETF代理，严格截取美东 09:30–16:00")}<div class="table-wrap"><table><thead><tr><th>指数/代理</th><th>RTH开盘</th><th>最高</th><th>最低</th><th>RTH收盘</th><th>RTH涨跌</th><th>前收至收盘</th><th>RTH量</th><th>5m条数</th></tr></thead><tbody>{market_rows(rendered_benchmarks)}</tbody></table></div><div class="chart-grid">{benchmark_chart}</div><p class="analysis-copy">{h(payload.get("benchmark_analysis") or "对比标普500与纳斯达克100的早盘、中盘与尾盘节奏及相对强弱；若采用 ETF 代理，以表格与图注标示的代理口径为准，未核验的因果不作强行归因。")}</p></section>',
            f'<section class="section">{section_head("04", "重点科技股 RTH 表现", "核心股 + SKHY、TSM 及可用时的 SPCX")}<div class="table-wrap"><table><thead><tr><th>股票</th><th>RTH开盘</th><th>最高</th><th>最低</th><th>RTH收盘</th><th>RTH涨跌</th><th>前收至收盘</th><th>RTH量</th><th>5m条数</th></tr></thead><tbody>{market_rows(stocks)}</tbody></table></div><div class="chart-grid">{key_bar}{stock_chart}</div><ul class="analysis-list">{stock_comments}</ul></section>',
            f'<section class="section">{section_head("05", "当日大幅波动股票", f"{len(movers)} 只；按前收至收盘绝对涨跌幅或影响力排序")}<div class="chart-grid">{mover_bar}</div><div class="table-wrap"><table><thead><tr><th>股票</th><th>收盘价</th><th>前收至收盘</th><th>RTH涨跌</th><th>类型</th><th>主要驱动与点评</th></tr></thead><tbody>{mover_rows}</tbody></table></div></section>',
            f'<section class="section">{section_head("06", "板块与市场结构", "行业 ETF 与宏观代理资产，并列 RTH 与前收口径")}<div class="split"><div class="table-wrap"><table><thead><tr><th>ETF/板块</th><th>RTH涨跌</th><th>前收至收盘</th><th>收盘</th></tr></thead><tbody>{compact_rows(sectors)}</tbody></table></div><div class="table-wrap"><table><thead><tr><th>宏观资产</th><th>RTH涨跌</th><th>前收至收盘</th><th>收盘</th></tr></thead><tbody>{compact_rows(macro)}</tbody></table></div></div><p class="analysis-copy">{h(payload.get("structure_analysis") or "根据可得板块 ETF 的实际涨跌分析成长/价值、大盘/小盘与防御/周期风格；若代理数据不完整，以数据缺口说明为准。")}</p></section>',
        ])
        section_number = 7
    else:
        parts.append(f'<section class="section"><div class="closed-banner">今日美股休市，无需生成完整美股复盘</div><p>本页仅保留可核验的市场新闻、国际新闻、人物言论与下一交易日关注。没有生成或替代任何当日 RTH 价格与图表。</p></section>')
        section_number = 2

    global_chart = bar_chart([(str(item.get("impact_type") or item.get("region") or f"事件{idx}"), item.get("impact_score")) for idx, item in enumerate(global_news, 1)], "国际新闻事件影响分类", "定性影响等级1–5；用于比较影响范围，不代表发生概率")
    parts.extend([
        f'<section class="section">{section_head(f"{section_number:02d}", "影响美股的关键新闻", "事件、影响资产、市场反应与逻辑链条分开表述")}{market_news_html}</section>',
        f'<section class="section">{section_head(f"{section_number+1:02d}", "过去 24 小时国际新闻大事", f"{len(global_news)} 条；按重要性排序，持续事件明确标注")}<div class="chart-grid">{global_chart}</div><div class="global-grid">{global_html}</div></section>',
        f'<section class="section">{section_head(f"{section_number+2:02d}", "重要人物发言与言论", f"{len(voices)} 条；原文仅保留可核验短句，网友热评不杜撰")}<div class="voice-grid">{voices_html}</div></section>',
        f'<section class="section">{section_head(f"{section_number+3:02d}", "下一交易日关注", "仅列可靠公开日程或明确待验证事项")}<div class="watchlist">{watch_html}</div></section>',
        f'<footer class="section foot"><h2>数据来源与说明</h2><h3>数据说明、来源与时效</h3><p>RTH 仅指美东 09:30–16:00；前收至收盘与 RTH 开盘至收盘分开展示。TradingView 为公开聚合图表数据，非交易所认证收盘价。</p><ul class="data-notes">{notes_html}</ul>{gaps_html}<h3>主要数据/新闻来源</h3><ol class="source-list">{source_list}</ol><p>生成时间：{h(generated_at)}。审计数据与报告同日保存。</p></footer>',
        '</main></body></html>',
    ])
    html = "".join(parts)
    audit = dict(payload)
    audit.update({
        "title": title, "used_series_files": used_series_files,
        "quality_checks": {
            "exact_title": True, "aapl_spelling": "AAPL" in html and "APPL" not in html,
            "rth_not_24h": "09:30–16:00" in html and "24小时完整期货时段" not in html,
            "inline_css": "<style>" in html, "external_js": "<script" in html,
            "visual_slots": html.count('data-chart-slot="true"'), "embedded_svg_charts": html.count("<svg"),
            "market_news_count": len(market_news), "global_news_count": len(global_news),
            "voices_count": len(voices), "mover_count": len(movers),
        },
        "rendered_benchmark_kpis": rendered_benchmarks,
    })
    return html, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit-output", required=True)
    parser.add_argument("--allow-draft", action="store_true")
    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    payload = load_json(input_path)
    raw_payload = input_path.read_text(encoding="utf-8")
    if not args.allow_draft and PLACEHOLDERS.search(raw_payload):
        raise SystemExit("Refusing final render: unfinished placeholder found in payload")
    if payload.get("report_type") not in {"full_rth", "closed_market"}:
        raise SystemExit("report_type must be full_rth or closed_market")
    css_path = Path(__file__).resolve().parent.parent / "assets" / "report.css"
    html, audit = build_html(payload, input_path, css_path.read_text(encoding="utf-8"))
    output = Path(args.output).resolve()
    audit_output = Path(args.audit_output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    audit["html_path"] = str(output)
    audit["audit_path"] = str(audit_output)
    audit["html_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    audit["html_bytes"] = output.stat().st_size
    audit_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"html": str(output), "audit": str(audit_output), "bytes": output.stat().st_size, "charts": html.count("<svg")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
