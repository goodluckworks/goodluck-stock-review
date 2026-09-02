# Visual QA workflow

Visual review is required after deterministic validation.

## Preferred preview path

Browsers may reject local `file://` navigation. Serve only the report directory through a loopback HTTP server:

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory "/absolute/report/folder"
```

Open `http://127.0.0.1:8765/market_review_YYYY-MM-DD.html`. Stop the server after review.

Do not expose the server on `0.0.0.0`. Do not bypass a browser security policy.

## Desktop pass

Review at approximately 1280–1440 px width:

1. Hero title fits without collision and the exact date/weekday is visible.
2. Subtitle and the full disclaimer remain readable against the dark background. The hero does not show generation time, report branch, data-boundary, or tracked-symbol metadata.
3. The report begins with the market overview rather than a standalone data-note card; its bold lead is visually clear and names sector winners/losers when the evidence supports them.
4. KPI cards form a balanced grid; the first two titles are exactly `标普500` and `纳斯达克100`, proxy details appear only in the smaller basis line, and neither ES/NQ placeholders nor `未核验` values appear.
5. Tables align numerically and horizontal overflow is contained within the table wrapper.
6. All five full-report visual slots have readable titles, legends, axes, and source/method captions. Section 03 shows two S&P 500/Nasdaq-100 RTH lines using SPX/NDX or visibly disclosed SPY/QQQ fallbacks; it is not a missing ES/NQ chart and never uses IXIC.
7. Red/green moves remain distinguishable with text signs and are not color-only.
8. Long Chinese news headlines wrap cleanly.
9. Global-news and quote cards have consistent heights and spacing without excessive empty areas. Quote cards contain no popular-comment/sample-boundary block; a person title appears only when the audit item includes source-backed `title` and `title_source_text`, otherwise only the name is shown.
10. URLs/source labels are readable and not raw unbroken strings.
11. Footer data notes, sources, gaps, and generated time are visible but lower-emphasis than body analysis; the disclaimer is not repeated there.
12. Interpretive paragraphs such as benchmark-relative-strength and sector-structure commentary use normal text, not yellow framed callouts.
13. With a user-local U.S. watchlist, section 04 shows every configured stock in saved order, the intraday comparison uses the first five, and section 06 shows every configured sector proxy. The built-in list keeps its existing labels and layout.

## Narrow/mobile pass

Review around 390–430 px width:

1. Page does not produce body-level horizontal scroll.
2. Hero padding and title size are proportional, and the full disclaimer wraps without clipping.
3. KPI cards collapse to one column.
4. Multi-column news, quote, watch, and source layouts collapse to one column.
5. Tables scroll inside their wrappers without clipping surrounding content.
6. SVG labels are not cut off; legends do not overlap lines or bars.
7. Links have enough line height and no card content overlaps.

## Closed-market pass

Confirm the page clearly says `今日美股休市，无需生成完整美股复盘` near the top. It must not visually imply that ES/NQ or stock RTH data exists. Only the global qualitative impact visual should appear.

For `closed_cn`, confirm the page instead says `今日A股休市，无需生成完整A股复盘` and omits same-day index, leader, mover, and sector visuals.

## A-share full-session pass

Use the same desktop and mobile checks as the U.S. report, plus:

1. The title is `A股每日盘后回顾` and the dark-blue hero, disclaimer, KPI cards, numbered sections, typography, spacing, and quiet footer match the U.S. visual system.
2. The first three KPI cards are exactly `上证综指`, `创业板指`, and `科创50`, with no ETF proxy labels.
3. Section 03 contains three real normalized intraday lines and visibly states Beijing time 09:30–11:30 and 13:00–15:00. The line breaks across the lunch gap and no synthetic lunch bars appear.
4. With the built-in list, the ten default leader cards/table rows wrap cleanly and no Shenwan industry contributes more than three names. With a user-local list, all configured cards/rows appear in saved order and remain readable for the supported 1–20 stocks.
5. Section 05 visibly states the restricted market universe and mover filters; no Beijing, ST, delisting, too-new, or below-threshold row appears.
6. Section 06 contains all effective fixed industries (the built-in default is 电子、计算机、通信、传媒), five strongest and five weakest level-one industries, and significant technology concepts without overflowing on narrow screens.
7. A full A-share report has the same five visual slots as the U.S. report, adapted to China-market content.
8. Section 09 follows the same title-evidence and no-public-comments rules as the U.S. report.

## Iteration rules

- Fix layout problems in `assets/report.css` or deterministic renderer markup, then rerender and repeat both passes.
- Fix individual content overflow by improving component rules, not by deleting required evidence.
- If a chart is too dense, reduce tick labels or split lines; never alter or smooth the underlying data.
- Keep source captions and data-gap disclosures after visual simplification.

## Fallback when interactive preview is unavailable

Run the validator and a renderer screenshot if the environment provides one. At minimum, inspect:

- exact title and viewport meta;
- inline CSS present;
- no external stylesheet/script/image dependency;
- expected section and chart-slot counts;
- no unclosed HTML tags according to a parser;
- mobile media queries present;
- full report has five visual slots, closed report has one;
- disclaimer and source links present.

Report the visual status accurately: `browser visual QA passed`, `screenshot visual QA passed`, or `static-only visual QA; browser unavailable`. Do not claim a visual pass that was not performed.
