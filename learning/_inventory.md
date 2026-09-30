# DISTILL-001 — Inventory & coverage matrix (Phase 1 + 2)

> Commit: 762b754ecb6c8aae21e005246649252c8bfd0762 (tag `v1.0-submission`). Draft for owner approval — nothing here is final until Phase 3 is approved.
> Evidence status: `path:line` below were read directly in this session ([REPO]). `path` with no line = file seen, line to be pinned in Phase 4 and checked by `_tools/check_refs.py`.
> Home file numbers: 01 python · 02 tooling · 03 architecture/GUI · 04 data I/O · 05 RAG pipeline · 06 embeddings/vector · 07 chunking/retrieval · 08 generation · 09 LLM API · 10 eval design · 11 judge · 12 statistics · 13 case study · 14 testing · 15 workflow · 16 beyond.
> Level: B basic · I intermediate · A advanced.

## 0. Repo map (what exists)

| Area | Size (read via `wc`) | Notes |
|---|---|---|
| `src/knowledge_assistant/` | 6 470 lines Python; largest: `run_evaluation.py` 467, `judge.py` 406, `experiment.py` 363, `scoring.py` 331, `gemini_llm.py` 279, `header_aware.py` 277 | layers `core / application / infrastructure / presentation` + `config.py`, `composition.py` |
| `tests/` + `scripts/` | 13 563 lines Python together | tests ≈ 2× source; fakes in `tests/fakes.py`, `eval_fakes.py`, `judge_fakes.py` |
| `docs/` | ≈ 1.6 MB Markdown: 12 specs, 5 ADRs, 7 epics, 25 execution reports, 14 code reviews + 15 evaluation reviews, 26 prompt-log files | ADR-0003 D1–D9, ADR-0004 D10–D13 (+amendment), ADR-0005 D14–D19 (+2 amendments) |
| `agents/` | 24 task prompts, 8 role files | executor/verifier workflow (`agents/prompts/99-VERIFY.md`) |
| `config/` | `chunking.json`, `messages.json`, `pricing.json`, `prompts/answer_v1|v2.md`, `judge_v1.md` | numbers live here, not in code |
| `validation/` | ingestion / retrieval / generation / evaluation reports | includes the owner-graded `judge-spot-check.md` (read-only for this task) |
| git | 207 commits reachable; tags `eval-freeze-v1`, `v1.0-submission` | worktrees under `.claude/worktrees/` |

Not read line-by-line yet (will be, before each file is written): `scoring.py`, `judge.py`, `experiment.py`, `run_evaluation.py` bodies, `normalizer` body, most `scripts/`, most `tests/`, `answer_v1.md`, 24 prompts, prompt-log, reports. Only docstrings/headers seen so far.

## 1. Coverage matrix (one home file per concept)

