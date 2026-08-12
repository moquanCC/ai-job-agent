# 秋招雷达 AI Notes

## Purpose

- Audience:
- Decision / outcome:
- Style preset: `bold-startup-narrative`

## Sources

- Add the datasets, URLs, or reference decks used to author this presentation.
- Record the provenance for every non-user image you stage through `asset_plan.json`.
- Promote researched claims into `evidence_plan.json` before adding them to slides.

## Research log to staging plan

Closes the gap where research produces good content but never turns into
staged visuals. Every row in this table should eventually trigger an
entry in `asset_plan.json` (wikimedia_query for a CC photo, or a staged
icon/chart).

| Fact discovered | Source | Becomes | In asset_plan as |
|---|---|---|---|
| _e.g. Chicago Pile-1, first controlled chain reaction, Dec 2 1942_ | _en.wikipedia.org/Chicago_Pile-1_ | _hero image on slide 3_ | _images[0].wikimedia_query: "Chicago Pile-1"_ |
|  |  |  |  |
|  |  |  |  |

If this table is empty at build time, ask yourself whether the deck
actually has no visual anchors or whether the research hasn't been
connected to the staging plan yet.

## Style Contract

- Slide size: 16:9 unless a reference deck says otherwise
- Title font: 48-36pt range via preset
- Section font: 32-24pt range via preset
- Body font: 22-15pt range via preset
- Margin x: 0.65
- Gutter: 0.3

## QA Notes

- Preserve alignment first.
- Keep subtitles below wrapped titles.
- Prefer local, source-backed assets in `assets/`.
- Use `asset:alias` references in `outline.json` after staging into `assets/staged/`.
- Add any deck-specific measurements here if you later match an existing deck manually.
# 秋招雷达 AI 路演材料说明

- 所有指标来自 `data/evaluation/results.json`，数据集明确为合成。
- CI 证据来自 GitHub Actions run `31552427632`，对应提交 `f546d92`。
- 不使用外部市场数据、岗位数量估算或未经验证的用户反馈。
- 目标讲述时间 3–5 分钟；每页只保留一个核心结论。
- 如果真实评测完成，优先更新第 7 页而不是新增更多功能页。
