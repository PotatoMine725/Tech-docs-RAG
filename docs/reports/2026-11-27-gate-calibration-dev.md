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

## 7. Label reliability (owner request 2026-11-27)

**Owner decisions, 2026-11-27:**
- The Gemini judge and the shipped threshold **0.5417 stay**, and there is no further calibration.
- The cross-validation with a second judge is **dropped**. It was never run, and its script, briefly committed in
  e4ef524, is removed again.
- No judge, threshold, config, code or ADR was changed.

### 7.1 What the 44 spot-check items are

They are 17 unique questions, not 44:
- **Unanswerable:** 9 questions, each answered by **all 4 systems** (Gemini and the 3 local models), so 36 items.
- **Answerable:** 8 questions, each sampled once: 4 Gemini, 3 gemma-4-e2b and 1 qwen3.5-2b items.

The owner's 14 hallucination labels sit on 8 of the 9 unanswerable questions:
- qwen3-1.7b 7, qwen3.5-2b 6, gemma-4-e2b 1 (Q3-DEV-017), Gemini 0.

So the high hallucination share comes from two models on the same questions. The κ of 0.93 (§6) is computed over
correlated items. The item map (item → run, case, owner label; no text) is committed as
`validation/evaluation/gc3-spot-labels.json`.

### 7.2 Label boundaries (judge_v1 + metrics/mapping.py)

The judge supplies the data and `mapping.py` picks the label.

**Answerable cases:**
- **incorrect:** the answer contradicts the ground truth or states a must-not-claim item, whatever it covers.
- **correct:** every **required** point is covered. Optional points are context only and are not graded.
- **partially_correct:** some required point is covered or partly covered, and nothing is contradicted.
- **false_refusal:** the system refused.

**Unanswerable cases:**
- **correct_refusal:** a bare refusal. A refusal or answer that mentions related content is also a correct refusal
  if the judge's `presents_related_as_answer` is false.
- **hallucination:** `presents_related_as_answer` is true. That means the response answers the question, presents
  related or adapted content as the answer, or does not say the documents lack it.

**The sentinel (ADR-0010 D3):** only a first line starting with exactly `[[INSUFFICIENT]]` makes the record a
refusal. Anywhere else, the sentinel is plain text and the record is an answer.

The owner's labels map one to one: correct, partial → partially_correct, wrong → incorrect, false refusal,
hallucination, correct refusal.

### 7.3 The two disagreements, recorded separately

- **S22** (qwen3.5-2b / Q3-DEV-020): judge correct refusal, owner hallucination.
  - The owner's clarification, 2026-11-27: the item is graded **at system level**. The model's text says the
    documents lack the information. But `[[INSUFFICIENT]]` stands on line 3, so the app registers no refusal and
    shows the whole text as an answer. From the user's view that is a hallucination.
  - The judge graded the text, as the rubric says. So this is a difference of level, not a judge error. §8.4
    covers the fix.
- **S29** (gemma-4-e2b / Q3-DEV-012): judge correct, owner partially correct.
  - This is a **ground-truth granularity** issue. "Return to the listing screen" is in `expected_answer`, but it is
    not a required point, so the judge does not grade it.
  - dev-v3 is frozen (`dev-freeze-v3`) and is not edited.

**To review in a future dev version:**
- **Q3-DEV-012:** split "returns to the listing screen" into a required point, or drop it from `expected_answer`.
- **Q3-DEV-007:** its must-not-claim item calls "đông đặc tròn" and "đông đặc lan tỏa do nấm ngô" image-only forms.
  They are, however, caption text in the extracted slide (section 2.2). Gemini listed them and was graded incorrect
  for it. Rephrase the must-not-claim item, or accept them as variations.

## 8. Failure modes, refusal format and orchestration (analysis only, no change made)

