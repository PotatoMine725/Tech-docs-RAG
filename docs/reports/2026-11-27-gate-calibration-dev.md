# System refusal threshold on dev: dense gate + LLM refusal, four answer models

**Runs:** 2026-11-27, 18:13–18:42 (UTC+7): 16 gate-off runs `gc3-dev-{v1,v2,v3c1,v3c2}-<system>`.
**Status:** dev measurement, **judge verdicts not yet spot-checked** (owner sheet pending). PROVISIONAL for every
system: 1–3 cases per system have no judge label (D2) and are counted as failures.
**Plan (fixed before the runs):** [`docs/plans/gate-calibration-v3.md`](../plans/gate-calibration-v3.md). Its rule is
applied unchanged. **No threshold was changed in config:** the shipped gate stays 0.5417 until the owner sets a value.
**Dev only:** these 32 cases tune a threshold. They are never reported as an evaluation result.

## 1. Method (summary of the plan)

- **Cases:** dev-v1 (6, corpus 1), dev-v2 (6, corpus 2), dev-v3 (20, tag `dev-freeze-v3`: 8 corpus 1, 12 corpus 2).
  In total 32 cases, 23 answerable and 9 unanswerable.
- **Fixed conditions:**
  - Retrieval: EmbeddingGemma fp32 @768, hybrid, arm A, `RERANK_PROVIDER=none`, top-k 5.
  - Prompt: `answer_v3`.
  - Gate: **off** (`INSUFFICIENT_SCORE_THRESHOLD=-1`), so every case reached the LLM.
  - Local runtime: as stage-2 `llm2r`, i.e. `llama-server` build `E:\models\llama.cpp\v1.0.0-cpu` with `-c 4096 -t 4 -ngl 0 --parallel 1 --jinja --seed 42 --cache-ram 0`, `--alias <model-id>`, thinking off.
- **Systems:** `gemini-3.5-flash-lite` and the three stage-2 local models.
- **Rule:** `gate_calibration.py` simulates the gate on the recorded dense top-1. A case below t is refused before the
  LLM; otherwise it keeps its judge label. The chosen t is the smallest candidate with the fewest hallucinations on
  the 9 unanswerable cases. A judge-missing case counts as a failure.
- **Run checks:** every `run.json` has threshold −1.0, git commit `2bfa64f` with `git_dirty = False`, and one
  invocation. All 32 cases in each run are ok, and no record has `gate_fired`.
- **Same retrieval:** `llm_run_summary.py --reference gc3-dev-<set>-gemini` exits 0 for all 4 sets, with
  `same_retrieval` "yes" in every row. The LLM is therefore the only variable.

## 2. Calibration (gate_calibration.py --current 0.5417)

Rates are over 9 unanswerable / 23 answerable cases. "Gate refused" counts cases below t.

### gemini (gemini-3.5-flash-lite)

| threshold | hallucination | false refusal | lenient | strict | gate refused |
|---|---|---|---|---|---|
| off **(chosen)** | 0/9 (0%) | 3/23 (13%) | 17/23 (74%) | 17/23 (74%) | 0 |
| 0.3482 | 0/9 (0%) | 3/23 (13%) | 17/23 (74%) | 17/23 (74%) | 1 |
| 0.4142 | 0/9 (0%) | 3/23 (13%) | 17/23 (74%) | 17/23 (74%) | 2 |
| 0.5417 (current) | 0/9 (0%) | 9/23 (39%) | 11/23 (48%) | 11/23 (48%) | 14 |

Unlabelled: Q3-DEV-004, Q3-DEV-005.

### gemma-4-e2b-it-q4_k_m

| threshold | hallucination | false refusal | lenient | strict | gate refused |
|---|---|---|---|---|---|
| 0.5911 | 1/9 (11%) | 11/23 (48%) | 11/23 (48%) | 11/23 (48%) | 19 |
| 0.5933 | 1/9 (11%) | 12/23 (52%) | 10/23 (43%) | 10/23 (43%) | 20 |
| 0.6081 **(chosen)** | 0/9 (0%) | 12/23 (52%) | 10/23 (43%) | 10/23 (43%) | 21 |
| 0.6288 | 0/9 (0%) | 13/23 (57%) | 9/23 (39%) | 9/23 (39%) | 22 |
| 0.6385 | 0/9 (0%) | 14/23 (61%) | 8/23 (35%) | 8/23 (35%) | 23 |
| 0.5417 (current) | 1/9 (11%) | 8/23 (35%) | 14/23 (61%) | 14/23 (61%) | 14 |

