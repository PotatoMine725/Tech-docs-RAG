# EVAL-003b — Metrics + LLM judge (pure, offline-tested)

Read `agents/prompts/_common.md` first and follow it.
Read: `evaluation-spec.md` (OD-4/OD-5 values from EVAL-001 — **if they differ from this prompt, the spec wins; report the difference**), ADR-0003 D8, ADR-0004 D12, EVAL-003a record schema.
Entry: EVAL-003a done.

## Step 0 — OD-12 (ask user): citation quality = automatic span check + judge support check (recommended: both, reported separately).

## 1. Retrieval metrics (answerable cases only; k = 5) — `application/evaluation/metrics/retrieval.py`
- **Evidence slots (owner decision D1, 2026-09-24):** every expected and alternate source in the dataset has a `slot` (S1, S2, …). A hit needs every slot; any source within a slot counts. See `evaluation-spec.md` § Retrieval hit rule.
- **Expected section spans:** for each expected and alternate (source_id, heading path), grouped by slot, the set of `[start, end)` spans in the normalized text (a heading path can occur in several version variants → several spans; any counts, ADR-0003 D8). Precompute once into `data/evaluation/questions/expected-spans-v1.json` from `normalized.jsonl`; test that every answerable eval case has ≥ 1 span in every slot (corpus-insufficient cases have no expected source, `evaluation-spec.md` § Proposed).
- `source_hit@k` = 1 if every slot has at least one of its source_ids among the top-k chunks. Secondary: fraction of slots satisfied (report separately; it differs from the main value only for multi-slot cases: cross-document and BP-EVAL-022).
- `section_hit@k` = 1 if every slot has a top-k chunk that overlaps a span of a section listed in that slot.
- `evidence_hit@k` = 1 if any top-k chunk's text contains the evidence quote (whitespace-normalized) — the strictest check; shows when a chunk boundary cuts the evidence.
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
- MRR with hit at rank 3 = 0.333…; no hit = 0;
- evidence_hit false when the quote is split across two chunks;
- every row of the mapping table, including both refusal-check outcomes for insufficient + related note;
- slots: case with S1 = {04}, S2 = {26, 20}: top-k {04, 20} → hit; {20, 26} → miss; slot fraction for {20, 26} = 0.5;
- points-covered: required P1 `yes`, P2 `partial`, P3 `no`, optional P4 `no` → 0.5;
- latency percentiles on a known list; retried records excluded from the main table;
- judge: fake LLM returning scripted JSON; cache prevents a second call; malformed judge JSON → record `judge_error`, never a guessed verdict.

## Acceptance
Pure functions, no I/O in metric code; offline pytest green; one live judge call on a dev record, output pasted into the execution report.
