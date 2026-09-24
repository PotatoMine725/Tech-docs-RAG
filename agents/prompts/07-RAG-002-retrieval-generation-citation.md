# RAG-002 — Retrieval, grounded generation, citations, "insufficient information"

Read `agents/prompts/_common.md` first and follow it.
Read: `generation-spec.md`, `citation-spec.md`, `retrieval-spec.md`, ADR-0003 D5/D9, ADR-0004, ADR-0005, RAG-001b report, `core/interfaces/llm.py`, `infrastructure/llm/gemini/__init__.py`.
Entry: RAG-001b done (both collections indexed).
Scope note: this task builds a **basic** Gemini LLM adapter (one model, no retry). Retry/backoff/fallback is RAG-003.

## 1. Core contracts (impact-check `LLM` and `Citation` first)
```python
# core/interfaces/llm.py
@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    response_schema: dict | None = None   # JSON schema; None = free text
    temperature: float = 0.0
    max_output_tokens: int = 1024

@dataclass(frozen=True)
class LLMResponse:
    text: str
    model_used: str
    retry_count: int
    fallback_used: bool
    prompt_tokens: int | None
    output_tokens: int | None
    latency_ms: float

class LLM(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...

# core/models (new)
@dataclass(frozen=True)
class AnswerResult:
    question: str
    language: str                      # "en" | "vi"
    answer: str                        # final text shown to the user (localized message if insufficient)
    insufficient: bool
    insufficient_reason: str | None    # "retrieval_gate" | "llm" | None
    citations: tuple[Citation, ...]    # ordered by first marker in the answer
    retrieved: tuple[RetrievedChunk, ...]
    dropped_markers: tuple[int, ...]   # [n] markers that pointed outside 1..k
    uncited_sentences: int             # diagnostic: factual sentences without any marker
    latency_ms: dict[str, float]       # embed_query, retrieve, generate, total
    llm: LLMResponse | None            # None when the retrieval gate fired
    prompt_version: str
```
`Citation` keeps its fields; add `chunk_id: str`, `marker: int`, `source_url: str`. `location_type="heading"`, `location` = heading path.
New core exceptions: `GenerationError` (LLM output unusable), `RetrievalError`.

## 2. Decisions to confirm with the user (then write into the specs)
**OD-10 prompt** — propose this template as `config/prompts/answer_v1.md` (versioned file; version string = file name). Show it to the user; apply edits; never inline prompts in code.
```
You are a documentation assistant for a fixed collection of technical documents.
Answer the QUESTION using ONLY the numbered CONTEXT passages.

Rules:
1. Use only facts stated in the CONTEXT. Do not use prior knowledge, even if you know the answer.
2. If the CONTEXT does not contain the information needed, set "insufficient": true and leave "answer" empty.
   If it contains only part of it, answer that part and say in "missing_information" what is not covered.
3. End every sentence that states a fact with citation markers such as [1] or [2][3] (passage numbers).
4. Write "answer" in {answer_language}. Keep code, identifiers, API and keyword names exactly as in the CONTEXT.
5. If passages describe different versions of the same feature, say which version each statement applies to; do not merge them.
6. Be concise (about 200 words max) unless a short code example from the CONTEXT is needed.

CONTEXT:
{passages}          # each: "[n] {document_name} — {heading_path}\n{chunk body, links stripped}"

QUESTION: {question}
```
Response schema: `{"insufficient": bool, "answer": string, "cited_passages": [int], "missing_information": string}` (all required).

**OD-9 insufficient-information rule** — two layers:
- (a) *retrieval gate*: if the top-1 score < `INSUFFICIENT_SCORE_THRESHOLD` → skip the LLM, `insufficient_reason="retrieval_gate"`.
- (b) *LLM layer*: `"insufficient": true` → `insufficient_reason="llm"`.
- Localized messages in `config/messages.json`:
  EN `"The document collection does not contain enough information to answer this question."`
  VI `"Bộ tài liệu hiện có không chứa đủ thông tin để trả lời câu hỏi này."`
- **Threshold tuning — dev set only** (`dev-v1.jsonl`, never the eval set), Arm A, one value used for both arms:
  run retrieval for every dev case → table of (case, answerable?, top-1 score). Rule: threshold = (lowest top-1 score among answerable dev cases) − 0.05, i.e. the gate must never refuse an answerable dev question; the LLM layer handles the rest. If answerable and unanswerable scores overlap completely, set threshold = 0 (gate off) and say so. Record the table, the rule and the value in `retrieval-spec.md` — with the honest caveat that n is small.

## 3. Do
1. `application/common/language.py`: `detect_language(text) -> "vi" | "en"` — "vi" if the text contains Vietnamese-specific letters (ă â đ ê ô ơ ư or Vietnamese tone-marked vowels), else "en". Deterministic, tested on 10+ examples incl. VI without diacritics (documented limitation → "en").
2. `application/retrieval/retrieve.py` — `Retriever(embedder, store, top_k)`: embed query with `EmbeddingTask.QUERY` (cached) → `store.search` → `list[RetrievedChunk]`; time both stages.
3. `application/generation/prompt_builder.py`: load template by version, render passages (numbered 1..k in rank order), answer language name, question. Pure function, tested with snapshot strings.
4. `application/generation/answer_question.py` — `AnswerQuestion(retriever, llm, prompt_builder, messages, threshold)` → `AnswerResult`:
   - gate → LLM with `response_schema` → parse JSON; parse failure → raise `GenerationError` with the raw text (never silently turn it into "insufficient");
   - markers: extract `[n]` from `answer`; keep n in 1..k, drop others (remove from text, record in `dropped_markers`); union with `cited_passages`;
   - build `Citation`s from the cited `RetrievedChunk`s: excerpt = first 300 chars of the chunk body (English, cut at a word boundary);
   - `uncited_sentences`: split answer into sentences, count those with ≥ 5 words and no marker;
   - `insufficient=true` → `answer` = localized message; citations empty.
5. `application/citation/` holds marker parsing + citation building (pure functions).
6. `infrastructure/llm/gemini/gemini_llm.py`: basic adapter implementing the new `LLM` (model from config `ANSWER_MODEL`, JSON mode with the schema via the installed `google-genai` API — inspect it, don't guess), fills token counts from usage metadata, measures latency. No retry yet (`retry_count=0`).
7. Tests (offline, `FakeEmbedder` + in-memory store + `FakeLLM` returning scripted JSON):
   - prompt contains only the retrieved passages, in rank order, with heading paths;
   - gate fires below threshold (LLM not called), not above;
   - `[7]` with k=5 → dropped and recorded; `[2]` → citation for rank 2 with correct heading path/excerpt;
   - VI question → VI message when insufficient; EN → EN;
   - invalid JSON → `GenerationError`;
   - presentation/infra imports still forbidden in application (structure test green).
8. Live (small, `@pytest.mark.gemini` or a script): the threshold-tuning run on the dev set (embeddings only) + 2 dev questions end-to-end to verify JSON mode works. Save outputs to `validation/generation/rag-002-dev-<date>.md`.

## Acceptance
Offline pytest green; `retrieval-spec.md`, `generation-spec.md`, `citation-spec.md` no longer say "TBD" for threshold, prompt, citation format; prompt file exists and is referenced by version; no eval-set question was used anywhere in this task (`grep` the eval IDs in validation/ and logs → 0).