All four systems saw the same 32 questions, the same retrieved passages (`same_retrieval` yes in every row), the
same prompt and the same judge. **No winner is concluded:** the sample is 32 dev cases, and model selection stays
under the stage-2 rule (none selected).

### 8.1 Full metric table per system (32 cases: 23 answerable, 9 unanswerable)

Gate "off" is the recorded run. At 0.5417, the current gate is simulated on the recorded dense top-1. "FR gate" is a
false refusal by the gate (before the LLM) and "FR LLM" one by the LLM. "owner-adj." uses the owner's label for the 44
reviewed items. "unlabelled" are the judge errors (D2).

| system | labels | gate | correct | partial | incorrect | unlabelled | FR gate | FR LLM | correct refusal | hallucination |
|---|---|---|---|---|---|---|---|---|---|---|
| gemini | judge | off | 17 | 0 | 1 | 2 | 0 | 3 | 9 | 0 |
| gemini | judge | 0.5417 | 11 | 0 | 1 | 2 | 8 | 1 | 9 | 0 |
| gemini | owner-adj. | off | 17 | 0 | 1 | 2 | 0 | 3 | 9 | 0 |
| gemini | owner-adj. | 0.5417 | 11 | 0 | 1 | 2 | 8 | 1 | 9 | 0 |
| gemma-4-e2b | judge | off | 19 | 0 | 1 | 1 | 0 | 2 | 8 | 1 |
| gemma-4-e2b | judge | 0.5417 | 14 | 0 | 0 | 1 | 8 | 0 | 8 | 1 |
| gemma-4-e2b | owner-adj. | off | 18 | 1 | 1 | 1 | 0 | 2 | 8 | 1 |
| gemma-4-e2b | owner-adj. | 0.5417 | 13 | 1 | 0 | 1 | 8 | 0 | 8 | 1 |
| qwen3-1.7b | judge | off | 14 | 1 | 5 | 3 | 0 | 0 | 2 | 7 |
| qwen3-1.7b | judge | 0.5417 | 10 | 0 | 2 | 3 | 8 | 0 | 7 | 2 |
| qwen3-1.7b | owner-adj. | off | 14 | 1 | 5 | 3 | 0 | 0 | 2 | 7 |
| qwen3-1.7b | owner-adj. | 0.5417 | 10 | 0 | 2 | 3 | 8 | 0 | 7 | 2 |
| qwen3.5-2b | judge | off | 13 | 2 | 6 | 2 | 0 | 0 | 4 | 5 |
| qwen3.5-2b | judge | 0.5417 | 9 | 1 | 3 | 2 | 8 | 0 | 7 | 2 |
| qwen3.5-2b | owner-adj. | off | 13 | 2 | 6 | 2 | 0 | 0 | 3 | 6 |
| qwen3.5-2b | owner-adj. | 0.5417 | 9 | 1 | 3 | 2 | 8 | 0 | 6 | 3 |

**Retrieval context:** the expected section is in the top 5 for 20 of the 23 answerable cases. The misses are
Q2-DEV-001, Q2-DEV-002 and Q3-DEV-003. On Q2-DEV-002 and Q3-DEV-003, Gemini's and gemma's false refusals are
the right behaviour for the passages they got. The Qwen models answered both from the wrong passages: a history
chapter, and `MapHealthChecks` instead of `MapGroup`.

### 8.2 Failure modes per model (every answer not labelled correct / correct refusal, plus late sentinels)

I classified each failing answer by reading it. A case can carry several tags; the primary tag is listed first.

