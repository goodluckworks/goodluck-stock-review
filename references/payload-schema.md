# Report payload schema

The renderer consumes UTF-8 JSON. Final payloads must not contain `TODO`, `TBD`, `PLACEHOLDER`, or `待补充`.

## Top-level fields

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `market` | string | no | `us` (default) or `cn`. |
| `report_date` | string | yes | Evaluated market calendar date, `YYYY-MM-DD`. |
| `report_type` | string | yes | U.S.: `full_rth`/`closed_market`; China: `full_cn`/`closed_cn`. |
| `generated_at` | string | yes | Human-readable timestamp with timezone. |
| `subtitle` | string | no | Hero subtitle; renderer supplies default. |
| `overview_lead` | string | full | One concise Chinese lead sentence, starting with verified sector winners/losers when sector data is available; rendered in bold. |
| `overview` | string | yes | Three-to-five-sentence Chinese market summary or closed-market explanation. |
| `data_notes` | string[] | yes | RTH/source/delay/gap notes; rendered quietly in the bottom source/disclaimer footer. |
| `data_gaps` | string[] | yes | Explicit unresolved data/research gaps; may be empty. |
| `series_files` | object | full | Paths to raw TradingView JSON files. Values may be string or string array. |
| `benchmark_kpis` | row[] | full | Resolved SPX/NDX rows or SPY/QQQ fallbacks; drives both KPI cards and the section-03 table/chart. |
| `benchmark_analysis` | string | no | Evidence-backed S&P 500/Nasdaq-100 intraday comparison for section 03. |
| `futures` | row[] | no | Optional legacy ES and NQ summary rows; not required for the shareable report. |
| `key_stocks` | row[] | full | Core stocks plus optional SPCX. |
| `sectors` | row[] | full | Sector/index ETF rows. |
| `macro` | row[] | full | VIX, US10Y, DXY, WTI, Gold when available. |
| `movers` | mover[] | full | 8–15 verified movers when possible. |
| `market_news` | item[] | yes | 5–8 items. |
| `global_news` | item[] | yes | 6–10 items. |
| `voices` | item[] | yes | 5–10 items. |
| `next_watch` | item[] | yes | Sourced next-session items. |
| `sources` | object | yes | `{label: url}` source index. |
| `cn_sectors` | object | China full | `fixed_tech`, `top5`, `bottom5`, and `significant_tech_concepts`. |
| `cn_watchlist` | object | China | Effective A-share sectors/stocks and configuration source: `builtin_default`, `local_override`, or `explicit_file`. |
| `mover_filter` | object | China full | Market scope, BSE exclusion, ST/delisting rules, minimum listing days, and minimum amount. |
| `us_watchlist` | object | U.S. full | Effective ordered U.S. stocks/sector proxies and source: `builtin_default`, `local_override`, or `explicit_file`. |

## Market row

```json
{
  "key": "NVDA",
  "ticker": "NVDA",
  "name": "NVIDIA",
  "open": 0,
  "high": 0,
  "low": 0,
  "close": 0,
  "rth_change": 0,
  "rth_pct": 0,
  "previous_close": 0,
  "day_change": 0,
  "day_pct": 0,
  "volume": 0,
  "bar_count": 78,
  "first_time_et": "YYYY-MM-DDT09:30:00-04:00",
  "last_time_et": "YYYY-MM-DDT15:55:00-04:00",
  "comment": "Source-backed intraday description",
  "source": "https://..."
}
```

Numbers may be `null` only when the row is deliberately retained to show a disclosed gap. Do not use zero for unknown values.

For China rows, use `session_change`, `session_pct`, `first_time_local`, and `last_time_local` instead of the U.S.-specific `rth_*` and `*_time_et` fields. `day_pct` always means previous official close to target-date close. China raw bars use `time_local` with an explicit `+08:00` offset and must fall inside 09:30–11:30 or 13:00–15:00.

Benchmark rows also include `kpi_label`, `kpi_basis`, and `is_proxy`. Always use the short labels `标普500` and `纳斯达克100`. Use `现金指数 · 前收至收盘` for SPX/NDX, or `SPY ETF代理 · 前收至收盘` / `QQQ ETF代理 · 前收至收盘` for fallback rows. Do not put proxy wording in `kpi_label`, and never place IXIC in this field.

## Mover

Extend a market row with:

```json
{
  "driver": "Verified event and cautious interpretation",
  "category": "财报/指引",
  "source": "https://..."
}
```

Sort by absolute `day_pct` or explained market importance. A mover with missing prices should normally be excluded; retain only when the missing price itself is clearly disclosed and the report still meets quality standards.

## Market-news item

Preferred object shape:

```json
{
  "title": "...",
  "source_time": "AP：YYYY-MM-DD HH:MM UTC",
  "fact": "[事实] ...",
  "inference": "[推断] 市场可能解读为...",
  "url": "https://..."
}
```

The renderer also accepts the legacy list shape `[title, source_time, fact, inference, url]`.

## Global-news item

```json
{
  "title": "...",
  "region": "...",
  "source_time": "...",
  "summary": "...",
  "importance": "...",
  "impact": "...",
  "impact_score": 4,
  "impact_type": "能源/地缘",
  "url": "https://..."
}
```

The renderer also accepts `[title, region, source_time, summary, importance, impact, impact_score, impact_type, url]`.

## Important-person item

```json
{
  "person": "黄仁勋｜NVIDIA创始人兼CEO",
  "time_platform": "YYYY-MM-DD；LinkedIn",
  "platform": "LinkedIn",
  "quote": "Short verified excerpt or clearly labeled paraphrase",
  "context": "Why it matters and verification boundary",
  "comments": "Auditable selected comments or explicit absence disclosure",
  "url": "https://...",
  "comment_url": "https://..."
}
```

Legacy list: `[person, time_platform, platform, quote, context, comments, url, comment_url]`.

## Next-watch item

```json
{
  "time": "08:30 ET",
  "title": "U.S. CPI",
  "detail": "What is confirmed and which assets may react",
  "source_label": "BLS official",
  "url": "https://..."
}
```

If no reliable URL exists for a proposed schedule, use a visible `暂无可靠来源确认` item and omit invented timing.

## Raw series file shape

The bundled TradingView fetcher writes:

```json
{
  "source": "TradingView anonymous chart websocket",
  "resolution": "5",
  "report_date": "YYYY-MM-DD",
  "symbols": {
    "NVDA": {
      "tradingview_symbol": "NASDAQ:NVDA",
      "summary": {"open": 0, "high": 0, "low": 0, "close": 0},
      "bars": [
        {"time_et": "YYYY-MM-DDT09:30:00-04:00", "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}
      ]
    }
  }
}
```

`series_files` can point to multiple retry/mover files. Later files override the same symbol key only when they contain a non-empty series.

The Sina China adapter uses the same top-level `symbols` map, with `time_local` bars and `summary.day_change_pct`. It may also include `sectors`, `movers`, `mover_filter`, `watchlist`, `latest_market_date_seen`, and `warnings`. `watchlist` preserves the effective ordered sectors/stocks and its source without an absolute user path. A historical request must not reuse a later ranking/sector snapshot.
