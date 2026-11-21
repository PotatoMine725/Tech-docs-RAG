# Report: local embedder benchmark, EmbeddingGemma 1 vs 2 (2026-11-21)

Phase 1 step 1 of `docs/plans/local-rag-upgrade-plan.md` (local embedder only, retrieval-only, no LLM call).
Raw results: `data/experiments/embedding-bench/20261121-191953/` (`results.json`, `summary.md`).
Scripts: `scripts/benchmark/embedding_bench.py`, `scripts/benchmark/download_embedding_models.py`.

## What was compared

| Model | ONNX build | Text parameters | Variants |
|---|---|---|---|
| EmbeddingGemma 1 (`gemma1`) | `onnx-community/embeddinggemma-300m-ONNX` @ `5090578d9565` | 300M | fp32, fp16, int8 (`model_quantized`, dynamic), int4 (`model_q4`, weight-only) |
| EmbeddingGemma 2 (`gemma2`) | `onnx-community/embeddinggemma-2-ONNX` @ `daa72c512439` | 270M (text graph only; vision/audio encoders not downloaded) | same four |
| Gemini baseline | `gemini-embedding-001@768`, vectors from `data/cache/embeddings.sqlite` (733/733 chunks, 36/36 queries cached, no API call) | n/a | n/a |

Held fixed: arm-A chunks (`embed_text`, 733 chunks, max 546 tokens, none truncated at 2048), the 32 answerable eval
questions (16 EN, 16 VI; the 4 unanswerable ones have no spans), prompts `title: none | text: ` / `task: search
result | query: `, and scoring: plain cosine top-k over all chunks, no dedup, no score gate, with the project's own
`section_hit_at_k`, `source_hit_at_k`, `reciprocal_rank`.

Checks on the harness:
- Re-scoring the recorded production run `20260928-eval-A-full-491f137` with the same metric calls reproduces its
  saved summary exactly (section/source hit @1/@3/@5).
- EmbeddingGemma 2 int4 reproduces the model card's worked example to three decimals (0.854 / 0.783 / 0.752 / 0.684),
  so feeding the text graph empty `image/video/audio_features` is the correct text-only call.
- No NaN, Inf or zero-norm vectors in any run.

## Retrieval quality

Section hit = every expected slot has a top-k chunk overlapping its expected section (lenient). MRR uses the first
chunk that hits any slot, so it saturates for Gemini.

| Model | Section@1 | @3 | @5 | @10 | Source@5 | MRR@10 | EN @1 / @5 | VI @1 / @5 |
|---|---|---|---|---|---|---|---|---|
| Gemini | 26/32 | 29 | 30 | 32 | 31 | 1.000 | 13 / 16 | 13 / 14 |
| gemma1 fp32 | 24/32 | 27 | 29 | 30 | 29 | 0.961 | 13 / 15 | 11 / 14 |
| gemma1 fp16 | 24/32 | 27 | 29 | 30 | 29 | 0.961 | 13 / 15 | 11 / 14 |
| gemma1 int8 | 24/32 | 27 | 29 | 30 | 29 | 0.959 | 13 / 15 | 11 / 14 |
| gemma1 int4 | 23/32 | 26 | 29 | 30 | 29 | 0.939 | 13 / 15 | 10 / 14 |
| gemma2 fp32 | 20/32 | 25 | 28 | 29 | 30 | 0.867 | 12 / 15 | 8 / 13 |
| gemma2 fp16 | 20/32 | 25 | 28 | 29 | 30 | 0.867 | 12 / 15 | 8 / 13 |
| gemma2 int8 | 20/32 | 25 | 28 | 29 | 30 | 0.867 | 12 / 15 | 8 / 13 |
| gemma2 int4 | 20/32 | 26 | 28 | 31 | 30 | 0.870 | 12 / 14 | 8 / 14 |

Against Gemini, case by case: gemma1 (every variant) loses 2 cases at @1 (Q-EVAL-008, -028; int4 also -016) and at
@5 wins 1 (-022) and loses 2 (-029, -032). gemma2 loses 6 cases at @1 and at @5 wins 2, loses 4.

Reading: with n = 16 per language, one or two cases is noise. gemma1 is within that margin of Gemini. gemma2 is
4 cases behind gemma1 at @1, almost all on Vietnamese questions (8/16 against 11/16); that gap is larger than noise
but rests on one 32-question set, so it is evidence, not proof.

