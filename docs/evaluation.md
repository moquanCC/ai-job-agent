# 评测说明

## 数据

仓库包含 36 条合成岗位与 12 份合成简历，形成 432 个候选人—岗位对，全部在文件中明确作为测试数据使用。岗位覆盖大模型应用、机器学习、数据挖掘、搜索推荐、NLP 和 AI 应用开发六类；候选人覆盖强匹配、相邻方向和跨方向迁移画像，每份简历对岗位都有 0～3 的完整分级相关性标签。

## 指标

- 技能提取：Precision、Recall、F1。
- 排序：Recall@5、Recall@10、MRR、nDCG@5、nDCG@10。
- 工程：本地完整评测运行时间。
- Agent 行为：Task Success Rate、精确工具序列准确率、工具参数有效率、平均工具调用数、不必要调用率和停止原因。

## 方法

`python scripts/run_evaluation.py` 比较五组可复现配置：关键词、语义、关键词+语义、规则融合、完整方法。每组权重、向量后端、汇总指标和逐候选人指标会一并写入 `data/evaluation/results.json`，便于检查平均值是否被少数画像主导。

## 当前结果

扩充后的合成集包含 12 个候选人、36 条岗位和 432 个候选人—岗位对，其中 174 对的标签不低于相关阈值 2。Hashing 基线上，技能提取 Precision 为 1.0、Recall 为 0.8917、F1 为 0.9364；完整方法 Recall@5 为 0.3819、Recall@10 为 0.6875、MRR 为 1.0、nDCG@5 为 1.0。结果文件同时保存逐候选人指标，跨方向、MLOps 等画像能够暴露平均值掩盖的失败模式。

在 CPU 上显式运行 `BAAI/bge-m3` 后，实际后端为 `bge-m3`、向量维度为 1024、无 fallback，12 人五种方法共耗时 151.7369 秒。纯语义 Recall@5 从 Hashing 的 0.3472 降至 0.2546，nDCG@5 从 0.9167 降至 0.7024；完整融合 Recall@10 从 0.6875 升至 0.7014，Recall@5 和 nDCG@5 不变。这组结果不支持“BGE-M3 在扩展合成集上全面更好”的结论。

规则融合和完整方法仍未显著拉开差距。36 条岗位由六类模板在六家公司重复生成，分级标签也来自候选人方向与岗位类型的确定性映射，因此技能重合与标签存在结构性相关。扩充候选人提高了方向覆盖和故障暴露能力，但没有把合成压力实验变成真实招聘效果验证。

## 复现实验

```powershell
python scripts/generate_sample_data.py
python scripts/run_evaluation.py
python scripts/run_evaluation.py --embedding-backend bge-m3 --embedding-device cpu --output data/evaluation/results_bge_m3_extended.json
python scripts/run_agent_evaluation.py --embedding-backend hashing --output data/evaluation/agent_results.json
```

## Agent 行为基准

行为基准使用 18 个合成任务，分别检查完整搜索/过滤/排序、关键偏好缺失时的追问，以及按需解释 Top-1 岗位。固定 Workflow 真实执行过滤和排名，但无法在单个请求内根据状态补做搜索、追问或解释；其任务成功率为 0.6667。受约束 Agent 的任务成功率、工具序列准确率和参数有效率均为 1.0，平均 2.8333 次工具调用，不必要调用率为 0。

这不是排序质量提升实验。结果文件明确记录 `synthetic=true` 和 `human_gold=false`；Agent 的 1.0 只说明预定义合成场景中的编排与停止行为符合期望，不能与 12 人/432 对排序压力实验或 3 人官方 JD 模型辅助裁决实验混报。

## 真实验收建议

1. 使用 3～5 份脱敏真实简历和 30～50 条仍可核验来源的上海校招 JD。
2. 由至少两名标注者独立给出 0～3 相关性，记录分歧与裁决。
3. 冻结数据版本、权重、Embedding 模型和运行环境。
4. 同时报告均值、逐简历结果、延迟、失败率和 API 成本。
5. 达到交接阈值前，重点分析错误类型而不是调参追逐单一指标。
