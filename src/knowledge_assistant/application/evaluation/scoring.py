"""Scores per record and their summaries (EVAL-003b §1 and §4). Pure: every input is parsed data, nothing is read here.

Inputs: EVAL-003a run records (read with `records.latest_records`), the judge's lines (`judge.latest_judgements`), the
expected spans (`expected-spans-v1.json` entries → `spans_from_entry`), the arm's chunk index (`retrieval.chunk_index`,
resolves `duplicate_chunk_ids`) and the parsed `config/pricing.json`. EVAL-003c turns the summaries into tables.

Rules that are easy to get wrong, all decided by the owner:
- headline retrieval numbers are lenient, strict is always next to them (`...:strict` keys); evidence_hit is per
  required point and content-level; the any-quote and alternate-only values are diagnostics (2026-09-25/26);
- the duplicate rule applies to every span/source value (2026-09-27); `duplicate_rule_changed` lists what it changed;
- a label the table needs a judge verdict for is None when the judgement is missing or a judge_error: it is counted
  as unlabelled, never guessed (`answer.unlabelled`);
- citation metrics cover answered records only; the related citations of an insufficient answer are only counted
  (`related_citation_count`). OD-12 (owner): an automatic span check (`auto_class`, section/source precision) AND the
  judge's support check (`judge_class`, support rate), reported separately.
"""
from collections.abc import Callable

from knowledge_assistant.application.evaluation.judge import (
    ANSWER_CHECK,
    OK,
    answer_sha256,
    cache_key,
    cited_passages,
    has_related_note,
    judge_check,
    to_judge_verdict,
)
from knowledge_assistant.application.evaluation.metrics.latency import summarize_values
from knowledge_assistant.application.evaluation.metrics.mapping import (
    CORRECT,
    CORRECT_REFUSAL,
    FALSE_REFUSAL,
    HALLUCINATION,
    PARTIALLY_CORRECT,
    YES,
    is_grounded,
    map_result,
    points_covered,
)
from knowledge_assistant.application.evaluation.metrics.retrieval import (
    HIT_KS,
    SECTION,
    SOURCE,
    RankedChunk,
    any_evidence_hit_at_k,
    duplicate_rule_changes,
    evidence_hit_at_k,
    evidence_hit_via_alternate_only_at_k,
    hits_any,
    reciprocal_rank,
    required_point_quotes,
    section_hit_at_k,
    slot_fraction_at_k,
    source_hit_at_k,
)
from knowledge_assistant.application.evaluation.metrics.spans import ExpectedSpan

CORRECT_EVIDENCE = "correct_evidence"
CORRECT_SOURCE_WRONG_EVIDENCE = "correct_source_wrong_evidence"
UNSUPPORTED_CITATION = "unsupported_citation"
CITATION_MISSING = "citation_missing"
CITATION_CLASSES = (CORRECT_EVIDENCE, CORRECT_SOURCE_WRONG_EVIDENCE, UNSUPPORTED_CITATION, CITATION_MISSING)
K = max(HIT_KS)  # 5, the headline cut-off
BREAKDOWNS = ("language", "arm", "size_class", "difficulty", "failure_mode")
ESTIMATE_NOTE = "estimate: list price per 1M tokens; the runs used the free tier and were not billed"


# --- per record -----------------------------------------------------------------------------------------------

def ranked_chunks(record: dict, index: dict | None) -> list[RankedChunk]:
    return [RankedChunk.from_record(chunk, index) for chunk in record["retrieved"]]


def retrieval_scores(record: dict, spans: list[ExpectedSpan], index: dict | None) -> dict:
    """§1 values of one answerable record (lenient headline, `:strict` next to it, diagnostics)."""
    chunks = ranked_chunks(record, index)
    point_quotes = required_point_quotes(record)
    quotes = [evidence["quote"] for evidence in record["evidence"]]
    scores = {}
    for k in HIT_KS:
        for strict in (False, True):
            suffix = ":strict" if strict else ""
            scores[f"source_hit@{k}{suffix}"] = source_hit_at_k(chunks, spans, k, strict)
            scores[f"section_hit@{k}{suffix}"] = section_hit_at_k(chunks, spans, k, strict)
        scores[f"evidence_hit@{k}"] = evidence_hit_at_k(chunks, point_quotes, k)
        scores[f"any_evidence_hit@{k}"] = any_evidence_hit_at_k(chunks, quotes, k)
    scores[f"slot_fraction@{K}"] = slot_fraction_at_k(chunks, spans, K)
    scores[f"source_slot_fraction@{K}"] = slot_fraction_at_k(chunks, spans, K, SOURCE)
    scores["mrr"] = reciprocal_rank(chunks, spans, K)
    scores["mrr:strict"] = reciprocal_rank(chunks, spans, K, strict=True)
    scores["source_mrr"] = reciprocal_rank(chunks, spans, K, level=SOURCE)
    scores["source_mrr:strict"] = reciprocal_rank(chunks, spans, K, level=SOURCE, strict=True)
    scores[f"evidence_hit_via_alternate_only@{K}"] = evidence_hit_via_alternate_only_at_k(chunks, point_quotes, spans, K)
    return scores


