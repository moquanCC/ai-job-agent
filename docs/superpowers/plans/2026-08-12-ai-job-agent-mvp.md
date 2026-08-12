# AI Job Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally runnable, testable Streamlit application that parses resumes and Shanghai AI job descriptions, ranks jobs with explainable hybrid scoring, generates grounded advice/interview questions, and reports reproducible evaluation metrics.

**Architecture:** A Python package separates parsing, domain models, repositories, retrieval/ranking, advisory services, evaluation, and UI orchestration. The default path is deterministic and offline; optional OpenAI-compatible configuration can later enhance extraction without making the demo dependent on network access.

**Tech Stack:** Python 3.11, Streamlit, Pydantic v2, PyMuPDF, python-docx, scikit-learn, pandas, NumPy, SQLite, pytest, Docker.

## Global Constraints

- Support PDF, DOCX, TXT, and Markdown resumes.
- Default to Shanghai campus/graduate AI, algorithm, data-mining, recommendation, and data-science roles.
- Never invent candidate experience; every direct rewrite must cite resume evidence.
- Read API keys only from environment variables and never log full resume text.
- Produce Top-K rankings, subscores, matched/missing skills, advice, interview questions, and Markdown export.
- Include at least 30 job samples and reproducible extraction/ranking metrics and ablations.

---

## File Map

- `app.py`: Streamlit five-page workflow and session orchestration.
- `src/models/schemas.py`: Pydantic domain contracts shared by every module.
- `src/parsers/`: file-to-text and text-to-structured-profile parsing.
- `src/matching/`: skill normalization, filtering, deterministic retrieval, scoring, and ranking.
- `src/repositories/`: SQLite job and analysis persistence.
- `src/agents/`: evidence-grounded advice, interview questions, and report rendering.
- `src/evaluation/`: extraction and ranking metric implementations.
- `scripts/`: imports, index preparation, and reproducible evaluation entry points.
- `data/evaluation/`: synthetic resumes, 30+ jobs, and relevance labels.
- `tests/`: unit and end-to-end behavior checks.
- `docs/`: architecture, evaluation, and demo handoff.

### Task 1: Configuration and Domain Contracts

**Files:**
- Create: `pyproject.toml`, `.env.example`, `.gitignore`, `configs/settings.yaml`, `configs/scoring.yaml`, `configs/skill_aliases.yaml`
- Create: `src/config.py`, `src/models/schemas.py`
- Test: `tests/unit/test_schemas.py`

**Interfaces:**
- Produces: `Settings.from_env()`, `ResumeProfile`, `JobProfile`, `MatchResult`, `AdviceReport`, and `InterviewQuestion`.

- [ ] Write tests proving score bounds, unique normalized skills, and required identifiers.
- [ ] Run `pytest tests/unit/test_schemas.py -q`; expect collection failure before implementation.
- [ ] Implement strict Pydantic models and environment-backed settings with safe defaults.
- [ ] Run the test again; expect all schema tests to pass.

### Task 2: Resume and Job Parsing

**Files:**
- Create: `src/parsers/file_parser.py`, `src/parsers/resume_parser.py`, `src/parsers/job_parser.py`, `src/matching/skills.py`
- Test: `tests/unit/test_parsers.py`

**Interfaces:**
- Consumes: schema models and `configs/skill_aliases.yaml`.
- Produces: `parse_document(name: str, content: bytes) -> ParsedDocument`, `parse_resume(text: str) -> ResumeProfile`, `parse_job(record: dict) -> JobProfile`, `normalize_skills(values: Iterable[str]) -> list[str]`.

- [ ] Add tests for TXT/MD parsing, repeated whitespace cleanup, Shanghai extraction, skill aliases, and scanned-PDF errors.
- [ ] Run `pytest tests/unit/test_parsers.py -q`; expect missing-module failures.
- [ ] Implement extension-specific extraction and deterministic, evidence-preserving structured parsing.
- [ ] Run parser tests; expect all to pass.

### Task 3: Persistence, Import, and Filtering

**Files:**
- Create: `src/repositories/database.py`, `src/repositories/job_repository.py`, `src/repositories/analysis_repository.py`, `src/matching/filters.py`, `scripts/import_jobs.py`
- Test: `tests/unit/test_repository.py`, `tests/unit/test_filters.py`

**Interfaces:**
- Produces: `JobRepository.upsert_many(jobs)`, `JobRepository.list_jobs(...)`, `AnalysisRepository.save(...)`, `filter_jobs(jobs, location, include_expired)`.

- [ ] Add temporary-SQLite tests for create/upsert/deduplicate/delete and filtering tests for location, role, campus status, and expiry.
- [ ] Run the repository/filter tests; expect failure before implementation.
- [ ] Implement parameterized SQLite operations and deterministic filters.
- [ ] Re-run tests; expect all to pass.

### Task 4: Retrieval, Explainable Scoring, and Ranking

