# EPIC-05-evaluation

Status: stage A in progress. EVAL-001 (design) done 2026-09-24. Owner reviewed; independent review done; owner re-check of the cases whose ground truth changed (design §20) filled 2026-09-25 and applied in OWNER-001 (016, 024, 017 changed; strict + lenient hit rule): [design](../../specs/evaluation-dataset-design.md), [report](../../reports/execution/EVAL-001.md). OWNER-001 verified 2026-09-25. EVAL-002 (2026-09-25): 36 eval + 6 dev questions written and validated; owner approved 2026-09-26 ([sheet](../../reviews/evaluation/eval-v1-review.md)); frozen and tagged `eval-freeze-v1` (**M1 / G5A reached**; [snapshot](../../snapshots/evaluation/eval-v1.md)). Stage A done.

Target: stage A Sat 26 Sep 2026 (Phase 1); stage B Mon 28 – Tue 29 Sep 2026 (Phase 3). Deadline for the whole project: 2026-10-01.

Scope:
- Stage A: EVAL-001 designs the dataset (mix, coverage, rubric; no final questions). EVAL-002 writes ≥ 30 questions (EN + VI) with ground truth, frozen and committed before any index is built (M1).
- Stage B: EVAL-003a/b/c resumable runner + metrics (retrieval, answer, citation, latency); EVAL-004 runs, judge spot-check, evaluation report.

Deliverables and exit gates G5A/G5B: [master-plan.md](../master-plan.md#epic-05-evaluation).