### 01 — Python for C# devs
| Concept | Evidence | Level |
|---|---|---|
| `@dataclass(frozen=True)` ≈ `record` (47 uses, 18 files) | `src/knowledge_assistant/core/models/__init__.py:9-16`; `config.py:38-49` | B |
| Type hints, `X \| None`, `list[str]`, `dict[str, X]` | `core/models/__init__.py:13-16`; `config.py:12` | B |
| Modules/packages, `__init__.py`, absolute imports | `src/knowledge_assistant/` tree (many empty `__init__.py`) | B |
| `pathlib.Path`, `/` operator, `Path(__file__).resolve().parents[2]` | `config.py:9-15` | B |
| f-strings, `!r` | `config.py:119`, `gemini_llm.py:252-262` | B |
| Exceptions: hierarchy, custom exceptions, `raise ... from error` (15 sites) | `core/exceptions/__init__.py:1-103`; `application/generation/answer_question.py:38-41` | B/I |
| Class attribute `kind = "other"` overridden in subclasses; `super().__init__` | `core/exceptions/__init__.py:41-87` | I |
| Keyword-only args (`*,`) (23 defs) | `core/exceptions/__init__.py:52-60`; `composition.py:58-65` | I |
| `*args/**kwargs` (26 defs) | `core/exceptions/__init__.py:73-75` (`**details`) | I |
| Comprehensions (907), generator expressions | `application/evaluation/stats.py:40-45` | B/I |
| `lambda` (128) as tiny functions/dict of checks | `answer_question.py:44-50` | I |
| Dict/set/tuple/`deque`/`Counter`/`defaultdict` idioms | `throttle.py:37`, `retrieve.py:29-45` | I |
| `enumerate(..., start=1)`, `zip`, slicing `a[start:end]` | `retrieve.py:43-44`, `embedding_cache.py:104,110` | B |
| Walrus `:=` (3 uses) | `scripts/evaluation/score_spot_check.py:133,221` | I |
| `@property`, `@staticmethod`, `@classmethod` | `config.py:51-54`; `gemini_llm.py:177-178` | B/I |
| `Enum` + `str` mixin | `core/interfaces/embedding.py:5-9` | I |
| `Protocol` (structural typing ≈ duck-typed interface; 11 uses) | `core/interfaces/llm.py:36-37`; `embedding.py:12-18` | I |
| `@contextlib.contextmanager` / `__enter__`-`__exit__` ≈ `using` | `scripts/ask.py:84`; `embedding_cache.py:92-96` | I |
| `with` statements (178) incl. `with self._db:` transaction | `embedding_cache.py:160` | B/I |
| Default-arg injection of `clock`/`sleep`/`jitter` (callables as deps) | `answer_question.py:67`; `gemini_llm.py:106-108` | I |
| `from __future__ import annotations`; forward refs `"Type"` | `presentation/desktop/workers.py:2`; `header_aware.py:102` | I |
| `dict` ordering as ordered set: `list(dict.fromkeys(...))` | `citations.py:90,146`; `embedding_cache.py:100` | I |
| `if __name__ == "__main__"`, `argparse` | `scripts/ask.py:203,236` | B |
| `struct.pack`, bytes/bytearray, `bytes.split`, file modes `ab+` | `embedding_cache.py:36-41`; `jsonl_record_store.py:53,74` | A |
| `itertools.count`, `bisect`, `fractions.Fraction`, `math.comb` | `workers.py:30`; `chunk_builder.py`; `stats.py:45` | A |
| `__post_init__` validation in frozen dataclass | `header_aware.py:37-39` | I |
| `dataclasses.replace`, `asdict` | `composition.py:38`; `run_evaluation.py` imports | I |
| `getattr(obj, name, default)` for duck-typed SDK objects | `gemini_llm.py:57-60,206-211` | I |
| Truthiness / `or` defaults (`os.getenv(..) or None`) | `config.py:35` | B |
| Regex: compile, groups, lookbehind, `re.Pattern[str]` typing | `citations.py:16-23,58` | I/A |

### 02 — Python tooling & dependencies
| Concept | Evidence | Level |
|---|---|---|
| venv, `pip install -e ".[dev]"`, editable install ≈ project reference | `pyproject.toml:10,19`; `README.md` (setup section) | B |
| `pyproject.toml` (deps, optional-deps `dev`), setuptools src layout | `pyproject.toml:1-31` | B |
| `requirements.txt` vs `pyproject` dependency lists (differ: PySide6 pin) | `requirements.txt`; `pyproject.toml:10-17` | I |
| pytest config: `testpaths`, `pythonpath`, `addopts -m 'not gemini'`, markers | `pyproject.toml:25-31` | B/I |
| Env vars & `.env` via `python-dotenv`; `.env.example` placeholders only | `.env.example`; `config.py:20-35`; CLAUDE.md rule 7 | B |
| Env-driven settings, strict bool parsing (typo fails loudly) | `config.py:105-119` | I |
| Paths resolved from repo root, never cwd | `config.py:7-15` | I |
| `OPENBLAS_NUM_THREADS=1` (low-RAM Windows) | `.env.example:34`; `README.md:125` | I |
| Third-party libs the repo teaches: `chromadb`, `google-genai`, `httpx`, `markitdown`, `PySide6`, `PyYAML`, `python-dotenv`, `pytest` | import scan (§2.1) | B |

### 03 — Architecture & GUI
| Concept | Evidence | Level |
|---|---|---|
| Layered / clean architecture; dependency rule | `CLAUDE.md` rule 3; `docs/architecture/system-architecture.md` | B |
| Ports & adapters: `Protocol` ports in `core/interfaces/`, adapters in `infrastructure/` | `core/interfaces/vector_store.py:1-19`; `chroma_store.py:69` | I |
| Composition root | `composition.py:1-5,58-77` | I |
| Architecture test with `ast` (import scanning) | `tests/unit/test_project_structure.py:1-80` | A |
| Wiring seam in presentation | `presentation/desktop/wiring.py` docstring | I |
| Provider exceptions never leave infrastructure (wrapped into core errors) | `gemini_retry.py:1-6`; `gemini_llm.py:14-15` | I |
| Format-independent domain models | `core/models/__init__.py`; ADR-0002 | I |
| ADR format; ADR-0002…0005 decisions & amendments | `docs/architecture/decisions/000*.md` | I |
| MVVM: view-model without Qt, injected executor | `presentation/desktop/viewmodels/ask_viewmodel.py:1-5` | I |
| Qt thread pool: `QRunnable`, `Signal`, `Slot`, results delivered on GUI thread | `presentation/desktop/workers.py:10-42` | A |
| GUI contract + one adapter mapping core→GUI result | `contracts.py:1-5`; `core_ask_question.py:1-6` | I |
| Lazy import of PySide6 in `app.py`; `--fake` offline demo | `presentation/desktop/app.py:1-19` | I |

