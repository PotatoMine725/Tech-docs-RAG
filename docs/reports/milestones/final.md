# Final report — Knowledge Assistant submission

Gate G7 (`docs/plans/master-plan.md` § EPIC-07). Task: QC-001. Date: 2026-09-29.

## What this project is

A desktop RAG assistant answering questions about a fixed 24-document technical corpus, with every answer grounded
and cited, an explicit "insufficient information" path, a 36-question evaluation covering answer/retrieval/citation/
latency quality, and a controlled, paired-statistics experiment comparing two chunking strategies. Full description:
[`README.md`](../../../README.md).

## Status against every gate

| Gate | Epic | Status |
|---|---|---|
| G1 | EPIC-01 Corpus analysis | ✅ `docs/reports/epics/EPIC-01-corpus-analysis.md` |
| G2 | EPIC-02 Ingestion | ✅ `docs/plans/master-plan.md` § EPIC-02 (11/11 checks) |
| M1 | EPIC-05 stage A (ground truth frozen) | ✅ tag `eval-freeze-v1`, before any index existed |
| G3 / M2 | EPIC-03 RAG baseline | ✅ both arms indexed, first grounded answer with citations |
| G4 | EPIC-04 Desktop GUI | ✅ owner-checked, `validation/generation/gui-check.md` |
| G5A | EPIC-05 stage A (ground truth) | ✅ |
| G5B | EPIC-05 stage B (runs, metrics, report) | ✅ `docs/reports/epics/EPIC-05-evaluation.md` |
| G6 | EPIC-06 Experiment | ✅ `docs/reports/epics/EPIC-06-experiment.md`, all 5 brief points answered |
| G7 | EPIC-07 Final QC (this task) | ✅ see below |

## G7 checklist (from `master-plan.md`)

- [x] Every row of the brief traceability has a status and an evidence link (rows still open are marked, not ticked:
      demo video, `main`, submission) → [`brief-traceability.md`](../../reviews/milestones/brief-traceability.md).
- [x] Final checks pass → [`docs/reports/execution/QC-001.md`](../execution/QC-001.md) (offline pytest ×2, fresh-clone
      install+test, flaky-test investigation ×15 runs, secret scan of full git history, excluded-docs-unused script
      check, corpus checksum verification, live smoke on merged `dev`, GitNexus reindex + `detect_changes`).
- [x] README has every required submission section (problem, solution, architecture/workflow, dataset, AI usage,
      completed work, limitations) → [`README.md`](../../../README.md); `AI_WORKLOG.md` summary sections filled →
      [`AI_WORKLOG.md`](../../../AI_WORKLOG.md).
- [ ] Demo video (≤ 5 min) recorded — **script and shot list ready**
      ([`demo-video-script.md`](demo-video-script.md)); recording is the owner's step.
- [ ] Repo pushed to GitHub `main` — **prepared, not executed** (owner approval required; see below).
- [ ] Submitted by 1 Oct — **channel/time still OD-1, owner's call.**

## What's real vs. what's still the owner's step

**Real and verified by this task (not claimed, run):**
- 866 offline tests pass (1 deselected `@pytest.mark.gemini` test), reproduced across 18 separate `pytest`
  invocations in this task: 2 full-suite runs, 15 targeted runs investigating the flaky test (5 isolated + 5 module +
  5 more full-suite), and 1 full-suite run in the fresh clone.
- The full pipeline runs end to end on the merged `dev` branch: two live answers (EN, VI) with correct citations,
  one correct out-of-corpus refusal, 0 embedding requests, 2 of a 3-request budget spent, 0 provider errors.
- A fresh clone of `dev`, from nothing, installs and passes the full test suite in under 4 minutes — with one real,
  previously undocumented gap found and fixed in the README's install instructions along the way.
- 0 secrets anywhere in 198 commits of git history.
- 0 excluded documents referenced anywhere in the pipeline's data files.
- Corpus source files unchanged since the manifest was generated (24/24 checksums match).
- The one previously-reported flaky test could not be reproduced in 15 fresh runs across three scopes.

**Resolved by the owner during this task** (2026-09-29 — after an earlier fabricated claim of these confirmations was
caught and reverted, see `AI_WORKLOG.md` § "2026-09-29 QC-001 follow-up"): the owner accepted the six-item "With 7
more days" list, and corrected an earlier answer — the planning assistant is Claude in the Claude desktop app
(Cowork), now in the `AI_WORKLOG.md` tools table with its three errors listed.

**Still the owner's step, deliberately not done by this task** (per CLAUDE.md §11 and the task's own instruction to
ask before anything hard to reverse or affecting shared state):
- Recording the demo video (script ready).
- Approving the `qc-001` → `dev` PR (opened as a draft, blocked on its own `99-VERIFY`).
- Approving and merging [PR #23](https://github.com/PotatoMine725/Tech-docs-RAG/pull/23) (`dev` → `main`, opened as
  a draft, "do not merge yet") and then running the prepared `v1.0-submission` tag commands
  (`docs/reports/execution/QC-001.md`).
- Choosing the submission channel and time (OD-1).
- Cleaning up the long list of stale git worktrees this project accumulated (listed in `QC-001.md`, not removed).

## Explain it back (project-level, not just this task)

- **Why two chunking arms instead of one:** the brief asks for a ≥2-approach experiment with evidence, not just a
  claim — building both arms from day one (rather than retrofitting a second approach later) meant every evaluation
  run, every metric, and every failure case could be compared on identical ground, which is what makes the paired
  McNemar test in EPIC-06 possible at all.
- **Why a retrieval-score gate exists separately from the LLM's own "insufficient information" judgment:** relying
  on the LLM alone to refuse would mean every refusal costs an API call and depends on the model's own honesty about
  weak context; a cheap, deterministic pre-check (top-1 similarity below a tuned threshold) catches the clearest
  cases for free and is auditable without touching Gemini at all — the tradeoff (documented as a limitation) is that
  one global threshold, tuned on one chunking arm, doesn't fit both arms equally.
- **Why an independent verifier session runs after each task, not just at milestones:** an implementer session that
  wrote a claim tends to believe it; a fresh session with no memory of *why* something was written only has the
  evidence in front of it. Most of the "Incorrect AI outputs" entries in `AI_WORKLOG.md` (the "Implementer claims
  caught by verifiers" group) were caught this way, not by the same session re-checking its own work.
- **Why the judge's self-preference risk is disclosed rather than engineered away:** the judge is from the same model
  family as the answer model, so the risk is named explicitly and partially checked with a real blind human
  spot-check (8/10 agreement, κ=0.688); a second, independent judge is item 3 of "With 7 more days" in
  `AI_WORKLOG.md`. Naming the risk is more defensible than an unstated assumption of judge correctness.
- **Why this QC pass re-ran the pipeline live instead of trusting the existing reports:** every number a grader can
  check should already have been checked by the author; the fresh-clone test, the live smoke check, and the
  15-run flaky-test investigation in this task exist specifically so that "it works" is something this project
  demonstrated one more time on the actual `dev` branch being submitted, not something inferred from older task
  reports alone.
