# Citation specification

Status: skeleton. Undecided items are TBD / DECISION REQUIRED.

## Known facts
- Locations must not assume page numbers (page, section, heading, paragraph, line, URL, document-relative, other).
- Conceptual fields: source_id, document_name, location_type, location, excerpt.

## Requirements
- Chunk citations use `location_type = heading` and the heading path (ADR-0003 D5/D6).
- Excerpts stay in the original English, even when the answer is Vietnamese (ADR-0003 D9).
- On an insufficient answer, citations are optional and point only to related content; they must not be presented as supporting an answer (owner decision D2, 2026-09-24).
- Everything else: TBD.