### 04 — Data I/O & reliability patterns
| Concept | Evidence | Level |
|---|---|---|
| JSON / JSONL files, `ensure_ascii=False`, UTF-8, `\n` line ends | `jsonl_record_store.py:1-9,34,72` | B |
| Append-only log + `fsync` per line | `jsonl_record_store.py:71-82` | I |
| Torn write (unterminated tail) ignored/cut; corruption raises | `jsonl_record_store.py:53-60,75-79` | A |
| Atomic write: temp file + `os.replace` | `jsonl_record_store.py:32-40` | A |
| Secret redaction before any write | `jsonl_record_store.py:34,72`; `gemini_retry.py:52-57` | I |
| SHA-256 content hashing (`content_hash`, `passage_hash`, cache key, frozen-file hash) | `passage.py:477-480`; `embedding_cache.py:32-33`; `integrity.py:16-40` | I |
| Idempotency & resume (latest `ok` record skips; `error` retried; run.json config-mismatch refusal) | `run_evaluation.py:1-13`; `core/exceptions/__init__.py:98-99` | A |
| Determinism: seeds, `sorted(..., key=(-score, chunk_id))` tie-break | `retrieve.py:31`; `stats.py:18` | I |
| SQLite as an on-disk cache (stdlib `sqlite3`), BLOB vectors, `INSERT OR REPLACE`, transaction per call | `embedding_cache.py:19-29,144-162` | I |
| SQLite bound-parameter limit → chunked `IN (...)` lookup | `embedding_cache.py:29,132-142` | A |
| Frozen data integrity (snapshot hash table verified before a run) | `integrity.py:1-40` | I |
| Unicode NFC normalization; CRLF vs LF (offsets & hashes depend on it) | `language.py:1-9`; `markdown_normalizer.py:1-5` | I |
| UTC ISO timestamps | `chroma_store.py:90`; `embedding_cache.py:153` | B |

### 05 — RAG fundamentals (pipeline walkthrough)
| Concept | Evidence | Level |
|---|---|---|
| End-to-end pipeline Documents→Parse→Chunk→Embed→Chroma→Retrieve→Gemini→Answer+Citation | `CLAUDE.md` rule 1; `docs/architecture/rag-pipeline.md` | B |
| "Trace one question": `scripts/ask.py` → `composition.py` → `AnswerQuestion.ask` | `answer_question.py:76-121`; `composition.py:58-77` | B/I |
| Grounding: answer only from context; explicit "insufficient" | `config/prompts/answer_v2.md` rule 1-2; `answer_question.py:1-9` | B |
| Two insufficient layers (retrieval gate, LLM) | `answer_question.py:1-9,90-96,111-113` | I |
| Corpus facts: 28/24/4 excluded, #25 never existed | `CLAUDE.md` rule 4; `tests/unit/test_project_structure.py:63-70` | B |
| Parsing → Markdown; normalization in memory only (ADR-0003 D1) | `markdown_normalizer.py:1-12`; `markitdown_parser.py:1-10` | I |
| Ingestion use cases (`normalize_corpus`, `build_chunks`, `index_corpus`) | `application/ingestion/*.py` docstrings | I |
| Language detection rule (vi diacritics), known limits | `language.py:1-9` | I |
| Bilingual (EN/VI) queries over EN corpus; citations stay English | ADR-0003 D9; `citations.py:74-85` | I |

