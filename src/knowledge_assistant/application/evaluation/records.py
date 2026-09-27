"""The evaluation record: one JSON line per case x arm x mode (EVAL-003a; schema = task prompt + owner addendum 2026-09-27).

Ground truth is copied verbatim from the frozen question file and never modified: `evidence[].supports` and the
answer-point `required` flags are what the metrics read. A record has EVERY field, whatever the mode or status;
what was not generated is null (or an empty list). Two conventions matter to the metric code (EVAL-003b-pre):
- a record without an LLM call (retrieval mode, or the gate answered) has `retry_count` 0 and `fallback_used` false,
  so it counts as clean in the latency table, and `latency_ms` is always a full dict, missing stages null;
- each retrieved chunk carries `display_text`, so `RankedChunk.from_record(retrieved[i])` works on it as it is.
`records.jsonl` is append-only: a retried case leaves its earlier error line, so read it with `latest_records`.
"""
import copy

from knowledge_assistant.application.common.passage import passage_hash
from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, Citation, RetrievedChunk

IDENTITY_FIELDS = ("run_id", "case_id", "arm", "mode", "status")
ERROR_FIELDS = ("error", "error_kind", "error_model", "error_type")
GROUND_TRUTH_FIELDS = (
    "question", "language", "parallel_group_id", "answerable", "expected_answer", "answer_points",
    "expected_sources", "acceptable_alternate_sources", "evidence", "acceptable_variations", "must_not_claim",
    "citation_criteria", "tags",
)
LATENCY_STAGES = ("embed_query", "retrieve", "generate", "retry_wait", "throttle_wait", "total")
GENERATED_DEFAULTS = {
    "llm_called": False,
    "retrieved": [],
    "top1_score": None,
    "gate_fired": None,
    "duplicates_dropped": None,
    "answer": None,
    "insufficient": None,
    "insufficient_reason": None,
    "missing_information": None,
    "citations": [],
    "dropped_markers": [],
    "uncited_sentences": None,
    "latency_ms": dict.fromkeys(LATENCY_STAGES),
    "model_used": None,
    "retry_count": 0,
    "fallback_used": False,
    "prompt_tokens": None,
    "output_tokens": None,
    "thoughts_tokens": None,
    "prompt_version": None,
}
GENERATED_FIELDS = tuple(GENERATED_DEFAULTS)
TIME_FIELDS = ("started_at", "finished_at")
RECORD_FIELDS = IDENTITY_FIELDS + ERROR_FIELDS + GROUND_TRUTH_FIELDS + GENERATED_FIELDS + TIME_FIELDS

RecordKey = tuple[str, str, str]  # (case_id, arm, mode)


def ground_truth(case: dict) -> dict:
    """The ground-truth fields of a dataset case, deep-copied so a record can never change the dataset."""
    missing = [field for field in GROUND_TRUTH_FIELDS if field not in case]
    if missing:
        raise ValueError(f"case {case.get('id', '?')} lacks ground-truth fields {missing}")
    return {field: copy.deepcopy(case[field]) for field in GROUND_TRUTH_FIELDS}


def chunk_entry(hit: RetrievedChunk) -> dict:
    """One retrieved chunk: position, score, text and dedup facts. `display_text` feeds evidence_hit."""
    chunk = hit.chunk
    return {
        "rank": hit.rank,
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "heading_path": HEADING_PATH_SEPARATOR.join(chunk.heading_path),
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "score": hit.score,
        "display_text": chunk.display_text,
        "passage_hash": passage_hash(chunk),
        "duplicate_chunk_ids": list(hit.duplicate_chunk_ids),
    }


def citation_entry(citation: Citation) -> dict:
    return {
        "marker": citation.marker,
        "chunk_id": citation.chunk_id,
        "source_id": citation.source_id,
        "heading_path": citation.location,
    }


def assemble(run_id: str, case: dict, arm: str, mode: str, status: str, started_at: str, finished_at: str,
             generated: dict, error: dict | None = None) -> dict:
    """The full record in schema order. `generated` and `error` override defaults; an unknown key is a bug."""
    unknown = set(generated) - set(GENERATED_DEFAULTS)
    if unknown:
        raise ValueError(f"not in the record schema: {sorted(unknown)}")
    unknown_error = set(error or {}) - set(ERROR_FIELDS)
    if unknown_error:
        raise ValueError(f"not in the record schema: {sorted(unknown_error)}")
    values = {
        "run_id": run_id, "case_id": case["id"], "arm": arm, "mode": mode, "status": status,
        **dict.fromkeys(ERROR_FIELDS), **(error or {}),
        **ground_truth(case),
        **copy.deepcopy(GENERATED_DEFAULTS), **generated,
        "started_at": started_at, "finished_at": finished_at,
    }
    return {field: values[field] for field in RECORD_FIELDS}


def record_key(record: dict) -> RecordKey:
    return record["case_id"], record["arm"], record["mode"]


def latest_records(records: list[dict]) -> dict[RecordKey, dict]:
    """The last line per (case_id, arm, mode), in first-seen order: what a retry left is the case's final state."""
    latest: dict[RecordKey, dict] = {}
    for record in records:
        latest[record_key(record)] = record
    return latest
