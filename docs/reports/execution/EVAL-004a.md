# EVAL-004a execution report: evaluation runs and judging, both arms (part 1 of EVAL-004)

Task: `agents/prompts/11-EVAL-004-run-and-report.md`, **part 1 only** (runs + judging), with the owner's invocation of
2026-09-28 (verbatim in [the prompt log](../../prompt-log/claude-code/EVAL-004a.md)); the invocation overrides the prompt
file where they differ. Branch `eval-004` from `dev` at `491f137` (the PR #17 merge), in its own git worktree; PR into
`dev`, not merged. Date: 2026-09-28. Tool: Claude Code, Claude Opus 5.5. Tables, prose and the EPIC-05 report are
EVAL-004b, after EVAL-003c (09c).

## Summary

- **First use of the eval split.** Both arms ran in full on the 36 eval cases, then both were judged. No config, prompt,
  threshold or code was changed before, during or after the runs; HEAD stayed at `491f137` until the runs and judging
  were finished, and every `run.json` records `git_dirty: false`.
- **Runner:** arm A 36 ok / 0 error, arm B 36 ok / 0 error. `fallback_used` = 0 on every record; every LLM record has
  `model_used` `gemini-3.5-flash-lite`; 0 retries.
- **Judge:** arm A 29 ok / 0 judge_error. Arm B 30 ok / **1 judge_error** (Q-EVAL-002: citation marker 22 instead of 1),
  unchanged after the owner's single-resume rule (the second attempt returned marker 22 again). Q-EVAL-002:B is unlabelled
  and listed in `answer.unlabelled`.
- **Quota:** embedding **36** requests (≤ 40), LLM **122** requests (≤ 170): answers 30 + 31, judge 29 + 31 + 1.
  0 HTTP 429, 0 5xx, 0 fallback calls.
- **Duplicate rule:** changed **0** case × arm values on both arms (owner's bound: at most 2, Q-EVAL-003/004 on arm A).
  Why: see "Sanity".
- **First 429/5xx body:** none captured (no `errors.jsonl` was created), so RAG-003's open question stays open.
- **Spot-check:** `validation/evaluation/judge-spot-check.md` (blind, 10 records) and
  `validation/evaluation/judge-spot-check-judge.md` (the judge's verdicts and the S-id mapping). The owner graded blind,
  then cross-checked against the key. Same rule applied to both sides (owner's per-point grades → `map_result`) vs. the
  judge: **8 of 10** agree (S03, S09, S10 disagree); the owner's own holistic "agree?" answer: **9 of 10** (S03 only).
  n = 10 (see "Owner spot-check").
- **Summaries:** `data/evaluation/results/<run>/summary.json` for both runs, computed with `scoring.py` (numbers only).

## Entry condition, environment

- Ledger row 11 depends on 09c, which is **not started**. The owner ordered part 1 now and the tables after 09c is merged.
  Rows 09a and 09b are `verified`.
- PR #17 (EVAL-003b, verified ACCEPT) was open at the start, so `dev` had no `judge_run.py` / `scoring.py`. I stopped before
  creating anything; the owner said "merge PR #17 then proceed with option 1". I merged it (`491f137`) and branched from it.
- Worktree `.claude/worktrees/eval-004` (`git worktree add -b eval-004 … origin/dev`). The main checkout had uncommitted
  `AGENTS.md` / `CLAUDE.md` edits from another session; untouched.
- Commands: the main checkout's `.venv` python by absolute path, `PYTHONPATH=src` (`src;.` for the scratch scripts, which
  import `scripts.evaluation`), `OPENBLAS_NUM_THREADS=1`; live commands also had `CHROMA_PATH` and `EMBEDDING_CACHE_PATH`
  pointing at the main checkout's `data/chroma` and `data/cache/embeddings.sqlite`. `find_dotenv()` found the main `.env`;
  the key was never printed.
- One heavy process at a time. Every live command ran in the background with its log in the session scratchpad, and the
  next step started only after the previous one exited (so the judge never overlapped a runner).

## Commands run and wall time (UTC, 2026-09-27; = 2026-09-28 06:07–06:20 UTC+7)

| Step | Command | Start → end | Exit | Result |
|---|---|---|---|---|
| a | `run_eval.py --arm A --mode full --split eval --estimate-only` | — | 0 | 36 uncached query embeddings; LLM 0–36; ≥ 2.8 min at 13 RPM; up to 36 of 500 RPD (7.2 %) |
| a | same, `--arm B` | — | 0 | same as A (A had not run yet) |
| b | `run_eval.py --arm A --mode full --split eval --max-llm-calls 40` | 23:07:37 → 23:09:53 | 0 | 36 ok, 0 error; LLM 30 (HTTP 30); embedding 36 (misses 36) |
| a' | `run_eval.py --arm B … --estimate-only` (re-run after A) | — | 0 | **0** uncached embeddings; LLM 31 to 31 (gate stops 5 known cases); up to 31 of 500 (6.2 %) |
| c | `run_eval.py --arm B --mode full --split eval --max-llm-calls 35` | 23:10:29 → 23:12:41 | 0 | 36 ok, 0 error; LLM 31 (HTTP 31); embedding **0** (cache hits 72 = 36 estimate + 36 run) |
| d | `judge_run.py --run-id … --estimate-only`, run A / run B | — | 0 / 0 | A: 29 to call, 7 labelled without a judge; B: 31 to call, 5 without |
| d | `judge_run.py --run-id 20260928-eval-A-full-491f137 --max-llm-calls 33` | 23:13:03 → 23:15:12 | 0 | 29 ok, 0 judge_error; HTTP 29 |
| d | `judge_run.py --run-id 20260928-eval-B-full-491f137 --max-llm-calls 35` | 23:15:28 → 23:17:41 | 1 | 30 ok, 1 judge_error (Q-EVAL-002); HTTP 31 |
| d' | same, `--max-llm-calls 1` (owner's single resume) | 23:19:47 → 23:19:51 | 1 | 0 ok, 1 judge_error (same case, same reason), 30 cached; HTTP 1 |
| 3 | `score_runs.py` (scratch, appendix A) | — | 0 | `summary.json` × 2, 36 rows each |
| 4 | `build_spot_check.py` (scratch, appendix B) | — | 0 | the two spot-check files |
| — | `pytest -q` | — | 0 | `775 passed, 1 deselected` (same as EVAL-003b; no code changed) |

Live wall time: runners 2 min 16 s (A) + 2 min 12 s (B); judges 2 min 9 s (A) + 2 min 13 s (B) + 4 s (resume).

## Quota used (this task)

| Model | Requests | Budget |
|---|---|---|
| `gemini-embedding-001` | 36 (arm A query embeddings; arm B 0; estimates 0) | ≤ 40 |
| `gemini-3.5-flash-lite` answers | 30 (A) + 31 (B) = 61 | |
| `gemini-3.5-flash-lite` judge | 29 (A) + 31 (B) + 1 (resume) = 61 | |
| LLM total | **122** | ≤ 170 |
| `gemini-3.5-flash` (fallback) | 0 | |

Counts are the adapters' HTTP counters (`llm_http_requests` in `run.json`; the judge's "HTTP n" line), which equal the
runner/judge request counts here (0 retries). Other use of the same key in this quota day (it runs from 14:00 UTC+7 on
2026-09-27; EVAL-003b's 2 judge requests fall inside it) is not counted.

## Sanity (no analysis; numbers from the records and `summary.json`)

**Counts per arm**

| Arm | Records ok / error | LLM called | Judge calls needed | Judge ok / judge_error (before → after resume) | Labelled without a judge | Unlabelled |
|---|---|---|---|---|---|---|
| A | 36 / 0 | 30 | 29 (28 answer, 1 refusal) | 29 / 0 → 29 / 0 | 7 | none |
| B | 36 / 0 | 31 | 31 (30 answer, 1 refusal) | 30 / 1 → 30 / 1 | 5 | Q-EVAL-002:B |

`runner_errors` is empty on both arms. The refusal check ran live for the first time (Q-EVAL-035 on both arms, status ok).

**Gate refusals on answerable cases** (threshold 0.686; top-1 score in brackets)

- Arm A: Q-EVAL-001 (0.6779), Q-EVAL-016 (0.6269), Q-EVAL-018 (0.6753).
- Arm B: Q-EVAL-016 (0.6246), Q-EVAL-018 (0.6483).
- Also refused by the LLM (not the gate) on an answerable case: Q-EVAL-022 on arm A.

**fallback_used:** 0 of 72 records. `model_used` is `gemini-3.5-flash-lite` on all 61 LLM records and null on the 11
gate answers. Every judge line has `judge_model` `gemini-3.5-flash-lite`, `fallback_used` false.

**Duplicate rule:** `duplicate_rule_changed` = `{'n': 32, 'count': 0}` on both arms. Arm A dropped duplicates on 4 cases
(`duplicates_dropped`: Q-EVAL-003 1, Q-EVAL-004 1, Q-EVAL-024 3, Q-EVAL-027 1), but no retrieved top-5 chunk carries
`duplicate_chunk_ids`. `duplicates_dropped` counts every dropped copy among the 15 over-fetched hits
(`dedupe_by_passage`), while `duplicate_chunk_ids` is only on the 5 kept chunks. I checked this against the chunk file
(scratch, read-only): recomputed `passage_hash` matches all 180 retrieved arm-A entries, the file has the known 13
duplicate groups (26 extra copies), and **none** of arm A's top-5 chunks belongs to a duplicate group. So every dropped
copy (and its kept twin) ranked 6–15, and the rule had nothing to change. Arm B has no duplicate groups and dropped 0.
This is below the owner's bound of 2 (the bound was a simulation over all group members, not a retrieval result).

**First 429 / 5xx body:** none. No `errors.jsonl` was created in either run folder; 0 provider errors in 122 LLM and 36
embedding requests. RAG-003's open question (daily-quota detection on a real 429) stays **open**.

## Judge reliability observation (owner rule, 2026-09-28)

- **Format errors / judge calls: 2 / 61** (both on the same record, Q-EVAL-002 arm B). Per arm: A 0 / 29; B 2 / 32.
- judge_error count per arm, before → after the single resume: **A 0 → 0** (no resume needed), **B 1 → 1**.
- Raw reason, both attempts: `citation markers [22] are not exactly [1]`. The judge's JSON was otherwise well-formed
  (P1 `covered: yes`, no contradiction, no unsupported claims, `supports_attached_claim: yes`), but it gave the citation
  as marker **22**; the answer has one citation, marker `[1]`, pointing at chunk `22:fixed-1600:0000` (source #22). The
  likely cause is that the judge copied the source id into the marker field; not verified. At temperature 0 the retry
  reproduced it exactly.
- Both attempts are kept in `judgements.jsonl` (32 lines in run B). The judge prompt and the parser were not changed.

## Summary JSON (numbers only)

`data/evaluation/results/<run_id>/summary.json`, one per run, from appendix A. It holds `inputs` (SHA-256 of
`records.jsonl`, `judgements.jsonl`, `expected-spans-v1.json`, `pricing.json`, and the chunk file used for the index),
`breakdown` (`scoring.breakdown`: overall, parallel, language, arm, size class, difficulty, failure mode), `judge_latency`
(latest line per record), `cost` (every judge line, so the resumed call is counted) and the 36 per-record `rows`.
Chunk index inputs (git-ignored, main checkout `data/processed/chunks/`):
- arm A: `arm-a.jsonl`, 733 chunks, `9c3bcc6c9428d0746c6dddc5509eab79b84d9a2c4ba35bcbcf9dc45f5fcf229f`;
- arm B: `arm-b.jsonl`, 859 chunks, `2bde1a0e3b42374f03d725f3a7c2b31225c0d6115aa5dc510f49c49a7edb7f2c`.

Interpretation, tables and narrative are EVAL-004b.

## Owner spot-check (ledger row 11)

- **Candidates:** records whose latest judgement is `ok` (59: A 29, B 30; Q-EVAL-002:B excluded as judge_error).
  Records labelled without a judge are not judge verdicts and are excluded.
- **Allocation rule** (appendix B): strata = (arm, result label), sorted. Each stratum's candidates are sorted by case id
  and shuffled with one `random.Random(42)`, strata in sorted order. Then round-robin over the strata, one pick per stratum
  per round, until 10. The 10 picks are shuffled with the same generator and numbered S01–S10, so the blind file's order
  says nothing about label or arm.
- **Strata sizes:** A/correct 23, A/correct_refusal 1, A/partially_correct 5, B/correct 23, B/correct_refusal 1,
  B/partially_correct 6. There were no `incorrect` or `hallucination` judge labels, so those strata do not exist.
- **Picks and the S-id → case / arm mapping:** only in `judge-spot-check-judge.md`, on purpose. The committed
  `summary.json` holds every case × arm label, so listing the mapping here would un-blind the sheet. 99-VERIFY can
  reproduce the picks with appendix B.
- **Limits of the blinding** (cannot be removed without changing the sample): the arm can be guessed from the passages
  (fixed-size chunks start mid-sentence, header chunks start at a `##` heading); and both refusal strata hold only
  `correct_refusal`, so an item headed "refusal check" reveals its judge label.
- **Blind file** `judge-spot-check.md`: per item the question and its language, the ground truth (expected answer,
  answer points with required flag, acceptable variations, MUST-NOT-CLAIM, citation criteria), the answer, the note about
  missing information, the full cited passages, and empty owner columns shaped like the judge's schema. It holds no label,
  no verdict, no reason, no arm and no case id (checked by grep: the only "correct"/"hallucination" hits are ground-truth
  and passage text).
- **Key file** `judge-spot-check-judge.md`: S-id → case, arm, run, check, label and the judge's verdict JSON.
- OD-13 (sample size) is still formally open; ~10 is the owner's addendum figure.

### Owner result (2026-09-28)

The owner filled the owner columns blind (`3b19dd7`), then opened the key and marked "agree with the judge?" per item
(`ce51d08`, S04 in `fb74118`). Grading is done, so the S-id is named here for the disagreements.

**Headline: label agreement using the same rule for both sides.** Feeding the owner's own blind per-point grades
through `map_result` (`application/evaluation/metrics/mapping.py`) and comparing the result to the judge's label gives
**8 of 10**. Reported alongside it: the owner's own holistic "agree with the judge?" answers give **9 of 10** — a
different question (subjective overall agreement, not a re-derivation of the label from the point grades), so both
numbers are kept, not smoothed into one. n = 10 (small sample; wide uncertainty — OD-13, sample size, is still open).

| | Count |
|---|---|
| Items graded | 10 |
| Label agreement — owner's per-point grades → `map_result` vs. the judge | **8** |
| Label agreement — owner's holistic "agree with the judge?" vs. the judge | **9** |

**Disagreements**

- **S03** (`Q-EVAL-012`, arm A, answer check, judge label `partially_correct`). Owner's note: "agree with judge on P1
  but no on P2, as the answer didn't give any clue about the generator silently skips validation for the type" — the
  judge credited a claim the answer doesn't make. The judge gave P2 `partial`; the owner gives `no`. Under both
  readings the record still maps to `partially_correct` (P1 `yes`, P2 `no`, P3 `yes`, no contradiction), so this
  disagreement is at point level only and doesn't move either count above.
- **S09** (`Q-EVAL-020`, arm B) and **S10** (`Q-EVAL-017`, arm B): the owner's holistic "agree?" answer is `yes` for
  both, but the owner's own blind per-point grades disagree with the judge on one required point each (S09 P2, S10 P3:
  owner `yes`, judge `partial`), and running the owner's own grades through `map_result` gives `correct` where the
  judge gave `partially_correct`. The owner's holistic column doesn't surface this — it's a legitimate subjective read
  ("good enough overall"), but it answers a different question than the mechanical recompute. These are the two cases
  the 9/10 holistic count doesn't catch and the 8/10 rule-based count does; that is the whole gap between the two
  headline numbers.
- On P1 (S03) the owner's blind grade was `partial`; after reading the key the owner agreed with the judge's `yes`.
  Recorded as written in the sheet; the blind column is kept unchanged.
- The owner's note on S07 ("this question appeared **TWICE**") refers to S05/S07: the same case in both arms, which the
  per-arm stratification allows (also S01/S10 and S02/S04). Not a defect of the sample.
- Reading: 8 of 10 (rule-based) / 9 of 10 (holistic) at item level, on a small sample (10 of 59 judged records). This is
  the owner's check of the judge, not a measured error rate; whether 10 is enough is OD-13. Interpretation is EVAL-004b.

## Eval firewall

This is the first run on the eval split; the owner ordered it, and the committed run folders and the spot-check files
**contain eval question texts and ground truth by design** (records carry them, EVAL-003a schema). The earlier "0 eval
question texts in changed files" rule of EVAL-003a/b therefore no longer applies to these data files. No eval content was
used to change anything: no code, config, prompt or threshold was edited.

Secret scan (scratch, key read in memory from the main `.env`, never printed) over the 14 new or modified files: **0** matches for the `AIza` + 35-character shape, the configured key, or its 12-character prefix.

## Files

New (all data or docs; no code, config or prompt file changed):

| File | What |
|---|---|
| `data/evaluation/results/20260928-eval-A-full-491f137/` | `run.json`, `records.jsonl` (36), `judgements.jsonl` (29), `summary.json` |
| `data/evaluation/results/20260928-eval-B-full-491f137/` | `run.json`, `records.jsonl` (36), `judgements.jsonl` (32), `summary.json` |
| `validation/evaluation/judge-spot-check.md` | blind owner sheet |
| `validation/evaluation/judge-spot-check-judge.md` | the judge's verdicts (key) |
| `docs/prompt-log/claude-code/EVAL-004a.md` | invocation and the two owner answers, verbatim |
| `docs/reports/execution/EVAL-004a.md` | this report |

Modified: `docs/plans/task-ledger.md` (row 11), `AI_WORKLOG.md`. No `errors.jsonl` exists to commit (none was created).

Run-folder SHA-256 at commit time:
```
0fa18da82e970675a4af83a1c166bd7b0fbdb82352fd8154eee8d7da6eba97e5  A/records.jsonl
7f12dcb0344e87ee383be1a284ca80d2ed6bb022a14e3adfffca3133085a570e  A/judgements.jsonl
e6aaf4f9afc43f29885b9dcd23ca591b9854134542de18183b4f4e65a356ff7d  A/run.json
02e6f4f6fd33b3d0cec88ed0eee27a45768d2251406d00a3c522de1908cfe96a  A/summary.json
910faf859d7e85ff3249dda4dba33c6082ab3521a68b6d2ad890c5e26442c2f3  B/records.jsonl
6958f4cc18deea447c2926306ffbce4cfa568e3369180dcc7b2206515f759277  B/judgements.jsonl
a50ff451f3317e5c6b50005295f9d692b10ef82c255cc72bd1c1cb3d846a574a  B/run.json
9dcc4eae9fac5913b4275806cf931eea2b913fc35578ac95ddf15ea8c141b675  B/summary.json
```
The hashes are of the committed (LF) files. The scratch scripts write with Python `write_text`, which gives CRLF on
Windows; git normalizes to LF (`.gitattributes` `eol=lf`), so compare after `sed -i 's/$//'` or via `git diff` (the re-run
check gave byte-identical CRLF output before normalization).
Frozen question files unchanged: `eval-v1.jsonl` `3436870e…`, `dev-v1.jsonl` `37d349e5…` (= snapshot).

## Unverified / open

- No real 429/5xx seen: RAG-003's open question stays open.
- The cause of the judge's marker 22 (source id copied into the marker field) is a reading, not verified.
- The judge's quality is checked only on the 10-item owner spot-check (8/10 rule-based (9/10 holistic)); OD-13 (sample size) is open.
- `thoughts_tokens` is null on all 61 answer records and all judge lines (the model reports none), so the cost estimate
  counts thinking tokens as 0 and says so.
- `scoring.py`'s module docstring still says the duplicate rule "applies to every span/source value"; the code applies it
  at section level only (owner, EVAL-003b). Documentation only; not changed here (no code change allowed). For 09c/EVAL-004b.
- The scratch scripts (appendices) are not committed as code; 99-VERIFY can re-run them from this report.

## Deviations from the prompt file

- Order: the owner's order replaced prompt 11's retrieval-mode pass (step 1) and its 3-case dry run (step 2); both arms
  ran in full mode directly after `--estimate-only`.
- Ledger row 11 depends on 09c (not started); part 1 ran ahead of it on the owner's instruction. Steps 5–6 of the prompt
  file (tables, OD-13 procedure with `make_spot_check.py` / `score_spot_check.py`) and the EPIC-05 report are not done:
  those scripts do not exist yet (09c), and the owner asked for a 10-record spot-check built here instead.
- I merged PR #17 on the owner's instruction (merging into `dev` is normally the owner's step).
- Master plan / epic status lines were not edited: the owner's step 5 lists only the ledger row and the worklog.

## GitNexus

No existing symbol was edited, so no impact analysis was needed. `detect_changes` returned `Repository "…\worktrees\eval-004" not found` (the index is registered for the main checkout only, as in EVAL-003a/b). Scope check instead: `git status` / `git diff --stat` list only the files in "Files" (2 modified docs: `AI_WORKLOG.md` +15, `task-ledger.md` 1 line; the rest new). No `src/`, `config/`, `scripts/` or `tests/` file changed.

## Explain it back

- **Why no change of anything after seeing eval results.** The eval split is the held-out test. If a threshold or
  prompt is tuned after seeing its answers, the numbers measure how well we fit these 36 questions, not how the system
  behaves (Goodhart). So the tree was frozen at one commit (`491f137`, `git_dirty: false` in both `run.json`), and every
  surprise was reported instead of fixed.
- **Why arm B cost 0 embedding requests.** A question's query vector does not depend on how the documents were chunked,
  so arm A's run cached all 36 and arm B reused them (72 cache hits, 0 misses). Only the chunk vectors differ per arm, and
  those were indexed earlier.
- **Why the judge_error stays unlabelled.** The judge's reply named a citation marker that does not exist. Guessing that
  "22" meant "1" would be inventing a verdict. The rule (one identical retry, then leave it and list it) is the same for
  both arms, so it cannot favour one arm. The record is left out of the labelled denominator and named in the table
  caption.
- **Why the duplicate rule changed nothing.** The rule only acts when a kept top-5 chunk has a dropped identical copy.
  On these 36 questions every duplicate pair ranked 6–15, below the cut, so no top-5 chunk had a twin. The earlier "2"
  was an upper bound from trying every group member, not a prediction of what retrieval would return.
- **Why the spot-check is blind and stratified.** The judge is the same model as the answer model, so it may favour its
  own style. The owner grades first without seeing the judge's verdict, so the judge's answer cannot anchor theirs.
  Round-robin over (arm, label) makes sure the rare labels (refusals, partials) are in the sample, not only the 46
  "correct" ones.
- **Why the rule-based comparison (8/10), not the holistic one (9/10), is the headline.** The judge's label was never a
  holistic call — it came from feeding per-point verdicts through the one fixed `map_result` table. Comparing it to the
  owner's *holistic* "agree?" answer scores two different kinds of judgement against each other. Comparing it to the
  owner's own per-point grades run through that same table scores the judge against the owner with the one rule both
  are supposed to follow, so a gap there (S09, S10) is a real, mechanically-found disagreement rather than a difference
  in how "good enough" was read.

## Appendix A: `score_runs.py` (scratch, verbatim)

Run from the worktree root: `PYTHONPATH="src;." python score_runs.py "<main checkout>/data/processed/chunks" 20260928-eval-A-full-491f137 arm-a.jsonl 20260928-eval-B-full-491f137 arm-b.jsonl`

```python
"""EVAL-004a: summary JSON per run with scoring.py (numbers only). No code change; reads committed/ignored files only.

usage: score_runs.py <chunk_dir> <run_id> <arm-chunk-file-name> [<run_id> <arm-chunk-file-name> ...]
Writes data/evaluation/results/<run_id>/summary.json (overall summary, breakdowns, judge latency, cost, inputs with sha256).
"""
import hashlib
import json
import sys
from pathlib import Path

from knowledge_assistant.application.evaluation.judge import latest_judgements
from knowledge_assistant.application.evaluation.metrics.retrieval import chunk_index
from knowledge_assistant.application.evaluation.metrics.spans import spans_from_entry
from knowledge_assistant.application.evaluation.records import latest_records
from knowledge_assistant.application.evaluation.scoring import (
    breakdown, cost_summary, score_record, summarize_judge_latency)
from knowledge_assistant.config import get_judge_settings

RESULTS = Path("data/evaluation/results")
SPANS = Path("data/evaluation/questions/expected-spans-v1.json")
PRICING = Path("config/pricing.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    chunk_dir, pairs = Path(sys.argv[1]), sys.argv[2:]
    spans_by_case = {case_id: spans_from_entry(entry)
                     for case_id, entry in json.loads(SPANS.read_text(encoding="utf-8"))["cases"].items()
                     if entry["answerable"]}
    pricing = json.loads(PRICING.read_text(encoding="utf-8"))
    prompt_version = get_judge_settings().prompt_version
    for run_id, chunk_name in zip(pairs[::2], pairs[1::2]):
        run_dir = RESULTS / run_id
        chunk_file = chunk_dir / chunk_name
        index = chunk_index(jsonl(chunk_file))
        records = list(latest_records(jsonl(run_dir / "records.jsonl")).values())
        judgement_lines = jsonl(run_dir / "judgements.jsonl")
        judgements = latest_judgements(judgement_lines)
        rows = [score_record(r, spans_by_case, index, judgements, prompt_version) for r in records]
        latest_lines = list(judgements.values())
        summary = {
            "run_id": run_id,
            "inputs": {
                "records.jsonl": sha(run_dir / "records.jsonl"),
                "judgements.jsonl": sha(run_dir / "judgements.jsonl"),
                "expected-spans-v1.json": sha(SPANS),
                "chunk_file": {"name": chunk_name, "sha256": sha(chunk_file), "chunks": len(index)},
                "pricing.json": sha(PRICING),
                "judge_prompt_version": prompt_version,
            },
            "breakdown": breakdown(rows),
            "judge_latency": summarize_judge_latency(latest_lines),
            # every judge line with a model = every judge call made (a retried judge_error line included)
            "cost": cost_summary(records, judgement_lines, pricing),
            "rows": rows,
        }
        out = run_dir / "summary.json"
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(out, len(rows), "rows")


if __name__ == "__main__":
    main()
```

## Appendix B: `build_spot_check.py` (scratch, verbatim)

Run after appendix A: `PYTHONPATH="src;." python build_spot_check.py 20260928-eval-A-full-491f137 20260928-eval-B-full-491f137`

```python
"""EVAL-004a: owner spot-check of 10 judge verdicts (ledger row 11). Seed 42, stratified by (arm, result label).

usage: build_spot_check.py <run_id_A> <run_id_B>
Writes validation/evaluation/judge-spot-check.md (blind: no label, no verdict, no reason, no arm) and
validation/evaluation/judge-spot-check-judge.md (the key: S-id -> case, arm, label, the judge's verdict).

Candidates: records whose latest judgement is status ok (a judge call happened and parsed). Records labelled without a
judge (bare refusals, false refusals) are not judge verdicts and are excluded.
Allocation: strata = (arm, result label), sorted; each stratum's candidates sorted by case_id and shuffled with
random.Random(42) (one generator, strata in sorted order); then round-robin over the strata, one pick per stratum per
round, until 10 are picked. Rare labels are therefore always represented. The 10 picks are then shuffled with the same
generator and numbered S01..S10, so the blind file's order carries no label or arm information.
"""
import json
import random
import sys
from pathlib import Path

from knowledge_assistant.application.evaluation.judge import (
    ANSWER_CHECK, answer_sha256, cache_key, cited_passages, latest_judgements)
from knowledge_assistant.application.evaluation.records import latest_records
from knowledge_assistant.config import get_judge_settings

RESULTS = Path("data/evaluation/results")
OUT = Path("validation/evaluation")
SEED, N = 42, 10


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def quote_block(text: str) -> str:
    return "\n".join("> " + line if line.strip() else ">" for line in (text or "").splitlines()) or "> (empty)"


def main() -> None:
    run_ids = sys.argv[1:3]
    version = get_judge_settings().prompt_version
    candidates = []
    for run_id in run_ids:
        records = latest_records(jsonl(RESULTS / run_id / "records.jsonl"))
        judgements = latest_judgements(jsonl(RESULTS / run_id / "judgements.jsonl"))
        labels = {row["case_id"]: row["answer"]["result"] for row in
                  json.loads((RESULTS / run_id / "summary.json").read_text(encoding="utf-8"))["rows"]
                  if row["answer"] is not None}
        for record in records.values():
            if record["status"] != "ok" or record["mode"] != "full":
                continue
            judgement = judgements.get(cache_key(record["case_id"], record["arm"], answer_sha256(record), version))
            if judgement is None or judgement["status"] != "ok":
                continue
            candidates.append({"run_id": run_id, "record": record, "judgement": judgement,
                               "label": labels[record["case_id"]]})
    strata: dict[tuple[str, str], list[dict]] = {}
    for c in candidates:
        strata.setdefault((c["record"]["arm"], c["label"]), []).append(c)
    rng = random.Random(SEED)
    keys = sorted(strata)
    for key in keys:
        strata[key].sort(key=lambda c: c["record"]["case_id"])
        rng.shuffle(strata[key])
    picks = []
    while len(picks) < N and any(strata[k] for k in keys):
        for key in keys:
            if strata[key] and len(picks) < N:
                picks.append(strata[key].pop(0))
    rng.shuffle(picks)
    print("strata sizes:", {f"{a}/{l}": len([c for c in candidates if (c['record']['arm'], c['label']) == (a, l)])
                            for a, l in keys})
    print("picks:", [(f"S{i:02d}", p["record"]["case_id"], p["record"]["arm"], p["label"]) for i, p in
                     enumerate(picks, 1)])
    write_blind(picks)
    write_key(picks, version)


def write_blind(picks: list[dict]) -> None:
    out = ["# Judge spot-check: owner grading sheet (blind)", "",
           "EVAL-004a, ledger row 11 (self-preference mitigation: the judge is the same model as the answer model).",
           "Grade each item yourself **before** opening `judge-spot-check-judge.md`. That file holds the judge's verdicts",
           "and the S-id → case / arm mapping. This file shows no label, no judge verdict and no arm.", "",
           "Grade with the judge's own rules (`config/prompts/judge_v1.md`), using only the ground truth and the cited",
           "passages shown, not your own knowledge:",
           "- **Answer check** (answerable question). Per required point: `yes` / `partial` / `no`. Contradicts ground truth or",
           "  states a MUST-NOT-CLAIM item: `true` / `false`. Unsupported claims: quote them, or write `none`. Per citation",
           "  marker: does the passage support the claim it is attached to: `yes` / `partial` / `no`.",
           "- **Refusal check** (question the documents do not answer). `presents_related_as_answer` is `true` if the",
           "  response presents related content, or an inferred technique, as the documents' answer, makes a substantive",
           "  answering claim, or never says the topic isn't covered; otherwise `false`.", "",
           "Sample: 10 judged records, seed 42, stratified by arm and result label (rule in",
           "`docs/reports/execution/EVAL-004a.md`). Owner columns are empty on purpose.", ""]
    for i, p in enumerate(picks, 1):
        r, j = p["record"], p["judgement"]
        out += [f"## S{i:02d} ({'answer check' if j['check'] == ANSWER_CHECK else 'refusal check'})", "",
                f"**Question** ({r['language']}):", "", quote_block(r["question"]), "",
                "**Ground truth**", "", f"- Expected answer: {r['expected_answer']}"]
        for point in r["answer_points"]:
            out.append(f"- {point['id']} ({'required' if point['required'] else 'optional, context only'}): {point['text']}")
        out.append(f"- Acceptable variations: {'; '.join(r['acceptable_variations']) or 'none'}")
        out.append(f"- MUST-NOT-CLAIM: {'; '.join(r['must_not_claim']) or 'none'}")
        out.append(f"- Citation criteria: {'; '.join(r['citation_criteria']) or 'none'}")
        out += ["", "**Answer**:", "", quote_block(r["answer"]), ""]
        if r["missing_information"]:
            out += ["**Note about missing information**:", "", quote_block(r["missing_information"]), ""]
        passages = cited_passages(r)
        out += [f"**Cited passages** ({len(passages)}):", ""]
        for marker, chunk in passages:
            out += [f"[{marker}] #{chunk['source_id']} — {chunk['heading_path']}", "", quote_block(chunk["display_text"]), ""]
        out += ["**Owner verdict**", ""]
        if j["check"] == ANSWER_CHECK:
            out += ["| Item | Owner | Note |", "|---|---|---|"]
            out += [f"| {p_['id']} covered |  |  |" for p_ in r["answer_points"] if p_["required"]]
            out += ["| contradicts ground truth |  |  |", "| unsupported claims |  |  |"]
            out += [f"| citation [{marker}] supports its claim |  |  |" for marker, _ in passages]
        else:
            out += ["| Item | Owner | Note |", "|---|---|---|", "| presents_related_as_answer |  |  |"]
        out += ["| agree with the judge? (fill after opening the key) |  |  |", ""]
    (OUT / "judge-spot-check.md").write_text("\n".join(out), encoding="utf-8")


def write_key(picks: list[dict], version: str) -> None:
    out = ["# Judge spot-check: the judge's verdicts (key)", "",
           "Open only after grading `judge-spot-check.md`. One entry per S-id: the record it came from and the judge's",
           f"verdict as written in `judgements.jsonl` (prompt `{version}`). The label is the §3 mapping of that verdict.", ""]
    for i, p in enumerate(picks, 1):
        r, j = p["record"], p["judgement"]
        out += [f"## S{i:02d}", "", f"- Case: `{r['case_id']}`, arm {r['arm']}, run `{p['run_id']}`",
                f"- Check: {j['check']}; judge model `{j['judge_model']}`; label: **{p['label']}**", "",
                "```json", json.dumps(j["verdict"], ensure_ascii=False, indent=1), "```", ""]
    (OUT / "judge-spot-check-judge.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
```
