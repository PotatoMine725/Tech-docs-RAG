"""Arm A vs Arm B comparison and failure classification (EXP-001 §1-§2). Pure: parsed data in, plain data out.

Inputs are the per-record `rows` of each arm's `summary.json` (scoring.py), the runner records (EVAL-003a) and, for
chunk-level facts, the expected spans and the set of chunk ids that cut a code fence (computed by the caller from the
normalized corpus). The statistics are `stats.py`'s; nothing here re-implements a test.

Pairing: a metric is compared only over the cases where BOTH arms have a value (a label that is None - unlabelled, or
not applicable - drops the case for that metric), so every table row carries its own paired n.
Failure rules (EXP-001 §2, owner addendum 2026-09-28): see `classify_failure`.
"""
from dataclasses import dataclass, field

from knowledge_assistant.application.evaluation.metrics.latency import nearest_rank
from knowledge_assistant.application.evaluation.metrics.mapping import (
    CORRECT,
    CORRECT_REFUSAL,
    FALSE_REFUSAL,
    HALLUCINATION,
    INCORRECT,
    PARTIALLY_CORRECT,
)
from knowledge_assistant.application.evaluation.metrics.retrieval import (
    SECTION,
    RankedChunk,
    any_evidence_hit_at_k,
    hits_any,
    required_point_quotes,
)
from knowledge_assistant.application.evaluation.metrics.spans import ExpectedSpan
from knowledge_assistant.application.evaluation.stats import (
    mcnemar_exact,
    paired_bootstrap_ci,
    wilcoxon_signed_rank,
)

BINARY = "binary"
CONTINUOUS = "continuous"
DESCRIPTIVE = "descriptive"  # shown per arm, no test (e.g. latency confounded by the embedding cache)
ALPHA = 0.05

RETRIEVAL_MISS = "retrieval_miss"
CHUNKING = "chunking"
RANKING = "ranking"
REFUSAL = "refusal"
GENERATION = "generation"
CITATION = "citation"
STAGES = (RETRIEVAL_MISS, CHUNKING, RANKING, REFUSAL, GENERATION, CITATION)
LANGUAGE = "language"


# --- metric extraction ------------------------------------------------------------------------------------------

def _retrieval(name):
    return lambda row, record: None if row["retrieval"] is None else row["retrieval"][name]


def _label_is(*labels, answerable):
    def get(row, record):
        result = (row["answer"] or {}).get("result")
        if row["answerable"] != answerable or result is None:
            return None
        return int(result in labels)
    return get


def _grounded(row, record):
    grounded = (row["answer"] or {}).get("grounded")
    return None if grounded is None else int(grounded)


def _citation(name):
    return lambda row, record: None if row["citation"] is None else row["citation"][name]


def _latency(stage):
    return lambda row, record: record["latency_ms"].get(stage)


def _tokens(*fields):
    def get(row, record):
        values = [record[name] for name in fields]
        return None if any(value is None for value in values) else sum(values)
    return get


@dataclass(frozen=True)
class Metric:
    name: str
    kind: str  # BINARY | CONTINUOUS | DESCRIPTIVE
    get: object  # (summary row, runner record) -> value or None (not applicable / unlabelled)
    note: str = ""


def _retrieval_metrics() -> list[Metric]:
    metrics = []
    for level in ("source", "section"):
        for k in (1, 3, 5):
            metrics.append(Metric(f"{level}_hit@{k}", BINARY, _retrieval(f"{level}_hit@{k}")))
            metrics.append(Metric(f"{level}_hit@{k}:strict", BINARY, _retrieval(f"{level}_hit@{k}:strict")))
    metrics += [Metric(f"evidence_hit@{k}", BINARY, _retrieval(f"evidence_hit@{k}")) for k in (1, 3, 5)]
    metrics += [Metric("mrr", CONTINUOUS, _retrieval("mrr")), Metric("mrr:strict", CONTINUOUS, _retrieval("mrr:strict"))]
    return metrics


