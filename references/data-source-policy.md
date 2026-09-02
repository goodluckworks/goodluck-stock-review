# Data and source policy

This file defines the unchanged U.S. source policy. For A-share requests, also apply `cn-market-policy.md`; never substitute China-market rules into a U.S. run or vice versa.

## 1. Date gate

1. Convert the execution instant to `America/New_York`.
2. Identify the U.S. calendar date being evaluated.
3. Determine whether 16:00 ET RTH has completed. Use a short post-close buffer for upstream finalization.
4. Verify the date against both official NYSE and official Nasdaq calendar/hours sources.
5. Treat early closes as a special case verified from exchange sources; do not assume 16:00 on an early-close day.
6. Use the U.S. date in the filename and Chinese title.

If the date is a weekend, holiday, or incomplete cash session, use `closed_market`. Do not roll the filename back to the prior trading day. Prior-session figures may appear only as explicitly labeled background.

## 2. RTH definitions

- RTH window: Eastern time `09:30 <= timestamp <= 16:00` for the target date.
- RTH open: first included bar's open.
- RTH high/low: extrema across included bars.
- RTH close: last included bar's close. For many stocks/ETFs this is the bar beginning at 15:55; disclose that it can differ slightly from an exchange-certified official close.
- RTH change: `RTH close - RTH open`.
- RTH percent: `(RTH close / RTH open - 1) * 100`.
- Previous-close change: `last RTH close - previous regular-session close`.
- Previous-close percent: `(last RTH close / previous regular-session close - 1) * 100`.

Never label the previous-close move as RTH. Never use a futures 24-hour session as the ES/NQ RTH series.

Five-minute expected coverage is usually 79 bars for ES/NQ and some macro series (including a 16:00 timestamp), and 78 bars for stocks/ETFs (last bar begins 15:55). These are diagnostics, not permission to pad. Preserve the actual count.

## 3. Instrument mappings

| Report label | Preferred TradingView mapping | Notes |
|---|---|---|
| ES | `CME_MINI:ES1!` | Continuous futures; disclose contract/roll differences. |
| NQ | `CME_MINI:NQ1!` | Continuous futures; disclose contract/roll differences. |
| SPX | `SP:SPX` | S&P 500 cash index; preferred close-to-close KPI benchmark. |
| NDX | `NASDAQ:NDX` | Nasdaq-100 cash index; preferred close-to-close KPI benchmark. |
| INTC | `NASDAQ:INTC` | Core stock. |
| NVDA | `NASDAQ:NVDA` | Core stock. |
| GOOG | `NASDAQ:GOOG` | Class C. |
| MSFT | `NASDAQ:MSFT` | Core stock. |
| AAPL | `NASDAQ:AAPL` | Required spelling in output. |
| SKHY | `NASDAQ:SKHY` | Verify listing/series on every run. |
| TSM | `NYSE:TSM` | ADR. |
| SPCX | `NASDAQ:SPCX` | Standing candidate only when it resolves. |
| VIX | `CBOE:VIX` | Index; volume may be unavailable. |
| US10Y | `TVC:US10Y` | Yield index; interpret changes in percentage points/basis points. |
| DXY | `TVC:DXY` | Dollar index proxy. |
| WTI | `NYMEX:CL1!` | Continuous futures; isolated retry may be needed. |
| Gold | `COMEX:GC1!` | Continuous futures. |

Sector structure can use liquid ETF proxies such as SPY, QQQ, DIA, IWM, XLK, SOXX/SMH, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLC, XLB, XLRE. Verify the exact symbol and disclose proxy use.

These stocks and sector proxies form the built-in first-run list. A verified user-local list may replace them, but it must preserve ticker/name/TradingView mapping and cannot replace the fixed SPX/NDX plus SPY/QQQ benchmark pair. Store the effective list and source in raw data, payload, and audit JSON without exposing an absolute home path.

