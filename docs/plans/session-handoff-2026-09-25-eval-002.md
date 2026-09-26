# Session handoff 2026-09-25: EVAL-002 (unattended cloud run)

Branch `eval-002` (from `dev` `9ee70bd`) · PR → `dev`: see the bottom · Report: [EVAL-002](../reports/execution/EVAL-002.md)
Result: questions + ground truth written and validated; **not frozen**. M1 is not reached until you approve and tag.

## 🚩 Owner actions, in order
1. **Review** [`docs/reviews/evaluation/eval-v1-review.md`](../reviews/evaluation/eval-v1-review.md): start with "Look at these first" (9 cases), then the checklist over the table (≈ 20 min).
2. **Answer** the AI decisions (below) and ground-truth proposal G1 (yes/no each). Fill the verdict line in the sheet.
3. **Fix** if needed:
   - wording → `data/evaluation/questions/question-wording-v1.yaml`;
   - ground truth → `data/evaluation/questions/blueprint.yaml` (then also `scripts/evaluation/build_coverage_matrix.py` if counts change);
   - then run:
   ```
   .venv/Scripts/python.exe scripts/evaluation/build_question_files.py
   .venv/Scripts/python.exe scripts/evaluation/validate_questions.py
   .venv/Scripts/python.exe scripts/evaluation/build_review_sheet.py
   .venv/Scripts/python.exe -m pytest
   ```
4. **Merge** PR `eval-002` → `dev` (after your review; CI/pytest green on Windows).
5. **Freeze** on `dev` (the tag time is the proof that ground truth predates any index; `data/chroma/` must still hold only `.gitkeep`):
   ```
   git checkout dev && git pull
   certutil -hashfile data\evaluation\questions\eval-v1.jsonl SHA256
   certutil -hashfile data\evaluation\questions\dev-v1.jsonl SHA256
   ```
   Write `docs/snapshots/evaluation/eval-v1.md` (commit hash of the merge, both SHA-256 values, date, "approved by the owner"), mark M1/G5A in `master-plan.md`, EPIC-05 and ledger row 02, commit `EVAL-002: freeze eval-v1`, then:
   ```
   git tag -a eval-freeze-v1 -m "EVAL-002: eval-v1 ground truth frozen (owner-approved)"
   git push origin dev eval-freeze-v1
   ```
   From then on, any change = an amendment in `docs/specs/evaluation-spec.md` § Amendments (what/why/date).
6. Only then: RAG-001a (`06a`).

## AI decisions to confirm (applied; none changes ground truth)
| # | Decision | Why / alternative |
|---|---|---|
| A1 | Case IDs `Q-EVAL-001…036`, `Q-DEV-001…006`; `blueprint_id` links to the blueprint. | `EVAL-001` would collide with task IDs. Alternative: reuse `BP-EVAL-…` (blurs plan vs. question). |
| A2 | `expected_answer` = required answer points joined, in English, for EN and VI cases; unanswerable = the refusal sentence. | Parallel pairs must share identical ground truth; the judge compares meaning. Alternative: a VI translation (a second, unreviewed ground truth). |
| A3 | `tags{…}` (09a runner) **and** flat `difficulty`, `cognitive_level`, `size_class`, `failure_mode`, `scope` (design §18); validator checks equal. | The two specs name them differently; keeping both avoids changing either spec. |
| A4 | Generated fields in a separate `generated` object, all null. | Prompt: "generated fields null"; design §18: outputs live in per-arm result files. |
| A5 | Extra copied fields: `evidence[].supports`, `near_miss_sources`, `absence_proof`, alternate `note`. | The judge needs which quote supports which point; the rest aids failure analysis. |
| A6 | Quote check on `normalized.jsonl` section text, whitespace collapsed on both sides, any variant. | "Same normalization EPIC-02 uses" (ADR-0003 D1); variants per D8. |
| A7 | Question wording lives in `question-wording-v1.yaml`; JSONL is built by script and test-checked equal to the build. | Guarantees EVAL-002 changed only wording. |
| A8 | Design §20 items "VI wording rule (identifiers stay English)" and "short code from the page in 016/018" were **followed** in the draft (also 020, 026 per their blueprint notes). | Both were "Proposed"; your approval of the sheet approves them. |
| A9 | Step 0: design §16 sentence aligned with the trimmed 017 note ("partly supports 017's P1"). | Keeps the design consistent with the note you approved. |
| A10 | Review-sheet table cells show code as inline code lines; `build_review_sheet.py` regenerates only the table part. | Code fences can't live in Markdown table cells. |

## Ground-truth proposals (NOT applied)
| # | Case | Proposal | Why |
|---|---|---|---|
| G1 | 011/012 `must_not_claim` | "The type must be public (internal is also allowed)." → "The type must be public (wrong: internal is also allowed)." | A judge could read the parenthesis as part of the forbidden claim. Meaning unchanged, but it is a ground-truth field, so yours to decide. |

## Verify verdict
**ACCEPT** ([EVAL-002-verify](../reviews/evaluation/EVAL-002-verify.md), fresh-context sub-agent, 2026-09-25). 0 FAIL; 2 UNVERIFIED (Windows run; GitNexus not available). No fix round needed.
Non-blocking notes for you:
1. Test gap: the eval/dev *expected-section* overlap check has no test of its own (mutation removing it leaves 19/19 green). Worth a one-test follow-up.
2. Q-EVAL-024 (vi) also leaks the cause ("vì test không chạy trong thư mục output"); added to "Look at these first".
3. Q-EVAL-028's quote matches only after whitespace collapsing (#18 line 29 has a no-break space). Citation matching in EVAL-003b must collapse whitespace the same way.

## Test results
- Baseline `dev` `9ee70bd`: 121 passed (Linux, Python 3.11.15).
- After EVAL-002: 140 passed (19 new in `tests/unit/test_eval_dataset.py`); `validate_questions.py` → OK (36 eval / 32 answerable / 6 dev / 107 quotes).
- Mutation: quote check disabled → 2 failed; restored → green.
- Not run: Windows; GitNexus (`detect_changes`) is not available in this container.

## Branch / commits (`eval-002`)
| Commit | What |
|---|---|
| `4172e98` | Step 0: ledger row 02 ready; 017 note trimmed to P1 |
| `459a902` | Question files, builder, validator, tests |
| `80b83f7` | Review sheet |
| `743f713` | Report, prompt log, worklog, plan status, this handoff |
| `0eb6cfa` | VERIFY EVAL-002: ACCEPT |
| (next) | Verifier notes into sheet + handoff |
