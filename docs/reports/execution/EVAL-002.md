# EVAL-002 execution report: write the questions + ground truth (freeze pending owner review)

Date: 2026-09-25 · Branch: `eval-002` (from `dev` `9ee70bd`) · Prompt: [prompt-log](../../prompt-log/claude-code/EVAL-002.md) (task prompt + the owner's unattended-run overrides) · Environment: Linux cloud container, `.venv` Python 3.11.15 (owner re-runs on Windows later)

**Scope of this run:** steps 1–4 of the prompt (question files, validator + test, review sheet). Steps 5–6 (owner approval, `eval-freeze-v1` tag, final snapshot) are **not done**: the owner's run instruction keeps that human gate closed. M1 is **not** reached.

## Entry check
- Ledger: EVAL-001 `verified`, REORIENT-001 `verified`, OWNER-001 `verified`, INGEST-004 `verified` (all 2026-09-25). Owner re-check sheet filled (applied in OWNER-001).
- `data/chroma/` holds only `.gitkeep`: no ChromaDB index exists.
- `git status` clean at start; branch `eval-002` created from `origin/dev`.
- No prior EVAL-002 work existed (no `eval-v1.jsonl`), so nothing to audit.

## Files changed
| File | Change |
|---|---|
| `docs/plans/task-ledger.md` | Step 0: row 02 status "ready — OWNER-001 and INGEST-004 verified 2026-09-25"; row 01o note on the 017 alternate marked trimmed. Later: row 02 status/commits/verdict. |
| `data/evaluation/questions/blueprint.yaml` | Step 0: BP-EVAL-017 #10 alternate note "P1 and P2" → "P1" (owner-approved). A note, not a ground-truth field; coverage matrix unchanged (test passes). |
| `docs/specs/evaluation-dataset-design.md` | Step 0: §16 wording aligned ("also partly supports 017's P1 … (slot S2)"). |
| `data/evaluation/questions/question-wording-v1.yaml` (new) | The only hand-written input: one question per blueprint (36 eval + 6 dev), with the wording rules in the header. |
| `scripts/evaluation/build_question_files.py` (new) | Builds `eval-v1.jsonl` / `dev-v1.jsonl` = blueprint ground truth + wording. Deterministic, LF, UTF-8. |
| `data/evaluation/questions/eval-v1.jsonl`, `dev-v1.jsonl` (new) | 36 + 6 cases. Schema below. |
| `scripts/evaluation/validate_questions.py` (new) | The step 3 validator (checks below). Exit 1 on any error. |
| `tests/unit/test_eval_dataset.py` (new) | 19 tests: validator passes on the real files; files equal the build output; OD-4 mix; generated fields null; slots kept; 13 parametrized + 1 combined mutation checks that the validator rejects each kind of bad case. |
| `scripts/evaluation/build_review_sheet.py` (new) | Regenerates the case tables of the review sheet from the question files (between markers). |
| `docs/reviews/evaluation/eval-v1-review.md` (new) | Human review sheet: checklist, "look at these first", AI decisions, ground-truth proposals, verdict line, full tables. |
| `docs/prompt-log/claude-code/EVAL-002.md` (new) | Prompt, verbatim (run instruction + task prompt). |
| `docs/plans/master-plan.md`, `docs/plans/epics/EPIC-05-evaluation.md` | Status: EVAL-002 drafted, waiting for owner review; G5A first box met, freeze boxes open. |
| `AI_WORKLOG.md` | EVAL-002 entry. |
| `docs/plans/session-handoff-2026-09-25-eval-002.md` (new) | Owner actions, AI decisions, proposals, verdict, commits. |

## Schema of a case (one JSON line)
`id`, `blueprint_id`, `split`, `language`, `parallel_group_id`, `question`, `question_chars`, `answerable`; ground truth: `expected_answer`, `expected_behavior` (unanswerable only), `answer_points[{id,text,required}]`, `expected_sources[{source_id,heading_path,slot}]`, `acceptable_alternate_sources[{source_id,heading_path,slot,note}]`, `evidence[{source_id,heading_path,quote,supports}]`, `acceptable_variations`, `must_not_claim`, `citation_criteria`, `near_miss_sources`, `absence_proof`; slicing: `scope`, `cognitive_level`, `difficulty`, `size_class`, `failure_mode`, `retrieval_challenges`, `concepts`, `tags{difficulty,cognitive_level,size_class,failure_mode,scope}`; `generated{generated_answer,citations,result}` = all null (real outputs go to per-arm result files, design §18).

## Validator checks (`validate_questions.py`)
Schema/types and allowed values; ID pattern per split; unique IDs; `question_chars` = length; question text looks like its language (Vietnamese letters present iff `vi`); `tags` = flat fields; generated fields null; `answerable` ⇔ scope; answerable → sources, ≥ 1 required point, every required point supported by a quote, alternates only in slots that have an expected source, every expected source has a quote; unanswerable → no sources/points/evidence and an `expected_behavior`; ≥ 30 eval cases and ≥ 30 answerable; both languages per split; parallel pairs: one en + one vi, identical sources, alternates, points, evidence, criteria, expected answer; every `source_id` (incl. near-miss) accepted and not 14/19/24/25/27; every heading path in `section-inventory.jsonl`; every quote ≤ 300 chars and an exact substring of its section's text in `normalized.jsonl` (ADR-0003 D1 normalization, LF EOLs; whitespace runs collapsed on both sides; any variant unless `evidence_variant` is set); eval/dev disjoint on ID, blueprint, question text and expected sections.

## Commands run and results (real output)
```
$ python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt pytest
$ .venv/bin/python -m pytest -q            # baseline on dev 9ee70bd
121 passed in 4.13s
$ .venv/bin/python scripts/evaluation/build_question_files.py
wrote data/evaluation/questions/eval-v1.jsonl: 36 cases
wrote data/evaluation/questions/dev-v1.jsonl: 6 cases
$ .venv/bin/python scripts/evaluation/validate_questions.py
eval: 36 cases (32 answerable); dev: 6 cases; evidence quotes checked: 107
OK
$ .venv/bin/python -m pytest -q
140 passed in 4.19s
$ sha256sum data/evaluation/questions/eval-v1.jsonl data/evaluation/questions/dev-v1.jsonl   # draft, NOT the frozen hash
f265f527deba30601c25cfce5912a97a1bd9d7f254c3c92f92c9217a71cb6785  data/evaluation/questions/eval-v1.jsonl
37d349e5a7fa43a179755d1c7993ef5a8438954f995bedcaee07bcfbf4da21d6  data/evaluation/questions/dev-v1.jsonl
```
Mutation: quote check replaced by "any section counts" → `tests/unit/test_eval_dataset.py` 2 failed, 17 passed; file restored from backup, 19 passed.
First run of the new tests: 1 failed (my mutation case: removing one of 003's three P1 quotes still leaves P1 supported); fixed by using a case whose evidence is emptied (015).

## What is unverified
- Windows run of the new tests (owner re-runs on Windows 3.13.3).
- `gitnexus_detect_changes()` / impact analysis: GitNexus is not available in this container (no MCP tool, no index, `npx --no-install gitnexus` fails). No existing symbol was edited: all code is in new files; the only edits to existing files are docs/YAML text.
- Whether the Vietnamese wording is natural and whether questions leak answers: that is the owner review (a script cannot judge it).

## Deviations from the prompt
1. Steps 4 (after the sheet) and 5–6 not done: owner review, `eval-freeze-v1` tag and final `docs/snapshots/evaluation/eval-v1.md` are left to the owner (run instruction, override 2).
2. "Ask the user" replaced by conservative AI decisions recorded in the review sheet and handoff (override 1); none changes ground truth. One ground-truth proposal (G1) is written up, not applied.
3. Added `question-wording-v1.yaml` + a builder instead of hand-editing the JSONL, so ground truth provably equals the approved blueprints (test-checked).

## Explain it back
- **Why a builder instead of writing the JSONL by hand?** The ground truth was already approved in `blueprint.yaml`. Copying it by script (and testing that the files equal the build) means EVAL-002 can only change wording, never silently change an answer point or a source. Alternative: hand-write 42 JSON lines, which risks copy errors that no reviewer would spot.
- **Why check quotes against the normalized text, not the raw Markdown?** Retrieval and citations run on chunks cut from the normalized text (ADR-0003 D1). A quote that exists only in raw text (e.g. inside removed boilerplate) could never be cited. Whitespace is collapsed on both sides because line wrapping is not meaning.
- **Why keep evidence slots instead of a flat source list?** Owner decision D1: a multi-part answer is only retrieved if every part is; a flat list would score a cross-document case as a hit with one of two documents.
- **Why keep the tag until the owner reviews?** The tag time is the proof that ground truth predates any index; tagging before the human check would freeze wording nobody has read.
- **Why English `expected_answer` for Vietnamese questions?** Parallel pairs must share identical ground truth, and the judge compares meaning; translating would create a second, unreviewed ground truth.
