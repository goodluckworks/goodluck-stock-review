---
name: goodluck-us-market-daily-review
description: Generate, repair, or quality-check the user's recurring standalone Chinese U.S. post-close market review HTML and audit JSON. Use for “美股每日总结”, “美股盘后回顾”, “每日美股复盘”, market_review_YYYY-MM-DD.html, strict 09:30–16:00 ET RTH data, TradingView five-minute charts, weekend/holiday branches, market and global news, important-person quotes, tomorrow-watch items, or visual QA of this report family.
---

# Generate U.S. Market Daily Review

Produce the saved HTML artifact first, then report its path and caveats. Treat evidence quality, strict RTH boundaries, source traceability, and visual review as hard deliverable requirements.

## Read the required references

Read these files completely before producing or repairing a report:

1. `references/report-contract.md` — full standing output contract.
2. `references/data-source-policy.md` — date gate, RTH definitions, source hierarchy, missing-data rules, and research boundaries.
3. `references/payload-schema.md` — renderer input fields and supported item shapes.
4. `references/visual-qa.md` — desktop/mobile rendering review and fallback checks.

Use the bundled resources rather than recreating them:

- `scripts/resolve_report_date.py` for the preliminary U.S.-date and close-state calculation.
- `scripts/fetch_tradingview_rth.py` for anonymous TradingView regular-session bars.
- `scripts/build_payload_skeleton.py` to turn raw price files into the content payload skeleton.
- `scripts/render_market_review.py` for the standalone HTML and audit JSON.
- `scripts/validate_market_review.py` for price, content, HTML, and self-containment checks.
- `assets/report.css` for the validated report design.

## Workflow

### 1. Resolve the report date and branch before research

Run:

```bash
python3 scripts/resolve_report_date.py
```

Use the returned U.S. Eastern date, not the computer's local date. Then verify the candidate against both an official NYSE calendar/hours source and an official Nasdaq calendar source.

- If it is a weekday trading session and RTH has fully closed, use `full_rth`.
- If it is a weekend, exchange holiday, or incomplete RTH, use `closed_market` and include exactly `今日美股休市，无需生成完整美股复盘`.
- Do not fetch or display same-day RTH OHLC, movers, or minute charts on the closed/incomplete branch.
- Do not infer an early close from weekday logic; verify it from the exchange calendar.

### 2. Read the standing project state

When running in the user's daily-report project, read the latest automation memory and the newest relevant report/audit pair before collecting fresh data. Reuse workflow conventions, not stale price data or narrative.

Resolve the output root in this order:

1. Use the folder explicitly supplied by the user or automation.
2. Otherwise use the current daily-report workspace when one is already open.
3. Otherwise create and use the current user's `~/Desktop/美股每日总结` folder.

Portable fallback:

```text
~/Desktop/美股每日总结
```

### 3. Collect and validate price data for `full_rth`

Fetch in this order: core assets, sector/macro proxies, then a small news-driven mover batch. Keep each raw response in `data/`.

Core symbols:

- `SP:SPX`, `NASDAQ:NDX` for the preferred benchmark KPI cards and RTH comparison chart
- `AMEX:SPY`, `NASDAQ:QQQ` as the always-fetched fallback pair for the same cards and chart
- `NASDAQ:INTC`, `NASDAQ:NVDA`, `NASDAQ:GOOG`, `NASDAQ:MSFT`, `NASDAQ:AAPL`
- `NASDAQ:SKHY`, `NYSE:TSM`
- standing candidate `NASDAQ:SPCX` when it resolves

Example:

```bash
python3 scripts/fetch_tradingview_rth.py \
  --date YYYY-MM-DD \
  --output data/tradingview_rth_YYYY-MM-DD.json \
  --symbols SPX NDX SPY QQQ INTC NVDA GOOG MSFT AAPL SKHY TSM SPCX
```

Use only bars whose Eastern timestamp is within 09:30–16:00 on the report date. Keep RTH open-to-last-bar change separate from previous-regular-close-to-last-bar change.

For the two leading KPI cards and the section-03 RTH comparison, use one fixed benchmark pair: the cash S&P 500 (`SPX`) and Nasdaq-100 (`NDX`). If either cash-index series is unavailable, fall back only to its matching ETF proxy, `SPY` or `QQQ`. Keep the card titles short as `标普500` and `纳斯达克100`; identify a fallback in the smaller basis line as `SPY ETF代理` or `QQQ ETF代理`. Never substitute the Nasdaq Composite (`IXIC`) for `NDX`, and never label `QQQ` as a Nasdaq Composite proxy. The table and chart use the same resolved benchmark rows, so missing ES/NQ must never suppress the section-03 chart. Omit any benchmark whose cash-index and ETF-proxy series are both missing; a final full report requires both benchmark series.

Carry the same pair into `overview_lead`, `overview`, and `benchmark_analysis` whenever they discuss the two primary benchmark moves. Do not describe an NDX/QQQ result as `纳斯达克综合指数`. The Nasdaq Composite may appear only as a separately sourced, explicitly named supplemental asset outside the fixed benchmark comparison.

Retry isolated failed symbols once or twice in smaller files. Merge only successful, auditable series. Keep actual short-series bar counts; never pad. Exclude unresolved movers from price charts/tables and disclose the omission.

### 4. Research the same evidence window

Use current web research because market data, news, quotes, schedules, and public figures are time-sensitive. Prefer primary or authoritative sources:

1. exchange/official economic data/company IR/SEC/Federal Reserve;
2. AP, Reuters, Bloomberg, CNBC, WSJ, FT, MarketWatch, Yahoo Finance;
3. social platforms only for clearly labeled original posts or selected public-comment samples.

