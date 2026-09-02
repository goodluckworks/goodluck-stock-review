---
name: goodluck-stock-review
description: Generate, repair, or quality-check standalone Chinese U.S. or China A-share post-close market review HTML and audit JSON. Use for 美股/A股每日总结、盘后回顾、指定日期复盘、指数与科技股走势、异动股、市场新闻、次日关注或视觉质量检查；route by the market explicitly named in the prompt.
---

# Generate U.S. or China A-share Market Daily Review

Produce the saved HTML artifact first, then report its path and caveats. Treat evidence quality, strict session boundaries, source traceability, and visual review as hard deliverable requirements. The A-share branch is additive: do not change or weaken the existing U.S. workflow.

## Route by the user's prompt

- If the prompt says `美股`, `U.S. market`, `NYSE`, `Nasdaq` or names the existing U.S. output, use the unchanged U.S. workflow below.
- If the prompt says `A股`, `沪深`, `上证`, `创业板` or `科创50`, use the China workflow in `references/cn-market-policy.md`.
- The two automations should use explicit prompts such as `生成美股每日总结` and `生成A股每日总结`. Do not infer the market from execution time when the prompt is ambiguous; ask which market is intended.
- U.S. output remains `market_review_YYYY-MM-DD.html` with `data/market_data_YYYY-MM-DD.json`.
- China output is `cn_market_review_YYYY-MM-DD.html` with `data/cn_market_data_YYYY-MM-DD.json`, so same-date reports never overwrite each other.

## Manage the user's local market defaults

The bundled A-share sectors and core stocks are the first-run fallback. When the user explicitly asks to `修改/更换/保存我的A股默认关注板块或个股`, treat that as a persistent local preference update, not as a one-report content edit.

1. Read `references/cn-market-policy.md` and verify each requested stock code/name and each exact Sina Shenwan level-one sector name from current reliable sources. Do not guess or silently substitute.
2. Save the verified list with `scripts/manage_cn_watchlist.py set`. The helper writes `~/.goodluck-stock-review/cn-watchlist.json`, outside the installed Skill, so reinstalling or upgrading the Skill does not overwrite the user's preferences.
3. Confirm the saved result with `scripts/manage_cn_watchlist.py show`. Future A-share runs automatically load it; the user does not need to repeat the list in daily report prompts.
4. When the user asks to `恢复内置默认名单`, run `scripts/manage_cn_watchlist.py reset`. This removes only the local override and restores the bundled sectors/stocks.

Example agent-side save command (users should not need to know this syntax):

```bash
python3 scripts/manage_cn_watchlist.py set \
  --sectors 电子 计算机 通信 国防军工 \
  --stock '002371|北方华创|电子' \
  --stock '688012|中微公司|电子'
```

