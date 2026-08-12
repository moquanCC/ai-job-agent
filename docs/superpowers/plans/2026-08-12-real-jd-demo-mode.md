# Real JD Demo Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 30 条官方公开 JD、27 条在招岗位和真实评测结果接入 Streamlit，让评委无需手工上传 JSON 即可体验并审计真实岗位匹配。

**Architecture:** 在 `AnalysisService` 增加受控的官方数据集导入与评测读取接口，保持 UI 不直接解析仓库 JSON。Streamlit 岗位库提供一键加载、状态统计和官方来源链接，新增“实验看板”页面读取已提交的可复现结果；匹配页显示官方来源和核验日期。所有写入仍只发生在本地 SQLite，不访问招聘网站、不自动投递。

**Tech Stack:** Python 3.11、Streamlit、Pydantic v2、SQLite、pandas、pytest。

## Global Constraints

- 只加载 `data/real_jobs/jobs.json` 中的已核验数据，不发起网络请求。
- 默认推荐仅包含 `status=active` 的上海岗位；`expired` 和 `unknown` 只用于审计展示。
- UI 必须明确写“模型辅助裁决基准”，不得写“真人金标准”。
- 保留用户批量导入和粘贴 JD 的现有能力。
- 不更改现有匹配公式和实验结果。

---

### Task 1: Official Dataset Service Boundary

**Files:**
- Modify: `src/services/analysis_service.py`
- Test: `tests/integration/test_real_dataset_flow.py`

**Interfaces:**
- Consumes: `JobProfile`, `JobRepository.upsert_many()` 和 `data/real_jobs/jobs.json`。
- Produces: `AnalysisService.import_verified_jobs(dataset_path: str | Path | None = None) -> tuple[int, dict[str, int]]`；`AnalysisService.load_real_evaluation(result_path: str | Path | None = None) -> dict`。

- [ ] **Step 1: Write failing service tests**

```python
def test_import_verified_jobs_reports_status_counts(tmp_path):
    service = AnalysisService(db_path=tmp_path / "app.db")
    count, statuses = service.import_verified_jobs(ROOT / "data/real_jobs/jobs.json")
    assert count == 30
    assert statuses == {"active": 27, "expired": 2, "unknown": 1}
    assert service.jobs.count() == 30


def test_load_real_evaluation_preserves_disclosure(tmp_path):
    service = AnalysisService(db_path=tmp_path / "app.db")
    result = service.load_real_evaluation(ROOT / "data/real_jobs/evaluation_results.json")
    assert result["dataset"]["human_gold"] is False
    assert result["dataset"]["active_jobs"] == 27
```

- [ ] **Step 2: Run tests and confirm missing methods**

Run: `pytest tests/integration/test_real_dataset_flow.py -q`

Expected: FAIL because `import_verified_jobs` and `load_real_evaluation` do not exist.

- [ ] **Step 3: Implement strict local loaders**

```python
def import_verified_jobs(self, dataset_path=None):
    path = Path(dataset_path) if dataset_path else ROOT / "data" / "real_jobs" / "jobs.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    jobs = [JobProfile.model_validate(record) for record in records]
    statuses = {status: sum(job.status == status for job in jobs) for status in ("active", "expired", "unknown")}
    return self.jobs.upsert_many(jobs), statuses


def load_real_evaluation(self, result_path=None):
    path = Path(result_path) if result_path else ROOT / "data" / "real_jobs" / "evaluation_results.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("dataset", {}).get("human_gold") is not False:
        raise ValueError("评测披露字段缺失或不合法")
    return result
```

- [ ] **Step 4: Run the focused tests**

Run: `pytest tests/integration/test_real_dataset_flow.py -q`

Expected: 2 passed.

- [ ] **Step 5: Commit the service boundary**

```powershell
git add src/services/analysis_service.py tests/integration/test_real_dataset_flow.py
git commit -m "Add verified dataset service loaders"
```

### Task 2: Official Job Library UX

