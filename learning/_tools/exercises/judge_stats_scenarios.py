"""Offline scenarios for learning/11 and learning/12 (no network, no key). Run from the worktree root:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="src;." python learning/_tools/exercises/judge_stats_scenarios.py
"""
import json
from knowledge_assistant.application.evaluation.judge import (
    JudgeOutputError, ANSWER_CHECK, REFUSAL_CHECK, judge_check, parse_verdict)
from knowledge_assistant.application.evaluation.metrics.mapping import (
    JudgeVerdict, JudgeVerdictMissing, map_result, points_covered)
from knowledge_assistant.application.evaluation.metrics.latency import nearest_rank
from knowledge_assistant.application.evaluation.stats import (
    mcnemar_exact, paired_bootstrap_ci, percentile_interval, wilcoxon_signed_rank)
from scripts.evaluation.score_spot_check import agreement_rate, cohens_kappa, confusion_matrix

print("== J1 map_result")
V = JudgeVerdict
rows = [
    ("unanswerable bare refusal", dict(answerable=False, insufficient=True)),
    ("unanswerable refusal + note, judge says related-as-answer", dict(answerable=False, insufficient=True, has_related_note=True, judge=V(presents_related_as_answer=True))),
    ("unanswerable refusal + note, judge says no", dict(answerable=False, insufficient=True, has_related_note=True, judge=V(presents_related_as_answer=False))),
    ("answerable but insufficient", dict(answerable=True, insufficient=True)),
    ("answerable all yes", dict(answerable=True, insufficient=False, judge=V(required_points=("yes", "yes")))),
    ("answerable yes+partial", dict(answerable=True, insufficient=False, judge=V(required_points=("yes", "partial")))),
    ("answerable no+no", dict(answerable=True, insufficient=False, judge=V(required_points=("no", "no")))),
    ("answerable all yes but contradicts", dict(answerable=True, insufficient=False, judge=V(required_points=("yes", "yes"), contradicts_ground_truth=True))),
]
for name, kw in rows:
    print(name, "->", map_result(**kw))
try:
    map_result(answerable=True, insufficient=False)
except JudgeVerdictMissing as e:
    print("missing verdict ->", type(e).__name__)

print("== J2 points_covered")
print(points_covered(["yes", "partial", "no"]), points_covered(["yes", "yes"]), points_covered(["partial"]))

print("== J3 judge_check routing")
base = dict(status="ok", mode="full", citations=[], missing_information="")
for name, rec in [
    ("answerable answered", dict(base, answerable=True, insufficient=False)),
    ("answerable insufficient", dict(base, answerable=True, insufficient=True)),
    ("unanswerable bare refusal", dict(base, answerable=False, insufficient=True)),
    ("unanswerable refusal + note", dict(base, answerable=False, insufficient=True, missing_information="only about X")),
    ("unanswerable answered", dict(base, answerable=False, insufficient=False)),
    ("retrieval mode", dict(base, mode="retrieval", answerable=True, insufficient=False)),
]:
    print(name, "->", judge_check(rec))

print("== J4 parse_verdict strictness (the Q-EVAL-002:B style error)")
record = {"answer_points": [{"id": "P1", "required": True}, {"id": "P2", "required": True}, {"id": "P3", "required": False}],
          "citations": [{"marker": 1}]}
good = {"required_points": [{"id": "P1", "covered": "yes"}, {"id": "P2", "covered": "partial"}],
        "contradicts_ground_truth": False, "unsupported_claims": [],
        "citations": [{"marker": 1, "supports_attached_claim": "yes"}], "reason": "ok"}
def attempt(name, data):
    try:
        out = parse_verdict(ANSWER_CHECK, json.dumps(data), record); print(name, "-> OK", [p["covered"] for p in out["required_points"]])
    except JudgeOutputError as e:
        print(name, "-> JudgeOutputError:", str(e)[:70])
