# Local RAG upgrade plan

**Status:** draft, pending owner approval. Written 2026-11-10.
**Source:** the owner's draft "Kế hoạch nâng cấp Knowledge Assistant lên local RAG" (2026-11-10), revised after a
review against the code on `main` (`c67a341`). Where this document and the owner's draft differ, the difference is
listed in [§10 Changes from the owner's draft](#10-changes-from-the-owners-draft).

Nothing here is built yet. Every number marked *estimate* is unmeasured and must be replaced by a measurement before
it is quoted anywhere else (CLAUDE.md rule 9).

## 1. Goal

Turn the Knowledge Assistant from a Gemini-backed assistant over a fixed 24-document corpus into a **local,
standalone** RAG desktop app that:

- runs on the user's machine with no cloud call by default;
- accepts the user's own study documents (Vietnamese and English);
- is a complete product on its own: the PySide6 app, with the study features as screens in it;
- can optionally serve the Smart Study Planner (C# .NET 10 WPF) over a local API. The two apps form a small
  study-tool ecosystem, but neither requires the other to be installed or running (§8.1);
- keeps the measured, citation-grounded behaviour the project has today.

## 2. Constraints and decisions already made by the owner

| Topic | Decision |
|---|---|
| Target hardware | Intel gen-10 CPU, 8 GB RAM, no discrete GPU. The integrated GPU is benchmarked as a configuration in Phase 1 (§6.2). Discrete-GPU offload is an optional later feature. |
| Development machine | Stronger than the target. The target is emulated (4 threads, no GPU layers, process capped at 8 GB in WSL2 or a VM); numbers from it are **relative only** (prompt size A against B, model A against B). Absolute numbers come from one run on a real gen-10 / 8 GB machine (§5 item 4). |
| Documents | Vietnamese and English. |
| Planner | C# .NET 10 WPF, separate repository, available from month 6. |
| GUI | The PySide6 GUI stays and stays independent of the Planner. |
| LLM runtime | Bundled `llama-server` (llama.cpp): OpenAI-style API, grammar-constrained JSON. Ollama remains usable through the same adapter. |
| Default LLM | 1.5–2B parameters, Q4 quantisation (Qwen3 1.7B or a newer model of the same size). "Quality" option: 4B Q4. |
| Default embedder | `multilingual-e5-small`, ONNX int8. `bge-m3` optional on stronger machines. Final choice by evaluation. |
| Keyword search for Vietnamese | Syllable + bigram tokens, plus a diacritic-stripped copy of the index. No heavy NLP library. |
| Ingestion | Convert every input file to Markdown with MarkItDown, then use the existing Markdown chunkers. |
| Product shape | Standalone PySide6 app: application layer in-process, starts and stops `llama-server` itself. Study features have screens in this app. |
| Planner integration | Optional mode of the same install, off by default and enabled in settings: FastAPI on localhost, versioned under `/v1`, C# client generated from OpenAPI (NSwag). Loose coupling through a discovery file (§8.1). |
| Gemini | Fallback only during the transition (see §4.3 for what "removed" means). |

RAM budget on the 8 GB target (*estimate*): Windows about 3 GB, and the Planner about 0.5 GB when both apps run,
leaving the assistant under 2.5 GB in total: LLM 1.2–1.5 GB, embedder 0.2 GB, index under 0.5 GB, **plus the
reranker, which the first draft did not count** (§7.1).

## 3. What the current code makes easy and hard

Easy:

- `core/interfaces` defines `LLM`, `Embedder`, `VectorStore` as protocols, and `AnswerQuestion` depends only on them.
- `EmbeddingTask` already distinguishes `DOCUMENT` from `QUERY`, which is what e5 models need for their
  `passage:` / `query:` prefixes.
- The ChromaDB collection name and the embedding cache key both contain the embedding model id, so a new embedder
  gets a new collection and never mixes vectors with the old one.
- The evaluation harness (frozen questions, resumable runs, paired statistics) exists and is reusable.

Hard (each is a task in §5–§8):

- `GeminiLLM` is imported directly in `presentation/desktop/wiring.py`, `scripts/evaluation/run_eval.py` and
  `scripts/evaluation/judge_run.py`; `composition.open_embedder` hard-codes the Gemini embedder.
- "Arm" means chunker only, and `("A", "B")` is hard-coded in about ten places (`composition.py:28`,
  `run_evaluation.py:42`, `ask_viewmodel.py:15`, several scripts). `compare_arms.py` accepts exactly A and B.
- `RunConfig` has no field for embedder, retriever or LLM, so a resumed run would not notice that one changed.
- `Retriever` is a concrete class with no interface; `VectorStore.search` takes only a vector; there is no delete.
- The score gate compares top-1 cosine similarity to a fixed 0.686.
- Chunk ids are positional per document; indexing can resume but cannot update or remove a document.
- `MarkdownNormalizer` rejects input without two H1 headings (it is specific to the web-export format), and the
  MarkItDown path skips normalisation altogether.
- The frozen ground truth (`expected-spans-v1.json`) stores character offsets into `normalized.jsonl`.
- `LLM.generate` returns one complete response; the GUI delivers one result per job; there is no streaming.

## 4. Rules that hold for the whole plan

### 4.1 The frozen 24-document benchmark stays byte-identical

Generalising ingestion must not change `normalized.jsonl` for the fixed corpus. Add a test that pins its hash. The
36 questions and their expected spans remain the regression benchmark for every phase.

### 4.2 One change per comparison

Never change the embedder, the LLM, the prompt or the retriever in the same comparison. Each evaluation run records
all of them, and a report compares runs that differ in exactly one.

### 4.3 Gemini's role

- **In the product:** fallback to Gemini is **opt-in and off by default**, with a visible indicator when an answer
  came from the cloud. An automatic fallback on timeout would silently send the user's private document text to a
  cloud API and contradicts the offline claim; on a slow CPU, timeouts will be frequent.
- **In development:** Gemini stays as the evaluation judge for the life of the project. A 1.5–2B local model cannot
  grade answers reliably. "Remove Gemini" in the last phase means removing it from the shipped product only.
- Known bias to disclose in every local-versus-Gemini report: the judge is the same model family as one of the two
  systems being compared. Grow the owner spot-check for these comparisons.

### 4.4 Governance

llama.cpp, ONNX Runtime, FastAPI and SQLite FTS5 are outside the stack locked in CLAUDE.md rule 2, and rule 6 pins
Gemini model names. Each needs an ADR before code lands, and CLAUDE.md is updated in the same change. Page-based
citations (§7.2) need an amendment to ADR-0003 D5/D6.

## 5. Phase 0 — foundations (month 1)

Nothing user-visible. This phase removes the obstacles that would otherwise distort every later measurement.

1. **Run-dimension refactor.** Replace "arm" with independent, named dimensions: chunker, embedder, retriever, LLM,
   prompt version. Add them to `RunConfig` so a resume with a different value fails loudly. Keep A and B as named
   presets so existing run files stay readable. Generalise `compare_arms.py` to compare any two runs that differ in
   one dimension.
2. **Provider seams.** One factory for `LLM` and one for `Embedder`, selected from configuration. Remove the direct
   `GeminiLLM` imports from the GUI wiring and the evaluation scripts. Give `Retriever` an interface.
3. **Benchmark expansion.** The 36-question set cannot support the later comparisons: dense retrieval already scores
   0.938 section_hit@5, leaving hybrid search almost no room to show a gain, and five disagreeing pairs cannot reach
   significance. Add, frozen before any new index is built:
   - Vietnamese questions over Vietnamese documents (a small second corpus of study material);
   - exact-identifier questions (class names, method names, error codes) where keyword search should help;
   - more unanswerable questions (there are 4 today), needed to measure the gate and hallucination.
   Target size: **DECISION REQUIRED** (owner). At least 100 questions in total is the smallest size at which a
   10-point accuracy difference is likely to be detectable with the existing paired test.
4. **Measurement harness.** Record for every answer: peak process memory, time to first token, prompt tokens,
   generated tokens, tokens per second. Two tools:
   - `scripts/benchmark/local_llm_bench.py` (written, standard library only): `llama-bench` plus streamed answers
     through `llama-server` per prompt size (one warm-up, then the median of 3 measured runs, prompt cache off), for
     each model, each GPU-layer setting, and with the model memory-mapped and fully loaded (`--no-mmap`, which gives
     the real RAM figure). It is a speed probe on filler
     text; it does not include retrieval and says nothing about answer quality.
   - The same fields added to evaluation run records once the local pipeline exists.
   Emulated runs on the development machine are relative only (§2). The script is run **once on a real gen-10 /
   8 GB machine**, and only those numbers feed the go/no-go (§6.3).
5. **Packaging spike.** Build a throwaway PyInstaller bundle (one-directory mode) of the standalone app: PySide6,
   ChromaDB, ONNX Runtime, and `llama-server` started as a child process. The standalone app needs a Windows bundle
   regardless of the Planner, and this is the riskiest engineering item in the plan and cheap to test now.

Exit gate: existing 866 tests pass; the frozen benchmark reproduces the EPIC-05 numbers through the refactored code
with 0 new API requests (cache hit); the spike bundle starts and answers on a clean Windows machine.

## 6. Phase 1 — local models (month 2)

### 6.1 Order of work

1. **Local embedder only.** Add `OnnxEmbedder` (e5 prefixes mapped from `EmbeddingTask`). Re-index both chunkers.
   Run **retrieval-only** evaluation, which makes no LLM call. Compare against the Gemini embedder.
   - Check whether `fastembed` ships `multilingual-e5-small`; if not, load the ONNX file with `onnxruntime` and
     `tokenizers` directly. ChromaDB already depends on ONNX Runtime, so this adds no large dependency.
   - e5-small reads at most 512 tokens. A 1,600-character chunk of Vietnamese or code can exceed that and is cut off
     silently. Measure the token length of every chunk; size chunks by the embedder's tokenizer or lower the
     character limit.
2. **Local LLM only.** Add `LlamaCppLLM` against `llama-server`. Hold retrieval fixed (same embedder, same chunks)
   and run full evaluation with the **same prompt version** on Gemini and on the local model.
3. **Prompt and context tuning for the small model**, as a separate, versioned step (`answer_v3`), re-run on both
   providers.

### 6.2 Things to decide in this phase

- **Latency is dominated by reading the prompt, not by generating.** 10–15 tokens per second (*estimate*) is
  generation speed. Five 1,600-character chunks plus instructions is roughly 2,000–2,500 prompt tokens, which the CPU
  must process before the first word appears; that may be tens of seconds (*estimate*). The speed work is listed in
  §6.4; each item that can change answers is its own comparison (§4.2).
- **Output format.** Today the answer is a string inside a JSON object, which cannot be shown while it is being
  generated. For the local model, use plain text with `[n]` markers; `resolve_citations` already works on markers.
  Grammar-constrained JSON stays available for structured tasks (quiz). The format is specified with its failure
  behaviour:
  - *Refusal sentinel:* when the passages do not answer the question, the model's output starts with the exact line
    `[[INSUFFICIENT]]`, optionally followed by one line saying what is missing. The client holds back the first line
    of the stream until it can tell whether it is the sentinel, so the sentinel is never shown as answer text.
  - *Malformed or missing markers degrade gracefully:* a marker that is out of range or not a number is removed from
    the text and produces no citation; the rest of the answer is still shown. An answer with no valid marker is
    shown with a visible "no source cited" notice and counted as a citation failure in evaluation. The retrieved
    sources are still listed under it: the question passed the gate, so they are usually relevant, and a small
    model often just forgets the markers. The missing-marker rate is measured and gated in §6.3. A sentinel that
    appears anywhere other than the first line is treated as ordinary text. None of these cases raises an error.
  - *Tests:* offline unit tests for each case above (valid, out-of-range, non-numeric, no marker, sentinel first,
    sentinel late, sentinel split across stream chunks).
- **Thinking mode.** Qwen3 models have a reasoning mode that spends tokens before answering; turn it off for the
  default profile and measure the effect.
- **Streaming.** Add a streaming method to the `LLM` interface, a token signal in `QtExecutor`, and a partial-answer
  state in `AskViewModel`. Citations resolve when the stream ends.
- **CPU against integrated GPU.** Every gen-10 Intel CPU has an integrated GPU. Benchmark it as a configuration:
  llama.cpp CPU build against its Vulkan (or SYCL) build with layers offloaded, using `--ngl 0 99` in the benchmark
  script. The expected gain is in prompt processing, the largest cost; whether it materialises on this hardware is
  unknown until measured. OpenVINO GenAI is a second candidate runtime; it needs its own model format and adapter,
  so try it only if the llama.cpp result is inconclusive. Integrated-GPU memory is shared system RAM and is not
  counted in the process's peak memory, so record system memory too.
- **Score gate, interim.** Re-tune the cosine threshold for the new embedder on the dev split, and expect it to be
  weak: e5 similarity scores sit in a narrow high band. The real fix is in Phase 2.
- **Model download.** First run downloads about 1.2 GB. Pin the file checksum, show progress, allow a manual file
  path. Confirm each model's licence allows redistribution or download-on-first-run.

### 6.3 Go / no-go at the end of month 2

Thresholds are fixed **before** the runs: **DECISION REQUIRED** (owner) for each of

- strict and lenient answer accuracy relative to Gemini on the same retrieval;
- hallucination rate on unanswerable questions (today 0.000);
- Vietnamese answer quality on the new Vietnamese questions (owner-graded sample);
- median time to first token and peak memory, from the one run on the real gen-10 / 8 GB machine (§5 item 4).

Decided (owner, 2026-11-10): **missing-marker rate**, the share of answered benchmark questions whose answer has no
valid `[n]` marker, must be at most 10%. Above that, the product switches to the strict behaviour: an answer with no
valid marker is replaced by the refusal message.

If the 1.5–2B model fails, the options are: make 4B the default and accept slower answers; or keep cloud answering as
a first-class opt-in mode rather than a fallback. The rest of the plan (hybrid search, ingestion, service) does not
depend on the outcome.

### 6.4 Speed work, in order of expected payoff

All payoffs are *estimates* until measured. Items 1–3 can change answer quality and each gets its own benchmark run.

| # | Change | Requirement attached |
|---|---|---|
| 1 | Send 3 passages instead of 5 (after reranking, Phase 2), and trim each passage to its relevant sentences | Trimming is a prompt-side view only. Every kept sentence carries `(chunk id, start, end)` offsets into the **original** chunk text. Citation excerpts, heading paths and scoring against `expected-spans-v1.json` always use the original chunk and its offsets, never the trimmed text. Test: each trimmed sentence equals the original chunk text at its recorded offsets. |
| 2 | Plain text with `[n]` markers instead of JSON, streamed | Sentinel and degradation rules in §6.2. |
| 3 | Thinking mode off; cap on answer length | Measured against thinking on. |
| 4 | Show retrieved sources at once, stream the answer under them | GUI only; no effect on scores. |
| 5 | Fixed instructions first in the prompt, byte-identical on every request, so `llama-server` reuses its prompt cache | Passages and question come after the fixed part. |
| 6 | Score gate before the model; cache of answers to repeated questions | Cache key: normalised question + collection version + LLM model id + prompt version + retriever configuration. The collection version changes on every upload, re-ingestion or delete, so a changed collection never serves an old answer. Cloud and local answers never share an entry. |
| 7 | Small reranker, at most 20 candidates, truncated to about 256 tokens each | See §7.1. |
| 8 | Runtime settings: threads equal to physical cores, context of 4,096 tokens, one server slot, model kept loaded and unloaded after an idle period | Settings recorded in every run. |

Not planned:

- **Speculative decoding** (a small draft model proposes tokens that the main model verifies). A 0.6B draft model is
  about 0.5 GB and does fit in 8 GB; the reason to skip it is that the gain on CPU is small, because the draft
  model competes for the same cores. Revisit only if the benchmark script shows otherwise.
- **Any step that calls the model twice per question** (query rewriting, keyword translation) as a default.

## 7. Phase 2 and 3 — retrieval and ingestion

### 7.1 Phase 2 — hybrid search and reranking (month 3)

- **Keyword index: SQLite FTS5**, not `bm25s`. FTS5 supports inserting and deleting single documents, which
  incremental indexing needs, has BM25 ranking built in, and adds no dependency. Tokens as decided in §2.
- **Fusion:** Reciprocal Rank Fusion (k = 60), which needs no score normalisation between the two indexes.
- **Reranker:** a small multilingual cross-encoder. `bge-reranker-v2-m3` is about as large as `bge-m3`, which is
  already ruled out for the 8 GB default, and reranking 20 long chunks on CPU adds seconds. Benchmark a
  MiniLM-class multilingual reranker and a shorter candidate list first; record its memory and added latency.
- **Gate:** use the reranker's **absolute** relevance score. A threshold relative to the other results cannot detect
  "nothing relevant", because all scores are then similarly low. Calibrate on the expanded benchmark across both
  corpora, and keep the LLM's own refusal as the second layer.
- **Cross-lingual keyword search:** run BM25 on the original question by default. Having the LLM translate keywords
  first costs an extra generation call on CPU; test it as one ablation configuration, not as the default.
- **Ablation:** dense, sparse, hybrid, hybrid + rerank, on the expanded benchmark, reported per question type
  (English, Vietnamese, exact-identifier, unanswerable).

### 7.2 Phase 3 — general ingestion (months 4–5)

Strategy: everything becomes Markdown through MarkItDown, then one chunking path. This matches ADR-0002. The gaps to
close:

| Gap | Plan |
|---|---|
| PDF text has no headings and no page numbers, so header-aware chunking finds nothing to split on and heading-path citations are empty | Convert PDFs page by page, record page boundaries as character offsets, cite with `location_type="page"`. Slides: use the slide markers MarkItDown emits. |
| Scanned PDFs have no text layer | Detect near-zero characters per page; tell the user the file needs OCR. OCR itself is out of scope for the 8 GB default. |
| Vietnamese text | Normalise to Unicode NFC at ingestion and at query time. Detect legacy-font PDFs (TCVN3, VNI) that extract as garbage and warn. |
| Normaliser accepts only the web-export format | Add a generic normalisation path. The 24-document path stays byte-identical (§4.1). |
| Two disclosed gaps (post-clean-up skipped for converted formats; binary `.txt` read as text) | Fix both before any upload is accepted (AI_WORKLOG "with 7 more days", item 5). |
| Only `pdf` and `docx` extras installed | Add `pptx`. |
| Conversion happens in memory | Store the converted Markdown on disk keyed by file hash: stable citation offsets, no reconversion, and the user can see what was indexed. |
| Positional chunk ids, no delete | Chunk ids derived from file hash; `VectorStore.delete(source_id)`; the same delete in the FTS5 index. Re-ingesting a changed file removes its old chunks first. |
| Tables, formulas, multi-column layouts convert badly | Accept and disclose; add a per-document conversion-quality summary. |
| Text inside an uploaded file may contain instructions aimed at the model | Delimit passages clearly in the prompt, instruct the model to treat them as data, and add adversarial documents to the benchmark. |
| Indexing a textbook on CPU takes minutes | Background job with progress and cancel; the document is searchable only when complete. |

Collections: one per subject or course, each with its own vector collection and keyword index.

No ground truth exists for uploaded documents. For them the project reports conversion and retrieval sanity checks
only, never an accuracy figure.

## 8. Phase 4 and 5 — service and study features

### 8.1 Phase 4 — standalone release and optional local API (months 6–7)

**Standalone app first.** The product is the PySide6 app. It calls the application layer in-process through ports
such as `AskQuestionPort`, starts `llama-server` as a child process on first use, unloads it after an idle period,
and stops it on exit. Full Windows packaging (one-directory PyInstaller build) is done here for the standalone app.

**Local API as an optional mode of the same install**, off by default and enabled in settings. It exposes the same
use cases the GUI calls; it is not a separate product and holds no logic of its own.

- Every route is under `/v1`, so the two apps can be updated independently. A breaking change means `/v2`.
- **Discovery file:** when the API is enabled, the app writes its port and bearer token to a well-known per-user
  file (for example under `%LOCALAPPDATA%`), readable by the current user only, and removes it on exit. The Planner
  reads that file, checks `GET /v1/health`, and shows its assistant features only when the check passes. A stale
  file (app crashed) fails the health check and is treated as "not available".
- **Neither app depends on the other.** The Planner works with the assistant absent; the assistant works with the
  Planner absent. The Planner may offer to start the assistant if it is installed, but never requires it.

Agree the API contract with a mock server during Phase 3, before the Planner repository is available.

| Endpoint | Purpose |
|---|---|
| `POST /v1/collections`, `POST /v1/ingest` | Create a subject, add documents (asynchronous, with job status) |
| `POST /v1/search` | Hybrid search with no LLM call |
| `POST /v1/ask` | Grounded answer with citations, streamed as server-sent events, cancellable |
| `POST /v1/quiz`, `POST /v1/summarize`, `GET /v1/quiz-results` | Study features (Phase 5), including quiz results by topic for the Planner to schedule reviews |
| `GET /v1/health`, `GET /v1/models` | Status, API version, loaded models |

Process requirements:

- the API binds to `127.0.0.1` only, with a bearer token and a port chosen at start (no fixed port);
- `llama-server` exits when the app exits or crashes (Windows job object or parent-process watchdog), so no orphan
  process holds 1.5 GB;
- the LLM loads on first use and unloads after an idle period;
- one generation at a time, with a queue shared by the GUI and the API;
- one-directory PyInstaller build (single-file builds unpack on every start and trigger antivirus false positives
  more often).

The MCP server from the first draft is **cut**; it is not needed by either app.

### 8.2 Phase 5 — study features (months 8–10)

The features live in this project. Each is an application-layer use case with a screen in the PySide6 app, and the
same use case is exposed through the API so the Planner can use it when connected. In this order, cheapest on weak
hardware first:

1. **Syllabus mapping:** topic list in, matching passages and reading-time estimates out. Retrieval only.
2. **Quiz and flashcards with citations:** grammar-constrained JSON; needs its own small evaluation (is the question
   answerable from the cited passage, is the marked answer correct), because question generation is hard for a
   1.5–2B model. Export to Anki.
3. **Weak-topic tracking:** the app stores quiz results by topic and shows weak topics on its own screen. When the
   Planner is connected it reads the same results to schedule reviews; scheduling logic stays in the Planner.

### 8.3 Phase 6 — release (months 11–12)

Optional discrete-GPU offload, hardware auto-profile (measure RAM and VRAM, choose the model profile), optimisation, removal of
Gemini from the shipped product (§4.3), final report including the local-versus-cloud benchmark.

## 9. Timeline

| Month | Phase | Measurable result |
|---|---|---|
| 1 | 0 Foundations | Refactor reproduces EPIC-05 numbers; expanded benchmark frozen; measurement harness; packaging spike runs on a clean machine |
| 2 | 1 Local models | Embedder comparison (retrieval-only); LLM comparison (retrieval fixed); CPU against integrated GPU; memory and time to first token from one run on a real gen-10 / 8 GB machine; go/no-go |
| 3 | 2 Hybrid + rerank | Four-configuration ablation per question type; reranker-score gate calibrated |
| 4–5 | 3 Ingestion | Upload, per-subject collections, incremental index, page citations; conversion-quality report |
| 6–7 | 4 Standalone release + optional API | Packaged standalone app runs on a clean Windows machine; with the API enabled, the Planner discovers it and calls `/v1/search` and `/v1/ask`; each app verified working with the other absent |
| 8–10 | 5 Study features | Syllabus mapping, quiz with evaluation, weak-topic tracking, as screens in the app and through the API |
| 11–12 | 6 Release | GPU option, auto-profile, cloud removed from product, final report |

## 10. Changes from the owner's draft

| # | Owner's draft | This plan | Why |
|---|---|---|---|
| 1 | Latency stated as 10–15 tokens/s | Time to first token is a first-class metric; prompt size is budgeted | Prompt processing dominates on CPU |
| 2 | Phase 1 swaps embedder and LLM, then compares with Gemini | Two separate comparisons, same prompt on both providers | Otherwise the cause of a change is unknown |
| 3 | Gemini removed in months 11–12 | Removed from the product only; kept as development judge | A small local model cannot judge |
| 4 | Fallback to Gemini on local error or timeout | Opt-in, off by default, visibly indicated | Private documents would leave the machine silently |
| 5 | Vietnamese benchmark in months 4–5 | Benchmark expanded in month 1 | 36 questions cannot support the month-3 ablation |
| 6 | "Add an adapter and edit `composition.py`" | Phase 0 refactor first | Hard-coded arms and direct Gemini imports |
| 7 | Reranker score plus relative threshold | Absolute reranker score | A relative threshold cannot detect "nothing relevant" |
| 8 | `bge-reranker-v2-m3`, not in the RAM budget | Small multilingual reranker, memory and latency recorded | Too large for the 8 GB default |
| 9 | `bm25s` or FTS5 | FTS5 | Incremental insert and delete |
| 10 | LLM translates keywords for BM25 | Ablation configuration only | Extra generation call per question |
| 11 | MarkItDown for all formats | Same, with page-by-page PDF conversion and the gap list in §7.2 | PDFs lose headings and pages |
| 12 | Packaging in months 6–7 | Spike in month 1, full packaging in months 6–7 | Highest engineering risk |
| 13 | Quiz first among study features | Syllabus mapping first | Retrieval-only, cheap on weak hardware |
| 14 | Optional MCP server | Cut | Scope |
| 15 | Sections 2–4 describe Ollama and a 4B default | Single consistent description (llama-server, 1.5–2B default) | The draft's section 0 superseded them |
| 16 | Not mentioned | Go/no-go gate, chunk token-length check, NFC normalisation, prompt-injection defence, sidecar lifecycle, ADRs | Added by the review |

Second round (owner's feedback, 2026-11-10):

| # | Before | Now | Why |
|---|---|---|---|
| 17 | A local service called by the Planner | Standalone PySide6 app; the API is an optional mode of the same install, off by default | Each app must run on its own |
| 18 | Planner starts the service as a sidecar and is told the port | Discovery file with port and token; Planner degrades gracefully when the assistant is absent | Loose coupling |
| 19 | Unversioned routes | `/v1` prefix | The two apps are updated independently |
| 20 | Study features surfaced in the Planner | Screens in this app; same use cases through the API | Owner's decision |
| 21 | Packaging spike started from a C# console program | Spike bundles the standalone app | The standalone app needs a Windows bundle anyway |
| 22 | Measure on the 8 GB machine | Emulated target for relative numbers; one run of the benchmark script on a real gen-10 / 8 GB machine for the go/no-go | Owner's development machine is stronger than the target |
| 23 | Integrated GPU not considered | CPU against integrated GPU is a benchmark configuration | It may speed up prompt processing, the largest cost |
| 24 | Speculative decoding skipped as not fitting in 8 GB (said in review, not in this document) | Skipped because the gain on CPU is small; a 0.6B draft model does fit | Corrected reason |
| 25 | Passage trimming, answer cache and `[n]` format listed without conditions | Offset-mapping requirement, cache key with collection version, sentinel and degradation rules with tests (§6.2, §6.4) | Owner's feedback |

## 11. Open decisions

All **DECISION REQUIRED** (owner):

1. Size and composition of the expanded benchmark, and which Vietnamese documents form the second corpus.
2. Go/no-go thresholds for Phase 1 (§6.3).
3. Whether cloud answering survives as an opt-in mode if the small model fails the gate.
4. Whether OCR for scanned PDFs is in scope at all.

Decided 2026-11-10:

- The GUI stays in-process; the HTTP API is an optional mode (§8.1).
- An answer with no valid citation marker is shown with a notice and its retrieved sources, and counted as a
  citation failure; the strict replacement applies only if the missing-marker rate exceeds 10% (§6.2, §6.3).