### 06 — Embeddings & vector search
| Concept | Evidence | Level |
|---|---|---|
| What an embedding is; task types DOCUMENT vs QUERY | `gemini_embedder.py:28-31`; `embedding.py:5-9` | B |
| Output dimensionality 768 vs full 3072 | `config.py:61`; `gemini_embedder.py:32`; ADR-0005 D14 | I |
| L2 normalization; only full-size vectors come normalized | `gemini_embedder.py:37-41,174` | I |
| Cosine similarity; `score = 1 - distance` | `chroma_store.py:20,146`; ADR-0005 D17 | I |
| HNSW / approximate nearest neighbour (`hnsw:space`) | `chroma_store.py:87`; QC-001 "HNSW 5×5 no-repro" (`.remember` / QC-001 report — pin) | A |
| Embedded vs client-server vector DB; `PersistentClient` | `chroma_store.py:78` | I |
| Collection name encodes chunker + model id; metadata check on open | `chroma_store.py:26-30,97-105` | I |
| Chroma metadata limits (no None, no lists) → JSON strings | `chroma_store.py:32-49` | I |
| Batching: `plan_calls`, count and half-minute token caps | `gemini_embedder.py:85-106` | I |
| Batched call counts one quota request per text (V-1 probe) | `throttle.py:19-22`; ADR-0005 V-1 | A |
| Cache decorator: only misses go out; commit per call | `embedding_cache.py:1-6,98-120` | I |
| Upsert by `chunk_id`; batch 500 | `chroma_store.py:22,115-132` | I |
| Token estimate 4 chars/token; over-estimates ~15% | `throttle.py:10-14` | I |

### 07 — Chunking & retrieval
| Concept | Evidence | Level |
|---|---|---|
| Why chunk; fixed-size (Arm B) windows + overlap | `fixed_size.py:1-3`; `config/chunking.json` | B |
| Header-aware chunker (Arm A) algorithm, 5 steps | `header_aware.py:1-16` | I |
| Merge small sibling sections; split oversized by blocks; overlap at word boundary; never inside code fence | `header_aware.py:79-132,222-237` | A |
| Tables: header row repeated in `embed_text` only | `header_aware.py:153-159` | A |
| `display_text` vs `embed_text`; contextual heading prefix | `chunk_builder.py:1-4`; `passage.py:468-474` | I |
| Chunk ID `{source_id}:{chunker_config}:{index:04d}` | `core/models/__init__.py:52` | B |
| Link stripping; content_hash vs passage_hash | `chunk_builder.py:293`; `passage.py:477-480` | I |
| Config-driven chunkers (`load_arm`) | `factory.py:9-25`; `config/chunking.json` | B |
| Retrieval: top-k, over-fetch, dedup by passage, re-rank 1..k | `retrieve.py:1-9,29-45,71` | I |
| Refusal gate; threshold 0.686 derived on dev set (0.7360 − 0.05) | `config.py:206-211`; `docs/specs/retrieval-spec.md:38-51` | I/A |
| Chunk stats (size distribution, code-fence cuts, small chunks) | `chunking/stats.py:1-30` | I |
| Heading path as citation location; version variants numbered | `core/models/__init__.py:20-28`; ADR-0003 D1/D5 | I |

### 08 — Generation & prompting
| Concept | Evidence | Level |
|---|---|---|
| Prompt as a versioned file; version = file name; never inline | `prompt_builder.py:1-3`; `config.py:149` | B |
| Prompt anatomy: role, rules, CONTEXT, QUESTION | `config/prompts/answer_v2.md` | B |
| Placeholder replace by one regex pass (not `str.format`) | `prompt_builder.py:441-452` | I |
| Structured output: JSON schema, `response_json_schema`, JSON mode | `prompt_builder.py:455-461`; `gemini_llm.py:3-4,178-182` | I |
| Strict output parsing → `GenerationError` w/ raw text; never guessed | `answer_question.py:36-56` | I |
| Citation markers `[n]`, only outside code (fenced + inline) | `citations.py:1-7,26-71` | A |
| Uncited-sentence diagnostic | `citations.py:110-119` | I |
| Excerpt as verbatim prefix, cut at word boundary | `citations.py:74-85` | I |
| Out-of-range markers dropped & recorded | `citations.py:136-150` | I |
| `answer_v1` → `answer_v2` change | `config/prompts/answer_v1.md` vs `answer_v2.md` (diff to read) | I |
| Prompt injection from documents (present risk, not mitigated in code) | `README.md:323`; QC-001 report | A |
| Localized insufficient message | `config/messages.json`; `answer_question.py:27-33` | B |

