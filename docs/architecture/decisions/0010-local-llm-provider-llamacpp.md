# ADR-0010 Local answer model: `LlamaCppLLM` over `llama-server`, plain-text answer format `answer_v3`

Date: 2026-11-26
Status: Accepted as infrastructure (owner approved the local LLM step and its pre-registration, 2026-11-26).
**Gemini stays the default** (`LLM_PROVIDER=gemini`) until a local model passes the go/no-go of
`docs/plans/local-llm-preregistration.md` and the owner accepts it. Refines: ADR-0006 (`LLM_PROVIDER=llamacpp` was
reserved), ADR-0004 (answer model). Plan: `docs/plans/local-rag-upgrade-plan.md` §6.

## Decision
- **D1 Runtime.** A pinned llama.cpp release's `llama-server` (CPU build; Vulkan build as a later configuration),
  called on its OpenAI-style `/v1/chat/completions`. No Ollama in the app. No new Python dependency: the adapter uses
  the standard library HTTP client. The server is started outside the app for now; the app starting and stopping it
  (job object / watchdog, idle unload) is a later plan step.
- **D2 Adapter.** `infrastructure/llm/llamacpp/LlamaCppLLM` behind `core/interfaces/llm.py`. Settings (`config.py`
  only): `LLAMACPP_URL`, `LOCAL_LLM_MODEL` (required, the pinned model id; the server is started with
  `--alias <id>`, one model per server), `LOCAL_LLM_CHAT_TEMPLATE_KWARGS` (default `{"enable_thinking": false}`),
  `LOCAL_LLM_SYSTEM_PROMPT` (optional), `LOCAL_LLM_MAX_OUTPUT_TOKENS` (512), `LOCAL_LLM_TIMEOUT_S` (600),
  `LOCAL_LLM_SEED` (42). No retries and no fallback. Errors: unreachable / timeout / 5xx -> `LLMUnavailableError`,
  other HTTP or unreadable reply -> `LLMRequestError`. A leading `<think>` block is removed. `LLMResponse` gains
  `time_to_first_token_ms` (the server's `timings.prompt_ms`), recorded per evaluation case.
- **D3 Answer format.** A prompt template whose first line is `<!-- answer_format: text -->` is plain text with `[n]`
  markers; a first line starting with `[[INSUFFICIENT]]` is the LLM refusal (second gate layer), the rest is the
  missing-information note. Degradation as plan §6.2: bad or out-of-range markers are dropped, no marker is shown
  without citations and counted, a late sentinel is text. `answer_v3` is that format; `answer_v2` (JSON) is unchanged.
  The same `answer_v3` runs on Gemini as the baseline.
- **D4 Evaluation.** `run_eval.py` builds the answer LLM with `create_llm` (`LLM_PROVIDER`); the run's
  `answer_model` is the active model id, so the model-purity check holds for local runs. The judge stays Gemini
  (ADR-0004 D12). `scripts/evaluation/llm_run_summary.py` reports missing-marker rate, language match, TTFT and checks
  that runs retrieved the same passages.

## Consequences
- Streaming, the GUI partial-answer state, server lifecycle and the model download (checksum, progress, manual path)
  are not built yet.
- Model licences are checked per file at download; NVIDIA Nemotron's licence is not Apache-2.0 (redistribution TBD).
