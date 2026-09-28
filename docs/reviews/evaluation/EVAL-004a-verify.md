# EVAL-004a — VERIFY (independent check)

Verifier session, own git worktree (`.claude/worktrees/verify-eval-004a`, branched from `origin/eval-004` at `83485fc`).
**Zero Gemini requests.** `.env` was never opened; the key was never read or printed. `OPENBLAS_NUM_THREADS=1` set for
every command that touches embeddings/BLAS. Scope: **EVAL-004a only** (runs + judging + owner spot-check). EVAL-004b
(tables, EPIC-05 report) has not started (needs 09c) and is out of scope here.

Inputs: `agents/prompts/11-EVAL-004-run-and-report.md`, `agents/prompts/_common.md`, `docs/reports/execution/EVAL-004a.md`,
commits `756d4b8`, `07264fc`, `936f0c5`, `3b19dd7`, `ce51d08`, `fb74118`, `83485fc` on branch `eval-004`, `CLAUDE.md`,
ADR-0004 (judge model).

## A. Acceptance / gate items

| Item | Result | Evidence |
|---|---|---|
| HEAD frozen at one commit for both arms, `git_dirty: false` | PASS | Both `run.json`: `"git_commit": "491f1371d8032d8496b78d6a2893375e07ae4e5e"`, `"git_dirty": false`, `"git_dirty_files": []` |
| No config/prompt/code change before/during/after the runs | PASS | `git diff origin/dev...eval-004 --name-status` (see D below) touches only `AI_WORKLOG.md`, `docs/plans/task-ledger.md`, `docs/prompt-log/...`, `docs/reports/execution/EVAL-004a.md`, `validation/evaluation/*`, `data/evaluation/results/*` — no `src/`, `config/`, `scripts/`, `prompts/`, `tests/` |
| Owner's run order followed (estimate → A → re-estimate → B → judge A → judge B, one heavy process at a time) | PASS (documented deviation, owner-authorized) | `run.json` timestamps are strictly sequential (23:07→23:09 A, 23:10→23:12 B, 23:13→23:15 judge A, 23:15→23:17 judge B, 23:19 resume); report §"Deviations" states the owner replaced prompt steps 1–2 (retrieval-only pass, 3-case dry run) — explicit, not silent |
| `judge_error` handled by the documented rule (one identical resume, then leave unlabelled) | PASS | Both judge-error attempts present in `judgements.jsonl` (B, 32 raw lines); resumed call reproduced the same error; record listed in `summary.json` `unlabelled` everywhere (see C5) |
| Owner spot-check built and graded (ledger row 11 task from EVAL-003b addendum) | PASS, with a materially incomplete write-up — see C/G and the fix prompt | `validation/evaluation/judge-spot-check.md` + `-judge.md` exist, graded (`3b19dd7`/`ce51d08`/`fb74118`); recomputation below shows the report's headline number needs a caveat |

## B. Tests

```
.venv/Scripts/python.exe -m pytest -q -m "not gemini"
775 passed, 1 deselected in 24.01s
```
Matches the execution report's claim exactly (no code changed on this branch, so the count is unchanged from EVAL-003b's verify). No new tests were added by this task (confirmed: no `tests/` file in the `origin/dev...eval-004` diff), which is correct — this task produced data/docs, not code.

## C. Claims vs reality

All numbers below were **independently recomputed from the committed files**, not copied from the report.

**C1. Run/record counts.** `records.jsonl` (raw lines, both arms): A=36, B=36. `status` = `ok` on every one, 0 `error`. `model_used`: A `{None: 6, 'gemini-3.5-flash-lite': 30}`, B `{'gemini-3.5-flash-lite': 31, None: 5}` (11 gate answers total). `fallback_used` = `False` on all 72 records. `retry_count` = `0` on every record and every judgement line (61 total). Matches report exactly.

**C2. `llm_http_requests` / quota.** `run.json` invocations: A `llm_http_requests: 30`, `embedding_requests: 36`, `embedding_cache_misses: 36`; B `llm_http_requests: 31`, `embedding_requests: 0`, `embedding_cache_hits: 72`. Judge calls are not in `run.json` (no committed judge-side HTTP counter); they equal the raw line count of `judgements.jsonl` — A 29, B 32 (30 ok + 2 judge_error for the same case) — sum 61, matching the report's "29(A)+31(B)+1(resume)=61". Total LLM = 61 answers + 61 judge = 122, embedding = 36+0 = 36. All PASS.

