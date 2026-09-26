# VERIFY RAG-001b

Verifier session, 2026-09-26 (14:40–14:50 UTC+7), Windows 11, `.venv` Python 3.13.3. Reviewed branch `rag-001b` at `3cad4fe` (PR #10 into `dev`, merge base `f81faa5` = `origin/dev`).

**Quota rule: zero Gemini requests were spent.** No build, index or sanity script was run. The Chroma store and the embedding cache were opened read-only. `.env` was not opened or printed.

## Verdict: ACCEPT

0 FAIL. 1 partly UNVERIFIED by the verifier (check 9, full-key and prefix scan; see the row).

## Checks

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Scope | PASS | `git diff dev...rag-001b --stat`: 29 files, none under `corpus/` or `data/evaluation/`. eval-v1 `3436870e…2937` and dev-v1 `37d349e5…21d6` unchanged. `data/cache/` and `.env` are git-ignored (`.gitignore:234`, `:223`); `data/chroma/*` is ignored (`.gitignore:227`), only `data/chroma/.gitkeep` is tracked. Non-task doc edits: the GitNexus stats line in `CLAUDE.md` and `AGENTS.md`. |
| 2 | Chunk inputs | PASS | `arm-a.jsonl` `9c3bcc6c…`, `arm-b.jsonl` `2bde1a0e…`. |
| 3 | Store | PASS | Exactly 2 collections: `kb_header-1600_gemini-embedding-001-768` (733) and `kb_fixed-1600_gemini-embedding-001-768` (859). Metadata `hnsw:space=cosine` and HNSW configuration `space=cosine`. Stored ID sets equal the JSONL `chunk_id` sets. 20 sampled vectors per arm: 768 dims, L2 norm 1.0 (tolerance 1e-3). All records (not only 10) compared with the JSONL: document = `embed_text`, metadata incl. `display_text` and JSON `heading_path` match, 0 mismatches of 733 and 859. |
| 4 | Duplicate texts | PASS (advisory) | See "Duplicates" below. |
| 5 | Cache | PASS | 1,569 rows = 1,568 `document` + 1 `query` (the sanity probe), all `gemini-embedding-001@768`, 768 dims. Key = `sha256("model_id\|task\|text")`, all 64 hex characters; the table has no key column. |
| 6 | Step 0 | PASS | `test_caching_embedder_conforms_to_the_core_embedder_protocol` compares members and signatures; `test_core_embedder_protocol_has_no_batching_detail` pins `{model_id, embed}`. `test_the_key_is_redacted_from_the_logged_429_body` asserts the key and a second key-shaped string are absent and `[REDACTED]` present. No real 429 occurred, so the logging is proven by a fake only. |
| 7 | Quota accounting | PASS | Arm A 6 + 709 + 1 = 716; Arm B 859; rebuild 0. Report, worklog, ledger and PR description agree. |
| 8 | Docs | PASS | ADR-0005 D16, the report and EPIC-03 say `data/chroma/`. `D:\ChromaDB` appears only as history (report lines 144–217, OD-7 decision text, `tech-stack.md` "was", earlier task files). |
| 9 | Key scan | PASS for `AIza+35`; full-key and prefix by executor | AIza+35 pattern scan 0 matches (covers any Gemini key format) over `data/chroma`, `data/cache`, `data/logs`, `validation/` and all tracked files (341 files); full-key/prefix scan done by the executor, 0 matches. The 27 plain `AIza` hits are documentation and the redaction regex. The verifier could not scan for the full key or prefix without opening `.env`. |
| 10 | Offline tests | PASS | Branch: 211 passed, 1 deselected. `origin/dev` (`f81faa5`): 186 passed, 1 deselected. Delta +25 = the PR claim. |
| D | Layers | PASS | No `chromadb`, `google.genai` or `PySide6` in `core/` or `application/`. |

## Duplicates (check 4)

Arm A: 733 chunks, 709 unique `embed_text`; 11 duplicated texts, 24 extra copies. Arm B: 859 unique.

| Doc | Groups | Copies | Sections (length in characters) |
|---|---|---|---|
| 17 Integration tests in ASP.NET Core | 8 | 5,4,4,4,4,3,3,2 | Integration tests sample (657); Test app prerequisites (781); Customize WebApplicationFactory (519 and 1,163); Customize the client with WithWebHostBuilder (1,134); Inject mock services (764); Basic tests with the default WebApplicationFactory (1,082); Additional resources (786) |
| 23 Routing in ASP.NET Core | 2 | 2,2 | Routing concepts > URL matching (1,070 and 1,155) |
| 13 Handle errors in ASP.NET Core | 1 | 2 | Problem details > Customize problem details (736) |

**Origin:** the source text. Copies share the heading path and text but differ in `chunk_id` and `char_start`; for example `17:header-1600:0111` at 150411 and `17:header-1600:0121` at 193293. Doc 17 is 258 KB and has 6 "Additional resources" headings and 5 "Integration tests sample" headings, i.e. the page was captured with repeated sections. The chunker is faithful to the text.

**Effect on retrieval (advisory for RAG-002):** yes, duplicates can take several slots in the same top-k. Identical text gives an identical vector and score, and `chroma_store.py` does not deduplicate. A doc 17 query can fill top-5 with copies of one section, which distorts Recall@k and MRR and crowds out context for the answer. RAG-002 should dedupe by `content_hash` at retrieval time (or at least report it).

## Findings

- No defect fails a requirement.
- Minor: the execution report line 149 ("did not … re-index into `data/chroma/`") was superseded by the rebuild at line 152. Fixed in the closing commit by a "(superseded …)" note; the original text is kept.
- Observation: the daily-429 path and the first-429 log are proven only against fakes (no real 429 has happened); the owner already accepted this as an open item.
