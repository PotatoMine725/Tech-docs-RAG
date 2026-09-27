"""Retrieval metrics (EVAL-003b §1; evaluation-spec.md § Retrieval hit rule). Pure functions, no I/O.

`chunks` is the ranked retrieval result, rank 1 first; `k` cuts it to the top k. A chunk hits a span only on
offsets: same source_id and overlapping half-open `[char_start, char_end)` ranges. The chunk's heading path is never
compared (Arm A labels a merged section with its first heading, ADR-0003 D3; Arm B uses the nearest heading, D5).
Duplicate rule (owner, EVAL-003b addendum 2026-09-27): for every span and source metric, lenient and strict, a chunk
also hits when one of its dropped same-passage copies (`duplicate_chunk_ids`) does; `duplicate_rule_changes` names the
values the rule changed for a case, so a report can count them.

- lenient (headline): a slot is satisfied by any of its expected or alternate sources/sections (D1);
- strict: the same with alternates removed (OWNER-001, 2026-09-25);
- a case hits when every slot is satisfied; the slot fraction and MRR use the lenient rule, strict MRR is secondary;
- evidence hit (headline): every required answer point has one of its quotes whole in a top-k chunk;
  any-quote evidence hit is a secondary diagnostic. Evidence hit is content-level: quotes found in chunks of
  owner-approved alternate sections count too (it aligns with lenient section hit, not strict); the diagnostic
  `evidence_hit_via_alternate_only_at_k` flags hits earned only outside the expected spans.
Corpus-insufficient cases have no spans and are excluded from these metrics; passing them in raises ValueError.
"""
from collections.abc import Mapping
from dataclasses import dataclass, replace

from knowledge_assistant.application.evaluation.metrics.spans import EXPECTED, ExpectedSpan
from scripts.evaluation.validate_questions import collapse_whitespace

SOURCE = "source"
SECTION = "section"
HIT_KS = (1, 3, 5)  # reported cut-offs (§1: @5 headline, @1 and @3 for ranking quality)


Location = tuple[str, int, int]  # (source_id, char_start, char_end) of a chunk


@dataclass(frozen=True)
class RankedChunk:
    """The fields of a retrieved chunk the metrics need; `text` is `display_text` (normalized slice, no heading).

    `duplicates` are the locations of the same-passage copies the retriever dropped for this chunk
    (`duplicate_chunk_ids`, RAG-002). Span and source metrics count a hit by the chunk OR any duplicate (owner,
    EVAL-003b addendum 2026-09-27); evidence metrics read `text` only.
    """

    source_id: str
    char_start: int
    char_end: int  # exclusive
    text: str = ""
    duplicates: tuple[Location, ...] = ()

    @classmethod
    def from_record(cls, record: dict, chunk_index: Mapping[str, Location] | None = None) -> "RankedChunk":
        """A runner record's retrieved chunk. `chunk_index` ({chunk_id: location}, from the arm's chunk file) resolves
        `duplicate_chunk_ids`; a chunk with duplicates and no index raises, so the rule is never skipped silently."""
        duplicate_ids = record.get("duplicate_chunk_ids") or []
        if duplicate_ids and chunk_index is None:
            raise ValueError(f"chunk at {record['source_id']} [{record['char_start']}, {record['char_end']}) has "
                             f"duplicate_chunk_ids {duplicate_ids}: pass the arm's chunk index to resolve them")
        unknown = [chunk_id for chunk_id in duplicate_ids if chunk_id not in chunk_index]
        if unknown:
            raise ValueError(f"duplicate chunk ids not in the chunk index: {unknown}")
        return cls(record["source_id"], record["char_start"], record["char_end"], record["display_text"],
                   tuple(tuple(chunk_index[chunk_id]) for chunk_id in duplicate_ids))


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Half-open ranges: [0, 10) and [10, 20) touch but do not overlap."""
    return max(a_start, b_start) < min(a_end, b_end)


def _check(spans: list[ExpectedSpan], k: int | None = None) -> None:
    if not spans:
        raise ValueError("no expected spans: corpus-insufficient cases are excluded from retrieval metrics")
    if k is not None and k < 1:
        raise ValueError(f"k must be >= 1, got {k}")


def _location_hits(location: Location, span: ExpectedSpan, level: str) -> bool:
    source_id, char_start, char_end = location
    if source_id != span.source_id:
        return False
    if level == SOURCE:
        return True
    if level == SECTION:
        return overlaps(char_start, char_end, span.char_start, span.char_end)
    raise ValueError(f"unknown level {level!r}")


def _hits(chunk: RankedChunk, span: ExpectedSpan, level: str) -> bool:
    """Section level: the chunk or any of its dropped duplicates overlaps the span (duplicate rule, owner 2026-09-27).
    Source level: the kept chunk's own document only, i.e. what the user sees (owner, same day)."""
    duplicates = chunk.duplicates if level == SECTION else ()
    return any(_location_hits(location, span, level)
               for location in ((chunk.source_id, chunk.char_start, chunk.char_end), *duplicates))


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


