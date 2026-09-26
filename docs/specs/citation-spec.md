# Citation specification

Status: decided for RAG-002 (2026-09-26). Code: `application/citation/citations.py`; model `core.models.Citation`.

## Known facts
- Locations must not assume page numbers (page, section, heading, paragraph, line, URL, document-relative, other).
- Conceptual fields: source_id, document_name, location_type, location, excerpt.

## Requirements
- Chunk citations use `location_type = heading` and the heading path (ADR-0003 D5/D6).
- Excerpts stay in the original English, even when the answer is Vietnamese (ADR-0003 D9).
- On an insufficient answer, citations are optional and point only to related content; they must not be presented as supporting an answer (owner decision D2, 2026-09-24).

## Format (RAG-002)
- `Citation` fields: `source_id`, `document_name`, `location` (heading path joined with " > "), `excerpt`, `chunk_id`,
  `marker` (the passage number n), `source_url` ("" if the document has none; all 24 accepted documents have one),
  `location_type` ("heading").
- **Markers.** The answer cites passage n with `[n]` (e.g. `[2]` or `[2][3]`), n = rank in the retrieved list (1..k).
  A marker or `cited_passages` number outside 1..k is removed from the text and recorded in
  `AnswerResult.dropped_markers`.
- **What is not a marker (RAG-002 fix F1, owner decision 2026-09-26).** A `[n]` inside inline code (a backtick span)
  or inside a fenced code block (``` or ~~~ fence) is never a marker, and neither is `[0]` anywhere, prose included
  (markers are 1-based). Such text is left byte-identical and recorded nowhere (not a citation, not in
  `dropped_markers`, and a sentence whose only `[n]` is in code counts as uncited). A plain-text `[n]` with n ≥ 1 is a
  marker even right after a word or a closing backtick (`sealed[2].`, `` `x`[1] ``). A `0` in `cited_passages` is
  still out of range and recorded in `dropped_markers`.
- **Order.** Citations follow the first appearance of their marker in the answer, then any `cited_passages` number
  not marked in the text; each passage at most once.
- **Excerpt.** The first 300 characters of the link-stripped chunk body, cut back to the last word boundary; a verbatim
  prefix of that body (no ellipsis), in English.
- **Diagnostic.** `uncited_sentences` = sentences of ≥ 5 words with no marker (markers right after the sentence end
  count for that sentence). A diagnostic only; no answer is rejected for it.
- **Insufficient answers.** Citations built from the model's `cited_passages` are related content only; the GUI
  shows them as related (GUI-001-pre contract `related_only = AnswerResult.insufficient`).
