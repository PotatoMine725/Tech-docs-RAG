# EXP-001 — VERIFY (independent check)

Verifier session, own git worktree (`.claude/worktrees/verify-exp-001`, local branch `review-exp-001` tracking
`origin/exp-001` at `c7b440d` — PR #20 into `dev`; the local `exp-001` worktree branch used by the author points to the
same commit). **Zero Gemini requests.** `.env` was never opened; the key was never read or printed.
`OPENBLAS_NUM_THREADS=1` set for every command. No source/tests/data/report file of the task was left modified (one
mutation-test edit to `experiment.py` was reverted immediately after a tool denial — see F). No other verifier was
running (checked `Win32_Process` for `python.exe` before the one full-suite run).

Inputs: `agents/prompts/12-EXP-001-experiment-and-failure-analysis.md`, `agents/prompts/_common.md`,
`docs/prompt-log/claude-code/EXP-001.md` (owner addendum, verbatim), `docs/reports/execution/EXP-001.md`,
`docs/reports/epics/EPIC-06-experiment.md`, `docs/snapshots/experiments/exp-001.md`, ADR-0003, `CLAUDE.md`, commits
`734e8ca` + `c7b440d` on branch `exp-001`.

## A. Acceptance / gate items

| Item | Result | Evidence |
|---|---|---|
| New code limited to `application/evaluation/experiment.py`, `scripts/experiments/compare_arms.py`, tests | PASS | `git diff origin/dev...origin/exp-001 --name-status`: 15 added (8 `data/experiments/exp-001/*`, 4 docs, `experiment.py`, `compare_arms.py`, `test_eval_experiment.py`) + 4 modified docs (`AI_WORKLOG.md`, `docs/plans/{epics/EPIC-06-experiment,master-plan,task-ledger}.md`). No other `src/`/`scripts/` file. |
| `git diff` on `config/` is empty | PASS | `git diff origin/dev...origin/exp-001 -- config/` → empty |
| `experiment.py` reuses `stats.py`, no reimplementation, pure (no I/O) | PASS | Read in full: imports `mcnemar_exact`/`paired_bootstrap_ci`/`wilcoxon_signed_rank` from `stats.py`; no `open`/`json`/`print`/`Path` in the file. All I/O is in `compare_arms.py`, which itself only imports and calls the existing functions. |
| Comparison script writes `comparison.json` + `tables.md` + AUTO blocks in the report, per the table spec | PASS | Re-ran verbatim: `python scripts/experiments/compare_arms.py --run-a 20260928-eval-A-full-491f137 --run-b 20260928-eval-B-full-491f137 --report docs/reports/epics/EPIC-06-experiment.md` → identical console output to the execution report ("report blocks filled: results-overall, results-en, results-vi, results-parallel, chunk-stats, failure-counts, failures, strict-lenient"; "discordant cases: 23; failures A 9, B 9; unlabelled ['Q-EVAL-002:B']"). |
| Reproducibility: outputs byte-identical on re-run | PASS | SHA-256 of all 9 files (`comparison.json`, `tables.md`, `per_case_diff.csv`, `discordant-chunks.{json,md}`, `failures.csv`, `chunk-stats.json`, `failure-overrides.json`, `EPIC-06-experiment.md`) before and after re-run: identical hashes; `git status --short` clean after. |
| Paired statistics: exact McNemar (b/c reported), exact Wilcoxon, paired bootstrap (10,000 resamples, seed 42) | PASS | Independently reimplemented (own script, not importing `stats.py`/`experiment.py`) from the algorithm description in `stats.py`'s docstrings. See C. |
| `per_case_diff.csv` has the required columns; `a_only_hits`/`b_only_hits`/`both_miss` present | PASS | Header: `case_id, language, size_class, difficulty, failure_mode_tag, a_section_hit@5, b_section_hit@5, a_first_hit_rank, b_first_hit_rank, a_result, b_result`; `comparison.json` `section_hit@5.{a_only_hits,b_only_hits,both_miss}` present. |
| Chunk-level explanation data for every discordant case | PASS | `discordant-chunks.json` has exactly 23 keys, matching an independent re-derivation of "discordant" from raw `summary.json` (label differs / groundedness differs / any retrieval metric differs) — see C6. Deviation (disclosed in the execution report): JSON keeps top-5 not top-3, because 3 cases are decided at rank 4–5 — reasonable, not a defect. |
| Failure analysis: deterministic rule order, `override_reason` column, ADR-0003 modes mapped | PASS | See C7. All 6 of ADR-0003's actual "Expected failure modes" bullets (not the prompt's paraphrase) are present as table rows with real case IDs or "not observed (checked cases: …)". |
| Report answers exactly the brief's 5 points; snapshot exists | PASS | `## 1. What changed` … `## 5. What was learned and what to try next` present in order; `docs/snapshots/experiments/exp-001.md` exists and its headline table matches the AUTO tables. |
| No parameter/config changed after seeing results | PASS | Empty `config/` diff (above); `HELD_CONSTANT` keys asserted equal by the script itself (`raise SystemExit` if they differ) and the run actually completed, so they were equal. |