Unlabelled: Q3-DEV-006.

### qwen3-1.7b-q4_k_m

| threshold | hallucination | false refusal | lenient | strict | gate refused |
|---|---|---|---|---|---|
| 0.5911 | 1/9 (11%) | 11/23 (48%) | 8/23 (35%) | 8/23 (35%) | 19 |
| 0.5933 | 1/9 (11%) | 12/23 (52%) | 7/23 (30%) | 7/23 (30%) | 20 |
| 0.6081 **(chosen)** | 0/9 (0%) | 12/23 (52%) | 7/23 (30%) | 7/23 (30%) | 21 |
| 0.6288 | 0/9 (0%) | 13/23 (57%) | 6/23 (26%) | 6/23 (26%) | 22 |
| 0.6385 | 0/9 (0%) | 14/23 (61%) | 5/23 (22%) | 5/23 (22%) | 23 |
| 0.5417 (current) | 2/9 (22%) | 8/23 (35%) | 10/23 (43%) | 10/23 (43%) | 14 |

Unlabelled at the chosen t: Q3-DEV-004, Q3-DEV-006. Gate off, the run also has Q3-DEV-005 unlabelled.

### qwen3.5-2b-instruct-q4_k_m

| threshold | hallucination | false refusal | lenient | strict | gate refused |
|---|---|---|---|---|---|
| 0.5911 | 1/9 (11%) | 11/23 (48%) | 8/23 (35%) | 7/23 (30%) | 19 |
| 0.5933 | 1/9 (11%) | 12/23 (52%) | 7/23 (30%) | 6/23 (26%) | 20 |
| 0.6081 **(chosen)** | 0/9 (0%) | 12/23 (52%) | 7/23 (30%) | 6/23 (26%) | 21 |
| 0.6288 | 0/9 (0%) | 13/23 (57%) | 6/23 (26%) | 5/23 (22%) | 22 |
| 0.6385 | 0/9 (0%) | 14/23 (61%) | 5/23 (22%) | 5/23 (22%) | 23 |
| 0.5417 (current) | 2/9 (22%) | 8/23 (35%) | 10/23 (43%) | 9/23 (39%) | 14 |

Unlabelled: Q3-DEV-004, Q3-DEV-006.

### What drives the result (analysis, not a decision)

The table below gives the gate-off judge label of each unanswerable case, ordered by dense top-1.

