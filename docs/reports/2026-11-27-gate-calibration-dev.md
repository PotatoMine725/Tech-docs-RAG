# System refusal threshold on dev: dense gate + LLM refusal, four answer models

**Runs:** 2026-11-27, 18:13–18:42 (UTC+7): 16 gate-off runs `gc3-dev-{v1,v2,v3c1,v3c2}-<system>`.
**Status:** dev measurement, **judge verdicts spot-checked by the owner** (2026-11-27, 44 items: agreement 42/44,
Cohen's κ 0.93, §6). No chosen threshold changes when the owner's labels replace the judge's. PROVISIONAL for every
system: 1–3 cases per system have no judge label (D2), and those are counted as failures.
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

## 6. Owner spot-check (graded 2026-11-27)

**Sample.** The owner's blind sheet holds 44 items, drawn by the seeded scratch script `spot_gc3.py`:
- every judge verdict on an unanswerable case: 36 (9 × 4);
- a seeded 10% of answerable verdicts: 8 of 79.

The owner graded blind: systems, sets and judge labels were hidden. Afterwards the grades were compared with the key
(`compare_spot.py`). The sheet, key and the owner's written reasons stay local in
`.claude/worktrees/gate-cal/validation/evaluation/gc3-spot-check/` and are **not committed**, because they quote corpus-2
passages (ADR-0008). Only counts and case ids are reported here.

**Agreement.** All 44 grades are filled in and parse.

| subset | agree | disagree |
|---|---|---|
| unanswerable | 35/36 | 1 |
| answerable | 7/8 | 1 |
| all | 42/44 (95.5%) | 2 |

Cohen's κ is 0.93 over all 44 items (observed 0.955, chance 0.378). The 8 answerable items are too few for a κ of
their own.

**The two disagreements:**

| item | system / case | top-1 | judge | owner | reasons |
|---|---|---|---|---|---|
| S22 | qwen3.5-2b / Q3-DEV-020 (unanswerable, XSD) | 0.5522 | correct refusal | **hallucination** | Judge: the answer "explicitly states that the documents do not cover the topic". The owner wrote no reason. The answer text first says the documents only cover XmlDocument / XmlReader, then emits `[[INSUFFICIENT]]` mid-text, so the system did **not** record a refusal (`insufficient = False`): the app shows it as an answer. The owner's label fits that system-level view. Owner to confirm. |
| S29 | gemma-4-e2b / Q3-DEV-012 (answerable, Close Class) | 0.6776 | correct | **partially correct** | Owner: everything is right except the return to the listing screen, which is missing. Judge: both *required* points are covered. Return-to-listing sits in the expected answer but not in a required point, so this is a ground-truth granularity question, not a judge error. |

**Spot-checked calibration view.** I replaced the judge's labels with the owner's for those 2 cases and recomputed:

| system | chosen t (judge = owner) | change at the chosen t | change at the current 0.5417 |
|---|---|---|---|
| gemini | off | none | none |
| gemma-4-e2b | 0.6081 | strict 10 → 9 of 23 (lenient unchanged) | strict 14 → 13 |
| qwen3-1.7b | 0.6081 | none | none |
| qwen3.5-2b | 0.6081 | none (Q3-DEV-020 is gated at 0.6081) | hallucination 2 → **3** of 9 |

The §2 tables stay as the judge-based record. With the owner's labels, no chosen threshold and no zero-hallucination
result changes.

**Systematic issues in the owner's reasons** (10 items carry a written reason, all others are bare labels):
1. **Local models answer unanswerable questions from general knowledge** and present it as grounded. Examples are
   S01 (FromSqlRaw), S02 (xUnit fixtures) and S13 (XSD), sometimes with a citation marker attached.
2. **Topic drift to the nearest document.** The question's topic is swapped for the one the corpus has: S09
   (anti-HCV answered with HBV markers from C2-29) and S03 / S35 (pneumothorax answered with consolidation opacity
   from C2-16). This is how the near-miss unanswerable cases defeat the LLM layer.
3. **Late refusal marker.** S27 (Q-DEV-006) and S35 write an answer and then `[[INSUFFICIENT]]`, and S22 writes the
   marker mid-text. The owner counts content before a refusal as a hallucination. Whenever the marker is not where
   the app expects it, the app records no refusal. This is an `answer_v3` / parser behaviour of the local models,
   worth a look before any local model ships.
4. **Wrong API for an answerable question.** S16 (qwen3.5-2b / Q3-DEV-003) used MapHealthChecks instead of MapGroup.
   The owner and the judge agree (incorrect).
5. **Judge strictness.** On these 44 items the judge was neither too lenient on unanswerable cases (35/36) nor too
   strict. The one answerable disagreement comes from required vs optional points in the ground truth (S29).

## 7. Label reliability (owner request 2026-11-27, before any judge or threshold change)

The owner asked four questions before reviewing the threshold:
1. How many independent questions does the spot-check hold?
2. Where do the label boundaries lie?
3. Does a stronger judge agree?
4. Is the comparison between systems fair?

**Threshold review waits for steps 1–4 (owner decision 2026-11-27).** No judge, threshold or config was changed.

### 7.1 Dataset: what the 44 spot-check items are

The 44 items are **not 44 independent questions**:
- **Unanswerable:** **9 unique questions × 4 systems = 36 items.** The four systems are Gemini plus the three local
  models: gemini-3.5-flash-lite, gemma-4-e2b, qwen3-1.7b and qwen3.5-2b. So each question appears 4 times, not 3.
- **Answerable:** 8 unique questions, each sampled once (seeded 10% of 79 verdicts): 4 Gemini, 3 gemma-4-e2b,
  1 qwen3.5-2b, and none from qwen3-1.7b.
- **Total:** 17 unique questions. Agreement per unique question: 8 of the 9 unanswerable questions agree on all
  4 systems. Q3-DEV-020 disagrees on 1 of its 4 items (S22). 7 of the 8 answerable questions agree; the exception
  is Q3-DEV-012 (S29).
- **Where the hallucinations sit:** the owner's 14 hallucination labels sit on **8 of the 9 unanswerable
  questions**. qwen3-1.7b has 7, qwen3.5-2b 6 and gemma-4-e2b 1 (Q3-DEV-017); Gemini has none. Only Q3-DEV-019
  draws a correct refusal from all four systems. The high hallucination share therefore comes from two models
  answering the same unanswerable questions, not from many independent cases. Because each question appears 4 times,
  the κ of 0.93 in §6 is computed over correlated items.

The item map (item → run, case, owner label; no text) is committed as `validation/evaluation/gc3-spot-labels.json`.

### 7.2 Rubric: the exact label boundaries

Labels are set by `metrics/mapping.py` from the judge's data; the judge never picks a label.
`config/prompts/judge_v1.md` defines that data.

| case | system output | judge data | label |
|---|---|---|---|
| answerable | refusal (`insufficient`) | none | false_refusal |
| answerable | answer | `contradicts_ground_truth` (incl. a must-not-claim item) | **incorrect** (wrong), whatever the coverage |
| answerable | answer | every **required** point `yes` | **correct** |
| answerable | answer | some required point `yes`/`partial`, none contradicted | **partially_correct** |
| answerable | answer | no required point covered | incorrect |
| unanswerable | bare refusal (no note, no citation) | none | correct_refusal |
| unanswerable | refusal with a related note/citations, or any answer | `presents_related_as_answer` | **hallucination** if true, else correct_refusal |

- **Optional points are ignored:** the judge lists required points only, and optional points are "context only".
  The owner's "partial" for S29 rests on an optional step, so it lands on a boundary the rubric does not grade.
- **Hallucination on unanswerable cases** is true when the response answers the question, presents related or
  adapted content as the answer, or does not say the documents lack it. Mentioning related content alongside a
  clear "not covered" is allowed.
- **Late or mid sentinel (ADR-0010 D3):** only a first line `[[INSUFFICIENT]]` is a refusal. A sentinel later in the
  text is plain text, so the record is an *answer* (`insufficient = False`), and the refusal check then judges the
  text.

The owner's labels map onto these one to one: correct, partial → partially_correct, wrong → incorrect,
false refusal, hallucination and correct refusal. Unsupported claims (groundedness) are a separate field and do not
change the label.

**Items on a boundary:**
- **Late or mid sentinel, 8 items:** S17, S22, S23, S25, S27, S35, S39, S42. All 8 are from the two Qwen models; Gemini
  and gemma never wrote one. The owner and judge agree on 7. The owner labels S23, S25, S39 and S42 correct refusals:
  same pattern, text refusal plus late sentinel. Only S22 got hallucination, without a written reason. Its text
  describes what the documents *do* cover, which the rubric allows. **S22 needs the owner's confirmation:** it is
  either a stricter rule (a refusal the app does not register counts as a failure) or a slip.
- **Refusal in plain text without any sentinel, 2 items:** S41 (gemini, `insufficient = False`, no citation) and S31
  (qwen3.5-2b, 5 citations). Both are judged and graded correct refusal.
- **Optional point, 1 item:** S29 (above).
- **Partial vs incorrect:** S16 (wrong API, judge incorrect, owner wrong) is the only answerable "wrong" in the
  sample. No partial-vs-incorrect disagreement occurred, but the sample holds only one partial and one wrong, so
  that boundary is barely tested.

### 7.3 Judge cross-validation (prepared, not run)

`scripts/evaluation/judge_crossval.py` (tested in `tests/unit/test_judge_crossval.py`) re-judges exactly the 44
owner-reviewed items:

- **What it does:** it copies each run's `run.json` and `records.jsonl` to a staging folder, runs `judge_run.py` there
  unchanged with `--cases`, and writes `judgements.crossval-<model>.jsonl` next to the run. `judgements.jsonl` is never
  read for the re-judge, never written and never replaced. `compare` prints owner vs flash-lite vs the second judge.
- **Cost:** 44 judge calls (retries extra), over 16 runs. Checked with `--estimate-only`: 0 requests spent.
- **When:** `gemini-3.8-flash` spent its free-tier daily quota today (D1). The run can go after the quota reset at
  14:00 (UTC+7) on 2026-11-28, if 3.8-flash is not returning 503s then. Under A5's 30-minute rule, a slow primary judge
  would not count as a cross-validation result.

Commands:
```powershell
$env:JUDGE_MODEL = "gemini-3.8-flash"; .venv/Scripts/python.exe scripts/evaluation/judge_crossval.py run --items validation/evaluation/gc3-spot-labels.json
.venv/Scripts/python.exe scripts/evaluation/judge_crossval.py compare --items validation/evaluation/gc3-spot-labels.json --model gemini-3.8-flash
```

### 7.4 Comparative evaluation (all 32 dev cases, gate off)

All four systems saw the **same 32 questions, the same retrieved passages** (`same_retrieval` yes in every row), the
same prompt (`answer_v3`) and the same judge (flash-lite). The comparison is therefore like for like. The one
difference that is not the model is that the Qwen models do not follow `answer_v3`'s refusal format (below).

In the table below, each cell gives the judge label first and, after the slash, the owner-checked label (owner
labels replace the judge's for the 44 reviewed items):

| system | lenient (judge / owner-checked) | strict | hallucination | false refusal (LLM) | abstention | answers with unsupported claims | unlabelled |
|---|---|---|---|---|---|---|---|
| gemini | 17 / 17 of 23 | 17 / 17 of 23 | 0 / 0 of 9 | 3 / 3 of 23 | 11/32 | 1/18 | 2 |
| gemma | 19 / 19 of 23 | 19 / 18 of 23 | 1 / 1 of 9 | 2 / 2 of 23 | 10/32 | 1/20 | 1 |
| q3-1.7b | 15 / 15 of 23 | 14 / 14 of 23 | 7 / 7 of 9 | 0 / 0 of 23 | 0/32 | 7/20 | 3 |
| q3.5-2b | 15 / 15 of 23 | 13 / 13 of 23 | 5 / 6 of 9 | 0 / 0 of 23 | 0/32 | 9/21 | 2 |

- **Abstention** counts records where the app registered a refusal (`insufficient = True`). The Qwen models never
  trigger it. They do write refusals in text, but with a late sentinel: qwen3-1.7b 4 times (3 unanswerable, 1
  answerable), qwen3.5-2b 6 times (5 unanswerable, 1 answerable). This is an instruction-following gap, not a
  missing refusal ability.
- **Groundedness:** the share of judged answers with at least one unsupported claim is 1/18 (gemini), 1/20
  (gemma-4-e2b), 7/20 (qwen3-1.7b) and 9/21 (qwen3.5-2b).
- **Unlabelled** cases are judge errors (D2), counted as not correct.

**Same-question matrix.** Labels: C correct, P partially correct, W incorrect, FR false refusal, R correct refusal,
H hallucination, ? unlabelled (judge error). An asterisk (*) marks a reviewed item; [x] is the owner's label where it
differs from the judge's. "differ" means the systems' final labels differ on that case.

| case | ans | top-1 | gemini | gemma | q3-1.7b | q3.5-2b | differ |
|---|---|---|---|---|---|---|---|
| Q-DEV-001 | Y | 0.6558 | C | C | W | W | yes |
| Q-DEV-002 | Y | 0.6363 | C | C | C | P | yes |
| Q-DEV-003 | Y | 0.7009 | C | C | C | C |  |
| Q-DEV-004 | Y | 0.5917 | FR | C | C | C | yes |
| Q2-DEV-001 | Y | 0.5905 | C* | C | C | C |  |
| Q2-DEV-002 | Y | 0.3923 | FR | FR | W | W | yes |
| Q2-DEV-003 | Y | 0.4702 | C | C | C | C |  |
| Q2-DEV-004 | Y | 0.6771 | C | C | C | C |  |
| Q2-DEV-005 | Y | 0.5061 | C | C | P | P | yes |
| Q3-DEV-001 | Y | 0.5106 | C | C | C | C |  |
| Q3-DEV-002 | Y | 0.6408 | C | C | C | W | yes |
| Q3-DEV-003 | Y | 0.4931 | FR | FR | W | W* | yes |
| Q3-DEV-004 | Y | 0.7397 | ? | C* | ? | ? | yes |
| Q3-DEV-005 | Y | 0.5629 | ? | C | ? | W | yes |
| Q3-DEV-006 | Y | 0.7917 | C | ? | ? | ? | yes |
| Q3-DEV-007 | Y | 0.6817 | W | C | C | C | yes |
| Q3-DEV-008 | Y | 0.4762 | C | C* | C | C |  |
| Q3-DEV-009 | Y | 0.6903 | C | C | W | C | yes |
| Q3-DEV-010 | Y | 0.4361 | C* | W | W | W | yes |
| Q3-DEV-011 | Y | 0.5813 | C* | C | C | C |  |
| Q3-DEV-012 | Y | 0.6776 | C | C*[P] | C | C | yes |
| Q3-DEV-013 | Y | 0.6214 | C | C | C | C |  |
| Q3-DEV-014 | Y | 0.4905 | C* | C | C | C |  |
| Q-DEV-005 | N | 0.5869 | R* | R* | R* | H* | yes |
| Q-DEV-006 | N | 0.5378 | R* | R* | H* | H* | yes |
| Q2-DEV-006 | N | 0.3041 | R* | R* | H* | R* | yes |
| Q3-DEV-015 | N | 0.5396 | R* | R* | H* | H* | yes |
| Q3-DEV-016 | N | 0.452 | R* | R* | H* | H* | yes |
| Q3-DEV-017 | N | 0.5948 | R* | H* | H* | H* | yes |
| Q3-DEV-018 | N | 0.5262 | R* | R* | H* | R* | yes |
| Q3-DEV-019 | N | 0.449 | R* | R* | R* | R* |  |
| Q3-DEV-020 | N | 0.5522 | R* | R* | H* | R*[H] | yes |

Reading of the matrix (analysis, not a decision):
- **Unanswerable (9):** Gemini refuses all 9 and gemma-4-e2b 8 of 9. qwen3-1.7b hallucinates on 7 and qwen3.5-2b on
  6 (owner-checked).
- **Answerable (23):** gemma-4-e2b has the best strict accuracy (18 owner-checked, 19 by the judge). Gemini follows
  with 17, then qwen3-1.7b 14 and qwen3.5-2b 13. Gemini's 3 false refusals (Q-DEV-004, Q2-DEV-002, Q3-DEV-003) are
  its main loss. Gemma shares two of them (Q2-DEV-002, Q3-DEV-003): those questions retrieve weakly
  (top-1 0.39 and 0.49), and both Qwen models answer them wrongly.
- **Q3-DEV-010** (Vietnamese without diacritics) is correct only for Gemini. The three local models answer in English
  (detector miss, §4) and are graded incorrect.
- **Judge errors** concentrate on Q3-DEV-004, -005 and -006 (D2), so the corpus-1 dev-v3 accuracy of every system is
  a lower bound.

## 8. Provenance

| Item | Value |
|---|---|
| Branch / code | `claude/project-thread-txfczm` (PR #45) at `2bfa64f` for all 16 runs, `git_dirty = False` |
| Question tags | `eval-freeze-v1` (739676f), `eval-freeze-v2.1` (5ca88e2), `dev-freeze-v3` (560cc54) |
| Run windows (UTC+7) | gemini 18:13–18:16; gemma-4-e2b 18:16–18:22; qwen3-1.7b 18:22–18:33; qwen3.5-2b 18:33–18:42 |
| Committed | corpus-1 runs only: `gc3-dev-v1-*`, `gc3-dev-v3c1-*` (8 folders). `gc3-dev-v2-*` and `gc3-dev-v3c2-*` stay local (ADR-0008). |
| Scratch | harness `run_gc3.sh`, `run_all_local.sh`, `judge_all.sh`, `check_runs.py`, `spot_gc3.py`; raw replies `out/<model>/capture.jsonl`, `server.log`, under `C:\Users\Wotbl\AppData\Local\Temp\claude\d03bb731c08d1fba\55624b58-5871-4f48-b996-c11f81ce03eb\scratchpad\gc3\`. Raw-reply capture: the stage-2 `llm_capture.py` (unchanged). |