## B. Tests

```
.venv/Scripts/python.exe -m pytest -q tests/unit/application/test_eval_experiment.py
18 passed

.venv/Scripts/python.exe -m pytest -q   (branch, offline)
793 passed, 1 deselected in 20.08s

.venv/Scripts/python.exe -m pytest -q   (origin/dev baseline, same worktree, detached HEAD)
775 passed, 1 deselected in 19.12s
```
775 + 18 = 793, matching the execution report's claimed arithmetic exactly (independently confirmed by actually running
the dev baseline, not just diffing file lists). No other `tests/` file changed in the branch diff.

Read `test_eval_experiment.py` in full: not tautological. `test_binary_row_reports_mcnemar_counts_and_cases` and
`test_continuous_row_uses_wilcoxon_and_descriptive_row_is_not_tested` have hand-worked expected values in comments
(e.g. `b=1, c=2, p = 2*(C(3,0)+C(3,1))/8 = 1.0`; Wilcoxon `W+ = 21, exact p = 2/2^6 = 0.03125`) that I checked by hand
and they are correct. `test_rule_3_ranking_needs_a_cited_wrong_chunk_above_the_first_hit` includes a rank-2 boundary
case (`fact(1, False), fact(2, True)` → `GENERATION`, not `RANKING`) — this is exactly the assertion that would fail
under mutation M2 (`rank >= 3` → `rank >= 2`); see F for why I did not re-execute the mutation.

## C. Claims vs reality

All numbers below were **independently recomputed**, most from the two `summary.json`/`records.jsonl` files directly,
without importing `experiment.py` or `stats.py` (own script, McNemar/Wilcoxon/bootstrap reimplemented from the
docstring description in `stats.py`).

**C1. Sanity targets** (`math.comb`, not copied): 5–0 split p = **0.0625** ✓. b=2,c=3 → p = **1.0** ✓ (matches the
accuracy row). b=11,c=5 → p = **0.210113525390625** ✓ (matches evidence_hit@1, reported 0.210).

**C2. Accuracy, lenient_accuracy, false_refusal, evidence_hit@1, section_hit@5** — recomputed paired on the two
summary files (own pairing code, own McNemar): accuracy n=31, A 0.710/B 0.742, b=2 c=3 p=1.0, Δ=+0.0323,
bootstrap CI [-0.0968, +0.1613] (seed 42, own resampler) — **matches the report row to the digit**, including the CI
bounds, which only match if the bootstrap uses the identical `random.Random(42)` draw order described in `stats.py`.
lenient_accuracy n=31 A 0.871/B 0.935 b=0 c=2 p=0.5 ✓. false_refusal n=31 A 0.129/B 0.065 b=2 c=0 p=0.5 ✓.
evidence_hit@1 n=32 A 0.594/B 0.406 b=11 c=5 p=0.210 Δ=-0.1875 CI[-0.4062,0.0625] ✓. section_hit@5 n=32 both 0.938
b=1 c=1 p=1.0 ✓. A-only/B-only case lists for accuracy: `[020,027]` / `[001,012,022]`, matching the strict/lenient
table's "accuracy" A-only/B-only column exactly.

**C3. tokens_prompt** — n=30, A mean 1628.6 / B mean 2122.6, Δ=494.0, own exact-Wilcoxon p ≈ 0 (report: <0.001), own
bootstrap CI [418.83, 567.23] (report: [418.8, 567.2]) ✓.