METRICS: list[Metric] = _retrieval_metrics() + [
    Metric("accuracy", BINARY, _label_is(CORRECT, answerable=True), "answerable, labelled in both arms"),
    Metric("lenient_accuracy", BINARY, _label_is(CORRECT, PARTIALLY_CORRECT, answerable=True),
           "correct or partially_correct"),
    Metric("false_refusal", BINARY, _label_is(FALSE_REFUSAL, answerable=True), "lower is better"),
    Metric("groundedness", BINARY, _grounded, "answer-checked records judged in both arms"),
    Metric("correct_refusal", BINARY, _label_is(CORRECT_REFUSAL, answerable=False), "corpus-insufficient cases"),
    Metric("hallucination", BINARY, _label_is(HALLUCINATION, answerable=False), "corpus-insufficient; lower is better"),
    Metric("citation_support_rate", CONTINUOUS, _citation("support_rate"), "judge; answered in both arms"),
    Metric("citation_section_precision", CONTINUOUS, _citation("section_precision"), "span check; answered in both"),
    Metric("latency_retrieve_ms", CONTINUOUS, _latency("retrieve")),
    Metric("latency_generate_ms", CONTINUOUS, _latency("generate"), "LLM called in both arms"),
    Metric("latency_embed_query_ms", DESCRIPTIVE, _latency("embed_query"),
           "not comparable: arm B's query embeddings were cache hits"),
    Metric("latency_total_ms", DESCRIPTIVE, _latency("total"), "not comparable: includes embed_query"),
    Metric("tokens_prompt", CONTINUOUS, _tokens("prompt_tokens"), "LLM called in both arms"),
    Metric("tokens_output", CONTINUOUS, _tokens("output_tokens"), "LLM called in both arms"),
    Metric("tokens_total", CONTINUOUS, _tokens("prompt_tokens", "output_tokens"), "LLM called in both arms"),
]


# --- pairing and one comparison row ---------------------------------------------------------------------------

def paired_values(case_ids, rows_a, rows_b, records_a, records_b, metric: Metric):
    """(case ids, A values, B values) over the cases where both arms have a value, in `case_ids` order."""
    ids, a, b = [], [], []
    for case_id in case_ids:
        value_a = metric.get(rows_a[case_id], records_a[case_id])
        value_b = metric.get(rows_b[case_id], records_b[case_id])
        if value_a is None or value_b is None:
            continue
        ids.append(case_id)
        a.append(value_a)
        b.append(value_b)
    return ids, a, b


def _mean(values):
    return sum(values) / len(values)


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def wording(p_value: float | None, n: int, delta: float) -> str:
    """EXP-001 wording rule: p >= 0.05 never names a winner."""
    if p_value is None:
        return "not tested"
    if p_value >= ALPHA:
        return f"no statistically reliable difference at n = {n}"
    return f"B {'higher' if delta > 0 else 'lower'} than A (p = {p_value:.3g}, n = {n})"


def compare(metric: Metric, ids: list[str], a: list, b: list) -> dict:
    """One table row. Binary: mean = rate, exact McNemar (b = A-only, c = B-only). Continuous: mean (and median),
    exact Wilcoxon, plus nearest-rank p50/p95 per arm. Both: paired bootstrap 95 % CI of the mean difference B - A. Descriptive: per-arm medians only."""
    row = {"metric": metric.name, "kind": metric.kind, "note": metric.note, "n": len(ids), "cases": ids}
    if not ids:
        return {**row, "a": None, "b": None, "delta": None, "ci": None, "test": None, "p": None, "wording": "no pairs"}
    if metric.kind == DESCRIPTIVE:
        return {**row, "a": _median(a), "b": _median(b), "delta": None, "ci": None, "test": None, "p": None,
                "statistic": "median", "wording": "not tested (" + metric.note + ")"}
    ci = paired_bootstrap_ci([float(x) for x in a], [float(y) for y in b])
    row.update(a=_mean(a), b=_mean(b), delta=ci.delta, ci=[ci.low, ci.high], statistic="mean")
    if metric.kind == BINARY:
        result = mcnemar_exact(a, b)
        row.update(test="mcnemar_exact", p=result.p_value, mcnemar_b=result.b, mcnemar_c=result.c,
                   a_only=[i for i, x, y in zip(ids, a, b) if x and not y],
                   b_only=[i for i, x, y in zip(ids, a, b) if y and not x])
    else:
        result = wilcoxon_signed_rank([float(x) for x in a], [float(y) for y in b])
        row.update(test="wilcoxon_exact", p=result.p_value, wilcoxon_n=result.n, zeros_dropped=result.zeros_dropped,
                   w_plus=result.w_plus, w_minus=result.w_minus, a_p50=nearest_rank(a, 50), a_p95=nearest_rank(a, 95),
                   b_p50=nearest_rank(b, 50), b_p95=nearest_rank(b, 95))
    row["wording"] = wording(row["p"], len(ids), row["delta"])
    return row


def compare_all(case_ids, rows_a, rows_b, records_a, records_b, metrics=None) -> list[dict]:
    return [compare(metric, *paired_values(case_ids, rows_a, rows_b, records_a, records_b, metric))
            for metric in (metrics or METRICS)]


# --- discordant cases -----------------------------------------------------------------------------------------

