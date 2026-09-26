"""Answer result mapping (EVAL-003b §3; evaluation-spec.md OD-5 labels, D2 refusal rule). Pure, deterministic.

The judge never picks the label; it only supplies data (`JudgeVerdict`), and this table picks the label:

| answerable | system                                         | judge          | result                              |
|------------|------------------------------------------------|----------------|-------------------------------------|
| no         | insufficient, bare (no related note/citations) | none           | correct_refusal                     |
| no         | insufficient + related note or citations       | refusal check  | hallucination if it presents related content as the answer, else correct_refusal |
| no         | answered                                       | refusal check  | same rule                           |
| yes        | insufficient                                   | none           | false_refusal                       |
| yes        | answered                                       | points         | correct / partially_correct / incorrect |

A verdict the table needs but did not get raises `JudgeVerdictMissing`: the caller records a judge error, never a
guessed label. The refusal-check field name in the judge's JSON is owned by EVAL-003b proper; here it is the named
boolean `presents_related_as_answer`.
"""
from dataclasses import dataclass

CORRECT = "correct"
PARTIALLY_CORRECT = "partially_correct"
INCORRECT = "incorrect"
FALSE_REFUSAL = "false_refusal"
CORRECT_REFUSAL = "correct_refusal"
HALLUCINATION = "hallucination"

YES, PARTIAL, NO = "yes", "partial", "no"
COVERAGE_VALUES = (YES, PARTIAL, NO)


class JudgeVerdictMissing(ValueError):
    """The mapping needs a judge verdict (or a verdict field) that was not supplied."""


@dataclass(frozen=True)
class JudgeVerdict:
    """The judge output fields the mapping reads (already parsed and validated by the judge step)."""

    required_points: tuple[str, ...] = ()  # coverage of each REQUIRED answer point: yes | partial | no
    contradicts_ground_truth: bool = False  # includes stating a must_not_claim item
    unsupported_claims: tuple[str, ...] = ()
    presents_related_as_answer: bool | None = None  # refusal check (D2); None = not judged


def _check_coverage(values) -> None:
    unknown = [value for value in values if value not in COVERAGE_VALUES]
    if unknown:
        raise ValueError(f"coverage must be one of {COVERAGE_VALUES}, got {unknown}")


def map_result(answerable: bool, insufficient: bool, has_related_note: bool = False,
               has_related_citations: bool = False, judge: JudgeVerdict | None = None) -> str:
    """The one `result` label of an answer record."""
    if not answerable:
        if insufficient and not has_related_note and not has_related_citations:
            return CORRECT_REFUSAL
        if judge is None or judge.presents_related_as_answer is None:
            raise JudgeVerdictMissing("unanswerable case with a related note, citations or an answer needs the "
                                      "judge's refusal check")
        return HALLUCINATION if judge.presents_related_as_answer else CORRECT_REFUSAL
    if insufficient:
        return FALSE_REFUSAL
    if judge is None or not judge.required_points:
        raise JudgeVerdictMissing("answered answerable case needs the judge's coverage of the required points")
    _check_coverage(judge.required_points)
    if judge.contradicts_ground_truth:
        return INCORRECT
    if all(value == YES for value in judge.required_points):
        return CORRECT
    if any(value in (YES, PARTIAL) for value in judge.required_points):
        return PARTIALLY_CORRECT
    return INCORRECT


def is_grounded(judge: JudgeVerdict) -> bool:
    """Groundedness (separate metric from `result`): the judge found no unsupported claim."""
    return not judge.unsupported_claims


def points_covered(required_coverage: list[str] | tuple[str, ...]) -> float:
    """(required `yes` + 0.5 x required `partial`) / required points (OD-5, owner 2026-09-24, REORIENT-001 C4).

    Pass the coverage of the required points only; optional points never count.
    """
    if not required_coverage:
        raise ValueError("points-covered needs at least one required point")
    _check_coverage(required_coverage)
    yes = sum(value == YES for value in required_coverage)
    partial = sum(value == PARTIAL for value in required_coverage)
    return (yes + 0.5 * partial) / len(required_coverage)
