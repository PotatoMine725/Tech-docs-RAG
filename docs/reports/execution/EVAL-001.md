# EVAL-001 execution report: design the evaluation dataset

**Date:** 2026-09-24 · **Prompts:** [full prompt](../../prompt-log/claude-code/EVAL-001%20—%20Design%20Evaluation%20Dataset.md) + [addendum](../../prompt-log/claude-code/EVAL-001.md) · **Model:** Claude Opus 5.5 (Claude Code) · **Status:** done. Owner reviewed; independent review done and addressed. Pending: the owner's re-check of the cases whose ground truth changed (review §5).

## Files
| File | Change |
|---|---|
| `docs/specs/evaluation-dataset-design.md` (new) | The design: all 20 required topics, schema, case table, open decisions |
| `data/evaluation/questions/blueprint.yaml` (new) | 36 evaluation + 6 dev blueprints with verbatim evidence quotes |
| `data/evaluation/questions/evidence-map.yaml` (new) | 6 absence proofs (search terms, zero hits) and 10 known distractor sections |
| `data/evaluation/questions/coverage-matrix.yaml` (new, generated) | Counts, cross-tables, per-source use, dominance checks |
| `scripts/evaluation/build_coverage_matrix.py` (new) | Generates the matrix from the blueprints (deterministic) |
| `tests/unit/test_evaluation_blueprints.py` (new) | 17 offline checks (85 evidence quotes in `blueprint.yaml`) |
| `docs/specs/evaluation-spec.md` | OD-4 mix and OD-5 labels (owner decisions); proposed metric details for EVAL-003; amendment log section |
| `pyproject.toml`, `requirements.txt` | `PyYAML>=6.0,<7.0` declared (it was installed only through chromadb; the prompt requires YAML files and the tests read them) |
| `docs/plans/master-plan.md`, `docs/plans/epics/EPIC-05-evaluation.md` | EVAL-001 status, OD-4/OD-5 decided, timeline |
| `docs/prompt-log/claude-code/EVAL-001.md` (new), `docs/prompt-log/README.md` | Addendum prompt copy (verbatim, `cmp`) |
| `AI_WORKLOG.md` | EVAL-001 entry |

