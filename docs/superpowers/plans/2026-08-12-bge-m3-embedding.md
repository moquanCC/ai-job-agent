# BGE-M3 Chinese Embedding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将岗位语义召回与匹配从字符 n-gram 基线升级为真正的 `BAAI/bge-m3` 中文稠密向量，同时保留可测试、可离线启动的 hashing fallback。

**Architecture:** 定义统一 `TextEmbedder` 协议和工厂函数，`BgeM3Embedder` 通过可选的 `sentence-transformers` 延迟加载模型、批量编码并归一化；默认配置仍可显式选择 hashing，生产演示配置选择 BGE-M3。排序链路一次性批量编码候选人与所有岗位，避免逐岗位重复推理；索引脚本保存模型元数据，防止用错维度或模型。FAISS 为可选加速层，缺少 `faiss-cpu` 时继续使用等价的 NumPy 余弦搜索。

**Tech Stack:** Python 3.10+、sentence-transformers、BAAI/bge-m3、NumPy、可选 faiss-cpu、Pydantic、pytest。

## Global Constraints

- 模型名称固定为 `BAAI/bge-m3`，默认最大长度 1024，批大小 8；模型支持更长输入，但岗位匹配无需默认使用 8192。
- 编码输出必须是 `float32`、二维、L2 归一化的稠密向量。
- `sentence-transformers` 和模型权重必须延迟加载；导入模块、运行 hashing 测试和启动 fallback 不得下载模型。
- 没有模型缓存或依赖时，只有配置为 `auto` 才回退 hashing；显式 `bge-m3` 必须给出可操作错误，不能静默伪装成功。
- CI 不下载 BGE-M3 权重；使用 fake model 测试适配层，真实模型只在显式集成/基准命令中运行。
- 每次排序最多批量编码一次候选人和一次岗位集合，不得在岗位循环内加载或调用模型。
- README 和实验结果必须记录实际 backend；未运行 BGE-M3 基准前不得用旧 hashing 指标宣称 BGE-M3 提升。

---

### Task 1: Embedder Protocol and BGE-M3 Adapter

**Files:**
- Modify: `src/retrieval/embeddings.py`
- Modify: `src/retrieval/__init__.py`
- Modify: `pyproject.toml`
- Test: `tests/unit/test_embeddings.py`

**Interfaces:**
- Produces: `TextEmbedder` protocol with `name: str` and `encode(texts: list[str]) -> np.ndarray`.
- Produces: `BgeM3Embedder(model_name="BAAI/bge-m3", batch_size=8, max_length=1024, device=None, model=None)`.
- Produces: `create_embedder(backend: str, ...) -> TextEmbedder` for `hashing`, `bge-m3`, and `auto`.

- [x] **Step 1: Write adapter tests with a fake SentenceTransformer**

```python
class FakeModel:
    def __init__(self):
        self.max_seq_length = None
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return np.array([[3.0, 4.0], [0.0, 2.0]], dtype="float64")


def test_bge_adapter_batches_normalizes_and_uses_float32():
    model = FakeModel()
    embedder = BgeM3Embedder(model=model, batch_size=8, max_length=1024)
    vectors = embedder.encode(["中文简历", "上海算法岗位"])
    assert vectors.dtype == np.float32
    assert np.linalg.norm(vectors, axis=1) == pytest.approx([1, 1])
    assert model.max_seq_length == 1024
    assert model.calls[0][1]["batch_size"] == 8
    assert model.calls[0][1]["normalize_embeddings"] is True
```

- [x] **Step 2: Verify the tests fail before implementation**

Run: `pytest tests/unit/test_embeddings.py -q`

Expected: import failure for `BgeM3Embedder` and `create_embedder`.

- [x] **Step 3: Implement lazy loading and strict fallback semantics**

`BgeM3Embedder._load_model()` must import `SentenceTransformer` inside the method and raise:

```python
RuntimeError("BGE-M3 不可用；请安装 `pip install -e .[embedding]` 并预下载 BAAI/bge-m3，或设置 EMBEDDING_BACKEND=hashing")
```

`auto` catches that error and returns `HashingEmbedder`; explicit `bge-m3` propagates it. Empty input returns a stable `(0, dimensions)` array only after the model dimension is known; callers should avoid empty batches.

- [x] **Step 4: Add optional dependencies**

```toml
embedding = ["sentence-transformers>=3.0,<6"]
retrieval = ["sentence-transformers>=3.0,<6", "faiss-cpu>=1.8"]
```

- [x] **Step 5: Run tests and commit**

Run: `pytest tests/unit/test_embeddings.py -q`

```powershell
git add src/retrieval/embeddings.py src/retrieval/__init__.py pyproject.toml tests/unit/test_embeddings.py
git commit -m "Add lazy BGE-M3 embedding backend"
```

