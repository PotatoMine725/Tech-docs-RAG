# Generation specification

Status: decided for RAG-002 (2026-09-26). Code: `application/generation/`, `infrastructure/llm/gemini/gemini_llm.py`.

## Known facts
- Questions may be in English or Vietnamese; the corpus is English (ADR-0003 D9).

## Requirements
- The answer MUST be in the question's language.
- The "insufficient information" message MUST be in the question's language.
- Answer model `gemini-3.5-flash-lite`; on repeated 503/429, retry with backoff then fall back to `gemini-3.5-flash`; each answer records the model used (ADR-0004). RAG-002 builds the basic adapter only (one model, no retry, `retry_count = 0`); retry/fallback is RAG-003 (OD-11).
- When the answer is insufficient, keep `missing_information` (what the documents don't cover). Optional related citations are allowed, but related content must not be presented as the answer (owner decision D2, 2026-09-24).

## Language
`application/common/language.py`: `detect_language(text)` = "vi" if the NFC-normalized text holds a Vietnamese-specific
letter (ă â đ ê ô ơ ư) or a tone-marked vowel, else "en". Limitations (tested): Vietnamese without diacritics → "en";
a word with a letter shared with other languages (e.g. "café") → "vi".

## OD-10 prompt (decided 2026-09-26, owner-approved before the live run)
- Template: `config/prompts/answer_v1.md`; the version string is the file name (`ANSWER_PROMPT_VERSION`, recorded in
  every `AnswerResult.prompt_version`). Prompts are never inlined in code. The file holds exactly the text sent.
- Current version: `answer_v2` (RAG-002 fix F1, 2026-09-26) = `answer_v1` + rule 4 "Wrap code, identifiers and
  expressions in backticks." so code indexers are not read as citation markers (citation-spec.md). `answer_v1.md` is
  kept unchanged; the first live dev answers were produced with it.
- Rule 2 is the owner's text (RAG-002 addendum 3). Two small additions, shown to and approved by the owner: rule 3 adds
  "and list every passage number you cite in "cited_passages""; rule 4 covers "answer" and "missing_information".
- Passages: numbered 1..k in rank order, each `[n] {document_name} — {heading path}` + newline + the link-stripped
  chunk body; blank line between passages. Placeholders `{answer_language}` (English | Vietnamese), `{passages}`,
  `{question}` are filled in one regex pass (braces in passages or questions are copied unchanged).
- JSON mode: `response_mime_type="application/json"` + `response_json_schema` (google-genai 1.75.0), schema
  `{"insufficient": bool, "answer": string, "cited_passages": [int], "missing_information": string}`, all required.
  Temperature 0.0, `max_output_tokens` 1024.

## Answer flow (`AnswerQuestion.ask`)
1. Detect the language; retrieve (retrieval-spec.md). Top-1 < threshold → gate answer (no LLM call).
2. Build the prompt; call the LLM; parse the JSON. Unusable output (not JSON, missing or mistyped key,
   `insufficient=false` with an empty answer, truncated at `MAX_TOKENS`, empty) raises `GenerationError` with the raw
   text; it is never turned into "insufficient".
3. `insufficient=true` → `answer` = localized message from `config/messages.json`, `insufficient_reason="llm"`,
   `missing_information` kept, citations = related content only (D2). Otherwise the answer text is shown with its
   markers resolved (citation-spec.md); a non-empty `missing_information` on a partial answer is kept too.
4. `latency_ms`: `embed_query`, `retrieve`, `generate` (absent when the gate fired), `total`.

## Messages
`config/messages.json`: EN "The document collection does not contain enough information to answer this question.";
VI "Bộ tài liệu hiện có không chứa đủ thông tin để trả lời câu hỏi này."
