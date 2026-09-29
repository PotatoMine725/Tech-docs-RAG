# RE-VERIFY EVAL-001

Verifier session, 2026-09-25, independent of the author. This re-verifies EVAL-001 after the first verify ([EVAL-001-verify](EVAL-001-verify.md), ACCEPT WITH FIXES, `e5e27b1`). It covers two commits:
- `629b931` ("EVAL-001: doc fixes from verification", 5 files), checked against the fix prompt at the end of the first review and the mapping in `docs/plans/task-ledger.md`, section "EVAL-001: verify findings → fixing commit";
- `831d5a0` ("EVAL-001: owner decisions D1-D3 (evidence slots, refusal rule, 030)", 7 files). It was committed after the first verify and had never been verified.

The branch `verify-eval-001-reverify` was created at `443582a` (`dev`); both commits are ancestors of it. Older revisions were read with `git show` / `git archive`. Test runs and mutation checks against old revisions ran on `git archive` copies in the session scratchpad, not in the checkout.

This session ran on Linux, not Windows, so the commands used `/home/user/Tech-docs-RAG/.venv/bin/python -m pytest`, not `.venv/Scripts/python.exe`. pytest's `pythonpath = ["src"]` (`pyproject.toml:26`) puts the tested tree's `src` first. GitNexus MCP tools were not available; the CLI (`npx -y gitnexus`, 1.6.12) was used. Nothing was copied from the execution report or the commit messages.

`8d04044` ("DOCS: carry owner decisions D1/D2 into the RAG-002 and EVAL-003 prompts") sits between the two commits. It has no `EVAL-001:` prefix and REORIENT-001 already audited and corrected it (`AI_WORKLOG.md:90`), so it is out of scope here. It is read only where it touches the D1/D2 wording.

The owner re-check sheet `EVAL-001-owner-recheck.md` has 9 empty `owner verdict:` lines. Filling them is a human step, and this session did not fill them. They do not affect this verdict, which is about `629b931` and `831d5a0` only, but **they still block EVAL-002**.

## A. Fix prompt items (first review), each check re-run

| # | Fix | Result | Evidence |
|---|---|---|---|
| 1 | Design §19 "Plain semantic matches 6%" → current value | PASS | `evaluation-dataset-design.md:132` "- Plain semantic matches 9%."; `coverage-matrix.yaml:355` `share_direct_semantic: 0.094`. The other §19 shares match lines 351–354 too (0.5 / 0.167 / 0.194 / 0.25). |
| 2 | Report "14 offline checks" → current count; optional quote total | PASS | `EVAL-001.md:13` "17 offline checks (85 evidence quotes in `blueprint.yaml`)". `pytest --collect-only -q tests/unit/test_evaluation_blueprints.py` → `17 tests collected in 0.02s`. `grep -cE "^ *quote:" data/evaluation/questions/blueprint.yaml` → `85`. Wording note: 85 counts `quote:` lines in the YAML. Parsed with the parallel-group anchors there are 107 evidence entries (84 unique, max 289 chars, scratch script), the same as the first review. |
| 3 | Stale "awaiting/waiting for the owner's review" status lines | PASS | `evaluation-dataset-design.md:3`, `EPIC-05-evaluation.md:3` and, in `629b931`, `master-plan.md:29/:167` now say "Owner reviewed; independent review done; pending the owner's re-check …" (`git show 629b931`). At HEAD the master plan links to the ledger instead (`master-plan.md:175`, a REORIENT-001 change). `grep -rn "awaiting owner review\|waiting for the owner's review" docs/ AI_WORKLOG.md` → hits only where the text is quoted: `EVAL-001-verify.md:30,97,119,122`, `task-ledger.md:47`, `REORIENT-001-verify.md:36`, `REORIENT-001.md:29`, `AI_WORKLOG.md:83`. None is a status line. |
| 4 | Tally "23 accepted, 1 partly accepted" → "22 / 1 / 1 decided by the author" | PASS | `AI_WORKLOG.md:75` and `EVAL-001.md:31` now say "22 accepted, 1 partly accepted, 1 decided by the author (DEV-006 …, since confirmed by the owner as D2)". Review §5 Decision column (`EVAL-001-blueprint-review.md:149-172`): #1 "Partly accepted", #2–#23 "Accepted" (22), #24 "Decided". The repo still says "23 accepted" only where earlier findings are quoted (`AI_WORKLOG.md:84`, `task-ledger.md:48`, `EVAL-001-verify.md:63,123`). |
| 4b | List the DEV-006 rule as an open owner decision | PASS (superseded) | The owner decided it as D2 before the fix commit: `EVAL-001-blueprint-review.md:180` reads "D2 (finding 24): the DEV-006 rule is confirmed and generalised", and D2 is in `evaluation-spec.md` (see B-D2). Nothing is left open. That the owner actually made the decision is taken from these records (U1). |
| 5 | pytest 45, `gitnexus_detect_changes()`, commit message, only the named files | PASS (after the fact) | The commit message is exact. `git show --stat 629b931` → exactly the 5 files the fix prompt names (design, report, master plan, EPIC-05, worklog), `8 insertions(+), 8 deletions(-)`, all `.md`. pytest on a `git archive 629b931` copy → `45 passed in 4.23s`. GitNexus with the worktree temporarily detached at `629b931`: `npx -y gitnexus detect-changes -s compare -b 8d04044` → `Changes: 5 files, 13 symbols` / `Affected processes: 0` / `Risk level: low`. Neither run is recorded as done before the commit (U2). |

