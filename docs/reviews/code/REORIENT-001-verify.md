# VERIFY REORIENT-001

Verifier session, 2026-09-25. Reviewed commits `15764d1` (CHORE: GitNexus index counts), `56ae159` (ledger, CHANGELOG, spec/prompt reconciliation) and `c867943` (master plan) against `agents/prompts/00R-REORIENT-001-sync-state-with-prompts.md` and `agents/prompts/_common.md`. Commands were re-run by the verifier in a Linux container (`.venv/bin/python` instead of `.venv/Scripts/python.exe`). GitNexus MCP tools are not available in this session. Nothing was copied from the execution report.

The later commit `2b5ab38` (CLAUDE.md rule 11: `dev` = integration, `main` = stable) is not part of the task. It does not contradict REORIENT-001: the ledger and report name the historical branch `reorient-001`, and no REORIENT-001 file says which branch tasks start from.

## A. Acceptance / gate items

| # | Item (00R "Do" / "Do not") | Result | Evidence |
|---|---|---|---|
| A1 | Do 1: `docs/plans/task-ledger.md`, one row per prompt file in README order + CORPUS-001 + this task, with all the listed columns, from git/files only | PASS | 20 rows (`task-ledger.md:16-35`) = 19 prompt files (`ls agents/prompts`) + CORPUS-001. Order and "Needs" match `agents/prompts/README.md:9-28`. Commit hashes checked with `git log --oneline`. |
| A2 | Do 2: audit CORPUS-001 / HOUSE-001 / EVAL-001, each gap classified, only must-fix gaps fixed, docs only | PASS | Report §Audit. Spot-checked: the 4 CORPUS-001 test names exist (`tests/unit/test_corpus_inventory.py:32,39,57,68`); `docs/knowledge/domain/corpus-topic-map.md`, `docs/reports/epics/EPIC-01-corpus-analysis.md` exist; no CORPUS-001 prompt-log file (`ls docs/prompt-log/claude-code/`). `git diff 629b931 c867943 --name-only -- src scripts tests corpus data config` → empty. |
| A3 | Do 3: grep prompts 06a–14 against `docs/specs/*` and ADRs; show both texts per conflict; change spec, make prompt match | FAIL (incomplete sweep) | C1–C4 are real and resolved consistently (see diff of `56ae159`: `evaluation-spec.md:40-46`, 09b §3/§4). **Missed:** `evaluation-dataset-design.md:123` (§18 result file per arm: `generated_answer`, `generated_citations[{…,excerpt}]`, `retries`, `latency_ms{embed_query,retrieve,generate}`, `points_covered`, `citation_label`) vs `09a-EVAL-003a-runner.md:15-17` (`answer`, `citations[{marker,…}]`, `retry_count`, `latency_ms{…,total}`). REORIENT-001 itself added "schema = evaluation-dataset-design.md §18" to 09a (line 13) while the generated half still differs from §18. Also `09c-…:12` CSV columns `expected_source, generated_answer` vs 09a's `expected_sources`, `answer` (09a's column list was changed by C3). The report says only "09a/09c/11/12 vs evaluation-spec" were checked. |
| A4 | Do 3: ask the user (AskUserQuestion) per conflict | UNVERIFIED | No artifact of the question/answer events; decisions are recorded in `evaluation-spec.md` status line and `CHANGELOG.md:12-14`. |
| A5 | Do 3: new `agents/prompts/CHANGELOG.md`, back-fill `8d04044` and the `09b` edit | PASS | `CHANGELOG.md:8-9`. `git log --oneline 09bd22f..HEAD -- agents/prompts` → only `8d04044`, `56ae159`, both covered. `8d04044` file list (07, 09a, 09b, generation-spec, citation-spec) matches `git show --stat 8d04044`. |
| A6 | Do 4: master plan task IDs = prompt files (RAG-001a/b, EVAL-003a/b/c, REORIENT-001, VERIFY), ledger linked, start rule, timeline to real position, 1 Oct deadline and cut line unchanged | PASS | Diff of `c867943`: glossary, phases, timeline, epics. `grep -nE "RAG-001[^ab]\|EVAL-003[^abc]\|Proposed task" docs/plans/master-plan.md` → no hits. Start rule at `master-plan.md:6`. §6 cut line not in the diff; deadline block unchanged. (Minor, not asked: `docs/plans/epics/EPIC-05-evaluation.md:9` still says "EVAL-003".) |
| A7 | Do 5: `_common.md` "Before you start" 4 (verbatim) + "When done" ledger update, both logged | PASS | `_common.md:7` is word-for-word the prompt text; `_common.md:21`; `CHANGELOG.md:16`. |
| A8 | Do 6a: map each EVAL-001 FAIL/fix to its commit; recommend re-verify, no self-verify | PASS | `task-ledger.md:39-53`. Re-ran the checks: `coverage-matrix.yaml:355` `share_direct_semantic: 0.094`; design line 132 "9%"; `pytest --collect-only -q tests/unit/test_evaluation_blueprints.py` → 17; `grep -cE "^ *quote:" blueprint.yaml` → 85; `EVAL-001.md:13` "17 offline checks", `:31` "22 accepted, 1 partly accepted, 1 decided by the author". EVAL-001 stays `verified with fixes`. |
| A9 | Do 6b: `EVAL-001-owner-recheck.md`, one block per changed case (009/010, 016, 022, 023, 024, 025, 031, 036): what changed, old vs new, quote, empty verdict line; STOP for the owner | PASS for the listed cases; FAIL on completeness (see C3) | All 8 blocks present; all `owner verdict:` lines empty. Script comparing every quoted string in the sheet with parsed `blueprint.yaml` at `9e0ab15` (old) and HEAD (new): every "Old …" string is in old, every "New …"/quote string is in new; every supporting quote is an `evidence.quote` in HEAD. |
| A10 | Do 6c: A21 recorded as accepted gap in ledger + AI_WORKLOG | PASS | `task-ledger.md:19` item (4), `:51`; `AI_WORKLOG.md` EVAL-001 entry, "Accepted process gap (REORIENT-001, …)". |
| A11 | Do 6c: run `gitnexus_detect_changes()` before this task's commits | UNVERIFIED | GitNexus MCP tools not available to the verifier. The report itself says the tool saw the main checkout, not the worktree (report §detect_changes), so the recorded runs do not cover the committed diff; the author substituted `git diff --cached --name-only`. |
| A12 | Do 7: three separate commits in the given order, nothing else | PASS with note | `git log`: `15764d1` → `56ae159` → `c867943`, messages exact. `c867943` also carries corrections to commit-2 files (AI_WORKLOG, ledger, report, re-check sheet), disclosed in its commit message but not in the report's "Deviations". |
| A13 | Do not: `src/`, `scripts/`, `tests/`, the 3 ground-truth YAML files; no EVAL-002/INGEST-001; no Gemini; no index | PASS | Empty diff for those paths (A2); `git log -- data/evaluation/questions/` last touched by `831d5a0`; `data/chroma/` empty; no `eval-v1.jsonl`. |

