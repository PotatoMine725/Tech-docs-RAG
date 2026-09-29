# EVAL-003b prompt log

Date: 2026-09-27 · Tool: Claude Code (CLI), Claude Opus 5.5 · Effort: high

## Owner invocation (chat, verbatim)

```text
Run agents/prompts/09b-EVAL-003b-metrics-and-judge.md (EVAL-003b) with this addendum; it overrides the prompt where they differ.
Also read ledger rows 07, 09a, 09b and the EVAL-003b-pre and EVAL-003a reports.

0. Branch eval-003b from dev (7db105b). Use your own git worktree. Standard git block, PR into dev, do not merge,
   stop for 99-VERIFY. OPENBLAS_NUM_THREADS=1, one heavy process at a time.

1. Audit, don't redo. §1 retrieval metrics, expected spans, the §3 mapping and §4 latency already exist (EVAL-003b-pre, verified).
   - Audit them against this prompt + the decisions below.
   - Change them only with a failing test first, and list every change in the report.
   - The latency record shape is resolved (EVAL-003a).

2. Owner decisions (already made, do not re-ask):
   - OD-12: both an automatic span check AND the judge support check, reported separately.
   - evidence_hit = per required point, content-level (owner 2026-09-26). It supersedes §1's "any chunk contains the
     evidence quote". Keep "any quote" and evidence_hit_via_alternate_only as diagnostics.
   - Headline = lenient; strict next to it.
   - D2 refusal rules as in §3.
   - NEW, duplicate overlap rule: for span/source metrics (lenient and strict), a retrieved chunk counts as overlapping
     a span if it OR any chunk in its duplicate_chunk_ids does. Report how many case×arm values this rule changed
     (expected: at most the 2 doc-12/13 cases). Test it.

3. Judge:
   - JUDGE_MODEL = gemini-3.5-flash-lite in config. allow_fallback=False, temperature 0, 13 RPM throttle.
   - It runs as a separate step, never concurrently with the runner.
   - Refusal-check key: presents_related_as_answer (bool) + reason. Use a separate schema/prompt section for
     unanswerable records; the answerable schema is as in §2.
   - Judge input: the cited chunks' full text comes from the record.
     Related citations on insufficient answers are excluded from citation metrics (related_citation_count only).
   - Malformed JSON / a missing verdict → judge_error, never a guessed label.
   - model_used must equal JUDGE_MODEL, or the judgement is rejected.
   - Record judge tokens and latency for the cost table.
   - Limitation to write in the spec: "the judge is the same model as the answer model (self-preference risk);
     mitigated by an owner spot-check of ~10 judgments after EVAL-004". Add that to ledger row 11 as a task.

4. Cost: config/pricing.json only from a source you can actually cite (URL + date). If you can't access one,
   set the prices to null with "not available" and never guess. The runs used the free tier either way.

5. Live: ≤ 3 judge calls on the committed dev dry-run records (read split from run.json; pre-fix records lack split).
   Cover 1 answerable + 1 unanswerable-answered or refusal-check if one exists; otherwise say so. 0 embed requests.
   No eval-split records exist yet; do not create any.

6. Tests per §5 + mutations on: the mapping row for the refusal check, the duplicate overlap rule, the per-point
   evidence rule, and the judge cache key. Report + "Explain it back", ledger 09b, AI_WORKLOG. Eval firewall grep.
```

## Task prompt (`agents/prompts/09b-EVAL-003b-metrics-and-judge.md`, verbatim at the time of the run)

````markdown
# EVAL-003b — Metrics + LLM judge (pure, offline-tested)

Read `agents/prompts/_common.md` first and follow it.
Read: `evaluation-spec.md` (OD-4/OD-5 values from EVAL-001 — **if they differ from this prompt, the spec wins; report the difference**), ADR-0003 D8, ADR-0004 D12, EVAL-003a record schema.
Entry: EVAL-003a done.

## Step 0 — OD-12 (ask user): citation quality = automatic span check + judge support check (recommended: both, reported separately).

