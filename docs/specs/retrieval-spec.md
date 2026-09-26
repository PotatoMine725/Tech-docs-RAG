# Retrieval specification

Status: decided for RAG-002 (2026-09-26). Code: `application/retrieval/retrieve.py`; settings in `config.py`
(`get_retrieval_settings`).

## Known facts
- Retrieval operates on chunks from the header-aware chunker (baseline); results carry heading-path citation info.
- Must let the system report insufficient information when nothing relevant is retrieved (OD-9 below).

## Requirements
- **Query.** The question is embedded with `EmbeddingTask.QUERY` (`RETRIEVAL_QUERY`, ADR-0004 D10) through the
  embedding cache, so a repeated question costs no quota. Similarity is cosine; `score = 1 - distance` (ADR-0005 D17).
- **top-k = 5** for both arms (ADR-0003 D7), `TOP_K`.
- **Dedup (RAG-002 addendum 1; owner decision 2026-09-26 on the key).** Fetch `top_k + 10` hits (`RETRIEVAL_OVERFETCH`),
  order them by (score descending, `chunk_id` ascending), keep the first hit of each `passage_hash`, cut to `top_k`,
  and number the ranks 1..k again. Same rule for both arms.
  - `passage_hash` = SHA-256 of the passage body: the link-stripped chunk text the LLM sees (`embed_text` without its
    contextual heading line). `content_hash` (hash of the raw `display_text`) is unchanged and not used here: in Arm A,
    doc 17 (19 extra copies), doc 23 (2) and doc 13 (1) repeat sections whose text differs only in a link URL, so their
    content hashes differ while their passages and vectors are identical. Arm A: 13 passages in > 1 chunk, 26 extra
    copies (by `content_hash`: 2). Arm B: 0. List: `validation/generation/rag-002-dev-2026-09-26.md`.
  - The kept hit carries `duplicate_chunk_ids`: the chunk IDs it replaced (on `RetrievedChunk`).
  - `duplicates_dropped` (per query, on `RetrievalResult` and `AnswerResult`) = number of over-fetched hits dropped as
    duplicates, including drops whose kept hit falls outside the top k.
  - Known effect: which copy is kept depends on the score (lowest `chunk_id` on a tie). For the doc 12/13 pair, the
    kept copy may be the one a case lists as an alternate rather than as expected.
- **Proposed for EVAL-003b (not implemented; the owner decides in 09b):** a kept chunk counts as overlapping an
  expected span if it or any chunk in its `duplicate_chunk_ids` overlaps it (identical content = same retrieval).
  The metric code is unchanged in RAG-002.
- **Errors.** An empty store result raises `RetrievalError`.

## OD-9 "insufficient information" rule (decided 2026-09-26, RAG-002)
Two layers:
- (a) **Retrieval gate:** if the top-1 score (after dedup) < `INSUFFICIENT_SCORE_THRESHOLD`, the LLM is not called;
  `insufficient_reason = "retrieval_gate"`.
- (b) **LLM layer:** the model answers `"insufficient": true` → `insufficient_reason = "llm"` (generation-spec.md).

**Threshold = 0.686**, used for both arms. Tuned on the dev set only (`dev-v1.jsonl`, never the eval set), Arm A.
Rule: threshold = (lowest top-1 score among answerable dev cases) − 0.05, so the gate never refuses an answerable dev
question; the LLM layer handles the rest.

| case | language | answerable | Arm A top-1 | (Arm B top-1, information only) |
|---|---|---|---:|---:|
| Q-DEV-001 | en | yes | 0.7360 | 0.7284 |
| Q-DEV-002 | vi | yes | 0.7943 | 0.7882 |
| Q-DEV-003 | en | yes | 0.7737 | 0.7646 |
| Q-DEV-004 | vi | yes | 0.7548 | 0.7256 |
| Q-DEV-005 | en | no | 0.6741 | 0.6714 |
| Q-DEV-006 | vi | no | 0.6710 | 0.6707 |

- 0.7360 − 0.05 = 0.6860. At this value the gate refuses both unanswerable dev cases and no answerable one.
- **EN vs VI** (questions in Vietnamese, documents in English): answerable top-1 EN 0.7360, 0.7737; VI 0.7943, 0.7548.
  VI is not systematically lower here. One threshold for both languages (no per-language tuning).
- **Caveat: n is small** (6 cases, 2 answerable per language). The margin between the lowest answerable (0.7360) and
  the highest unanswerable (0.6741) score is 0.06; eval questions may fall on either side. The evaluation reports how
  often the gate fires, per arm, so a wrong gate is visible.