## B. Tests
`.venv/bin/python -m pytest -q` → `45 passed in 4.08s`. `tests/unit/test_corpus_inventory.py` + `tests/unit/infrastructure/test_markdown_structure.py` → `19 passed`. REORIENT-001 added no tests (docs-only task, as the prompt requires), so there is nothing to judge for tests that cannot fail.

## C. Claims vs reality
| # | Claim (report / ledger / sheet) | Result |
|---|---|---|
| C1 | 45 passed; 19 passed | PASS (B) |
| C2 | `cmp` prompt-log copy identical | PASS (`cmp agents/prompts/00R-… docs/prompt-log/claude-code/REORIENT-001.md` → identical) |
| C3 | Re-check sheet line 6: "The only change to every case is the new `slot` field … not repeated below"; AI_WORKLOG "re-check sheet for the 9 changed cases" | FAIL (incomplete) | Parsed diff `9e0ab15` → HEAD, ignoring `slot`, shows 27 changed blueprints. Besides the 9 on the sheet, eval cases with scoring-relevant changes the owner has not seen: **005/006, 013/014, 017, 018, 027** (new or replaced `acceptable_alternate_sources`, i.e. what counts as a source hit; CLAUDE.md rule 9 defines ground truth as expected `source_id` + heading path), **003/004** (new evidence quote for P3), **013/014, 027** (citation criteria), **019, 027, 029, 034** (acceptable variations), **030** (question notes, D3), and dev cases 002, 003, 005, 006. The prompt's list came from review §5 line 176 (answer-point changes only); the prompt said "verify each line — do not trust it". The sheet neither lists these cases nor says they were left out. |
| C4 | `local main = 629b931`, `origin/main = e82c922`, 19 unpushed commits | PASS (`git rev-list --count origin/main..629b931` → 19; `e82c922` = "Initial commit") |
| C5 | Commit 2 = 15 Markdown files, nothing under src/scripts/tests/YAML | PASS (`git show 56ae159 --name-only` → 15 files, 0 non-`.md`) |
| C6 | `grep … "awaiting owner review"` → 3 hits, all in `EVAL-001-verify.md` | PASS at the time; now also hits `task-ledger.md:47` and `REORIENT-001.md:29`, which quote the command (self-reference, not a defect). |
| C7 | detect_changes outputs (`risk_level: low`, 8 sections in 4 files, `affected_processes: []`) | UNVERIFIED (tool not available; tool output not stored) |
| C8 | The uncommitted 09b edit and the README 00R row were the owner's | UNVERIFIED (pre-commit state no longer exists; consistent with the prompt's "Known state") |
| C9 | Master plan "EVAL-001 … originally planned to end with the question freeze on 26 Sep, so the plan is about a day ahead" | PASS (pre-change EPIC-05 Stage A "When: Sat 26 Sep"; new timeline follows README target dates) |
No untraceable number was found.