## 1. Retrieval metrics (answerable cases only; k = 5) — `application/evaluation/metrics/retrieval.py`
- **Evidence slots (owner decision D1, 2026-09-24):** every expected and alternate source in the dataset has a `slot` (S1, S2, …). A hit needs every slot; any source within a slot counts. See `evaluation-spec.md` § Retrieval hit rule.
- **Expected section spans:** for each expected and alternate (source_id, heading path), grouped by slot, the set of `[start, end)` spans in the normalized text (a heading path can occur in several version variants → several spans; any counts, ADR-0003 D8). Precompute once into `data/evaluation/questions/expected-spans-v1.json` from `normalized.jsonl`; test that every answerable eval case has ≥ 1 span in every slot (corpus-insufficient cases have no expected source, `evaluation-spec.md` § Proposed).
- `source_hit@k` = 1 if every slot has at least one of its source_ids among the top-k chunks. Secondary: fraction of slots satisfied (report separately; it differs from the main value only for multi-slot cases: cross-document, BP-EVAL-022 and BP-EVAL-017).
- **Strict and lenient (owner, 2026-09-25, OWNER-001):** report `source_hit@k` and `section_hit@k` both **lenient** (the rule above: expected + alternate sources/sections per slot) and **strict** (expected sources/sections only; alternates ignored). Tag every span in `expected-spans-v1.json` with its role (`expected` / `alternate`) so strict section hit can be computed. **Headline = lenient**; strict always sits next to it in the same table (owner, 2026-09-25). MRR and the slot fraction use the lenient rule; also compute `strict MRR` (same function, expected spans only) as a secondary value. See `evaluation-spec.md` § Retrieval hit rule (EXP-001 must report a strict/lenient flip).
- `section_hit@k` = 1 if every slot has a top-k chunk that overlaps a span of a section listed in that slot.
- `evidence_hit@k` = 1 if any top-k chunk's text contains the evidence quote, matched with the same whitespace normalization as `scripts/evaluation/validate_questions.py` (`re.sub(r"\s+", " ", text).strip()` on both sides: collapses all Unicode whitespace, including U+00A0; example Q-EVAL-028 / #18) — the strictest check; shows when a chunk boundary cuts the evidence.
- `MRR` (section level) = 1 / rank of the first chunk that hits any slot's span, 0 if none. Also `source MRR`.
- Also report @1 and @3 for the same metrics (cheap, shows ranking quality).

## 2. Judge — `application/evaluation/judge.py` + `config/prompts/judge_v1.md` + `scripts/evaluation/judge_run.py --run-id ID`
For answerable cases where the system answered, and for unanswerable cases where the system answered (refusal check, owner decision D2, 2026-09-24; see mapping). One call per record, temperature 0, `JUDGE_MODEL` from config, JSON schema:
```json
{"required_points":[{"point":"...","covered":"yes|partial|no"}],
 "contradicts_ground_truth": false,
 "unsupported_claims": ["..."],
 "citations":[{"marker":1,"supports_attached_claim":"yes|partial|no"}],
 "reason":"<= 2 sentences"}
```
Judge input: question, expected answer + all answer points with their `required` flag (the judge rates only required points; optional points are context) + `acceptable_variations` + `must_not_claim` + citation criteria (from the dataset, schema `evaluation-dataset-design.md` §18), the generated answer and its `missing_information` note, and the full text of each cited chunk with its marker. Judge prompt tells it: judge only against the given ground truth and passages, not its own knowledge; paraphrase and other language (VI answer vs EN ground truth) are fine.
- Cache: `judgements.jsonl` in the run folder, key = (case_id, arm, sha256(answer), judge prompt version). Re-run = 0 calls. Resumable, `--max-llm-calls`.

