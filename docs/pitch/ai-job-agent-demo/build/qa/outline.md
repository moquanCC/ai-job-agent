# Deck Outline

- File: C:\Users\cc\Desktop\黑客松项目\docs\pitch\ai-job-agent-demo\build\ai.pptx
- Slides: 8

## Slide 1: (No title)

Body:
- 秋招雷达 AI
- 可解释的上海 AI 校招岗位匹配与简历优化 Agent
- Explainable · Grounded · Reproducible

## Slide 2: (No title)

Body:
- 直接把简历和 JD 发给大模型，还不够
- 真正的求职决策需要稳定规则、证据和可复现实验
- 常见做法
- 一次提示词输出一个总分
- 地点、学历与技能混在语义判断里
- 建议容易越过真实经历边界
- 效果好坏缺少可复现指标
- 我们的设计
- 上海、校招与截止状态先硬过滤
- 六项分数逐项展示并附证据
- 缺失经历只给学习建议
- F1、Recall、MRR、nDCG 统一评测
- 不是让模型替用户决定，而是把决定依据组织得更清楚。
- 2/8

## Slide 3: (No title)

Body:
- 一次上传，贯通求职准备全流程
- 离线可运行；配置模型后可继续增强提取与项目相关性判断
- 解析与确认
- PDF / DOCX / TXT / MD → 教育、技能、项目、证据；用户可人工修正。
- 过滤与排名
- 上海校招硬过滤 → Top-K → 六维分项、命中技能与缺口。
- 行动与训练
- 真实简历建议 → 五类面试题 → Markdown 报告导出。
- Sources: README.md；app.py；src/services/analysis_service.py
- 3/8

## Slide 4: (No title)

Body:
- 六维评分：把硬约束与语义信号分开
- 大模型只能辅助项目相关性，不独立决定最终总分
- 来源：configs/scoring.yaml；src/matching/score_fusion.py
- 4/8

## Slide 5: (No title)

Body:
- 不是拼接 Prompt，而是一套可运行的 MVP
- 所有数字来自当前仓库与 2026-08-12 成功运行记录
- 21/21
- 自动化测试通过
- 单元 + 端到端；本地与 GitHub Actions 一致
- 36
- 合成岗位
- 覆盖 6 类上海 AI / 算法 / 数据岗位
- 4
- 简历格式
- PDF、DOCX、TXT、Markdown
- 5
- 完整页面
- 解析、岗位库、推荐、优化、面试
- Sources: GitHub Actions run 31552427632；仓库测试与评测数据
- 5/8

## Slide 6: (No title)

Body:
- 最重要的产品约束：不替用户编造经历
- 建议必须能追溯到简历证据
- 可直接修改
- 重排已有项目的“问题—行动—结果”
- 前置展示已命中的真实技能
- 只保留原文已经出现的量化指标
- 每条建议展示对应证据片段
- 完成相关工作后才能加入
- 简历没有 FAISS：先完成最小项目验证
- 缺少硬技能：输出学习与实践计划
- 不生成虚假实习、论文或比赛
- 不把建议目标写成既有成果
- 系统优化表达，但不改变事实边界。
- Sources: src/agents/resume_advisor.py；tests/unit/test_agents.py
- 6/8

## Slide 7: (No title)

Body:
- 评测诚实：合成集验证的是管线，不是真实招聘效果
- 36 条合成岗位 · 3 份合成简历 · 5 种方法
- 技能提取 F1=1.0。重复模板与密集相关标签让排序差异不明显；下一步必须换成真实公开 JD 和多人标注。
- Sources: data/evaluation/results.json；docs/evaluation.md
- 7/8

## Slide 8: (No title)

Body:
- 下一步：从稳定 Demo 到可信在线产品
- 按风险递增，不把云服务复杂度提前带进演示主线
- 01
- NOW
- 工程基线
- 私有仓库 · v0.1.0-demo · 绿色 CI
- 02
- NEXT
- 真实评测
- 公开 JD · 多人标注 · BGE-M3 精排
- 03
- LATER
- 云端版本
- Supabase Auth · RLS
- Sources: GitHub Actions run 31552427632；docs/superpowers/plans/2026-08-12-github-ci-and-cloud-roadmap.md
- 8/8