## D. Project rules
- Layers: `grep -rnE "chromadb|google.genai|PySide6" src/knowledge_assistant/core src/knowledge_assistant/application` → no hits; structure test in the 45 passing. PASS.
- Keys: `git grep -nE "AIza[0-9A-Za-z_-]{30}"` → no hits. PASS.
- Model names: no model names added to code (no code changed). PASS.
- Corpus untouched: snapshot checksum test passes; no `corpus/` diff. PASS.
- Excluded docs 14/19/24/27: not referenced by any new content. PASS.
- Eval freeze: `git tag -l 'eval-freeze*'` → none; N/A. Ground-truth YAML unchanged by this task. PASS.

## E. Scope
- Beyond the prompt, disclosed: `02` entry condition (follows from Do 6b), `99-VERIFY.md` ledger rights (`CHANGELOG.md:17`, "owner to confirm"). The 99-VERIFY change is a process decision taken by the AI; owner confirmation is still open (UNVERIFIED). The verifier applied it here only because the run instructions asked for the ledger update.
- Side effect not followed through: `agents/prompts/README.md:36` headless VERIFY command still allows only `Write(docs/reviews/**)` and `Edit(AI_WORKLOG.md)`, so a headless verifier cannot do the new step 4 (ledger row). FAIL (minor).
- Ledger adds a prerequisite not in the README "Needs" column: INGEST-001 and EVAL-002 wait for REORIENT-001 `verified` (`task-ledger.md:20-21`). Reasonable (the guard must be verified first) and stated in the ledger, but not logged in `CHANGELOG.md` and not in README. Note only.
- No decision was taken silently on metrics: C1–C4 are recorded as owner decisions (event UNVERIFIED, A4).

## F. Quality spot-read
No functions were added. Read line by line instead: the ledger rules (`task-ledger.md:6-10`), the `_common.md` guard, the `99-VERIFY.md` verdict → status rule, the C1 routing in `evaluation-spec.md:40-46` vs 09b §3 table, and the C4 formula in both places.
- C1: spec and 09b agree row by row (bare refusal → no call; refusal + related note/citations → judge; answered → judge). 09b adds tests for both new outcomes. OK.
- C4: spec example (yes, partial, no → 0.50) and 09b test (P1 yes, P2 partial, P3 no, optional P4 no → 0.5) agree. OK.
- Rules: `verified with fixes` does not count as a prerequisite, and only a re-verify sets `verified`: consistent across ledger, `_common.md` and `99-VERIFY.md`. No deadlock: REORIENT-001's own entry rule is "done" (stated as one-off).
- 09a record lists `expected_sources [{source_id, heading_path, slot}]` without the optional `evidence_variant` that §18 has; 023 no longer uses it, other cases may. Low risk, covered by the A3 fix.