| failure mode | gemini | gemma-4-e2b | qwen3-1.7b | qwen3.5-2b |
|---|---|---|---|---|
| Context substitution: general knowledge (answers or invents API/code not in the passages) | 0 | 0 | 5: Q-DEV-006, Q2-DEV-006, Q3-DEV-015, Q3-DEV-016, Q3-DEV-020 | 5: Q-DEV-002 (partial), Q-DEV-005, Q-DEV-006, Q3-DEV-015, Q3-DEV-016 |
| Context substitution: nearest-document drift (a related passage used as the answer) | 0 | 1: Q3-DEV-017 | 4: Q3-DEV-017, Q3-DEV-018 (HCV→HBV), Q2-DEV-002, Q3-DEV-003 | 3: Q3-DEV-017, Q2-DEV-002, Q3-DEV-003 |
| Misreading or conflating the retrieved facts (swapped cases, wrong rule) | 0 | 1: Q3-DEV-010 | 3: Q-DEV-001, Q3-DEV-009, Q3-DEV-010 | 4: Q-DEV-001, Q3-DEV-002, Q3-DEV-005, Q3-DEV-010 |
| Late or malformed abstention (sentinel not at the start of line 1) | 1: Q3-DEV-015 (`[[INSUFFICient]]`) | 0 | 4: Q-DEV-003, Q-DEV-005, Q-DEV-006, Q3-DEV-019 | 6: Q-DEV-006 (`[INSUFFICIENT]`), Q2-DEV-006, Q3-DEV-008, Q3-DEV-017, Q3-DEV-019, Q3-DEV-020 |
| Missing or wrong citation (answered with no valid marker; wrong passage cited) | 1: Q3-DEV-015 | 0 | 9: no marker on Q-DEV-002, -003, -005, -006, Q3-DEV-013, -018, -019, -020; wrong passage on Q2-DEV-005 | 5: no marker on Q-DEV-002, Q-DEV-006, Q2-DEV-006, Q3-DEV-019, Q3-DEV-020 |
| Wrong answer language | 0 (Q3-DEV-010 answered in en, graded correct) | 1: Q3-DEV-010 | 2: Q3-DEV-010, Q-DEV-006 | 1: Q3-DEV-010 |
| False refusal by the LLM | 3: Q-DEV-004 (section retrieved); Q2-DEV-002, Q3-DEV-003 (section not retrieved) | 2: Q2-DEV-002, Q3-DEV-003 (section not retrieved) | 0 | 0 |
| Other | Q3-DEV-007 (ground-truth issue, §7.3) | Q3-DEV-012 (omits an optional step, §7.3) | Q2-DEV-005 (partial); Q3-DEV-005 echoes the question back (unlabelled) | Q2-DEV-005 (partial, omits details) |
| Judge error, unlabelled (D2) | Q3-DEV-004, Q3-DEV-005 | Q3-DEV-006 | Q3-DEV-004, Q3-DEV-005, Q3-DEV-006 | Q3-DEV-004, Q3-DEV-006 |

Read off the table (analysis):
- **Main failure on unanswerable questions.** For both Qwen models it is **context substitution**, mostly general
  knowledge: an answer is written with no refusal at all. gemma-4-e2b fails only on the near-miss Q3-DEV-017, by
  drift. Gemini has no substitution.
- **Wrong language on Q3-DEV-010** comes from question detection (§4), not from the models. Q-DEV-006 is the only
  model-caused language error (qwen3-1.7b).
- **The 8 judge errors are not model failures.** Of the unlabelled answers, Gemini's, gemma's and qwen3.5-2b's read
  correct. qwen3-1.7b's Q3-DEV-004 contains a wrong claim, and its Q3-DEV-005 only echoes the question.

### 8.3 Late abstention: where the sentinel sits and what the app showed

All 11 answers holding a sentinel that is not at the start of line 1 were recorded with `insufficient = False`. The
app therefore showed the **whole text, sentinel included, as an answer**: no "not enough information" banner, and
no related-citations handling.

