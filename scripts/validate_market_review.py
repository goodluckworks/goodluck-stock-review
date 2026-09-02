#!/usr/bin/env python3
"""Validate market review data, content contract, and standalone HTML."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import date, datetime, time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from cn_watchlist import builtin_watchlist as builtin_cn_watchlist
from us_watchlist import builtin_watchlist as builtin_us_watchlist


WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
PLACEHOLDERS = re.compile(r"\b(?:TODO|TBD|PLACEHOLDER)\b|待补充", re.I)


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.links.append(str(attributes["href"]))


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def approx(left: Any, right: Any, tolerance: float = 1e-7) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)


def normalize_item(item: Any, keys: list[str]) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    return dict(zip(keys, item)) if isinstance(item, list) else {}


def normalize_voice(item: Any) -> dict[str, Any]:
    legacy_keys = ["person", "time_platform", "platform", "quote", "context", "comments", "url", "comment_url"]
    raw = dict(item) if isinstance(item, dict) else dict(zip(legacy_keys, item)) if isinstance(item, list) else {}
    person = str(raw.get("person") or "").strip()
    raw["person"] = re.split(r"\s*[|｜]\s*", person, maxsplit=1)[0].strip()
    raw.pop("comments", None)
    raw.pop("comment_url", None)
    return raw


def load_series(paths: list[str]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, obj in (data.get("symbols") or {}).items():
            if isinstance(obj, dict) and ((obj.get("bars") or []) or key not in merged):
                merged[key] = obj
        for obj in data.get("movers") or []:
            if not isinstance(obj, dict):
                continue
            key = str(obj.get("key") or obj.get("symbol") or "")
            if key and ((obj.get("bars") or []) or key not in merged):
                merged[key] = obj
    return merged


def validate_series(audit: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    report_date = str(audit.get("report_date"))
    is_cn = str(audit.get("market") or "us").lower() == "cn"
    paths = [str(path) for path in audit.get("used_series_files", [])]
    check(bool(paths), "full_rth_has_series_files", failures)
    check(all(Path(path).exists() for path in paths), "all_series_files_exist", failures)
    series = load_series(paths)
    checked = 0
    for group in ["rendered_benchmark_kpis", "futures", "key_stocks", "sectors", "macro", "movers"]:
        for row in audit.get(group, []) or []:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key") or row.get("ticker") or "")
            obj = series.get(key)
            if not obj:
                if row.get("close") is not None:
                    failures.append(f"series_missing_for_row:{group}:{key}")
                continue
            bars = obj.get("bars") or []
            if not bars:
                if row.get("close") is not None:
                    failures.append(f"bars_missing_for_row:{group}:{key}")
                continue
            time_key = "time_local" if is_cn else "time_et"
            stamps = [datetime.fromisoformat(str(bar[time_key])) for bar in bars]
            check(all(stamp.date().isoformat() == report_date for stamp in stamps), f"series_date:{key}", failures)
            if is_cn:
                check(all(
                    time(9, 30) <= stamp.time().replace(tzinfo=None) <= time(11, 30)
                    or time(13, 0) <= stamp.time().replace(tzinfo=None) <= time(15, 0)
                    for stamp in stamps
                ), f"series_cn_session_window:{key}", failures)
            else:
                check(all(time(9, 30) <= stamp.time().replace(tzinfo=None) <= time(16, 0) for stamp in stamps), f"series_rth_window:{key}", failures)
            check(stamps == sorted(stamps), f"series_sorted:{key}", failures)
            change_field = "session_change" if is_cn else "rth_change"
            pct_field = "session_pct" if is_cn else "rth_pct"
            first_field = "first_time_local" if is_cn else "first_time_et"
            last_field = "last_time_local" if is_cn else "last_time_et"
            expected = {
                "open": bars[0].get("open"), "high": max(bar.get("high") for bar in bars),
                "low": min(bar.get("low") for bar in bars), "close": bars[-1].get("close"),
                change_field: bars[-1].get("close") - bars[0].get("open"),
                pct_field: (bars[-1].get("close") / bars[0].get("open") - 1) * 100,
                "bar_count": len(bars), first_field: bars[0].get(time_key), last_field: bars[-1].get(time_key),
            }
            for field, value in expected.items():
                if field.endswith("time_et") or field.endswith("time_local"):
                    check(str(row.get(field)) == str(value), f"row_recompute:{key}:{field}", failures)
                else:
                    check(approx(row.get(field), value), f"row_recompute:{key}:{field}", failures)
            source_summary = obj.get("summary") or {}
            for row_field, source_field in [("previous_close", "previous_close"), ("day_change", "day_change"), ("day_pct", "day_change_pct")]:
                check(approx(row.get(row_field), source_summary.get(source_field)), f"row_source_summary:{key}:{row_field}", failures)
            checked += 1
    return {"series_paths": len(paths), "series_symbols_checked": checked}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()
    html_path, audit_path = Path(args.html).resolve(), Path(args.audit).resolve()
    failures: list[str] = []
    check(html_path.exists(), "html_exists", failures)
    check(audit_path.exists(), "audit_exists", failures)
    if failures:
        print(json.dumps({"status": "FAIL", "failures": failures}, ensure_ascii=False, indent=2))
        return 2

    html = html_path.read_text(encoding="utf-8")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    parser_obj = Parser()
    try:
        parser_obj.feed(html)
        parse_ok = True
    except Exception:
        parse_ok = False
    report_date = date.fromisoformat(str(audit.get("report_date")))
    market = str(audit.get("market") or "us").lower()
    is_cn = market == "cn"
    market_title = "A股每日盘后回顾" if is_cn else "美股每日盘后回顾"
    title = f"{market_title} — {report_date.year}年{report_date.month}月{report_date.day}日（{WEEKDAYS[report_date.weekday()]}）"
    report_type = audit.get("report_type")

    check(parse_ok, "html_parse", failures)
    check(f"<title>{title}</title>" in html and f"<h1>{title}</h1>" in html, "exact_title", failures)
    check("APPL" not in html, "APPL_absent", failures)
    check(not PLACEHOLDERS.search(html), "no_placeholders", failures)
    check("<style>" in html, "inline_css", failures)
    check(not re.search(r"<link[^>]+rel=[\"']?stylesheet", html, re.I), "no_external_stylesheet", failures)
    check("<script" not in html.lower(), "no_script", failures)
    check(not re.search(r"<(?:img|source)[^>]+src=[\"']https?://", html, re.I), "no_external_image", failures)
    check("@media (max-width: 560px)" in html, "mobile_css", failures)
    disclaimer = "本报告仅用于个人市场复盘与研究，不构成任何投资建议。市场数据可能存在延迟或口径差异，请以交易所、经纪商及官方公告为准。"
    check(disclaimer in html, "disclaimer", failures)
    header_end = html.find("</header>")
    header_html = html[:header_end] if header_end >= 0 else ""
    check(disclaimer in header_html, "disclaimer_inside_hero", failures)
    check(html.count(disclaimer) == 1, "disclaimer_exactly_once", failures)
    check(all(label not in header_html for label in ["生成时间：", "报告分支：", "数据边界：", "重点跟踪："]), "hero_metadata_removed", failures)
    check(hashlib.sha256(html_path.read_bytes()).hexdigest() == audit.get("html_sha256"), "html_sha256", failures)

    market_items = [normalize_item(item, ["title", "source_time", "fact", "inference", "url"]) for item in audit.get("market_news", [])]
    global_items = [normalize_item(item, ["title", "region", "source_time", "summary", "importance", "impact", "impact_score", "impact_type", "url"]) for item in audit.get("global_news", [])]
    voices = [normalize_voice(item) for item in audit.get("voices", [])]
    watches = [item for item in audit.get("next_watch", []) if isinstance(item, dict)]
    gaps = " ".join(str(item) for item in audit.get("data_gaps", []))
    check(all(item.get("title") and item.get("source_time") and item.get("url") for item in market_items), "market_news_per_item_source_time_url", failures)
    check(all(item.get("title") and item.get("region") and item.get("source_time") and item.get("url") for item in global_items), "global_news_per_item_source_time_url", failures)
    check(all(item.get("person") and item.get("time_platform") and item.get("platform") and item.get("quote") and item.get("url") for item in voices), "voices_required_fields", failures)
    check(all(not item.get("title") or (item.get("title_source_text") and item.get("url")) for item in voices), "voice_titles_have_original_source_text", failures)
    check(all(not re.search(r"[|｜]", str(item.get("person") or "")) for item in voices), "voice_person_name_only", failures)
    check(all(term not in html for term in ["热门网友评论", "原帖热评", "评论样本", "跨平台热度排名"]), "no_public_comment_content", failures)
    check(all(item.get("title") and item.get("detail") for item in watches), "watch_required_fields", failures)
    check(len(market_items) in range(5, 9) or "市场新闻" in gaps, "market_news_count_5_8_or_gap", failures)
    check(len(global_items) in range(6, 11) or "国际新闻" in gaps, "global_news_count_6_10_or_gap", failures)
    check(len(voices) in range(5, 11) or "人物" in gaps, "voices_count_5_10_or_gap", failures)
    check(bool(watches) or "日程" in gaps, "watch_present_or_gap", failures)

    expected_sections = ["数据说明、来源与时效", "一句话市场总览", "影响A股的关键新闻" if is_cn else "影响美股的关键新闻", "过去 24 小时国际新闻大事", "重要人物发言与言论", "下一交易日关注", "数据来源与说明"]
    check(all(section in html for section in expected_sections), "required_common_sections", failures)
    footer_pos = html.find('<footer class="section foot">')
    check(footer_pos >= 0 and html.find("数据说明、来源与时效", footer_pos) >= footer_pos, "data_notes_inside_footer", failures)
    check(html.find("一句话市场总览") < footer_pos, "data_notes_after_overview", failures)
    check('<div class="num">00</div>' not in html, "data_notes_not_numbered_section", failures)
    footer_html = html[footer_pos:] if footer_pos >= 0 else ""
    check('<div class="notice">' not in footer_html, "footer_not_yellow_callout", failures)

    series_result: dict[str, Any] = {}
    if report_type == "full_cn":
        cn_watchlist = audit.get("cn_watchlist") if isinstance(audit.get("cn_watchlist"), dict) else builtin_cn_watchlist()
        cn_watchlist_source = str(cn_watchlist.get("source") or "builtin_default")
        cn_custom_watchlist = cn_watchlist_source != "builtin_default"
        cn_stock_section_title = "核心关注个股表现" if cn_custom_watchlist else "核心科技龙头股表现"
        cn_sector_section_title = "申万行业与关注板块结构" if cn_custom_watchlist else "申万行业与科技板块结构"
        check(bool(str(audit.get("overview_lead") or "").strip()), "cn_overview_lead_present", failures)
        check('<p class="overview-lead"><strong>' in html, "cn_overview_lead_bold", failures)
        benchmark_start = html.find("上证综指 / 创业板指 / 科创50 日内走势分析")
        benchmark_end = html.find(cn_stock_section_title)
        benchmark_html = html[benchmark_start:benchmark_end] if 0 <= benchmark_start < benchmark_end else ""
        structure_html = html[html.find(cn_sector_section_title):html.find("影响A股的关键新闻")]
        check('<div class="notice">' not in benchmark_html, "cn_benchmark_analysis_not_yellow_callout", failures)
        check('<div class="notice">' not in structure_html, "cn_structure_analysis_not_yellow_callout", failures)
        benchmark_rows = [row for row in audit.get("rendered_benchmark_kpis", []) if isinstance(row, dict)]
        tickers = {str(row.get("ticker")) for row in benchmark_rows}
        check(tickers == {"SSE", "CHINEXT", "STAR50"}, "cn_three_cash_indexes", failures)
        check(all(isinstance(row.get("day_pct"), (int, float)) for row in benchmark_rows), "cn_index_moves_verified", failures)
        check("上证综指" in benchmark_html and "创业板指" in benchmark_html and "科创50" in benchmark_html, "cn_index_labels", failures)
        check('data-chart="line"' in benchmark_html and 'data-series-count="3"' in benchmark_html, "cn_benchmark_chart_three_series", failures)
        check("该图因数据不足未生成" not in benchmark_html, "cn_benchmark_chart_rendered", failures)
        full_sections = ["核心 KPI", cn_stock_section_title, "当日大幅波动股票", cn_sector_section_title]
        check(all(section in html for section in full_sections), "required_cn_full_sections", failures)
        check("今日A股休市，无需生成完整A股复盘" not in html, "cn_full_not_closed_phrase", failures)
        check(html.count('data-chart-slot="true"') == 5, "cn_full_visual_slots_5", failures)
        check(html.count("<svg") + html.count("该图因数据不足未生成") == 5, "cn_visual_slots_resolved", failures)
        core = [row for row in audit.get("key_stocks", []) if isinstance(row, dict)]
        configured_stocks = [row for row in cn_watchlist.get("stocks", []) if isinstance(row, dict)]
        expected_symbols = {str(row.get("symbol") or "") for row in configured_stocks}
        actual_symbols = {str(row.get("key") or "") for row in core}
        check(1 <= len(configured_stocks) <= 20, "cn_watchlist_stock_count_1_20", failures)
        check(len(core) == len(configured_stocks), "cn_core_matches_watchlist_count", failures)
        check(actual_symbols == expected_symbols, "cn_core_matches_watchlist_symbols", failures)
        if not cn_custom_watchlist:
            sector_counts: dict[str, int] = {}
            for row in core:
                sector = str(row.get("sector") or "")
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
            check(len(core) == 10, "cn_builtin_core_stocks_10", failures)
            check(all(count <= 3 for count in sector_counts.values()), "cn_builtin_core_max_three_per_sector", failures)
        movers = [row for row in audit.get("movers", []) if isinstance(row, dict)]
        filters = audit.get("mover_filter") or {}
        min_amount = float(filters.get("min_amount_cny") or 0)
        min_days = int(filters.get("min_listing_days") or 0)
        check(filters.get("exclude_bse") is True, "cn_movers_exclude_bse_config", failures)
        check(all(not str(row.get("key") or "").startswith("bj") for row in movers), "cn_movers_no_bse", failures)
        check(all(not re.search(r"(?:\*?ST|退市|退)", str(row.get("name") or ""), re.I) for row in movers), "cn_movers_no_st_delisting", failures)
        check(all(float(row.get("amount") or 0) >= min_amount for row in movers), "cn_movers_min_amount", failures)
        check(all(int(row.get("listing_days_observed") or 0) >= min_days for row in movers), "cn_movers_min_listing_days", failures)
        check(len(movers) == 10 or "movers only" in gaps or "historical mover" in gaps.lower(), "cn_movers_10_or_gap", failures)
        cn_sectors = audit.get("cn_sectors") or {}
        fixed_names = {str(row.get("name")) for row in cn_sectors.get("fixed_tech", []) if isinstance(row, dict)}
        configured_sectors = {str(value) for value in cn_watchlist.get("sectors", []) if str(value).strip()}
        check(1 <= len(configured_sectors) <= 8, "cn_watchlist_sector_count_1_8", failures)
        check(fixed_names == configured_sectors, "cn_fixed_sectors_match_watchlist", failures)
        check(len(cn_sectors.get("top5", [])) == 5, "cn_sector_top5", failures)
        check(len(cn_sectors.get("bottom5", [])) == 5, "cn_sector_bottom5", failures)
        check("北京时间09:30–11:30、13:00–15:00" in html, "cn_session_text", failures)
        series_result = validate_series(audit, failures)
    elif report_type == "full_rth":
        us_watchlist = audit.get("us_watchlist") if isinstance(audit.get("us_watchlist"), dict) else builtin_us_watchlist()
        us_watchlist_source = str(us_watchlist.get("source") or "builtin_default")
        us_custom_watchlist = us_watchlist_source != "builtin_default"
        us_stock_section_title = "重点关注股 RTH 表现" if us_custom_watchlist else "重点科技股 RTH 表现"
        us_sector_section_title = "关注板块与市场结构" if us_custom_watchlist else "板块与市场结构"
        if not us_custom_watchlist:
            check("AAPL" in html, "AAPL_present", failures)
        check(bool(str(audit.get("overview_lead") or "").strip()), "full_overview_lead_present", failures)
        check('<p class="overview-lead"><strong>' in html, "full_overview_lead_bold", failures)
        benchmark_section_start = html.find("标普500 / 纳斯达克100 RTH 走势分析")
        benchmark_section_end = html.find(us_stock_section_title)
        benchmark_section_html = html[benchmark_section_start:benchmark_section_end] if 0 <= benchmark_section_start < benchmark_section_end else ""
        check('<div class="notice">' not in benchmark_section_html, "benchmark_analysis_not_yellow_callout", failures)
        check('<div class="notice">' not in html[html.find(us_sector_section_title):html.find("影响美股的关键新闻")], "structure_analysis_not_yellow_callout", failures)
        kpi_start, kpi_end = html.find("核心 KPI"), benchmark_section_start
        kpi_html = html[kpi_start:kpi_end] if 0 <= kpi_start < kpi_end else ""
        overview_start = html.find("一句话市场总览")
        benchmark_scope_html = html[overview_start:benchmark_section_end] if 0 <= overview_start < benchmark_section_end else ""
        benchmark_rows = [row for row in audit.get("rendered_benchmark_kpis", []) if isinstance(row, dict)]
        check(len(benchmark_rows) == 2 and all(isinstance(row.get("day_pct"), (int, float)) for row in benchmark_rows), "benchmark_kpis_two_verified", failures)
        check("<span>标普500</span>" in kpi_html and "<span>纳斯达克100</span>" in kpi_html, "benchmark_kpi_short_labels", failures)
        check("（SPY ETF代理）" not in kpi_html and "（QQQ ETF代理）" not in kpi_html, "benchmark_kpi_no_proxy_parentheses", failures)
        for row in benchmark_rows:
            if row.get("is_proxy"):
                ticker = str(row.get("ticker") or "")
                check(f"{ticker} ETF代理" in str(row.get("kpi_basis") or ""), f"benchmark_proxy_basis:{ticker}", failures)
        benchmark_tickers = {str(row.get("ticker") or "").upper() for row in benchmark_rows}
        check(bool(benchmark_tickers & {"SPX", "SPY"}) and bool(benchmark_tickers & {"NDX", "QQQ"}), "benchmark_pair_spx_ndx_or_matching_proxies", failures)
        check("IXIC" not in benchmark_tickers, "benchmark_no_ixic", failures)
        check("纳斯达克综合指数" not in benchmark_scope_html and "IXIC" not in benchmark_scope_html, "benchmark_scope_no_composite_mixing", failures)
        check(not re.search(r'<article class="kpi[^>]*><span>(?:ES|NQ)</span>', kpi_html), "no_es_nq_kpi_cards", failures)
        check("未核验" not in kpi_html, "no_unverified_kpi_cards", failures)
        check("标普500 / 纳斯达克100 RTH 归一化走势" in benchmark_section_html, "benchmark_trend_chart_title", failures)
        check('data-chart="line"' in benchmark_section_html and 'data-series-count="2"' in benchmark_section_html, "benchmark_trend_chart_two_series", failures)
        check("该图因数据不足未生成" not in benchmark_section_html, "benchmark_trend_chart_rendered", failures)
        check("ES / NQ RTH 走势分析" not in html, "legacy_futures_section_removed", failures)
        full_sections = ["核心 KPI", "标普500 / 纳斯达克100 RTH 走势分析", us_stock_section_title, "当日大幅波动股票", us_sector_section_title]
        check(all(section in html for section in full_sections), "required_full_sections", failures)
        check("今日美股休市，无需生成完整美股复盘" not in html, "full_not_closed_phrase", failures)
        check(html.count('data-chart-slot="true"') == 5, "full_visual_slots_5", failures)
        check(html.count("<svg") + html.count("该图因数据不足未生成") == 5, "full_visual_slots_resolved", failures)
        tickers = {str(row.get("ticker")) for row in audit.get("key_stocks", []) if isinstance(row, dict)}
        configured_stock_tickers = {str(row.get("ticker")) for row in us_watchlist.get("stocks", []) if isinstance(row, dict)}
        configured_sector_tickers = {str(row.get("ticker")) for row in us_watchlist.get("sectors", []) if isinstance(row, dict)}
        rendered_sector_tickers = {str(row.get("ticker")) for row in audit.get("sectors", []) if isinstance(row, dict)}
        check(1 <= len(configured_stock_tickers) <= 20, "us_watchlist_stock_count_1_20", failures)
        check(1 <= len(configured_sector_tickers) <= 20, "us_watchlist_sector_count_1_20", failures)
        check(tickers == configured_stock_tickers, "us_core_matches_watchlist_tickers", failures)
        check(rendered_sector_tickers == configured_sector_tickers, "us_sectors_match_watchlist_tickers", failures)
        if not us_custom_watchlist:
            check({"INTC", "NVDA", "GOOG", "MSFT", "AAPL", "SKHY", "TSM"}.issubset(tickers), "required_core_stocks", failures)
        check(len(audit.get("movers", [])) in range(8, 16) or "波动股" in gaps, "mover_count_8_15_or_gap", failures)
        check("美东 09:30–16:00" in html, "strict_rth_text", failures)
        series_result = validate_series(audit, failures)
    elif report_type in {"closed_market", "closed_cn"}:
        phrase = "今日A股休市，无需生成完整A股复盘" if report_type == "closed_cn" else "今日美股休市，无需生成完整美股复盘"
        check(phrase in html, "closed_phrase", failures)
        check("标普500 / 纳斯达克100 RTH 走势分析" not in html and "上证综指 / 创业板指 / 科创50 日内走势分析" not in html, "closed_no_benchmark_section", failures)
        check("当日大幅波动股票" not in html, "closed_no_movers_section", failures)
        check(html.count('data-chart-slot="true"') == 1, "closed_visual_slots_1", failures)
        check(not audit.get("futures") and not audit.get("key_stocks") and not audit.get("movers"), "closed_no_session_payload", failures)
    else:
        failures.append("valid_report_type")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "html": str(html_path), "audit": str(audit_path), "report_type": report_type,
        "title": title, "html_bytes": html_path.stat().st_size, "source_links": len(parser_obj.links),
        "svg_count": html.count("<svg"), "visual_slots": html.count('data-chart-slot="true"'),
        "market_news": len(market_items), "global_news": len(global_items), "voices": len(voices),
        "movers": len(audit.get("movers", [])), **series_result, "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
