# Standing report contract

This file is the complete durable contract for the user's recurring Chinese U.S. post-close report. Apply it to fresh runs, repairs, and backfills. The U.S. contract below is unchanged. For A-share requests, apply the additive market-specific contract in `cn-market-policy.md` while preserving the same visual system and evidence standards.

## 1. Execution time and report-date decision

- The automation normally runs after U.S. RTH, around 09:00 China Standard Time.
- Determine the U.S. Eastern calendar date first. Never use the local computer date blindly.
- Verify whether that U.S. date is a normal NYSE/Nasdaq trading day and whether the full RTH session has completed.
- If it is a weekend, exchange holiday, early-close/incomplete session not yet complete, or otherwise lacks a completed cash session, do not generate a full recap.
- On that branch, generate only source-backed U.S.-market news, global news, important-person items, and next-session watch items. Show `今日美股休市，无需生成完整美股复盘`.
- The report filename/title date is the evaluated U.S. date. A weekend report remains dated that weekend day and must label prior-session figures as background rather than same-day RTH.

## 2. Output artifact

- Output one standalone HTML file named `market_review_YYYY-MM-DD.html`.
- Resolve the output folder in this order: the folder explicitly supplied by the user or automation; the current daily-report workspace; otherwise the current user's portable fallback below.

```text
~/Desktop/美股每日总结
```

- Create the folder when missing.
- Save an accompanying audit JSON at `data/market_data_YYYY-MM-DD.json` and retain the raw market JSON files.
- Use inline CSS. Use inline SVG or embedded base64 images. Do not require external JS, CSS, images, fonts, or chart libraries.
- Page language is Chinese.
- Exact title: `美股每日盘后回顾 — YYYY年M月D日（星期X）`.
- The HTML must open and remain complete without network access. Links to evidence may open externally, but presentation cannot depend on them.

## 3. Design and layout

Use a professional research-daily visual system:

- moderate page width suitable for browser and email reading;
- clear Chinese typography and hierarchy;
- dark/blue hero, light cards, subtle borders/shadows;
- green for positive, red for negative, gray/blue for neutral;
- title, subtitle, and the exact disclaimer at the top;
- answer-first overview, KPI cards, section headers, tables, charts, news cards, source labels, and a quiet footer containing data notes and sources;
- responsive layout for desktop and narrow/mobile screens;
- tables use contained horizontal scrolling on narrow screens;
- print-friendly rules;
- no decorative image clutter.

Charts must be clean and legible, with title, axis/units, method/source caption, and necessary notes. Do not fill a chart slot with invented or interpolated data.

## 4. Asset coverage and RTH scope

Strict RTH is U.S. Eastern 09:30–16:00.

Cash-index benchmarks for core KPI cards:

- S&P 500 cash index (`SPX`).
- Nasdaq-100 cash index (`NDX`).
- The same resolved rows drive both the KPI cards and section-03 RTH comparison.
- If a cash-index series is unavailable, use its matching `SPY` or `QQQ` fallback and disclose `SPY ETF代理` or `QQQ ETF代理` in the basis line and chart/table caption. Keep the card titles short as `标普500` and `纳斯达克100`. Do not mix Nasdaq Composite/IXIC with Nasdaq-100/QQQ.

Optional index futures data, when independently useful and available:

- ES — E-mini S&P 500 futures.
- NQ — E-mini Nasdaq 100 futures.

Built-in first-run standing stocks:

- INTC
- NVDA
- GOOG
- MSFT
- AAPL
- SKHY
- TSM
- SPCX as `NASDAQ:SPCX` only when the public series resolves.

The user may replace the standing stocks and sector ETF proxies with a persistent local default. Use the saved order, while SPX/NDX, SPY/QQQ fallback, RTH boundaries, macro assets, movers, and news rules remain fixed. A user-local list supports 1–20 verified stocks and 1–20 verified sector/index ETF proxies and is not investment advice.

Optional/conditional assets:

- SPY, QQQ, DIA, IWM;
- VIX, U.S. 10-year yield, DXY;
- WTI crude, gold;
- sector ETFs and other assets with clear same-day relevance.

Use `AAPL`, never an incorrect ticker spelling. Verify every nonstandard mapping each run.

## 5. Market-data requirements

