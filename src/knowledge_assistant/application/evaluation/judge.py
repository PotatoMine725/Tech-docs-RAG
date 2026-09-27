"""LLM judge (EVAL-003b §2): one call per generated answer that needs a judgement; the label is picked by the §3 table
in `metrics/mapping.py`, never by the judge.

Which records get a call (`judge_check`):
- answerable, answered → the answer check: coverage of each REQUIRED point (by id), contradiction (incl. a
  must_not_claim item), unsupported claims, and support per citation marker;
- corpus-insufficient and answered, or insufficient with a related note (`missing_information`) or related citations
  → the refusal check (owner decision D2): `presents_related_as_answer` + reason;
- anything else (a bare refusal, an answerable refusal, an error record, retrieval mode) → no call.
Answer-prompt rule 2 makes the model fill `missing_information` on almost every refusal it writes itself, so almost
every LLM refusal of a corpus-insufficient case gets a refusal check; only retrieval-gate refusals are bare.

Judge input: the dataset ground truth copied into the run record, the generated answer and its `missing_information`,
and the full `display_text` of each cited chunk, taken from the record's `retrieved` list (never re-read from files).
Output is parsed strictly: malformed JSON, a missing or mistyped field, a point id or a citation marker that is not
exactly the expected set → `judge_error` with the raw text kept; never a guessed verdict. A judgement from any model
other than the configured judge model (or from a fallback) is rejected as `judge_error` too.

Cache (`judgements.jsonl` in the run folder): key = (case_id, arm, sha256(answer), judge prompt version). A key whose
latest line is `ok` is never judged again; a `judge_error` line is retried on the next invocation. The prompt file
hash and the judge model are validity checks: an ok line with the same key but another prompt hash or model refuses
the run (JudgeCacheMismatch) instead of being reused or silently replaced. For an insufficient record `answer` is the
fixed localized message; that is safe because a run never regenerates an ok record (EVAL-003a), so one run holds one
answer per case x arm.
"""
import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from knowledge_assistant.application.evaluation.metrics.mapping import COVERAGE_VALUES, JudgeVerdict
from knowledge_assistant.application.evaluation.records import latest_records
from knowledge_assistant.core.exceptions import EvaluationError, GenerationError, LLMError
from knowledge_assistant.core.interfaces.llm import LLM, LLMRequest
from knowledge_assistant.core.interfaces.record_store import JudgementStore

ANSWER_CHECK, REFUSAL_CHECK = "answer", "refusal"
CHECKS = (ANSWER_CHECK, REFUSAL_CHECK)
OK, JUDGE_ERROR = "ok", "judge_error"
QUOTA, MAX_LLM_CALLS = "quota", "max_llm_calls"  # JudgeSummary.stopped

SECTION_MARKER = re.compile(r"^<!-- section: (answerable|refusal) -->\s*$", re.MULTILINE)
SECTION_OF_CHECK = {ANSWER_CHECK: "answerable", REFUSAL_CHECK: "refusal"}
ANSWER_PLACEHOLDERS = ("question", "expected_answer", "answer_points", "acceptable_variations", "must_not_claim",
                       "citation_criteria", "answer", "missing_information", "cited_passages")
REFUSAL_PLACEHOLDERS = ("question", "expected_answer", "acceptable_variations", "must_not_claim", "citation_criteria",
                        "insufficient", "answer", "missing_information", "cited_passages")
PLACEHOLDERS = {ANSWER_CHECK: ANSWER_PLACEHOLDERS, REFUSAL_CHECK: REFUSAL_PLACEHOLDERS}
_PLACEHOLDER = re.compile(r"\{(" + "|".join(sorted(set(ANSWER_PLACEHOLDERS + REFUSAL_PLACEHOLDERS))) + r")\}")