| case | top-1 | gemini | gemma-4-e2b | qwen3-1.7b | qwen3.5-2b |
|---|---|---|---|---|---|
| Q3-DEV-017 (pneumothorax, near C2-16) | 0.5948 | refusal | **halluc.** | **halluc.** | **halluc.** |
| Q-DEV-005 | 0.5869 | refusal | refusal | refusal | **halluc.** |
| Q3-DEV-020 (XSD, near C2-08) | 0.5522 | refusal | refusal | **halluc.** | refusal |
| Q3-DEV-015 (FromSqlRaw, near #22) | 0.5396 | refusal | refusal | **halluc.** | **halluc.** |
| Q-DEV-006 | 0.5378 | refusal | refusal | **halluc.** | **halluc.** |
| Q3-DEV-018 (anti-HCV, near C2-29) | 0.5262 | refusal | refusal | **halluc.** | refusal |
| Q3-DEV-016 (ICollectionFixture, near #17/#28) | 0.4520 | refusal | refusal | **halluc.** | **halluc.** |
| Q3-DEV-019 (Unity Netcode) | 0.4490 | refusal | refusal | refusal | refusal |
| Q2-DEV-006 | 0.3041 | refusal | refusal | **halluc.** | refusal |

- **Gemini.** Its own refusal covers all 9 unanswerable cases, so the rule picks "gate off". At the current 0.5417 the
  gate costs it 6 more false refusals (lenient 74% → 48%) and prevents no hallucination.
- **The three local models get the same t, 0.6081.** One case decides it: Q3-DEV-017 has the highest top-1 of the 9,
  and all three local models answer it. Zeroing hallucinations means gating everything below 0.6081, which refuses
  12 of 23 answerable cases.
- **gemma-4-e2b refuses on its own in 8 of the 9.** It is the only local model whose LLM layer works as a second gate.
- **The two Qwen models never refused** (LLM refused = 0 in every set). Gate off, they hallucinate on 7 of 9
  (qwen3-1.7b) and 5 of 9 (qwen3.5-2b).
- **n is small.** A "zero" here rests on 9 unanswerable cases, and the local choice rests on one of them (plan §3).

## 3. Non-judge metrics (llm_run_summary.py, per set, reference = Gemini run)

| set | system | answered | LLM refused | false refusal (LLM) | missing marker | lang_match | TTFT median / p90 ms | gen median ms |
|---|---|---|---|---|---|---|---|---|
| v1 | gemini | 3 | 3 | 25.0% | 0.0% | 83.3% | n/a | 1,281 |
| v1 | gemma-4-e2b | 4 | 2 | 0.0% | 0.0% | 100.0% | 4,814 / 6,306 | 10,128 |
| v1 | qwen3-1.7b | 6 | 0 | 0.0% | 66.7% | 83.3% | 8,375 / 11,727 | 15,318 |
| v1 | qwen3.5-2b | 6 | 0 | 0.0% | 33.3% | 100.0% | 9,349 / 12,052 | 20,791 |
| v2 | gemini | 4 | 2 | 20.0% | 0.0% | 100.0% | n/a | 1,138 |
| v2 | gemma-4-e2b | 4 | 2 | 20.0% | 0.0% | 100.0% | 6,218 / 7,975 | 9,936 |
| v2 | qwen3-1.7b | 6 | 0 | 0.0% | 0.0% | 100.0% | 12,788 / 18,129 | 18,455 |
| v2 | qwen3.5-2b | 6 | 0 | 0.0% | 16.7% | 100.0% | 11,246 / 14,148 | 17,120 |
| v3c1 | gemini | 6 | 2 | 16.7% | 16.7% | 100.0% | n/a | 1,203 |
| v3c1 | gemma-4-e2b | 5 | 3 | 16.7% | 0.0% | 100.0% | 4,117 / 4,850 | 7,051 |
| v3c1 | qwen3-1.7b | 8 | 0 | 0.0% | 0.0% | 100.0% | 6,949 / 7,735 | 13,549 |
| v3c1 | qwen3.5-2b | 8 | 0 | 0.0% | 0.0% | 100.0% | 7,867 / 8,845 | 14,539 |
| v3c2 | gemini | 8 | 4 | 0.0% | 0.0% | 100.0% | n/a | 1,154 |
| v3c2 | gemma-4-e2b | 9 | 3 | 0.0% | 0.0% | 91.7% | 6,026 / 7,401 | 10,684 |
| v3c2 | qwen3-1.7b | 12 | 0 | 0.0% | 33.3% | 91.7% | 12,034 / 16,384 | 19,815 |
| v3c2 | qwen3.5-2b | 12 | 0 | 0.0% | 16.7% | 100.0% | 11,270 / 13,903 | 18,265 |

**Pooled over 32 cases:**

| system | LLM refusals | missing marker (answered) | lang_match |
|---|---|---|---|
| gemini | 11 | 1/21 | 31/32 (96.9%) |
| gemma-4-e2b | 10 | 0/22 | 31/32 (96.9%) |
| qwen3-1.7b | 0 | 8/32 | 30/32 (93.8%) |
| qwen3.5-2b | 0 | 5/32 | 32/32 (100%) |

The cases behind each flag:
- **Answerable, refused by the LLM:** gemini on Q-DEV-004, Q2-DEV-002 and Q3-DEV-003; gemma-4-e2b on Q2-DEV-002 and Q3-DEV-003.
- **No valid marker:** gemini on Q3-DEV-015. qwen3-1.7b on Q-DEV-002, -003, -005, -006 and Q3-DEV-013, -018, -019, -020.
  qwen3.5-2b on Q-DEV-002, Q-DEV-006, Q2-DEV-006, Q3-DEV-019 and Q3-DEV-020.

## 4. Language

- **Question detection on dev-v3** (fixed detector, PR #40): 19 of 20 questions are detected as labelled. The miss
  is Q3-DEV-010, Vietnamese typed without diacritics, which is detected as `en`. The two mixed VI-EN questions
  (Q3-DEV-014, -020) are detected as `vi`.
- **Effect of that miss on answers:** the app sets the answer language from detection, so **all four systems
  answered Q3-DEV-010 in English**. `lang_match` flags it for gemma-4-e2b and qwen3-1.7b only. The English answers of
  gemini and qwen3.5-2b quote Vietnamese terms from the source (e.g. "động cơ đánh lửa cưỡng bức"), and the
  any-diacritic rule then reads them as `vi`. That is the limitation the script's docstring warns about. Counted
  strictly, Q3-DEV-010 is an answer-language failure for all four, and its cause is question detection.
- **Q-DEV-006** (Vietnamese, unanswerable) is a `lang_match` mismatch for gemini and qwen3-1.7b. Gemini's refusal
  text is Vietnamese, but its record still mismatches. The flag comes from the LLM-written refusal note it checks,
  and I did not re-classify it by hand. qwen3-1.7b answered (hallucinated) in English.
- This is the first measurement of the fixed detector on data it was not written against. Apart from Q3-DEV-010, every
  question was detected as labelled, including the three other Vietnamese questions typed without diacritics.
  `lang_match` flags no answer-language mismatch beyond the cases listed above.

## 5. Deviations

| # | Deviation | Effect |
|---|---|---|
| D1 | **Judge fallback (amendment A5) applied for the whole table.** `gemini-3.8-flash` (`JUDGE_API_KEY`) failed 5 cases in a row with HTTP 503 after retries on the first run (A5 trigger: 3 in a row). It then hit its daily quota (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`) after 12 lines: 1 ok, 11 judge errors. I judged all 16 runs with `gemini-3.5-flash-lite` (`JUDGE_MODEL` set by hand). The partial 3.8-flash lines are archived, not deleted and not counted, as `judgements.gemini-3.8-flash-partial.jsonl` in the 4 Gemini runs. | One judge in every table: `gemini-3.5-flash-lite`. |
| D2 | **8 judge errors that do not clear.** These are the known flash-lite output error: the judge writes source ids as citation markers, e.g. "markers [10] are not exactly [1, 2]" for document #10. They hit only corpus-1 answerable cases of dev-v3: Q3-DEV-004 (#10), Q3-DEV-005 (#07) and Q3-DEV-006 (#17). Two retry passes reproduced the same errors (temperature 0). | Per plan rule 5 they count as "not correct" and mark every table PROVISIONAL. Lenient and strict accuracy may be under-counted by up to 2 (gemini), 1 (gemma), 2–3 (qwen3-1.7b) and 2 (qwen3.5-2b) cases. No hallucination count is affected, because all 8 are answerable. |
| D3 | **Per-minute 429s on flash-lite** when judge processes ran back to back (each process has its own RPM window). I retried them with a 65 s pause between runs. | None. Every such case was judged ok on retry. |
| D4 | **Corpus-2 chunks** were read from `.claude/worktrees/corpus2-index/data/processed/chunks-corpus2`, as in stage 2. Chroma, keyword index and embedding cache came from the main checkout. | Same retrieval as stage 2. `same_retrieval` holds within the table. |
| D5 | **Overlap.** The gemma runs started at 18:16:52, while the first Gemini judge run started at 18:17:13. | None on answers. Local runs make no Gemini call, and the judge used a separate key. |

Gemini answer requests: 32 (one per case, no retries). Judge requests: about 140 flash-lite calls plus 12 to 3.8-flash.

## 6. Spot-check (pending)

The owner's blind sheet holds 44 items, built by the seeded scratch script `spot_gc3.py`:
- every judge verdict on an unanswerable case: 36 (9 × 4);
- a seeded 10% of answerable verdicts: 8 of 79.

The sheet is at `validation/evaluation/gc3-spot-check/blind.md` with the key in `key.md`, in the `gate-cal` worktree.
**It is not committed**, because it quotes corpus-2 passages (ADR-0008). Until it is graded, §2 rests on unverified
judge verdicts.

## 7. Provenance

| Item | Value |
|---|---|
| Branch / code | `claude/project-thread-txfczm` (PR #45) at `2bfa64f` for all 16 runs, `git_dirty = False` |
| Question tags | `eval-freeze-v1` (739676f), `eval-freeze-v2.1` (5ca88e2), `dev-freeze-v3` (560cc54) |
| Run windows (UTC+7) | gemini 18:13–18:16; gemma-4-e2b 18:16–18:22; qwen3-1.7b 18:22–18:33; qwen3.5-2b 18:33–18:42 |
| Committed | corpus-1 runs only: `gc3-dev-v1-*`, `gc3-dev-v3c1-*` (8 folders). `gc3-dev-v2-*` and `gc3-dev-v3c2-*` stay local (ADR-0008). |
| Scratch | harness `run_gc3.sh`, `run_all_local.sh`, `judge_all.sh`, `check_runs.py`, `spot_gc3.py`; raw replies `out/<model>/capture.jsonl`, `server.log`, under `C:\Users\Wotbl\AppData\Local\Temp\claude\d03bb731c08d1fba\55624b58-5871-4f48-b996-c11f81ce03eb\scratchpad\gc3\`. Raw-reply capture: the stage-2 `llm_capture.py` (unchanged). |