- Use real, auditable market data.
- Prefer one-minute or five-minute RTH data. Use 15-minute data only when finer data is unavailable and disclose the downgrade.
- For every focus asset, provide when available:
  - RTH open;
  - RTH high;
  - RTH low;
  - RTH close/last regular-session bar;
  - RTH absolute change;
  - RTH percent change;
  - previous-regular-close-to-close change as a separate field;
  - RTH volume or a visible `未提供`;
  - bar count and first/last Eastern timestamp;
  - concise intraday description.
- If ES/NQ are collected for supplementary research, clip them to the corresponding 09:30–16:00 ET window. Never substitute the full 24-hour futures session. The shareable report's required chart must not depend on them.
- Stocks must exclude premarket and after-hours.
- Identify gaps, delays, aggregation status, continuous-contract differences, and source-definition differences in `数据说明`.
- Preserve a 15:55 stock/ETF final five-minute bar as the final available regular-session bar and disclose the distinction from an exchange-certified close.

## 6. U.S.-market news

Select 5–8 important items when evidence supports the count. Cover as relevant:

- Federal Reserve, rates, inflation, employment, fiscal policy;
- U.S. economic data;
- large technology, semiconductors, AI, cloud, consumer electronics;
- earnings, guidance, rating changes, M&A, regulation, investigations;
- energy, geopolitics, dollar, Treasury yields;
- events affecting ES/NQ or focus stocks.

Each item must include:

- event/title;
- source name and publication/update time;
- direct link;
- affected assets;
- observed market reaction;
- cautious logic chain;
- fact/inference separation.

Do not overstate causality. Use conditional research language for uncertain effects.

## 7. International news from the past 24 hours

Select 6–10 important global events, prioritized by macro, geopolitical, trade, energy, technology, public-safety, or international-relations significance.

Each item must include:

- title;
- region;
- source name/time and direct link;
- event summary;
- why it matters;
- possible impact;
- development status when ongoing;
- a qualitative impact score/category used only for the embedded comparison chart.

The 24-hour boundary is strict. An older event needs a material current update to qualify.

## 8. Large-move stocks

Screen 8–15 stocks when verifiable, drawing from S&P 500, Nasdaq 100, active large caps, or clearly news-driven names.

Prioritize:

- large absolute close-to-close moves;
- abnormal activity when volume evidence exists;
- clear earnings, M&A, regulatory, rating, industry, macro, or technical drivers;
- market relevance.

Each row must include ticker, company, close/last RTH bar, day move, RTH move, driver, category, source, and concise commentary. Sort by absolute day move or market impact. Explain the most important 3–5 names in the driver/comment field.

If a candidate has no complete price series, retry it separately. Exclude unresolved names from quantitative charts/tables and disclose the omission. Never turn a headline into an invented price.

## 9. Full-report section order

### Top

- Exact title.
- Subtitle: RTH trend, focus futures/stocks, movers, U.S. news, global news.
- Show the exact disclaimer below the subtitle in the hero. Do not show generation time, report branch, data-boundary, or tracked-symbol metadata in the hero.
- Exact disclaimer: `本报告仅用于个人市场复盘与研究，不构成任何投资建议。市场数据可能存在延迟或口径差异，请以交易所、经纪商及官方公告为准。`

### 01. One-sentence market overview

Start with one concise, bold sentence that summarizes the verified market structure. When sector proxy data is available, name the strongest rising groups and weakest falling groups before the broad index direction. Do not infer sector leadership without supporting data.

Follow with 3–5 Chinese sentences covering:

- major index direction;
- style characteristics;
- leading/lagging themes;
- core variables;
- change in risk sentiment.

When the overview cites the two primary benchmark moves, use the same resolved S&P 500 and Nasdaq-100 rows as sections 02–03. Do not call NDX/QQQ `纳斯达克综合指数`.

### 02. Core KPI cards

Lead with the verified close-to-close day moves for the S&P 500 and Nasdaq-100 cash indexes. If cash-index data is unavailable, use the matching verified SPY/QQQ close-to-close moves. Always title the cards `标普500` and `纳斯达克100`; disclose `SPY ETF代理` or `QQQ ETF代理` only in the smaller basis line. Do not use ES/NQ or IXIC in the KPI cards. Follow with NVDA, MSFT, GOOG, AAPL, INTC, and optionally SKHY, TSM, SPCX, VIX, or U.S. 10-year yield only when their displayed values are verified. Do not render `未核验` KPI cards.

### 03. S&P 500/Nasdaq-100 RTH analysis