For each market-news item, store event, affected assets, observed reaction, cautious logic chain, source name, timestamp, and direct URL. For each global-news item, store region, summary, why it matters, possible impact, source/time, and development status.

For important-person items, use a short verifiable original quote only when the original text is available. Otherwise label it as a source paraphrase. Do not invent a platform, timestamp, quote, engagement count, or popular-comment ranking. Write `未找到可审计的原帖热评排名` when necessary.

Separate facts from inference with `[fact]` / `[inference]` in the payload or `[事实]` / `[推断]` in Chinese copy. Do not use price action alone as proof of a catalyst.

### 5. Build the payload

Create a draft skeleton from verified price files:

```bash
python3 scripts/build_payload_skeleton.py \
  --date YYYY-MM-DD \
  --core data/tradingview_rth_YYYY-MM-DD.json \
  --benchmark data/tradingview_rth_YYYY-MM-DD.json \
  --sector data/tradingview_sector_YYYY-MM-DD.json \
  --macro data/tradingview_macro_YYYY-MM-DD.json \
  --movers data/tradingview_movers_YYYY-MM-DD.json \
  --output data/report_payload_YYYY-MM-DD.json
```

Complete every content field from verified research. Remove all `TODO` values before rendering. Include 5–8 market-news items, 6–10 global-news items, 5–10 important-person items, 8–15 movers when verifiable, and a sourced next-trading-day watch list. If evidence cannot support a target count, include an explicit `data_gaps` entry and do not fabricate filler.

For `full_rth`, write `overview_lead` as one concise, evidence-backed market-regime sentence. Lead with the strongest verified sector structure—what rose and what fell—then state the broad tape direction. Keep the remaining 3–5-sentence explanation in `overview`. The renderer bolds only `overview_lead`. Put RTH/source/frequency/delay notes in `data_notes`; they render quietly inside the bottom `数据来源与说明` footer rather than as a numbered opening section. The exact investment disclaimer belongs in the hero below the subtitle; do not repeat it in the footer or show report-branch, data-boundary, tracked-symbol, or generation-time metadata in the hero.

### 6. Render the artifact

Run:

```bash
python3 scripts/render_market_review.py \
  --input data/report_payload_YYYY-MM-DD.json \
  --output market_review_YYYY-MM-DD.html \
  --audit-output data/market_data_YYYY-MM-DD.json
```

The renderer refuses unfinished placeholders unless `--allow-draft` is explicitly used for a non-final preview. The final file must not use that flag.

For `full_rth`, keep five visual slots: S&P 500/Nasdaq-100 normalized RTH line, key-stock normalized line, key-stock RTH bar, mover day-move bar, and global-news impact chart. The first chart must contain both resolved benchmark series and must not depend on ES/NQ. A slot may show `该图因数据不足未生成` only when the gap is disclosed, but a final shareable full report must resolve the benchmark comparison through SPX/NDX or SPY/QQQ. For `closed_market`, render only the qualitative global-news impact visual and omit same-day RTH/mover sections.

### 7. Run deterministic QA

Run sequentially after the final files are written:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 -m py_compile scripts/*.py
python3 scripts/validate_market_review.py \
  --html market_review_YYYY-MM-DD.html \
  --audit data/market_data_YYYY-MM-DD.json
```

Do not finish with a failed validation. Fix and rerun. Hard checks include date/title, strict RTH timestamps, recomputed OHLC/change, AAPL spelling, required sections, item counts or explicit gaps, per-item links, inline CSS, no external JS/CSS/images, SVG/placeholder slots, disclaimer, and closed-market isolation.

### 8. Perform visual QA

Follow `references/visual-qa.md`. Serve the output through local HTTP when `file://` is blocked. Inspect at least desktop and narrow/mobile widths. Check the hero, KPI wrapping, tables, SVG labels, long Chinese headlines, quote cards, sources, and footer. Iterate until there is no clipping, overlap, illegible axis text, or broken hierarchy.

### 9. Save and hand off

Save the HTML to the fixed output root using `market_review_YYYY-MM-DD.html`. Save the audit JSON and raw market inputs under `data/`. When running from the standing automation, append a concise durable record to its memory: report type, paths, raw sources, QA outcome, and unresolved gaps. Do not store transient market opinions as automation memory.

Return only a concise completion summary containing:

1. success/failure;
2. absolute HTML path;
3. U.S. report date and branch;
4. main data/news sources;
5. missing data or manual-review items;
6. static and visual QA status.

## Non-negotiable rules

- Never fabricate prices, moves, volume, news, quotes, comments, sources, or causal explanations.
- Never mix premarket, after-hours, or 24-hour futures data into an RTH claim.
- In the shareable report, use verified cash-index rows for the S&P 500 and Nasdaq-100 KPI cards and section-03 chart; fall back to SPY/QQQ with the proxy ticker disclosed in the smaller basis line, never inside the card title, and never use ES/NQ or Nasdaq Composite/IXIC as the dependency.
- Never clone yesterday's narrative without re-researching and scrubbing stale dates/copy.
- Keep `AAPL` consistent throughout every saved artifact.
- Treat `SPCX` as `NASDAQ:SPCX` only when that mapping resolves on the run date.
- Label TradingView as a public aggregated chart source, not an exchange-certified close.
- Label stock 15:55 5-minute bars as the final regular-session bar when applicable.
- Preserve visible source name, publication/update time, and link for every news/person item.
- Replace unsupported visuals or explanations with explicit gaps; do not synthesize missing evidence.
- Do not provide buy, sell, or position advice.
