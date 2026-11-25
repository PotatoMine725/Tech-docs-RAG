# Reranker benchmark, retrieval only (plan §7.1 step 4b, ADR-0009)

Date: 2026-11-25. Status: **pre-registered, not run yet**. This section was committed before any speed or quality
number of the configuration below existed; the results are appended under it, never edited into it.

## 1. Pre-registered procedure (owner decisions 2026-11-25)

- **Models:** `Alibaba-NLP/gte-multilingual-reranker-base` (onnx-community export @ee64367) and
  `BAAI/bge-reranker-v2-m3` (onnx-community export @6f5ff65): multilingual cross-encoders that read long input.
  mMiniLM (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) is **dropped**: in the exploratory run (§3) it was worse than
  no reranker on corpus 1, where the passage cut was not the cause, so it is a limit of the model itself.
- **Variant: int8 only.** fp32 is excluded before measuring: its file alone (gte 1,200 MiB, bge 2,166 MiB + graph) is
  over the ~0.5 GB reranker budget of the brief.
- **Passage handling: sliding windows + MaxP, no head cut.** Question cut to 128 tokens; each (question, window) pair is
  at most 512 tokens, so a window is 512 − question − 4 special tokens long; consecutive windows overlap by 128; the
  passage score is its best window's sigmoid(logit). Text: heading path + blank line + link-stripped passage body.
  Nothing about window length is chosen on the test set.
- **Candidates:** the retriever's best K unique passages, embedder's best current mode, Arm A (local: hybrid; Gemini:
  dense). The reranker's top 5 replace the retriever's top 5.
- **K is chosen on speed only**, before any accuracy is computed: per model, the largest K in {20, 15, 10} whose
  median latency per question is <= **2 s** on the low-end profile (4 efficiency cores of the i7-12700H pinned, 4
  intra-op threads, a stand-in for a 4-core Intel gen-10 laptop), measured on the dev questions (v1 + v2, local
  hybrid candidates). Batch size 8. Nothing else runs on the machine during the low-end pass.
- **Eval: exactly one run per model** at its K (full profile, every case of v1 eval, v2 eval corpus 1 + 2, and dev).
  Any other configuration reported is labelled "exploratory, chosen on test".
- **If K = 10 is still over 2 s for a model:** its eval still runs (to know the quality), the default ships **off**
  (`RERANK_PROVIDER=none`), the reranker becomes an opt-in "high quality" mode, and the report states the real latency.
- **Metrics:** evidence_hit@1 and @5 (headline @5), section MRR@5, per pool (v1 eval; v2 corpus 2 A-D; v2 corpus 1 E),
  per category / language / typing; paired exact McNemar against `none` (the production retriever, TOP_K=5), raw p.
  Peak working set and added RAM per model on the low-end profile.
- **Gate:** absolute reranker top-1 (sigmoid), set on **dev only** (dev v1 + v2), rule of retrieval-spec.md (lowest
  answerable − 0.05). Dev has 9 answerable cases (local), so the value stays **PROVISIONAL**. A reliable value needs
  15–20 new dev questions approved by the owner; the frozen eval sets are not touched.
- **Gemini:** v1 only. Gemini v2 has no corpus-2 index and uncached queries (quota): **TBD**.

## 2. Results

TBD (appended after the runs).

## 3. Exploratory run before the procedure (head cut, chosen before the owner decisions)

mMiniLM int8, each passage cut to its first 256 tokens, 20 candidates: worse than no reranker. Local hybrid A,
evidence_hit@5: v1 26/32 → 21/32 (p=0.062), v2 corpus 2 48/52 → 39/52 (b=9, c=0, p=0.004), E 10/10 → 9/10; Gemini dense
v1 30/32 → 21/32 (p=0.012). Cause on corpus 2: chunks are longer than 256 tokens (median 394; 83% exceed 256) and in
8 of the 9 lost cases at least one required quote starts after token 256 in its chunk (in 7, every quote does). On
corpus 1, 3 of the 16 lost cases (local v1 5, local v2-E 1, Gemini 10) have one quote past token 256; in the other 13
every quote lies within the first 256 tokens and the model still ranks a required chunk below 5th.
Ceiling of the candidate list (evidence_hit@5 if the best 5 of 20 were chosen; local v1 / v2 corpus 2 / E, Gemini v1):
31/32, 49/52, 10/10, 32/32, against `none` 26, 48, 10, 30. Run folder `data/experiments/rerank-bench/20261125-run1`
(git-ignored), candidates at commit c9dba7b with uncommitted reranker code; these numbers are exploratory only.
