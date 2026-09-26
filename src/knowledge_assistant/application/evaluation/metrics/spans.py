"""Expected section spans per evidence slot (EVAL-003b §1; evaluation-spec.md § Retrieval hit rule; ADR-0003 D8).

Pure: takes parsed `normalized.jsonl` records and question cases, returns plain data. Every expected and alternate
(source_id, heading path) of a case maps to all its `[char_start, char_end)` spans in the normalized text: a heading
path can occur in several version variants, and any variant counts. Each span keeps its slot and its role
(`expected` / `alternate`) so strict hits (expected only) can be computed. File I/O is in `build_expected_spans.py`.
"""
from collections import defaultdict
from dataclasses import dataclass

EXPECTED = "expected"
ALTERNATE = "alternate"


@dataclass(frozen=True)
class ExpectedSpan:
    """One span of an expected or alternate section; offsets index the normalized document text."""

    slot: str
    role: str  # EXPECTED | ALTERNATE
    source_id: str
    heading_path: str
    variant: int
    char_start: int
    char_end: int  # exclusive


def section_index(normalized_records: list[dict]) -> dict[tuple[str, str], list[tuple[int, int, int]]]:
    """{(source_id, heading_path): [(variant, char_start, char_end), ...]} in document order."""
    index = defaultdict(list)
    for record in normalized_records:
        for section in record["metadata"]["sections"]:
            index[(record["id"], section["heading_path"])].append(
                (section["variant"], section["char_start"], section["char_end"])
            )
    return dict(index)


def case_spans(case: dict, index: dict[tuple[str, str], list[tuple[int, int, int]]]) -> list[ExpectedSpan]:
    """All spans of a case: expected sources first, then alternates, each in file order, variants ascending."""
    spans = []
    for role, refs in ((EXPECTED, case["expected_sources"]), (ALTERNATE, case["acceptable_alternate_sources"])):
        for ref in refs:
            variants = index.get((ref["source_id"], ref["heading_path"]))
            if not variants:
                raise ValueError(f"{case['id']}: section not in the normalized corpus: #{ref['source_id']} "
                                 f"{ref['heading_path']!r}")
            spans += [ExpectedSpan(ref["slot"], role, ref["source_id"], ref["heading_path"], variant, start, end)
                      for variant, start, end in variants]
    return spans


def _slot_order(slot: str) -> int:
    return int(slot[1:])  # "S2" < "S10"


def build_expected_spans(normalized_records: list[dict], cases: list[dict]) -> dict[str, dict]:
    """{case_id: {"answerable": bool, "slots": {slot: [span dict, ...]}}}; corpus-insufficient cases have no slots."""
    index = section_index(normalized_records)
    result = {}
    for case in cases:
        slots = defaultdict(list)
        for span in case_spans(case, index):
            slots[span.slot].append({
                "role": span.role,
                "source_id": span.source_id,
                "heading_path": span.heading_path,
                "variant": span.variant,
                "char_start": span.char_start,
                "char_end": span.char_end,
            })
        result[case["id"]] = {
            "answerable": case["answerable"],
            "slots": {slot: slots[slot] for slot in sorted(slots, key=_slot_order)},
        }
    return result


def spans_from_entry(entry: dict) -> list[ExpectedSpan]:
    """Inverse of one `build_expected_spans` entry: the case's spans as `ExpectedSpan` objects."""
    return [ExpectedSpan(slot, span["role"], span["source_id"], span["heading_path"], span["variant"],
                         span["char_start"], span["char_end"])
            for slot, spans in entry["slots"].items() for span in spans]
