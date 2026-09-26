"""EVAL-003b-pre: paired statistics (EXP-001 §1) on hand examples; p-values worked out by hand in the comments."""
import pytest

from knowledge_assistant.application.evaluation.stats import (
    mcnemar_exact,
    paired_bootstrap_ci,
    percentile_interval,
    wilcoxon_signed_rank,
)


# --- exact McNemar ----------------------------------------------------------------------------------------------

def _pairs(both, a_only, b_only, neither):
    a = [1] * both + [1] * a_only + [0] * b_only + [0] * neither
    b = [1] * both + [0] * a_only + [1] * b_only + [0] * neither
    return a, b


@pytest.mark.parametrize("a_only, b_only, p", [
    (1, 6, 0.125),                 # n = 7: 2 * (C(7,0) + C(7,1)) / 2^7 = 2 * 8/128
    (0, 5, 0.0625),                # n = 5: 2 * 1/32
    (2, 10, 158 / 4096),           # n = 12: 2 * (1 + 12 + 66) / 4096 = 0.0385742...
    (3, 3, 1.0),                   # 2 * (1 + 6 + 15 + 20)/64 = 1.3125 -> capped at 1
    (0, 0, 1.0),                   # no discordant pairs
])
def test_mcnemar_exact(a_only, b_only, p):
    a, b = _pairs(both=20, a_only=a_only, b_only=b_only, neither=4)
    result = mcnemar_exact(a, b)
    assert (result.b, result.c) == (a_only, b_only)
    assert result.p_value == pytest.approx(p, abs=1e-15)


def test_mcnemar_b_is_a_only_and_c_is_b_only():
    result = mcnemar_exact([True, True, False], [False, True, True])
    assert (result.b, result.c) == (1, 1)
    assert mcnemar_exact([1, 1, 0], [0, 0, 0]).b == 2


def test_mcnemar_is_symmetric_in_the_p_value():
    a, b = _pairs(5, 1, 6, 5)
    assert mcnemar_exact(a, b).p_value == mcnemar_exact(b, a).p_value


def test_unequal_lengths_raise():
    for test in (mcnemar_exact, paired_bootstrap_ci, wilcoxon_signed_rank):
        with pytest.raises(ValueError, match="equal lengths"):
            test([1, 0], [1])


# --- paired bootstrap -------------------------------------------------------------------------------------------

def test_bootstrap_resamples_pairs_together():
    # B = A + 1 for every case but the cases vary a lot: resampling pairs gives a difference of exactly 1 every time;
    # resampling the arms independently would give a wide interval.
    a = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0]
    b = [x + 1 for x in a]
    result = paired_bootstrap_ci(a, b)
    assert (result.delta, result.low, result.high) == pytest.approx((1.0, 1.0, 1.0), abs=1e-9)  # float sums only
    assert (result.resamples, result.seed, result.confidence) == (10_000, 42, 0.95)


def test_bootstrap_two_pairs_hand_distribution():
    # differences {0, 1}: a resampled mean is 0 (p 1/4), 0.5 (p 1/2) or 1 (p 1/4); with 10 000 resamples the
    # 2.5th percentile is 0 and the 97.5th is 1 (fewer than 250 zeros among 10 000 draws is practically impossible).
    result = paired_bootstrap_ci([0.0, 0.0], [0.0, 1.0])
    assert (result.delta, result.low, result.high) == (0.5, 0.0, 1.0)


def test_bootstrap_is_reproducible_with_the_fixed_seed():
    a = [0, 1, 1, 0, 1, 0, 0, 1, 1, 1]
    b = [1, 1, 0, 1, 1, 1, 0, 1, 1, 0]
    assert paired_bootstrap_ci(a, b) == paired_bootstrap_ci(a, b)
    result = paired_bootstrap_ci(a, b)
    assert result.delta == pytest.approx(0.1)
    assert result.low <= result.delta <= result.high


def test_percentile_interval_uses_exact_nearest_ranks():
    values = list(range(1, 10_001))
    # ranks ceil(2.5% x 10 000) = 250 and ceil(97.5% x 10 000) = 9750 (a float tail of 2.5000000000000022 gives 251)
    assert percentile_interval(values, 0.95) == (250, 9750)
    assert percentile_interval(values, 0.9) == (500, 9500)


# --- Wilcoxon signed-rank ---------------------------------------------------------------------------------------

def test_wilcoxon_all_positive():
    # d = 1..5: W+ = 15, W- = 0; P(W+ >= 15) = 1/32 -> p = 2/32
    result = wilcoxon_signed_rank([0] * 5, [1, 2, 3, 4, 5])
    assert (result.n, result.w_plus, result.w_minus) == (5, 15, 0)
    assert result.p_value == 0.0625


def test_wilcoxon_one_negative():
    # d = 1, -2, 3, 4, 5: W- = 2; subsets of {1..5} with sum <= 2 are {}, {1}, {2} -> 3/32; p = 6/32
    result = wilcoxon_signed_rank([0] * 5, [1, -2, 3, 4, 5])
    assert (result.w_plus, result.w_minus) == (13, 2)
    assert result.p_value == 0.1875


def test_wilcoxon_ties_use_average_ranks_and_the_exact_distribution():
    # |d| = 2, 2, 2, 1 -> ranks 3, 3, 3, 1; W+ = 9, W- = 1. Doubled ranks {6, 6, 6, 2}: of the 16 sign patterns
    # W+ (doubled) >= 18 only for {6,6,6} (18) and {6,6,6,2} (20) -> 2/16; p = 2 * 2/16 = 0.25
    result = wilcoxon_signed_rank([0] * 4, [2, 2, 2, -1])
    assert (result.w_plus, result.w_minus) == (9, 1)
    assert result.p_value == 0.25


def test_wilcoxon_drops_zero_differences():
    result = wilcoxon_signed_rank([0, 5, 5, 5, 5, 5], [0, 6, 7, 8, 9, 10])  # first pair has d = 0
    assert (result.n, result.zeros_dropped, result.p_value) == (5, 1, 0.0625)


def test_wilcoxon_float_noise_is_a_tie():
    # 0.1 + 0.2 = 0.30000000000000004: |d| must tie with 0.3 (ranks 1.5, 1.5), not rank 2 vs 1
    result = wilcoxon_signed_rank([0.0, 0.0], [0.1 + 0.2, -0.3])
    assert (result.w_plus, result.w_minus) == (1.5, 1.5)
    assert result.p_value == 1.0


def test_wilcoxon_no_differences():
    result = wilcoxon_signed_rank([1, 2], [1, 2])
    assert (result.n, result.zeros_dropped, result.p_value) == (0, 2, 1.0)