### 09 — LLM API engineering
| Concept | Evidence | Level |
|---|---|---|
| Rate limits RPM/TPM/RPD; free-tier numbers | `config.py:71-83,152-153` | B |
| Client-side sliding-window throttle | `throttle.py:17-60` | I |
| Retry with exponential backoff + jitter; `Retry-After`/`retryDelay`; cap 120 s | `gemini_retry.py:16-18,67-82,104-108` | I |
| Error classification: quota / unavailable / other; retryable set | `gemini_retry.py:16,111-149` | I |
| Daily quota vs per-minute 429; reset 14:00 UTC+7 | `gemini_retry.py:19-20,85-101` | A |
| Fallback model: one attempt, own output budget, off for eval | `gemini_llm.py:6-20,163-175`; `config.py:86-102` | I |
| Error types wrapped into core (`LLMQuotaError` etc.); `__cause__` | `core/exceptions/__init__.py:41-87`; `gemini_llm.py:245-279` | I |
| finish_reason handling (MAX_TOKENS, SAFETY…) → `GenerationError` | `gemini_llm.py:52,204-231` | I |
| Token accounting incl. thinking tokens; latency split (retry_wait, throttle_wait) | `core/interfaces/llm.py:13-33`; `gemini_llm.py:206-243` | I |
| Cost estimate; null price = "not available", never a guess | `config/pricing.json`; `config.py:191-193` | I |
| Observer hook that must not change behaviour; swallowed exceptions logged | `gemini_llm.py:19-20,196-200` | A |
| Quota budget per evaluation run | `run_evaluation.py:11-13` | A |
| Key redaction (`AIza…` pattern) | `gemini_retry.py:21,52-57` | I |
| SDK retry deliberately off; attempts counted in one place | `gemini_llm.py:18` | A |
| Timeouts, `HttpOptions(timeout=ms)` | `gemini_llm.py:134-137` | I |

### 10 — Evaluation design
| Concept | Evidence | Level |
|---|---|---|
| Golden set; ≥30 questions (here 36 eval + 6 dev, 32 answerable / 4 not) | `docs/specs/evaluation-spec.md`; `docs/snapshots/evaluation/eval-v1.md` | B |
| Freezing (tag `eval-freeze-v1`, SHA-256 table), dev/eval split | `integrity.py:1-40`; `git tag` | I |
| Ground truth before indexes (leakage/Goodhart) | `CLAUDE.md` rule 9; `EPIC-05-evaluation.md:47` | I |
| Hit rule on offsets, not heading text | `metrics/retrieval.py:1-19` | A |
| Lenient vs strict; alternates; headline vs diagnostic | `metrics/retrieval.py:9-19`; `scoring.py:1-20` | A |
| Expected spans built offline & deterministic | `build_expected_spans.py:1-10`; `metrics/spans.py:1-10` | I |
| Metric denominators, unlabelled ≠ guessed | `scoring.py:77-86` | A |
| Result labels & `map_result` table | `metrics/mapping.py:3-12,50-71` | I |
| `points_covered` (yes + 0.5·partial) | `mapping.py:79-89` | I |
| Latency percentiles: nearest-rank, clean vs retried/fallback | `metrics/latency.py:1-12,19-57` | I |
| Run records: append-only, all fields always present | `records.py:1-12` | I |
| Parallel EN/VI pairs (isolate cross-lingual effect) | ADR-0003 D9 | I |
| Construct validity, Goodhart's law | Goodhart in 7 files; "construct validity" 0 files → `[GENERAL]` | A |

### 11 — LLM-as-judge
| Concept | Evidence | Level |
|---|---|---|
| Judge = data supplier; label picked by deterministic table | `mapping.py:1-16`; `judge.py:1-3` | I |
| Judge prompt (grading rules, per-point ids, citations support) | `config/prompts/judge_v1.md` | I |
| Which records get judged (`judge_check`) | `judge.py:28-35` | I |
| Strict parsing → `judge_error`; expected id sets | `judge.py:39-42` | A |
| Judge cache key & validity checks (`JudgeCacheMismatch`) | `judge.py:43-47` | A |
| Self-preference risk (same model as answerer) → manual spot-check | ADR-0004 D12; `config.py:160-162` | I |
| Blind spot-check, Cohen's κ = 0.688, 8/10 agreement (n = 10, seed 42) | `EPIC-05-evaluation.md:25,381,436` | A |
| Real judge failures (S03 invented claim; marker 22) | `AI_WORKLOG.md:873-881` | I |

### 12 — Statistics
| Concept | Evidence | Level |
|---|---|---|
| Paired design (same cases both arms) | `stats.py:1-9` | I |
| Exact McNemar via `Fraction` + `math.comb` | `stats.py:34-46` | A |
| Paired bootstrap 95 % CI, 10 000 resamples, seed 42 | `stats.py:17-18,63-81` | A |
| Wilcoxon signed-rank, exact, average ranks, ties | `stats.py:99-140` | A |
| Nearest-rank percentile with exact rational rank | `latency.py:19-27`; `stats.py:84-87` | I |
| p-value wording rule ("no reliable difference", never "A better") | `stats.py:8`; `AI_WORKLOG.md:844-847` | I |
| Power at small n; one case moves a rate 1.6–2.8 pts | `AI_WORKLOG.md:888-890` | I |
| Float tie noise (`round(...,12)`) | `stats.py:19,123` | A |

