# `answer_v4` + O1 against `answer_v3` on dev: pre-registered comparison

Status: **fixed before any `answer_v4` run** (2026-11-28; owner chose "O1 + answer_v4, then re-measure on dev").
Changes after the runs are amendments, reported as post-hoc. Inputs: ADR-0010 amendment 2026-11-28,
`config/prompts/answer_v4.md`, `docs/reports/2026-11-27-gate-calibration-dev.md` (the `gc3` baseline).

## 1. Arms

- **Baseline `gc3`:** the existing gate-off runs, `answer_v3`, old parser (late sentinel = text). Not re-run.
- **New `gc4`:** `answer_v4` with the O1 parser. Same 4 systems, same 32 dev cases (dev-v1, dev-v2, dev-v3; 23
  answerable / 9 unanswerable), same retrieval (EmbeddingGemma fp32, hybrid, chunker A, no rerank), gate off
  (`INSUFFICIENT_SCORE_THRESHOLD=-1`), same `llama-server` runtime as stage 2 / `gc3`. Run ids
  `gc4-dev-{v1,v2,v3c1,v3c2}-<system>`. `llm_run_summary.py --reference gc3-dev-<set>-<system>` must show the same
  retrieval.
- Two things change at once (prompt and parser). The parser's own effect on `answer_v3` is the simulation in the
  baseline report §8.5; it is quoted, not re-run.

## 2. Judge

`gemini-3.5-flash-lite` for this table, the judge every `gc3` verdict came from (amendment A5 applied to the `gc3`
series), so the two arms share one judge (no table mixes judges). `judge_v1`, label table unchanged. Judge errors are
retried twice; any left count as failures and are listed.

## 3. Metrics (per system, gate off, and at the current gate 0.5417 by simulation)

Correct / partial / incorrect / LLM false refusal over 23 answerable; correct refusal / hallucination over 9
unanswerable; lenient accuracy; late sentinels in `raw_text` (sentinel not at the start of line 1); missing-marker
rate; `lang_match`; TTFT median (the prompt is about 150 tokens longer); gate calibration with the unchanged rule of
`gate-calibration-v3.md` (for information only, no threshold change).

## 4. Decision rule (directional, dev only)

Per system, `gc4` against `gc3`:
- **no harm:** hallucination not higher, lenient accuracy at most 2 cases lower, LLM false refusals at most 2 cases
  higher;
- **gain:** fewer hallucinations, or fewer late sentinels, with no harm.

`answer_v4` may be proposed as the default text-format prompt only if **Gemini and gemma show no harm** and at least
one system shows a gain. Even then it is a dev result on the cases it was written against (the draft cites dev
failures), so it is optimistic: before any local model or default change, the owner decides on a confirmation run
on eval. No threshold, judge or default config changes in this step.

## 5. Spot-check

Owner, blind, same format as `gc3`: every unanswerable verdict of `gc4` (36) plus every answerable case whose label
changed from `gc3`. Until graded, tables say "not yet spot-checked".
