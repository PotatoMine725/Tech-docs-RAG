# Small local LLMs as the answer model of a grounded bilingual RAG assistant: stage-2 screening benchmark

**Runs:** quality runs `llm2-*` on 2026-11-26, 20:05–21:12 (UTC+7); RAM/TTFT re-measure `llm2r-*` (amendment A3) on
2026-11-27, 07:29–08:25 (UTC+7).
**Status:** stage-2 decision record. The pre-registered rule is applied in §5. **Outcome: no model is selected.**
**Pre-registration:** `docs/plans/local-llm-preregistration.md` (§3–§5, amendments A1–A4). A4 (new judge) was **not
applied**; see deviation D7.
**Predecessor:** `docs/reports/2026-11-26-local-llm-stage1.md`.

---

## Abstract

We screened three quantised language models of about 2 billion parameters as offline replacements for the cloud
answer model (`gemini-3.5-flash-lite`) of a retrieval-augmented question-answering assistant. The assistant works
over English technical corpora and receives questions in English and Vietnamese. The three models are
qwen3.5-2b-instruct, gemma-4-e2b-it and qwen3-1.7b, all Q4_K_M GGUF files served by llama.cpp b12359 on the CPU only.

Every model ran the pre-registered evaluation split: 108 questions, of which 94 are answerable and 14 unanswerable,
over two corpora. Retrieval and the prompt were held fixed, and an LLM judge (`gemini-3.5-flash-lite`, `judge_v1`)
graded the answers.

**Answer quality was at Gemini's level.**
- Lenient accuracy was 65.96%, 68.09% and 64.89%, against Gemini's 63.83%.
- No paired difference from Gemini was significant (exact McNemar test, p ≥ 0.06).
- Every model cleared both accuracy thresholds.

**Memory passes for all three after A3.** With the fixed runtime `--cache-ram 0`, the peak working set of
`llama-server` over the same 108 requests was 2.03, 2.94 and 2.41 GB, under the 3.5 GB cap. With llama.cpp's default
8 GiB host prompt cache it had been 8.29, 5.26 and 10.89 GB. 227 of 228 local answers were byte-identical between the
two configurations.

**No model passed every pre-registered threshold, so no model is selected.**
- **Language match failed for all three** (93.4–94.7%, against 95%). gemma-4-e2b fails on this threshold only, by one
  case.
- **Hallucination failed for both Qwen models:** each answered 2 of the 14 unanswerable questions.
- qwen3.5-2b also missed the citation-marker threshold, at 10.5% against 10%.

The language failures trace mainly to the application's own detector: Vietnamese typed without diacritics was
detected as English, so the prompt told the models to answer in English. The detector was fixed in PR #40; under the
owner's instruction these runs used the pre-fix detector, and the new detector is measured in a later round.

This is not a perfectly controlled experiment: retrieval differed from the Gemini reference at ranks 4–5 on three
cases. All three were stopped by the retrieval gate in every run, so no LLM saw them (§3.6, deviation D1).

---

## 1. Introduction

The assistant (CLAUDE.md §1) answers questions from a curated corpus, with citations. Gemini is the default answer
model. The project is testing whether a small local model can answer offline on a low-end target machine: a
10th-generation Intel CPU with 8 GB RAM in total, of which the LLM may use 3.5 GB under amendment A1.

The evaluation has four pre-registered stages (§3 of the pre-registration):
1. smoke test;
2. screen (this report);
3. pick and Vietnamese owner grading;
4. real-machine measurement.

Stage 1 sent 12 development questions to five models. It dropped the two 4B models on memory under amendment A1 and
passed the three 2B models to stage 2.

**Research question.** On the frozen evaluation split, with retrieval and prompt held fixed, does any 2B-class local
model meet every pre-registered quality, latency and memory threshold relative to the Gemini baseline?

## 2. Method

### 2.1 Systems under test

| Model ID (alias) | Class | File | Size (bytes) |
|---|---|---|---|
| qwen3.5-2b-instruct-q4_k_m | 2B | same GGUF as stage 1 | 1,280,835,840 |
| gemma-4-e2b-it-q4_k_m | 2B | same GGUF as stage 1 | 3,106,738,272 |
| qwen3-1.7b-q4_k_m | 2B | same GGUF as stage 1 | 1,282,439,264 |
| gemini-3.5-flash-lite | baseline (cloud) | n/a | n/a |

**Server.** The server was the llama.cpp CPU build b12359. Two configurations were run over the same requests:

| Runs | Server command | Used for |
|---|---|---|
| `llm2-*` | `llama-server -m <gguf> --alias <id> -c 4096 -t 4 -ngl 0 --parallel 1 --jinja --seed 42 --port 8080` | quality (judge), language, markers, refusals |
| `llm2r-*` | the same plus `--cache-ram 0` (A3) | RAM and TTFT |

With `--cache-ram 0` the server logs `--cache-idle-slots requires --cache-ram, disabling`; in-slot prompt-prefix reuse
stays on.

Each request carried `temperature 0`, `seed 42`, `max_tokens 512`, `cache_prompt true` and
`chat_template_kwargs.enable_thinking = false`.