| system | case | answerable | label (final) | sentinel form | position | text before the sentinel |
|---|---|---|---|---|---|---|
| gemini | Q3-DEV-015 | no | correct refusal | `[[INSUFFICient]]` (wrong case) | line 1 of 2, char 0 | none: a case typo |
| qwen3-1.7b | Q-DEV-003 | yes | correct | `[[INSUFFICIENT]]` | line 1/1, char 681 of 830 | a full answer |
| qwen3-1.7b | Q-DEV-005 | no | correct refusal | `[[INSUFFICIENT]]` | line 3/3, char 196 | a refusal in words |
| qwen3-1.7b | Q-DEV-006 | no | hallucination | `[[INSUFFICIENT]]` | line 8/8, char 725 | a hallucinated how-to, then "does not provide" |
| qwen3-1.7b | Q3-DEV-019 | no | correct refusal | `[[INSUFFICIENT]]` | line 1/1, char 141 | a refusal in words |
| qwen3.5-2b | Q-DEV-006 | no | hallucination | `[INSUFFICIENT]` (single brackets) | line 39/40, char 1179 | hallucinated code |
| qwen3.5-2b | Q2-DEV-006 | no | correct refusal | `[[INSUFFICIENT]]` | line 3/4, char 305 | a refusal in words |
| qwen3.5-2b | Q3-DEV-008 | yes | correct | `[[INSUFFICIENT]]` | line 3/3, char 522 of 539 | a full correct answer plus a wrong "missing" sentence |
| qwen3.5-2b | Q3-DEV-017 | no | hallucination | `[[INSUFFICIENT]]` | line 3/4, char 263 | a drifted answer |
| qwen3.5-2b | Q3-DEV-019 | no | correct refusal | `[[INSUFFICIENT]]` | line 3/4, char 279 | a refusal in words |
| qwen3.5-2b | Q3-DEV-020 | no | hallucination (owner) / correct refusal (judge) | `[[INSUFFICIENT]]` | line 3/4, char 376 | a refusal in words (S22) |

**Refusal in words with no sentinel anywhere:** 1 answer, qwen3.5-2b on Q3-DEV-018 (judge: correct refusal). It
says the documents do not contain the information, carries 5 citations, and was shown as an answer. I counted with
a Vietnamese/English "not in the documents" phrase search over all 128 answers, then checked the hits by hand.

### 8.4 Generation prompt review (answer_v3)

The failing answers break these `config/prompts/answer_v3.md` instructions:
- **rule 1 (only CONTEXT facts):** all general-knowledge substitutions, 10 Qwen answers;
- **rule 2 (sentinel as the first line, nothing else):** all 11 late or malformed sentinels;
- **rule 3 (a marker on every fact sentence):** the 14 answers with no valid marker, and bare marker lists
  (qwen3.5-2b on Q3-DEV-003 and Q3-DEV-005);
- **"Write the answer in {answer_language}":** qwen3-1.7b on Q-DEV-006.

Nearest-document drift breaks **no** rule: the facts are in the CONTEXT, and nothing says that a passage about a
related entity is not an answer.

A concrete proposal is in [`docs/plans/answer-v4-draft.md`](../plans/answer-v4-draft.md) (PROPOSED, not used anywhere):
- a decide-first step with a "related but different is not an answer" rule;
- the sentinel fenced to line 1 only, and a distinct phrase for partial answers;
- a citation example;
- "keep each value with its case";
- the language and refusal rules repeated after the CONTEXT.

### 8.5 Output orchestration options (each needs an ADR-0010 D3 amendment)

I simulated each option on the 128 recorded answers with owner-adjusted labels. A triggered answer becomes a refusal:
false refusal if answerable, correct refusal if unanswerable. That assumes the refusal shows only the note, not the
text before the sentinel. Counts are hallucination of 9 / false refusal (LLM) of 23 / lenient of 23.