- Use the same resolved SPX/NDX or SPY/QQQ rows as the KPI cards.
- Show an OHLC/change/volume/bar-count table that makes any ETF proxy ticker visible.
- Show a two-series normalized RTH line chart; ES/NQ availability must not control this slot.
- Describe morning, midday, close, relative strength, and cautious interpretation.

### 04. Focus stocks

- table for all effective standing stocks with verified data;
- RTH percent bar chart;
- normalized intraday chart for INTC, NVDA, GOOG, MSFT, AAPL under the built-in list, or the first five saved stocks under a user-local list;
- individual concise comments.

### 05. Large-move stocks

- 8–15-row table when evidence permits;
- close-to-close percent bar chart;
- source-backed drivers and categories.

### 06. Sector and market structure

When data exists, cover technology, semiconductors, financials, energy, health care, consumer, industrials, small caps, and defensive groups. State whether growth/value, large/small, cyclical/defensive leadership is supported by the proxy data.

### 07. Key U.S.-market news

5–8 sourced items with event, reaction, affected assets, and logic chain.

### 08. Past-24-hour international news

6–10 sourced items plus an embedded qualitative impact chart.

### 09. Important-person statements and discussion

5–10 entries when evidence supports them. Candidate people include Jensen Huang, Elon Musk, Tim Cook, large-company leaders, and prominent policymakers such as the U.S. president.

Each entry needs the person's name, time, platform, a short original quote or labeled paraphrase, context, and source. A role/title is optional and may appear only when the cited original source explicitly states it; retain the source wording in `title_source_text`. If that evidence is absent, display only the name. Do not collect or display popular-comment samples, comment rankings, engagement counts, or absence disclosures about comments.

### 10. Next trading day watch

Cover only source-confirmed items:

- economic data;
- Federal Reserve speakers/events;
- earnings;
- option expiration/special market mechanics;
- geopolitical events;
- observed technical boundaries.

Write `暂无可靠来源确认` when exact schedule evidence is unavailable.

### Footer

- a low-emphasis `数据说明、来源与时效` subsection containing the RTH definition, source list, frequency, delay/missing coverage, chart-data status, and explicit data gaps;
- market-data sources;
- news sources;
- generated time;
- audit JSON location;
- no repeated disclaimer.

## 10. Required visual slots

Full RTH report:

1. S&P 500/Nasdaq-100 normalized RTH line using SPX/NDX or the disclosed SPY/QQQ fallback;
2. INTC/NVDA/GOOG/MSFT/AAPL normalized RTH line;
3. focus-stock RTH percent bars;
4. mover close-to-close percent bars;
5. international-news impact classification/timeline.

Closed/incomplete report:

- one qualitative international-news impact visual;
- no same-day RTH line/bar visuals.

If a required full-report visual lacks sufficient real data, preserve the slot with `该图因数据不足未生成` and disclose the exact gap.

## 11. Analysis language

Do more than list data. Address:

- why the market rose/fell without false precision;
- whether the S&P 500 or Nasdaq-100 benchmark was stronger;
- internal technology dispersion;
- semiconductor, AI, cloud, and consumer-electronics themes;
- whether stock moves were fundamental, news, earnings, regulatory, macro, or technical;
- short-term sentiment versus medium/long-term fundamentals.

Use `不确定`, `尚未得到可靠证实`, `可能影响`, and `市场倾向于解读为`. Avoid `显然`, `必然`, or `一定会`. Do not give buy/sell/position advice.

## 12. Final quality gate and handoff

Before completion, verify:

1. U.S. report date and weekday are correct.
2. `AAPL` is present and no incorrect ticker spelling is visible.
3. Every number, news item, quote, displayed person title, and schedule has a source chain or explicit gap.
4. RTH is separated from premarket/after-hours/24-hour futures.
5. The section-03 comparison contains two real RTH benchmark series and does not depend on ES/NQ.
6. Charts use real data or an explicit missing-data placeholder.
7. HTML is self-contained and parses successfully.
8. Chinese typography and tables are visually aligned.
9. Desktop and narrow/mobile preview have no clipping/overlap.
10. HTML and audit JSON are saved in the required folder.
11. Audit JSON includes report type, counts, raw files, checksum, and caveats.
12. The automation-memory record contains artifact paths, report type, QA result, and gaps but not transient market opinion.

Return a concise handoff with success, absolute HTML path, U.S. report date/branch, main sources, missing/manual-review items, and static/visual QA status. Never return only the report text without saving the file.
