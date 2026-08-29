# Goodluck 美股每日盘后回顾

`goodluck-us-market-daily-review` 是一个用于生成、修复和质量检查中文美股盘后复盘的 Codex Skill。它会优先生成独立 HTML 报告，同时保存数据审计 JSON，并对数据口径、来源链接和页面展示进行检查。

## 主要功能

- 生成中文美股每日盘后复盘 HTML。
- 使用美东时间 09:30–16:00 的常规交易时段（RTH）数据。
- 核心指数固定为标普500与纳斯达克100，优先使用 SPX、NDX 现金指数；缺失时仅使用对应的 SPY、QQQ ETF 代理并明确披露。
- 展示重点科技股、市场板块、异动股票、宏观资产、市场新闻和国际要闻。
- 区分已核验事实、分析判断和待核实信息，并为重要内容保留来源链接。
- 生成数据审计文件，并检查报告结构、数据覆盖和图表完整性。
- 支持正常交易日、周末及休市日分支。

## 安装

将仓库克隆到 Codex 的技能目录：

```bash
git clone https://github.com/Simi-art/goodluck-us-market-daily-review.git ~/.codex/skills/goodluck-us-market-daily-review
```

重新打开 Codex 后，即可通过技能名称调用。

## 使用示例

```text
使用 $goodluck-us-market-daily-review 生成最新已完成美股交易日的中文盘后复盘。
```

也可以指定历史交易日：

```text
使用 $goodluck-us-market-daily-review 生成 2026-08-21 的美股每日复盘。
```

技能默认先保存以下文件，再返回文件位置和数据缺口：

- `market_review_YYYY-MM-DD.html`：可独立打开的复盘网页。
- `data/market_data_YYYY-MM-DD.json`：数据审计文件。
- `data/` 下的原始行情与报告输入文件。

## 数据口径

- 常规交易时段统一采用美东时间 09:30–16:00。
- 标普500与纳斯达克100的 KPI 和对比图使用同一组数据口径。
- 优先使用 SPX、NDX；不可用时才回退至 SPY、QQQ，并在报告中标明 ETF 代理。
- 不使用 ES/NQ 全天期货数据替代现金指数，也不将纳斯达克综合指数 IXIC 与纳斯达克100混用。
- 缺失或无法核验的数据会披露，不会通过猜测补齐。

## 目录结构

```text
goodluck-us-market-daily-review/
├── SKILL.md                 # 技能入口与执行要求
├── agents/openai.yaml       # Codex 展示信息与默认调用提示
├── scripts/                 # 数据获取、渲染和校验脚本
├── references/              # 数据政策、报告规范和视觉检查要求
└── assets/                  # 页面样式与技能图标
```

## 注意事项

- 行情和新闻数据可能受到来源可用性、延迟及访问限制影响。
- 使用者应检查报告中的来源、数据说明和未核验项目。
- 本技能及其生成内容仅用于个人市场复盘与研究，不构成任何投资建议。