_COVERAGE = {"type": "string", "enum": list(COVERAGE_VALUES)}
ANSWER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "required_points": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "point": {"type": "string"}, "covered": _COVERAGE},
            "required": ["id", "point", "covered"]}},
        "contradicts_ground_truth": {"type": "boolean"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "citations": {"type": "array", "items": {
            "type": "object",
            "properties": {"marker": {"type": "integer"}, "supports_attached_claim": _COVERAGE},
            "required": ["marker", "supports_attached_claim"]}},
        "reason": {"type": "string"},
    },
    "required": ["required_points", "contradicts_ground_truth", "unsupported_claims", "citations", "reason"],
}
REFUSAL_SCHEMA: dict = {
    "type": "object",
    "properties": {"presents_related_as_answer": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["presents_related_as_answer", "reason"],
}
SCHEMAS = {ANSWER_CHECK: ANSWER_SCHEMA, REFUSAL_CHECK: REFUSAL_SCHEMA}


class JudgeOutputError(ValueError):
    """The judge's reply is not a usable verdict (recorded as judge_error, never turned into a label)."""


class JudgeCacheMismatch(EvaluationError):
    """judgements.jsonl holds an ok judgement for the same key made with another prompt file or judge model."""


# --- which records, and the cache key -------------------------------------------------------------------------

def has_related_note(record: dict) -> bool:
    """D2 "related note": a non-empty `missing_information` (same rule as the EVAL-003a feed test)."""
    return bool((record.get("missing_information") or "").strip())


def judge_check(record: dict) -> str | None:
    """ANSWER_CHECK, REFUSAL_CHECK or None (no judge call) for one run record (§3 table)."""
    if record["status"] != "ok" or record["mode"] != "full":
        return None
    if record["answerable"]:
        return None if record["insufficient"] else ANSWER_CHECK
    if record["insufficient"] and not has_related_note(record) and not record["citations"]:
        return None  # bare refusal → correct_refusal without a call
    return REFUSAL_CHECK


def answer_sha256(record: dict) -> str:
    return hashlib.sha256((record["answer"] or "").encode("utf-8")).hexdigest()


def cache_key(case_id: str, arm: str, answer_hash: str, prompt_version: str) -> tuple[str, str, str, str]:
    return case_id, arm, answer_hash, prompt_version


def entry_key(entry: dict) -> tuple[str, str, str, str]:
    return cache_key(entry["case_id"], entry["arm"], entry["answer_sha256"], entry["judge_prompt_version"])


def latest_judgements(entries: list[dict]) -> dict[tuple[str, str, str, str], dict]:
    """The last line per cache key: a retried judge_error leaves its earlier line."""
    latest: dict = {}
    for entry in entries:
        latest[entry_key(entry)] = entry
    return latest


# --- prompt ---------------------------------------------------------------------------------------------------

def parse_template(text: str) -> dict[str, str]:
    """{check: section text} from the judge prompt file (`<!-- section: answerable|refusal -->` markers)."""
    parts = SECTION_MARKER.split(text)
    sections = {parts[i]: parts[i + 1].strip() + "\n" for i in range(1, len(parts) - 1, 2)}
    templates = {}
    for check, name in SECTION_OF_CHECK.items():
        if name not in sections:
            raise ValueError(f"judge prompt lacks the section <!-- section: {name} -->")
        missing = [p for p in PLACEHOLDERS[check] if "{" + p + "}" not in sections[name]]
        if missing:
            raise ValueError(f"judge prompt section {name} lacks placeholders {missing}")
        templates[check] = sections[name]
    return templates


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "(none)"


def _points(record: dict) -> str:
    return "\n".join(f"- {point['id']} ({'required' if point['required'] else 'optional, context only'}): "
                     f"{point['text']}" for point in record["answer_points"]) or "(none)"


def cited_passages(record: dict) -> list[tuple[int, dict]]:
    """(marker, retrieved chunk entry) per citation, in citation order. A citation whose chunk is not among the
    retrieved chunks is a runner bug and raises."""
    by_id = {chunk["chunk_id"]: chunk for chunk in record["retrieved"]}
    missing = [c["chunk_id"] for c in record["citations"] if c["chunk_id"] not in by_id]
    if missing:
        raise EvaluationError(f"{record['case_id']}: cited chunks not in the retrieved list: {missing}")
    return [(citation["marker"], by_id[citation["chunk_id"]]) for citation in record["citations"]]


def _passages(record: dict) -> str:
    return "\n\n".join(f"[{marker}] #{chunk['source_id']} — {chunk['heading_path']}\n{chunk['display_text'].strip()}"
                       for marker, chunk in cited_passages(record)) or "(no citations)"


def build_judge_prompt(templates: dict[str, str], check: str, record: dict) -> str:
    """One regex pass, like the answer prompt: braces inside inserted text are copied unchanged."""
    values = {
        "question": record["question"],
        "expected_answer": record["expected_answer"] or "(none)",
        "answer_points": _points(record),
        "acceptable_variations": _bullets(record["acceptable_variations"]),
        "must_not_claim": _bullets(record["must_not_claim"]),
        "citation_criteria": _bullets(record["citation_criteria"]),
        "insufficient": "yes" if record["insufficient"] else "no",
        "answer": record["answer"] or "(empty)",
        "missing_information": (record["missing_information"] or "").strip() or "(none)",
        "cited_passages": _passages(record),
    }
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], templates[check])


