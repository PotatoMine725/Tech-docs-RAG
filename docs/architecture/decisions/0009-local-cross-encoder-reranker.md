# ADR-0009 Local cross-encoder reranker (opt-in), MaxP windows, reranker gate PROVISIONAL

Date: 2026-11-26
Status: **Accepted** (owner decisions 2026-11-26, D7): merged as infrastructure, default `none`; the opt-in mode is
**EXPERIMENTAL / PROVISIONAL**; the gate stays PROVISIONAL on the dense score.
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
  A window is cut on the passage's own tokens but the pair tokenizes it afresh, so its boundary tokens can come out a
  token or two longer: such a pair is cut back at the window's end and never exceeds the limit (2026-11-26; pairs that
  fit are untouched; evidence and scope: report §4).
- **D3 Retriever.** With a reranker, the retriever keeps its best `RERANK_CANDIDATES` unique passages, reranks them
  (heading path + passage body) and returns the top_k by reranker score; `rerank_score` = reranker top-1. Evaluation
  runs record `rerank_model` and `rerank_candidates`.
- **D4 Default off; opt-in "high quality" mode (EXPERIMENTAL / PROVISIONAL): bge-reranker-v2-m3 int8, K = 10, local
  embedder only** (`RERANK_CANDIDATES` default 10).
  By the pre-registered rule, K is the largest of {20, 15, 10} within 2 s on the low-end profile; both candidates
  are over 2 s even at K = 10 (gte 5.6 s, bge-m3 13.8 s median), so the default ships off. bge-m3 is the opt-in
  choice: its @5 totals are never below `none` on local hybrid (v1 27 vs 26 with 1 lost / 2 gained), @1 on corpus 2
  41 vs 31 (p = 0.006), @1 on corpus 1 slightly lower. Not recommended with the Gemini dense embedder (lower @1 and
  @5 on v1). The model choice and "local only" were made on eval results (not pre-registered): provisional.
- **D5 Gate: PROVISIONAL, unchanged.** The gate keeps reading the dense top-1 cosine (0.686 / 0.5417). A reranker
  threshold is set on dev only; pooled dev scores overlap for both models (DECISION REQUIRED) and dev has 9
  answerable cases. No dev questions are added now (owner, 2026-11-26, D7); the frozen eval sets are untouched.
- **D6 Models.** Compared: gte-multilingual-reranker-base and bge-reranker-v2-m3 (onnx-community exports, pinned
  commits; Apache-2.0 originals, the exports carry no license tag). mMiniLM (mmarco) dropped: worse on corpus 1 where
  the cut was not the cause; also trained on mMARCO, a translation of MS MARCO, whose terms are non-commercial.
  bge-m3's training mix includes bge-m3-data (whether it holds MS MARCO: TBD).
- **D7 Owner decisions, 2026-11-26.**
  1. Merge the reranker as infrastructure. The default stays `RERANK_PROVIDER=none`.
  2. The opt-in mode is bge-reranker-v2-m3 int8, K = 10, local embedder only, labelled **EXPERIMENTAL / PROVISIONAL**:
     it was chosen on eval results, not by the pre-registered rule. Reasons: latency on a weak machine (bge-m3 13.8 s
     per question, gte 5.6 s, both at K = 10 on the low-end profile) and +1.6-2.1 GB RAM (bge-m3 1.6, gte 2.1) are
     over budget; there is no @5 gain; there is only an @1 gain, on corpus 2.
  3. `RERANK_CANDIDATES` = 10 (chosen by the speed rule) and `RERANK_BATCH_SIZE` = 8 stay.
  4. The gate stays PROVISIONAL on the dense score. No dev questions are added now. Gate re-calibration moves to the
     local LLM step, where the LLM refusal is the second gate layer.

## Consequences
- With `RERANK_PROVIDER=none` nothing changes (the reranker is not called; RERANK_* settings are not even read).
- The opt-in mode costs about 1.6 GB RAM and seconds per question; the GUI should label it slow (TBD with the GUI).
  The GUI builds ONE reranker and both arms share it (fixed 2026-11-26 in `presentation/desktop/wiring.py`: before,
  each arm's answer service built its own, so using both arms loaded the model twice, about 2 × 1.6 GB). The
  reranker is created at app start like the LLM and the embedder (its model still loads on the first rerank), so a bad
  `RERANK_*` value now fails at start, not on the first question.
- `scripts/evaluation/run_eval.py` in full mode builds two retrievers per arm (one in `open_services`, one inside
  `build_answer_service`); `open_services` now creates ONE reranker and passes it to both, so with reranking on the
  model loads once per process (2026-11-26, owner-requested; with `none` nothing changes). `scripts/ask.py` serves one
  arm per process and is not affected.
- Open: Gemini v2 (quota, TBD); gte's 2.1 GB peak (TBD); reranker gate value (moves to the local LLM step, D7); a
  smaller long-input multilingual cross-encoder within 2 s (owner to name candidates).
