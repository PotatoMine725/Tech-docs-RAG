# EVAL-002 prompt (verbatim)

Two parts: (1) the owner's run instruction for this unattended cloud session, 2026-09-25; (2) the task prompt file it executes, `agents/prompts/02-EVAL-002-write-and-freeze.md`, as of `dev` `9ee70bd`.

## 1. Owner run instruction (chat, 2026-09-25)

````text
Autonomous cloud run — the owner is away and cannot answer questions. Work on a new branch eval-002 from origin/dev.

Task: Execute agents/prompts/02-EVAL-002-write-and-freeze.md, with the overrides below. Read agents/prompts/_common.md first.

Step 0 (housekeeping, first commit): INGEST-004 is verified and merged (2026-09-25).
- docs/plans/task-ledger.md row 02: "ready — OWNER-001 and INGEST-004 verified 2026-09-25".
- docs/plans/master-plan.md (~line 129) and docs/plans/epics/EPIC-02-*.md (line 3): INGEST-004 "waiting for 99-VERIFY" → "verified 2026-09-25".
- Trim the note on BP-EVAL-017's #10 "Service lifetimes" alternate from "P1 and P2" to "P1" (owner-approved, verifier note OWNER-001 #3).

Overrides for this unattended run:
1. No questions. Where _common.md says "ask the user", do this instead: choose the most conservative option, apply it only if it does NOT change ground truth (answer points, evidence, sources, slots, answerability), and record it in the handoff note under "AI decisions to confirm". Anything that would change ground truth: do NOT apply it; write it up as a proposal for the owner.
2. Human gates stay closed. Build everything up to and including the review sheet docs/reviews/evaluation/eval-v1-review.md. Do NOT create the eval-freeze-v1 tag, do NOT write docs/snapshots/evaluation/eval-v1.md as final, do NOT mark M1 done. The owner reviews and tags.
3. Make the owner's review fast: at the top of the review sheet add (a) a checklist (Vietnamese sounds natural; question does not leak the answer or the exact name to look up; answer matches the evidence quote), and (b) a "look at these first" list of the cases you are least sure about, each with one line why.
4. Independent check before you stop: run agents/prompts/99-VERIFY.md for TASK-ID=EVAL-002 in a sub-agent with fresh context. At most one fix round; re-verify only if something FAILED. Record the verdict in the ledger.
5. Save progress often: commit and push eval-002 after Step 0, after the question files + validator, after the review sheet, and after the verify. If the session ends early, the pushed state must be consistent (tests green at every push).
6. Environment: this is Linux. Use a local venv, install requirements.txt + pytest, run the full suite before every push. Write text files with explicit newline="\n". The owner re-runs pytest on Windows later.
7. Scope: no Gemini calls, no ChromaDB index, do not start RAG-001a or any later task.

At the end:
- Write docs/plans/session-handoff-2026-09-25-eval-002.md: 🚩 owner actions in order (review sheet → approve/fix → tag command to run), AI decisions to confirm, ground-truth proposals (not applied), verify verdict, test results, branch/commit list.
- Open a PR eval-002 → dev (do not merge). STOP.
````

## 2. Task prompt file

````markdown
# EVAL-002 — Write the questions + ground truth, then freeze (M1)

Read `agents/prompts/_common.md` first and follow it.
Entry: EVAL-001 done and approved by the user; every `owner verdict:` line in `docs/reviews/evaluation/EVAL-001-owner-recheck.md` is filled; EVAL-001 is `verified` in `docs/plans/task-ledger.md`. No ChromaDB index exists yet (check `data/chroma/`).

## Do
1. Turn every approved blueprint into a final case in `data/evaluation/questions/eval-v1.jsonl` (and dev cases into `dev-v1.jsonl`). Schema from `evaluation-dataset-design.md`. Ground-truth fields and future generated fields are clearly separated (generated fields null). Every case MUST carry the design §18 fields the runner and metrics need later (see `09a-EVAL-003a-runner.md` record schema; owner 2026-09-24, REORIENT-001 C3): `answerable` (bool), `answer_points` [{id, text, required}] (optional points kept), `expected_sources` and `acceptable_alternate_sources` with their evidence `slot` (owner decision D1 — never flattened to a plain list), `evidence` [{source_id, heading_path, quote}], `acceptable_variations`, `must_not_claim`, `citation_criteria`, `parallel_group_id`, and `tags` {difficulty, cognitive_level, size_class, failure_mode, scope}.
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
````
