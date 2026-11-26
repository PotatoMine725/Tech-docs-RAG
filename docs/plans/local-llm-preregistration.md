# Local LLM step: candidates and pre-registered procedure

Status: **PROPOSED, awaiting owner approval (2026-11-26).** Nothing below has been run. No number in this file is
a result; thresholds are proposals until the owner approves them. Plan reference: `local-rag-upgrade-plan.md` §6
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

Out: Llama 3.2 (Vietnamese not listed as supported, custom licence), SmolLM3 / Granite (no Vietnamese), anything
above 4B (8 GB app budget), Vietnamese-only fine-tunes of older bases (licence varies; add only if all five fail
Vietnamese). Image input is out of scope here (OCR is TBD); multimodal projector files are not downloaded.

## 2. Fixed conditions (identical for every model)

- **Retrieval frozen once:** local embedder (EmbeddingGemma v1), hybrid, chunker A, `RERANK_PROVIDER=none`, current
  passage count. Retrieved contexts are saved to one JSONL and every LLM, Gemini included, reads that file. So the
  LLM is the only variable (plan §4.2).
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

## 4. Metrics and proposed go/no-go (DECISION REQUIRED, owner)

| Metric | Proposed threshold |
|---|---|
| Lenient accuracy (correct + partial, answerable) | ≥ Gemini `answer_v3` − 10 pp |
| Strict accuracy (correct only) | ≥ Gemini − 15 pp |
| Hallucination on unanswerable (14 cases) | ≤ 1 of 14 |
| False refusal on answerable | ≤ 10% |
| Missing-marker rate | ≤ 10% (**decided**, owner 2026-11-10) |
| Answer language = question language | ≥ 95% |
| Vietnamese owner grade (20 answers, ok / not ok) | ≥ 16 ok |
| TTFT median, low-end profile, real passages | ≤ 15 s (2B class), ≤ 25 s (4B class) |
| Peak RAM of `llama-server` | ≤ 2.0 GB (2B), ≤ 3.5 GB (4B); whole app ≤ 8 GB |

## 5. Selection rule (fixed before the runs)

Among models passing every threshold in its class: highest lenient accuracy; within 3 pp, the lower TTFT median.
If no 2B model passes: options from plan §6.3 (4B default, or cloud answering as a first-class opt-in), owner
decides. Gemini stays the default until the owner accepts a local model on these numbers.

## 6. After the pick (not part of this pre-registration)

LLM refusal becomes the second gate layer. Then 15–20 new dev questions (owner-approved, frozen before use) to set a
system-level threshold: dense-score gate + LLM refusal, judged together.

## 7. Downloads (RULE: owner confirms the location first)

Proposed: models in `E:\models\llm\<model>\`, llama.cpp binaries in `E:\models\llama.cpp\<release>-cpu\`.
Total download about 10–12 GB for five Q4 files (estimate; recorded per file at download).
