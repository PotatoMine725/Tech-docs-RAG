# Reindex with the local embedder (plan step 3), 2026-11-23

What happened when the corpus was re-indexed with EmbeddingGemma v1 (FP32, 768 dims, ADR-0006). The gate threshold
was re-tuned and the local embedder's retrieval was compared with the recorded Gemini runs. Retrieval mode only: no LLM
was called and no full-mode run was made.

Embedder: `embeddinggemma-300m-5090578d-fp32-t2048@768`, ONNX Runtime 1.20.1 (project venv), CPU, `threads=0`,
batch size 8. Code: commit `4937f03` (branch `reindex-local`).

## 1. Indexing speed: length-sorted batches

The app batched texts in input order, so each batch was padded to its longest text. The benchmark
(`embedding_bench.py`, `encode_all`) sorted by token count first. All runs below embed arm A's 733 chunks from an empty
temporary cache on the owner's machine, through `CachingEmbedder`. Each starts after a 2-text warm-up and measures
embedding only (no Chroma writes).

| run (time order) | batching | seconds | texts/s |
|---|---|---:|---:|
| 1 | input order (code before this change) | 141.6 | 5.18 |
| 2 | sorted by character length (first attempt) | 112.5 | 6.52 |
| 3 | benchmark script itself, `gemma1 fp32 full` (reference) | 91.1 | 8.05 |
| 4 | sorted by token count (committed) | 90.8 | 8.08 |
| 5 | sorted by character length, repeated | 106.9 | 6.85 |

- Runs 3–5 ran back to back. Token-count sorting matches the benchmark (8.08 vs 8.05 texts/s), and character-length
  sorting does not (6.85), so the committed plan sorts by token count.
- Unsorted → token-sorted: 5.18 → 8.08 texts/s (+56%). Runs 1 and 4 were about 8 minutes apart and the machine was
  not idle (a browser was running), so the gain is an estimate, not a controlled measurement.
- The benchmark recorded 9.66 texts/s on 2026-11-21 under the same ORT 1.20.1. Today it gave 8.05, so the machine is
  slower today. The ~10.7 figure in the task came from ORT 1.32 in the benchmark venv, not the project venv.
- 89 embed calls for 733 texts: identical chunk texts are embedded once (cache dedup).

Contract (`CachingEmbedder`): each planned group is still one embed call, committed before the next, and results come
back in input order. What changed: groups may now come in any order, as long as every missing text is in exactly one
group (a dropped or repeated text still raises `EmbeddingError`). Unit tests cover the sorted plan, input-order output,
less padding, a reordered plan, and resume after a crash mid-plan.

## 2. Arm B local index

`build_index.py --arm B`: 859 chunks embedded and stored, `store.count() = 859 = lines in arm-b.jsonl` (MATCH), 156.65 s
including model load and Chroma upserts (5.48 texts/s; arm B chunks are longer, est. 307K tokens). Collection
`kb_fixed-1600_embeddinggemma-300m-5090578d-fp32-t2048-768`. Arm A (733) was already built; the dry run shows 733/733
present.

## 3. Gate threshold

Per provider now (`config.GATE_THRESHOLDS`, `INSUFFICIENT_SCORE_THRESHOLD` overrides): gemini 0.686, embeddinggemma
**0.5417**. Tuning table and notes: `docs/specs/retrieval-spec.md` (OD-9).

- Rule: dev only, Arm A, lowest answerable top-1 (0.5917, Q-DEV-004) − 0.05.
- No overlap on dev. The highest unanswerable top-1 is 0.5869 (Q-DEV-005), only 0.0048 below the lowest answerable;
  Gemini's gap was 0.06. Q-DEV-005 passes the gate (left to the LLM layer); Q-DEV-006 is refused.
- **Owner note (not marked DECISION REQUIRED, since the scores do not overlap):** with this narrow a gap, the rule
  refuses few unanswerable questions. Changing the rule is the owner's call. It must not be tuned on eval.

## 4. Retrieval: local vs Gemini

Every number below comes from `scripts/evaluation/compare_retrieval_runs.py` over the recorded run folders, using the
EVAL-003b scoring code. Duplicates are resolved through the arms' full chunk files. Run on the Gemini runs, the script
reproduces the recorded `summary-20260928-eval-A-full-491f137-20260928-eval-B-full-491f137.json` exactly.