We checked the captured raw replies of the `llm2` runs (228 local calls) for reasoning output:
- every call returned HTTP 200 with `finish_reason = stop`;
- no reply contained a `<think>` block or a non-empty `reasoning_content`;
- the longest replies were 279, 331 and 459 tokens, under the 512 cap;
- prompts were 889–3,171 tokens long.

### 2.2 Pipeline (held constant)

| Setting | Value |
|---|---|
| `LLM_PROVIDER` | `llamacpp` (or Gemini for the baseline) |
| `ANSWER_PROMPT_VERSION` | `answer_v3` |
| `EMBEDDING_PROVIDER` | `embeddinggemma` |
| `RETRIEVAL_MODE` | `hybrid` (dense + SQLite FTS5, reciprocal-rank fusion) |
| `RERANK_PROVIDER` | `none` |

A retrieval gate refuses before any LLM call when the dense top-1 similarity is below 0.5417. Arm A was used,
with the header-aware chunks.

**Code version.** Every run, `llm2` and `llm2r`, records `git_commit = a75c0fa` and `git_dirty = False`. The `llm2r`
runs were started from a separate detached worktree at `a75c0fa`, so they use the **pre-fix** language detector, the
same one as the `llm2` runs. Evidence: the module imported at run time was
`.claude/worktrees/llm2r-a75c0fa/src/knowledge_assistant/application/common/language.py` with sha256
`135e4a68…c84c38a`, equal to `git show a75c0fa:…/language.py`. The fixed detector at `f7b8588` hashes to
`98cd12e4…9995ba`. `run_eval.py` puts its own checkout's `src` first on `sys.path`, ahead of the editable install.

### 2.3 Data

| Run set | Questions | Corpus | Cases | Answerable / unanswerable |
|---|---|---|---|---|
| v1 | eval-v1 | corpus 1 (technical docs) | 36 | from the frozen split |
| v2 | eval-v2 | corpus 2 (multi-domain, EN/VI) | 58 | from the frozen split |
| v2c1 | eval-v2, corpus-1 cases | corpus 1 | 14 | 10 / 4 |
| **Pooled** | | | **108** | **94 / 14** |

The v2c1 set was added (deviation D3). All metrics below are pooled per model over the three sets.

### 2.4 Metrics and thresholds (pre-registration §4)

| Metric | Definition | Threshold |
|---|---|---|
| Lenient accuracy | judge `correct` + `partially_correct`, over 94 answerable | ≥ Gemini − 10 pp (≥ 53.83%) |
| Strict accuracy | judge `correct`, over 94 answerable | ≥ Gemini − 15 pp (≥ 42.45%) |
| Hallucination | judge `hallucination` on the 14 unanswerable | ≤ 1 of 14 |
| False refusal, LLM (A2) | answerable cases the LLM refused, over answerable cases that reached the LLM | ≤ 10% |
| Missing marker | answered cases with no valid `[n]` citation marker | ≤ 10% |
| Language match | LLM-written text whose detected language equals the question's label | ≥ 95% |
| TTFT median | recorded `time_to_first_token_ms` over LLM calls, `llm2r` runs (A3) | ≤ 15 s (2B) |
| Peak RAM | highest `PeakWorkingSet64` of `llama-server`, sampled at 1 Hz, `llm2r` runs (A3) | ≤ 3.5 GB (2B, A1) |
| VI owner grade | 20 Vietnamese answers, graded blind by the owner | ≥ 16/20 (stage 3 only) |

**False refusal (A2).** Gate refusals (answerable, gate fired) are reported without a threshold; they are identical
for every model because retrieval is. The ≤ 10% threshold applies to LLM refusals. The definition as written before
A2 (all answerable cases) is also reported.

**Selection rule (§5).** Among models that pass every threshold in their class, pick the highest lenient accuracy.
If two are within 3 pp, pick the one with the lower TTFT median.

### 2.5 Judging and statistics

The judge was `gemini-3.5-flash-lite` with prompt `judge_v1`, and every `llm2` run was judged. The `llm2r` runs were
not judged: their answers are compared with `llm2` by exact text (§3.4). Amendment A4 (`gemini-3.8-flash`) was
started and abandoned on the owner's instruction (deviation D7), so all quality tables use one judge.

Eleven answer checks failed in the same way every time (`JudgeOutputError`). The judge echoed the chunk's numeric
corpus-1 `source_id` (e.g. `[16]`) instead of the citation marker (e.g. `[1]`). These 11 stay unjudged, and the
judge was not modified. They count as not correct in the accuracy numerator. Bounds that assume they are all
correct are given in §3.1.

| Model | Unjudged (run set: cases) |
|---|---|
| Gemini | v2c1: Q2-EVAL-063 |
| qwen3.5-2b | v1: Q-EVAL-015; v2c1: Q2-EVAL-059, Q2-EVAL-061, Q2-EVAL-066 |
| gemma-4-e2b | v1: Q-EVAL-026; v2c1: Q2-EVAL-064, Q2-EVAL-065 |
| qwen3-1.7b | v1: Q-EVAL-025; v2c1: Q2-EVAL-061, Q2-EVAL-068 |

