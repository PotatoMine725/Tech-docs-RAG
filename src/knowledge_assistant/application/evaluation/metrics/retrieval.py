"""Retrieval metrics (EVAL-003b §1; evaluation-spec.md § Retrieval hit rule). Pure functions, no I/O.

`chunks` is the ranked retrieval result, rank 1 first; `k` cuts it to the top k. A chunk hits a span only on
offsets: same source_id and overlapping half-open `[char_start, char_end)` ranges. The chunk's heading path is never
compared (Arm A labels a merged section with its first heading, ADR-0003 D3; Arm B uses the nearest heading, D5).

- lenient (headline): a slot is satisfied by any of its expected or alternate sources/sections (D1);
- strict: the same with alternates removed (OWNER-001, 2026-09-25);
- a case hits when every slot is satisfied; the slot fraction and MRR use the lenient rule, strict MRR is secondary;
- evidence hit (headline): every required answer point has one of its quotes whole in a top-k chunk;
  any-quote evidence hit is a secondary diagnostic.
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


def required_point_quotes(case: dict) -> dict[str, list[str]]:
    """{required answer point id: the evidence quotes whose `supports` lists it}, in eval-v1 order.

    Optional points are left out. A quote supporting several points counts for each of them. Every evidence quote
    counts, also the few that lie in an approved alternate section (EVAL-003b-pre report, decision 5).
    """
    if not case["answerable"]:
        raise ValueError(f"{case['id']}: corpus-insufficient cases are excluded from retrieval metrics")
    points = {point["id"]: [] for point in case["answer_points"] if point["required"]}
    if not points:
        raise ValueError(f"{case['id']}: no required answer point")
    for evidence in case["evidence"]:
        for point_id in evidence["supports"]:
            if point_id in points:
                points[point_id].append(evidence["quote"])
    missing = [point_id for point_id, quotes in points.items() if not quotes]
    if missing:
        raise ValueError(f"{case['id']}: required points without an evidence quote: {missing}")
    return points


def _quotes_found(chunks: list[RankedChunk], quotes: list[str], k: int) -> list[bool]:
    """Per quote: is it contained whole in one top-k chunk? Both sides go through
    `validate_questions.collapse_whitespace` (every run of Unicode whitespace, incl. U+00A0, becomes one space), the
    same normalization that verified the quotes against the corpus. A quote split across two chunks does not count.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    texts = [collapse_whitespace(chunk.text) for chunk in chunks[:k]]
    return [any(collapse_whitespace(quote) in text for text in texts) for quote in quotes]


def evidence_hit_at_k(chunks: list[RankedChunk], point_quotes: dict[str, list[str]], k: int) -> int:
    """Headline (owner decision 2026-09-26): 1 if every required answer point has at least one of its supporting
    quotes contained whole in some top-k chunk - all-of across required points, any-of across the quotes of one point.

    `point_quotes` is `required_point_quotes(case)`; optional-point quotes are therefore ignored.
    """
    if not point_quotes:
        raise ValueError("no required points: corpus-insufficient cases are excluded from retrieval metrics")
    return int(all(any(_quotes_found(chunks, quotes, k)) for quotes in point_quotes.values()))


def any_evidence_hit_at_k(chunks: list[RankedChunk], quotes: list[str], k: int) -> int:
    """Secondary diagnostic: 1 if any one of the case's evidence quotes is contained whole in a top-k chunk."""
    if not quotes:
        raise ValueError("no evidence quotes: corpus-insufficient cases are excluded from retrieval metrics")
    return int(any(_quotes_found(chunks, quotes, k)))


def mean(values: list[float]) -> float:
    """Arithmetic mean over cases (e.g. MRR = mean of reciprocal ranks); raises on an empty list."""
    if not values:
        raise ValueError("mean of no values")
    return sum(values) / len(values)