def _case_label(case: dict) -> str:
    """The case id for error messages: a dataset case has `id`, a runner record (EVAL-003a) has `case_id`."""
    return case.get("id") or case.get("case_id", "?")


def required_point_quotes(case: dict) -> dict[str, list[str]]:
    """{required answer point id: the evidence quotes whose `supports` lists it}, in eval-v1 order.

    Optional points are left out. A quote supporting several points counts for each of them. Every evidence quote
    counts, also the few that lie in an approved alternate section (EVAL-003b-pre report, decision 5).
    `case` is a dataset case or an EVAL-003a run record: both carry `answerable`, `answer_points` and `evidence`.
    """
    if not case["answerable"]:
        raise ValueError(f"{_case_label(case)}: corpus-insufficient cases are excluded from retrieval metrics")
    points = {point["id"]: [] for point in case["answer_points"] if point["required"]}
    if not points:
        raise ValueError(f"{_case_label(case)}: no required answer point")
    for evidence in case["evidence"]:
        for point_id in evidence["supports"]:
            if point_id in points:
                points[point_id].append(evidence["quote"])
    missing = [point_id for point_id, quotes in points.items() if not quotes]
    if missing:
        raise ValueError(f"{_case_label(case)}: required points without an evidence quote: {missing}")
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


def evidence_hit_via_alternate_only_at_k(chunks: list[RankedChunk], point_quotes: dict[str, list[str]],
                                         spans: list[ExpectedSpan], k: int) -> int:
    """Diagnostic (owner, 2026-09-26; the headline is unchanged): 1 if `evidence_hit_at_k` is 1 and every required
    point was satisfied only by top-k chunks outside the expected spans, i.e. no top-k chunk overlapping a span with
    role `expected` contains one of that point's quotes. Such a hit was earned from alternate (or other) sections only.
    """
    _check(spans, k)
    if not point_quotes:
        raise ValueError("no required points: corpus-insufficient cases are excluded from retrieval metrics")
    expected = _usable(spans, strict=True)
    inside, outside = [], []
    for chunk in chunks[:k]:
        (inside if any(_hits(chunk, span, SECTION) for span in expected) else outside).append(chunk)

    def found(part: list[RankedChunk], quotes: list[str]) -> bool:
        return bool(part) and any(_quotes_found(part, quotes, len(part)))

    return int(all(found(outside, quotes) and not found(inside, quotes) for quotes in point_quotes.values()))


def chunk_index(chunk_records: list[dict]) -> dict[str, Location]:
    """{chunk_id: (source_id, char_start, char_end)} from an arm's parsed chunk file; resolves duplicate_chunk_ids."""
    return {record["chunk_id"]: (record["source_id"], record["char_start"], record["char_end"])
            for record in chunk_records}


def hits_any(chunk: RankedChunk, spans: list[ExpectedSpan], level: str = SECTION, strict: bool = False) -> bool:
    """Does this one chunk (or a duplicate of it) hit any span of the case? Used for citation precision."""
    _check(spans)
    return any(_hits(chunk, span, level) for span in _usable(spans, strict))


def duplicate_rule_changes(chunks: list[RankedChunk], spans: list[ExpectedSpan]) -> list[str]:
    """Names of the span/source values of one case x arm that the duplicate rule changed (for the report count):
    hit@1/3/5 at source and section level, lenient and strict, the four MRR values and the two slot fractions,
    each computed with the duplicates and again with them removed."""
    bare = [replace(chunk, duplicates=()) for chunk in chunks]
    changed = []
    for k in HIT_KS:
        for level, hit in ((SOURCE, source_hit_at_k), (SECTION, section_hit_at_k)):
            for strict in (False, True):
                if hit(chunks, spans, k, strict) != hit(bare, spans, k, strict):
                    changed.append(f"{level}_hit@{k}" + (":strict" if strict else ""))
    for level in (SECTION, SOURCE):
        for strict in (False, True):
            if reciprocal_rank(chunks, spans, level=level, strict=strict) != reciprocal_rank(bare, spans, level=level,
                                                                                           strict=strict):
                changed.append(("mrr" if level == SECTION else "source_mrr") + (":strict" if strict else ""))
        if slot_fraction_at_k(chunks, spans, max(HIT_KS), level) != slot_fraction_at_k(bare, spans, max(HIT_KS), level):
            changed.append(f"{level}_slot_fraction@{max(HIT_KS)}")
    return changed


def mean(values: list[float]) -> float:
    """Arithmetic mean over cases (e.g. MRR = mean of reciprocal ranks); raises on an empty list."""
    if not values:
        raise ValueError("mean of no values")
    return sum(values) / len(values)