**Spot-check (ADR-0004 D12).** Sample: every refusal-check verdict and every verdict mapped to hallucination (12),
plus seeded random answer verdicts (`random.Random(42)`) up to 10% of the 278 ok verdicts: 28 in total. **The agent
(Claude) graded the sample blind, not the owner**, then compared it with the judge:

| Agreement | Count |
|---|---|
| Exact label | 24/28 |
| Lenient bucket (correct + partial vs other) | 27/28 |
| Required items (refusal checks and hallucinations) | 12/12 |

The four disagreements:

| Item | Judge | Agent |
|---|---|---|
| Gemini Q-EVAL-026 | partially correct | correct |
| gemma-4-e2b Q-EVAL-013 | partially correct | correct |
| qwen3.5-2b Q2-EVAL-047 | correct (an unsupported claim was noted) | partially correct |
| qwen3-1.7b Q-EVAL-026 | partially correct | incorrect (the version number it gave is not in the context) |

Only the last one changes a lenient count: qwen3-1.7b would drop to 60/94 = 63.83%, still above 53.83%. No pass/fail
changes. All 5 hallucination verdicts were confirmed. The blind sheet is kept for the owner to re-grade (Appendix A).

**Statistics.** Proportions have 95% Wilson intervals. Paired accuracy differences against Gemini use an exact
two-sided McNemar test on the same 94 cases. These statistics were not pre-registered. They help interpretation and
do not change the go/no-go rule.

### 2.6 Machine

- CPU: Intel i7-12700H, 14 cores (6P + 8E), 20 threads. RAM: 25.4 GB (23.6 GiB) in total. OS: Windows 11.
- This is **not** the target machine. Latency and memory values here are relative across models, not target-machine
  values.
- Each model ran in its own server process, one after another. Only that one `llama-server` was running.
- CPU load just before each server started (qwen3.5-2b / gemma-4-e2b / qwen3-1.7b): 6 / 33 / 4% in `llm2`,
  38 / 24 / 30% in `llm2r`. Other sessions were active on the machine; "system memory in use" is whole-machine.
- No Gemini or judge call ran during the `llm2r` runs.

## 3. Results

### 3.1 Main table (pooled, 108 cases per model)

Quality columns: `llm2` runs, judge `gemini-3.5-flash-lite`. TTFT and RAM: `llm2r` runs (A3).

| Metric (threshold) | Gemini (ref.) | qwen3.5-2b | gemma-4-e2b | qwen3-1.7b |
|---|---|---|---|---|
| Lenient (≥ 53.83%) | 63.83% (60/94) | 65.96% (62/94) ✅ | **68.09%** (64/94) ✅ | 64.89% (61/94) ✅ |
| 95% CI | 53.8–72.8 | 55.9–74.7 | 58.1–76.6 | 54.8–73.8 |
| Strict (≥ 42.45%) | 57.45% (54/94) | 48.94% (46/94) ✅ | 50.00% (47/94) ✅ | 46.81% (44/94) ✅ |
| 95% CI | 47.4–67.0 | 39.1–58.9 | 40.1–59.9 | 37.0–56.8 |
| Lenient, if every unjudged case were correct | 64.89% | 70.21% | 71.28% | 68.09% |
| Hallucination (≤ 1/14) | 0/14 | 2/14 ❌ | 1/14 ✅ | 2/14 ❌ |
| False refusal, gate (reported only) | 21/94 (22.3%) | 21/94 | 21/94 | 21/94 |
| False refusal, LLM, A2 (≤ 10%) | 10/73 (13.7%) | 0/73 ✅ | 5/73 (6.8%) ✅ | 0/73 ✅ |
| False refusal, all answerable, as written before A2 | 31/94 (33.0%) | 21/94 (22.3%) | 26/94 (27.7%) | 21/94 (22.3%) |
| Missing marker (≤ 10%) | 0/63 (0.0%) | 8/76 (10.53%) ❌ | 1/69 (1.45%) ✅ | 7/76 (9.21%) ✅ |
| Language match (≥ 95%) | 74/76 (97.37%) | 72/76 (94.74%) ❌ | 72/76 (94.74%) ❌ | 71/76 (93.42%) ❌ |
| TTFT median / p90, `llm2r` (≤ 15 s) | n/a | 10.16 / 14.09 s ✅ | 5.51 / 7.94 s ✅ | 9.78 / 16.34 s ✅ |
| Peak working set, `llm2r` (≤ 3.5 GB) | n/a | 2.03 GB ✅ | 2.94 GB ✅ | 2.41 GB ✅ |
| Unjudged (answerable) | 1 | 4 | 3 | 3 |

**Notes on the table.**
- **Judge labels, answerable** (correct / partially correct / incorrect / false refusal / unjudged):

  | Model | correct | partially correct | incorrect | false refusal | unjudged |
  |---|---|---|---|---|---|
  | Gemini | 54 | 6 | 2 | 31 | 1 |
  | qwen3.5-2b | 46 | 16 | 7 | 21 | 4 |
  | gemma-4-e2b | 47 | 17 | 1 | 26 | 3 |
  | qwen3-1.7b | 44 | 17 | 9 | 21 | 3 |