Persistent local settings support 1–8 fixed sectors and 1–20 core stocks. Preserve user order. Exclude BSE, ST/*ST and delisting names. Custom stocks do not change the separately calculated daily mover universe. If the user says `仅本次`, do not save: create a temporary watchlist JSON and pass it to `fetch_sina_cn_market.py --watchlist-config`; delete the temporary file after the report is complete. Never edit Skill source files merely to store one user's preferences.

Apply the same behavior when the user explicitly asks to modify or save their `美股默认关注板块或个股`:

1. Verify each ticker, company/fund name, primary exchange, and TradingView `EXCHANGE:SYMBOL` mapping. Read the current effective config first and preserve any stock or sector group the user did not ask to change.
2. Save 1–20 stocks and 1–20 sector/index ETF proxies with `scripts/manage_us_watchlist.py set`. It writes `~/.goodluck-stock-review/us-watchlist.json`, outside the installed Skill.
3. Confirm with `scripts/manage_us_watchlist.py show`. Future U.S. runs load the saved list automatically. When the user asks to `恢复美股内置默认名单`, run `scripts/manage_us_watchlist.py reset`.
4. Never let a custom list change SPX/NDX, the SPY/QQQ fallback, strict RTH, macro, mover, news, output, or validation behavior.

Example agent-side save command:

```bash
python3 scripts/manage_us_watchlist.py set \
  --stock 'NVDA|NVIDIA|NASDAQ:NVDA' \
  --stock 'AAPL|Apple|NASDAQ:AAPL' \
  --sector 'XLK|科技|AMEX:XLK' \
  --sector 'SMH|半导体|NASDAQ:SMH'
```

For a one-run U.S. override, use a temporary JSON with `fetch_tradingview_rth.py --watchlist-config` plus `--watchlist-part`; do not save it unless the user explicitly says `默认`, `以后`, or `保存`.

## Read the required references

Read these files completely before producing or repairing a report:

1. `references/report-contract.md` — full standing output contract.
2. `references/data-source-policy.md` — date gate, RTH definitions, source hierarchy, missing-data rules, and research boundaries.
3. `references/payload-schema.md` — renderer input fields and supported item shapes.
4. `references/visual-qa.md` — desktop/mobile rendering review and fallback checks.

For an A-share request, also read `references/cn-market-policy.md` completely.

Use the bundled resources rather than recreating them:

- `scripts/resolve_report_date.py` for the preliminary U.S.-date and close-state calculation.
- `scripts/fetch_tradingview_rth.py` for anonymous TradingView regular-session bars.
- `scripts/build_payload_skeleton.py` to turn raw price files into the content payload skeleton.
- `scripts/render_market_review.py` for the standalone HTML and audit JSON.
- `scripts/validate_market_review.py` for price, content, HTML, and self-containment checks.
- `assets/report.css` for the validated report design.

A-share resources:

- `scripts/resolve_cn_report_date.py` for the preliminary China-date and close-state decision.
- `scripts/fetch_sina_cn_market.py` for Sina cash-index, stock, mover, Shenwan-industry, and technology-concept data.
- `scripts/build_cn_payload_skeleton.py` for the A-share payload skeleton.
- The same `scripts/render_market_review.py`, `scripts/validate_market_review.py`, and `assets/report.css` for a market-aware report that preserves the existing U.S. visual system.

## China A-share workflow

1. Run `python3 scripts/resolve_cn_report_date.py`, then verify the candidate date against official SSE and SZSE calendars or closure notices.
   For `closed_cn`, create the qualitative-only payload without a market snapshot:

```bash
python3 scripts/build_cn_payload_skeleton.py \
  --date YYYY-MM-DD \
  --report-type closed_cn \
  --output data/cn_report_payload_YYYY-MM-DD.json
```

2. For a completed trading day, run:

```bash
python3 scripts/fetch_sina_cn_market.py \
  --date YYYY-MM-DD \
  --output data/sina_cn_market_YYYY-MM-DD.json
python3 scripts/build_cn_payload_skeleton.py \
  --date YYYY-MM-DD \
  --input data/sina_cn_market_YYYY-MM-DD.json \
  --output data/cn_report_payload_YYYY-MM-DD.json
```

The fetcher automatically resolves the watchlist in this order: explicit `--watchlist-config` for a one-run override, the user's persistent local file, then the bundled default. The raw snapshot, payload, and audit JSON record the effective sectors, stocks, and configuration source without exposing the user's home path.

3. Complete the narrative/news fields from current, source-backed research. Keep `[事实]` and `[推断]` separate. For historical dates, prefer a saved same-day snapshot. If the current Sina ranking cannot represent the requested date, use sourced historical mover candidates and disclose the coverage gap; never reuse today's rank.
4. Render and validate:

```bash
python3 scripts/render_market_review.py \
  --input data/cn_report_payload_YYYY-MM-DD.json \
  --output cn_market_review_YYYY-MM-DD.html \
  --audit-output data/cn_market_data_YYYY-MM-DD.json
python3 scripts/validate_market_review.py \
  --html cn_market_review_YYYY-MM-DD.html \
  --audit data/cn_market_data_YYYY-MM-DD.json
```

5. Follow `references/visual-qa.md` at desktop and mobile widths. The A-share report must use the same dark-blue hero, KPI cards, numbered sections, tables, inline SVG charts, footer hierarchy, and responsive rules as the U.S. report.

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

Fixed benchmark symbols plus the effective stock watchlist:

- `SP:SPX`, `NASDAQ:NDX` for the preferred benchmark KPI cards and RTH comparison chart
- `AMEX:SPY`, `NASDAQ:QQQ` as the always-fetched fallback pair for the same cards and chart
- the built-in first-run stocks are INTC, NVDA, GOOG, MSFT, AAPL, SKHY, TSM, and the standing candidate SPCX;
- when a user-local list exists, use its verified TradingView mappings instead of the built-in stock list.

Example:

```bash
python3 scripts/fetch_tradingview_rth.py \
  --date YYYY-MM-DD \
  --output data/tradingview_rth_YYYY-MM-DD.json \
  --symbols SPX NDX SPY QQQ \
  --watchlist-part stocks
```

Fetch the effective sector/index ETF proxies separately:

```bash
python3 scripts/fetch_tradingview_rth.py \
  --date YYYY-MM-DD \
  --output data/tradingview_sector_YYYY-MM-DD.json \
  --watchlist-part sectors
```

The U.S. fetcher resolves an explicit one-run config, the user-local config, then the built-in list. It records `us_watchlist` in every raw file. Keep SPX/NDX and SPY/QQQ in the core fetch regardless of the selected stocks or sectors.

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
- Do not alter the U.S. benchmark, RTH, symbol, output, section, or validation behavior when adding or repairing the A-share branch.
- For A shares, use the cash indexes 上证综指、创业板指、科创50; never replace them with ETF proxies.
- Exclude Beijing Stock Exchange securities from A-share movers. Include only Shanghai/Shenzhen main boards, ChiNext, and STAR Market.
- Exclude ST/*ST, delisting-consolidation names, stocks with fewer than 20 observed trading days, and stocks below the default RMB 500 million daily-amount threshold unless the user explicitly changes the filter.