def find_judgement(record: dict, judgements: dict, prompt_version: str) -> dict | None:
    return judgements.get(cache_key(record["case_id"], record["arm"], answer_sha256(record), prompt_version))


def answer_scores(record: dict, judgement: dict | None) -> dict:
    """The §3 label, groundedness and points-covered of one full-mode ok record. `result` is None (unlabelled) when the
    table needs a judge verdict and the judgement is missing or a judge_error."""
    check = judge_check(record)
    scores = {"check": check, "judge_status": None, "result": None, "grounded": None, "points_covered": None}
    note, citations = has_related_note(record), bool(record["citations"])
    if check is None:
        scores["result"] = map_result(record["answerable"], record["insufficient"], note, citations)
        return scores
    if judgement is None or judgement["status"] != OK:
        scores["judge_status"] = "missing" if judgement is None else judgement["status"]
        return scores
    scores["judge_status"] = OK
    verdict = to_judge_verdict(judgement)
    scores["result"] = map_result(record["answerable"], record["insufficient"], note, citations, verdict)
    if check == ANSWER_CHECK:
        scores["grounded"] = is_grounded(verdict)
        scores["points_covered"] = points_covered(verdict.required_points)
    return scores


def _class(n: int, evidence: list[bool], source: list[bool]) -> str:
    if n == 0:
        return CITATION_MISSING
    if any(evidence):
        return CORRECT_EVIDENCE
    return CORRECT_SOURCE_WRONG_EVIDENCE if any(source) else UNSUPPORTED_CITATION


def citation_scores(record: dict, spans: list[ExpectedSpan] | None, index: dict | None, judgement: dict | None) -> dict:
    """Answered records: presence, precision and the two 4-way classes. Insufficient records: related count only."""
    citations = record["citations"]
    scores = {"answered": not record["insufficient"], "related_citation_count": None, "citation_count": None,
              "citation_present": None, "source_precision": None, "section_precision": None, "support_rate": None,
              "auto_class": None, "judge_class": None}
    if record["insufficient"]:
        scores["related_citation_count"] = len(citations)
        return scores
    n = len(citations)
    scores.update(citation_count=n, citation_present=n > 0)
    if not record["answerable"]:
        return scores  # no evidence to check a citation against; the refusal check judges the answer
    chunks = [RankedChunk.from_record(chunk, index) for _, chunk in cited_passages(record)]
    source_ok = [hits_any(chunk, spans, SOURCE) for chunk in chunks]
    section_ok = [hits_any(chunk, spans, SECTION) for chunk in chunks]
    if n:
        scores.update(source_precision=sum(source_ok) / n, section_precision=sum(section_ok) / n)
    scores["auto_class"] = _class(n, section_ok, source_ok)
    if judgement is not None and judgement["status"] == OK and judgement["check"] == ANSWER_CHECK:
        support = [c["supports_attached_claim"] == YES for c in judgement["verdict"]["citations"]]
        if n:
            scores["support_rate"] = sum(support) / n
        scores["judge_class"] = _class(n, support, source_ok)
    return scores


def score_record(record: dict, spans_by_case: dict[str, list[ExpectedSpan]], index: dict | None,
                 judgements: dict, prompt_version: str) -> dict:
    """One row: identity, breakdown dimensions, and every per-record score (None where it does not apply)."""
    tags = record["tags"]
    row = {"case_id": record["case_id"], "arm": record["arm"], "mode": record["mode"], "status": record["status"],
           "language": record["language"], "parallel_group_id": record["parallel_group_id"],
           "answerable": record["answerable"], "size_class": tags.get("size_class"),
           "difficulty": tags.get("difficulty"), "failure_mode": tags.get("failure_mode"),
           "retrieval": None, "duplicate_rule_changed": None, "answer": None, "citation": None}
    if record["status"] != "ok":
        return row
    if record["answerable"]:
        if record["case_id"] not in spans_by_case:
            raise ValueError(f"{record['case_id']}: no expected spans (expected-spans-v1.json covers the eval split only)")
        spans = spans_by_case[record["case_id"]]
        row["retrieval"] = retrieval_scores(record, spans, index)
        row["duplicate_rule_changed"] = duplicate_rule_changes(ranked_chunks(record, index), spans)
    if record["mode"] == "full":
        judgement = find_judgement(record, judgements, prompt_version)
        row["answer"] = answer_scores(record, judgement)
        row["citation"] = citation_scores(record, spans_by_case.get(record["case_id"]), index, judgement)
    return row


