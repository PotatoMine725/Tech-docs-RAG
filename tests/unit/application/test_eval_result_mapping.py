"""EVAL-003b-pre: every row of the 09b §3 result-mapping table, points-covered and groundedness."""
import pytest

from knowledge_assistant.application.evaluation.metrics.mapping import (
    CORRECT,
    CORRECT_REFUSAL,
    FALSE_REFUSAL,
    HALLUCINATION,
    INCORRECT,
    PARTIALLY_CORRECT,
    JudgeVerdict,
    JudgeVerdictMissing,
    is_grounded,
    map_result,
    points_covered,
)

PRESENTS = JudgeVerdict(presents_related_as_answer=True)
NOT_PRESENTS = JudgeVerdict(presents_related_as_answer=False)


# --- unanswerable (corpus-insufficient) ------------------------------------------------------------------------

def test_unanswerable_bare_insufficient_is_correct_refusal_without_a_judge():
    assert map_result(answerable=False, insufficient=True) == CORRECT_REFUSAL


@pytest.mark.parametrize("note, citations", [(True, False), (False, True), (True, True)])
def test_unanswerable_insufficient_with_related_material_uses_the_refusal_check(note, citations):
    kwargs = {"answerable": False, "insufficient": True, "has_related_note": note, "has_related_citations": citations}
    # e.g. names MapGroup as related and says versioning isn't covered
    assert map_result(**kwargs, judge=NOT_PRESENTS) == CORRECT_REFUSAL
    # e.g. "use MapGroup("/v1") to version" presented as the documents' answer
    assert map_result(**kwargs, judge=PRESENTS) == HALLUCINATION
    with pytest.raises(JudgeVerdictMissing):
        map_result(**kwargs)


def test_unanswerable_answered_is_decided_by_the_refusal_check_never_auto_hallucination():
    assert map_result(answerable=False, insufficient=False, judge=NOT_PRESENTS) == CORRECT_REFUSAL
    assert map_result(answerable=False, insufficient=False, judge=PRESENTS) == HALLUCINATION
    with pytest.raises(JudgeVerdictMissing):
        map_result(answerable=False, insufficient=False)
    with pytest.raises(JudgeVerdictMissing):  # a verdict without the refusal field is not a refusal check
        map_result(answerable=False, insufficient=False, judge=JudgeVerdict(required_points=("yes",)))


# --- answerable -------------------------------------------------------------------------------------------------

def test_answerable_insufficient_is_false_refusal_without_a_judge():
    assert map_result(answerable=True, insufficient=True) == FALSE_REFUSAL
    assert map_result(answerable=True, insufficient=True, has_related_note=True) == FALSE_REFUSAL


@pytest.mark.parametrize("coverage, contradicts, expected", [
    (("yes", "yes"), False, CORRECT),
    (("yes", "partial"), False, PARTIALLY_CORRECT),
    (("partial", "no"), False, PARTIALLY_CORRECT),
    (("yes", "no"), False, PARTIALLY_CORRECT),
    (("no", "no"), False, INCORRECT),
    (("yes", "yes"), True, INCORRECT),  # all points covered but a contradiction / must_not_claim
    (("partial",), True, INCORRECT),
])
def test_answerable_answered(coverage, contradicts, expected):
    judge = JudgeVerdict(required_points=coverage, contradicts_ground_truth=contradicts)
    assert map_result(answerable=True, insufficient=False, judge=judge) == expected


def test_answerable_answered_without_verdict_or_points_raises():
    with pytest.raises(JudgeVerdictMissing):
        map_result(answerable=True, insufficient=False)
    with pytest.raises(JudgeVerdictMissing):
        map_result(answerable=True, insufficient=False, judge=JudgeVerdict(required_points=()))


def test_unknown_coverage_value_raises():
    with pytest.raises(ValueError, match="coverage"):
        map_result(answerable=True, insufficient=False, judge=JudgeVerdict(required_points=("maybe",)))


def test_unsupported_claims_do_not_change_the_label_only_groundedness():
    judge = JudgeVerdict(required_points=("yes",), unsupported_claims=("an extra claim",))
    assert map_result(answerable=True, insufficient=False, judge=judge) == CORRECT
    assert is_grounded(judge) is False
    assert is_grounded(JudgeVerdict(required_points=("yes",))) is True


# --- points-covered ---------------------------------------------------------------------------------------------

def test_points_covered_required_yes_partial_no_optional_ignored():
    # P1 yes, P2 partial, P3 no (required); optional P4 no is not passed -> (1 + 0.5) / 3 = 0.5
    assert points_covered(["yes", "partial", "no"]) == 0.5


@pytest.mark.parametrize("coverage, expected", [(["yes"], 1.0), (["no"], 0.0), (["partial", "partial"], 0.5),
                                                (["yes", "yes", "partial", "no"], 0.625)])
def test_points_covered_values(coverage, expected):
    assert points_covered(coverage) == expected


def test_points_covered_needs_required_points():
    with pytest.raises(ValueError):
        points_covered([])
