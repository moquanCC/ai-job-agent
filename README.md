# 秋招雷达 AI：岗位匹配与简历优化 Agent

[![CI](https://github.com/moquanCC/ai-job-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/moquanCC/ai-job-agent/actions/workflows/ci.yml)

面向上海地区 AI、算法、数据挖掘、推荐与数据科学岗位的可解释求职助手。上传简历并导入岗位后，应用会完成结构化解析、上海校招硬过滤、混合评分、技能缺口分析、真实经历约束下的简历建议、岗位定制面试题与 Markdown 报告导出。

> 当前版本不需要 API Key。语义后端支持 `BAAI/bge-m3`、自动回退和完全离线的 hashing 基线；模型下载完成后，推理在本机执行，不会把简历发送到外部推理服务。

![秋招雷达 AI 界面预览](docs/assets/app-preview.svg)

## 功能

- 解析 PDF、DOCX、TXT、Markdown 简历；扫描 PDF 会给出明确提示。
- 导入 CSV/JSON 岗位或粘贴单条 JD，SQLite 自动去重。
- 默认硬过滤上海、校招/应届、AI/算法/数据方向及未截止岗位。
- 按必需技能、加分技能、项目、语义、学历、地点六项评分并给出证据。
- 把建议分成“可直接修改”和“完成相关工作后才能加入”，防止编造经历。
- 生成项目深挖、岗位知识、技能缺口、系统设计和行为面试题。
- 导出完整 Markdown 分析报告，并支持删除个人分析记录。
- 内置 30 条企业官方公开 JD 快照，其中 27 条核验为在招；保留合成数据用于可复现的管线测试。
- 提供真实 JD 实验看板，展示排序方法对比、双模型标注一致性、分歧规模和实验局限。

## 快速开始

要求 Python 3.10+（开发验证环境为 Python 3.13）。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
streamlit run app.py
```

浏览器打开 `http://localhost:8501`，进入“岗位库”并点击“一键加载 30 条官方 JD”。状态看板应显示 30 条岗位，其中在招 27 条、过期 2 条、待确认 1 条；表格中的链接可回溯至官方职位页。随后上传合成文件 `data/evaluation/demo_resume.md`，依次体验 Top-5 推荐、证据约束下的简历优化、岗位面试题与实验看板。演示无需导入合成岗位。

### UI 真实演示流程

1. 在“岗位库”一键加载仓库内已核验的 30 条官方 JD，并检查 `30 / 27 / 2 / 1` 状态统计与官方来源链接。
2. 在“简历解析”上传 `data/evaluation/demo_resume.md`；该候选人资料是合成数据，可安全用于公开演示。
3. 在“岗位推荐”运行 Top-5，查看状态、核验日期、官方来源、六项评分、技能命中与证据。
4. 选中一个岗位，在“简历优化”查看 grounded 建议，在“模拟面试”查看岗位定制题及关联依据。
5. 在“实验看板”比较关键词与规则融合方法，并审计标注一致性、分歧和三项实验限制。

演示的数据口径是：**真实官方公开 JD + 3 个合成候选人画像 + 双模型独立盲标与裁决形成的模型辅助评测基准**。`human_gold=false`，因此这些标签不能表述为真人专家标注或人类金标准。

## Docker 启动

```bash
docker compose up --build
```

打开 `http://localhost:8501`。容器将 `./data` 挂载到本地，分析数据不会随容器重建丢失。

## 项目结构

```text
app.py                         Streamlit 六页工作台
configs/                       技能别名、权重和运行配置
src/parsers/                   四类文件解析与结构化提取
src/matching/                  过滤、规则、语义、融合、排序
src/retrieval/                 离线向量与可持久化索引
src/repositories/              SQLite 岗位和分析记录
src/agents/                    简历建议、面试题、报告
src/evaluation/                F1、Recall、MRR、nDCG
scripts/                       样本、导入、索引和实验脚本
data/evaluation/               明确标注为合成的评测数据与结果
data/real_jobs/                官方公开 JD 与规则辅助相关性初标
tests/                         单元测试与完整流程测试
docs/                          架构、评测和演示材料
```

详细设计见 [系统架构](docs/architecture.md)，合成评测解释见 [评测说明](docs/evaluation.md)，真实 JD 实验口径见 [真实 JD 评测说明](docs/evaluation_real.md)。

## 岗位数据格式

CSV 最低字段：

```csv
job_id,company,title,location,description,source_url,published_at,deadline
```

JSON 是相同字段对象组成的数组。推荐额外提供 `employment_type`、`required_skills`、`preferred_skills`、`education_requirement`、`responsibilities` 和 `status`。无法确认的状态应使用 `unknown`，不要标为正在招聘。

真实数据位于 `data/real_jobs/jobs.json`：30 条均来自企业官方职位详情，覆盖百度、上海人工智能实验室和哔哩哔哩，包含来源证据和 2026-08-12 核验日期。90 个候选人—岗位对已完成独立双模型复标、一致性评估和逐条裁决；它是可复现实验基准，但不是两位真人专家形成的人类金标准。完整口径见 `docs/evaluation_real.md`。

研究文档更新后可重新生成并校验结构化数据：

```powershell
python scripts/compile_real_jobs.py
```

## 匹配评分

```text
Score = 0.30 × 必需技能 + 0.10 × 加分技能 + 0.20 × 项目
      + 0.20 × 语义相似 + 0.10 × 学历 + 0.10 × 地点
```

地点不是上海的岗位会在评分前过滤。每个结果均返回 0～100 分的六个分项、命中/缺失技能、简历证据和建议等级。权重可在 `configs/scoring.yaml` 调整。

## 配置

复制 `.env.example` 为 `.env` 或设置同名环境变量。`LLM_*` 是后续接入 OpenAI 兼容接口的保留项，不会被当前代码调用。

### Embedding 后端

安装可选的 BGE-M3 依赖：

```powershell
pip install -e ".[embedding]"
```

三种后端语义如下：

- `EMBEDDING_BACKEND=bge-m3`：显式使用官方模型 `BAAI/bge-m3`；依赖或模型不可用时直接报错，不静默降级。
- `EMBEDDING_BACKEND=auto`：优先使用 BGE-M3，加载失败时回退到 `local-hashing-v1`，UI 会披露实际后端和 fallback 状态。
- `EMBEDDING_BACKEND=hashing`：固定使用 512 维字符 n-gram hashing，适合离线演示、测试和 CI，不下载模型。

首次使用 BGE-M3 会从 Hugging Face 下载模型并写入本机缓存，耗时和磁盘占用取决于网络与环境。Windows 若未启用开发者模式或管理员权限，Hugging Face 可能提示缓存无法创建 symlink；通常仍可运行，但缓存会占用更多空间。可按需设置 `HF_HOME` 指向有足够空间的目录。`EMBEDDING_DEVICE` 可设为 `cpu` 或可用的加速设备；默认批大小为 8、最大长度为 1024。

## 测试与评测

```powershell
pytest -q
python scripts/run_evaluation.py --embedding-backend hashing
python scripts/run_real_evaluation.py --embedding-backend hashing
python scripts/run_real_evaluation.py --embedding-backend bge-m3 --embedding-model BAAI/bge-m3 --output data/real_jobs/evaluation_results_bge_m3.json
python scripts/build_index.py --backend hashing --db data/app.db --output data/faiss_index
```

GitHub Actions 会在每次推送和 Pull Request 时使用 Python 3.11 执行源码编译、测试、合成数据再生成、双模型一致性与裁决复现、真实 JD 评测和 SQLite 导入冒烟测试，并保留 14 天的评测结果 artifact。CI 显式固定 `--embedding-backend hashing`，不会安装或下载 BGE-M3。

最新仓库内结果由 `data/evaluation/results.json` 给出。合成集用于验证管线和指标实现，不应用于宣称真实招聘效果；真实验收应替换为脱敏简历、真实公开 JD 和人工多标注者相关性标签。

“实验看板”读取 `data/real_jobs/evaluation_results.json` 与一致性报告，展示 30 条官方 JD（27 条在招）、3 个合成候选人画像、排序指标和双模型标注分歧。当前标签是双模型独立盲标后逐条裁决形成的模型辅助基准，`human_gold=false`；它适合黑客松中的可复现实验与流程审计，但不等同于真人专家评测，也不能用于宣称真实招聘效果。

本机 CPU 实测中，`BAAI/bge-m3` 输出 1024 维、`float32`、L2 归一化稠密向量，完整真实 JD 评测耗时 64.7194 秒且没有 fallback。与 hashing 相比，纯语义方法的 Recall@5 从 0.1373 升至 0.4314、nDCG@5 从 0.5436 升至 0.6451，但 Recall@10 从 0.6275 降至 0.5294；完整融合方法的 nDCG@5 从 0.6962 变为 0.6940，基本持平且略降。因此当前结果只证明部分短列表语义指标改善，不代表所有指标或完整系统全面提升。

### 探索性融合权重搜索

在 BGE-M3 分项缓存上，搜索使用 26 个实际通过硬过滤的岗位、3 个合成候选人和 78 个相关性对。最终一致性修复后的 JSON 显示：步长 0.05 的约束网格包含 2050 组权重，产生 208 种唯一排序，另有 1842 组等价并列；三个 LOCO 折出现 2 个不同 winner，说明选择不稳定。探索性 medoid 为 `required=.25 / preferred=.10 / project=.15 / semantic=.35 / education=.15 / location=0`。此前阶段性统计均以 `data/real_jobs/fusion_weight_search_bge_m3.json` 的最终值为准。

描述性全数据指标从 baseline 到 medoid 分别为：Recall@5 `0.4901961 → 0.4901961`、Recall@10 `0.6078431 → 0.5882353`、MRR `0.7777778 → 0.8333333`、nDCG@5 `0.6939607 → 0.7559514`、nDCG@10 `0.7213242 → 0.7426167`。LOCO mean 为 Recall@10 `0.5882353`、nDCG@5 `0.7536770`、nDCG@10 `0.7409596`，三个 held-out 折的 nDCG@5 范围为 `0.6215484–0.8869466`。Recall@10 的下降说明结果不是全面改善。这些数值不能视作独立测试：LOCO 验证的是每折的权重选择流程，而不是汇总后的 medoid；全数据指标又是在同一数据上搜索后得到。

因此 promotion 已拒绝，`configs/scoring.yaml` 保持不变。另一个工程原因是 location 已在排序前硬过滤：搜索时把它设为 0 不影响候选岗位顺序，但若直接部署，会改变绝对匹配分和推荐阈值。未来若有独立真人标注集并允许部署，须恢复 `location=0.10`，再把其余五项按 0.90 缩放。当前 `human_gold=false` 且只有 3 个合成候选人，不足以更新默认权重。

## 隐私与安全

- 完整简历只保存在当前 Streamlit 会话，不写入日志或 SQLite。
- SQLite 仅保存岗位以及匹配/建议摘要，可在侧栏按候选人编号删除。
- API Key 仅允许通过环境变量读取，`.env` 已加入 `.gitignore`。
- 应用不登录招聘网站、不爬取受限内容、不自动投递。
- 缺少经历时只输出学习/项目补充建议，不生成虚假实习、论文、指标或技术。

## 已知限制

- 默认提取器是确定性规则，复杂版式、表格简历和模糊标题可能需要人工修正。
- 扫描 PDF 未集成 OCR；请改用可复制 PDF 或 DOCX。
- hashing 基线的语义泛化能力有限；BGE-M3 首次运行需要下载较大模型，CPU 延迟也显著高于 hashing，并且本次实测并非所有排名指标都提高。
- 当前真实 JD 实验仍使用 3 个合成候选人画像，相关性标签来自双模型裁决而非真人专家；正式招聘效果仍需脱敏真实简历和多人独立人工复标验证。
- 当前为单机 Demo，没有账户、权限、多租户和高并发能力。

## 后续计划

1. 接入带 JSON Schema 的 OpenAI 兼容提取器，并保留证据与最多两次重试。
2. 在现有 BGE-M3 稠密向量接入基础上，评估 FAISS 召回和 Cross-Encoder 精排。
3. 将当前 30 条官方 JD 扩展至 50 条和更多公司，并完成双人独立复标。
4. 增加简历版本对比、回答反馈和岗位截止提醒。

## 演示与项目表达

3～5 分钟演示路径见 [演示脚本](docs/demo_script.md)。项目可用于简历的表述与面试展开点也包含在该文档中。