- **Hallucination cases:** qwen3.5-2b: Q-EVAL-033, Q-EVAL-035; gemma-4-e2b: Q-EVAL-033; qwen3-1.7b: Q-EVAL-035,
  Q2-EVAL-036.
- **Missing-marker cases:**
  - qwen3.5-2b: Q-EVAL-004, -006, -010, -019, -032, Q2-EVAL-036, -049, -068;
  - gemma-4-e2b: Q2-EVAL-015;
  - qwen3-1.7b: Q-EVAL-007, -009, -010, -023, -026, -033, Q2-EVAL-064.
- **LLM refusals (A2):**
  - Gemini: Q-EVAL-006, -008, -009, -014, -017, -030, -032, Q2-EVAL-011, -049, -066;
  - gemma-4-e2b: Q-EVAL-006, -007, -014, -032, Q2-EVAL-056.
- **The baseline would itself fail the LLM false-refusal threshold** (13.7%). The thresholds are relative to Gemini
  only for accuracy.
- **Misplaced refusal sentinel (sensitivity note, not re-scored).** Seven local answers contain `[[INSUFFICIENT]]`
  later than the first line, so they are parsed as answers (the rule defines a refusal as the sentinel on the first
  line). qwen3.5-2b: Q-EVAL-019, -031, Q2-EVAL-036, -049; qwen3-1.7b: Q-EVAL-031, -033, Q2-EVAL-041; gemma and Gemini:
  none. Several of them are on the missing-marker lists above. For the two unanswerable ones, the judge gave
  `correct_refusal`, which the spot-check confirmed.

### 3.2 Paired comparison with Gemini (not pre-registered)

| Model | Lenient: Gemini-only / model-only | p | Strict: Gemini-only / model-only | p |
|---|---|---|---|---|
| qwen3.5-2b | 5 / 7 | 0.77 | 12 / 4 | 0.077 |
| gemma-4-e2b | 5 / 9 | 0.42 | 15 / 8 | 0.21 |
| qwen3-1.7b | 9 / 10 | 1.00 | 17 / 7 | 0.064 |

- **No accuracy difference reaches significance.** The lenient gains of the local models are small and within noise.
- **They come mostly from refusing less** at the LLM step; some of those extra answers are graded partially correct.
- **On strict accuracy all three trend below Gemini** (8–11 pp). At n = 94, that is not significant.
- **The three models are statistically indistinguishable on accuracy.**

### 3.3 Latency

| Model | TTFT median, stage 1 (7 calls) | TTFT median / p90, `llm2` (default cache) | TTFT median / p90, `llm2r` (`--cache-ram 0`) | Generation median, `llm2` → `llm2r` | Wall time for 108 cases, `llm2` → `llm2r` |
|---|---|---|---|---|---|
| qwen3.5-2b | 10.47 s | 10.89 / 15.27 s | 10.16 / 14.09 s | 16.92 → 15.49 s | 21.5 → 19.9 min |
| gemma-4-e2b | 5.54 s | 5.76 / 8.05 s | 5.51 / 7.94 s | 10.74 → 10.08 s | 15.0 → 13.9 min |
| qwen3-1.7b | 11.32 s | 10.07 / 16.69 s | 9.78 / 16.34 s | 18.32 → 16.72 s | 24.0 → 21.6 min |

`llm2r` per set, TTFT median (v1 / v2 / v2c1): qwen3.5-2b 8.03 / 12.77 / 8.23 s; gemma-4-e2b 4.38 / 6.99 / 4.55 s;
qwen3-1.7b 7.25 / 13.75 / 7.48 s.

- **Removing the host cache did not slow the runs.** TTFT and generation were 3–9% lower in `llm2r`. The 76 prompts
  are all distinct, so the host cache had nothing useful to restore; in-slot prefix reuse is unaffected. The
  difference is within what the CPU-load confound (§2.6) can explain; we do not claim the flag speeds anything up.
- **Gemma's TTFT median is about half that of either Qwen model**, as in stage 1.
- **qwen3-1.7b's p90 (16.3 s) is over 15 s, though its median is under.** The threshold is on the median.
- **TTFT is longer on corpus-2 questions** for both Qwen models, probably because of longer prompts (not tabulated).

### 3.4 Memory

| Model | Peak working set, default cache (`llm2`) | Peak working set, `--cache-ram 0` (`llm2r`) | Private bytes, `llm2` → `llm2r` | System memory in use, peak, `llm2` → `llm2r` | Stage-1 peak working set |
|---|---|---|---|---|---|
| qwen3.5-2b | 8,289 MB ❌ | **2,033 MB** ✅ | 7,276 → 1,023 MB | 21.96 → 14.46 GB | 2,556 MB |
| gemma-4-e2b | 5,262 MB ❌ | **2,943 MB** ✅ | 3,822 → 1,504 MB | 18.58 → 12.99 GB | 3,066 MB |
| qwen3-1.7b | 10,894 MB ❌ | **2,406 MB** ✅ | 9,945 → 1,340 MB | 23.40 → 12.44 GB | 2,927 MB |