**C4. Q-EVAL-002 pairing — real finding.** `Q-EVAL-002:B` is `judge_error`/unlabelled. Confirmed absent from
`accuracy`/`lenient_accuracy`/`false_refusal` (n=31, not 32) and present in `evidence_hit@1`/`section_hit@5` (n=32,
retrieval-level, correct per addendum item 1). **However**, `citation_section_precision` (overall n=28, vi n=13,
parallel n=13) **does include** `Q-EVAL-002` — removing it gives exactly 27, matching `citation_support_rate`'s n.
Reason (confirmed in `summary.json`): `Q-EVAL-002:B`'s `citation.section_precision = 1.0` (`auto_class:
"correct_evidence"`, a deterministic span check that only needs `answered: true`) while `citation.support_rate =
null` and `judge_class: null` (needs the judge, which errored). This is a real, defensible reason — but EPIC-06 §2
states plainly: *"`Q-EVAL-002:B` is unlabelled... **that case is out of every answer-level pair**"* and then, one
sentence later, *"citation rows (**27/28**)"* — the "28" is never explained and directly contradicts the "out of
every answer-level pair" sentence for that one row. The underlying numbers are all correct and shown in the table;
only the prose overclaims. **FAIL** on this one sentence (see fix prompt item 1).

**C5. Q-EVAL-001 gate story** — `records.jsonl`: A `top1_score = 0.677908718585968`, `gate_fired: true`; B
`top1_score = 0.6908349990844727`, `gate_fired: false`. Matches worked example 1 exactly (0.6779 < 0.686 ≤ 0.6908).
OD-9 in `docs/plans/master-plan.md` (row 286): "retrieval gate top-1 < 0.686 (**dev set, Arm A**, one value)" — traces
the "tuned on Arm A" claim to an actual decision record, not asserted from nothing.

**C6. Discordant set (23 cases)** — re-derived from raw `summary.json` with my own rule (label differs, or
groundedness differs (both labelled), or any retrieval metric differs) without importing `discordant_cases()`: **23
cases, exact same set** as `discordant-chunks.json`'s keys. Spot-checked 3 against `records.jsonl` directly (not the
derived `discordant-chunks.json`, to avoid circularity):
- 022:A `retrieved[:5]` `source_id`/`heading_path`: all five are `#13 ... UseStatusCodePagesWithReExecute` variants —
  matches "all five A chunks are #13 version variants of S2 only" exactly.
- 027:B `retrieved[0]`: `chunk_id = 12:fixed-1600:0016`, `display_text[:120]` starts `"h an implementation that also
  supports formatting responses as XML..."` — matches the worked example's quoted text exactly.
- 027:A `retrieved[0].chunk_id = 12:header-1600:0022`, length 1,145 chars — matches "the whole 1,145-char ...
  section" exactly.

**C7. Failure counts and labels** — re-derived `is_failure` (own code, from `summary.json` only): A 9 / B 9, **exact
same case lists** as `failures.csv`/the AUTO:failures table (A: 001,010,012,016,017,018,021,022,030; B:
010,016,017,018,020,021,027,030,031). Spot-checked field-level triggers directly against `summary.json`: 022:A
`section_hit@5=0, slot_fraction@5=0.5` → `retrieval_miss` (matches rule text); 027:B `section_hit@5=1,
evidence_hit@5=0` → `chunking` (matches); 031:B `section_hit@5=0` (despite `result=correct`) → `retrieval_miss`
(matches decision 3's two-slot reading). `failures.csv`: 18 rows, `rule_stage == stage` on every row (no override
used, matching `failure-overrides.json = {}`).