**Files:**
- Modify: `app.py`
- Test: `tests/unit/test_demo_presenters.py`
- Create: `src/ui/demo_presenters.py`

**Interfaces:**
- Consumes: `AnalysisService.import_verified_jobs()` 和 `list[JobProfile]`。
- Produces: `job_status_summary(jobs: list[JobProfile]) -> dict[str, int]`；`job_table_rows(jobs: list[JobProfile]) -> list[dict]`。

- [ ] **Step 1: Write failing presenter tests**

```python
def test_job_status_summary_and_source_rows():
    jobs = [JobProfile(job_id="j", company="测试", title="算法", location="上海", status="active", source_url="https://example.com", checked_at="2026-08-12")]
    assert job_status_summary(jobs) == {"全部": 1, "在招": 1, "过期": 0, "待确认": 0}
    assert job_table_rows(jobs)[0]["官方来源"] == "https://example.com"
```

- [ ] **Step 2: Run the presenter test and confirm failure**

Run: `pytest tests/unit/test_demo_presenters.py -q`

Expected: FAIL because the presenter module does not exist.

- [ ] **Step 3: Implement pure presentation helpers**

```python
def job_status_summary(jobs):
    return {
        "全部": len(jobs),
        "在招": sum(job.status == "active" for job in jobs),
        "过期": sum(job.status == "expired" for job in jobs),
        "待确认": sum(job.status == "unknown" for job in jobs),
    }


def job_table_rows(jobs):
    return [{"公司": job.company, "岗位": job.title, "地点": job.location, "状态": job.status, "核验日期": job.checked_at or job.last_checked_at, "官方来源": job.source_url} for job in jobs]
```

- [ ] **Step 4: Add the verified dataset controls to `page_jobs`**

Add an “一键加载 30 条官方 JD” button that calls `api.import_verified_jobs()`, renders four status metrics, adds company/status filters, and displays `st.link_button("打开官方职位页", source_url)` only when a single row is selected. Keep the existing file upload and pasted-JD controls below a divider.

- [ ] **Step 5: Run focused and existing UI-adjacent tests**

Run: `pytest tests/unit/test_demo_presenters.py tests/integration/test_end_to_end.py -q`

Expected: all pass.

- [ ] **Step 6: Commit the official library UX**

```powershell
git add app.py src/ui/demo_presenters.py tests/unit/test_demo_presenters.py
git commit -m "Add official job library demo mode"
```

### Task 3: Source-Audited Ranking Cards

**Files:**
- Modify: `app.py`
- Test: `tests/unit/test_demo_presenters.py`
- Modify: `src/ui/demo_presenters.py`

**Interfaces:**
- Consumes: `JobProfile` 和 `MatchResult`。
- Produces: `source_badge(job: JobProfile) -> str`，值必须包含状态、核验日期和来源类型。

- [ ] **Step 1: Add a failing source badge test**

```python
def test_source_badge_discloses_verification():
    job = JobProfile(job_id="j", company="测试", title="算法", status="active", checked_at="2026-08-12", source_url="https://example.com")
    assert source_badge(job) == "官方公开页｜在招｜核验于 2026-08-12"
```

- [ ] **Step 2: Run the test and confirm failure**

Run: `pytest tests/unit/test_demo_presenters.py::test_source_badge_discloses_verification -q`

Expected: FAIL because `source_badge` is missing.

- [ ] **Step 3: Implement the badge and render it in ranking cards**

