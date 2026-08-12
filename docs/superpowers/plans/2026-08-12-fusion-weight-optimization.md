# Fusion Weight Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explore BGE-M3 fusion weights with a reproducible, leakage-aware search while preserving hard eligibility filters and refusing deployment promotion from the three-candidate model-assisted sample.

**Architecture:** Separate expensive score-component extraction from cheap weight search. Cache the six per-job subscores once, enumerate a constrained simplex, select weights with leave-one-candidate-out validation, and only promote a deployment profile when it passes explicit baseline guardrails. Persist the complete search protocol and results so the UI never presents tuned metrics as human-ground-truth performance.

**Tech Stack:** Python 3.11+, NumPy, Pydantic models, pytest, existing ranking metrics, BAAI/bge-m3 dense embeddings.

## Global Constraints

- Shanghai, active-status and eligibility checks remain hard filters and are never tunable score weights.
- The source dataset contains 27 public active JDs; the shared eligibility filter admits 26 jobs, yielding 78 pairs for 3 synthetic candidates with model-assisted labels and `human_gold=false`.
- No claim of production or real hiring effectiveness is allowed.
- BGE-M3 is encoded once per candidate/job set; the grid search must operate on cached subscores without re-running the model.
- The search space, objective, tie-breakers, seed (if any), candidate-level results and rejected candidates must be serialized.
- CI continues to use hashing and must not download BGE-M3.
- Default weights must not change in this experiment: three synthetic candidates and `human_gold=false` are insufficient for deployment promotion.
- Search compares against the five non-location baseline weights normalized from `(0.30, 0.10, 0.20, 0.20, 0.10)` by their `0.90` sum; any future deployment must restore `location=0.10` and scale the other five weights by `0.90` to preserve absolute score thresholds.

---

## File Structure

- `src/evaluation/fusion_tuning.py`: pure candidate generation, ranking from cached subscores, metric aggregation, LOCO selection and guardrails.
- `scripts/tune_fusion_weights.py`: dataset loading, one-time embedding/subscore extraction, CLI, JSON output and optional configuration promotion.
- `data/real_jobs/fusion_weight_search_bge_m3.json`: auditable BGE-M3 search result.
- `configs/scoring.yaml`: promoted default weights only after guardrails pass.
- `scripts/run_real_evaluation.py`: named optimized method and optional weight-file consumption.
- `src/ui/demo_presenters.py`, `app.py`: honest baseline-versus-tuned display.
- `tests/unit/test_fusion_tuning.py`: deterministic search, constraints, tie-breaks and guardrails.
- `tests/integration/test_tune_fusion_cli.py`: hashing/fake smoke test with temporary output and no downloads.
- `README.md`, `docs/evaluation_real.md`, `docs/demo_script.md`: protocol, measured result and limitations.

### Task 1: Pure constrained weight search

**Files:**
- Create: `src/evaluation/fusion_tuning.py`
- Create: `tests/unit/test_fusion_tuning.py`
- Modify: `src/evaluation/__init__.py`

**Interfaces:**
- Produces: `generate_weight_candidates(step: float) -> list[dict[str, float]]`
- Produces: `evaluate_weights(cached_rows: list[dict], weights: dict[str, float]) -> dict`
- Produces: `leave_one_candidate_out(cached_rows: list[dict], candidates: list[dict[str, float]]) -> dict`
- Produces: `passes_guardrails(baseline: dict, candidate: dict) -> tuple[bool, list[str]]`

- [x] **Step 1: Write failing tests for the constrained simplex**

Assert every candidate sums to `1.0`, uses `location=0.0`, keeps `required_skill >= 0.25`, `0.10 <= semantic <= 0.35`, and uses multiples of the requested step.

- [x] **Step 2: Run the tests and verify the functions are missing**

Run: `pytest tests/unit/test_fusion_tuning.py -q`

- [x] **Step 3: Implement candidate generation and cached ranking**