**C8. "447 exact-duplicate chunks" claim** — traces to `data/processed/chunks/stats-arm-a.json`
(`"duplicates_dropped": 447`, `"duplicates_dropped_per_document": {"11": 4, "13": 135, "17": 118, "23": 190}`) — a
pre-existing ingestion-time artefact (also cited in INGEST-002/004's own reports), not fabricated by this task. PASS,
not a FAIL — traceable to a file as required.

**C9. Fence-cut claim (45.05% B vs 3.27% A)** — reimplemented the fence-detection rule independently (own regex-based
`fenced_ranges`/`cuts_code_fence`, not importing `markdown_structure.py`/`stats.py`), applied to
`normalized.jsonl` + `arm-a.jsonl`/`arm-b.jsonl`: **24/733 = 3.27%, 387/859 = 45.05%** — exact match.

**C10. `failure_mode_signals` sums** — same-heading repeats A 46 / B 48, large-doc-off-target A 9 / B 13, link-list
noise 0/0 in both arms: recomputed as `sum(...)` over `comparison.json`'s `failure_mode_signals` — all match the
report's ADR-0003 table exactly. `stats-arm-b.json` `duplicates_dropped = 0` confirmed directly.

**C11. Character counts** in the worked examples — 001:A chunk 848 chars / 001:B chunk 1,600 chars; 027:A chunk 1,145
chars; tiny-doc #29 chunks A `[201, 681, 396]` / B `[1282]` — all recomputed directly from `arm-a.jsonl`/`arm-b.jsonl`
`display_text` lengths, exact match.

**C12. Wording rule — real finding.** Grepped `better|outperform|improv|worse` (0 misuses beyond the rule statement
itself) and, on the advisor's prompt, widened to `ahead|wins|equivalent|superior|beats`. Two hits deserve scrutiny:
- §3 "B ahead"/"A ahead" (section_hit@1 lenient/strict, p=1.000/0.625): immediately followed by "Neither difference is
  statistically reliable (all p ≥ 0.375)" two sentences later — hedged in context, not a FAIL.
- §5 "**Answer quality is equivalent at this n**" (describing accuracy, p=1.0, n=31) directly **contradicts** the
  report's own §2 "threats to validity" paragraph: *"'no statistically reliable difference at n = 31' here means
  'too few disagreements to tell', **not 'the arms are equal'**"*. "Equivalent" and "the arms are equal" are the same
  claim the report itself just said not to make. **FAIL** — self-contradictory wording on the exact metric the rule
  exists to protect (see fix prompt item 2).

## D. Project rules

- **Layer imports.** `experiment.py`: no `chromadb`/`google.genai`/`PySide6` import (grepped). All I/O confined to
  `compare_arms.py` (a script, not `core`/`application`). `test_project_structure.py` is in the 793 passing tests.
- **Model names only in config.** No `gemini-embedding-001`/`gemini-3.5-flash*` literal in `experiment.py` or
  `compare_arms.py` (grepped) — the script reads model names from the runs' own `run.json`.
- **No API key in repo/logs.** `AIza[0-9A-Za-z_-]{35}` scan: 0 matches across every file in the branch diff, and 0
  matches in `git log -p origin/dev..origin/exp-001` (full patch history, not just current file contents).
- **Corpus untouched.** No `corpus/` file in the branch diff.
- **Excluded docs (14/19/24/27) unused, #25 absent.** Swept `source_id` across every chunk in `arm-a.jsonl` and
  `arm-b.jsonl`: none of `{14,19,24,27}` present, `#25` absent from both.
- **Eval question hash unchanged since freeze.** `data/evaluation/questions/eval-v1.jsonl` SHA-256 =
  `3436870e...` (matches the report exactly); `git diff --quiet eval-freeze-v1 HEAD -- data/evaluation/questions/eval-v1.jsonl`
  → exit 0 (no diff against the tag itself).
- **No eval-set question used for tuning.** No config/parameter changed on this branch (empty `config/` diff, D above)
  — nothing to have tuned with.
- **Minor documentation nit (not a rule violation, not blocking):** `compare_arms.py`'s docstring, the execution
  report and the snapshot all describe `data/processed/chunks/arm-{a,b}.jsonl` and `normalized.jsonl` as
  "git-ignored." `git ls-files` shows both are actually tracked (pre-existing on `dev`, not introduced by this task).
  Doesn't affect any acceptance criterion or number; noted for a future docs pass, not included in the fix prompt.

## E. Scope

Read all 7 "Decisions taken inside the task" in the execution report against the prompt + addendum:
1. Gate-refusal-before-chunking rule — **authorized**: addendum item 4 explicitly says "Gate false refusals (A: 001,
   016, 018; B: 016, 018) are classified as `refusal` with the gate reason," which is exactly this rule.
2. "Citation stage cannot fire" — a logical deduction from the §2 trigger definition, not a parameter change.
3. Two-slot `retrieval_miss` (slot fraction) — a reasonable generalization of "no top-5 chunk overlaps the expected
   section" to multi-slot cases, disclosed with the rule text shown per record.
4. 35-case answer-level pairing — **authorized**: addendum item 1 states this exactly.
5. Latency threat paragraph beyond the addendum's four — explicitly labelled "beyond the addendum's four," additive
   disclosure, not a silent decision.
6. Discordant-set definition — an implementation choice for an underspecified term ("every A/B discordant case"),
   disclosed and independently re-derivable (C6).
7. `language` tag scope — correctly implements addendum wording (VI needs an EN twin).