## B. `831d5a0` (owner decisions D1–D3), first verification

### Tests
- HEAD (`443582a`): `.venv/bin/python -m pytest -q` → `92 passed in 5.79s`. `tests/unit/test_evaluation_blueprints.py` alone → `17 passed in 4.10s`.
- `git archive 831d5a0` copy → `45 passed in 4.55s`. The blueprint file has `17 tests collected`, matching the report's "Test count unchanged (17 in the blueprint file), 45 in total" (`EVAL-001.md:37`).
- `git diff --stat 831d5a0 HEAD -- data/evaluation tests/unit/test_evaluation_blueprints.py scripts/evaluation` → empty. The ground truth and its tests are unchanged since `831d5a0`.

### Checks

| # | Claim / item (`831d5a0`) | Result | Evidence |
|---|---|---|---|
| B1 | D1: every expected and alternate source of an answerable case has a slot | PASS | Scratch script over the parsed YAML: `missing slot: []`; no corpus-insufficient case carries a slot. `git grep -c "slot:"` → 63. |
| B2 | Slot layout: cross-document cases have one slot per document, 022 has one slot per method, the rest have one slot | PASS | Script: `slot-count histogram: {1: 31, 2: 5}`, `multi-slot: ['BP-EVAL-022', 'BP-EVAL-029', 'BP-EVAL-030', 'BP-EVAL-031', 'BP-EVAL-032']`. 029 S1 #10 / S2 #22; 030 S1 #03 / S2 #28; 031 S1 #04 / S2 #26 + alternate #20; 032 S1 #13 / S2 #10; 022 S1 = WithRedirects (H3 + older H2), S2 = WithReExecute (H3 + older H2), all #13. This matches `evaluation-spec.md:51` and design §18 `:124`. 022's `expected_behavior` says "Both methods appear in the top 5", which justifies two slots. 017's `expected_behavior` asks for a contrast, not both sections in the top 5, so one slot is consistent with design `:124`. |
| B3 | `stands_in_for` fully replaced; 031's citation criterion accepts #20 | PASS | `grep -rn stands_in_for` (md/yaml/py) → only the new test's negative assertion (`test_evaluation_blueprints.py:197`) and historical text (reviews, report, worklog). 031 citation: "One citation per slot: S1 from #04 '`default` expressions'; S2 from #26 'Value types and reference types' or #20 'Familiar C# features'." The other cross-document cases say "One citation per premise; each from the matching document". Each of their slots holds one document, so this means the same thing. |
| B4 | New test `test_sources_are_grouped_in_evidence_slots` can fail; "failed before tagging" | PASS | The `831d5a0` test file run against the `831d5a0~1` blueprint fails on `assert 'stands_in_for' not in …` (the author's stated reason). Mutations on a HEAD copy, one at a time (blueprint restored after each; sha256 `952173a0…3913` equal to the checkout afterwards): baseline `1 passed`; #20 alternate slot removed → `1 failed`; #20 slot `S3` → `1 failed`; 031 #26 moved to S1 → `1 failed`; 029 #22 moved to S1 → `1 failed`; slot value `X1` → `1 failed`. **Gap:** 022's ReExecute entries collapsed into S1 → `1 passed`. No test pins 022's two-slot split (N1). |
| B5 | "Coverage matrix unchanged" | PASS | `831d5a0` does not touch `coverage-matrix.yaml`. Re-generated on a HEAD copy with `scripts/evaluation/build_coverage_matrix.py`: sha256 `bf9109d5…1481` before and after. This is the same hash the first review recorded. |
| B6 | D2 written into the spec, the design and the cases (034, DEV-005, DEV-006; "the others already said so") | PASS (note) | `evaluation-spec.md:37-38` labels, design §11 `:80` and the §20 row. The scratch script prints all 6 insufficient cases. 034 and DEV-005 have the new D2 variation. DEV-005 and DEV-006 have "any citation must not be presented as supporting an answer". DEV-006, 036, 033 and 035 already had a related-content variation. The variations of 033 ("may mention what the documents do cover") and 035 ("may say the documents only link …") do not repeat the "not presented as the answer" condition. The general D2 rule in `evaluation-spec.md` covers them (note, N4). |
| B7 | D2 routing rule as committed in `831d5a0` | PASS at HEAD (historical gap) | In `831d5a0` the spec said: "if the system marks the answer insufficient, the result is `correct_refusal` (no judge call)". That skipped the check on an insufficient answer that carries a related note or related citations and presents them as the answer, which D2 itself calls `hallucination`. HEAD already fixes this: `evaluation-spec.md:40-44` splits a bare message (no judge) from "insufficient + related note or citations" (judge refusal check). This is labelled "routing amended by the owner 2026-09-24, REORIENT-001 C1" (`56ae159`), and `09b-EVAL-003b-metrics-and-judge.md:33-35` has the same three rows. No action needed (N3). |
| B8 | D1 hit rule in the spec is consistent with the downstream prompt | PASS (note) | `evaluation-spec.md:48-54` and `09b:10-15,56` agree: all slots, any source within a slot, secondary = fraction of slots, MRR = first chunk that hits any slot. Note: both of 022's slots are #13, so `source_hit@5` and the source-level slot fraction cannot tell them apart. Only `section_hit@5` enforces "both methods". `09b:12` says the secondary value differs for 022; that is true only at section level (N2). |
| B9 | D3: 030 stays cross-document | PASS | 030 `scope: cross-document`, 2 slots (#03, #28). Its blueprint is unchanged in `831d5a0` (the `question_notes` change is from `ce04909`, first review #4). |
| B10 | Re-check sheet covers `831d5a0`'s ground-truth changes | PASS (note) | `EVAL-001-owner-recheck.md:6` says every case got `slot` and that slots are "not repeated below". The 022 block (`:35`) names its two slots, the 031 block (`:73-78`) the S2 alternate and the per-slot citation rule, and the table (`:115,118,119`) the D2 changes to 034, DEV-005 and DEV-006. **Not on the sheet:** design §18's remark that 017 "has one slot; the owner can split it" (`evaluation-dataset-design.md:124`). The owner may never be asked about it (N5). |
| B11 | Owner actually took D1–D3 | UNVERIFIED (U1) | Recorded in `evaluation-spec.md:3`, review `:178-181`, `AI_WORKLOG.md:76-79` and the commit message. The conversation with the owner is not an artifact. Same standing as the first review's A14. |
| B12 | GitNexus for `831d5a0` | PASS (after the fact) | Worktree temporarily detached at `831d5a0`: `npx -y gitnexus detect-changes -s compare -b 831d5a0~1` → `Changes: 7 files, 17 symbols` / `Affected processes: 0` / `Risk level: low`. Over the whole range `831d5a0~1`→`629b931`, with `8d04044` included: `14 files, 36 symbols`, `0` processes, `low`. The tool also printed a warning that its FTS extension is not installed. After the runs the worktree went back to `verify-eval-001-reverify` @ `443582a`, and `git status --short` was empty. Not recorded before the commit (U2). |

## C. Claims vs reality (both commits)

| Claim | Result |
|---|---|
| `629b931` message: 9% (0.094), 17 checks, 85 quotes, status lines, 22/1/1 tally | PASS (A1–A4) |
| `831d5a0` message: slots S1/S2, #20 in 031's S2, 022 one slot per method, "slot test failed before tagging and passes after", D2 applied to 034/DEV-005/DEV-006, D3 unchanged, "Coverage matrix unchanged. 45 tests pass." | PASS (B1–B6, B9; 45 on the `831d5a0` copy) |
| Report `EVAL-001.md:36-39` (D1/D2/D3 bullets, "Test count unchanged (17 …), 45 in total") | PASS |
| Ledger mapping table (REORIENT-001 re-run column) | PASS. Every check reproduces (A1–A5). Its line numbers `master-plan.md:29/:167` are correct for `629b931`; the master plan was restructured later. |

No fabricated number was found.

## D. Project rules
- Layers: `grep -rnE "chromadb|google\.genai|PySide6" src/knowledge_assistant/core src/knowledge_assistant/application` → no hits. The structure test is among the 92 that pass. PASS
- Model names: `grep -rnE "gemini-[0-9]" src scripts` → no hits. PASS
- Secrets: `git grep -nE "AIza[0-9A-Za-z_-]{30}"` → no hits. PASS
- Corpus: `git diff --stat 916b5bc HEAD -- corpus` → empty. Excluded IDs: `git grep -nE 'source_id: "(14|19|24|25|27)"' -- data` → no hits. PASS
- Eval freeze: `git tag -l 'eval-freeze*'` → none. N/A (EVAL-002).
- Ground truth written before indexes: `831d5a0` changes ground truth before any index exists (RAG-001b not started). PASS

## E. Scope
- `629b931` touches only the files the fix prompt names. PASS
- `831d5a0` carries out owner decisions. Two choices in it are the author's, not the owner's: 022 gets two slots, and 017 keeps one. Both are disclosed (design §18, commit message). 022 is on the re-check sheet; 017 is not (N5). It also appends an "Owner decisions" section to the author's own blueprint review response, which is allowed (the reviewer's sections 1–4 are unchanged).
- `831d5a0` replaces the `stands_in_for` test with a broader one. It now applies to all answerable cases, not only cross-document ones, and B4 shows it can fail. This does not weaken the tests.

## F. Quality spot-read
- `test_sources_are_grouped_in_evidence_slots` (`test_evaluation_blueprints.py:195-210`):
  - `str(e.get("slot"))` makes a missing slot fail the `S\d+` match. Good.
  - Alternate slots must be a subset of the expected slots, so an alternate cannot open a slot of its own.
  - For cross-document cases each slot must hold exactly one document, and the documents must differ. This relies on each cross-document slot having exactly one expected source_id. That holds today, and a two-document slot would fail loudly rather than pass.
  - Gap: nothing checks which non-cross-document cases have several slots (N1).
- `evaluation-spec.md` §Retrieval hit rule: clear and consistent with 09b (B8). The source-level note for 022 is N2.

## G. Explain-it-back
The fix sessions' chat reports are not visible (U3). The execution report's D1/D2/D3 bullets are correct, with one clarification: "022 has two slots because its blueprint requires both methods" is true for section hit. At source level both slots are #13 (N2).

With this re-verify, EVAL-001 is `verified`. EVAL-002 has three entry conditions (`task-ledger.md` row 02). Two are now met: EVAL-001 verified, and REORIENT-001 verified. The third is not: every `owner verdict:` line in `EVAL-001-owner-recheck.md` (`:21,31,41,51,60,70,82,95,121`) is still empty, so **EVAL-002 stays blocked**.

## Verdict
**ACCEPT.** Fixes 1–5 of the first review pass their checks (fix 4's second half is superseded by owner decision D2). `831d5a0` reproduces: every source has a slot and the layout matches the spec; the new slot test fails when it should; the coverage matrix is byte-identical; and the tests pass (45 at the commit, 92 at HEAD). No code, corpus or matrix changed. Together with the first review, EVAL-001 as a whole is accepted.

**FAIL: 0. UNVERIFIED: 3**, none of them checkable after the fact:
- U1: the owner's D1–D3 decision event;
- U2: pytest and `detect_changes` before the two commits (both re-run afterwards: 45 passed, 0 processes, risk low);
- U3: the fix sessions' chat reports.

Open, non-blocking:
1. **N1 (test gap, low):** no test pins BP-EVAL-022's two slots. Merging them into S1 still passes (B4). Consider a check in EVAL-002's schema test that the multi-slot set is exactly {022, 029, 030, 031, 032}, or that a case whose `expected_behavior` requires several sections has several slots.
2. **N2 (EVAL-003b note):** for 022, source-level hit and slot fraction cannot tell its two #13 slots apart; only section hit enforces "both methods" (`09b:12` wording).
3. **N3 (resolved):** the `831d5a0` refusal routing auto-labelled every insufficient answer `correct_refusal`; the owner's REORIENT-001 C1 amendment fixed this (`evaluation-spec.md:40-44`).
4. **N4 (wording):** 033 and 035 variations omit D2's "not presented as the answer" condition; the spec's general rule covers them.
5. **N5 (owner):** design §18 says the owner can split 017 into two slots, but the re-check sheet does not ask. The owner can add `change: BP-EVAL-017: split slots` to the sheet's final verdict line if wanted.
6. **Owner, blocking EVAL-002:** fill every `owner verdict:` line in `EVAL-001-owner-recheck.md`.
