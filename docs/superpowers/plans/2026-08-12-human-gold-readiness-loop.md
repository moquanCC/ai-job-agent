# Human Gold Readiness Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete, auditable minimum workflow for collecting two independent human labels and one adjudication across 30 heterogeneous synthetic candidates and 750 candidate–JD pairs, while refusing production promotion until real humans complete the files.

**Architecture:** Generate deterministic synthetic candidate profiles and freeze a candidate-level 18/6/6 train/validation/blind-test split. Export three answer-isolated Excel workbooks, import them through strict validators, compute human agreement and adjudicated gold only when every required field is genuinely completed, and gate production weight promotion on `human_gold=true`, blind-test metrics, stability and engineering checks.

**Tech Stack:** Python 3.11+, JSON, pytest, scikit-learn metrics, `@oai/artifact-tool` XLSX authoring.

## Global Constraints

- Candidate profiles are synthetic and must always declare `synthetic=true`; do not call them real resumes.
- The 30 candidates must cover LLM/RAG, NLP, CV, multimodal, recommendation, data mining, search/ads, AI infra, agents, autonomous driving and AI testing with varied education and evidence strength.
- Use exactly 25 eligible public JDs per candidate, yielding exactly 750 unique pairs.
- Split by candidate, never by pair: 18 train, 6 validation, 6 blind test; store a deterministic manifest and SHA-256 fingerprint.
- Annotator A and B workbooks cannot contain each other's answers; the adjudicator workbook starts blank and may include both grades only after import.
- Blank/template workbooks are not human labels. Until complete imports pass, `human_gold=false` and production promotion must be rejected.
- Promotion requires complete human labels, adjudication, frozen blind test, agreement thresholds, ranking guardrails and explicit configuration review; no automatic write to `configs/scoring.yaml` in readiness mode.

---

### Task 1: Generate heterogeneous profiles and frozen task manifest

**Files:**
- Create: `scripts/generate_human_gold_dataset.py`
- Create: `data/human_gold/candidates.json`
- Create: `data/human_gold/split_manifest.json`
- Create: `data/human_gold/annotation_tasks.json`
- Test: `tests/unit/test_human_gold_dataset.py`

- [x] Write tests requiring 30 unique synthetic candidates, 11+ role families, 18/6/6 candidate split, 25 jobs per candidate, 750 unique pairs, eligible job IDs only and stable fingerprint.
- [x] Run tests and confirm the generator is missing.
- [x] Implement deterministic generation from explicit profile archetypes and repository JD IDs.
- [x] Generate artifacts twice and assert byte-identical output.
- [ ] Run focused tests and commit.（实现与 focused tests 已完成；待根任务提交）

### Task 2: Strict human annotation import, agreement and adjudication

**Files:**
- Create: `src/evaluation/human_gold.py`
- Create: `scripts/import_human_annotations.py`
- Create: `scripts/build_human_gold.py`
- Test: `tests/unit/test_human_gold_pipeline.py`
- Test: `tests/integration/test_human_annotation_cli.py`

- [x] Write failing tests for blank grades, invalid scale, missing rationale, duplicated pairs, coverage mismatch, annotator identity collision and synthetic/template disclosure.
- [x] Implement CSV/XLSX-neutral row validation using normalized JSON input from the workbook exporter/importer boundary.
- [x] Compute exact agreement and weighted kappa only after two complete independent imports.
- [x] Require adjudicator grade and rationale for every disagreement; agreements may pass through with explicit decision metadata.
- [x] Emit gold with `human_gold=true` only after complete A/B/adjudication coverage and identity checks; otherwise emit readiness status with `human_gold=false`.
- [ ] Run tests and commit.（实现与 tests 已完成；待根任务提交）

### Task 3: Production promotion gate

**Files:**
- Create: `src/evaluation/promotion_gate.py`
- Create: `scripts/check_production_promotion.py`
- Test: `tests/unit/test_production_promotion.py`

- [x] Write failing tests for missing human gold, insufficient agreement, split leakage, weak blind-test improvement, Recall@10 regression, direction instability and missing engineering audit.
- [x] Implement a pure gate returning `passed`, machine-readable failures and evaluated evidence.
- [x] Require `human_gold=true`, 30 complete candidates, exact frozen split, exact agreement >= 0.70, quadratic weighted kappa >= 0.60, blind nDCG@5 gain >= 0.02, Recall@5 non-decrease, Recall@10 drop <= 0.01, >=70% candidate-level non-decrease and engineering audit passed.
- [x] Make readiness mode always refuse configuration writes when annotation files are blank.
- [ ] Run tests and commit.（实现与 tests 已完成；待根任务提交）

### Task 4: Create and visually verify three blind workbooks

**Files:**
- Create: `outputs/human_gold/annotator_A.xlsx`
- Create: `outputs/human_gold/annotator_B.xlsx`
- Create: `outputs/human_gold/adjudicator.xlsx`

- [x] Use `@oai/artifact-tool` to create Instructions, Candidates, Tasks and QC sheets with frozen panes, filters, validation lists and formula-driven completeness checks.
- [x] Keep grade, rationale, confidence and annotator identity blank; mark every workbook `human_gold=false` and `status=template_not_completed`.
- [x] Ensure A and B files contain identical tasks in independently shuffled order and no answer columns from the other file.
- [x] Keep adjudicator decision fields blank and explain that A/B grades are populated only after validated import.
- [x] Inspect key ranges and formula errors, render every sheet, visually review previews, then export the three XLSX files.

### Task 5: Documentation, verification and publication

**Files:**
- Create: `docs/human_annotation_protocol.md`
- Modify: `README.md`
- Modify: `docs/evaluation_real.md`
- Modify: this plan

- [x] Document assignment, blinding, grade rubric, adjudication, identity and conflict-of-interest rules, import commands and the exact promotion gate.
- [x] Run all tests, compile scripts and execute readiness checks against blank templates; expected promotion result is rejected with `human_labels_incomplete`.（readiness 验证完成；主线最终测试数曾为 141，后续合并可能增加）
- [x] Verify 30/750/18-6-6 counts, workbook formula/error scans and visual renders.
- [ ] Commit, publish and verify hashing-only CI.

**Readiness outcome:** 30 synthetic candidates spanning 11 role families, 25 eligible official JDs per candidate, 750 pairs and a frozen 18/6/6 candidate split are complete. Three blank blind workbooks exist under `outputs/human_gold/`; all 12 sheets passed visual/formula QA with 0 formula errors, and the adjudicator QC bug was fixed and rechecked. The collection/import/adjudication/gate workflow is ready, but no human has completed the templates: `human_gold=false`, `status=template_not_completed`, and production promotion remains prohibited.

**Closed-loop evaluation:** Complete adjudication output now carries gate-ready status, split/fingerprint, counts and agreement. `run_human_gold_evaluation.py` creates a shortlist on 18 train candidates, selects on 6 validation candidates and evaluates the frozen 6-candidate blind test exactly once before `check_production_promotion.py`. The command path is implemented and verified, but has not been run on real human gold because all workbooks remain blank.