Rank by the weighted sum of `required_skill`, `preferred_skill`, `project`, `semantic`, and `education`; use `job_id` as the deterministic final tie-break. Compute Recall@5, Recall@10, MRR, nDCG@5 and nDCG@10 from cached grades.

- [x] **Step 4: Implement LOCO selection and deterministic tie-breaks**

For each held-out candidate, select on the other two by: highest mean nDCG@5, then worst-candidate nDCG@5, lower L1 distance from the normalized baseline, and finally lexicographic weight tuple. Evaluate the selected weights only on the held-out candidate. Compute the component-wise median only as a target, then choose the legal searched candidate with minimum L1 distance to that target as a deterministic medoid. Label its all-data metrics `descriptive_only`; LOCO validates the selection procedure, not this medoid as an independently tested deployment profile.

- [x] **Step 5: Implement promotion guardrails**

Compute diagnostic comparisons including per-candidate direction, worst-candidate nDCG@5, fold-winner L1 spread, unique ranking count and tied-best count. Always return promotion rejected with `exploratory_insufficient_candidates` and `human_gold_false`; these data cannot update production defaults.

- [ ] **Step 6: Run unit tests and commit**（测试已完成；待根任务提交）

Run: `pytest tests/unit/test_fusion_tuning.py tests/unit/test_metrics.py -q`

Commit: `Add constrained fusion weight search`

### Task 2: Reproducible tuning CLI and cached components

**Files:**
- Create: `scripts/tune_fusion_weights.py`
- Create: `tests/integration/test_tune_fusion_cli.py`

**Interfaces:**
- Consumes the pure functions from Task 1.
- Produces a JSON document containing `dataset`, `embedding`, `search`, `baseline`, `loco`, `deployment_candidate`, `guardrails`, and `limitations`.

- [x] **Step 1: Write a failing hashing CLI test**

Run against repository fixtures with `--embedding-backend hashing --step 0.10 --output <tmp>` and assert the result declares the actual backend, candidate count, fold winners, descriptive-only deployment metrics and guardrail decision.

- [x] **Step 2: Verify the CLI test fails**

Run: `pytest tests/integration/test_tune_fusion_cli.py -q`

- [x] **Step 3: Implement one-time component extraction**

Load only active jobs, parse each candidate, call the embedder once for the resume and once for all eligible jobs, then cache each job's six `Subscores` and adjudicated grade. Do not invoke `rank_jobs` inside the grid loop.

- [x] **Step 4: Implement CLI and audit output**

Support `--embedding-backend`, `--embedding-model`, `--embedding-device`, `--batch-size`, `--max-length`, `--step`, `--output`, and `--promote-config`. In this experiment `--promote-config` always exits with an actionable refusal because there is no independent human-labelled test set.

- [ ] **Step 5: Run integration and regression tests and commit**（测试已完成；待根任务提交）

Run: `pytest tests/integration/test_tune_fusion_cli.py tests/integration/test_evaluation_backend_cli.py -q`

Commit: `Add auditable fusion tuning CLI`

### Task 3: Run BGE-M3 exploratory search and retain defaults

**Files:**
- Create: `data/real_jobs/fusion_weight_search_bge_m3.json`
- Do not modify: `configs/scoring.yaml`

**Interfaces:**
- Consumes the cached official BGE-M3 model.
- Produces measured fold results and an explicit non-promotion decision.

- [x] **Step 1: Run the coarse search**

Run:

```powershell
python scripts/tune_fusion_weights.py --embedding-backend bge-m3 --embedding-model BAAI/bge-m3 --embedding-device cpu --step 0.05 --output data/real_jobs/fusion_weight_search_bge_m3.json
```

- [x] **Step 2: Audit the result**

Verify `actual_backend=bge-m3`, `fallback_occurred=false`, all three candidates appear exactly once as held-out folds, and search candidates obey every constraint.

- [x] **Step 3: Retain baseline**

Verify `--promote-config` refuses to write. Retain the current default weights and record the exploratory medoid without manual override. A future promotion requires additional heterogeneous candidates and an independent human-labelled holdout set.

