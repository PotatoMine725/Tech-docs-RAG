# System refusal threshold on dev (dense gate + LLM refusal): pre-registered procedure

Status: **PROPOSED, fixed before any run** (2026-11-27). Owner asked for this step on 2026-11-27 ("triển khai phần
việc tiếp theo"); the rule below was written before any dev-v3 answer existed and is not changed after the runs.
Anything changed later is an amendment, reported as post-hoc. Plan reference: `local-llm-preregistration.md` §6;
questions: `dev-v3.jsonl` (tag `dev-freeze-v3`) plus `dev-v1` and `dev-v2`.

## 1. Why

The local retrieval gate (dense top-1 < 0.5417, EmbeddingGemma) was tuned on 9 answerable dev cases and is
PROVISIONAL. In stage 2 it stopped 15.6% of answerable eval-v1 cases before any LLM saw them. With the LLM's own
refusal (`[[INSUFFICIENT]]`, `answer_v3`) as a second layer, the gate may be lowered. This step measures the two
layers together. It does **not** select a local model (that stays under the stage-2 rule: none selected) and does
not touch eval data.

## 2. Data and fixed conditions

- **Cases:** dev-v1 (6, corpus 1), dev-v2 (6, corpus 2), dev-v3 (20: 8 corpus 1, 12 corpus 2). Pooled: 23 answerable,
  9 unanswerable. Dev only: never reported as an evaluation result.
- **Retrieval (same as stage 2):** EmbeddingGemma v1 fp32 @768, hybrid, chunker A, `RERANK_PROVIDER=none`, top-k 5.
- **Gate off in the runs:** `INSUFFICIENT_SCORE_THRESHOLD=-1`, so every case reaches the LLM; the gate is applied
  afterwards by simulation on the recorded dense top-1 (`top1_score`, the gate input in every mode, ADR-0007 D6).
- **Systems (answer LLM, `answer_v3`):** `gemini-3.5-flash-lite` (default), and the three stage-2 local models
  `gemma-4-e2b-it-q4_k_m`, `qwen3-1.7b-q4_k_m`, `qwen3.5-2b-instruct-q4_k_m` with the stage-2 runtime
  (`llama-server` pinned build, `-c 4096 -t 4 -ngl 0 --parallel 1 --jinja --seed 42 --cache-ram 0`, thinking off).
- **Detector:** the current `detect_language` (PR #40 fix). Language match on these runs is the first measurement of
  the fixed detector on data it was not written against.
- **Judge:** `gemini-3.8-flash` (`JUDGE_API_KEY`), fallback `gemini-3.5-flash-lite` per table under amendment A5.

## 3. Rule (fixed)

`scripts/evaluation/gate_calibration.py`, per system, pooled over the four dev runs:

1. For a threshold t, a case is refused by the gate if its dense top-1 < t (answerable -> false refusal, unanswerable
   -> correct refusal); otherwise the recorded LLM answer keeps its judge label.
2. Candidates: gate off, and the midpoints between consecutive distinct top-1 scores.
3. **Chosen t:** the smallest candidate with zero hallucinations on the 9 unanswerable cases; if none reaches zero,
   the smallest with the fewest.
4. Reported with it: false refusal and lenient / strict accuracy over the 23 answerable cases, the two neighbouring
   candidates on each side (sensitivity), and the current 0.5417 for comparison.
5. A judge-missing case counts as a failure (hallucination or not correct) and marks the result PROVISIONAL.

The shipped threshold stays 0.5417 until the owner sets a new value from these numbers. With 9 unanswerable cases a
zero is weak evidence: a chosen t far below the current one should be read with that in mind (n is small).

## 4. Also reported (no threshold)

- `llm_run_summary.py` per set against the Gemini run (same retrieval, `--reference`), incl. missing-marker rate,
  `lang_match` and its mismatched cases, TTFT.
- Question-language detection on dev-v3 (known: 19/20, Q3-DEV-010 typed without diacritics -> en).

## 5. Spot-check

Owner grades, blind: every unanswerable verdict (9 per system) plus 10% of answerable verdicts (ADR-0004 D12). Until
graded, the tables are marked "judge verdicts not yet spot-checked".
