# 真实公开 JD 双模型标注与评测

核验与标注日期：2026-08-12

## 数据与盲标设计

- 30 条企业官方公开 JD，覆盖百度、上海人工智能实验室和哔哩哔哩；
- 3 个匿名合成候选人画像，共 90 个候选人—岗位对；
- 第一标注者为 `codex-rule-assisted-v1`，属于关键词规则辅助初标；
- 第二标注者为 `independent-expert-model-v1`，只读取候选人画像、JD 和标注协议，未读取首标；
- 标签为 0～3 有序等级，最终由 `adjudicated-model-panel-v1` 逐条处理分歧。

这是一套可复现的**双模型裁决基准**，不是两位真人专家形成的人类金标准。它适合黑客松内部实验和迭代，但论文、招聘决策或对外效果声明前仍需真人复标。

## 标注者一致性

| 指标 | 结果 |
|---|---:|
| 精确一致率 | 47.78% |
| 相差不超过一级 | 91.11% |
| 平均绝对等级差 | 0.6222 |
| 线性加权 Cohen's κ | 0.3135 |
| 二次加权 Cohen's κ | 0.3751 |
| Spearman ρ | 0.4085 |
| 分歧项 | 47 / 90 |
| 跨两级以上严重分歧 | 8 / 90 |

一致性偏低到一般，不能跳过裁决直接使用。严重分歧主要来自初始关键词规则未识别部分“大语言模型/智能体”岗位语义；第二标注者对候选人证据与岗位核心要求进行了更细的逐项比较。

## 裁决规则与结果

统一标尺：仅有通用工具重合记 1；同一主方向但缺关键子技能记 2；有直接项目证据且覆盖多数核心要求才记 3。43 条一致项直接保留，47 条分歧全部裁决：45 条采用独立复标，2 条由裁决者降级。最终标签分布为 0级 10 条、1级 45 条、2级 33 条、3级 2 条。

原始初标、独立复标、分歧清单和最终裁决标签全部分别保存，不覆盖历史结果。最终裁决文件还保存 `first_grade`、`second_grade` 和 `decision`，可追踪每一条结论。

## 正式实验口径

真实评测只使用 27 条 `active` 岗位，排除 2 条 `expired` 和 1 条 `unknown`。相关阈值为等级 ≥2。运行：

```powershell
python scripts/evaluate_annotation_agreement.py
python scripts/adjudicate_relevance_labels.py
python scripts/run_real_evaluation.py --embedding-backend hashing
python scripts/run_real_evaluation.py --embedding-backend bge-m3 --embedding-model BAAI/bge-m3 --output data/real_jobs/evaluation_results_bge_m3.json
```

指标结果保存在 `data/real_jobs/evaluation_results.json`。由于候选人画像只有 3 个且为合成画像，结果应描述为“真实 JD 上的模型辅助裁决实验”，不能泛化为真实求职成功率。

## BGE-M3 实测与对照

可选依赖通过 `pip install -e ".[embedding]"` 安装。此次在 CPU 上显式运行官方模型 `BAAI/bge-m3`，耗时 64.7194 秒；实际后端为 `bge-m3`，无 fallback。输出为 1024 维、`float32`、L2 归一化的 dense 向量。BGE-M3 也支持 sparse 和 multi-vector 检索，但本实验未使用这两类能力。

| 方法 / 指标 | hashing | BGE-M3 | 观察 |
|---|---:|---:|---|
| semantic Recall@5 | 0.1373 | 0.4314 | 短列表召回提高 |
| semantic nDCG@5 | 0.5436 | 0.6451 | 短列表排序提高 |
| semantic Recall@10 | 0.6275 | 0.5294 | 下降 |
| full nDCG@5 | 0.6962 | 0.6940 | 基本持平，略降 |

结果不支持“BGE-M3 全面优于 hashing”的结论。它改善了本小样本上的部分纯语义 Top-5 指标，但 Top-10 召回下降，完整融合的 nDCG@5 也没有提高；此外 CPU 运行时间显著更长。仓库保留 hashing 基线与 BGE 输出，评测 JSON 同时记录 requested/actual backend、模型、维度、批大小、最大长度和 fallback 状态，避免把 hashing 结果误称为 BGE 结果。

首次运行会下载模型到 Hugging Face 缓存。Windows 未启用开发者模式或缺少 symlink 权限时可能出现缓存警告，通常不影响正确性但可能增加磁盘占用。GitHub Actions 始终显式使用 hashing，不触发 BGE 下载。

最重要的效度限制不因换用 BGE-M3 而消失：3 个候选人画像仍为合成数据，相关性仍是双模型独立盲标与裁决形成的模型辅助基准，`human_gold=false`，并非真人金标准。
