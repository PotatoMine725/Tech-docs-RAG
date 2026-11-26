# Local LLM step: candidates and pre-registered procedure

Status: **APPROVED by owner (2026-11-26)**: candidates, procedure, thresholds and download locations. Nothing below
has been run; no number in this file is a result. Plan reference: `local-rag-upgrade-plan.md` §6
(step 2 "Local LLM only", §6.2 output format, §6.3 go/no-go). Gate context: ADR-0009 D7 decision 4.

## 1. Candidates (screen 5, keep 2)

Facts from public pages read on 2026-11-26; the exact GGUF repo, file size, SHA-256 and licence file are verified
on the model card at download time and recorded in the report. Vietnamese quality is unknown for all of them and is
measured, not assumed.

| Class | Model | Licence | Why |
|---|---|---|---|
| Default (~2B) | Qwen3.5-2B Instruct, Q4_K_M | Apache-2.0 | Newest small Qwen; 200+ languages; text use only |
| Default (~2B) | Gemma 4 E2B Instruct, Q4_K_M | Apache-2.0 | 140+ languages; "effective 2B" (more weights on disk, RAM measured) |
| Default (~2B) | Qwen3-1.7B, Q4_K_M | Apache-2.0 | Plan's baseline (§3); text-only, smallest |
| Quality (~4B) | Qwen3.5-4B Instruct, Q4_K_M | Apache-2.0 | Opt-in "quality" profile |
| Quality (~4B) | Gemma 4 E4B Instruct, Q4_K_M | Apache-2.0 | Opt-in "quality" profile |

Out: NVIDIA-Nemotron-3-Nano-4B (added, then dropped by the owner 2026-11-26: card lists English only, non-Apache licence), Llama 3.2 (Vietnamese not listed as supported, custom licence), SmolLM3 / Granite (no Vietnamese), anything
above 4B (8 GB app budget), Vietnamese-only fine-tunes of older bases (licence varies; add only if all five fail
Vietnamese). Image input is out of scope here (OCR is TBD); multimodal projector files are not downloaded.

## 2. Fixed conditions (identical for every model)

- **Same retrieval for every model:** local embedder (EmbeddingGemma v1), hybrid, chunker A,
  `RERANK_PROVIDER=none`, current passage count. Query embeddings come from the on-disk cache and the indexes do not
  change between runs, so every run retrieves the same passages; `scripts/evaluation/llm_run_summary.py --reference`
  checks it per case (same chunk ids, same order) and fails otherwise. The LLM is the only variable (plan §4.2).
- **Prompt `answer_v3`** (new, versioned): fixed instructions first (prompt-cache friendly), plain text with `[n]`
  markers, refusal sentinel `[[INSUFFICIENT]]` on the first line, answer in the question's language, excerpts stay
  English. Gemini runs the same `answer_v3` as the baseline.
- **Runtime:** `llama-server` (pinned llama.cpp release, CPU build), temperature 0, fixed seed, context 4,096, one
  slot, threads = physical cores, thinking mode **off** (chat-template switch per model, recorded), answer cap
  512 tokens.
- **Low-end profile:** `-t 4`, `--ngl 0`. iGPU (Vulkan, `--ngl 99`) is a separate, later configuration.
- **Judge:** `gemini-3.5-flash-lite`, `judge_v1`, existing label table (`metrics/mapping.py`); manual spot-check of
  10% of verdicts (ADR-0004 D12).

## 3. Stages

1. **Smoke + speed (all 5):** dev-v1 + dev-v2 (12 questions) and `local_llm_bench.py` at 800 and 2,500 prompt
   tokens. Drop a model that crashes, exceeds the RAM cap (§4), or breaks the format on more than 3 of 12.
2. **Screen (survivors):** eval-v1 + eval-v2 (108 questions, 94 answerable / 14 unanswerable), one run each.
3. **Pick:** best in each class by the rule in §5; the owner grades a Vietnamese sample (20 answers) of the 2 picks.
4. **Real machine:** one speed/RAM run of the 2 picks on a real gen-10 / 8 GB machine (plan §5 item 4).

