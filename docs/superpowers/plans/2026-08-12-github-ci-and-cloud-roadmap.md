# GitHub CI and Cloud Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the completed AI job-agent MVP under safe private version control, add reproducible GitHub CI, strengthen evaluation and pitch materials, and preserve Supabase as an isolated post-MVP migration.

**Architecture:** The current Streamlit/SQLite application remains the stable demo baseline. GitHub provides source control and CI without changing runtime behavior; evaluation and presentation assets are committed as reproducible artifacts. Supabase work starts only on a separate branch after the local baseline and CI are green.

**Tech Stack:** Git, GitHub CLI, GitHub Actions, Python 3.11, pytest, Streamlit, SQLite; optional later Supabase Postgres/Auth/Storage/pgvector.

## Global Constraints

- The first GitHub repository must be private.
- Never commit `.env`, `data/app.db`, real resumes, API keys, access tokens, or Supabase service-role keys.
- Keep the current SQLite demo runnable throughout the GitHub and evaluation phases.
- Run all 21 tests before the baseline commit and in GitHub Actions.
- Do not begin Supabase migration until the GitHub CI baseline is green.
- Supabase user-data tables must use ownership-based RLS before any public deployment.

---

### Task 1: GitHub Prerequisites and Scope Audit

**Files:**
- Inspect: `.gitignore`, `.env.example`, all tracked-candidate files
- Modify: `.gitignore`

**Interfaces:**
- Produces: an allowlisted, secret-free set of files suitable for the initial private repository.

- [ ] Install GitHub CLI with `winget install --id GitHub.cli` and confirm `gh --version` succeeds.
- [ ] Authenticate with `gh auth login`, selecting GitHub.com and HTTPS, then confirm `gh auth status` reports the intended account.
- [ ] Extend `.gitignore` to exclude `.env`, virtual environments, caches, `data/app.db`, generated vector indexes, real-resume directories, and local report exports while retaining synthetic evaluation fixtures.
- [ ] Run the repository secret scan:

```powershell
rg -n -i --hidden -g '!*.db' -g '!*.npy' -g '!__pycache__/**' -g '!.git/**' '(api[_-]?key|service[_-]?role|secret|password|token)\s*[:=]\s*[^\s"'']+' .
```

Expected: no credential values; names in `.env.example` may appear only with empty values.

### Task 2: Reproducible GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`

**Interfaces:**
- Produces: a `ci` workflow that installs the package on Python 3.11, runs compilation, all tests, sample-data generation, evaluation, and a deterministic import smoke test.

- [ ] Create `.github/workflows/ci.yml` triggered by pushes and pull requests with these commands:

```yaml
- run: python -m pip install --upgrade pip
- run: pip install -e ".[dev]"
- run: python -m compileall -q src app.py scripts
- run: pytest -q
- run: python scripts/generate_sample_data.py
- run: python scripts/run_evaluation.py
- run: python scripts/import_jobs.py --input data/evaluation/jobs.json --db data/ci.db
```

- [ ] Add the workflow badge and a “CI checks” section to `README.md`.
- [ ] Run the same commands locally; expect 21 passing tests, 36 generated jobs, evaluation JSON output, and 36 imported jobs.

### Task 3: Private Repository and Baseline Release

**Files:**
- Track: the audited project tree

**Interfaces:**
- Produces: private GitHub repository `ai-job-agent`, branch `main`, and tag `v0.1.0-demo`.

- [ ] Initialize with `git init -b main` and set repository-local author details if global values are absent.
- [ ] Inspect `git status --short --ignored`; confirm ignored files include `.env`, caches, `data/app.db`, and generated index files.
- [ ] Stage the audited project and review `git diff --cached --stat` plus `git diff --cached --check`.
- [ ] Commit with `git commit -m "build: add hackathon MVP baseline"`.
- [ ] Create the private repository and push with `gh repo create ai-job-agent --private --source . --remote origin --push`.
- [ ] Tag and push the verified baseline with `git tag -a v0.1.0-demo -m "Hackathon demo baseline"` and `git push origin v0.1.0-demo`.
- [ ] Inspect Actions with `gh run list --workflow ci.yml --limit 1`; expect a completed successful run.

### Task 4: Evaluation and Pitch Package

**Files:**
- Create: `docs/pitch/outline.md`, `docs/pitch/metrics-summary.md`
- Create: `docs/pitch/ai-job-agent-demo.pptx`
- Modify: `docs/demo_script.md`

**Interfaces:**
- Produces: a 6–8 slide editable deck using only repository facts and clearly labeling all synthetic results.

- [ ] Summarize problem, architecture, scoring, evidence constraints, demo flow, metrics, limitations, and roadmap in `outline.md`.
- [ ] Generate charts from `data/evaluation/results.json`, labeling the dataset as 36 synthetic jobs and 3 synthetic resumes.
- [ ] Build the deck with title, pain point, product flow, hybrid scoring, demo, evaluation, privacy, and roadmap slides.
- [ ] Render every slide and verify text overflow, clipping, alignment, chart labels, and synthetic-data disclosures.
- [ ] Run `pytest -q` after adding pitch assets; expect all tests to remain green.

### Task 5: Supabase Migration Design Gate

**Files:**
- Create: `docs/supabase-migration.md`
- Future branch: `agent/supabase-cloud`

**Interfaces:**
- Produces: a reviewed schema and security plan without changing the SQLite `main` branch.

- [ ] Define `profiles`, `jobs`, `analyses`, and `resume_files` ownership, retention, and deletion behavior.
- [ ] Specify RLS policies using `TO authenticated` plus `(select auth.uid()) = user_id` for reads and writes; UPDATE policies include both `USING` and `WITH CHECK`.
- [ ] Specify public-client publishable keys and server-only secrets; prohibit `service_role` in Streamlit client code.
- [ ] Map SQLite repositories to a storage interface so the local backend remains available for offline demos.
- [ ] Start `agent/supabase-cloud` only after the baseline GitHub Actions run succeeds.

## Self-Review

- Spec coverage: private source control, secrets, CI, tests, reproducible evaluation, pitch delivery, and a gated Supabase design are each assigned.
- Placeholder scan: all deliverables, commands, branch names, checks, and security rules are explicit.
- Type consistency: GitHub work does not change application interfaces; later Supabase repositories must preserve the existing `JobRepository` and `AnalysisRepository` service behavior.
