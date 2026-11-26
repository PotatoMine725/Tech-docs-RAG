# Local LLM stage 1: smoke + speed, 12 dev questions (plan `local-llm-preregistration.md` §3 stage 1, ADR-0010)

Date: 2026-11-26 (runs 16:15–17:10 +07:00). Status: **stage 1 run once, as pre-registered; nothing decided here.**
Stage 2 (eval split) was not started. Every number below comes from a file listed in §6; anything not measured is
n/a. Run code: `dev` at `679f689` (PR #37 merged); every run's `run.json` has `git_dirty: false`.

## 1. What ran

- **Models (5):** the five Apache-2.0 candidates of plan §1. **Nemotron 3 Nano 4B is excluded by the owner**
  ("5 model thôi, loại nemotron", 2026-11-26 16:11), so it was neither downloaded nor run.
- **Runtime:** llama.cpp **v1.0.0** (latest stable release, 2026-11-13). That release has no binaries; its
  `nightly-tag.txt` points to build **b12359**, so the binary is `llama-b12359-bin-win-cpu-x64.zip`
  (SHA-256 `837c1655e87df3b66989f4be33a792a1399c785bf259038dc75c900096683e69`, matches GitHub's digest;
  `llama-server --version`: `1.0.0-dev (build 12359, commit b1b770d90)`), unzipped to `E:\models\llama.cpp\v1.0.0-cpu\`.
- **Server, per model:** `llama-server.exe -m <gguf> --alias <model-id> -c 4096 -t 4 -ngl 0 --parallel 1 --jinja
  --seed 42 --port 8080`. One server per model for both runs, stopped before the bench.
- **Env:** `LLM_PROVIDER=llamacpp`, `LOCAL_LLM_MODEL=<model-id>`, `ANSWER_PROMPT_VERSION=answer_v3`,
  `EMBEDDING_PROVIDER=embeddinggemma` (v1 fp32 @768, from `.env`), `RETRIEVAL_MODE=hybrid`, `RERANK_PROVIDER=none`,
  `LOCAL_LLM_CHAT_TEMPLATE_KWARGS` default `{"enable_thinking": false}` (the captured requests carry it). Gemini
  baseline: same with `LLM_PROVIDER=gemini` (`gemini-3.5-flash-lite`, fallback off).
- **Runs:** `run_eval.py --arm A --mode full --split dev` with `--questions v1 --corpus corpus1` and `--questions v2
  --corpus corpus2`, run ids `llm1-dev-{v1,v2}-<model-id>`; then `judge_run.py` on all 12 runs (Gemini judge, `judge_v1`);
  then `llm_run_summary.py` per question set with the Gemini run as `--reference`; then `local_llm_bench.py`
  (`--dry-run` first) per model with the server stopped.
- **Same retrieval everywhere:** `llm_run_summary.py --reference` reports `same_retrieval: yes` for every run in both
  sets (exit code 0 for v1 and for v2). The LLM is the only variable.

**Only 7 of the 12 cases reach the LLM.** The retrieval gate (dense top-1 < 0.5417) stops Q-DEV-006 and
Q2-DEV-002/003/005/006 in every run, identically. Three of those (Q2-DEV-002/003/005) are answerable, so every model,
Gemini included, has 3 gate false refusals it had no part in. Per-model differences come from Q-DEV-001…005,
Q2-DEV-001 and Q2-DEV-004.

## 2. Results per model

Format breaks = `GenerationError` records + answered cases with no valid `[n]` marker, out of 12 (gate-stopped
cases stay in the denominator). TTFT = the server's `timings.prompt_ms` over the 7 LLM calls of v1 + v2 pooled (same
percentile rule as `llm_run_summary.py`); Gemini reports none. Peak RAM = the highest `PeakWorkingSet64` of
`llama-server.exe` sampled once per second over both runs, read before the server was stopped. MB = 10^6 bytes.

| Model (class) | Crash | Peak RAM, working set (cap) | TTFT median / p90 (ms) | GenerationError | No valid marker | Format breaks /12 | Language mismatch | Bench tok/s, llama-bench pp800 / pp2500 / tg200 |
|---|---|---|---|---|---|---|---|---|
| qwen3.5-2b-instruct-q4_k_m (2B) | no | **2,556 MB** (2,000) | 10,471 / 11,751 | 0 | 1 (Q-DEV-002) | 1 | 0 / 7 | 189.7 / 178.3 / 20.9 |
| gemma-4-e2b-it-q4_k_m (2B) | no | **3,066 MB** (2,000) | 5,543 / 6,667 | 0 | 0 | 0 | 0 / 7 | 379.3 / 347.9 / 19.0 |
| qwen3-1.7b-q4_k_m (2B) | no | **2,927 MB** (2,000) | 11,316 / 12,756 | 0 | 3 (Q-DEV-002, -003, -005) | 3 | 0 / 7 | 183.9 / 156.5 / 24.2 |
| qwen3.5-4b-instruct-q4_k_m (4B) | no | **6,383 MB** (3,500) | 34,336 / 38,489 | 0 | 0 | 0 | 0 / 7 | 54.7 / 51.4 / 8.6 |
| gemma-4-e4b-it-q4_k_m (4B) | no | **6,240 MB** (3,500) | 18,926 / 22,939 | 0 | 0 | 0 | 0 / 7 | 106.8 / 102.7 / 8.9 |
| Gemini `gemini-3.5-flash-lite` (baseline) | n/a | n/a | n/a | 0 | 0 | 0 | 0 / 7 | n/a |

Judge labels (12 cases each: 9 answerable, 3 unanswerable):

| Model | correct | partially_correct | incorrect | false_refusal | correct_refusal | hallucination |
|---|---|---|---|---|---|---|
| qwen3.5-2b-instruct-q4_k_m | 4 | 1 (Q-DEV-002) | 1 (Q-DEV-001) | 3 (gate) | 2 | **1 (Q-DEV-005)** |
| gemma-4-e2b-it-q4_k_m | 6 | 0 | 0 | 3 (gate) | 3 | 0 |
| qwen3-1.7b-q4_k_m | 5 | 0 | 1 (Q-DEV-001) | 3 (gate) | 3 | 0 |
| qwen3.5-4b-instruct-q4_k_m | 6 | 0 | 0 | 3 (gate) | 3 | 0 |
| gemma-4-e4b-it-q4_k_m | 6 | 0 | 0 | 3 (gate) | 3 | 0 |
| Gemini (answer_v3) | 4 | 0 | 0 | 5 (3 gate + Q-DEV-002, Q-DEV-004 by the LLM) | 3 | 0 |

12 cases is a smoke test, not an accuracy estimate: one case is 8 pp. Gemini's two LLM refusals are the two
Vietnamese C# questions (Q-DEV-002, Q-DEV-004); all five local models answered both.

Other memory and speed readings, kept separate from the drop-rule number:

| Model | File size (bytes) | Private bytes, peak (MB) | System memory in use, peak (GB, whole machine) | Bench server peak (MB) | Bench server TTFT 800 / 2500 tok (s) | Bench server gen tok/s 800 / 2500 |
|---|---|---|---|---|---|---|
| qwen3.5-2b-instruct-q4_k_m | 1,280,835,840 | 1,520 | 13.77 | 2,522 | 4.3 / 14.0 | 19.6 / 18.8 |
| gemma-4-e2b-it-q4_k_m | 3,106,738,272 | 1,684 | 14.41 | 3,027 | 2.1 / 7.0 | 15.4 / 14.6 |
| qwen3-1.7b-q4_k_m | 1,282,439,264 | 2,545 | 13.99 | 3,462 | 4.4 / 15.9 | 20.1 / 14.2 |
| qwen3.5-4b-instruct-q4_k_m | 3,032,091,584 | 3,739 | 16.92 | 6,342 | 14.3 / 45.6 | 7.9 / 7.3 |
| gemma-4-e4b-it-q4_k_m | 4,977,171,584 | 3,372 | 18.28 | 6,179 | 7.5 / 24.0 | 7.7 / 7.4 |

"System memory in use" is the whole 23.6 GB machine with the desktop and other programs open. It is not the app's
share, and no idle baseline was taken, so the app-level "≤ 8 GB" line is n/a here.

**Thinking check:** a pass-through wrapper (§5) logged every raw `/v1/chat/completions` reply. Across all 35 local
calls: no `<think>` in `message.content`, `message.reasoning_content` empty, `finish_reason: stop` every time, no reply
at the 512-token cap (longest: 366 tokens, Qwen3.5-4B). `enable_thinking: false` held for all five, Gemma 4 included.

## 3. Stage-1 drop rule (plan §3: crash, RAM over the §4 cap, > 3/12 format breaks)

| Model | Crash | RAM (peak working set) over cap | Format breaks > 3/12 | Rule outcome |
|---|---|---|---|---|
| qwen3.5-2b-instruct-q4_k_m | no | **yes** (2,556 > 2,000) | no (1) | drop |
| gemma-4-e2b-it-q4_k_m | no | **yes** (3,066 > 2,000) | no (0) | drop |
| qwen3-1.7b-q4_k_m | no | **yes** (2,927 > 2,000) | no (3, at the limit) | drop |
| qwen3.5-4b-instruct-q4_k_m | no | **yes** (6,383 > 3,500) | no (0) | drop |
| gemma-4-e4b-it-q4_k_m | no | **yes** (6,240 > 3,500) | no (0) | drop |

**Models that go to stage 2 under the rule as written, with peak working set as the RAM measure: none.** No model
crashed or broke the format more than 3 times. Every model fails on RAM alone.

**The RAM measure decides the outcome, so the owner must decide it before stage 2.** The plan says "peak RAM of
`llama-server`" and the stage-1 prompt says "peak working set", and that is what the rule table uses. But the
working set also counts pages of the memory-mapped GGUF file, which the OS can drop and re-read. Gemma 4 E2B's peak
working set (3,066 MB) is about the size of its file (3,107 MB), yet its private bytes are 1,684 MB. Measured by
**private bytes** (memory only this process holds), three models are under their caps:
- qwen3.5-2b-instruct-q4_k_m: 1,520 MB, cap 2,000
- gemma-4-e2b-it-q4_k_m: 1,684 MB, cap 2,000
- gemma-4-e4b-it-q4_k_m: 3,372 MB, cap 3,500

The other two are over:
- qwen3-1.7b-q4_k_m: 2,545 MB, cap 2,000
- qwen3.5-4b-instruct-q4_k_m: 3,739 MB, cap 3,500

This reading is shown for the decision only. It was not pre-registered and it is not applied above. On this 23.6 GB
machine nothing was under memory pressure, so neither number shows how a model behaves when 8 GB is tight. The
real-machine run (plan stage 4) is the one that measures that.

Other stage-1 observations, all from the tables above:
- The 2B-class TTFT medians are under the 15 s line (5.5–11.3 s).
- Gemma 4 E4B (18.9 s) is under the 25 s line for the 4B class. Qwen3.5-4B (34.3 s) is over it.
- TTFT is a stage-2 metric, not a stage-1 drop criterion.

## 4. Judge spot-check (10%)

40 ok judge verdicts across the 12 runs. A seeded draw (`random.Random(42)`, 4 = 10%) picked:
- v1-gemini Q-DEV-003
- v1-qwen3.5-2b Q-DEV-003
- v1-gemma-4-e2b Q-DEV-004
- v2-gemma-4-e2b Q2-DEV-001

**Graded by the agent (Claude), not by the owner**, against the ground truth and the cited chunk text. The result:
**4/4 labels agree** with the judge (all `correct`). The v2 Gemma E2B case is the only one with a citation detail.
The judge marked its citation `[1]` as not supporting the claim. The cited chunk (`C2-16:header-1600:0000`, title
slide + objectives) does not list the causes, so the judge is right there too. The answer is still correct on content.
The owner has not graded this sample. The judge is the same model as the Gemini answer model, the same limitation as
ADR-0004 D12.

## 5. Deviations and provenance (read before using any number)

- **Machine:** i7-12700H, 14 cores (6P + 8E) / 20 threads, 23.6 GB RAM, Windows 11. This is not the gen-10 / 8 GB
  target. `-t 4` was not pinned to particular cores, so the OS may place threads on P- or E-cores. Speed numbers are
  relative across models, not target-machine values.
- **Download sources:**
  - The official repos have no Q4_K_M file. `Qwen/Qwen3-1.7B-GGUF` has none, and Google publishes only
    `*-qat-q4_0-gguf`.
  - So the plan's order was followed: `ggml-org` where it has Q4_K_M (Qwen3-1.7B, Qwen3.5-4B), else `unsloth`
    (Qwen3.5-2B, Gemma 4 E2B, Gemma 4 E4B).
  - The quantizers are therefore mixed.
  - The Qwen3.5 base repos are `Qwen/Qwen3.5-2B` / `Qwen/Qwen3.5-4B`. They have no separate "-Instruct" repo, and
    the `-instruct` in the model id is the plan's naming.
- **Licences:** Apache-2.0 on both the GGUF repo and the base model card for all five (HF card metadata, recorded in
  the manifest). SHA-256 of every file matches the Hub's LFS hash.
- **Corpus-2 chunk file:**
  - The worktree has no corpus-2 chunk file, because it is git-ignored. The main checkout doesn't have one either.
  - The v2 runs used `CHUNKS_DIR` → `.claude/worktrees/corpus2-index/data/processed/chunks`, which resolves to
    `chunks-corpus2/arm-a.jsonl`.
  - Before use, it was checked: 1,045 header-1600 chunk ids, the exact id set of `data/keyword-corpus2/kw_header-1600.sqlite`.
  - `CHROMA_PATH`, `KEYWORD_INDEX_DIR` and `EMBEDDING_CACHE_PATH` pointed to the main checkout's data. Every query
    embedding was a cache hit (0 embedding requests in every run).
- **Raw-reply capture:** every run_eval invocation went through a scratch wrapper. It replaces
  `urllib.request.urlopen`, passes request and reply bytes through unchanged, and appends them to a JSONL file. It
  then runs `scripts/evaluation/run_eval.py` with `runpy`, with the same arguments as the commands in §1. No tracked
  file was changed. The wrapper is the only source of the thinking check in §2.
- **Bench, `mmap=off`:** the bench's `--no-mmap` configuration failed to start on every model. llama.cpp v1.0.0
  rejects the flag (`error: invalid argument: --no-mmap`; it now has a load-mode option instead). Only the
  `mmap=on` rows exist. The bench script was not changed.
- **Order and load:**
  - The Gemini baseline ran (16:15–16:17) while the model downloads were still running (network only). No local
    model had started yet.
  - Judging of a finished model overlapped the next model's runs. This is network only; the local runs make no
    Gemini call.
  - The bench ran with no server and no eval running.
- **Judge retry:** v2 Gemma E4B Q2-DEV-004 got HTTP 503 ×3 (`judge_error`), and a second `judge_run.py` judged it ok.
  All 12 runs now have every needed verdict (exit 0).
- **What is committed:**
  - Committed: the v1 run folders (corpus 1 is in the repo) and `data/experiments/local-llm-bench/`.
  - Not committed: the v2 run folders. They hold retrieved text of non-redistributable corpus-2 documents
    (ADR-0008; `C2-16` is `redistributable: false`). Their ids `llm1-dev-v2-*` don't match the `.gitignore` pattern
    `*-corpus2-*`, so they are kept local by not staging them. They stay at
    `data/evaluation/results/llm1-dev-v2-*` in the `eval/local-llm-stage1` worktree.

## 6. Evidence

- Runs: `data/evaluation/results/llm1-dev-v1-{gemini,qwen3.5-2b-instruct-q4_k_m,gemma-4-e2b-it-q4_k_m,
  qwen3-1.7b-q4_k_m,qwen3.5-4b-instruct-q4_k_m,gemma-4-e4b-it-q4_k_m}/` (`run.json`, `records.jsonl`,
  `judgements.jsonl`); v2 equivalents local only (§5).
- Bench: `data/experiments/local-llm-bench/stage1-<model-id>.json` + server logs.
- Model manifest (`E:\models\llm\manifest.json`, copied here):

| Model id | HF repo @ revision | File | Size (bytes) | SHA-256 | Licence |
|---|---|---|---|---|---|
| qwen3.5-2b-instruct-q4_k_m | unsloth/Qwen3.5-2B-GGUF @ f6d5376be1edb4d416d56da11e5397a961aca8ae | Qwen3.5-2B-Q4_K_M.gguf | 1,280,835,840 | aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223 | apache-2.0 |
| gemma-4-e2b-it-q4_k_m | unsloth/gemma-4-E2B-it-GGUF @ 0314792d7f1f7e229411f620751375812bb9faf2 | gemma-4-E2B-it-Q4_K_M.gguf | 3,106,738,272 | 740185b21d22ceb83a11c3aa62ad5842ef32c70f6096d756bbee85a1e4ec34b8 | apache-2.0 |
| qwen3-1.7b-q4_k_m | ggml-org/Qwen3-1.7B-GGUF @ daeb8e2d528a760970442092f6bf1e55c3b659eb | Qwen3-1.7B-Q4_K_M.gguf | 1,282,439,264 | d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5 | apache-2.0 |
| qwen3.5-4b-instruct-q4_k_m | ggml-org/Qwen3.5-4B-GGUF @ 8d43d974efc48399cb58957ad49c8b26bf5a109c | Qwen3.5-4B-Q4_K_M.gguf | 3,032,091,584 | 217002fa8008ef4fc6d548353a3aebef055a96e6ff8e0e2c0953ef8254a89c14 | apache-2.0 |
| gemma-4-e4b-it-q4_k_m | unsloth/gemma-4-E4B-it-GGUF @ bfc15c382204943c3a8fff0c750b94ae2364d7a3 | gemma-4-E4B-it-Q4_K_M.gguf | 4,977,171,584 | 85a896a047553e842f25297ee5b031d64ff30147d9c4af17b1e4b394cd1fab87 | apache-2.0 |

- `llm_run_summary.py` output, verbatim:

v1 (`--reference llm1-dev-v1-gemini`, exit 0):

| run | model | prompt | ok | errors | answered | llm_refused | gate | missing_marker | lang_match | ttft median ms | ttft p90 ms | gen median ms | same_retrieval |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llm1-dev-v1-gemini | gemini-3.5-flash-lite | answer_v3 | 6 | 0 | 2 | 3 | 1 | 0.0% | 100.0% | n/a | n/a | 2,350 | yes |
| llm1-dev-v1-qwen3.5-2b-instruct-q4_k_m | qwen3.5-2b-instruct-q4_k_m | answer_v3 | 6 | 0 | 5 | 0 | 1 | 20.0% | 100.0% | 7,706 | 12,670 | 17,195 | yes |
| llm1-dev-v1-gemma-4-e2b-it-q4_k_m | gemma-4-e2b-it-q4_k_m | answer_v3 | 6 | 0 | 4 | 1 | 1 | 0.0% | 100.0% | 4,081 | 6,913 | 10,826 | yes |
| llm1-dev-v1-qwen3-1.7b-q4_k_m | qwen3-1.7b-q4_k_m | answer_v3 | 6 | 0 | 5 | 0 | 1 | 60.0% | 100.0% | 7,243 | 12,756 | 16,185 | yes |
| llm1-dev-v1-qwen3.5-4b-instruct-q4_k_m | qwen3.5-4b-instruct-q4_k_m | answer_v3 | 6 | 0 | 5 | 0 | 1 | 0.0% | 100.0% | 24,582 | 40,343 | 53,340 | yes |
| llm1-dev-v1-gemma-4-e4b-it-q4_k_m | gemma-4-e4b-it-q4_k_m | answer_v3 | 6 | 0 | 4 | 1 | 1 | 0.0% | 100.0% | 13,863 | 22,939 | 26,884 | yes |

- llm1-dev-v1-qwen3.5-2b-instruct-q4_k_m: no valid marker in Q-DEV-002
- llm1-dev-v1-qwen3-1.7b-q4_k_m: no valid marker in Q-DEV-002, Q-DEV-003, Q-DEV-005

v2 (`--reference llm1-dev-v2-gemini`, exit 0):

| run | model | prompt | ok | errors | answered | llm_refused | gate | missing_marker | lang_match | ttft median ms | ttft p90 ms | gen median ms | same_retrieval |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llm1-dev-v2-gemini | gemini-3.5-flash-lite | answer_v3 | 6 | 0 | 2 | 0 | 4 | 0.0% | 100.0% | n/a | n/a | 13,869 | yes |
| llm1-dev-v2-qwen3.5-2b-instruct-q4_k_m | qwen3.5-2b-instruct-q4_k_m | answer_v3 | 6 | 0 | 2 | 0 | 4 | 0.0% | 100.0% | 11,302 | 11,751 | 17,353 | yes |
| llm1-dev-v2-gemma-4-e2b-it-q4_k_m | gemma-4-e2b-it-q4_k_m | answer_v3 | 6 | 0 | 2 | 0 | 4 | 0.0% | 100.0% | 6,413 | 6,667 | 10,126 | yes |
| llm1-dev-v2-qwen3-1.7b-q4_k_m | qwen3-1.7b-q4_k_m | answer_v3 | 6 | 0 | 2 | 0 | 4 | 0.0% | 100.0% | 12,838 | 13,738 | 17,228 | yes |
| llm1-dev-v2-qwen3.5-4b-instruct-q4_k_m | qwen3.5-4b-instruct-q4_k_m | answer_v3 | 6 | 0 | 2 | 0 | 4 | 0.0% | 100.0% | 36,668 | 38,489 | 55,662 | yes |
| llm1-dev-v2-gemma-4-e4b-it-q4_k_m | gemma-4-e4b-it-q4_k_m | answer_v3 | 6 | 0 | 2 | 0 | 4 | 0.0% | 100.0% | 22,748 | 25,186 | 32,141 | yes |

## 7. Owner decisions needed (not taken here)

1. **RAM measure for the cap:** the peak working set (as written: no model goes to stage 2) or the private bytes
   (would pass qwen3.5-2b, gemma-4-e2b, gemma-4-e4b), or something else, e.g. re-measure under an 8 GB limit.
2. If the answer is "as written", the options of plan §5/§6.3 apply: a 4B default, cloud answering as a first-class
   opt-in, or new candidates.
3. Whether the owner wants to grade the 4-item spot-check themselves.