| option | gemini | gemma-4-e2b | qwen3-1.7b | qwen3.5-2b | cases flipped |
|---|---|---|---|---|---|
| as run (ADR-0010 D3 today) | 0 / 3 / 17 | 1 / 2 / 19 | 7 / 0 / 15 | 6 / 0 / 15 | none |
| **O1** sentinel anywhere (case-insensitive, `[` or `[[`) → refusal | 0 / 3 / 17 | 1 / 2 / 19 | 6 / 1 / 14 | 3 / 1 / 14 | qwen3-1.7b: Q-DEV-006 H→R, Q-DEV-003 C→FR. qwen3.5-2b: Q-DEV-006, Q3-DEV-017, Q3-DEV-020 H→R; Q3-DEV-008 C→FR. Gemini's Q3-DEV-015 now registers as a refusal (label unchanged) |
| O2 = O1 + a "not in the documents" sentence anywhere → refusal | same as O1 on these 32 | same | same | same | no extra flip here |
| O3 drop answers with no valid citation → refusal | 0 / 3 / 17 | 1 / 2 / 19 | 4 / 3 / 12 | 4 / 1 / 14 | qwen3-1.7b: Q-DEV-006, Q3-DEV-018, Q3-DEV-020 H→R; Q-DEV-002, Q-DEV-003, Q3-DEV-013 C→FR. qwen3.5-2b: Q-DEV-006, Q3-DEV-020 H→R; Q-DEV-002 P→FR |
| O1 + O3 | 0 / 3 / 17 | 1 / 2 / 19 | 4 / 3 / 12 | 3 / 2 / 13 | union of the above |

**Side effects:**
- **O1** turns the two "full answer, then a stray sentinel" cases (qwen3-1.7b Q-DEV-003, qwen3.5-2b Q3-DEV-008) into
  false refusals. It also hides any useful text written before the sentinel.
- **O2** would also refuse the partial answers that answer_v3 rule 2 *asks for*: answer the covered part, then one
  "what is missing" sentence. On these 32 it adds nothing over O1, so it carries risk without measured gain.
- **O3** costs three correct qwen3-1.7b answers that only lacked markers. It also depends on marker parsing, which
  varies by model.
- **None of the options touches Gemini's or gemma's labels.** Their failures are not format failures.

**Recommended option (analysis, owner decides): O1, together with the answer_v4 prompt change.**
- **What O1 gains:** it removes the largest share of shown-but-refused content (4 of 13 Qwen hallucinations) for 2
  false refusals, fixes Gemini's case-typo display bug, and needs only a parser change in
  `parse_answer_text`.
- **What O1 does not fix:** the main Qwen failure, an answer with no refusal at all. That needs the prompt (answer_v4)
  or a different model. Neither is decided here.
- **What adopting it needs:** an ADR-0010 D3 amendment, unit tests and a pre-registered dev re-run.

The threshold review waits for these steps (owner decision 2026-11-27). No threshold is changed.

## 9. Provenance

| Item | Value |
|---|---|
| Branch / code | `claude/project-thread-txfczm` (PR #45) at `2bfa64f` for all 16 runs, `git_dirty = False` |
| Question tags | `eval-freeze-v1` (739676f), `eval-freeze-v2.1` (5ca88e2), `dev-freeze-v3` (560cc54) |
| Run windows (UTC+7) | gemini 18:13–18:16; gemma-4-e2b 18:16–18:22; qwen3-1.7b 18:22–18:33; qwen3.5-2b 18:33–18:42 |
| Committed | corpus-1 runs only: `gc3-dev-v1-*`, `gc3-dev-v3c1-*` (8 folders). `gc3-dev-v2-*` and `gc3-dev-v3c2-*` stay local (ADR-0008). |
| Scratch | harness `run_gc3.sh`, `run_all_local.sh`, `judge_all.sh`, `check_runs.py`, `spot_gc3.py`; raw replies `out/<model>/capture.jsonl`, `server.log`, under `C:\Users\Wotbl\AppData\Local\Temp\claude\d03bb731c08d1fba\55624b58-5871-4f48-b996-c11f81ce03eb\scratchpad\gc3\`. Raw-reply capture: the stage-2 `llm_capture.py` (unchanged). |
