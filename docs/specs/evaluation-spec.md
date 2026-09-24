# Evaluation specification

Status: dataset mix (OD-4) and result labels (OD-5) decided 2026-09-24. Other metric details are **proposed** (marked) until EVAL-003 decides them. Undecided items are TBD / DECISION REQUIRED.

## Known facts
- At least 30 questions; each case: question, expected answer/ground truth, expected source, generated answer, result.
- Dimensions: answer quality, retrieval quality, citation quality, latency.

## Requirements
Source: `assignment-requirements.md`. Report must explain how each metric was measured. Failure analysis and evidence for any claimed improvement are graded emphasis.

## Chunking experiment (ADR-0003 D7-D8, accepted)
- Arms: header-aware (max 1,600 chars) vs fixed-size (1,600 chars, 200 overlap); one ChromaDB collection per arm; embedding model, distance metric, top-k=5, prompt, Gemini model and question set held constant.
- Retrieval metrics: source hit@5, section hit@5 (char-span overlap with expected section; any variant counts), MRR. Also answer quality (rubric), citation quality (cited chunk contains evidence), per-stage latency, and per-arm chunk statistics.
- Ground truth (expected `source_id` + heading path) is written before indexes are built. Questions must cover small docs as well as #13/#17/#23.
- Query language: English + Vietnamese (ADR-0003 D9). Each case has a `language` field; metrics reported overall and per language; a parallel EN/VI subset (same ground truth) isolates the cross-lingual effect.
- Answer model and LLM judge: `gemini-3.5-flash-lite` (ADR-0004). Judge verdicts are spot-checked manually on a sample (self-grading bias). Each result records the model that produced the answer and the retry/fallback count; retried calls are reported separately in latency statistics.
- Optional: <= 20-question subset answered by `gemini-3.5-flash` for an answer-model comparison.

## Dataset mix (OD-4, decided by the owner 2026-09-24)
- **Evaluation set: 36 cases** = 28 single-source answerable + 4 cross-document answerable + 4 "not in the documents" (`scope: corpus-insufficient`).
- **Languages:** 18 English, 18 Vietnamese.
- **Parallel subset:** 7 EN/VI groups (14 cases). Both cases of a group share the same expected sources, answer points and acceptance criteria.
- **Floor:** at least 30 answerable cases must remain. Up to 2 answerable cases may be dropped during verification (EVAL-002); dropping more needs a replacement.
- **Dev set: 6 cases** (`split: dev`), disjoint from the evaluation set. Used only to tune the prompt and the "insufficient information" rule. Never reported as evaluation results.
- Design and blueprints: `docs/specs/evaluation-dataset-design.md`, `data/evaluation/questions/blueprint.yaml`.

## Answer result labels (OD-5, decided by the owner 2026-09-24)
Every generated answer gets exactly one `result`:

| `result` | Case type | Rule |
|---|---|---|
| `correct` | answerable | All required answer points present; no wrong or `must_not_claim` statement. |
| `partially_correct` | answerable | At least one required point present, at least one missing; nothing wrong. |
| `incorrect` | answerable | A wrong or `must_not_claim` statement, or no required point present. |
| `false_refusal` | answerable | The system said the documents are insufficient although they contain the answer. |
| `correct_refusal` | corpus-insufficient | The system said the documents don't contain enough information and made no unsupported claim. |
| `hallucination` | corpus-insufficient | The system answered anyway (any substantive claim not supported by the documents). |

Plus a **points-covered score** for answerable cases: required points present ÷ required points (e.g. 3/4 = 0.75). It gives finer comparisons between the two arms than the label alone. Optional points never lower the score.

## Proposed for EVAL-003 (not decided; marked `metric_decision: proposed`)
- **Citation quality** (method is OD-12): one label per answer: `correct_evidence` (a cited chunk contains the evidence for the answer's claim), `correct_source_wrong_evidence` (right document, but the cited chunk doesn't support the claim), `unsupported_citation` (cited chunk from an unrelated place), `citation_missing`. Judge the chunk *text* against the evidence, not heading strings: Arm A may label a merged small section with the first section's heading path (ADR-0003 D3), and Arm B uses the nearest preceding heading (D5).
- **Cross-document cases:** source hit@5 = all expected sources in the top 5 (primary); "any expected source" reported as secondary.
- **Acceptable alternate sources:** a hit on an `acceptable_alternate_sources` section counts as a source/section hit for that case. In cross-document cases each alternate names the expected source it replaces (`stands_in_for`), and counts only for that source under the "all" rule.
- **Corpus-insufficient cases:** excluded from source hit@5, section hit@5 and MRR (no expected source). Scored only with `correct_refusal` / `hallucination`.
- **Vietnamese questions:** API names and identifiers stay in their original form (e.g. `DbContext`, `UseExceptionHandler`), as a Vietnamese developer would type them.
- **Record layout:** ground truth lives only in the question files (`data/evaluation/questions/`). Generated answer, citations, retrieved chunks, latency per stage, model used, retry count and `result` go into per-arm result files (`data/evaluation/results/`) keyed by case `id`, so one question set serves both arms.

## Amendments after the freeze
None yet. After `eval-freeze-v1` (EVAL-002), every change is logged here with what, why and date.