def discordant_cases(case_ids, rows_a, rows_b, records_a, records_b) -> dict[str, list[str]]:
    """{case_id: [what differs]} for every case whose answer label or groundedness (both labelled) or any retrieval
    metric (hit@k, lenient and strict, evidence hit, MRR) differs between the arms."""
    names = [metric for metric in _retrieval_metrics()]
    result = {}
    for case_id in case_ids:
        row_a, row_b = rows_a[case_id], rows_b[case_id]
        reasons = []
        label_a = (row_a["answer"] or {}).get("result")
        label_b = (row_b["answer"] or {}).get("result")
        if label_a is not None and label_b is not None and label_a != label_b:
            reasons.append(f"label {label_a} -> {label_b}")
        grounded_a, grounded_b = _grounded(row_a, None), _grounded(row_b, None)
        if grounded_a is not None and grounded_b is not None and grounded_a != grounded_b:
            reasons.append(f"grounded {grounded_a} -> {grounded_b}")
        for metric in names:
            value_a = metric.get(row_a, records_a[case_id])
            value_b = metric.get(row_b, records_b[case_id])
            if value_a != value_b:
                reasons.append(f"{metric.name} {_fmt(value_a)} -> {_fmt(value_b)}")
        if reasons:
            result[case_id] = reasons
    return result


def _fmt(value) -> str:
    return f"{value:.3g}" if isinstance(value, float) else str(value)


# --- chunk-level facts ----------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ChunkFact:
    rank: int
    chunk_id: str
    source_id: str
    heading_path: str
    score: float
    hits_section: bool | None  # None: corpus-insufficient case, no spans
    slots_hit: tuple[str, ...]  # slots whose (expected or alternate) span this chunk overlaps, lenient
    evidence_quotes_contained: int  # evidence quotes of the case contained whole (same normalization as evidence_hit)
    evidence_quotes_total: int
    points_covered: tuple[str, ...]  # required points with a supporting quote whole in this chunk (evidence_hit rule)
    cuts_code_fence: bool
    head: str  # first 200 characters of display_text


def chunk_facts(record: dict, spans: list[ExpectedSpan] | None, fence_cut_ids: set[str], index=None,
                head_chars: int = 200) -> list[ChunkFact]:
    """Per retrieved chunk of one record, in rank order."""
    quotes = [evidence["quote"] for evidence in record["evidence"]]
    point_quotes = required_point_quotes(record) if record["answerable"] else {}
    facts = []
    for chunk in record["retrieved"]:
        ranked = RankedChunk.from_record(chunk, index)
        contained = sum(any_evidence_hit_at_k([ranked], [quote], 1) for quote in quotes)
        slots = tuple(sorted({span.slot for span in spans or () if hits_any(ranked, [span], SECTION)},
                             key=lambda slot: int(slot[1:])))
        facts.append(ChunkFact(
            rank=chunk["rank"], chunk_id=chunk["chunk_id"], source_id=chunk["source_id"],
            heading_path=chunk["heading_path"], score=chunk["score"],
            hits_section=bool(slots) if spans else None, slots_hit=slots,
            evidence_quotes_contained=contained, evidence_quotes_total=len(quotes),
            points_covered=tuple(point for point, point_q in point_quotes.items()
                                 if any_evidence_hit_at_k([ranked], point_q, 1)),
            cuts_code_fence=chunk["chunk_id"] in fence_cut_ids, head=chunk["display_text"][:head_chars]))
    return facts


# --- failure classification (EXP-001 §2) -----------------------------------------------------------------------

@dataclass(frozen=True)
class Failure:
    case_id: str
    arm: str
    result: str | None
    stage: str
    rule: str  # why the rule fired, from the record fields
    secondary: tuple[str, ...] = field(default=())


def is_failure(row: dict) -> bool:
    """EXP-001 §2 trigger: result is not a success, or section hit@5 = 0. Unlabelled records are not classified."""
    result = (row["answer"] or {}).get("result")
    if result is None:
        return False
    miss = row["retrieval"] is not None and row["retrieval"]["section_hit@5"] == 0
    return result not in (CORRECT, CORRECT_REFUSAL) or miss


