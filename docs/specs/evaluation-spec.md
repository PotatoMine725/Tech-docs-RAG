# Evaluation specification

Status: dataset mix (OD-4), result labels (OD-5), the evidence-slot hit rule (D1) and the refusal rule (D2) decided by the owner 2026-09-24; refusal routing, citation label names, the question-file schema and the points-covered formula settled by the owner the same day (REORIENT-001 C1–C4). Other metric details are **proposed** (marked) until EVAL-003 decides them. Undecided items are TBD / DECISION REQUIRED.

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
| `correct_refusal` | corpus-insufficient | The system said the documents don't contain enough information and made no unsupported claim. It may mention related content from the documents if it says the topic isn't covered and doesn't present that content as the answer (D2). |
| `hallucination` | corpus-insufficient | The system answered anyway: any substantive claim not supported by the documents, or related content presented as the answer (D2). |

**Who labels unanswerable cases (D2, owner 2026-09-24; routing amended by the owner 2026-09-24, REORIENT-001 C1):**
- The system marks the answer insufficient and gives a bare message (no related note in `missing_information`, no related citations) → `correct_refusal`, no judge call.
- The system marks the answer insufficient but adds a related note or related citations → the LLM judge runs the refusal check: `correct_refusal` if nothing is presented as the answer, `hallucination` if related content or an inferred technique is presented as the documents' answer (e.g. "use `MapGroup("/v1")` to version").
- The system doesn't mark the answer insufficient → the judge decides between `correct_refusal` and `hallucination` with the same rule; such answers are never auto-labelled `hallucination`.
- This needs the generation step to keep `missing_information` and allow optional related citations on insufficient answers (RAG-002).

Plus a **points-covered score** for answerable cases: (required points judged `yes` + 0.5 × required points judged `partial`) ÷ required points (e.g. yes, partial, no → 1.5/3 = 0.50; owner decision 2026-09-24, REORIENT-001 C4). It gives finer comparisons between the two arms than the label alone. Optional points never count, so they never lower the score.

## Retrieval hit rule: evidence slots (D1, decided by the owner 2026-09-24)
- Every expected and alternate source of an answerable case belongs to one **evidence slot** (`slot: S1`, `S2`, …; test-checked).
- **All of the slots, any source within a slot.** source hit@5 = 1 when every slot has at least one of its sources among the top-5 chunks. section hit@5 = the same at section level (a top-5 chunk overlaps a span of a section listed in that slot; any variant counts, ADR-0003 D8). An alternate source counts only for its own slot.
- Most cases have one slot, so any listed source or section counts. Several slots: the 4 cross-document cases (one slot per document), BP-EVAL-022 (one slot per method, because its blueprint requires both in the top 5) and BP-EVAL-017 (S1 = the #11 intro, S2 = 'IMiddleware'; owner, 2026-09-25, OWNER-001).
- Secondary, reported separately: fraction of slots satisfied.
- MRR is unchanged: 1 / rank of the first chunk that hits any slot.
- Citations in multi-slot cases: one per slot, from any source in that slot (e.g. BP-EVAL-031 slot S2 = #26 or #20).
- **Strict and lenient hit (owner, 2026-09-25, OWNER-001; condition for accepting the widened alternates of the EVAL-001 re-check).** EVAL-003b reports source hit@k and section hit@k twice:
  - **lenient** = the D1 rule above: every slot needs one of its expected **or alternate** sources/sections;
  - **strict** = the same rule with the alternates removed: every slot needs one of its **expected** sources/sections.
  - Example: slots S1 = {#04 expected}, S2 = {#26 expected, #20 alternate}; top-k {#04, #20} → lenient hit, strict miss.
  - MRR and the fraction of slots satisfied stay on the D1 (lenient) rule; strict applies only to source and section hit. Which of the two hit values is the headline number in the report: **TBD / DECISION REQUIRED** (EVAL-003c/EVAL-004).

## Proposed for EVAL-003 (not decided; marked `metric_decision: proposed`)
- **Citation quality** (method is OD-12): one label per answer: `correct_evidence` (a cited chunk contains the evidence for the answer's claim), `correct_source_wrong_evidence` (right document, but the cited chunk doesn't support the claim), `unsupported_citation` (cited chunk from an unrelated place), `citation_missing`. These four names are the ones every prompt uses (owner, 2026-09-24, REORIENT-001 C2). Judge the chunk *text* against the evidence, not heading strings: Arm A may label a merged small section with the first section's heading path (ADR-0003 D3), and Arm B uses the nearest preceding heading (D5).
- **Corpus-insufficient cases:** excluded from source hit@5, section hit@5 and MRR (no expected source). Scored only with `correct_refusal` / `hallucination` (who labels them: D2 above).
- **Vietnamese questions:** API names and identifiers stay in their original form (e.g. `DbContext`, `UseExceptionHandler`), as a Vietnamese developer would type them.
- **Record layout:** ground truth lives only in the question files (`data/evaluation/questions/`). Generated answer, citations, retrieved chunks, latency per stage, model used, retry count and `result` go into per-arm result files (`data/evaluation/results/`) keyed by case `id`, so one question set serves both arms. The question-file fields are the ones in `evaluation-dataset-design.md` §18 (answer points with a `required` flag, expected and alternate sources with their evidence `slot`, acceptable variations, `must_not_claim`, citation criteria); the EVAL-002 question file, the EVAL-003a run records and the EVAL-003b judge input use that schema, not flat source lists (owner, 2026-09-24, REORIENT-001 C3).

## Amendments after the freeze
None yet. After `eval-freeze-v1` (EVAL-002), every change is logged here with what, why and date.
