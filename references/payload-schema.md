# Report payload schema

The renderer consumes UTF-8 JSON. Final payloads must not contain `TODO`, `TBD`, `PLACEHOLDER`, or `待补充`.

## Top-level fields

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `report_date` | string | yes | U.S. calendar date, `YYYY-MM-DD`. |
| `report_type` | string | yes | `full_rth` or `closed_market`. |
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