- MB = 10⁶ bytes. Same sampler both times (`ramwatch.ps1`, 1 Hz, `PeakWorkingSet64`); `llm2r` took 874, 610 and 952
  samples.
- System memory in use is whole-machine and includes other sessions; it is context, not a metric.
- **Cause of the difference:** llama.cpp's host-memory prompt cache (`--cache-ram`, default 8,192 MiB) kept the state
  of every finished prompt. A controlled diagnostic before A3 (gemma, 20 distinct prompts) measured private bytes
  +22 MB per prompt with the default and flat with `--cache-ram 0`. The default grew with the number of distinct
  requests per server: 7 in stage 1, 76 in stage 2.
- **Answers did not change.** Exact text comparison of `llm2r` against `llm2`, every case of every model and set:
  228 of 228 cases that reached the LLM had the same retrieval and the same gate result; 227 had byte-identical answer
  text. The one difference is qwen3-1.7b, v2, Q2-EVAL-017: same retrieval, same citations, same `insufficient`
  flag, text identical for the first 188 characters (225 vs 227 characters). All 96 gate-stopped cases are identical.
  The stop condition (more than 10 differing cases) was not met, so quality is not re-judged.
- **Working set remains a configuration-sensitive metric.** In the diagnostic the OS trimmed gemma's working set by
  half at one point while private bytes kept rising. On this 25 GB machine there was little memory pressure; only
  stage 4 on the 8 GB machine can show resident behaviour under pressure.

### 3.5 Language match

**Every language mismatch on the corpus-2 questions falls on the same four cases:** Q2-EVAL-001, -003, -008 and
-022. Gemini mismatches on two of them, 001 and 003. qwen3-1.7b has one more mismatch, Q-EVAL-026: Vietnamese text
around an English NuGet error message.

### 3.6 Retrieval identity

`llm_run_summary.py --reference llm2-eval-<set>-gemini --known-differences Q-EVAL-011,Q2-EVAL-033,Q2-EVAL-071`
returned **exit 0** for all six invocations (v1, v2, v2c1; `llm2` and `llm2r`). The script accepts a listed case only
if the gate fired on it in both the run and the reference; any other difference would exit 1.

| Case | Differs from the reference, `llm2` | Differs, `llm2r` | Where |
|---|---|---|---|
| Q-EVAL-011 (v1) | qwen3.5-2b, gemma-4-e2b | gemma-4-e2b, qwen3-1.7b | ranks 4–5 only |
| Q2-EVAL-033 (v2) | qwen3.5-2b, gemma-4-e2b | all three | ranks 4–5 only |
| Q2-EVAL-071 (v2c1) | gemma-4-e2b | gemma-4-e2b | ranks 4–5 only |

All three cases are stopped by the gate in every run. The gate uses dense top-1, which is the same in all runs. No
LLM saw these contexts, and their judge labels are identical across all four systems (Q-EVAL-011 false refusal;
Q2-EVAL-033 and Q2-EVAL-071 correct refusal). The set of differing models changes between `llm2` and `llm2r` with the
same code and indexes, which points to run-to-run non-determinism in the tail of the hybrid fusion (for example tie
order). This was not investigated further. **The gate result is identical across all models and all runs.**

## 4. Discussion

### 4.1 Memory: the first measurement captured a server cache, not a model property

The 2–4× growth from stage 1 to `llm2` came from the server's default 8 GiB host prompt cache (§3.4). An 8 GiB cache
limit alone exceeds the 8 GB target machine's whole-app budget, so the default is a configuration error for this
deployment. A3 fixed the runtime to `--cache-ram 0`. Under that runtime all three models are under the A1 cap, with
gemma closest to it (2.94 of 3.5 GB). A3 was decided after the RAM data was seen and is post-hoc (deviation D5).

### 4.2 Language match: the detector, not the models, chose English

**The app picks the answer language with a detector.** At `a75c0fa` it labels a text as Vietnamese if it contains
any Vietnamese diacritic, and English otherwise (`application/common/language.py`). The prompt builder writes "answer
in {language}" into the prompt. The metric compares the answer with the question bank's language label.

**Eleven v2 questions are Vietnamese typed without diacritics**: answerable Q2-EVAL-001, -003, -006, -008, -012,
-016, -019, -022, -053; unanswerable Q2-EVAL-031, -033. For all eleven the detector returned English:
- **Seven** were stopped by the gate, and the fixed English refusal message was returned. Not LLM-written, not
  counted.
- **Four** reached the LLM: 001, 003, 008 and 022. All three local models followed the instruction and answered in
  English. Gemini answered 008 and 022 in Vietnamese, against the instruction, and 001 and 003 in English.

**Sensitivity check (post-hoc, not part of the rule).** With these four cases left out: qwen3.5-2b 72/72 = 100%,
gemma-4-e2b 72/72 = 100%, qwen3-1.7b 71/72 = 98.6% (Q-EVAL-026 remains), Gemini 72/72 = 100%.