### 13 — Case study EXP-001
| Concept | Evidence | Level |
|---|---|---|
| Hypothesis, controls (same threshold, same embeddings), arms A/B | `docs/reports/epics/EPIC-06-experiment.md`; `docs/snapshots/experiments/exp-001.md` | I |
| Failure classification rules | `experiment.py:1-9` | A |
| Honest conclusion (no significant difference at n) | `EPIC-06-experiment.md` §5; `AI_WORKLOG.md:844-847` | I |
| Arm B reuses query embeddings | `tests/unit/test_eval_arm_b_reuses_query_embeddings.py` | I |

### 14 — Testing & quality
| Concept | Evidence | Level |
|---|---|---|
| pytest basics; `tmp_path` (23 files), `monkeypatch` (80 uses) | `tests/`; scan | B |
| Fixtures (`autouse`, `scope=module`) & `parametrize` (~45 uses) | scan (§2.2) | I |
| Fakes over mocks: `FakeEmbedder`, `FakeLLM`, `FakeClock`, `FakeModels`, `ScriptedLLM` | `tests/fakes.py:12,50,65,187`; `eval_fakes.py:69,97` | I |
| Injected clock/sleep/jitter make time-based code testable | `throttle.py:24-31`; `gemini_llm.py:106-108` | I |
| Offline-by-default; `@pytest.mark.gemini` deselected | `pyproject.toml:28-31` | B |
| Architecture tests | `test_project_structure.py` | A |
| Mutation testing as acceptance gate | 46 files mention; RAG-003 verify, INGEST-003 re-verify | A |
| Flaky tests / HNSW no-repro | QC-001 (`.remember` note; report to pin) | A |
| Test-count history (866 passed / 1 deselected) | QC-001 verify | B |

### 15 — AI-assisted dev workflow
| Concept | Evidence | Level |
|---|---|---|
| Executor–verifier (`99-VERIFY`), fix prompts, re-verify | `agents/prompts/99-VERIFY.md`; `docs/reviews/code/*-verify.md` | I |
| Task prompts + addenda + CHANGELOG | `agents/prompts/*.md`, `CHANGELOG.md` | I |
| Task ledger, execution reports, prompt-log, worklog | `docs/plans/task-ledger.md`; `docs/reports/execution/` | I |
| Git: `dev` integration, feature branches, PRs, tags, worktrees | `CLAUDE.md` rule 11; `git tag`; worktree list | I |
| Secrets hygiene; `.env` untracked; key never logged | `CLAUDE.md` rule 7; `gemini_retry.py:52-57` | B |
| GitNexus impact analysis rule | `CLAUDE.md` (GitNexus section) | I |
| Incidents (see §2.4) | `AI_WORKLOG.md:812-881` | I |

### 16 — Beyond this project (all `[GENERAL]`)
Hybrid search (BM25+vectors) · reranking · query rewriting · user-uploaded docs (`README.md:323`, `AI_WORKLOG.md:899-901`) · observability/tracing · eval frameworks · long-context vs RAG · agents/tool use · second judge model · per-arm threshold tuning. Repo pointers: task prompt `agents/prompts/13-BONUS-001-hybrid-and-query-rewrite.md`; `README.md:245` states no BONUS-001 item was built.


### 01b — Python code-reading guide (added at owner request, 2026-09-29)
| Concept | Evidence | Level |
|---|---|---|
| Reading procedure for an unfamiliar file (docstring → imports → constants → types → public API → trace) | this repo's docstring-heavy style, e.g. `src/knowledge_assistant/config.py:1-15` | B |
| Symbol decoder table (`*`, `**`, `:=`, `->`, `_`, `...`, slices, `is None`, `__name__`) | `scripts/ask.py:236`, `core/exceptions/__init__.py:73` | B |
| ~22 syntax templates (`[GENERAL]`) each paired with a real repo example (defaults/kw-only, guard clause, enumerate/zip, `*rest`, comprehensions, slices, f-string formats, try/else/finally, decorators, generator, lambda+sorted, isinstance/getattr, argparse, pytest fixture/parametrize, fakes, any/all, truthiness, literals) | see `01b` T1–T22 | B/I/A |
| Trace-by-hand drills with executed answers (dedupe, excerpt, throttle, cache store) | `retrieve.py:29-45`, `citations.py:74-85`, `throttle.py:40-60`, `embedding_cache.py:144-162` | I |

