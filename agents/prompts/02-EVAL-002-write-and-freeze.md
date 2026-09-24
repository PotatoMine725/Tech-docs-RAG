# EVAL-002 — Write the questions + ground truth, then freeze (M1)

Read `agents/prompts/_common.md` first and follow it.
Entry: EVAL-001 done and approved by the user. No ChromaDB index exists yet (check `data/chroma/`).

## Do
1. Turn every approved blueprint into a final case in `data/evaluation/questions/eval-v1.jsonl` (and dev cases into `dev-v1.jsonl`). Schema from `evaluation-dataset-design.md`. Ground-truth fields and future generated fields are clearly separated (generated fields null). Every case MUST also carry the fields the runner and metrics need later (see `09a-EVAL-003a-runner.md` record schema): `answerable` (bool), `expected_source_ids` (list), `expected_heading_paths` (list), `evidence_quotes` (list), `required_points`, `must_not_claim`, `parallel_group_id`, and `tags` {difficulty, cognitive_level, size_class, failure_mode, scope}.
2. Vietnamese questions: natural phrasing a Vietnamese developer would type (technical terms may stay English, e.g. "middleware", "DbContext"). Not word-by-word translation.
3. **Validator** `scripts/evaluation/validate_questions.py` + offline test `tests/unit/test_eval_dataset.py`:
   - schema valid, IDs unique, ≥ 30 eval cases, both languages, parallel pairs share source/heading/answer points;
   - every `source_id` accepted (not 14/19/24/27/25); every heading path exists in the section inventory;
   - every evidence quote is found in the source text after the same whitespace/EOL normalization EPIC-02 will use (exact substring match) — this is the anti-hallucination check on ground truth;
   - eval and dev sets disjoint.
4. **Human review sheet** → `docs/reviews/evaluation/eval-v1-review.md`: table (id, lang, question, expected answer, source, heading path, evidence quote) for the user to check. STOP and ask the user to review. Apply corrections.
5. After user approval: commit, then create annotated git tag `eval-freeze-v1` (the tag time is the proof that ground truth predates any index). Add `docs/snapshots/evaluation/eval-v1.md` with the commit hash and SHA-256 of both files.
6. Any later change = a new amendment entry in `docs/specs/evaluation-spec.md` (what/why/date), never a silent edit.

## Do not
Call Gemini, build indexes, or generate answers.