### Task 2: Configuration and Runtime Embedder Lifecycle

**Files:**
- Modify: `src/config.py`
- Modify: `configs/settings.yaml`
- Modify: `.env.example`
- Modify: `src/services/analysis_service.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/integration/test_embedding_service.py`

**Interfaces:**
- Extends `Settings` with `embedding_backend`, `embedding_model`, `embedding_device`, `embedding_batch_size`, and `embedding_max_length`.
- Produces `AnalysisService.embedder`, created once per service rather than per job.

- [x] **Step 1: Write environment parsing tests**

```python
def test_embedding_settings_from_env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_BACKEND", "bge-m3")
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "4")
    monkeypatch.setenv("EMBEDDING_MAX_LENGTH", "1024")
    settings = Settings.from_env()
    assert settings.embedding_backend == "bge-m3"
    assert settings.embedding_batch_size == 4
```

- [x] **Step 2: Verify failure, then implement settings**

Defaults:

```env
EMBEDDING_BACKEND=auto
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=
EMBEDDING_BATCH_SIZE=8
EMBEDDING_MAX_LENGTH=1024
```

Reject nonpositive batch/max length with `ValueError`.

- [x] **Step 3: Create one embedder per service**

Allow dependency injection:

```python
def __init__(..., embedder: TextEmbedder | None = None):
    self.embedder = embedder or create_embedder(...)
```

Tests inject `HashingEmbedder` or a fake embedder, so CI never downloads weights.

- [x] **Step 4: Run tests and commit**

Run: `pytest tests/unit/test_config.py tests/integration/test_embedding_service.py -q`

```powershell
git add src/config.py configs/settings.yaml .env.example src/services/analysis_service.py tests/unit/test_config.py tests/integration/test_embedding_service.py
git commit -m "Configure embedding backend lifecycle"
```

### Task 3: Batched Semantic Scoring

**Files:**
- Modify: `src/matching/semantic_matcher.py`
- Modify: `src/matching/ranker.py`
- Modify: `src/services/analysis_service.py`
- Test: `tests/unit/test_semantic_batching.py`
- Test: `tests/unit/test_matching.py`

**Interfaces:**
- Produces `semantic_scores(query_text: str, document_texts: list[str], embedder: TextEmbedder) -> list[float]`.
- Extends `score_job(..., semantic_score: float | None = None)`.
- Extends `rank_jobs(..., embedder: TextEmbedder | None = None)`.

- [x] **Step 1: Write a call-count regression test**

```python
def test_rank_jobs_encodes_one_query_and_one_job_batch():
    embedder = CountingEmbedder()
    results = rank_jobs(resume, jobs, embedder=embedder)
    assert embedder.batches == [1, len(jobs)]
    assert len(results) == len(jobs)
```

- [x] **Step 2: Verify current implementation fails**

Expected: current code constructs `HashingEmbedder` for every pair and cannot accept the injected embedder.

- [x] **Step 3: Implement vectorized scoring**

Encode the resume text once and eligible job texts as one batch. Compute clipped cosine scores with matrix multiplication. Pass each score into `score_job`; never re-encode inside `score_job` when `semantic_score` is supplied.

- [x] **Step 4: Wire the service embedder**

```python
return rank_jobs(..., embedder=self.embedder)
```

- [x] **Step 5: Run regression tests and commit**

Run: `pytest tests/unit/test_semantic_batching.py tests/unit/test_matching.py tests/integration/test_end_to_end.py -q`

```powershell
git add src/matching/semantic_matcher.py src/matching/ranker.py src/services/analysis_service.py tests/unit/test_semantic_batching.py tests/unit/test_matching.py
git commit -m "Batch semantic scoring across jobs"
```

### Task 4: Model-Aware Persistent Vector Index

**Files:**
- Modify: `src/retrieval/faiss_store.py`
- Modify: `scripts/build_index.py`
- Test: `tests/unit/test_vector_store.py`
- Test: `tests/integration/test_build_index.py`

**Interfaces:**
- Extends `VectorStore.save(directory, metadata: dict | None = None)`.
- Extends `VectorStore.load(directory, expected_model: str | None = None)`.
- CLI adds `--backend`, `--model`, `--device`, `--batch-size`, and `--max-length`.

- [x] **Step 1: Write metadata mismatch tests**

```python
store.save(path, metadata={"backend": "bge-m3", "model": "BAAI/bge-m3", "dimensions": 1024})
with pytest.raises(ValueError, match="模型不匹配"):
    VectorStore.load(path, expected_model="local-hashing-v1")
```

- [x] **Step 2: Implement `metadata.json`**

Save backend, model, dimensions, normalized flag, job count and build timestamp. Validate vector/ID count and dimensions on load.

