# ADR-0009 Local cross-encoder reranker (opt-in), MaxP windows, reranker gate PROVISIONAL

Date: 2026-11-26
Status: **Proposed** (owner decisions 2026-11-25 applied; default and gate need owner OK).
Refines: ADR-0006 (Reranker contract), ADR-0007 D6 (gate in hybrid/sparse mode, TBD until this step). Plan step 4b of
`docs/plans/local-rag-upgrade-plan.md` §7.1. Evidence: `docs/reports/2026-11-25-reranker-benchmark.md`.

## Context
Every evidence miss in the corpus-2 report was a ranking problem, and the dense-cosine gate cannot separate
answerable from unanswerable across domains (ADR-0007 amendment). The owner chose a reranker next, gated on its
absolute score, with the LLM refusal as second layer.

## Decision
- **D1 Provider.** `infrastructure/rerank/onnx_cross_encoder.py`: ONNX Runtime CPU, lazy load, fp32 / int8, no
  download by the app (`RERANK_MODEL_DIR` points to an existing export). `RERANK_PROVIDER` = `none` (default) |
  `cross-encoder`. Score = sigmoid(logit), a fixed 0..1 scale; the `Reranker` contract gains `absolute_scores`
  (true here, false for `none`, which is then never called).
- **D2 Passages: sliding windows + MaxP, no head cut** (owner). The question is cut to 128 tokens; each pair is at
  most `RERANK_MAX_TOKENS` = 512 tokens (and the model's positions), windows overlap by 128, the passage score is its
  best window. Reason: chunks are longer than 256 tokens (corpus 2 median 394) and a head cut hid the evidence.
- **D3 Retriever.** With a reranker, the retriever keeps its best `RERANK_CANDIDATES` unique passages, reranks them
  (heading path + passage body) and returns the top_k by reranker score; `rerank_score` = reranker top-1. Evaluation
  runs record `rerank_model` and `rerank_candidates`.
- **D4 Default off; opt-in "high quality" mode: bge-reranker-v2-m3 int8, K = 10** (`RERANK_CANDIDATES` default 10).
  By the pre-registered rule, K is the largest of {20, 15, 10} within 2 s on the low-end profile; both candidates
  are over 2 s even at K = 10 (gte 5.6 s, bge-m3 13.8 s median), so the default ships off. bge-m3 is the opt-in
  choice: its @5 totals are never below `none` on local hybrid (v1 27 vs 26 with 1 lost / 2 gained), @1 on corpus 2
  41 vs 31 (p = 0.006), @1 on corpus 1 slightly lower. Not recommended with the Gemini dense embedder (lower @1 and
  @5 on v1). The model choice and "local only" were made on eval results (not pre-registered): provisional.
- **D5 Gate: PROVISIONAL, unchanged.** The gate keeps reading the dense top-1 cosine (0.686 / 0.5417). A reranker
  threshold is set on dev only; pooled dev scores overlap for both models (DECISION REQUIRED) and dev has 9
  answerable cases. A usable value needs 15-20 new owner-approved dev questions; the frozen eval sets are untouched.
- **D6 Models.** Compared: gte-multilingual-reranker-base and bge-reranker-v2-m3 (onnx-community exports, pinned
  commits; Apache-2.0 originals, the exports carry no license tag). mMiniLM (mmarco) dropped: worse on corpus 1 where
  the cut was not the cause; also trained on mMARCO, a translation of MS MARCO, whose terms are non-commercial.
  bge-m3's training mix includes bge-m3-data (whether it holds MS MARCO: TBD).

## Consequences
- With `RERANK_PROVIDER=none` nothing changes (the reranker is not called; RERANK_* settings are not even read).
- The opt-in mode costs about 1.6 GB RAM and seconds per question; the GUI should label it slow (TBD with the GUI).
  The GUI caches one answer service per arm and each builds its own reranker, so using both arms loads the model
  twice (about 2 × 1.6 GB); sharing one instance is a small wiring change (TBD if the mode is kept).
- Open: Gemini v2 (quota, TBD); gte's 2.1 GB peak (TBD); reranker gate value (needs new dev questions); a smaller
  long-input multilingual cross-encoder within 2 s (owner to name candidates).