- [x] **Step 4: Re-run real evaluation**

Add the exploratory profile as a named method and write its descriptive metrics to a separate result file. Never overwrite the original BGE baseline and never label this profile “optimized” or “production”.

- [ ] **Step 5: Commit measured artifacts**（待根任务提交）

Commit: `Benchmark optimized BGE fusion weights`

### Task 4: Evaluation integration and UI disclosure

**Files:**
- Modify: `scripts/run_real_evaluation.py`
- Modify: `src/ui/demo_presenters.py`
- Modify: `app.py`
- Modify: `tests/unit/test_demo_presenters.py`
- Modify: `tests/integration/test_evaluation_backend_cli.py`

**Interfaces:**
- Consumes the tuning JSON and promoted/retained weights.
- Produces baseline/tuned/LOCO rows with explicit validation scope.

- [x] **Step 1: Write failing presenter and CLI tests**

Assert the UI labels all-data tuned metrics as “描述性（调参后）”, LOCO metrics as “留一候选人验证”, and renders a rejected candidate without calling it optimized.

- [x] **Step 2: Implement named optimized method support**

Allow the real evaluation CLI to load a weight JSON or explicit YAML profile, serialize the exact weights, and keep `full_baseline` separate from `full_tuned`.

- [x] **Step 3: Implement honest dashboard rows**

Show baseline, descriptive candidate, LOCO mean and per-fold range. Include the promotion decision and failed guardrails. Do not display a winner badge when promotion is rejected.

- [ ] **Step 4: Run related tests and commit**（测试已完成；待根任务提交）

Run: `pytest tests/unit/test_demo_presenters.py tests/integration/test_evaluation_backend_cli.py -q`

Commit: `Disclose fusion tuning validation`

### Task 5: Documentation, full verification and publication

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation_real.md`
- Modify: `docs/demo_script.md`
- Modify: `docs/superpowers/plans/2026-08-12-fusion-weight-optimization.md`

**Measured outcome (final JSON after consistency fix):** 26 eligible jobs / 78 labelled pairs; 2050 legal candidates produced 208 unique rankings and 1842 equivalent ties. The three LOCO folds produced 2 unique winners. The exploratory legal medoid is `(required=.25, preferred=.10, project=.15, semantic=.35, education=.15, location=0)`. Baseline → descriptive metrics are Recall@5 `.4901961 → .4901961`, Recall@10 `.6078431 → .5882353`, MRR `.7777778 → .8333333`, nDCG@5 `.6939607 → .7559514`, and nDCG@10 `.7213242 → .7426167`. LOCO means are Recall@10 `.5882353`, nDCG@5 `.7536770`, and nDCG@10 `.7409596`; held-out nDCG@5 range is `.6215484–.8869466`. Earlier provisional numbers are superseded by `data/real_jobs/fusion_weight_search_bge_m3.json`. Promotion is rejected; defaults remain unchanged because Recall@10 declines, LOCO validates the selection procedure rather than the medoid, fold winners are unstable, deployment would require restoring/scaling the location weight, and the sample remains three synthetic candidates with `human_gold=false`.

**Consistency repair:** Ranking signatures were corrected to include candidate identity when counting unique cross-candidate ranking outcomes. Implementation and regression verification are complete; documentation now uses the final serialized artifact as the sole metric source. Commit/push/CI remain pending in the root task.

- [x] **Step 1: Document the exact protocol and result**

Explain why three profiles are insufficient for a publication-grade learned ranker, distinguish LOCO validation from descriptive all-data metrics, list the search constraints and guardrails, and report negative or null results unchanged.

- [x] **Step 2: Run complete verification**

Run:

```powershell
pytest -q
python -m compileall -q src app.py scripts
python scripts/run_real_evaluation.py --embedding-backend hashing --output $env:TEMP/evaluation_hashing.json
```

- [ ] **Step 3: Commit, publish and verify CI**

Commit documentation, push through direct Git or the established GitHub API fallback, and wait for CI. CI must remain hashing-only.

