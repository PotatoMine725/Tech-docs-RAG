# ADR-0007 Keyword index (SQLite FTS5) and hybrid retrieval with Reciprocal Rank Fusion

Date: 2026-11-23
Status: Accepted (owner, 2026-11-23: keep Gemini as the default embedder; next step hybrid search, then re-measure).
D3, the tokenizer, is **PROVISIONAL** (owner decision 2026-11-23). D6, the gate in hybrid/sparse mode, is
**TBD until the reranker step**.
Refines: ADR-0005 (index storage), ADR-0006 (Reranker contract, not wired yet). Plan step 4a of
`docs/plans/local-rag-upgrade-plan.md` §7.1. The reranker (step 4b) is out of scope here.

## Context
Local dense retrieval is behind Gemini (`docs/reports/2026-11-23-local-reindex.md`). The plan's next lever is keyword
search fused with dense search. The keyword index must support inserting and deleting single documents (incremental
ingestion, plan §7.2) and must not add a dependency.

## Decision
- **D1 Engine: SQLite FTS5** through the standard-library `sqlite3` (SQLite 3.49.1 in the project venv, FTS5 built
  in). No new package. FTS5 has BM25 ranking (`bm25()`) and row-level insert/delete. `bm25s` was rejected in the plan
  (§10 item 9) because it has no incremental update. SQLite and FTS5 are outside the stack locked in CLAUDE.md rule 2,
  which this change amends: SQLite is now used for the embedding cache **and** the keyword index.
- **D2 Contract and storage.** `core/interfaces/keyword_index.py` `KeywordIndex` is a separate contract from
  `VectorStore` (upsert, `delete_source(source_id)`, `search(query, top_k)`, `count`, `get_ids`). The implementation is
  `infrastructure/keyword_index/fts5_index.py`. There is one file per arm, `data/keyword/kw_<chunker config>.sqlite`
  (`KEYWORD_INDEX_DIR`, git-ignored). It is keyed by the chunker config like the Chroma collection, but not by the
  embedder: BM25 needs no vector, so the gemini and embeddinggemma runs of an arm share it. The indexed text is
  `embed_text`, the same text the dense index embeds. The other chunk fields are stored UNINDEXED, so a search returns
  whole chunks. A `meta` table holds the chunker config, the tokenizer, the normalizer id and the schema version. They
  are checked on open, so a mismatch raises `KeywordIndexError` (a `VectorStoreError`). `build_index.py` builds the
  keyword index first, from the same chunk file and with the same resume rule (chunk_ids already present are
  skipped). It needs no quota and no model.
- **D3 Tokenizer: PROVISIONAL.** `unicode61 remove_diacritics 0` on the original text: words of letters and digits,
  case folded, diacritics **kept**. Tokenization lives only in the FTS5 module (`TOKENIZER` and a `normalize` step
  applied to both the indexed text and the query, identity for now). A later change touches no caller.
  - Why keep diacritics now (owner decision 2026-11-23). With 2, Vietnamese syllables merge ("thể", "thế" → `the`, which
    is also an English stop word). With 1, SQLite leaves letters with stacked marks unfolded and folds others, which
    is inconsistent for Vietnamese. Probe on SQLite 3.49.1:

    | input | `remove_diacritics 0` | `1` | `2` |
    |---|---|---|---|
    | kiểm, một, dẫn | kiểm, một, dẫn | kiểm, một, dẫn | kiem, mot, dan |
    | thể, thế | thể, thế | thể, thế | the, the |
    | đường, được | đường, được | đuờng, đuợc | đuong, đuoc |
    | cách, hàm, không | cách, hàm, không | cach, ham, khong | cach, ham, khong |
    | C#, .NET, Task.Run, max_tokens | c, net, task, run, max, tokens (all modes) | | |

    `đ` is a letter, not a diacritic, and is never folded. `#`, `.`, `_` separate tokens. A snake_case query word is
    quoted, so it matches as a phrase (`max_tokens` → "max tokens").
  - **Target design, TBD / DECISION REQUIRED:** plan §2 (owner): Vietnamese syllable + bigram tokens, plus a
    diacritic-stripped copy of the index. It will be implemented and measured once the benchmark has Vietnamese
    documents and questions, including questions typed without diacritics. **The current corpus is English only, so
    no Vietnamese tokenization choice can be validated on it**; D3 is not evidence for or against the target design.
- **D4 Query.** BM25 runs on the original question (no translation, plan §7.1). The question is never passed raw to
  MATCH (FTS5 syntax would reject `?`, `"`, `:`, `-` or read AND/OR/NOT as operators). Its distinct word tokens are
  each quoted and joined with OR, so a chunk with any question word matches and BM25 ranks them. An implicit AND
  would match almost nothing for a Vietnamese question over the English corpus. Order: `bm25()` ascending, then
  chunk_id. The exposed score is `-bm25` (higher = better), comparable only within one search.
- **D5 Fusion: Reciprocal Rank Fusion, k = 60** (`RRF_K`, Cormack et al. 2009; plan §7.1). It needs no score
  normalisation between cosine and BM25. `RETRIEVAL_MODE` = `dense` (default) | `sparse` | `hybrid`. Hybrid fetches
  N = `top_k + overfetch` = 5 + 10 = **15** from each index (the same fetch size dense already used) and scores each
  chunk sum(1 / (60 + rank)) over the lists that hold it. Ties are broken by chunk_id. The existing passage dedup then
  runs on the fused list and cuts it to top_k. Dense mode is byte-for-byte the old behaviour, and it never opens the
  keyword index.
- **D6 Gate: TBD until the reranker step.** RRF scores are rank-based (with k = 60 and two lists, at most
  2/61 ≈ 0.033, whatever the relevance) and BM25 is unbounded, so neither can say "nothing relevant". In every mode the retriever embeds the question, runs the dense
  search and reports `gate_score` = the dense top-1 cosine of the active embedder. The OD-9 gate compares that score
  with the provider's threshold (gemini 0.686, embeddinggemma 0.5417). Sparse mode embeds the question for the gate
  only. Records keep `top1_score` = this gate score in every mode; it equals rank 1's score in dense mode as before.
  The fused or BM25 scores stay in `retrieved[i].score`. Consequence: in hybrid mode the gate can refuse a question
  whose fused top 5 is good, or pass one whose fused top 5 is poor. The plan's fix is the reranker's absolute score
  (step 4b).
- **D7 Run identity.** `RunConfig` records `retrieval_mode` and `rrf_k`. A manifest written before this ADR has neither
  key and is read as `dense` / 60, so recorded runs still resume. The runner refuses a retriever whose mode differs
  from the run's.

## Consequences
- The default (dense) behaviour and every recorded run are unchanged; switching mode needs no re-embedding.
- `scripts/evaluation/compare_retrieval_runs.py` shows the mode, the cases that ended in an error (a sparse run whose
  question shares no word with the index) and a per-language table.
- The desktop app calls one retriever from any thread-pool worker. The FTS5 connection is therefore opened with
  `check_same_thread=False`, and every statement holds one lock (tested from several threads). Hybrid/sparse in the
  GUI has not been tried by hand.
- Memory/latency on the 8 GB target: not measured in this step (TBD with the reranker, plan §2 RAM budget).
- Sparse rankings do not depend on the embedder. The gemini and the embeddinggemma sparse runs differ only in the
  gate column.
