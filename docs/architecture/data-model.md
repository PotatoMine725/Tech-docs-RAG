# Data model

Concepts: Document, ParsedDocument, DocumentChunk, Citation, Question, EvaluationCase, EvaluationResult, Experiment.
Defined (INGEST-001): `Document` (source_id, name, path, source_url), `ParsedDocument` (document, text, document_name, source_url, wrapper_title, sections, normalized), `SectionSpan` (heading_path, level, variant, variant_count, char_start, char_end into the normalized text), `DocumentChunk` (exactly the ADR-0003 D6 fields), `Citation` (`location_type` defaults to `heading`). Question/EvaluationCase/EvaluationResult/Experiment: still skeletons (EVAL-002/003).
Citation conceptual fields: source_id, document_name, location_type, location, excerpt.