# --- parsing --------------------------------------------------------------------------------------------------

def _require(condition: bool, message: str) -> None:
    if not condition:
        raise JudgeOutputError(message)


def _is_str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def parse_verdict(check: str, text: str, record: dict) -> dict:
    """The judge's JSON, validated against the record; raises JudgeOutputError, never fills a gap."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError) as error:
        raise JudgeOutputError(f"not JSON: {error}") from error
    _require(isinstance(data, dict), "the reply is not a JSON object")
    _require(isinstance(data.get("reason"), str), "missing or non-string 'reason'")
    if check == REFUSAL_CHECK:
        _require(type(data.get("presents_related_as_answer")) is bool, "missing or non-boolean 'presents_related_as_answer'")
        return {"presents_related_as_answer": data["presents_related_as_answer"], "reason": data["reason"]}

    _require(type(data.get("contradicts_ground_truth")) is bool, "missing or non-boolean 'contradicts_ground_truth'")
    _require(_is_str_list(data.get("unsupported_claims")), "missing or malformed 'unsupported_claims'")
    points, citations = data.get("required_points"), data.get("citations")
    _require(isinstance(points, list) and all(isinstance(p, dict) for p in points), "missing or malformed 'required_points'")
    _require(isinstance(citations, list) and all(isinstance(c, dict) for c in citations), "missing or malformed 'citations'")

    required_ids = [point["id"] for point in record["answer_points"] if point["required"]]
    got_ids = [point.get("id") for point in points]
    _require(sorted(map(str, got_ids)) == sorted(required_ids) and len(set(got_ids)) == len(got_ids),
             f"required point ids {got_ids} are not exactly {required_ids}")
    _require(all(point.get("covered") in COVERAGE_VALUES for point in points), "a 'covered' value is not yes/partial/no")

    markers = [citation["marker"] for citation in record["citations"]]
    got_markers = [citation.get("marker") for citation in citations]
    _require(all(type(m) is int for m in got_markers) and sorted(got_markers) == sorted(markers)
             and len(set(got_markers)) == len(got_markers),
             f"citation markers {got_markers} are not exactly {markers}")
    _require(all(c.get("supports_attached_claim") in COVERAGE_VALUES for c in citations),
             "a 'supports_attached_claim' value is not yes/partial/no")

    by_id = {point["id"]: point for point in points}
    by_marker = {citation["marker"]: citation for citation in citations}
    return {
        "required_points": [{"id": pid, "point": str(by_id[pid].get("point", "")), "covered": by_id[pid]["covered"]}
                            for pid in required_ids],
        "contradicts_ground_truth": data["contradicts_ground_truth"],
        "unsupported_claims": list(data["unsupported_claims"]),
        "citations": [{"marker": m, "supports_attached_claim": by_marker[m]["supports_attached_claim"]} for m in markers],
        "reason": data["reason"],
    }


def to_judge_verdict(entry: dict) -> JudgeVerdict:
    """The mapping's input from an ok judgement line (required points in dataset order)."""
    if entry.get("status") != OK:
        raise ValueError("only an ok judgement has a verdict")
    verdict = entry["verdict"]
    if entry["check"] == REFUSAL_CHECK:
        return JudgeVerdict(presents_related_as_answer=verdict["presents_related_as_answer"])
    return JudgeVerdict(
        required_points=tuple(point["covered"] for point in verdict["required_points"]),
        contradicts_ground_truth=verdict["contradicts_ground_truth"],
        unsupported_claims=tuple(verdict["unsupported_claims"]),
    )


