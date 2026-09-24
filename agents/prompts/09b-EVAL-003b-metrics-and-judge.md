# EVAL-003b — Metrics + LLM judge (pure, offline-tested)

Read `agents/prompts/_common.md` first and follow it.
Read: `evaluation-spec.md` (OD-4/OD-5 values from EVAL-001 — **if they differ from this prompt, the spec wins; report the difference**), ADR-0003 D8, ADR-0004 D12, EVAL-003a record schema.
Entry: EVAL-003a done.

## Step 0 — OD-12 (ask user): citation quality = automatic span check + judge support check (recommended: both, reported separately).

## 1. Retrieval metrics (answerable cases only; k = 5) — `application/evaluation/metrics/retrieval.py`
- **Expected section spans:** for each expected (source_id, heading path) the set of `[start, end)` spans in the normalized text (a heading path can occur in several version variants → several spans; any counts, ADR-0003 D8). Precompute once into `data/evaluation/questions/expected-spans-v1.json` from `normalized.jsonl`; test that every eval case has ≥ 1 span.
- `source_hit@k` = 1 if any top-k chunk has an expected source_id. Cross-document cases: fraction of expected sources present (report separately).
- `section_hit@k` = 1 if any top-k chunk from the expected source overlaps an expected span.
- `evidence_hit@k` = 1 if any top-k chunk's text contains the evidence quote (whitespace-normalized) — the strictest check; shows when a chunk boundary cuts the evidence.
- `MRR` (section level) = 1 / rank of the first section-hit chunk, 0 if none. Also `source MRR`.
- Also report @1 and @3 for the same metrics (cheap, shows ranking quality).

## 2. Judge — `application/evaluation/judge.py` + `config/prompts/judge_v1.md` + `scripts/evaluation/judge_run.py --run-id ID`
Only for answerable cases where the system answered (see mapping). One call per record, temperature 0, `JUDGE_MODEL` from config, JSON schema:
```json
{"required_points":[{"point":"...","covered":"yes|partial|no"}],
 "contradicts_ground_truth": false,
 "unsupported_claims": ["..."],
 "citations":[{"marker":1,"supports_attached_claim":"yes|partial|no"}],
 "reason":"<= 2 sentences"}
```
Judge input: question, expected answer + required points + must-not-claim list (from the dataset), the generated answer, and the full text of each cited chunk with its marker. Judge prompt tells it: judge only against the given ground truth and passages, not its own knowledge; paraphrase and other language (VI answer vs EN ground truth) are fine.
- Cache: `judgements.jsonl` in the run folder, key = (case_id, arm, sha256(answer), judge prompt version). Re-run = 0 calls. Resumable, `--max-llm-calls`.

## 3. Result mapping — deterministic code, NOT the judge
| answerable | system | judge | `result` |
|---|---|---|---|
| no | insufficient | – (no call) | `correct_refusal` |
| no | answered | – (no call) | `hallucination` |
| yes | insufficient | – (no call) | `false_refusal` |
| yes | answered | all required `yes`, no contradiction | `correct` |
| yes | answered | ≥ 1 `yes`/`partial`, no contradiction | `partially_correct` |
| yes | answered | otherwise | `incorrect` |
Also `grounded` = no unsupported claims (separate metric: groundedness rate).

## 4. Other metrics
- **Answer:** accuracy = correct / answerable; lenient accuracy = (correct + partial) / answerable; groundedness rate.
- **Refusal:** correct-refusal rate (unanswerable), hallucination rate (unanswerable), false-refusal rate (answerable).
- **Citation** (answered records): presence rate; source precision (cited chunk source ∈ expected); section precision (cited chunk overlaps expected span); support rate (judge `yes`); and the 4-way class per record: `correct_evidence` / `right_source_wrong_evidence` / `unsupported` / `missing`.
- **Latency:** per stage (embed_query, retrieve, generate, total): n, mean, p50, p95, max — computed on records with `retry_count == 0 and not fallback_used`; a separate table for retried/fallback records with their count. Percentiles by nearest-rank; state the method.
- **Cost:** tokens (prompt, output) per stage per question (answer, judge); estimated $ from `config/pricing.json` (price per 1M tokens, source URL, retrieved date; labelled *estimate* — the runs actually used the free tier).
- **Breakdowns** for every metric: overall, by language, by arm, parallel EN/VI subset, size class, difficulty, failure-mode tag.

## 5. Tests (offline) — each metric on hand-made records where the expected value is computed by hand in the test
- section hit via span overlap incl. edge cases (touching spans `[0,10)` vs `[10,20)` = no overlap; multiple variants);
- MRR with hit at rank 3 = 0.333…; no hit = 0;
- evidence_hit false when the quote is split across two chunks;
- every row of the mapping table;
- latency percentiles on a known list; retried records excluded from the main table;
- judge: fake LLM returning scripted JSON; cache prevents a second call; malformed judge JSON → record `judge_error`, never a guessed verdict.

## Acceptance
Pure functions, no I/O in metric code; offline pytest green; one live judge call on a dev record, output pasted into the execution report.