def classify_failure(row: dict, record: dict, facts: list[ChunkFact], threshold: float) -> Failure | None:
    """One primary stage, first rule that applies (EXP-001 §2 order, owner addendum item 4 for the gate):

    1. retrieval_miss: section hit@5 = 0 (for a two-slot case: some slot has no overlapping top-5 chunk);
    1b. refusal (gate): a false refusal where the threshold gate fired - the LLM never saw the chunks, so the gate is
        the cause (owner addendum); a chunking signal on the same record is kept as a secondary tag;
    2. chunking: section hit but evidence hit@5 = 0, or the only section-hitting top-5 chunk cuts a code fence;
    3. ranking: first section hit at rank >= 3 and the answer cites a higher-ranked chunk outside the expected spans;
    4. refusal: a false refusal by the LLM, or a hallucination;
    5. generation: the right chunk was in context but the answer is incomplete or wrong;
    6. citation: answer correct, citation missing / unsupported / wrong section. Under the §2 trigger a correct answer
       enters only with section hit@5 = 0, which rule 1 takes first, so this rule cannot fire (kept for completeness).
    """
    if not is_failure(row):
        return None
    result = row["answer"]["result"]
    retrieval = row["retrieval"]
    case_id, arm = row["case_id"], row["arm"]
    secondary = []
    if retrieval is not None and retrieval["evidence_hit@5"] == 0 and retrieval["section_hit@5"] == 1:
        secondary.append(CHUNKING)

    def failure(stage, rule, extra=()):
        return Failure(case_id, arm, result, stage, rule, tuple(tag for tag in (*secondary, *extra) if tag != stage))

    if retrieval is not None and retrieval["section_hit@5"] == 0:
        slots = retrieval.get("slot_fraction@5")
        return failure(RETRIEVAL_MISS, f"section_hit@5 = 0 (slot fraction {_fmt(slots)})")
    if result == FALSE_REFUSAL and record["gate_fired"]:
        return failure(REFUSAL, f"gate: top-1 score {record['top1_score']:.4f} < threshold {threshold}")
    hitting = [fact for fact in facts[:5] if fact.hits_section]
    if retrieval is not None and retrieval["evidence_hit@5"] == 0:
        return failure(CHUNKING, "section hit but evidence_hit@5 = 0 (no required-point quote whole in one chunk)")
    if len(hitting) == 1 and hitting[0].cuts_code_fence:
        return failure(CHUNKING, f"only section-hitting chunk {hitting[0].chunk_id} cuts a code fence")
    if hitting and hitting[0].rank >= 3:
        cited = {citation["chunk_id"] for citation in record["citations"]}
        wrong_above = [fact.chunk_id for fact in facts if fact.rank < hitting[0].rank and fact.chunk_id in cited
                       and not fact.hits_section]
        if wrong_above:
            return failure(RANKING, f"first section hit at rank {hitting[0].rank}; cites {wrong_above}")
    if result == FALSE_REFUSAL:
        return failure(REFUSAL, "LLM: answered insufficient although the gate passed")
    if result == HALLUCINATION:
        return failure(REFUSAL, "hallucination on a corpus-insufficient case")
    if result in (PARTIALLY_CORRECT, INCORRECT):
        return failure(GENERATION, f"{result}: expected section and evidence in context")
    return failure(CITATION, "correct answer with a citation defect")


def language_tag(case_id: str, rows: dict[str, dict], failures: set[str]) -> bool:
    """Secondary tag `language`: a VI case fails while its EN parallel twin (same parallel_group_id) passes."""
    row = rows[case_id]
    if row["language"] != "vi" or row["parallel_group_id"] is None or case_id not in failures:
        return False
    twins = [other for other_id, other in rows.items() if other_id != case_id
             and other["parallel_group_id"] == row["parallel_group_id"] and other["language"] == "en"]
    return any(twin["case_id"] not in failures and (twin["answer"] or {}).get("result") is not None for twin in twins)


# --- ADR-0003 expected failure modes: per-record signals ------------------------------------------------------

LINK_LIST_DOCS = ("08", "09")  # ADR-0003: link-list sections
LARGE_DOCS = ("13", "17", "23")  # ADR-0003: the version-repeating docs, ~63 % of the text after dedup


def failure_mode_signals(record: dict, k: int = 5) -> dict:
    """Counts over the top-k chunks of one record; `expected` = the case's expected and alternate source ids.

    - link_list_noise: chunks from #08/#09 when neither is expected;
    - large_doc_off_target: chunks from #13/#17/#23 when none of them is expected;
    - same_heading_repeats: k minus the distinct (source, heading path) pairs, i.e. slots taken by another variant or
      piece of a section already in the list (version variants and near-duplicates).
    """
    top = record["retrieved"][:k]
    expected = {ref["source_id"] for ref in record["expected_sources"] + record["acceptable_alternate_sources"]}
    link = [c["chunk_id"] for c in top if c["source_id"] in LINK_LIST_DOCS and c["source_id"] not in expected]
    large = [c["chunk_id"] for c in top if c["source_id"] in LARGE_DOCS and not expected & set(LARGE_DOCS)]
    distinct = {(c["source_id"], c["heading_path"]) for c in top}
    return {"sources": [c["source_id"] for c in top], "link_list_noise": link, "large_doc_off_target": large,
            "same_heading_repeats": len(top) - len(distinct)}