**Files:**
- Create: `src/retrieval/embeddings.py`, `src/retrieval/faiss_store.py`, `src/matching/rule_matcher.py`, `src/matching/semantic_matcher.py`, `src/matching/score_fusion.py`, `src/matching/ranker.py`
- Test: `tests/unit/test_matching.py`

**Interfaces:**
- Produces: `HashingEmbedder.encode(texts) -> np.ndarray`, `VectorStore.search(query, k)`, `score_job(resume, job, weights) -> MatchResult`, `rank_jobs(resume, jobs, top_k) -> list[MatchResult]`.

- [ ] Add tests asserting Shanghai filtering, missing-skill explanation, weighted-score arithmetic, stable ordering, and 0-100 bounds.
- [ ] Run `pytest tests/unit/test_matching.py -q`; expect missing-module failures.
- [ ] Implement normalized hashing vectors, optional FAISS persistence, overlap/project/education/location subscores, fusion, and stable ranking.
- [ ] Re-run tests; expect all to pass.

### Task 5: Grounded Advice, Interviews, and Reports

**Files:**
- Create: `src/agents/resume_advisor.py`, `src/agents/interview_agent.py`, `src/agents/report.py`
- Test: `tests/unit/test_agents.py`

**Interfaces:**
- Produces: `generate_advice(resume, job, match) -> AdviceReport`, `generate_questions(resume, job, match, difficulty) -> list[InterviewQuestion]`, `render_markdown_report(...) -> str`.

- [ ] Add tests that direct edits contain evidence, absent skills are marked learning-only, interview items contain rationale/follow-up/evidence, and export includes score details.
- [ ] Run agent tests; expect missing-module failures.
- [ ] Implement template-driven, traceable outputs without fabricated achievements.
- [ ] Re-run tests; expect all to pass.

### Task 6: Complete Streamlit Workflow

**Files:**
- Create: `app.py`, `src/services/analysis_service.py`
- Test: `tests/integration/test_end_to_end.py`

**Interfaces:**
- Produces: `AnalysisService.parse_resume_file`, `import_jobs`, `rank`, `build_detail`, and `delete_candidate_data` used by the UI.

- [ ] Add an end-to-end test that imports jobs, parses a synthetic resume, ranks, advises, interviews, exports, and deletes saved analysis.
- [ ] Run `pytest tests/integration/test_end_to_end.py -q`; expect failure before implementation.
- [ ] Implement the five-page Streamlit flow with correction widgets, clear privacy notices, errors, download buttons, and local persistence.
- [ ] Re-run the integration test; expect it to pass.

### Task 7: Evaluation Data and Reproducible Experiments

**Files:**
- Create: `src/evaluation/extraction_metrics.py`, `src/evaluation/ranking_metrics.py`, `scripts/generate_sample_data.py`, `scripts/run_evaluation.py`
- Create: `data/evaluation/jobs.json`, `data/evaluation/resumes.json`, `data/evaluation/relevance.json`, `data/evaluation/results.json`
- Test: `tests/unit/test_metrics.py`

**Interfaces:**
- Produces: `precision_recall_f1`, `recall_at_k`, `mrr`, `ndcg_at_k`, and a JSON result comparing keyword, semantic, hybrid, rule-fusion, and full methods.

- [ ] Add hand-calculated metric tests including empty-label behavior.
- [ ] Run metric tests; expect failure before implementation.
- [ ] Implement metrics, generate 3 synthetic resumes and at least 30 synthetic Shanghai-oriented job records, and define graded labels.
- [ ] Execute `python scripts/run_evaluation.py`; expect a saved result with dataset size, runtime, method parameters, and all required metrics.
- [ ] Re-run metric tests; expect all to pass.

### Task 8: Packaging, Documentation, and Release Verification

**Files:**
- Create: `README.md`, `Dockerfile`, `docker-compose.yml`, `docs/architecture.md`, `docs/evaluation.md`, `docs/demo_script.md`

**Interfaces:**
- Consumes: all runnable commands and generated evaluation results.
- Produces: newcomer setup, data contract, scoring formula, privacy/limitations, architecture, experiment interpretation, and 3-5 minute demo instructions.

- [ ] Document local and Docker startup, configuration, import formats, score semantics, privacy, known limitations, and screenshots/GIF capture instructions.
- [ ] Run `python -m compileall src app.py scripts` and `pytest -q`; expect success.
- [ ] Run `python scripts/import_jobs.py --input data/evaluation/jobs.json --db data/app.db`; expect 30+ jobs imported.
- [ ] Run a Streamlit headless smoke start and confirm the health endpoint responds.
- [ ] Review the handoff checklist line by line and record any environment-dependent limitations honestly.

## Self-Review

- Spec coverage: all four input formats, Shanghai/campus filtering, hybrid ranking, evidence, advice, interview, export, persistence, privacy, 30+ samples, five ablations, metrics, Docker, README, architecture, and demo material are assigned above.
- Placeholder scan: implementation steps name exact behaviors and commands; no deferred features are required for MVP completion.
- Type consistency: parsing produces `ResumeProfile`/`JobProfile`; ranking produces `MatchResult`; advisory/report services consume those exact models; UI consumes the service facade.