No parameter/config change, no undisclosed decision found.

## F. Quality spot-read

Read `experiment.py` and `compare_arms.py` in full (not excerpts). `classify_failure`'s rule order matches the §2 +
addendum spec exactly, with no silent fallback that swallows an exception into a wrong label — `is_failure` explicitly
returns `False` (not classified) for `result is None`, and the caller lists `unlabelled` separately rather than
guessing. `chunk_facts` correctly treats a corpus-insufficient case (`spans is None`) as `hits_section = None`, not
`False`, so it isn't silently scored as a miss. The rank-ordering edge case (`hitting[0].rank >= 3` for `ranking`) is
covered by an explicit rank-2 boundary test.

**Mutation testing was not re-executed.** I attempted to reproduce mutation M2 (`rank >= 3` → `rank >= 2`) by editing
`experiment.py` directly to run the targeted test against it — this is exactly what the VERIFY protocol forbids
("You MUST NOT edit source, tests, data or reports of the task"). The edit was caught by the harness's own permission
classifier before the test ran ("Modify Shared Resources" denial); I reverted the edit immediately
(`git diff`/`git status --short` confirmed clean) and did not retry through another tool. What I have instead:
static confirmation that `test_rule_3_ranking_needs_a_cited_wrong_chunk_above_the_first_hit`'s rank-2 case
(`fact(1, False), fact(2, True)` asserted `GENERATION`) would fail under the M2 mutation, by inspection of the
mutated condition (`hitting[0].rank >= 2` would be `True` at rank 2, routing to `RANKING` instead of falling through
to `GENERATION`) — this is code-review confirmation, not an executed kill. M1/M3/M4 were not independently
re-attempted at all (same reason). This is a genuine limitation of this verification, not a defect in the task.

## G. Explain-it-back

All four bullets in the execution report's "Explain it back" section were checked against the independent
recomputation above and hold:
- Paired design rationale — consistent with C2/C6 (every comparison genuinely pairs the same 30–32 cases).
- "No statistically reliable difference" ≠ "arms are equal," 5-0 split = 0.0625 — confirmed by hand in C1
  (`math.comb`), and this is exactly the sentence that §5's "equivalent" wording contradicts (C12) — the report's own
  authors got this right in one place and wrong in another.
- "Chunker mostly moves evidence around" — supported by C6/C9 (section_hit@5 equal, evidence_hit@1 differs, fence
  cuts differ 14×).
- "Several arm differences are not credited to the chunker" (001 gate, 020 judge, 005/026 groundedness) — 001
  confirmed in C5; 020/005/026 rely on reading judge `reason` text and the owner's blind grades, which I did not
  re-grade (correctly marked "unverified" in the execution report, not asserted as fact).

## Verdict: **ACCEPT WITH FIXES**

0 FAIL on acceptance items, tests, reproducibility, project rules, scope, or the vast majority of traced numbers.
2 FAIL, both docs-only wording/prose issues that do not change any table number, statistic, or failure label:
- C4: the sentence "that case is out of every answer-level pair" (EPIC-06 §2) is false for `citation_section_precision`.
- C12: "Answer quality is equivalent at this n" (EPIC-06 §5) contradicts the report's own wording rule.

## Fix prompt (docs-only, `docs/reports/epics/EPIC-06-experiment.md`)

1. **§2, the `Q-EVAL-002` paragraph.** Replace "that case is out of every answer-level pair" with something that
   accounts for `citation_section_precision`'s n=28 (overall)/13 (vi)/13 (parallel), e.g.: "...so that case is out of
   every judge-dependent answer-level pair (accuracy, lenient accuracy, false refusal, groundedness, correct refusal,
   hallucination, citation support rate). `citation_section_precision` does not need the judge — it is a deterministic
   span check over the answer's citations — so `Q-EVAL-002:B`'s `section_precision = 1.0` is included there, which is
   why that row's n (28/13/13) is one higher than `citation_support_rate`'s (27/12/12)." Proof: this task's C4.
2. **§5, "Decisions I would make now."** Replace "Answer quality is equivalent at this n" with wording consistent with
   §2's own rule, e.g.: "Answer quality shows no statistically reliable difference at this n (not evidence the arms
   are equal — see §2)." Proof: this task's C12, and the report's own §2 sentence it contradicts.

No number, table, CSV, JSON file, or failure label needs to change. Re-verify only needs to confirm the two sentences
were edited; no script re-run is required.