attempt("good", good)
attempt("marker 22 instead of 1", dict(good, citations=[{"marker": 22, "supports_attached_claim": "yes"}]))
attempt("optional point listed", dict(good, required_points=good["required_points"] + [{"id": "P3", "covered": "yes"}]))
attempt("bad covered value", dict(good, required_points=[{"id": "P1", "covered": "maybe"}, {"id": "P2", "covered": "yes"}]))
attempt("bool as marker", dict(good, citations=[{"marker": True, "supports_attached_claim": "yes"}]))
print("refusal ok:", parse_verdict(REFUSAL_CHECK, '{"presents_related_as_answer": false, "reason": "r"}', record))

print("== S1 kappa reproduces the real spot-check (confusion matrix from EPIC-05)")
pairs = ([("correct", "correct")] * 4 + [("correct_refusal", "correct_refusal")] * 2
         + [("partially_correct", "correct")] * 2 + [("partially_correct", "partially_correct")] * 2)
print(agreement_rate(pairs), round(cohens_kappa(pairs), 3))
print(confusion_matrix(pairs))
print("perfect single label:", cohens_kappa([("a", "a")] * 5), "empty:", cohens_kappa([]))

print("== S2 nearest-rank percentiles")
v = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
print([nearest_rank(v, p) for p in (10, 50, 51, 90, 95, 100)], nearest_rank([5], 95), nearest_rank([3, 1, 2], 50))

print("== S3 McNemar exact")
for name, a, b in [
    ("5-0 split", [1] * 5, [0] * 5),
    ("b=2 c=3 (accuracy row)", [1, 1, 0, 0, 0], [0, 0, 1, 1, 1]),
    ("b=11 c=5 (evidence hit@1 row)", [1] * 11 + [0] * 5, [0] * 11 + [1] * 5),
    ("b=1 c=1", [1, 0], [0, 1]),
    ("no discordant", [1, 0, 1], [1, 0, 1]),
]:
    r = mcnemar_exact(a, b); print(name, "-> b,c,p =", r.b, r.c, round(r.p_value, 4))

print("== S4 Wilcoxon exact")
r = wilcoxon_signed_rank([1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 3.0, 4.0, 5.0, 6.0]); print("all +1:", r)
r = wilcoxon_signed_rank([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]); print("all zero diffs:", r)
r = wilcoxon_signed_rank([0.1 + 0.2], [0.3]); print("float noise is a tie:", r.n, r.zeros_dropped)

print("== S5 bootstrap CI is reproducible (seed 42)")
a = [1, 0, 1, 1, 0, 1, 0, 1]; b = [1, 1, 1, 0, 1, 1, 1, 1]
c1 = paired_bootstrap_ci([float(x) for x in a], [float(x) for x in b], resamples=2000)
c2 = paired_bootstrap_ci([float(x) for x in a], [float(x) for x in b], resamples=2000)
print(round(c1.delta, 3), round(c1.low, 3), round(c1.high, 3), c1 == c2)
print(percentile_interval(list(range(1, 101))))

print("== X1 answers used by exercises in 11")
print(points_covered(["yes", "partial", "no", "yes"]))
print(round(cohens_kappa([("A", "A")] * 5 + [("B", "B")] * 2 + [("A", "B")] * 3), 3))

print("== X2 answers used by exercises in 12")
print(round(mcnemar_exact([1] * 4, [0] * 4).p_value, 4), round(mcnemar_exact([1] * 3 + [0] * 8, [0] * 3 + [1] * 8).p_value, 4))
import math
print(0.95 * 20, math.ceil(0.95 * 20), nearest_rank(list(range(1, 21)), 95))
print(nearest_rank(list(range(1, 11)), 50), nearest_rank([8, 3, 5, 1, 9, 7, 2, 6, 4, 10], 95))
print(round(2122.6 / 1628.6, 3))
print("== X3 float vs Fraction rank"); print(7 / 100 * 100, math.ceil(7 / 100 * 100), nearest_rank(list(range(1, 101)), 7))