## 3. Result mapping — deterministic code, NOT the judge
| answerable | system | judge | `result` |
|---|---|---|---|
| no | insufficient, bare message (no related note, no citations) | – (no call) | `correct_refusal` |
| no | insufficient + related note or related citations | refusal check (D2) | `correct_refusal` if the note presents nothing as the answer (e.g. names MapGroup as related, says versioning isn't covered); `hallucination` if it presents related content or an inferred technique as the documents' answer (e.g. "use MapGroup(\"/v1\") to version") |
| no | answered | refusal check (owner decision D2, 2026-09-24) | `correct_refusal` if the answer says the topic isn't covered and presents no related content as the answer; otherwise `hallucination` |
| yes | insufficient | – (no call) | `false_refusal` |
| yes | answered | all required `yes`, no contradiction | `correct` |
| yes | answered | ≥ 1 `yes`/`partial`, no contradiction | `partially_correct` |
| yes | answered | otherwise | `incorrect` |
Also `grounded` = no unsupported claims (separate metric: groundedness rate).
The unanswerable-but-answered row is the one place where the judge's verdict picks the label (owner decision D2, 2026-09-24); design its judge output here and keep the mapping itself in code.

## 4. Other metrics
- **Answer:** accuracy = correct / answerable; lenient accuracy = (correct + partial) / answerable; groundedness rate; **points-covered score** per answered answerable record = (required `yes` + 0.5 × required `partial`) ÷ required points, optional points ignored (OD-5; formula decided by the owner 2026-09-24, REORIENT-001 C4), reported as a mean.
- **Refusal:** correct-refusal rate (unanswerable), hallucination rate (unanswerable), false-refusal rate (answerable).
- **Citation** (answered records only; related citations attached to an insufficient answer are excluded here and counted separately as `related_citation_count`): presence rate; source precision (cited chunk source is in any evidence slot, alternates included — D1); section precision (cited chunk overlaps expected span); support rate (judge `yes`); and the 4-way class per record, with the names in `evaluation-spec.md` (owner 2026-09-24, REORIENT-001 C2): `correct_evidence` / `correct_source_wrong_evidence` / `unsupported_citation` / `citation_missing`.
- **Latency:** per stage (embed_query, retrieve, generate, total): n, mean, p50, p95, max — computed on records with `retry_count == 0 and not fallback_used`; a separate table for retried/fallback records with their count. Percentiles by nearest-rank; state the method.
- **Cost:** tokens (prompt, output) per stage per question (answer, judge); estimated $ from `config/pricing.json` (price per 1M tokens, source URL, retrieved date; labelled *estimate* — the runs actually used the free tier).
- **Breakdowns** for every metric: overall, by language, by arm, parallel EN/VI subset, size class, difficulty, failure-mode tag.

## 5. Tests (offline) — each metric on hand-made records where the expected value is computed by hand in the test
- section hit via span overlap incl. edge cases (touching spans `[0,10)` vs `[10,20)` = no overlap; multiple variants);
- MRR with hit at rank 3 = 0.333…; no hit = 0; strict MRR: alternate hit at rank 1 and expected hit at rank 3 → lenient 1.0, strict 0.333…;
- evidence_hit false when the quote is split across two chunks;
- evidence_hit true when the chunk and the quote differ only in whitespace (runs of spaces, newlines, U+00A0), e.g. Q-EVAL-028 / #18;
- every row of the mapping table, including both refusal-check outcomes for insufficient + related note;
- slots: case with S1 = {04 expected}, S2 = {26 expected, 20 alternate}: top-k {04, 20} → lenient hit, strict miss; {04, 26} → hit under both; {20, 26} → miss under both, slot fraction 0.5;
- points-covered: required P1 `yes`, P2 `partial`, P3 `no`, optional P4 `no` → 0.5;
- latency percentiles on a known list; retried records excluded from the main table;
- judge: fake LLM returning scripted JSON; cache prevents a second call; malformed judge JSON → record `judge_error`, never a guessed verdict.

## Acceptance
Pure functions, no I/O in metric code; offline pytest green; one live judge call on a dev record, output pasted into the execution report.
````

## Shared rules (`agents/prompts/_common.md`, verbatim at the time of the run)

````markdown
# Common rules for every task prompt (read this first)

## Before you start
1. Read `CLAUDE.md`, `docs/plans/master-plan.md`, `docs/specs/assignment-requirements.md`, and every ADR/spec the task names.
2. Check the task's entry condition. If it is not met, STOP and report why.
3. Check `git status`. If there are uncommitted changes you did not make, list them and ask before touching them.
4. Open `docs/plans/task-ledger.md`. Every prerequisite must be `verified`; otherwise STOP. If work for this task already exists (done outside the prompt set), audit it against this prompt instead of redoing it, and record the audit in the execution report.

## While working
- MUST NOT fabricate results, scores, latency, ground truth, or "tests passed". Unverified = say "unverified".
- Offline tests by default: `.venv/Scripts/python.exe -m pytest`. Live Gemini calls only when the task says so; every live result is cached to disk so quota is never spent twice.
- Existing symbols: run GitNexus impact analysis before editing (CLAUDE.md). New files: no impact check needed.
- An open decision (OD-x in master-plan §8) that blocks the task: give 2–3 options with trade-offs and a recommendation, then ask the user (AskUserQuestion). Record the answer in an ADR or the owning spec. Never decide silently.
- Keep the layer rules (presentation → application → core ← infrastructure). `tests/unit/test_project_structure.py` must stay green.
- Small, reviewable changes. No new dependency without saying why; add it to BOTH `pyproject.toml` and `requirements.txt`.

## When done (all steps required)
1. Save this prompt verbatim to `docs/prompt-log/claude-code/<TASK-ID>.md`.
2. Execution report → `docs/reports/execution/<TASK-ID>.md`: files changed, commands run, test summary (real output), what is unverified, deviations from the prompt.
3. Append an entry to `AI_WORKLOG.md` (format is in that file): what AI did, what the AI got wrong in this task and how it was found/fixed (only real events: failing tests, user corrections, wrong assumptions; write "none observed" if none).
4. Update task/epic status and gate checkboxes in `docs/plans/master-plan.md` and the epic file, and update the task's row in `docs/plans/task-ledger.md`.
5. Run `gitnexus_detect_changes()`, then commit: `<TASK-ID>: <summary>`. Do not push unless the task says so.
6. Final chat report: files, tests, gate status, open decisions, and an **"Explain it back"** section — 3–5 bullets the user must be able to defend in an interview (why this design, what the alternative was). Save the same bullets in the execution report (section "Explain it back") before the commit, so the verifier can check them; chat alone is not enough.
7. STOP. Do not start the next task. The user will run `99-VERIFY.md` for this task in a fresh session.
````