**Gemma misses by one case:** 72/76 = 94.74%, where 73/76 = 96.05% would pass. The 95% Wilson interval for 72/76 is
87.2–97.9%, which contains the threshold.

**Other limits of the language metric:** diacritics are the only signal; mixed-language questions (Q-EVAL-026) have
no single correct answer language; the denominator is small (76, about 30 Vietnamese); and the metric checks the
language, not the quality, of the Vietnamese. Unaccented questions may also retrieve worse: the gate stopped 5 of 9
answerable unaccented questions against 16 of the other 85 (n = 9, a hypothesis only).

**Status of the fix.** The detector fix (PR #40, merged into `dev` as `f597c8f`) detects Vietnamese without
diacritics from common ASCII syllables. It changes the prompts for these questions, so it needs new runs, not a
re-score. By the owner's instruction these runs kept the pre-fix detector and the new detector is measured in a later
round.

### 4.3 Hallucination and grounding

**The threshold (≤ 1 of 14) is strict and the counts are tiny.** The 95% interval for 2/14 is 4.0–39.9%, and for 1/14
1.3–31.5%. Passing (gemma, 1) and failing (both Qwen, 2) differ by one case. The threshold is a pre-registered policy
line and is applied as written. All five hallucination verdicts were confirmed by the spot-check.

| Case | Question | Models judged hallucinating | What the answer did |
|---|---|---|---|
| Q-EVAL-033 | How to stop EF Core tracking the entities a read-only query returns | qwen3.5-2b, gemma-4-e2b | qwen3.5-2b named a `TrackingOptions.None` setting. Gemma answered with an unrelated claim about query execution and cited [1]. |
| Q-EVAL-035 | What scope validation checks in ASP.NET Core DI, and when it is enabled | qwen3.5-2b, qwen3-1.7b | Both gave generic descriptions. |
| Q2-EVAL-036 | How to draw a mind map when taking notes in a lecture | qwen3-1.7b | Generic advice. |

These are "plausible prior" questions: a general-purpose model knows a likely answer and the retrieved context does
not contain it, which is the case the grounding rule (CLAUDE.md §6) exists for. Gemini refused all 14. The local
models refuse less at the LLM step (both Qwen 0 of 73, Gemini 10): lower false refusal and higher hallucination are
probably one cause, a weaker abstention behaviour.

### 4.4 Citation markers

gemma-4-e2b 1.4%, qwen3-1.7b 9.2% (just under the line), qwen3.5-2b 10.5% (just over). For the Qwen models, missing
markers cluster on corpus-1 questions (v1: 17.2% and 20.7%). Some of them are answers that put the refusal sentinel
mid-text (§3.1 notes). Citations are a product requirement (CLAUDE.md §5).

### 4.5 The retrieval gate dominates refusals

The gate stopped 21 of 94 answerable questions (22.3%) for every system, a larger effect than any difference between
the models. Without A2 every model would fail false refusal on a retrieval cause. The gate is recalibrated after this
step (pre-registration §6).

## 5. Outcome under the pre-registered rule

Rule as pre-registered, with A1 caps, A2 false-refusal split and A3 runtime. Quality from the `llm2` runs judged by
`gemini-3.5-flash-lite` (A4 not applied, D7); RAM and TTFT from `llm2r`. No threshold was changed.

| Model | Failed thresholds | Passed |
|---|---|---|
| qwen3.5-2b | hallucination (2/14), missing marker (10.53%), language (94.74%) | accuracy, LLM false refusal, TTFT, RAM |
| gemma-4-e2b | language (94.74%) | accuracy, hallucination, LLM false refusal, markers, TTFT, RAM |
| qwen3-1.7b | hallucination (2/14), language (93.42%) | accuracy, LLM false refusal, markers, TTFT, RAM |

**No model passes every threshold. Under §5 no model is selected**, so there is no stage-3 Vietnamese grading sheet.
The owner chooses among the options in plan §6.3 (4B default, or cloud answering as a first-class opt-in). Gemini
stays the default.

**What could still change this** (analysis, not a decision):
- **gemma-4-e2b fails only on language, by one case, and the four mismatching cases trace to the pre-fix detector**
  (§4.2). The round with the fixed detector is the test of whether that failure is a model property. Any pick through
  it would rest on post-hoc changes (A3 and the detector fix) and must be reported as such.
- **The two Qwen models also fail on hallucination**, which the spot-check confirmed. The detector round does not
  change that.

## 6. Deviation log (owner, 2026-11-26: no data edited or dropped)

| # | Deviation | Effect |
|---|---|---|
| D1 | **Retrieval not identical to the reference on 3 cases** (Q-EVAL-011, Q2-EVAL-033, Q2-EVAL-071), ranks 4–5 only. `llm_run_summary.py` first exited 1 (stop); the owner then accepted them as known differences, and the script was extended to accept a listed case only if the gate fired in both runs. All six summaries exit 0. **This is therefore not a perfectly controlled experiment.** | None on any metric: gate-stopped in every run, no LLM saw them, identical labels (§3.6). |
| D2 | **Gate result identical across all models** and both run families (21 answerable + all gated unanswerable cases). | Confirms the gate costs every model the same. |
| D3 | **Extra v2c1 runs.** The owner's two commands (v1 on corpus 1, v2 on corpus 2) cover 94 cases; 14 v2 questions target corpus 1. v2c1 adds them to reach the plan's 108. | Adds cases, changes no setting. |
| D4 | **A2 timing.** A2 (false refusal split) was written after stage 2 started: committed `4959514` at 13:03:29Z on the PR #40 branch, not in the run code (`a75c0fa`); the first stage-2 run (`llm2-eval-v1-gemini`) started at 13:05:06Z. No eval-split data had been seen. | False-refusal threshold applies to LLM refusals only. |
| D5 | **A3 timing.** A3 (`--cache-ram 0`, re-measure RAM/TTFT) was written after stage 2 started and after the RAM data was seen: committed `a0fa7bd` at 14:20:02Z, after all `llm2` runs (last finished 14:12Z). Post-hoc. | RAM passes for all three (§3.4). |
| D6 | **11 unjudged cases** (judge marker error, §2.5). | Counted as not correct; no pass/fail would change if all were correct. |
| D7 | **A4 not applied; judge fell back to `gemini-3.5-flash-lite`.** A4 (committed `1a95ca1` at 15:01:50Z, after judging) required re-judging all runs with `gemini-3.8-flash` on `JUDGE_API_KEY`. The re-judge started 2026-11-27 ~08:25 (UTC+7) with the correct startup line (`key from JUDGE_API_KEY`, `gemini-3.8-flash`). In about 11 minutes it produced 2 ok verdicts and 3 errors, with 9 failed HTTP calls (503 UNAVAILABLE, 504 DEADLINE_EXCEEDED, no 429), on a 289-call job. The owner instructed at 08:36: "if 3.8 flash is too slow, fall back to original 3.5". The re-judge was stopped; the archived flash-lite verdicts were restored as `judgements.jsonl` in all 12 runs. The 5 partial 3.8-flash lines are kept unused as `llm2-eval-v1-gemini/judgements.3.8-flash-partial.jsonl`. | One judge in every table; no secondary table. The 11 judge marker errors (one of A4's reasons) remain. Written down afterwards as amendment A5 (owner, 2026-11-27): one judge fallback, `gemini-3.5-flash-lite`, chosen per table (plan §4, ADR-0004 amendment 2026-11-27, CLAUDE.md §6). |
| D8 | **`llm2r` from a detached worktree at `a75c0fa`**, so the pre-fix detector was used (sha256 evidence in §2.2). | Same detector as `llm2`; answers comparable. |
| D9 | **`--cache-idle-slots` disabled** by `--cache-ram 0` (server warning). | Part of the A3 runtime. |
| D10 | **CPU load before each server differed** (§2.6) between models and between `llm2` and `llm2r`. | Small TTFT confound; gemma was fastest in both. |
| D11 | **Spot-check graded by the agent, not by a human** (§2.5). | Blind sheet kept for the owner. |

## 7. Threats to validity and limitations

1. **Small denominators.** Unanswerable n = 14, answerable n = 94, language n ≈ 76 (about 30 Vietnamese). One case
   moves hallucination by 7.1 pp, language by 1.3 pp, accuracy by 1.1 pp.
2. **One judge model and one prompt**, from the same family as the baseline answer model. Self-preference would
   favour Gemini, which works against the local models.
3. **Single run, deterministic decoding.** One sample per case. Run-to-run CPU non-determinism is small but not zero:
   1 of 228 answers differed between `llm2` and `llm2r`.
4. **The machine is not the target.** Latency and memory are from a 20-thread i7 with 25 GB RAM and little memory
   pressure.
5. **The language metric is confounded by the app's pre-fix detector** (§4.2) and does not measure Vietnamese quality.
6. **Two settings were fixed, not tuned per model** (`answer_v3`, 512-token cap), as the protocol requires.
7. **Deviations D1–D11** (§6).

## 8. Conclusion

**Quality.** On 108 frozen questions, three ~2B quantised local models matched a small cloud model on lenient answer
accuracy, and none differed significantly from it. They refused less and, for the two Qwen models, hallucinated more
on unanswerable questions.

**Memory.** With the fixed runtime (`--cache-ram 0`), all three fit the 3.5 GB cap (2.0–2.9 GB). The first readings of
5–11 GB were the server's default 8 GiB prompt cache, not the models. The flag left 227 of 228 answers byte-identical
and did not slow generation.

**Rule outcome.** No model passes every threshold; **no model is selected**. gemma-4-e2b fails only on language, by one
case, on questions where the pre-fix detector told every model to answer in English. It is also the fastest (TTFT
median 5.5 s) and has the best citation compliance. The fixed-detector round is the next test.

## Appendix A. Provenance

| Item | Value |
|---|---|
| Branch / base | `eval/local-llm-stage2`, fast-forwarded to `origin/dev` `f7b8588` (PR #40 merged) for the report and summary script |
| Run code | `a75c0fa` for all 21 runs (`git_dirty = False`) |
| Quality run IDs | `llm2-eval-{v1,v2,v2c1}-{gemini, qwen3.5-2b-instruct-q4_k_m, gemma-4-e2b-it-q4_k_m, qwen3-1.7b-q4_k_m}` |
| Re-measure run IDs | `llm2r-eval-{v1,v2,v2c1}-{qwen3.5-2b-instruct-q4_k_m, gemma-4-e2b-it-q4_k_m, qwen3-1.7b-q4_k_m}` |
| Run windows (UTC+7) | `llm2`: Gemini 20:05–20:11; qwen3.5-2b 20:11–20:33; gemma-4-e2b 20:33–20:48; qwen3-1.7b 20:48–21:12 (2026-11-26). `llm2r`: qwen3.5-2b 07:29–07:49; gemma-4-e2b 07:49–08:03; qwen3-1.7b 08:03–08:25 (2026-11-27) |
| Committed | v1 folders only (owner): `llm2-eval-v1-*` (4) and `llm2r-eval-v1-*` (3). v2 folders are **never** committed (corpus-2 text, ADR-0008); v2c1 folders are kept local by the owner's instruction. |
| Judge files | `judgements.jsonl` = `gemini-3.5-flash-lite` in every `llm2` run; `llm2-eval-v1-gemini/judgements.3.8-flash-partial.jsonl` = 5 unused lines (D7) |

**Scratch scripts and raw data (not committed):**

| Location | Contents |
|---|---|
| `C:\Users\Wotbl\AppData\Local\Temp\claude\d03bb731c08d1fba\6ac764a7-04dd-4203-98ae-599ef6ea8cf5\scratchpad\` | `llm2` harness (`run_local.sh`, `llm_capture.py`, `ramwatch.ps1`), `out/<model>/ram.json`, `capture.jsonl`, `server.log`; cache diagnostic `cache_diag.py`, `out/diag-*.json` |
| `C:\Users\Wotbl\AppData\Local\Temp\claude\d03bb731c08d1fba\36459b74-d775-43aa-b8c3-5d22f06bdded\scratchpad\` | `llm2r` harness (same scripts, `--cache-ram 0`), `out-llm2r/<model>/{ram.json,capture.jsonl,server.log}`, `out-llm2r/summary-{llm2,llm2r}-{v1,v2,v2c1}.md`; `compare.py`/`compare.json` (answer comparison); `pool2.py`/`pool2.json` (pooled metrics); `spot.py`, `spot/blind.md` (blind sheet), `spot/reveal.md`; `judge/` (aborted 3.8-flash log) |
| `.claude/worktrees/llm2r-a75c0fa` | detached worktree at `a75c0fa` the `llm2r` runs ran from |

## Appendix B. Per-set summaries (`llm_run_summary.py`, `llm2r` for local models)

| Run | answered | LLM refused | gate | missing marker | lang match | TTFT median / p90 (ms) | gen median (ms) | same retrieval |
|---|---|---|---|---|---|---|---|---|
| v1 Gemini | 20 | 9 | 7 | 0.0% | 100.0% | n/a | 5,043 | ref. |
| v1 qwen3.5-2b | 29 | 0 | 7 | 17.2% | 100.0% | 8,032 / 10,566 | 14,669 | yes |
| v1 gemma-4-e2b | 24 | 5 | 7 | 0.0% | 100.0% | 4,383 / 5,558 | 10,283 | yes* (Q-EVAL-011) |
| v1 qwen3-1.7b | 29 | 0 | 7 | 20.7% | 96.6% | 7,247 / 9,836 | 16,533 | yes* (Q-EVAL-011) |
| v2 Gemini | 34 | 3 | 21 | 0.0% | 94.6% | n/a | 4,716 | ref. |
| v2 qwen3.5-2b | 37 | 0 | 21 | 5.4% | 89.2% | 12,774 / 14,968 | 16,338 | yes* (Q2-EVAL-033) |
| v2 gemma-4-e2b | 35 | 2 | 21 | 2.9% | 89.2% | 6,986 / 8,192 | 10,233 | yes* (Q2-EVAL-033) |
| v2 qwen3-1.7b | 37 | 0 | 21 | 0.0% | 89.2% | 13,748 / 16,468 | 17,715 | yes* (Q2-EVAL-033) |
| v2c1 Gemini | 9 | 1 | 4 | 0.0% | 100.0% | n/a | 3,542 | ref. |
| v2c1 qwen3.5-2b | 10 | 0 | 4 | 10.0% | 100.0% | 8,234 / 9,538 | 12,188 | yes |
| v2c1 gemma-4-e2b | 10 | 0 | 4 | 0.0% | 100.0% | 4,552 / 5,123 | 8,140 | yes* (Q2-EVAL-071) |
| v2c1 qwen3-1.7b | 10 | 0 | 4 | 10.0% | 100.0% | 7,478 / 9,218 | 10,850 | yes |

`yes*` = accepted known difference (gate fired in both runs). Counts of answered/refused/gate, markers and language
are identical in `llm2` and `llm2r`. The `llm2` TTFT values are in §3.3.