Gemini quota: the judge needs about 108 calls per model plus 216 for the Gemini baseline, so about 760 for stage 2;
spread over days if needed (free tier ~1,000/day).

## 4. Metrics and go/no-go (approved, owner 2026-11-26)

| Metric | Proposed threshold |
|---|---|
| Lenient accuracy (correct + partial, answerable) | ≥ Gemini `answer_v3` − 10 pp |
| Strict accuracy (correct only) | ≥ Gemini − 15 pp |
| Hallucination on unanswerable (14 cases) | ≤ 1 of 14 |
| False refusal on answerable, **by the LLM** (amended A2) | ≤ 10% of answerable cases that reached the LLM |
| Missing-marker rate | ≤ 10% (**decided**, owner 2026-11-10) |
| Answer language = question language | ≥ 95% |
| Vietnamese owner grade (20 answers, ok / not ok) | ≥ 16 ok |
| TTFT median, low-end profile, real passages | ≤ 15 s (2B class), ≤ 25 s (4B class) |
| Peak RAM of `llama-server` (working set) | ≤ 3.5 GB (2B), ≤ 5.0 GB (4B); whole app ≤ 8 GB (amended, see below) |

**Amendment A1 (owner, 2026-11-26, after stage 1; post-hoc).** Stage 1 (`docs/reports/2026-11-26-local-llm-stage1.md`)
put every model over the first caps (2.0 / 3.5 GB). Those caps came from the plan's estimate "LLM 1.2-1.5 GB", not
from the binding constraint, the 8 GB budget for the whole app. The metric stays the **working set** of
`llama-server` (it includes the memory-mapped GGUF weights, which must be resident to run; private bytes would
under-count them). New caps, derived from the 8 GB budget minus embedder (≤ 1 GB), index (~0.5 GB) and app/GUI/Chroma
(~1.5 GB, estimate): **2B ≤ 3.5 GB, 4B ≤ 5.0 GB**. Effect on stage 1: the three 2B models pass, both 4B models
(6.2-6.4 GB) are dropped. This change was made after seeing the data and is reported as such. The whole-app ≤ 8 GB
check on the real gen-10 / 8 GB machine (stage 4) is unchanged.

**Amendment A2 (owner, 2026-11-26, before stage 2; no eval-split data seen).** The retrieval gate (dense top-1 <
0.5417) refuses before any LLM call and is identical for every model: in stage 1 it stopped 3 of 9 answerable dev
questions in every run. Counting those against the LLM would fail every model for a retrieval cause. So false refusals
are reported two ways: **gate** (answerable, gate fired: a retrieval / gate-threshold result, reported, no LLM
threshold) and **LLM** (answerable, reached the LLM, LLM refused: the ≤ 10% threshold applies here, over answerable
cases that reached the LLM). Accuracy stays over all answerable cases and is compared with Gemini on the same
retrieval, so the gate costs every model the same. The gate itself is recalibrated after this step (§6).

## 5. Selection rule (fixed before the runs)

Among models passing every threshold in its class: highest lenient accuracy; within 3 pp, the lower TTFT median.
If no 2B model passes: options from plan §6.3 (4B default, or cloud answering as a first-class opt-in), owner
decides. Gemini stays the default until the owner accepts a local model on these numbers.

## 6. After the pick (not part of this pre-registration)

LLM refusal becomes the second gate layer. Then 15–20 new dev questions (owner-approved, frozen before use) to set a
system-level threshold: dense-score gate + LLM refusal, judged together.

## 7. Downloads (location approved, owner 2026-11-26)

Approved: models in `E:\models\llm\<model>\`, llama.cpp binaries in `E:\models\llama.cpp\<release>-cpu\`.
Total download about 10–12 GB for five Q4 files (estimate; recorded per file at download).