# --- summaries ------------------------------------------------------------------------------------------------

def _rate(numerator: int, denominator: int) -> dict:
    return {"n": denominator, "count": numerator, "value": numerator / denominator if denominator else None}


def _mean(values: list) -> dict:
    values = [v for v in values if v is not None]
    return {"n": len(values), "value": sum(values) / len(values) if values else None}


def summarize_retrieval(rows: list[dict]) -> dict:
    scored = [row["retrieval"] for row in rows if row["retrieval"] is not None]
    names = list(scored[0]) if scored else []
    summary = {name: _mean([scores[name] for scores in scored]) for name in names}
    alternate_only = f"evidence_hit_via_alternate_only@{K}"
    if scored:
        summary[alternate_only]["cases"] = sorted(
            row["case_id"] for row in rows if row["retrieval"] and row["retrieval"][alternate_only])
    changed = [row for row in rows if row["duplicate_rule_changed"]]
    summary["duplicate_rule_changed"] = {"n": len(scored), "count": len(changed),
                                         "cases": sorted(f"{row['case_id']}:{row['arm']}" for row in changed)}
    return summary


def summarize_answers(rows: list[dict]) -> dict:
    """Answer and refusal rates over labelled records; unlabelled records (judge missing/error) are listed apart."""
    scored = [row for row in rows if row["answer"] is not None]
    labelled = [row for row in scored if row["answer"]["result"] is not None]
    answerable = [row for row in labelled if row["answerable"]]
    unanswerable = [row for row in labelled if not row["answerable"]]

    def count(group: list[dict], *labels: str) -> int:
        return sum(1 for row in group if row["answer"]["result"] in labels)

    judged = [row["answer"] for row in answerable if row["answer"]["check"] == ANSWER_CHECK]
    return {
        "records": len(scored),
        # a runner error has no answer to label: listed so a table caption can name it (never counted as right or wrong)
        "runner_errors": sorted(f"{row['case_id']}:{row['arm']}" for row in rows if row["status"] != "ok"),
        "unlabelled": sorted(f"{row['case_id']}:{row['arm']}" for row in scored if row["answer"]["result"] is None),
        "labels": {label: count(labelled, label) for label in
                   (CORRECT, PARTIALLY_CORRECT, "incorrect", FALSE_REFUSAL, CORRECT_REFUSAL, HALLUCINATION)},
        "accuracy": _rate(count(answerable, CORRECT), len(answerable)),
        "lenient_accuracy": _rate(count(answerable, CORRECT, PARTIALLY_CORRECT), len(answerable)),
        "groundedness_rate": _rate(sum(1 for a in judged if a["grounded"]), len(judged)),
        "points_covered_mean": _mean([a["points_covered"] for a in judged]),
        "correct_refusal_rate": _rate(count(unanswerable, CORRECT_REFUSAL), len(unanswerable)),
        "hallucination_rate": _rate(count(unanswerable, HALLUCINATION), len(unanswerable)),
        "false_refusal_rate": _rate(count(answerable, FALSE_REFUSAL), len(answerable)),
    }


def summarize_citations(rows: list[dict]) -> dict:
    """Answered answerable records only; related citations of insufficient answers are just counted."""
    cited = [row["citation"] for row in rows if row["citation"] is not None]
    answered = [c for row, c in ((row, row["citation"]) for row in rows if row["citation"] is not None)
                if c["answered"] and row["answerable"]]
    judged = [c for c in answered if c["judge_class"] is not None]
    return {
        "answered": len(answered),
        "presence_rate": _rate(sum(1 for c in answered if c["citation_present"]), len(answered)),
        "source_precision": _mean([c["source_precision"] for c in answered]),
        "section_precision": _mean([c["section_precision"] for c in answered]),
        "support_rate": _mean([c["support_rate"] for c in judged]),
        "auto_class": {name: sum(1 for c in answered if c["auto_class"] == name) for name in CITATION_CLASSES},
        "judge_class": {name: sum(1 for c in judged if c["judge_class"] == name) for name in CITATION_CLASSES},
        "judge_class_n": len(judged),
        "related_citation_count": sum(c["related_citation_count"] or 0 for c in cited),
        "answered_unanswerable_with_citations": sum(
            1 for row in rows if row["citation"] and row["citation"]["answered"] and not row["answerable"]
            and row["citation"]["citation_present"]),
    }