## Home-file decisions after batch 1 (one home per concept)
- 0.686 threshold rule and dev table: home **07 §3.3**; 05 links to it and keeps only the consequence.
- Exact McNemar / bootstrap / Wilcoxon: home **12**; 01 §3.3 uses McNemar only as a syntax-reading example and says so.
- Sliding-window throttle: code walkthrough in 01b (T20); concept home **09 §2.1**.
- Retry/backoff/jitter, error kinds, fallback, redaction, quota timezone, cost estimate: home **09**.
- Embedding cache, batching, cosine, HNSW, quota plan: home **06**. Chunkers, dedup, over-fetch, gate: home **07**.
- Layers, ports/adapters, composition root, architecture test, MVVM/QThread: home **03**.

## 2. Phase 2 — discovery pass results

### 2.1 Import scan (AST over `src/`, `tests/`, `scripts/`)
**stdlib (36):** `__future__ argparse ast bisect collections contextlib copy csv dataclasses datetime enum fractions hashlib html importlib inspect io itertools json logging math os pathlib random re shlex sqlite3 struct subprocess sys threading time types typing unicodedata zipfile`
**third-party:** `PySide6 chromadb dotenv google(genai) httpx markitdown pytest yaml`
Concepts each teaches → `bisect` (binary search, `chunk_builder`/`markdown_structure`) 07; `struct` (binary vectors) 04/06; `sqlite3` 04; `fractions` (exact stats) 12; `threading` (`threading.Lock` in `core_ask_question.py:58`) 03; `html` (escape in GUI) 03; `shlex/subprocess/zipfile/importlib/inspect/types` (tests & scripts) 14; `csv` (report scripts) 04; `logging` 09; `random` 09/12; `unicodedata` 04/05; `copy` 04.

### 2.2 Syntax/idiom scan (counts from AST)
`@dataclass(frozen=True)` 47 · `Protocol` bases 11 · `Enum` 2 · exception classes: 17 in `core/exceptions/__init__.py` (24 across `src/`+`scripts/`) · `@property` 14 · `@contextmanager` 3 · generators 3 (`yield`) · keyword-only 23 · `*args/**kwargs` 26 · `raise … from` 15 · walrus 3 · `match` 0 · `__slots__` 0 · `functools` 0 · `TypedDict/Literal/Final/generics` 0 (not used → not taught as "in repo", mentioned `[GENERAL]` only) · `with` 178 · `lambda` 128 · comprehensions 907 · pytest fixtures 13 · `parametrize` ≈ 45 · `staticmethod` 1 · `classmethod` 2.

### 2.3 Docs-term scan
Not yet exhaustive. Candidate terms found so far: OD-n (open decision ids), D1–D19 decision ids, V-1 probe, "arm", "gate", "over-fetch", "passage", "slot", "alternate source", "headline vs diagnostic", "lenient/strict", "clean vs retried", "model purity", "torn tail", "frozen", "amendment", "addendum", "99-VERIFY", "fix round", "mutation", "blind spot-check", "leakage timeline". **Todo Phase 4:** full term sweep over specs/ADRs/reports → glossary.