## G. Explain-it-back
The final chat report (ledger, gaps, decisions, next steps) is not visible to the verifier: UNVERIFIED. The execution report and ledger state the next steps correctly (owner fills the re-check sheet; re-verify EVAL-001 covering `629b931` and `831d5a0`; verify REORIENT-001; then EVAL-002 and INGEST-001). One correction: the owner re-check does not cover every ground-truth change since the owner's review (C3), so "owner re-check filled" alone does not mean the owner has seen all changed ground truth.

## Verdict
**ACCEPT WITH FIXES.** 3 FAIL (A3 missed spec↔prompt conflict, C3/A9 re-check sheet completeness, E README verify command), 6 UNVERIFIED (A4 owner questions, A11/C7 detect_changes, C8 owner authorship of the uncommitted edits, 99-VERIFY owner confirmation, G chat report). The fixes are documentation only and must be done before EVAL-002 freezes the question file.

## Fix prompt (paste into a new session)

```
Fix REORIENT-001 per docs/reviews/code/REORIENT-001-verify.md. Read agents/prompts/_common.md first. Docs only: do NOT touch src/, scripts/, tests/, or data/evaluation/questions/*.yaml.

1. docs/reviews/evaluation/EVAL-001-owner-recheck.md: replace line 6's "The only change to every case is the new slot field" with an accurate statement, and add a section "Other changes since your review (owner to confirm)" listing every blueprint whose parsed content (ignoring `slot`) differs between blueprint.yaml at 9e0ab15 and HEAD but has no block above: eval 003/004 (added P3 evidence quote), 005/006, 013/014, 017, 018, 027 (alternate sources), 013/014, 027 (citation criteria), 019, 027, 029, 034 (acceptable variations), 030 (question notes, D3), dev 002, 003, 005, 006. One line each: field, old → new (short), review finding #. Add one `owner verdict:` line for the section.
   Check: a script that diffs the parsed YAML (ignoring `slot`) lists exactly the cases named in the sheet; every `owner verdict:` line is still empty.
2. Spec <-> prompt conflict C5: evaluation-dataset-design.md §18 "Result file per arm" field names (generated_answer, generated_citations[...excerpt], retries, latency_ms without total, points_covered, citation_label) vs 09a record schema (answer, citations[marker...], retry_count, latency_ms.total) and 09c CSV columns (expected_source, generated_answer). Show both texts, recommend one, ask the owner (AskUserQuestion), update the spec, then make 09a/09b/09c match. Log it in agents/prompts/CHANGELOG.md as C5.
   Check: grep -n "generated_answer\|retry_count\|retries\|expected_source\b" docs/specs agents/prompts shows one consistent naming (or an explicit mapping line in 09c for the brief's CSV columns).
3. agents/prompts/README.md "Suggested CLI usage": add "Edit(docs/plans/task-ledger.md)" to the headless VERIFY --allowedTools so the verifier can do 99-VERIFY step 4. Log it in CHANGELOG.md. Ask the owner to confirm the 99-VERIFY ledger-rights change (CHANGELOG line "owner to confirm") and record the answer in that row.
   Check: README line contains Edit(docs/plans/task-ledger.md); CHANGELOG row updated with "confirmed by owner <date>" or the owner's alternative.
4. docs/reports/execution/REORIENT-001.md "Deviations": add that c867943 also carried corrections to commit-2 files, and that the ledger adds "REORIENT-001 verified" as an extra prerequisite for EVAL-002 and INGEST-001 (also log that in CHANGELOG.md or README "Needs").
   Check: both sentences present.
5. Optional (not a FAIL): docs/plans/epics/EPIC-05-evaluation.md:9 "EVAL-003" -> "EVAL-003a/b/c".

Run .venv/Scripts/python.exe -m pytest -q (must stay 45 passed), run gitnexus_detect_changes(), commit "REORIENT-001: fixes from verification", update the REORIENT-001 row in docs/plans/task-ledger.md, append to AI_WORKLOG.md. STOP; the owner re-runs 99-VERIFY for REORIENT-001.
```
