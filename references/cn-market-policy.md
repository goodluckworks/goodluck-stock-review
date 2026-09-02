# China A-share report policy

Read this reference only for A-share requests. It adds a China branch without changing the standing U.S. report workflow.

## 1. Date, session, and output

- Use `Asia/Shanghai` for the evaluated calendar date.
- Confirm the trading day against official Shanghai and Shenzhen Stock Exchange calendars or closure notices.
- Full-session data covers Beijing time 09:30–11:30 and 13:00–15:00. Do not insert synthetic lunch-break bars; charts must break the line across the midday gap.
- Use `full_cn` for a completed trading session and `closed_cn` for weekends, exchange holidays, or an incomplete session.
- On `closed_cn`, show exactly `今日A股休市，无需生成完整A股复盘` and omit same-day index, stock, mover, and sector tables/charts.
- Save `cn_market_review_YYYY-MM-DD.html`, `data/cn_market_data_YYYY-MM-DD.json`, and the raw same-day Sina snapshot. Keep U.S. filenames unchanged.

## 2. Core indexes

Use cash indexes only:

| Report label | Sina symbol | Role |
|---|---|---|
| 上证综指 | `sh000001` | Shanghai broad-market benchmark |
| 创业板指 | `sz399006` | ChiNext growth benchmark |
| 科创50 | `sh000688` | STAR Market large-cap technology benchmark |

The three KPI cards, section-03 table, overview, and normalized intraday chart must use the same rows. Do not use ETF proxies.

## 3. Market universe and mover filters

The A-share mover universe contains only:

- Shanghai/Shenzhen main boards;
- ChiNext;
- STAR Market.

Always exclude:

- Beijing Stock Exchange symbols;
- ST and *ST names;
- delisting-consolidation or names visibly marked for delisting;
- securities with fewer than 20 observed trading days before and including the target date;
- securities with target-date turnover amount below RMB 500 million.

The 20-day and RMB 500 million defaults are configurable only when the user asks. Select five qualified gainers and five qualified losers when data supports the count. Preserve the filter values and observed listing-day count in the audit JSON.

Sina's current ranking has no reliable target-date field. Use it only when the requested date matches the latest cash-index K-line date. For historical backfills:

1. use a previously saved same-day raw snapshot when available;
2. otherwise identify mover candidates from source-backed historical market reviews and fetch their target-date daily/K-line data;
3. if neither is available, leave the mover section explicitly incomplete rather than reusing a later ranking.

## 4. Industry and technology structure

Use the Sina endpoint labeled as Shenwan industry classification. Display its percentage as `新浪接口标示的申万行业涨跌幅`; do not describe it as an exchange-certified or licensed official Shenwan index return.

Every completed current-day report includes:

- fixed industries from the effective watchlist; the built-in first-run default is 电子、计算机、通信、传媒;
- the five strongest and five weakest Shenwan level-one industries;
- up to five technology concepts with the largest absolute daily moves, prioritizing AI, semiconductors, chips, computing power, robots, servers, storage, optical communications, cloud/software/data, HarmonyOS, consumer electronics, PCB, advanced packaging, machine vision, IoT, quantum, and low-altitude-economy concepts.

Keep sector facts and explanatory inference separate. A price move alone does not prove the catalyst.

## 5. Built-in default and user-local watchlist

The built-in default list was selected from the 2026-08-28 Sina Shenwan-industry market-cap snapshot and the preceding 60 observed trading days. Selection favored positive 60-day performance and larger market capitalization within the relevant industry, capped at three names per Shenwan level-one industry. This is a monitoring list, not investment advice.

| Sina symbol | Company | Shenwan level-one industry |
|---|---|---|
| `sz002371` | 北方华创 | 电子 |
| `sh688012` | 中微公司 | 电子 |
| `sh688347` | 华虹宏力 | 电子 |
| `sz002415` | 海康威视 | 计算机 |
| `sz000938` | 紫光股份 | 计算机 |
| `sz000977` | 浪潮信息 | 计算机 |
| `sh601728` | 中国电信 | 通信 |
| `sz301165` | 锐捷网络 | 通信 |
| `sz002558` | 巨人网络 | 传媒 |
| `sz002517` | 恺英网络 | 传媒 |

Users may replace the fixed sectors and core stocks through a persistent local file at `~/.goodluck-stock-review/cn-watchlist.json`. The bundled list remains unchanged as the fallback and is restored by removing the local override. Reinstalling the Skill must not overwrite the local file.

Resolution order is: explicit one-run file passed with `--watchlist-config`, user-local override, then built-in default. The effective configuration must be copied into the raw snapshot, report payload, and audit JSON with source `explicit_file`, `local_override`, or `builtin_default`; do not expose the absolute home path in shareable artifacts.

Local settings allow 1–8 fixed sectors and 1–20 core stocks. Preserve the user's order. Stock codes must resolve to Shanghai/Shenzhen main board, ChiNext, or STAR Market symbols; reject Beijing, ST/*ST, delisting, duplicate, malformed, or unavailable names. Verify code, company name, and sector before saving. A custom stock may belong to a sector outside the fixed-sector table. Do not enforce the built-in three-per-industry balancing rule on an explicit user selection.

Recheck the built-in list's 60-day direction, sector classification, market capitalization, listing status, and data availability at least quarterly or whenever the user asks for a refresh. A stock failing a later trend check may remain visible only if the report labels the list as the standing default rather than claiming it is still rising.

## 6. Source hierarchy and evidence boundaries

1. SSE/SZSE official sources for trading calendars, rules, exchange notices, and listed-company announcements.
2. Company announcements and investor-relations sources for company-specific facts.
3. Sina public endpoints for index/stock K-lines, current mover ranking, and sector/concept snapshots.
4. Reputable reporting for market context, with original source/time/link retained per item.

Treat Sina as a public aggregated source without a published interface SLA. The quote/ranking/sector interfaces can change, and a request can return the previous trading day's data before the next session. Verify every returned date against the requested report date. Preserve source, retrieval time, endpoint status, filter settings, and gaps in the audit file.

## 7. Report structure and visuals

Reuse the existing U.S. visual system and the same section order:

1. 一句话市场总览;
2. 核心 KPI;
3. 上证综指 / 创业板指 / 科创50 日内走势分析;
4. 核心科技龙头股表现（使用自定义名单时显示为核心关注个股表现）;
5. 当日大幅波动股票;
6. 申万行业与科技板块结构（使用自定义板块时显示为申万行业与关注板块结构）;
7. 影响A股的关键新闻;
8. 过去24小时国际新闻;
9. 重要人物发言与言论;
10. 下一交易日关注;
11. 数据来源与说明.

Keep five full-session visual slots: three-index normalized intraday line, core-leader normalized line, core-leader daily-move bars, mover daily-move bars, and international-news impact chart. The hero, disclaimer, cards, typography, colors, inline SVG, responsive behavior, and quiet footer must match the U.S. version.
