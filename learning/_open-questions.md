# Open questions / [UNVERIFIED]

> Pinned commit 762b754 (tag `v1.0-submission`). Items move out of here only when confirmed against a repo file.

## For the owner (need a decision before Phase 4)
1. **Outline approval** (Phase 3) — see the proposal in chat: file list, merges/splits, batch order.
2. **Scale.** The proposal is ~17 topic files + glossary + interview bank + Anki. A realistic estimate is 150–250 k words. Confirm you want the full set, or a smaller "core" first (files 01, 03, 05, 06, 07, 09 first).
3. **Anki file** (`anki-cards.tsv`) — optional in the brief; include? → **Owner answer (2026-09-29): skip for now.** Outline approved for the core first; owner then said "continue on the rest documents" (2026-09-30).

## [UNVERIFIED] — believed but not confirmed yet
1. Test count "866 passed / 1 deselected" comes from earlier QC notes, not re-run in this worktree. Plan: run once in Phase 5 with `OPENBLAS_NUM_THREADS=1` (needs the main checkout's `.venv`).
2. HNSW "5×5 no-repro" flaky-test note is from session memory of QC-001; the exact report line is not pinned yet.
3. `scoring.py`, `judge.py`, `experiment.py`, `run_evaluation.py`, `markdown_normalizer.py` bodies: only headers/docstrings read so far.
4. `answer_v1.md` vs `answer_v2.md` difference not yet diffed.
5. Docs-term sweep and review/report incident sweep incomplete (inventory §2.3–2.4).
6. Whether `data/` and eval run folders in the main checkout still match the tagged commit (untracked; read-only access planned).

## Tag caveat
`v1.0-submission` points at 762b754 (merge of PR #23), not at the latest `main` commit ec7846c ("Update README status…"). Notes are pinned to 762b754 as the brief requires; README text added after the tag will not match.

## Added during batch 1 (core files)
1. ~~Wording mismatch, 502 retry~~ **Resolved with evidence:** commit `7e192d4` added 502 (`git log -S"502"` on `gemini_retry.py`), re-verify ACCEPT (`docs/reviews/code/RAG-003-verify.md:160-164`). `AI_WORKLOG.md:826-828` still calls F1 an accepted gap, so that worklog paragraph is stale. Recorded as a verified `[REAL]` item in file 09 §3.3; to be reused in file 15.
2. **Daily-quota reset time.** `DAILY_RESET = "14:00 UTC+7"` is hard-coded. My inference (`[GENERAL]`, not in the repo): it equals midnight Pacific only while Pacific is on daylight time. `[UNVERIFIED]` what the provider actually uses year-round.
3. **Data numbers from untracked files.** Chunk counts/sizes quoted from `data/processed/chunks/*.jsonl` and `stats-arm-*.json` (main checkout, untracked, read-only) match `docs/reports/execution/INGEST-004.md:44-52` and ADR-0005; they are not pinned to the tag.
4. **Test count.** `pytest` was run only for `tests/unit/test_project_structure.py` (9 passed). The README's "866 passed, 1 deselected" is not re-run yet (Phase 5).
5. **Exercise answers marked "đã chạy thử"** were run in the main checkout's `.venv` against this worktree's `src/` (PYTHONPATH), offline, with fakes; the two architecture-test mutations ran on a scratch copy outside the repo.

## Resolved in batch 2 (2026-09-30)
- **Test count re-run.** Full offline suite run once in this worktree (`-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`, `OPENBLAS_NUM_THREADS=1`): `866 passed, 1 deselected in 13.27s`, exit 0. Matches README. One run only: it does not prove the flaky HNSW test is gone (file 14 §3.1). Not run on Linux.
- **`answer_v1` vs `answer_v2`** diffed: only rule 4 differs (added sentence about backticks). Documented in file 08 §1.1.
- **`scoring.py`, `judge.py`, `experiment.py`, `run_evaluation.py`, `stats.py`, `mapping.py`, `retrieval.py`, `integrity.py`** read in full for files 10–13 and 04; incident sweep done from the ledger/review lines cited in file 15 §3.1.
- Stale "sẽ viết sau" forward references in files 07 and 09 fixed. Interview bank and glossary are generated (`_tools/build_interview_bank.py`, `_tools/expand_links.py`).

## Added during batch 2 (files 02, 04, 08, 10–16, glossary, interview bank, README)
1. **Negative claim, file 12 §3.1:** "the repo does not correct for multiple comparisons" rests on a `git grep` for *multiple comparison / Bonferroni / power analysis* in `docs/` and `src/` at the pin (no hits). Not read line-by-line across all reports. `[UNVERIFIED]` beyond that search.
2. **Full headline table not read row by row** for every metric (file 12 §3.1): I only claim what the snapshot table (`docs/snapshots/experiments/exp-001.md:19-30`) shows.
3. **File 15 §3.1 incident table** quotes ledger/review/worklog lines I read; I did **not** re-verify each commit hash in git (only `07264fc` via `git show`, cited in file 04 §3.3). Treat hashes as `[UNVERIFIED]` until re-checked.
4. **File 10 exercise I3** uses **constructed** label counts (22/5/1/3) to practise the formula; only the 22/31 = 0.710 ratio matches the report. The text says so.
5. **Cohen's κ (file 11):** value 0.688 reproduced from the report's confusion matrix; no CI for κ was computed. The remark that the judge was *stricter* in the two label-flipping cases is n = 10 and is marked `[UNVERIFIED]` for generalisation.
6. **File 16** is entirely `[GENERAL]`: paper titles/authors are from memory (no network used); only URLs I am sure of are included (RAG paper arXiv id, OWASP, python.org, jsonlines.org, packaging.python.org, git-scm.com).
7. **Observed, not an incident:** `pyproject.toml` lists `PySide6` without a version while `requirements.txt` has `PySide6>=6.6,<7.0` (file 02 §1.3, exercise A3). `_common.md` says new dependencies go in both files.
8. **Observed environment fact:** the shared `.venv` has an editable install pointing at the **main checkout**; without `PYTHONPATH` a worktree import resolves to the main checkout's `src` (executed, file 02 §2.2). All exercise scripts therefore set `PYTHONPATH="src;."`.
9. **Mutation demo (file 14 §3.2)** results are one run each on a scratch copy outside the repo: M0 13 passed; M1 2 failed; M2 1 failed; M3 (`fsync` removed) survived. The scratch copy was deleted.
10. **Temp files created outside the repo** by the exercise scripts (`ka-learning-*`, `ka-dotenv-*` in the OS temp folder) were deleted; `__pycache__` folders under `learning/_tools` were deleted.
11. **Which exercise answers were run** (offline, fakes, main `.venv` + this worktree's `src`): `llm_retry_scenarios.py` (file 09), `generation_scenarios.py` (08), `eval_metrics_scenarios.py` (10), `judge_stats_scenarios.py` (11, 12), `persistence_scenarios.py` (04), `tooling_scenarios.py` (02), `mutation_demo.py` (14), `hybrid_demo.py` (16; my own teaching code, not the repo's).

## Closed / updated on 2026-09-30 (owner instructions before the commit)
- **Commit hashes (file 15 §3.1, also 04, 09, 13, 01):** `07264fc 491f137 5845603 7e192d4 aa270a9 ba5aa59 ddeabb1 fa522c2` all checked with `git show --stat`; subjects/dates match how the files describe them. **Closed.** (Diff bodies not read.)
- **Multiple-comparison claim (file 12 §3.1):** reworded to "no correction found (git grep of docs/, src/, scripts/, README.md, AI_WORKLOG.md for multiple comparison/Bonferroni/Holm/family-wise/false discovery/multiplicity: no relevant hits)"; still `[UNVERIFIED]` because the reports were not read line by line. **Downgraded, stays open.**
- **Daily quota reset (file 09 §3.2, glossary):** now stated per the owner: midnight Pacific = 14:00 UTC+7 in PDT, 15:00 UTC+7 in PST; source = owner observation + Google AI Studio docs (docs part `[GENERAL]`, not checked by me); AI Studio's usage chart buckets days in UTC-8. The hard-coded `DAILY_RESET = "14:00 UTC+7"` is therefore right only during PDT. **Closed** (owner-confirmed).
- **Owner answer 1 (01b format)** arrived as the unfilled placeholder `<OK / your feedback>`; treated as "no objection recorded". Ask again if you want changes.
- `anki-cards.tsv` stays deferred until the owner asks.