**C3. `judge_model` / `model_used` = answer model.** `config.py`: `ANSWER_MODEL` and `JUDGE_MODEL` both default to `gemini-3.5-flash-lite`; no env override is visible in either `run.json` (both record `"answer_model": "gemini-3.5-flash-lite"`). Every one of the 61 raw judgement lines has `judge_model` = `model_used` = `gemini-3.5-flash-lite`, `fallback_used: false`. PASS.

**C4. Gate refusals on answerable cases.** A: 001 (top1 0.6779), 016 (0.6269), 018 (0.6753), all `< 0.686`, `model_used: null`. B: 016 (0.6246), 018 (0.6483), `< 0.686`. B/001 (top1 0.6908 ≥ 0.686) was **not** gated and got an LLM answer — correctly excluded from the report's B list. Swept every `gate_fired: true` record in both arms: A also fires on Q-EVAL-033/034/036, B on the same three; `expected-spans-v1.json` confirms all three are `answerable: false` — the gate firing there is correct behaviour, not a defect, and no other answerable record has `gate_fired`. PASS, and extended beyond what the report showed.

**C5. Q-EVAL-002/B `judge_error`.** Both attempts are in `judgements.jsonl` (raw lines, same `case_id`/`arm`/`answer_sha256`), both `status: judge_error`, `error: "citation markers [22] are not exactly [1]"`. `summary.json`'s `unlabelled` list contains `Q-EVAL-002:B` in every breakdown slice (`overall`, `arm/B`, `language/vi`, etc.) — excluded from the denominator, not guessed. **Source-id-copied-into-marker hypothesis: CONFIRMED**, with prompt-level evidence beyond what the report offered: the record's one citation is marker `1` → chunk `22:fixed-1600:0000` (`source_id: "22"`). I rebuilt the actual judge prompt for this record offline with `judge.py`'s own `build_judge_prompt`/`cited_passages` (no LLM call) and searched every line for the token `22`: it appears **only** as `#22` — once in the citation-criteria bullet ("Cites #22...") and once in the passage header (`[1] #22 — Querying Data`) — never as a marker number. The judge's malformed JSON gave `"marker": 22`, which is the source id sitting immediately after the real marker `[1]` in the prompt, and nowhere else does "22" appear. This is about as close to proof as static evidence gets.

**C6. Duplicate rule.** Swept **all 36 records per arm** (not just the 4 named cases): zero top-5 chunks in either arm ever carry a non-empty `duplicate_chunk_ids`. Arm A total `duplicates_dropped` across all cases = 6 (003:1, 004:1, 024:3, 027:1 = 6, matching the 4 named cases; no other arm-A case dropped anything); arm B total = 0. `summary.json`'s own `breakdown.overall.retrieval.duplicate_rule_changed` = `{"n": 32, "count": 0, "cases": []}` on **both** arms (n=32 = the 32 answerable cases retrieval metrics run over). Independent re-derivation (own script, read-only Chroma + cached-embedding lookup, zero live calls) for the 4 named arm-A cases: recomputed top-5 chunk IDs are **identical** to the committed record for all 4, recomputed `duplicates_dropped` matches exactly (1,1,3,1), and every duplicate-group member (the dropped twin of a kept chunk) falls in overfetch ranks 6–13 — e.g. Q-EVAL-003's duplicate pair sits at pre-dedup ranks 6 and 13, Q-EVAL-024's four-way group at ranks 7–10 — always outside the top-5 cut, never inside it. PASS, with independent numeric proof, not just a re-read of the report's own reasoning.