For shareable KPI cards and the section-03 comparison chart, always use the fixed benchmark pair SPX and NDX. When they are unavailable, SPY and QQQ provide their matching fallbacks. Card titles remain `标普500` and `纳斯达克100`; the basis line must say `SPY ETF代理` or `QQQ ETF代理`, and the table exposes the actual ticker. Do not substitute ES/NQ or the Nasdaq Composite/IXIC. Fetch SPY and QQQ alongside SPX and NDX so the fallback is available without a second recovery run. A final full report requires two real benchmark series for the comparison chart.

The market overview and benchmark analysis must use the same fixed pair and labels. Never use a Nasdaq Composite figure or name to narrate an NDX/QQQ value.

## 4. Price-source hierarchy and recovery

1. Use TradingView anonymous chart WebSocket with `session=regular` for minute/five-minute RTH bars.
2. Use exchange, company, AP/Reuters, or another authoritative source to cross-check cash-index close and contextual narrative.
3. Treat source disagreement as different instrument/session/aggregation definitions until reconciled.
4. Retry null/empty symbols separately. A successful HTTP/WebSocket exchange with `summary=null` is still missing data.
5. Do not promote a retry series until timestamps, date, and OHLC recomputation pass.
6. Exclude unresolved movers; disclose them rather than inserting media-only prices into a TradingView chart.
7. If only 15-minute data is available, label every affected table/chart accordingly.
8. Never interpolate or duplicate bars to create apparent completeness.

## 5. News and event evidence

Use direct sources whenever possible:

- exchange calendars and notices;
- BLS, BEA, Census, Federal Reserve, Treasury, SEC and other official data;
- company investor relations, earnings releases, filings, and prepared remarks;
- AP, Reuters, Bloomberg, CNBC, WSJ, FT, MarketWatch, Yahoo Finance;
- social-platform originals only when the public post can be inspected.

Every item needs source name, publication/update time, direct URL, and event/reaction/logic separation. Put uncertain causal claims in conditional language such as `市场可能解读为`, `可能对…形成影响`, or `尚未得到可靠证实`.

For the 24-hour international section, verify that the event happened or materially updated inside the window. An older event may remain only if there is a new, sourced development, and should be marked `仍在发展中` where applicable.

## 6. Quotes and source-verified person titles

- Quote at most a short verifiable excerpt.
- If the exact original post is unavailable, use a paraphrase and label the intermediary source.
- Store the platform only when confirmed.
- Keep `person` as the person's name only.
- Add `title` only when the cited original source explicitly states that role or title; preserve the exact source wording in `title_source_text` for audit.
- A translated title must remain faithful to the original wording and cannot add seniority, organization, scope, or function.
- If the source does not state a title, omit it and show only the person's name. Do not fill it from memory, search-result snippets, biographies, or other sources.
- Do not collect, summarize, store, or render public-comment samples, engagement counts, or comment rankings.

## 7. Tomorrow-watch evidence

Prefer official economic calendars, Federal Reserve calendars, company IR dates, exchange/clearing notices, and primary event notices. If a precise schedule is not reliably confirmed, write `暂无可靠来源确认`.

Technical levels may use only already-observed RTH highs/lows or clearly computed values. Present them as monitoring references, not predictions or advice.

## 8. Missing-data disclosure

Put all gaps in both `data_notes` and `data_gaps`. Common examples:

- missing or short TradingView series;
- absent previous regular close;
- public aggregator instead of exchange-certified price;
- continuous-futures roll/settlement difference;
- 15:55 final stock bar;
- unverified single-stock catalyst;
- unavailable original social post;
- unresolved schedule/time;
- article timestamp unavailable.

Use `该图因数据不足未生成` for a visual slot that lacks real data.

## 9. Research safety checks

- Search the final HTML for stale dates and prior-day market wording.
- Confirm all quoted numbers appear in source data or a cited source.
- Confirm every price-bearing row has a source chain.
- Confirm no after-hours earnings result is used to explain that same day's RTH unless it was released before/during RTH.
- Separate cash-index close from futures and ETF proxy moves.
- Do not publish speculative causality as fact.