Runs: Gemini `20260928-eval-{A,B}-full-491f137` (full mode, retrieval fields only; no Gemini eval run was recorded in
retrieval mode) and local `20261123-{dev,eval}-{A,B}-retrieval-local-4937f03`.

### Eval split (32 answerable, 4 unanswerable)

| metric | Gemini A | Gemini B | Local A | Local B |
|---|---:|---:|---:|---:|
| source_hit@1 | 0.875 | 0.875 | 0.812 | 0.781 |
| section_hit@1 | 0.812 | 0.844 | 0.750 | 0.750 |
| evidence_hit@1 | 0.594 | 0.406 | 0.406 | 0.438 |
| source_hit@5 | 0.969 | 0.938 | 0.906 | 0.875 |
| section_hit@5 | 0.938 | 0.938 | 0.906 | 0.875 |
| evidence_hit@5 | 0.938 | 0.844 | 0.719 | 0.719 |
| mrr | 1.000 | 0.984 | 0.961 | 0.938 |
| answerable top-1 (min–max) | 0.6269–0.8091 | 0.6246–0.8127 | 0.4121–0.7766 | 0.3755–0.7634 |
| unanswerable top-1 (min–max) | 0.6481–0.7540 | 0.6467–0.6908 | 0.4872–0.7146 | 0.4719–0.6522 |
| threshold | 0.686 | 0.686 | 0.5417 | 0.5417 |
| gate refuses answerable | 3/32 | 2/32 | 5/32 | 5/32 |
| gate refuses unanswerable | 3/4 | 3/4 | 2/4 | 2/4 |

- The local embedder is behind Gemini on every metric of both arms, except evidence_hit@1 on Arm B
  (0.438 vs 0.406). The biggest drop is evidence_hit@5 (0.938 → 0.719 on Arm A).
- Answerable cases the gate refuses: Arm A Q-EVAL-011 (en), 016, 018, 020, 028 (vi); Arm B Q-EVAL-010, 016, 018, 020,
  028 (all vi). Four of the five on Arm A, and all five on Arm B, are Vietnamese questions. Median answerable top-1,
  EN / VI (16 each): Gemini A 0.7531 / 0.7500, local A 0.6475 / 0.5865, local B 0.6472 / 0.5834. Local VI scores
  are lower than EN and Gemini's are not, so a single local threshold refuses VI questions more often. A
  per-language threshold is **TBD** (owner's call; n is small).
- On the eval split, answerable and unanswerable top-1 scores overlap for both embedders (local A: an unanswerable
  case scores 0.7146, the lowest answerable 0.4121), so no single threshold separates them there.
- Top-1 chunk from a source that is neither expected nor an acceptable alternate: local A Q-EVAL-008, 028; local B
  Q-EVAL-008, 016, 028. Gemini: none.
- Consistent with the benchmark (2026-11-21, section@1: Gemini 26/32, gemma1 fp32 24/32): Arm A section_hit@1 here
  is 0.812 (26/32) and 0.750 (24/32).

### Dev split (4 answerable, 2 unanswerable)

| run | expected source in top-1 | in top-5 | gate refuses answerable | gate refuses unanswerable |
|---|---:|---:|---:|---:|
| Gemini A `20260927-dev-A-retrieval-05680f9` | 2/2 | 2/2 | 0/2 | 1/1 |
| Local A | 4/4 | 4/4 | 0/4 | 1/2 |
| Local B | 4/4 | 4/4 | 0/4 | 0/2 |

The recorded Gemini dev retrieval run holds 3 of the 6 dev cases (Q-DEV-001, 002, 005); a Gemini dev Arm B run was not
recorded. Span metrics are not available for dev (`expected-spans-v1.json` covers the eval split only). "Expected
source" = a `source_id` in the case's `expected_sources` or `acceptable_alternate_sources`.

## Not done / open

- Full mode (answers + judge) with the local embedder: not run (no LLM quota; the owner decides when).
- Threshold for INT4 or other dims: TBD.
- Whether the gate rule should change for the local embedder (narrow dev gap, 5/32 answerable refused on eval):
  owner's call.