**C7. Re-running the pasted scripts.** Appendix A (`score_runs.py`) and Appendix B (`build_spot_check.py`), copied verbatim from the report and run in an isolated scratch directory against the same committed inputs (`records.jsonl`, `judgements.jsonl`, `expected-spans-v1.json`, `pricing.json`, the two chunk files):
- `summary.json` (both runs): **byte-identical** to the committed files after LF normalization (Windows `write_text` CRLF vs. git's LF-on-commit, exactly as the report notes) — SHA-256 `02e6f4f6...` (A) and `9dcc4eae...` (B) match the report's printed hashes exactly.
- `judge-spot-check-judge.md` (the key): **byte-identical**, including all 10 picks (`S01 Q-EVAL-017 A ... S10 Q-EVAL-017 B`) and strata sizes (`A/correct 23, A/correct_refusal 1, A/partially_correct 5, B/correct 23, B/correct_refusal 1, B/partially_correct 6`), reproduced from `random.Random(42)` with no code change.
- `judge-spot-check.md` (the blind sheet): I diffed my regenerated (empty-column) sheet against **the actual pre-grading committed version** (`git show 936f0c5:validation/evaluation/judge-spot-check.md`, byte-identical to `756d4b8`'s copy), not against today's owner-graded copy. After normalizing the `git show`/PowerShell redirection's BOM and CRLF artifacts, the two are **byte-identical** (SHA-256 `b1754a4d...` both). The later diff against today's file shows only the owner's added grades, which is expected and is not a discrepancy. PASS — full reproducibility, checked against the correct baseline.

**C8. Owner spot-check headline number — see G (Explain-it-back) below; this is the one finding that changes the verdict.**

## D. Project rules

- **Layer imports / no code touched.** `git diff origin/dev...eval-004 --name-status` (using `origin/dev`, not local `dev` — see note under E) touches only: `AI_WORKLOG.md` (M), `docs/plans/task-ledger.md` (M), `docs/prompt-log/claude-code/EVAL-004a.md` (A), `docs/reports/execution/EVAL-004a.md` (A), `data/evaluation/results/20260928-eval-{A,B}-full-491f137/{records,judgements,run,summary}.json*` (A), `validation/evaluation/judge-spot-check{,-judge}.md` (A). **No `src/`, `config/`, `scripts/`, `tests/` file.** Layer-import rules are therefore not engaged by this task (already checked by EVAL-003b's verify for the code these runs exercise).
- **Model names only in config, not hard-coded.** Confirmed in `config.py`: `ANSWER_MODEL`/`JUDGE_MODEL`/`FALLBACK_MODEL` all `os.getenv(..., "gemini-3.5-...")` defaults; both `run.json`s record the resolved names, no literal elsewhere in the diff.
- **No API key in repo/logs.** `AIza[0-9A-Za-z_-]{35}` scan: 0 matches across both run folders, both spot-check files, the execution report, the prompt log, `AI_WORKLOG.md` and the ledger. Also scanned the full patch text of every commit unique to `eval-004` (`git log -p origin/dev..eval-004`): 0 matches — the key was never in history and later removed, it was never present.
- **Corpus untouched, excluded docs unused.** No `corpus/` file in the diff. Swept every retrieved chunk's `source_id` in both arms' `records.jsonl`: none of `{14, 19, 24, 27}` (the excluded sources) appears.
- **Eval question file hash unchanged since freeze.** `git diff --quiet eval-freeze-v1 HEAD -- data/evaluation/questions/{eval-v1,dev-v1}.jsonl` → exit 0 (no diff against the tag itself, not just against the config's recorded hash). `git log --oneline -- data/evaluation/questions/eval-v1.jsonl data/evaluation/questions/dev-v1.jsonl` shows no commit after the freeze (`739676f`). Both `run.json`s record `eval-v1.jsonl: 3436870e...`, `dev-v1.jsonl: 37d349e5...`, matching the current working-tree files' own SHA-256 exactly.
- **No eval-set question used for tuning.** No code/config/prompt file changed on this branch (see above) — there is nothing that could have been tuned.

## E. Scope

- **Correct base for the scope diff is `origin/dev`, not local `dev`.** This worktree's local `dev` ref was stale at `7db105b` (before PR #17 merged); `origin/dev` is at `491f137`, the actual commit `eval-004` branched from. `git diff dev...eval-004` (local) misleadingly shows `config/pricing.json`, `config/prompts/judge_v1.md`, `judge.py`, `scoring.py`, `judge_run.py`, `config.py` etc. as "added" — these are EVAL-003b's own files, already on `origin/dev`, just not on this worktree's stale local branch pointer. Using `origin/dev` (fetched fresh) gives the clean data/docs-only diff in D. This is a caveat for whoever runs this check next, not a defect in the task.
- Everything else in the diff is data (`data/evaluation/results/`) or docs (`docs/`, `validation/`, `AI_WORKLOG.md`) — no undisclosed decision found beyond what §"Deviations from the prompt file" in the execution report already states (owner replaced the retrieval-only pass and 3-case dry run; merged PR #17 on the owner's instruction).
- `gitnexus_detect_changes(scope=all, repo=Tech-docs-RAG)` run before this commit: `risk_level: low`, 2 changed symbols (both `AGENTS.md`/`CLAUDE.md`, the main checkout's pre-existing uncommitted edits noted in the execution report, unrelated to this branch), 0 affected processes. The index tracks the main checkout, not this worktree — same limitation EVAL-003a/b's verify already documented.

## F. Quality spot-read

- `dedupe_by_passage` / `Retriever.retrieve` (`application/retrieval/retrieve.py`): read line by line. Overfetch = `top_k + overfetch`, dedup key = SHA-256 of link-stripped passage body (not `content_hash`, deliberately, per the docstring, so link-only variants still collapse) — this is exactly what my independent recomputation in C6 exercised and matched. No silent fallback: `RetrievalError` raised on an empty store or a vector-count mismatch, not swallowed.
- `map_result` (`application/evaluation/metrics/mapping.py:50`): read line by line. `contradicts_ground_truth` → `INCORRECT` always wins over point coverage; `all yes` → `CORRECT`; `any(yes/partial)` → `PARTIALLY_CORRECT`; otherwise `INCORRECT`. This is the exact function I used (not a re-implementation) to recompute labels from the owner's blind grades in G below — no edge case (empty required-points list would raise via `_check_coverage`, not silently mis-score; not exercised here since every sampled record has ≥1 required point).
- `cited_passages` / `build_judge_prompt` (`application/evaluation/judge.py:152-181`): a citation whose chunk isn't in the retrieved list raises `EvaluationError` rather than being dropped — used this exact function in C5 to rebuild the real prompt and confirm the marker/source-id collision hypothesis.

## G. Explain-it-back — the one finding that changes the verdict

The report's four "Explain it back" bullets (frozen tree/Goodhart, arm B's 0-embedding reuse, unlabelled judge_error, blind+stratified spot-check rationale) are all **correct** and match what I independently reproduced above.

**But the "Owner spot-check" section's headline number is incomplete**, and the instruction for this check was explicit: *"report agreement on the label (x/10) and on citation support, and list every disagreement with both reasons — do not smooth it."* The report and ledger row 11 report only the owner's self-answered "agree with the judge?" column: **9/10, only S03 disagrees**. That column is a real, legitimate data point, but it is not the whole picture, and I recomputed the alternative reading with the project's own `map_result` function (not by eye):

| S-id | Case:arm | Judge's required-point coverage | Owner's **blind** required-point coverage | Judge label | `map_result(owner's grades)` | Owner's self-reported "agree?" |
|---|---|---|---|---|---|---|
| S01 | Q-EVAL-017:A | yes, yes, partial | yes, yes, **no** | partially_correct | partially_correct (match) | yes |
| S02 | Q-EVAL-035:B (refusal) | — | — | correct_refusal | correct_refusal (match) | yes |
| S03 | Q-EVAL-012:A | yes, partial, yes | **partial**, **no**, yes | partially_correct | partially_correct (match) | **no** (documented in the report) |
| S04 | Q-EVAL-035:A (refusal) | — | — | correct_refusal | correct_refusal (match) | yes |
| S05–S08 | 024:A, 025:A, 024:B, 022:B | all yes | all yes | correct | correct (match) | yes |
| S09 | Q-EVAL-020:B | yes, **partial**, yes | yes, **yes**, yes | partially_correct | **correct (MISMATCH)** | yes |
| S10 | Q-EVAL-017:B | yes, yes, **partial** | yes, yes, **yes** | partially_correct | **correct (MISMATCH)** | yes |

(Recomputed with `map_result(True, False, False, True, verdict)` from `metrics/mapping.py`, fed the owner's own blind per-point grades — command run interactively, output pasted above; `S09`/`S10` produce `correct`.)

- **Label agreement, recomputed from the owner's own blind grades: 8/10**, not 9/10 — S09 and S10 are undocumented disagreements the owner's "agree?" column doesn't surface, because on both the owner rated a point `yes` where the judge rated it `partial` (S09/P2, S10/P3), and doing so flips the record's overall label from the judge's `partially_correct` to `correct` under the project's own mapping rule. The owner answered "agree with the judge?" = yes on both, which is a legitimate subjective read (they may have judged the overall answer "good enough" without re-deriving the formal label), but it is a different question from "does a mechanical recompute of your own point grades reproduce the judge's label," and the report conflates the two.
- **Full point-level agreement (every required point + contradicts + unsupported-claims identical): 6/10.** S01 (P3), S03 (P1, P2 — already documented), S09 (P2) and S10 (P3) each have at least one point where the owner's blind grade differs from the judge's.
- **Citation-support agreement: 25/25 markers, 10/10 items** — every citation marker across the whole sample was rated `yes` by both the judge and the owner. This is real full agreement, but it is uninformative about the judge's ability to catch a *bad* citation: the sample happens to contain zero cases where either side rated a citation `partial`/`no`, so this number shows no disagreement rather than proving detection.
- **Sample coverage:** the 10 picks cover only **7 distinct questions** (Q-EVAL-017, 020, 022, 024, 025, 012, 035); three questions (017, 024, 035) were drawn once per arm each, which the report's own note about S05/S07 and the owner's "TWICE" comment on S07 already flags as expected under per-(arm, label) stratification, not a sampling bug.
- Reasons, quoted from the judge's `reason` field where the owner left no note: S09 — *"The answer successfully covers the rule, the uint value of the literal, and the unchecked cast method. It only partially covers P2 because it omits explicitly mentioning that it is not int -1."* S10 — *"The answer correctly covers points 1 and 2, and partially covers point 3 by mentioning the service container registration but omitting the UseMiddleware factory resolution detail."* Neither the owner's S09 nor S10 row carries a note explaining the more lenient grade; I did not infer one.
- **Blinding chain of custody (Check 8):** the S-id → case/arm mapping *was* briefly committed in plain text inside the execution report (`756d4b8`, 06:25:22 +07) — "Picks (also in the key file): S01 Q-EVAL-017 A, ..." — before being redacted (`936f0c5`, 06:27:54 +07, "keep the spot-check mapping out of the report"). This is already self-disclosed in `AI_WORKLOG.md` ("Blinding leak... found by the advisor's final review"). Confirmed from commit timestamps that the redaction landed **~83 minutes before** the owner's first grading commit (`3b19dd7`, 07:50:25 +07), and the blind grading file itself (`judge-spot-check.md`) never contained the mapping at any commit (`git diff 756d4b8 936f0c5 -- validation/evaluation/judge-spot-check.md` is empty). No evidence the owner viewed the ~2-minute exposure window. PASS, already correctly self-reported — not a new defect, but worth confirming explicitly since the task asked for it.

## Verdict: **ACCEPT WITH FIXES**

Every recomputed number matches the report **except** the "Owner spot-check" headline, which reports only one of two legitimate readings of the same data and omits the S09/S10 point-level disagreements entirely. Nothing here implicates the runs, the judge, the duplicate rule, or the scoring pipeline — all of that is independently reproduced byte-for-byte or numerically. The fix is a documentation correction only: add the recomputed 8/10 (or present both numbers with their different meanings, un-smoothed) to the execution report and ledger row 11. **`validation/evaluation/judge-spot-check.md` must not be edited** (owner-graded, per instruction) — the fix is confined to `docs/reports/execution/EVAL-004a.md` and `docs/plans/task-ledger.md`.

0 FAIL among independently-reproduced numbers; 1 finding (G) that the execution report's own prose does not support without a caveat. No UNVERIFIED items — every check that could be run without a live Gemini call was run.

---

## Fix prompt (docs-only, run in a new session)

1. **`docs/reports/execution/EVAL-004a.md`, "Owner spot-check" → "Owner result" subsection.** After the existing 9/10 table, add: recomputing `map_result` (`application/evaluation/metrics/mapping.py`) from the owner's own blind per-point grades gives **8/10** label agreement, not 9/10 — S09 (`Q-EVAL-020:B`) and S10 (`Q-EVAL-017:B`) also disagree: the owner rated a required point `yes` (S09/P2, S10/P3) where the judge rated it `partial`, which is lenient enough to flip the record's mapped label from `partially_correct` to `correct`. State both numbers and what each means (9/10 = the owner's own overall "agree?" answer; 8/10 = the same grades passed through the project's own scoring formula). Add: full point-level agreement (every field identical) is 6/10 of 10 items; citation-support agreement is 25/25 markers across the sample, but the sample contains no case where either side rated a citation `partial`/`no`, so it does not test whether the judge would catch a bad one. Note the sample covers 7 distinct questions, not 10.
   - Check that proves it: `map_result(True, False, False, True, verdict)` from `metrics/mapping.py`, called with a minimal object exposing `required_points=[owner's blind grades]` and `contradicts_ground_truth=False`, for S01/S03/S09/S10; compare to the judge's assigned label read from `judge-spot-check-judge.md`.
2. **`docs/plans/task-ledger.md`, row 11, Open items.** Replace "**agrees with the judge on 9 of 10**; S03 (Q-EVAL-012:A) disagrees on P2..." with a version naming both numbers (9/10 self-reported agreement; 8/10 recomputed label agreement, S09/S10 added) so a reader of the ledger alone isn't misled.
3. Do **not** touch `validation/evaluation/judge-spot-check.md` or `-judge.md` — they are the owner's graded record and must stay exactly as graded.
4. Re-run this file's re-derivation to confirm the corrected numbers, then re-verify with `99-VERIFY` before setting ledger row 11's EVAL-004a portion to `verified` (the row as a whole stays `in progress` until EVAL-004b/09c lands).