### 2.4 Incident scan — `[REAL]` lessons (source `AI_WORKLOG.md:812-881` + reviews)
| # | Incident | Lesson file | Source |
|---|---|---|---|
| 1 | "Strict-like" evidence_hit claim false for 4/32 cases | 10 | `EVAL-003b-pre-verify.md` C1 |
| 2 | `[n]` parsed inside code blocks (F1) | 08 | `RAG-002-verify.md`; fix `ba5aa59` |
| 3 | 502 not retried vs owner's status list | 09 | `RAG-003-verify.md` F1 |
| 4 | Unguarded observer hook could end retry loop | 09 | `EVAL-003a-verify.md` F1 |
| 5 | Spot-check tool never run on real sheet | 14/15 | `EVAL-003c-verify.md` |
| 6 | "Already based on `dev`" claimed, not checked | 15 | EXP-001 entry (worklog) |
| 7 | Wrong first-index time in report | 15 | `EVAL-004b-verify.md` C |
| 8 | "Equivalent" wording contradicts own rule | 12 | `EXP-001-verify.md` C12 |
| 9 | Planning-assistant: evidence quotes "only from expected sections" (3/100 not) | 10 | `EVAL-003b-pre-verify.md` Extra 3 |
| 10 | "span/source" wording (predicted ≤2, measured 6) | 10/15 | worklog EVAL-003b |
| 11 | Leftover `.git` lock files | 15 | owner statement only |
| 12 | Blueprint 018 parent-heading alternate would inflate section hit | 10 | `EVAL-001-blueprint-review.md` #13 |
| 13 | Judge invented claim (S03) | 11 | worklog `:875` |
| 14 | Judge marker 22 = source id → `judge_error` | 11 | worklog `:878` |
| 15 | **QC-001 fork fabricated owner confirmation** (commits reverted) | 15 | worklog `:760-`; `QC-001-verify.md:22` |
| 16 | Boilerplate list "in one constant" (FAIL minor) | 15 | `INGEST-001-verify.md` A9 |
| 17 | Commit message claimed "0 processes, risk low" — actual 5 / medium | 15 | `INGEST-001-verify.md` A17 |
| 18 | Stale test counts in worklog (30 vs 32; 171 vs 173) | 15 | `RAG-001a-verify.md` C3 |
| 19 | Re-check sheet claimed "only `slot` changed" — 27 blueprints changed | 15 | `REORIENT-001-verify.md` C3 |
| 20 | `.env.example` missing 12 variables `config.py` reads | 02/15 | `QC-001-verify.md` A18 |
| 21 | Frozen-file rule; leakage timeline correction | 10/15 | `EVAL-004b-verify.md` |
| 22 | RAG-003 open: no real 429/503 ever observed | 09 | `provider_error_log.py:1-9`; worklog `:895` |

Full sweep of the remaining ~25 review/verify files is a Phase 4 task per file (each lesson tagged `[REAL]` with path).

### 2.5 Seed checklist — confirmed against repo?
✅ in repo: pathlib · JSON/JSONL · append-only · fsync/atomic · idempotency/resume · SHA-256 hashing/cache keys · Unicode NFC · CRLF/LF · regex (markers, code) · SQLite cache · determinism/seeds · embeddings task types · L2 norm/cosine · HNSW · embedded DB · chunking/overlap · dedup · over-fetch · refusal gate threshold · JSON schema output · prompt versioning · rate limits · throttle · retry/backoff/jitter/retry-after · fallback · error classification · quota reset/timezone · token accounting incl. thinking · cost estimate · golden set · freeze · dev/eval split · lenient/strict · denominators · Goodhart · LLM-as-judge · mapping table · κ · paired design · McNemar · bootstrap · Wilcoxon · nearest-rank · layered arch · ports/adapters · composition root · architecture tests · MVVM+QThread · fakes · offline tests · flaky test note · mutation testing · worktrees/branches/tags · executor–verifier · secrets hygiene.
⚠️ partial: prompt injection (named as a limitation, no code) · statistical power (stated qualitatively) · key **rotation** (0 hits — only "never commit"; → `[GENERAL]`) · construct validity (0 hits → `[GENERAL]`) · hybrid/BM25/rerank (14 files mention; `README.md:245` says BONUS-001 was not built → `[GENERAL]` only).
❌ dropped from "in repo": `match`, `TypedDict`, `Literal`, `Final`, `functools`, `__slots__`.

### 2.6 Next-level pass → file 16 (roadmap, all `[GENERAL]`)
hybrid search & reranking · query rewriting · long-context vs RAG · user uploads (ingestion, page-level citations, no ground truth, doc-borne prompt injection, privacy, multi-tenancy) · observability/tracing · eval frameworks (RAGAS-style; named as concept only) · agents/tool use · second judge · larger frozen set · per-arm threshold.

## 3. Gaps / risks in the inventory
1. Evidence for `scoring.py`, `judge.py`, `experiment.py`, `run_evaluation.py`, `normalizer` body not yet read past headers — rows using them cite docstrings only.
2. Docs-term sweep and the review/report incident sweep are incomplete (see 2.3/2.4).
3. Numbers not yet re-verified against source: 0.686 (seen in `config.py:210` and `retrieval-spec.md:38`, ✔), κ 0.688 and 8/10 (seen in EPIC-05, ✔), 866 tests (from repo memory/QC notes, **not** re-run — offline pytest needs the main checkout's `.venv`; will re-run once, with `OPENBLAS_NUM_THREADS=1`, in Phase 5).
4. Runtime data (`data/`, eval run folders) is untracked and lives in the main checkout; reading it needs the main path.