# --- the use case ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class JudgeConfig:
    model: str  # JUDGE_MODEL from config; the only model a judgement may come from
    prompt_version: str
    prompt_sha256: str
    max_output_tokens: int


@dataclass(frozen=True)
class JudgePlan:
    need_judge: int  # records that need a judgement (answer or refusal check)
    cached: int  # of those, already judged ok with this key
    to_call: int
    no_call: int  # ok full-mode records the table labels without a judge (bare refusal, answerable refusal)
    not_scored: int  # error records and retrieval-mode records


@dataclass(frozen=True)
class JudgeSummary:
    ok: int
    errors: int
    cached: int
    llm_requests: int
    stopped: str | None
    stop_detail: str | None
    remaining: int  # records still without an ok judgement


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class JudgeRecords:
    """Judge the latest record of every case x arm of one run. Resumable: ok keys are skipped; the budget counts LLM
    requests (retries included) and is checked before each call; a quota error stops the run after recording it."""

    def __init__(self, run_id: str, split: str, config: JudgeConfig, templates: dict[str, str], llm: LLM,
                 store: JudgementStore, max_llm_calls: int, progress: Callable[[str], None] = lambda _: None,
                 clock: Callable[[], float] = time.perf_counter, now: Callable[[], str] = _utc_now) -> None:
        self._run_id = run_id
        self._split = split
        self._config = config
        self._templates = templates
        self._llm = llm
        self._store = store
        self._max_llm_calls = max_llm_calls
        self._progress = progress
        self._clock = clock
        self._now = now

    def _key(self, record: dict) -> tuple[str, str, str, str]:
        return cache_key(record["case_id"], record["arm"], answer_sha256(record), self._config.prompt_version)

    def _cache(self) -> dict:
        latest = latest_judgements(self._store.read_judgements())
        for key, entry in latest.items():
            if key[3] != self._config.prompt_version or entry["status"] != OK:
                continue
            if entry["judge_prompt_sha256"] != self._config.prompt_sha256 or entry["judge_model"] != self._config.model:
                raise JudgeCacheMismatch(
                    f"{entry['case_id']} arm {entry['arm']}: judgements.jsonl has an ok judgement for prompt version "
                    f"{key[3]} made with prompt sha256 {entry['judge_prompt_sha256'][:12]} and model {entry['judge_model']}; "
                    f"now {self._config.prompt_sha256[:12]} and {self._config.model}. Bump the prompt version or use "
                    f"another run folder; judgements are never mixed or overwritten")
        return latest

    def plan(self, records: list[dict]) -> JudgePlan:
        latest = list(latest_records(records).values())
        cache = self._cache()
        need = [r for r in latest if judge_check(r)]
        cached = sum(1 for r in need if cache.get(self._key(r), {}).get("status") == OK)
        no_call = sum(1 for r in latest if r["status"] == "ok" and r["mode"] == "full" and not judge_check(r))
        return JudgePlan(len(need), cached, len(need) - cached, no_call, len(latest) - len(need) - no_call)

    def run(self, records: list[dict]) -> JudgeSummary:
        cache = self._cache()
        need = [r for r in latest_records(records).values() if judge_check(r)]
        ok = errors = cached = requests = 0
        stopped = detail = None
        for number, record in enumerate(need, start=1):
            key = self._key(record)
            if cache.get(key, {}).get("status") == OK:
                cached += 1
                continue
            if requests >= self._max_llm_calls:
                stopped, detail = MAX_LLM_CALLS, f"--max-llm-calls {self._max_llm_calls} reached"
                break
            entry, spent, quota = self._judge(record, key)
            requests += spent
            self._store.append_judgement(entry)
            cache[key] = entry
            if entry["status"] == OK:
                ok += 1
            else:
                errors += 1
            self._progress(f"[{number}/{len(need)}] {record['case_id']} {record['arm']} {entry['check']}: "
                           f"{entry['status']}" + (f" ({entry['error_type']})" if entry["status"] != OK else ""))
            if quota:
                stopped, detail = QUOTA, entry["error"]
                break
        remaining = sum(1 for r in need if cache.get(self._key(r), {}).get("status") != OK)
        return JudgeSummary(ok, errors, cached, requests, stopped, detail, remaining)

    def _judge(self, record: dict, key: tuple) -> tuple[dict, int, bool]:
        """(judgement line, LLM requests spent, stop for quota)."""
        check = judge_check(record)
        entry = {
            "run_id": self._run_id, "case_id": record["case_id"], "arm": record["arm"], "mode": record["mode"],
            "split": self._split, "check": check, "answer_sha256": key[2], "judge_prompt_version": key[3],
            "judge_prompt_sha256": self._config.prompt_sha256, "judge_model": self._config.model,
            "status": JUDGE_ERROR, "verdict": None, "error": None, "error_kind": None, "error_type": None,
            "raw_text": None, "model_used": None, "retry_count": None, "fallback_used": None, "prompt_tokens": None,
            "output_tokens": None, "thoughts_tokens": None,
            "latency_ms": {"generate": None, "retry_wait": None, "throttle_wait": None, "total": None},
            "started_at": self._now(), "finished_at": None,
        }
        prompt = build_judge_prompt(self._templates, check, record)
        request = LLMRequest(prompt=prompt, response_schema=SCHEMAS[check], temperature=0.0,
                             max_output_tokens=self._config.max_output_tokens)
        start = self._clock()
        try:
            response = self._llm.generate(request)
        except LLMError as error:
            entry.update(error=str(error), error_kind=error.kind, error_type=type(error).__name__,
                         retry_count=error.retry_count, finished_at=self._now())
            entry["latency_ms"]["total"] = (self._clock() - start) * 1000.0
            return entry, error.retry_count + 1 + int(error.fallback_attempted), error.kind == QUOTA
        except GenerationError as error:
            entry.update(error=str(error), error_kind="other", error_type=type(error).__name__,
                         raw_text=error.raw_text, finished_at=self._now())
            entry["latency_ms"]["total"] = (self._clock() - start) * 1000.0
            return entry, 1, False
        total = (self._clock() - start) * 1000.0
        entry.update(raw_text=response.text, model_used=response.model_used, retry_count=response.retry_count,
                     fallback_used=response.fallback_used, prompt_tokens=response.prompt_tokens,
                     output_tokens=response.output_tokens, thoughts_tokens=response.thoughts_tokens,
                     latency_ms={"generate": response.latency_ms, "retry_wait": response.retry_wait_ms,
                                 "throttle_wait": response.throttle_wait_ms, "total": total},
                     finished_at=self._now())
        spent = response.retry_count + 1 + int(response.fallback_used)
        if response.model_used != self._config.model or response.fallback_used:
            entry.update(error=f"judgement from {response.model_used} (fallback_used={response.fallback_used}), "
                               f"not the judge model {self._config.model}: rejected",
                         error_kind="other", error_type="JudgeModelMismatch")
            return entry, spent, False
        try:
            entry["verdict"] = parse_verdict(check, response.text, record)
        except JudgeOutputError as error:
            entry.update(error=str(error), error_kind="other", error_type="JudgeOutputError")
            return entry, spent, False
        entry.update(status=OK, raw_text=None)
        return entry, spent, False