def summarize(rows: list[dict]) -> dict:
    return {"records": len(rows), "retrieval": summarize_retrieval(rows), "answer": summarize_answers(rows),
            "citation": summarize_citations(rows)}


def breakdown(rows: list[dict], summary: Callable[[list[dict]], dict] = summarize) -> dict:
    """Every metric overall, by language, by arm, on the parallel EN/VI subset, by size class, difficulty and
    failure-mode tag."""
    result = {"overall": summary(rows),
              "parallel": summary([row for row in rows if row["parallel_group_id"]])}
    for key in BREAKDOWNS:
        values = sorted({row[key] for row in rows if row[key] is not None})
        result[key] = {value: summary([row for row in rows if row[key] == value]) for value in values}
    return result


# --- judge latency and cost -----------------------------------------------------------------------------------

def summarize_judge_latency(judgement_lines: list[dict]) -> dict:
    """Judge call latency, like the answer table: clean calls (no retry, no fallback) apart from the others."""
    timed = [line for line in judgement_lines if line["retry_count"] is not None]
    clean = [line for line in timed if line["retry_count"] == 0 and not line["fallback_used"]]
    other = [line for line in timed if line not in clean]

    def stages(lines):
        return {stage: summarize_values([line["latency_ms"][stage] for line in lines
                                         if line["latency_ms"].get(stage) is not None])
                for stage in ("generate", "total")}
    return {"main": {"count": len(clean), "stages": stages(clean)},
            "retried_or_fallback": {"count": len(other), "stages": stages(other)}}


def _tokens(items: list[dict], model_key: str) -> dict:
    calls = [item for item in items if item.get(model_key)]
    models = sorted({item[model_key] for item in calls})
    return {
        "calls": len(calls),
        "models": models,
        "prompt_tokens": sum(item["prompt_tokens"] or 0 for item in calls),
        "output_tokens": sum(item["output_tokens"] or 0 for item in calls),
        "thoughts_tokens": sum(item["thoughts_tokens"] or 0 for item in calls),
        "calls_without_prompt_tokens": sum(1 for item in calls if item["prompt_tokens"] is None),
        "calls_without_output_tokens": sum(1 for item in calls if item["output_tokens"] is None),
        "calls_without_thoughts_tokens": sum(1 for item in calls if item["thoughts_tokens"] is None),
    }


def estimate_usd(tokens: dict, pricing: dict) -> dict:
    """Prompt tokens x input price + (output + thinking tokens) x output price (the source prices output including
    thinking tokens). None, with the reason, when a model's price is null or the calls span several models."""
    if len(tokens["models"]) != 1:
        return {"usd": None, "reason": f"models {tokens['models']}: need exactly one priced model"}
    price = pricing.get("models", {}).get(tokens["models"][0])
    if not price or price.get("input_per_1m_usd") is None or price.get("output_per_1m_usd") is None:
        return {"usd": None, "reason": f"price for {tokens['models'][0]} not available"}
    usd = (tokens["prompt_tokens"] * price["input_per_1m_usd"]
           + (tokens["output_tokens"] + tokens["thoughts_tokens"]) * price["output_per_1m_usd"]) / 1_000_000
    note = ESTIMATE_NOTE
    if tokens["calls_without_thoughts_tokens"]:
        note += f"; {tokens['calls_without_thoughts_tokens']} call(s) reported no thinking-token count (counted as 0)"
    return {"usd": usd, "reason": note}


def cost_summary(records: list[dict], judgement_lines: list[dict], pricing: dict) -> dict:
    """Tokens per stage (answer, judge), per question and in total, with the estimated $ (§4)."""
    answers = [record for record in records if record["status"] == "ok" and record["llm_called"]]
    judged = [line for line in judgement_lines if line["model_used"]]
    result = {"note": ESTIMATE_NOTE, "pricing_source": pricing.get("source"), "stages": {}}
    for stage, items in (("answer", answers), ("judge", judged)):
        tokens = _tokens(items, "model_used")
        # one answer call per case x arm and one judge call per judged record, so per call = per question and arm
        per_question = {name: tokens[name] / tokens["calls"] if tokens["calls"] else None
                        for name in ("prompt_tokens", "output_tokens", "thoughts_tokens")}
        result["stages"][stage] = {**tokens, "per_question": per_question, "estimate": estimate_usd(tokens, pricing)}
    return result