## Commands run (real output)
- Owner decisions via AskUserQuestion: order HOUSE-001 → EVAL-001; OD-4 "32 answerable + 4 insufficient"; OD-5 "6 labels + points-covered score".
- Corpus reading: section list from the inventory (all 24 docs); full reads of #09, #18, #22, #29; first 9 sections of #08; non-link lines of #05; every section used as evidence. The rest of the huge documents was not read line by line.
- Absence searches (case-insensitive, fixed string, `corpus/sources/*.md` only): every term in `evidence-map.yaml` gives 0 hits. The one allowed term, "scope validation", hits 4 times, all inside #10's link-only section.
- `.venv/Scripts/python.exe scripts/evaluation/build_coverage_matrix.py` twice → identical SHA-256 (deterministic).
- `tests/unit/test_evaluation_blueprints.py` before the matrix script existed: 12 passed, 1 failed (`FileNotFoundError`, the expected red step). After: 13 passed.
- `.venv/Scripts/python.exe -m pytest`: 41 passed at commit `585f434`.
- Follow-up after review: five evidence quotes had been trimmed so far that they no longer contained the fact they were meant to prove (BP-EVAL-025, 026, 027, 029, BP-DEV-002). They were replaced with full sentences, and 17 missing supporting quotes were added (62 → 79 quotes). Every quote now lists the answer points it `supports`, and a new test fails if a required point has none: 1 failed before the edit, 14 passed after. Matrix: source IDs are quoted.
- `.venv/Scripts/python.exe -m pytest` after the follow-up: **42 passed**.
- Independent review (2026-09-24, after the owner's review): a separate read-only agent reported 24 findings (4 high, 9 medium, 11 low) in [`docs/reviews/evaluation/EVAL-001-blueprint-review.md`](../../reviews/evaluation/EVAL-001-blueprint-review.md). Each finding's corpus quote was re-checked by script (all found in the named sections).
  - While triaging, a YAML defect was found: 32 values cut off at " #" and one variation read as a mapping. It was fixed in `9e0ab15`, with 2 new tests that failed before the fix (44 passed after).
  - Then all 24 findings were addressed (22 accepted, 1 partly accepted, 1 decided by the author: the DEV-006 scoring rule, since confirmed by the owner as D2); the response table is section 5 of the review.
  - A new test for `stands_in_for` failed with the field removed and passed with it. (The field was later replaced by `slot`, below.)
  - The evidence map now has 11 distractor sections (one wrong entry removed, two added).
  - `.venv/Scripts/python.exe -m pytest`: **45 passed**.
  - After the alternates were added, a script compared the dev and eval sets on expected *and* alternate sections: no dev section matches any eval section. The disjointness test covers expected sources only.
  - Owner decisions after the review (2026-09-24):
    - **D1, evidence slots.** Every expected/alternate source now has `slot: S1|S2`; hit = all slots, any source within a slot. `stands_in_for` was replaced by `slot` (#20 is in 031's S2 slot, and 031's citation criterion accepts #20). 022 has two slots because its blueprint requires both methods. The new slot test failed before the tagging (the file still contained `stands_in_for`) and passed after. Test count unchanged (17 in the blueprint file), 45 in total.
    - **D2, refusal rule.** Related content may be mentioned if the answer says the topic isn't covered and doesn't present it as the answer. It is applied to 034, DEV-005 and DEV-006 (the others already said so). The label rules and the judge-decides rule are in `evaluation-spec.md`. The downstream task prompts (RAG-002, EVAL-003a/b) are updated in a separate `DOCS:` commit.
    - **D3, 030 stays cross-document.** Already implemented; no change.
  - 030: #28 also has a `[Fact]` test `IsPrime_InputIs1_ReturnFalse` with an input below 2, so `question_notes` now name the `[Theory]` test.

## Exit-gate check (prompt §22)
| Criterion | Result |
|---|---|
| CLAUDE.md consistent with the RAG project | Yes. The duplicate GitNexus block was removed in HOUSE-001; the count line is tool-generated and changes after each re-index |
| 24 accepted / 4 excluded / #25 never existed | Yes (manifest + tests; no excluded ID or 25 in any blueprint, test-checked) |
| Decisions traceable or marked proposed/TBD | Yes: OD-4/OD-5 owner-decided; other metric items marked proposed in `evaluation-spec.md` §"Proposed" and design §20 |
| ≥ 30 final cases supported; ~36 slots | 36 eval slots, 32 answerable; 2 may be dropped |
| EN and VI | 18 / 18 |
| 6–8 parallel groups | 7 (test-checked identical ground truth) |
| Small docs covered | #22 (3), #29 (2), #18 (1); hub docs #05/#08/#09 used as distractors (justified) |
| #13/#17/#23 covered | 5 / 1 / 3 cases |
| Failure modes represented | All 8 (test-checked) |
| easy/medium/hard; all 6 cognitive levels | 7/17/12; recall 6, explain 6, apply 9, analyze 4, compare 3, diagnose 8 (test-checked) |
| Single-source majority; limited cross-doc | 28 single, 4 cross-document, each premise from one document |
| Ground truth has source_id + heading path | Yes; heading paths test-checked against the inventory |
| Designed independently of retrieval | Yes; no chunks or indexes exist |
| Citation and answer criteria per case | Yes (test-checked for every answerable case) |
| No generated answers or results | None created |
| No external knowledge as evidence | All answer points come from quoted corpus text (quotes test-checked verbatim) |
| No excluded source used | Not opened, not searched, not referenced |
| Coverage matrix without unexplained gaps | Gaps #05–#09 explained in design §5 |
| Duplicate risks documented | Design §16 |
| Unresolved decisions listed | Design §20 |

## Deviations from the prompts
1. **Order:** HOUSE-001 ran first, as the owner chose (the prompt table lists it as a prerequisite of EVAL-001).
2. **Rubric:** the master plan said EVAL-001 writes the rubric into `evaluation-spec.md`; the EVAL-001 prompt says to propose metrics and mark them TBD. I followed the prompt: only the owner's OD-4/OD-5 answers are recorded as decided; citation labels, the cross-document hit rule and others are marked *proposed*. Master-plan wording updated.
3. **Mix:** the addendum suggested ~26 single + ~4 cross + ~4–6 insufficient; the owner chose 28 + 4 + 4, so at least 30 answerable cases survive dropping two.
4. **Schema:** the prompt's example keeps `generated_answer`, `result` etc. inside each case. The design keeps ground truth in the question file and generated fields in one results file per arm, because one question set is run through two arms (design §18).
5. **Field names:** the prompt's `unacceptable_claims` and `must_not_claim` are merged into `must_not_claim`. `answer_points` carry a `required` flag instead of separate required/optional lists.
6. **"Inspect all 24 documents":** met through the inventory structure plus full reads of the tiny docs and every target section, not a line-by-line read of the 1.2 M characters (stated in design §12).

## Unverified
- Statements about how each arm will cut a section (merges under 400 chars, exact-duplicate removal, table handling) follow the ADR-0003 rules. They are not measured, since no chunker exists yet (EPIC-02).
- Whether each blueprint leads to a natural question: to be checked in EVAL-002 and by the owner's review.
- `agents/` files (owner's prompt set, `verifier.md`) are still uncommitted: the owner is editing them; they were not touched.
