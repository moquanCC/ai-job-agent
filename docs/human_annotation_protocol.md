# 真人标注与生产晋级协议

## 当前状态

真人评测 readiness 闭环已经搭建完成，但真人工作尚未开始。当前所有工作簿均为空白模板，必须保持以下披露：

```text
human_gold=false
status=template_not_completed
```

因此当前项目没有真人金标准，不能据此声称已通过真人验证、可以正式上线或适合真实招聘决策。

已冻结的数据集包含 30 个明确标注为 `synthetic=true` 的合成候选人，覆盖 11 个方向：LLM/RAG、NLP、计算机视觉、多模态、推荐、数据挖掘、搜索/广告、AI Infra、Agent、自动驾驶和 AI 测试。每位候选人对应 25 条 eligible 官方公开 JD，共 750 个唯一 pair；按候选人冻结为 18 train、6 validation、6 blind test，避免同一候选人跨集合泄漏。manifest 与 SHA-256 fingerprint 位于 `data/human_gold/split_manifest.json`。

## 角色、盲标与利益冲突

- 标注者 A 与 B 必须是两个不同的真人，独立完成全部 750 条任务；二者不能查看对方的等级、理由或完成进度。
- 第三位真人只负责裁决 A/B 的分歧，身份必须与 A、B 均不同。裁决表在 A/B 通过完整性校验后才能填入双方等级。
- 三人开始前应声明与候选人画像、岗位公司和项目团队是否存在利益冲突。存在可能影响判断的直接关系时，应更换标注者或把冲突写入审计记录。
- 标注者不得查看系统排名、匹配分、现有双模型标签或调优结果。只能依据合成候选人证据和公开 JD 要求判断。
- blind-test 候选人身份及其指标在权重方案冻结前不得用于调参或选择方案。

## 0–3 级标尺

| 等级 | 定义 |
|---:|---|
| 0 | 岗位核心方向无关，或存在明确且不可忽略的资格冲突。 |
| 1 | 仅有 Python、Git 等通用能力重合，缺少岗位核心方向证据。 |
| 2 | 主方向相关，但缺少关键子技能、直接项目或足够证据。 |
| 3 | 方向直接匹配，多数核心要求有明确项目、研究或实习证据支持。 |

每一条必须填写 grade、非空 rationale 和 confidence。只使用画像中已经存在的证据，不得把“可能学会”当作已经掌握，也不得依据候选人的潜在能力补全经历。

## 工作簿填写流程

模板路径：

- `outputs/human_gold/annotator_A.xlsx`
- `outputs/human_gold/annotator_B.xlsx`
- `outputs/human_gold/adjudicator.xlsx`

每份工作簿包含 Instructions、Candidates、Tasks 和 QC 四个 sheet。先阅读 Instructions，再在 Tasks 填写；QC 必须显示完成，无空白、非法等级或公式错误。A/B 工作簿的任务相同但顺序独立打乱，不包含另一人的答案。

完成后，在 Excel 中仅将 **Tasks sheet 另存为 CSV UTF-8**。不要把整个工作簿或其他 sheet 拼进 CSV。示例文件名为 `annotator_A_tasks.csv`、`annotator_B_tasks.csv` 和 `adjudicator_tasks.csv`。

分别导入 A/B：

```powershell
python scripts/import_human_annotations.py `
  --tasks data/human_gold/annotation_tasks.json `
  --manifest data/human_gold/split_manifest.json `
  --input outputs/human_gold/annotator_A_tasks.csv `
  --role A --annotator-id HUMAN_A --completed-at 2026-08-12T12:00:00+08:00 `
  --output outputs/human_gold/annotator_A.validated.json

python scripts/import_human_annotations.py `
  --tasks data/human_gold/annotation_tasks.json `
  --manifest data/human_gold/split_manifest.json `
  --input outputs/human_gold/annotator_B_tasks.csv `
  --role B --annotator-id HUMAN_B --completed-at 2026-08-12T12:00:00+08:00 `
  --output outputs/human_gold/annotator_B.validated.json
```

导入器会拒绝空白等级、0–3 以外的等级、空理由、重复或缺失 pair、指纹不匹配和身份/角色错误。A/B 全部通过后，把分歧交给第三人填写 adjudicator 的 Final Grade 与裁决理由，再构建 gold：

```powershell
python scripts/build_human_gold.py `
  --tasks data/human_gold/annotation_tasks.json `
  --manifest data/human_gold/split_manifest.json `
  --annotator-a outputs/human_gold/annotator_A.validated.json `
  --annotator-b outputs/human_gold/annotator_B.validated.json `
  --adjudication outputs/human_gold/adjudicator_tasks.csv `
  --adjudicator-id HUMAN_C --completed-at 2026-08-12T18:00:00+08:00 `
  --output outputs/human_gold/human_gold.json
```

只有 A/B 750 条均完成、身份不同、fingerprint 一致，且第三人裁决每一条分歧后，构建器才会输出 `human_gold=true`。

最终 gold 会直接携带 gate 所需的 status、30/750 计数、冻结 split/fingerprint 和 A/B agreement，不需要人工复制这些字段。随后运行真实闭环评测：

```powershell
python scripts/run_human_gold_evaluation.py `
  --human-gold outputs/human_gold/human_gold.json `
  --embedding-backend bge-m3 `
  --embedding-model BAAI/bge-m3 `
  --step 0.05 `
  --output outputs/human_gold/blind_evaluation.json
```

该脚本先在 18 个 train 候选人上形成权重短名单，再用 6 个 validation 候选人选定唯一方案；6 个 blind-test 候选人在选择完成后只评测一次，不参与短名单、tie-break 或方案选择。输出会保留 train/validation/blind candidate IDs、split fingerprint、所选权重和 blind baseline/candidate 指标，供下一步 gate 审计。

## Production promotion gate

Gate 只读 status、blind evaluation 和 engineering audit JSON，不写 `configs/scoring.yaml`：

```powershell
python scripts/check_production_promotion.py `
  --status outputs/human_gold/human_gold.json `
  --evaluation outputs/human_gold/blind_evaluation.json `
  --audit outputs/human_gold/engineering_audit.json `
  --output outputs/human_gold/promotion_gate.json
```

必须同时满足：

- `human_gold=true`，30 个完整候选人、750 个 pair；
- split fingerprint 完全一致，18/6/6 且无候选人泄漏；
- exact agreement ≥ 0.70；
- quadratic weighted κ ≥ 0.60；
- 冻结 blind test 的 nDCG@5 gain ≥ 0.02；
- blind Recall@5 不下降；
- blind Recall@10 下降不超过 0.01；
- 至少 70% 候选人的 nDCG@5 不下降；
- engineering audit 明确 `passed=true`。

任何缺文件、空文件、空白模板、readiness 状态或阈值失败都会返回 machine-readable failure codes 并拒绝晋级。即使所有 gate 条件通过，脚本仍不会自动改配置；还需显式人工配置审查、批准和受控发布。

当前工作簿为空白，因此尚未运行 `run_human_gold_evaluation.py`，也没有可供 gate 通过的 blind evaluation。不可使用模型辅助标签替代这一输入。

## QA 记录

三份模板共 12 个 sheet 已完成公式扫描和视觉检查，公式错误为 0；裁决工作簿 QC 中曾发现的公式/计数 bug 已修复并重新验证。该 QA 证明模板可用，不证明真人标注已完成。
