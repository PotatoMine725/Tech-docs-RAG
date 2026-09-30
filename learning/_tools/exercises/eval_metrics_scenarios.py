"""Offline scenarios for learning/10 (no network, no key). Run from the worktree root:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="src;." python learning/_tools/exercises/eval_metrics_scenarios.py
"""
from knowledge_assistant.application.evaluation.integrity import frozen_hashes, sha256_hex, verify_frozen_files
from knowledge_assistant.application.evaluation.metrics.retrieval import (
    RankedChunk, overlaps, reciprocal_rank, section_hit_at_k, slot_fraction_at_k, slots_satisfied, source_hit_at_k)
from knowledge_assistant.application.evaluation.metrics.spans import ALTERNATE, EXPECTED, ExpectedSpan
from knowledge_assistant.core.exceptions import IntegrityError

print("== E1 overlaps (half-open)")
print(overlaps(0, 10, 10, 20), overlaps(0, 10, 9, 20), overlaps(5, 6, 0, 100))

# Case: slot S1 = doc 04 [0,100) expected ; slot S2 = doc 26 [0,50) expected + doc 20 [0,80) alternate
spans = [
    ExpectedSpan("S1", EXPECTED, "04", "H", 1, 0, 100),
    ExpectedSpan("S2", EXPECTED, "26", "H", 1, 0, 50),
    ExpectedSpan("S2", ALTERNATE, "20", "H", 1, 0, 80),
]
C = RankedChunk
print("== E2 strict vs lenient, two slots")
topk = [C("04", 10, 60), C("20", 0, 40)]
print("lenient src", source_hit_at_k(topk, spans, 5), "strict src", source_hit_at_k(topk, spans, 5, strict=True))
print("lenient sec", section_hit_at_k(topk, spans, 5), "strict sec", section_hit_at_k(topk, spans, 5, strict=True))
print("slots", slots_satisfied(topk, spans, 5), "fraction", slot_fraction_at_k(topk, spans, 5))

print("== E3 MRR")
print(reciprocal_rank([C("99", 0, 5), C("99", 0, 5), C("04", 10, 60)], spans, 5))
print(reciprocal_rank([C("99", 0, 5)], spans, 5))
print("strict MRR (only alt doc 20 first):", reciprocal_rank([C("20", 0, 40), C("04", 0, 10)], spans, 5, strict=True))

print("== E4 hit@1 vs hit@5 on one-slot case")
one = [ExpectedSpan("S1", EXPECTED, "04", "H", 1, 0, 100)]
ranked = [C("07", 0, 9), C("07", 9, 20), C("04", 0, 10)]
print([section_hit_at_k(ranked, one, k) for k in (1, 3, 5)])

print("== E5 section-level duplicate rule vs source-level")
dup = C("12", 0, 30, duplicates=(("13", 0, 30),))
sp13 = [ExpectedSpan("S1", EXPECTED, "13", "H", 1, 0, 30)]
print("section", section_hit_at_k([dup], sp13, 5), "source", source_hit_at_k([dup], sp13, 5))

print("== E6 wrong span at same doc, different offsets")
print(section_hit_at_k([C("04", 100, 200)], one, 5), source_hit_at_k([C("04", 100, 200)], one, 5))

print("== E7 freeze check")
snap = "| `data/evaluation/questions/eval-v1.jsonl` SHA-256 | `%s` |" % sha256_hex(b"line\n")
print(list(frozen_hashes(snap)))
print(verify_frozen_files(snap, {"eval-v1.jsonl": b"line\n"}))
try:
    verify_frozen_files(snap, {"eval-v1.jsonl": b"line \n"})
except IntegrityError as e:
    print("IntegrityError:", str(e)[:60])
