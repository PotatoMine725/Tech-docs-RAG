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
  - **Headline = lenient** (owner, 2026-09-25, OWNER-001). Strict is always reported next to it, in the same table.
  - MRR and the fraction of slots satisfied use the lenient rule. Strict MRR (the same formula over expected sections only) is reported as a secondary value.
  - EXP-001 compares the two arms under both rules. If the conclusion flips between strict and lenient (e.g. Arm A wins lenient but loses strict), the report MUST say so.
- **Duplicate overlap rule (owner, 2026-09-27, EVAL-003b; scope corrected by the owner the same day).** For the section-level (span) metrics, lenient and strict (section hit@k, MRR, section slot fraction, citation section precision), a retrieved chunk counts as overlapping a span if it OR any chunk in its `duplicate_chunk_ids` does. The retriever keeps one chunk per `passage_hash` group (RAG-002), and the chunk it keeps can lie in the other document of the #12/#13 pair. **Source metrics** (source hit@k, source MRR, source slot fraction, citation source precision) **use the kept chunk's own document**, i.e. what the user sees. The EVAL-003b addendum said "span/source metrics"; the owner has since said that wording was a mistake and that section level was intended (the owner's prediction: at most 2 cases). Simulated on the chunk files (not a retrieval result), the rule can change only Q-EVAL-003 and 004 on Arm A; Arm B has no duplicate groups. EVAL-004 reports the actual number of changed case × arm values (`duplicate_rule_changed`).
- **evidence_hit@k (owner, 2026-09-26).** Headline = per required point: every required answer point has at least one of its supporting quotes (`evidence[].supports`) contained whole in some top-k chunk (all-of across required points, any-of across the quotes of one point; whitespace collapsed as in `validate_questions.py`). Optional-point quotes are ignored. evidence_hit is content-level: a required point counts if a supporting quote appears whole in any top-k chunk, including chunks from owner-approved alternate sections. It therefore aligns with lenient section hit, not strict. Strict section hit is reported alongside. Diagnostics, reported separately: "any quote of the case in a top-k chunk" and `evidence_hit_via_alternate_only` (4 of 32 eval cases can score it with alternate-only retrieval: 003, 004, 007, 008; the same 4 with the duplicate rule, EVAL-003b). The duplicate rule does not apply here: it is a content check on the chunk text.

## Answer and citation scoring (EVAL-003b, owner decisions 2026-09-26/27)
- **Judge.** `JUDGE_MODEL` = `gemini-3.5-flash-lite` (config only), temperature 0, no fallback model (a judgement from another model is rejected), its own 13-RPM throttle, run as a separate step after generation and never at the same time as the runner. Prompt `config/prompts/judge_v1.md`, two sections: the answer check for answered answerable records (coverage `yes`/`partial`/`no` of each required point by id, contradiction incl. `must_not_claim`, unsupported claims, support per citation marker, reason) and the refusal check for corpus-insufficient records (`presents_related_as_answer` + reason). The judge sees the ground truth, the answer, its `missing_information` and the full text of every cited chunk taken from the run record. Malformed JSON, a missing field, or point ids / markers that are not exactly the expected set give `judge_error`, never a guessed verdict; such records stay unlabelled and are listed. Runner-error records (no answer) are listed apart and are not in any denominator. Cache: `judgements.jsonl` in the run folder, key (case, arm, sha256 of the answer, prompt version).
- **Related note (D2).** A "related note" is a non-empty `missing_information`. Answer-prompt rule 2 makes the model fill it on almost every refusal it writes itself, so nearly every LLM refusal of a corpus-insufficient case gets the refusal check; only retrieval-gate refusals are bare `correct_refusal` without a judge call.
- **OD-12, citation quality (owner, 2026-09-26): both checks, reported separately.** Automatic span check: source precision (cited chunk's own document is a source in any evidence slot, alternates included), section precision (cited chunk, or a duplicate of it, overlaps a lenient span) and a 4-way class per record (`correct_evidence` if a cited chunk overlaps a span, else `correct_source_wrong_evidence` if one comes from a slot source, else `unsupported_citation`; `citation_missing` without citations). Judge support check: support rate (citations judged `yes`) and the same 4-way class with "judged `yes`" in place of "overlaps a span". Only answered answerable records are scored; related citations of an insufficient answer are only counted (`related_citation_count`).
- **Limitation.** The judge is the same model as the answer model (self-preference risk); mitigated by an owner spot-check of ~10 judgments after EVAL-004.

## Proposed for EVAL-003 (not decided; marked `metric_decision: proposed`)
- **Citation quality** (method OD-12 decided 2026-09-26, see "Answer and citation scoring" above): one label per answer: `correct_evidence` (a cited chunk contains the evidence for the answer's claim), `correct_source_wrong_evidence` (right document, but the cited chunk doesn't support the claim), `unsupported_citation` (cited chunk from an unrelated place), `citation_missing`. These four names are the ones every prompt uses (owner, 2026-09-24, REORIENT-001 C2). Judge the chunk *text* against the evidence, not heading strings: Arm A may label a merged small section with the first section's heading path (ADR-0003 D3), and Arm B uses the nearest preceding heading (D5).
- **Corpus-insufficient cases:** excluded from source hit@5, section hit@5 and MRR (no expected source). Scored only with `correct_refusal` / `hallucination` (who labels them: D2 above).
- **Vietnamese questions:** API names and identifiers stay in their original form (e.g. `DbContext`, `UseExceptionHandler`), as a Vietnamese developer would type them.
- **Record layout:** ground truth lives only in the question files (`data/evaluation/questions/`). Generated answer, citations, retrieved chunks, latency per stage, model used, retry count and `result` go into per-arm result files (`data/evaluation/results/`) keyed by case `id`, so one question set serves both arms. The question-file fields are the ones in `evaluation-dataset-design.md` §18 (answer points with a `required` flag, expected and alternate sources with their evidence `slot`, acceptable variations, `must_not_claim`, citation criteria); the EVAL-002 question file, the EVAL-003a run records and the EVAL-003b judge input use that schema, not flat source lists (owner, 2026-09-24, REORIENT-001 C3).

## Amendments after the freeze
After `eval-freeze-v1` (EVAL-002), every change is logged here with what, why and date. The question files are unchanged; these are scoring rules only.
- 2026-09-26 (owner): evidence_hit@k per required point, content-level; any-quote and alternate-only as diagnostics (EVAL-003b-pre, `240f948`, `943f063`). Why: "the evidence quote" was ambiguous for multi-quote cases.
- 2026-09-26 (owner): OD-12 = automatic span check and judge support check, reported separately (EVAL-003b).
- 2026-09-27 (owner): duplicate overlap rule, section level only (EVAL-003b). Why: RAG-002 keeps one chunk per passage group, which can sit in the other document of the #12/#13 pair. The addendum's "span/source" was a wording mistake (owner, same day); source metrics use the kept chunk's own document.
- 2026-09-27 (owner): judge limitation recorded (same model as the answers; ~10-judgment owner spot-check after EVAL-004).