- [x] **Step 3: Update the index CLI**

Example:

```powershell
python scripts/build_index.py --backend bge-m3 --model BAAI/bge-m3 --db data/app.db --output data/bge_m3_index
```

The CLI must print the actual backend/model/dimensions. Explicit BGE failure exits nonzero with the actionable installation message.

- [x] **Step 4: Run tests and commit**

Run: `pytest tests/unit/test_vector_store.py tests/integration/test_build_index.py -q`

```powershell
git add src/retrieval/faiss_store.py scripts/build_index.py tests/unit/test_vector_store.py tests/integration/test_build_index.py
git commit -m "Persist embedding index metadata"
```

### Task 5: Backend-Aware Evaluation

**Files:**
- Modify: `scripts/run_evaluation.py`
- Modify: `scripts/run_real_evaluation.py`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/integration/test_evaluation_backend.py`

**Interfaces:**
- Both scripts accept `--embedding-backend`, `--embedding-model`, `--embedding-device`, and `--output`.
- Results record `requested_backend`, `actual_backend`, `model`, `dimensions`, batch size and max length.

- [x] **Step 1: Write CLI tests using hashing backend**

Run each script in a temporary output path with `--embedding-backend hashing`; assert `actual_backend == "hashing"` and metrics exist.

- [x] **Step 2: Refactor scripts to use one injected embedder**

Do not instantiate the model inside candidate or job loops. CI continues to use:

```powershell
python scripts/run_evaluation.py --embedding-backend hashing
python scripts/run_real_evaluation.py --embedding-backend hashing
```

- [x] **Step 3: Add optional manual BGE benchmark command**

```powershell
python scripts/run_real_evaluation.py --embedding-backend bge-m3 --embedding-model BAAI/bge-m3 --output data/real_jobs/evaluation_results_bge_m3.json
```

- [x] **Step 4: Run tests and commit**

Run: `pytest tests/integration/test_evaluation_backend.py -q`

```powershell
git add scripts/run_evaluation.py scripts/run_real_evaluation.py .github/workflows/ci.yml tests/integration/test_evaluation_backend.py
git commit -m "Make evaluations embedding-backend aware"
```

### Task 6: Real Model Installation, Benchmark, UI Disclosure and Docs

**Files:**
- Modify: `app.py`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/evaluation_real.md`
- Modify: `docs/demo_script.md`
- Generated: `data/real_jobs/evaluation_results_bge_m3.json`
- Test: full suite and manual model smoke test

**Interfaces:**
- UI sidebar displays actual backend/model and whether fallback occurred.
- Experiment dashboard compares hashing baseline with BGE-M3 only after the BGE result file exists and passes disclosure validation.

- [x] **Step 1: Install the optional backend**

Run:

```powershell
pip install -e ".[embedding]"
```

This changes the local environment and downloads packages; obtain environment approval when required.

- [x] **Step 2: Download and smoke-test BGE-M3**

Run one two-sentence encoding and assert shape `(2, 1024)`, dtype `float32`, finite values and L2 norms near 1. Record model download size/time separately from query latency.

- [x] **Step 3: Run the real benchmark**

Run:

```powershell
python scripts/run_real_evaluation.py --embedding-backend bge-m3 --embedding-model BAAI/bge-m3 --output data/real_jobs/evaluation_results_bge_m3.json
```

Do not claim improvement unless the measured metrics exceed the stored hashing baseline. If they regress, report the regression and keep both files.

- [x] **Step 4: Add UI backend disclosure**

Render `实际语义后端`, `模型`, and fallback warning in the sidebar. In the experiment dashboard, show BGE-M3 metrics only from its result file; otherwise show the exact command required to generate it.

- [x] **Step 5: Update documentation with official usage facts**

Document that the official model supports dense, sparse and multi-vector retrieval, while this project initially uses its normalized dense vectors only. Cite the official model card and FlagEmbedding repository. Document first-run download, CPU latency, optional GPU device, privacy, cache directory and hashing fallback.

- [x] **Step 6: Run complete verification**

```powershell
pytest -q
python -m compileall -q src app.py scripts
python scripts/run_real_evaluation.py --embedding-backend hashing
python scripts/run_real_evaluation.py --embedding-backend bge-m3 --output data/real_jobs/evaluation_results_bge_m3.json
```

Expected: all tests pass, both result files declare their actual backend, and the app launches with backend disclosure.

- [x] **Step 7: Commit, push and verify CI**（远端提交 `69d2174`，CI run `31560055693` 已通过）

```powershell
git add app.py README.md docs data/real_jobs/evaluation_results_bge_m3.json
git commit -m "Document and benchmark BGE-M3 retrieval"
```

Push with the established GitHub API fallback if direct transport is unavailable, then wait for CI. CI must not download the BGE-M3 weights.
