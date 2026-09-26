"""Retrieval metrics (EVAL-003b §1; evaluation-spec.md § Retrieval hit rule). Pure functions, no I/O.

`chunks` is the ranked retrieval result, rank 1 first; `k` cuts it to the top k. A chunk hits a span only on
offsets: same source_id and overlapping half-open `[char_start, char_end)` ranges. The chunk's heading path is never
compared (Arm A labels a merged section with its first heading, ADR-0003 D3; Arm B uses the nearest heading, D5).

- lenient (headline): a slot is satisfied by any of its expected or alternate sources/sections (D1);
- strict: the same with alternates removed (OWNER-001, 2026-09-25);
- a case hits when every slot is satisfied; the slot fraction and MRR use the lenient rule, strict MRR is secondary.
Corpus-insufficient cases have no spans and are excluded from these metrics; passing them in raises ValueError.
"""
from dataclasses import dataclass

from knowledge_assistant.application.evaluation.metrics.spans import EXPECTED, ExpectedSpan
from scripts.evaluation.validate_questions import collapse_whitespace

SOURCE = "source"
SECTION = "section"


@dataclass(frozen=True)
class RankedChunk:
    """The fields of a retrieved chunk the metrics need; `text` is `display_text` (normalized slice, no heading)."""

    source_id: str
    char_start: int
    char_end: int  # exclusive
    text: str = ""

    @classmethod
    def from_record(cls, record: dict) -> "RankedChunk":
        return cls(record["source_id"], record["char_start"], record["char_end"], record["display_text"])


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Half-open ranges: [0, 10) and [10, 20) touch but do not overlap."""
    return max(a_start, b_start) < min(a_end, b_end)


def _check(spans: list[ExpectedSpan], k: int | None = None) -> None:
    if not spans:
        raise ValueError("no expected spans: corpus-insufficient cases are excluded from retrieval metrics")
    if k is not None and k < 1:
        raise ValueError(f"k must be >= 1, got {k}")


def _hits(chunk: RankedChunk, span: ExpectedSpan, level: str) -> bool:
    if chunk.source_id != span.source_id:
        return False
    if level == SOURCE:
        return True
    if level == SECTION:
        return overlaps(chunk.char_start, chunk.char_end, span.char_start, span.char_end)
    raise ValueError(f"unknown level {level!r}")


def _usable(spans: list[ExpectedSpan], strict: bool) -> list[ExpectedSpan]:
    return [span for span in spans if span.role == EXPECTED] if strict else list(spans)


def slots_satisfied(chunks: list[RankedChunk], spans: list[ExpectedSpan], k: int, level: str = SECTION,
                    strict: bool = False) -> dict[str, bool]:
    """{slot: satisfied by a top-k chunk}. Every slot of the case is listed, also when strict leaves it empty."""
    _check(spans, k)
    usable = _usable(spans, strict)
    return {slot: any(_hits(chunk, span, level) for chunk in chunks[:k] for span in usable if span.slot == slot)
            for slot in sorted({span.slot for span in spans}, key=lambda s: int(s[1:]))}


def source_hit_at_k(chunks: list[RankedChunk], spans: list[ExpectedSpan], k: int, strict: bool = False) -> int:
    """1 if every slot has one of its source_ids among the top-k chunks."""
    return int(all(slots_satisfied(chunks, spans, k, SOURCE, strict).values()))


def section_hit_at_k(chunks: list[RankedChunk], spans: list[ExpectedSpan], k: int, strict: bool = False) -> int:
    """1 if every slot has a top-k chunk overlapping a span of one of its sections."""
    return int(all(slots_satisfied(chunks, spans, k, SECTION, strict).values()))


def slot_fraction_at_k(chunks: list[RankedChunk], spans: list[ExpectedSpan], k: int, level: str = SECTION) -> float:
    """Fraction of slots satisfied (lenient). Differs from the hit only for multi-slot cases."""
    satisfied = slots_satisfied(chunks, spans, k, level)
    return sum(satisfied.values()) / len(satisfied)


def reciprocal_rank(chunks: list[RankedChunk], spans: list[ExpectedSpan], k: int | None = None,
                    level: str = SECTION, strict: bool = False) -> float:
    """1 / rank of the first chunk hitting any slot's span (lenient by default), 0.0 if none in the top k."""
    _check(spans, k)
    usable = _usable(spans, strict)
    for rank, chunk in enumerate(chunks[:k] if k else chunks, start=1):
        if any(_hits(chunk, span, level) for span in usable):
            return 1.0 / rank
    return 0.0


def evidence_hit_at_k(chunks: list[RankedChunk], quotes: list[str], k: int, require_all: bool = False) -> int:
    """1 if a top-k chunk contains a whole evidence quote: any of the case's quotes (default), or with
    `require_all` every quote (each may sit in a different chunk, but each one whole in a single chunk).

    Both sides are compared after `validate_questions.collapse_whitespace` (every run of Unicode whitespace,
    incl. U+00A0, becomes one space), the same normalization that verified the quotes against the corpus.
    A quote split across two chunks is not contained in either, so it does not count.
    """
    if not quotes:
        raise ValueError("no evidence quotes: corpus-insufficient cases are excluded from retrieval metrics")
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    texts = [collapse_whitespace(chunk.text) for chunk in chunks[:k]]
    found = [any(collapse_whitespace(quote) in text for text in texts) for quote in quotes]
    return int(all(found) if require_all else any(found))


def mean(values: list[float]) -> float:
    """Arithmetic mean over cases (e.g. MRR = mean of reciprocal ranks); raises on an empty list."""
    if not values:
        raise ValueError("mean of no values")
    return sum(values) / len(values)
