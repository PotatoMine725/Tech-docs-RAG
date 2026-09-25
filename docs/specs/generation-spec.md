# Generation specification

Status: skeleton. Undecided items are TBD / DECISION REQUIRED.

## Known facts
- Questions may be in English or Vietnamese; the corpus is English (ADR-0003 D9).

## Requirements
- The answer MUST be in the question's language.
- The "insufficient information" message MUST be in the question's language.
- Answer model `gemini-3.5-flash-lite`; on repeated 503/429, retry with backoff then fall back to `gemini-3.5-flash`; each answer records the model used (ADR-0004).
- When the answer is insufficient, keep `missing_information` (what the documents don't cover). Optional related citations are allowed, but related content must not be presented as the answer (owner decision D2, 2026-09-24).
- Everything else: TBD.