Map `active/expired/unknown` to `在招/过期/待确认`. In every ranking card, render the badge and a Markdown link `[查看官方 JD](source_url)` when present. Do not label pasted or imported third-party records as official; use `用户导入｜状态…` unless the host belongs to the verified allowlist.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_demo_presenters.py tests/integration/test_end_to_end.py -q`

Expected: all pass.

- [ ] **Step 5: Commit the audit cards**

```powershell
git add app.py src/ui/demo_presenters.py tests/unit/test_demo_presenters.py
git commit -m "Show verified sources in ranking cards"
```

### Task 4: Real Evaluation Dashboard

**Files:**
- Modify: `app.py`
- Modify: `src/ui/demo_presenters.py`
- Test: `tests/unit/test_demo_presenters.py`

**Interfaces:**
- Consumes: `AnalysisService.load_real_evaluation()` 和 `data/real_jobs/annotation_agreement.json`。
- Produces: `ranking_comparison_rows(result: dict) -> list[dict]`。

- [ ] **Step 1: Write a failing comparison-table test**

```python
def test_ranking_comparison_rows_marks_best_ndcg():
    result = {"ranking": {"keyword": {"recall@5": .15, "ndcg@10": .61}, "rule_fusion": {"recall@5": .49, "ndcg@10": .73}}}
    rows = ranking_comparison_rows(result)
    assert rows[1]["最佳 nDCG@10"] is True
```

- [ ] **Step 2: Run the test and confirm failure**

Run: `pytest tests/unit/test_demo_presenters.py::test_ranking_comparison_rows_marks_best_ndcg -q`

Expected: FAIL because the helper is missing.

- [ ] **Step 3: Implement comparison rows**

```python
def ranking_comparison_rows(result):
    best = max(values["ndcg@10"] for values in result["ranking"].values())
    return [{"方法": name, "Recall@5": values["recall@5"], "nDCG@10": values["ndcg@10"], "最佳 nDCG@10": values["ndcg@10"] == best} for name, values in result["ranking"].items()]
```

- [ ] **Step 4: Add the “实验看板” page**

The page must display dataset disclosure (`30 official jobs`, `27 active`, `3 synthetic profiles`, `human_gold=false`), agreement metrics (`47.78%`, weighted κ `0.3751`, `47` disputes, `8` severe), a method-comparison dataframe, and three limitation callouts. Use the exact copy “双模型独立盲标与裁决形成的模型辅助评测基准”。

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/test_demo_presenters.py -q`

Expected: all pass.

- [ ] **Step 6: Commit the dashboard**

```powershell
git add app.py src/ui/demo_presenters.py tests/unit/test_demo_presenters.py
git commit -m "Add real evaluation dashboard"
```

### Task 5: Demo Documentation and Full Verification

**Files:**
- Modify: `docs/demo_script.md`
- Modify: `README.md`
- Test: existing full suite

**Interfaces:**
- Consumes: the complete verified demo flow.
- Produces: a reproducible 4–5 minute judge walkthrough.

- [ ] **Step 1: Update the demo preparation commands**

Replace synthetic job import with starting Streamlit and clicking “一键加载 30 条官方 JD”. Continue using `data/evaluation/demo_resume.md` because candidate profiles remain synthetic.

- [ ] **Step 2: Update the timeline**

The walkthrough must show official source links, 27 active jobs, a Top-5 match, one grounded resume suggestion, one interview question, and the real evaluation dashboard. It must state that labels are model-assisted rather than human gold.

- [ ] **Step 3: Run complete verification**

Run:

```powershell
python scripts/compile_real_jobs.py
python scripts/evaluate_annotation_agreement.py
python scripts/adjudicate_relevance_labels.py
python scripts/run_real_evaluation.py
pytest -q
```

Expected: 30 jobs, 90 labels, 27 or more tests passing, and no failures.

- [ ] **Step 4: Launch the app for smoke testing**

Run: `streamlit run app.py --server.headless true`

Verify: app starts, official dataset imports once without duplicates, status metrics show `30/27/2/1`, ranking cards link to official sources, and the experiment dashboard loads without exceptions.

- [ ] **Step 5: Commit docs and final integration**

```powershell
git add README.md docs/demo_script.md
git commit -m "Document verified JD demo flow"
```

- [ ] **Step 6: Push and verify CI**

Push the resulting commit chain to `main` using the already-established GitHub API fallback if direct Git transport remains unavailable. Wait for GitHub Actions to pass compilation, tests, agreement reconstruction, adjudication and real-JD evaluation.