## Precision fidelity (cosine to the same model's fp32)

| Variant | Doc cosine mean / min | Query top-5 overlap with fp32 |
|---|---|---|
| gemma1 fp16 | 1.0000 / 1.0000 | 0.99 |
| gemma1 int8 | 0.9893 / 0.9802 | 0.92 |
| gemma1 int4 | 0.9593 / 0.9358 | 0.88 |
| gemma2 fp16 | 1.0000 / 1.0000 | 1.00 |
| gemma2 int8 | 0.9999 / 0.9999 | 0.99 |
| gemma2 int4 | 0.9829 / 0.9764 | 0.87 |

fp16 gives the same vectors as fp32 and slightly more memory: the builds appear to store fp16 weights and compute
in fp32 on ORT's CPU provider (inferred from the numbers, not checked in the graph).

## Speed and memory

Machine: i7-12700H, 23.6 GB RAM, ONNX Runtime 1.32.0 (CPU provider) in a separate venv
(`E:\models\embeddinggemma\.venv-bench`; the project venv's ORT 1.20.1 cannot open gemma2 int8/int4).
`full` = all cores, ORT default threads, 733 chunks. `lowend` = pinned to 4 E-cores, 4 threads, 200 chunks.
Batch 8, length-sorted. Query latency = one question per call, 36 questions x 3, after warm-up.
Peak RAM = the process's peak working set (includes Python, NumPy and the tokenizer, about 35 MB at start).

| Model | Profile | Index chunks/s | Query p50 / p90 ms | Peak RAM MB |
|---|---|---|---|---|
| gemma1 fp32 | full / lowend | 10.7 / 2.3 | 29 / 37 · 106 / 146 | 977 / 933 |
| gemma1 fp16 | full / lowend | 9.7 / 2.1 | 33 / 41 · 113 / 167 | 1024 / 959 |
| gemma1 int8 | full / lowend | 8.7 / 2.1 | 124 / 133 · 245 / 285 | 1648 / 1643 |
| gemma1 int4 | full / lowend | 4.8 / 1.4 | 52 / 76 · 165 / 234 | 553 / 502 |
| gemma2 fp32 | full / lowend | 6.8 / 1.6 | 41 / 49 · 152 / 212 | 1736 / 1723 |
| gemma2 fp16 | full / lowend | 5.0 / 1.4 | 50 / 61 · 159 / 226 | 1788 / 1885 |
| gemma2 int8 | full / lowend | 5.3 / 1.4 | 204 / 218 · 497 / 589 | 1377 / 1375 |
| gemma2 int4 | full / lowend | 7.0 / 1.5 | 36 / 45 · 178 / 239 | 1289 / 1281 |

Observations, as measured:
- int8 (dynamic quantization) is slower than fp32 and, for gemma1, peaks higher in RAM during batch indexing, even
  though it is the smallest right after loading (149 MB working set against 552 MB for fp32). Not investigated.
- gemma1 int4 is the only build near the plan's embedder budget: about 0.5 GB peak, against about 1 GB for gemma1
  fp32 and 1.3-1.9 GB for every gemma2 build.
- Low-end indexing of all 733 chunks would take about 5-6 min (gemma1 fp32) to 9 min (gemma1 int4) at these rates.

Limits of the low-end emulation: E-cores only approximate a 4-core gen-10 CPU. The instruction set (INT8 speed depends
on VNNI, which Comet Lake lacks), memory bandwidth and the 8 GB RAM ceiling are not emulated. Treat the absolute
numbers as indicative and the ordering as the result; confirm on the real machine (plan Phase 1 gate).

## Outcome

- Best candidate from this run: **EmbeddingGemma 1**. Quality within noise of Gemini on both languages; fp32 is the
  fastest build, int4 halves memory for a one-case loss at @1.
- EmbeddingGemma 2 (text only) is slower, uses more memory, and retrieves worse on this corpus, mainly for Vietnamese
  questions. Not recommended here, despite its better published MTEB scores.
- int8 builds are not worth it on this CPU (slower, no memory saving under load).
- Not decided here (owner): fp32 vs int4 for gemma1 on the 8 GB target; whether to also run the plan's original
  candidate (`multilingual-e5-small`) under the same harness; production retriever settings (dedup, score gate) for
  the new embedder, which need re-tuning on the dev split.
