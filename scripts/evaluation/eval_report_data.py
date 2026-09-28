"""EVAL-003c: shared loading and scoring glue for `make_tables.py` and `make_spot_check.py`. Offline, no I/O beyond
the local filesystem, no live Gemini calls: reads `data/evaluation/results/<run_id>/` (`run.json`, `records.jsonl`,
`judgements.jsonl`) and `data/evaluation/questions/expected-spans-v1.json`, and turns them into scored rows using the
pure functions of `application/evaluation/scoring.py` (EVAL-003b). Never re-derives a metric formula: every number a
report shows traces back to `scoring.py` or `metrics/*.py`.

`expected-spans-v1.json` covers the eval split only (EVAL-003b-pre); `scoring.score_record` therefore refuses (raises
ValueError) to score an answerable record outside it. That is correct for the real eval-split runs EVAL-004 produces,
but EVAL-003c is developed and demonstrated against the committed **dev** dry-run runs, whose answerable cases
(Q-DEV-001/002/...) are never in that file. `score_row` below recomposes `score_record`'s steps (same functions, same
order) with one added guard: an answerable record without span coverage is scored for `answer` (which needs no spans)
but not for `retrieval` or `citation` (which do), and is flagged `spans_unavailable` so a report caption can list it
as excluded, and why. When every case_id is covered (the eval split), `score_row` and `score_record` agree exactly.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _extra in (PROJECT_ROOT / "src", PROJECT_ROOT):  # "src" for knowledge_assistant.*; the root for scripts.* (retrieval.py imports scripts.evaluation.validate_questions)
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from knowledge_assistant.application.evaluation.judge import latest_judgements  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.retrieval import chunk_index  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.spans import spans_from_entry  # noqa: E402
from knowledge_assistant.application.evaluation.records import latest_records  # noqa: E402
from knowledge_assistant.core.exceptions import EvaluationError  # noqa: E402
from knowledge_assistant.infrastructure.persistence.jsonl_record_store import JsonlRecordStore  # noqa: E402

RESULTS_DIR = Path("data/evaluation/results")
SPANS_FILE = Path("data/evaluation/questions/expected-spans-v1.json")
PRICING_FILE = Path("config/pricing.json")


def _no_redact(text: str) -> str:
    return text


def run_split(manifest: dict, records: list[dict]) -> str:
    """The run's split: from each record, or (pre-fix records that predate the field) from `run.json`'s config.

    Copied from `scripts/evaluation/judge_run.py::run_split` (not imported: that module also builds a live LLM and
    pulls in the Gemini adapter package, which this offline, report-only module must never import — EVAL-003c is a
    zero-Gemini-request task). Behaviour is identical.
    """
    split = manifest["config"]["split"]
    other = sorted({record["split"] for record in records if record.get("split") not in (None, split)})
    if other:
        raise EvaluationError(f"records carry split {other}, run.json says {split!r}")
    return split


class RunNotFoundError(EvaluationError):
    """No `run.json` for the given run id."""


def load_run(run_id: str, root: Path = PROJECT_ROOT) -> dict:
    """One run folder: manifest, latest record per (case_id, arm, mode), split, and latest judgement per cache key."""
    store = JsonlRecordStore(root / RESULTS_DIR / run_id, redact=_no_redact)
    manifest = store.read_manifest()
    if manifest is None:
        raise RunNotFoundError(f"no run {run_id} ({RESULTS_DIR.as_posix()}/{run_id}/run.json missing)")
    records = store.read_records()
    latest = sorted(latest_records(records).values(), key=lambda r: (r["case_id"], r["arm"], r["mode"]))
    split = run_split(manifest, records)
    judgement_lines = sorted(latest_judgements(store.read_judgements()).values(),
                             key=lambda j: (j["case_id"], j["arm"], j["check"]))
    return {"run_id": run_id, "manifest": manifest, "raw_count": len(records), "records": latest, "split": split,
            "judgement_lines": judgement_lines}


def load_runs(run_ids: list[str], root: Path = PROJECT_ROOT) -> list[dict]:
    return [load_run(run_id, root) for run_id in run_ids]


def build_chunk_indexes(runs: list[dict]) -> dict[str, dict]:
    """{arm: chunk_index} built from the union of every chunk retrieved anywhere in the given runs (grouped by arm,
    since a chunk id encodes the chunking scheme). This resolves `duplicate_chunk_ids` for any duplicate that was
    itself retrieved by some other case in the same runs; one that was never retrieved by anything cannot be resolved
    this way and `RankedChunk.from_record` raises (never a silently skipped duplicate) - a full corpus chunk index
    would remove that limitation, but no such file is produced by this project outside ChromaDB itself."""
    by_arm: dict[str, list[dict]] = {}
    for run in runs:
        arm = run["manifest"]["config"]["arm"]
        entries = by_arm.setdefault(arm, [])
        for record in run["records"]:
            for chunk in record["retrieved"]:
                entries.append({"chunk_id": chunk["chunk_id"], "source_id": chunk["source_id"],
                                "char_start": chunk["char_start"], "char_end": chunk["char_end"]})
    return {arm: chunk_index(entries) for arm, entries in by_arm.items()}


def load_spans_by_case(root: Path = PROJECT_ROOT) -> dict[str, list]:
    """{case_id: [ExpectedSpan, ...]} for every answerable case in `expected-spans-v1.json` (eval split only)."""
    data = json.loads((root / SPANS_FILE).read_text(encoding="utf-8"))
    return {case_id: spans_from_entry(entry) for case_id, entry in data["cases"].items() if entry["answerable"]}


def load_pricing(root: Path = PROJECT_ROOT) -> dict:
    return json.loads((root / PRICING_FILE).read_text(encoding="utf-8"))


def score_row(record: dict, spans_by_case: dict, index: dict | None, judgements: dict, prompt_version: str | None) -> dict:
    """One row: identity, breakdown dimensions and every per-record score - `scoring.score_record`'s own fields, plus
    `spans_unavailable`. See the module docstring for why this recomposes score_record instead of calling it."""
    tags = record["tags"]
    row = {"case_id": record["case_id"], "arm": record["arm"], "mode": record["mode"], "status": record["status"],
           "language": record["language"], "parallel_group_id": record["parallel_group_id"],
           "answerable": record["answerable"], "size_class": tags.get("size_class"),
           "difficulty": tags.get("difficulty"), "failure_mode": tags.get("failure_mode"),
           "retrieval": None, "duplicate_rule_changed": None, "answer": None, "citation": None,
           "spans_unavailable": False}
    if record["status"] != "ok":
        return row
    has_spans = (not record["answerable"]) or (record["case_id"] in spans_by_case)
    row["spans_unavailable"] = record["answerable"] and not has_spans
    if record["answerable"] and has_spans:
        spans = spans_by_case[record["case_id"]]
        row["retrieval"] = scoring.retrieval_scores(record, spans, index)
        row["duplicate_rule_changed"] = scoring.duplicate_rule_changes(scoring.ranked_chunks(record, index), spans)
    if record["mode"] == "full":
        judgement = scoring.find_judgement(record, judgements, prompt_version)
        row["answer"] = scoring.answer_scores(record, judgement)
        if has_spans:
            row["citation"] = scoring.citation_scores(record, spans_by_case.get(record["case_id"]), index, judgement)
    return row


def judgements_and_prompt_version(judgement_lines: list[dict]) -> tuple[dict, str | None]:
    """({cache_key: judgement}, the one judge prompt version present) - `None` when there are no judgements to key by
    (a run judged with more than one prompt version would break `judgements.jsonl`'s own cache-mismatch guard, so
    this never happens for a real run; if it somehow did, no judgement would be found, which is the safe direction)."""
    versions = sorted({line["judge_prompt_version"] for line in judgement_lines})
    prompt_version = versions[0] if len(versions) == 1 else None
    keyed = {(line["case_id"], line["arm"], line["answer_sha256"], line["judge_prompt_version"]): line
            for line in judgement_lines}
    return keyed, prompt_version


def score_run_pairs(run: dict, spans_by_case: dict, index: dict | None) -> list[tuple[dict, dict]]:
    """[(record, row), ...] for one run, in the run's own (case_id, arm, mode) order. `row` carries `run_id` and the
    record's `split` (resolved) besides `score_row`'s fields; the record is kept alongside it so a caller (the CSV
    writer) can read ground-truth fields (`question`, `expected_answer`, ...) that never enter the scored row."""
    judgements, prompt_version = judgements_and_prompt_version(run["judgement_lines"])
    pairs = []
    for record in run["records"]:
        row = score_row(record, spans_by_case, index, judgements, prompt_version)
        pairs.append((record, {**row, "run_id": run["run_id"], "split": record.get("split") or run["split"]}))
    return pairs


def score_runs(runs: list[dict], spans_by_case: dict, chunk_indexes: dict) -> list[dict]:
    """Every record of every given run, scored; each row carries its `run_id` besides `scoring.score_record`'s fields."""
    rows = []
    for run in runs:
        index = chunk_indexes.get(run["manifest"]["config"]["arm"])
        rows.extend(row for _, row in score_run_pairs(run, spans_by_case, index))
    return rows


def gate_refused_answerable(runs: list[dict]) -> list[str]:
    """`case_id:arm` of every ok, answerable record the retrieval gate refused (top-1 below threshold), across the
    given runs - the same expression `run_evaluation.py` uses for `RunSummary.answerable_refused_by_gate`."""
    return sorted(f"{record['case_id']}:{record['arm']}" for run in runs for record in run["records"]
                 if record["status"] == "ok" and record["answerable"] and record["gate_fired"])
