"""Run the evaluation questions through one arm and record what came out (EVAL-003a). Generation only: no scoring.

One `RunEvaluation` is one run = one arm x one mode (`retrieval`: embeddings and search only, no LLM; `full`: the whole
pipeline) over one split. It writes a record per case through a `RecordStore` and is built to be stopped and resumed:
- resume: a case whose latest record is `ok` is skipped, an `error` one is retried (its earlier line stays);
- it refuses to resume when the recorded settings differ from the current ones, so one run never mixes settings
  (git commit, dirty flag and times are not settings: each invocation records its own);
- model purity: an answer from the fallback model or from any model but the run's answer model is a bug. It is written
  to the error log (not to the records) and aborts the run;
- quota: the LLM budget counts requests, retries included, and is checked before each case; a quota error (LLM or
  embedding) records that one case as an error and stops the run without touching the rest, so a resume finishes it;
  any other provider failure is recorded and the run goes on. A bug (any other exception) aborts.
"""
import math
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from knowledge_assistant.application.evaluation.records import (
    LATENCY_STAGES,
    assemble,
    chunk_entry,
    citation_entry,
    latest_records,
    record_key,
)
from knowledge_assistant.application.generation.answer_question import AnswerQuestion
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.core.exceptions import (
    EmbeddingError,
    EvaluationError,
    GenerationError,
    LLMError,
    ModelPurityError,
    QuotaExhaustedError,
    RetrievalError,
    RunConfigMismatch,
)
from knowledge_assistant.core.interfaces.record_store import RecordStore

ARMS = ("A", "B")
RETRIEVAL, FULL = "retrieval", "full"
MODES = (RETRIEVAL, FULL)
SPLITS = ("eval", "dev")
SCHEMA_VERSION = 1

QUOTA, MAX_LLM_CALLS, ABORTED = "quota", "max_llm_calls", "aborted"  # RunSummary.stopped
CASE_ERRORS = (LLMError, GenerationError, EmbeddingError, RetrievalError)  # a case fails; anything else is a bug


@dataclass(frozen=True)
class RunConfig:
    """Everything that decides what a record means. Recorded in run.json and compared on resume."""

    arm: str
    mode: str
    split: str
    answer_model: str
    fallback_model: str
    allow_fallback: bool
    embedding_model: str
    embedding_dim: int
    throttle_rpm: int
    threshold: float
    prompt_version: str
    prompt_sha256: str  # of the template file: an edited prompt under the same version name is a different run
    top_k: int
    overfetch: int
    freeze_tag: str
    freeze_tag_commit: str
    question_files: dict[str, str]  # file name -> SHA-256 (both files, whichever split runs)

    def __post_init__(self) -> None:
        if self.arm not in ARMS:
            raise ValueError(f"arm must be one of {ARMS}, got {self.arm!r}")
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {self.mode!r}")
        if self.split not in SPLITS:
            raise ValueError(f"split must be one of {SPLITS}, got {self.split!r}")
        if self.allow_fallback:
            raise ValueError("evaluation runs never use the fallback model (allow_fallback must be false): "
                             "every answer must come from the one answer model")
        if not math.isfinite(self.threshold):
            raise ValueError(f"threshold must be a finite number (a disabled gate is never evaluated), got {self.threshold}")
        if self.top_k < 1 or self.overfetch < 0 or self.throttle_rpm < 1:
            raise ValueError("top_k and throttle_rpm must be at least 1 and overfetch at least 0")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RunEnvironment:
    """Where an invocation ran. Recorded per invocation, never compared."""

    git_commit: str
    git_dirty: bool
    git_dirty_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    selected: int  # cases passed to run()
    skipped: int  # already ok before this invocation
    ok: int  # ok in this invocation
    errors: int  # recorded as error in this invocation
    llm_requests: int  # requests spent in this invocation (retries included)
    stopped: str | None  # QUOTA | MAX_LLM_CALLS | None
    stop_detail: str | None
    remaining: int  # selected cases without an ok record afterwards
    answerable_refused_by_gate: tuple[str, ...]  # ok records of the whole run: answerable, top-1 below the threshold


@dataclass(frozen=True)
class RunEstimate:
    """What a run is expected to cost, worked out before it starts without spending anything."""

    mode: str
    selected: int
    already_ok: int
    to_run: int
    answerable: int  # ground truth, of the cases to run
    insufficient: int
    uncached_embeddings: int  # unique query texts not in the embedding cache: each costs one embedding request
    gated_known: int  # cached questions whose top-1 is below the threshold: the gate answers, no LLM request
    llm_requests_min: int  # cached questions that pass the gate
    llm_requests_max: int  # every case that is not known to be gated (the unknown ones might still be gated)
    throttle_rpm: int

    def lines(self, rpd: int) -> list[str]:
        lines = [
            f"cases: {self.selected} selected, {self.already_ok} already ok, {self.to_run} to run "
            f"({self.answerable} answerable, {self.insufficient} corpus-insufficient)",
            f"query embeddings: {self.uncached_embeddings} not cached = up to {self.uncached_embeddings} embedding "
            f"requests, once (the other arm reuses them from the cache)",
        ]
        if self.mode == RETRIEVAL:
            return lines + ["LLM requests: 0 (retrieval mode calls no LLM)"]
        unknown = self.llm_requests_max - self.llm_requests_min
        lines += [
            f"LLM requests: {self.llm_requests_min} to {self.llm_requests_max} (the gate stops {self.gated_known} "
            f"known case(s); {unknown} case(s) with uncached queries are unknown until retrieved; retries not counted)",
            f"time at {self.throttle_rpm} RPM: at least {self.llm_requests_max / self.throttle_rpm:.1f} min "
            f"for {self.llm_requests_max} requests",
            f"quota: up to {self.llm_requests_max} of {rpd} requests per day "
            f"({100 * self.llm_requests_max / rpd:.1f} %); other use of the same key today is not counted",
        ]
        return lines


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def error_kind_and_model(error: Exception) -> tuple[str, str | None]:
    """(quota | unavailable | other, the model that failed). Only an LLM error names a model."""
    if isinstance(error, LLMError):
        return error.kind, error.model
    if isinstance(error, QuotaExhaustedError):
        return "quota", None
    return "other", None


def requests_spent(error: Exception) -> int:
    """LLM requests a failed case cost, as far as the error tells: the answer model's attempts, plus the fallback's."""
    if isinstance(error, LLMError):
        return error.retry_count + 1 + (1 if error.fallback_attempted else 0)
    if isinstance(error, GenerationError):
        return 1  # a response arrived but was unusable; retries inside the call are not visible
    return 0


@dataclass
class _Tally:
    skipped: int = 0
    ok: int = 0
    errors: int = 0
    requests: int = 0
    stopped: str | None = None
    detail: str | None = None


class RunEvaluation:
    def __init__(
        self,
        run_id: str,
        config: RunConfig,
        store: RecordStore,
        retriever: Retriever,
        answerer: AnswerQuestion | None = None,
        *,
        max_llm_calls: int = 200,
        clock: Callable[[], float] = time.perf_counter,
        now: Callable[[], datetime] = _utc_now,
        progress: Callable[[str], None] | None = None,
        stats: Callable[[], dict] | None = None,
    ) -> None:
        if config.mode == FULL and answerer is None:
            raise ValueError("full mode needs an answerer (AnswerQuestion)")
        if answerer is not None and answerer.threshold != config.threshold:
            raise ValueError(f"the answerer's gate threshold {answerer.threshold} differs from the configured "
                             f"threshold {config.threshold}")
        if max_llm_calls < 0:
            raise ValueError(f"max_llm_calls must be >= 0, got {max_llm_calls}")
        self._run_id = run_id
        self._config = config
        self._store = store
        self._retriever = retriever
        self._answerer = answerer
        self._max_llm_calls = max_llm_calls
        self._clock = clock
        self._now = now
        self._progress = progress or (lambda line: None)
        self._stats = stats

    # --- estimate ---------------------------------------------------------------------------------------------

    def estimate(self, cases: list[dict], missing_embeddings: Callable[[list[str]], list[str]]) -> RunEstimate:
        """Cost of running `cases` now. `missing_embeddings(questions)` returns the unique texts not in the cache.

        Questions whose embedding is cached are retrieved for real (no API request) to see whether the gate stops
        them; the others stay unknown. Nothing is spent and nothing is written. Like `run`, it refuses a run whose
        recorded settings differ (a finished run has nothing left to run, so this is where the caller learns of it).
        """
        self._check_resumable(self._store.read_manifest())
        done = self._ok_keys()
        pending = [case for case in cases if self._key(case) not in done]
        missing = set(missing_embeddings([case["question"] for case in pending])) if pending else set()
        gated = predicted = 0
        if self._config.mode == FULL:
            for case in pending:
                if case["question"] in missing:
                    continue
                try:
                    top1 = self._retriever.retrieve(case["question"]).chunks[0].score
                except (EmbeddingError, RetrievalError):
                    continue
                if top1 < self._config.threshold:
                    gated += 1
                else:
                    predicted += 1
        full = self._config.mode == FULL
        return RunEstimate(
            mode=self._config.mode,
            selected=len(cases),
            already_ok=len(cases) - len(pending),
            to_run=len(pending),
            answerable=sum(1 for case in pending if case["answerable"]),
            insufficient=sum(1 for case in pending if not case["answerable"]),
            uncached_embeddings=len(missing),
            gated_known=gated,
            llm_requests_min=predicted if full else 0,
            llm_requests_max=len(pending) - gated if full else 0,
            throttle_rpm=self._config.throttle_rpm,
        )

    # --- run --------------------------------------------------------------------------------------------------

    def run(self, cases: list[dict], environment: RunEnvironment) -> RunSummary:
        manifest, invocation = self._open(environment)
        tally = _Tally()
        try:
            self._process(cases, tally)
        except BaseException as error:  # a crash or Ctrl-C still leaves a closed invocation; the error goes on
            tally.stopped, tally.detail = ABORTED, f"{type(error).__name__}: {error}"
            raise
        finally:
            self._close(manifest, invocation, tally, len(cases))
        final = latest_records(self._store.read_records())
        return RunSummary(
            run_id=self._run_id,
            selected=len(cases),
            skipped=tally.skipped,
            ok=tally.ok,
            errors=tally.errors,
            llm_requests=tally.requests,
            stopped=tally.stopped,
            stop_detail=tally.detail,
            remaining=sum(1 for case in cases if final.get(self._key(case), {}).get("status") != "ok"),
            answerable_refused_by_gate=tuple(
                key[0] for key, record in final.items()
                if record["status"] == "ok" and record["answerable"] and record["gate_fired"]
            ),
        )

    def _process(self, cases: list[dict], tally: _Tally) -> None:
        done = self._ok_keys()
        for position, case in enumerate(cases, start=1):
            label = f"[{position}/{len(cases)}] {case['id']} {case['language']}"
            if self._key(case) in done:
                tally.skipped += 1
                self._progress(f"{label} skipped (already ok)")
                continue
            if self._config.mode == FULL and tally.requests >= self._max_llm_calls:
                tally.stopped, tally.detail = MAX_LLM_CALLS, f"{tally.requests} of {self._max_llm_calls} LLM requests used"
                return
            started = self._clock()
            record, error, spent = self._run_case(case)
            tally.requests += spent
            self._store.append_record(record)
            status = record["status"]
            if status == "ok":
                tally.ok += 1
            else:
                tally.errors += 1
                status = f"error({record['error_kind']})"
            self._progress(f"{label} {status} {self._clock() - started:.1f}s")
            if error is not None and record["error_kind"] == "quota":
                tally.stopped, tally.detail = QUOTA, str(error)
                return

    def _run_case(self, case: dict) -> tuple[dict, Exception | None, int]:
        """(record, the case error or None, LLM requests spent). Lets bugs, the purity abort and Ctrl-C through."""
        config = self._config
        started_at = self._stamp()
        started = self._clock()
        error: Exception | None = None
        try:
            generated, spent = self._generate(case)
            error_fields = None
        except CASE_ERRORS as caught:
            error, spent = caught, requests_spent(caught)
            kind, model = error_kind_and_model(caught)
            error_fields = {"error": str(caught), "error_kind": kind, "error_model": model,
                            "error_type": type(caught).__name__}
            generated = {
                "llm_called": isinstance(caught, (LLMError, GenerationError)),
                "retry_count": caught.retry_count if isinstance(caught, LLMError) else 0,
                "latency_ms": {**dict.fromkeys(LATENCY_STAGES), "total": (self._clock() - started) * 1000.0},
                "prompt_version": config.prompt_version if config.mode == FULL else None,
            }
            self._store.append_error({
                "type": "case_error", "run_id": self._run_id, "case_id": case["id"], "arm": config.arm,
                "mode": config.mode, "at": self._stamp(), "error_kind": kind, "error_model": model,
                "error_type": type(caught).__name__, "message": str(caught),
                "retry_count": generated["retry_count"], "provider_body": getattr(caught, "provider_body", None),
                "raw_text": getattr(caught, "raw_text", None),
            })
        record = assemble(self._run_id, case, config.arm, config.mode, "error" if error else "ok", started_at,
                          self._stamp(), generated, error_fields)
        return record, error, spent

    def _generate(self, case: dict) -> tuple[dict, int]:
        """The generated fields of one case and the LLM requests it cost."""
        question = case["question"]
        if self._config.mode == RETRIEVAL:
            start = self._clock()
            result = self._retriever.retrieve(question)
            latency = dict.fromkeys(LATENCY_STAGES)
            latency.update(result.latency_ms, total=(self._clock() - start) * 1000.0)
            return {**self._retrieval_fields(result.chunks, result.duplicates_dropped), "latency_ms": latency}, 0

        answer = self._answerer.ask(question)
        fields = self._retrieval_fields(answer.retrieved, answer.duplicates_dropped)
        llm = answer.llm
        if fields["gate_fired"] != (llm is None):
            raise EvaluationError(
                f"{case['id']}: the gate decision ({fields['gate_fired']}) and the LLM call ({llm is not None}) "
                f"disagree; the runner and the answerer do not share one threshold"
            )
        if llm is not None and (llm.fallback_used or llm.model_used != self._config.answer_model):
            self._store.append_error({
                "type": "model_purity", "run_id": self._run_id, "case_id": case["id"], "arm": self._config.arm,
                "mode": self._config.mode, "at": self._stamp(), "model_used": llm.model_used,
                "fallback_used": llm.fallback_used, "expected_model": self._config.answer_model,
                "answer": answer.answer, "raw_text": llm.text,
            })
            raise ModelPurityError(
                f"{case['id']}: answered by {llm.model_used!r} (fallback_used={llm.fallback_used}), but this run "
                f"allows only {self._config.answer_model!r}; the answer was not recorded and the run is aborted"
            )
        fields.update(
            llm_called=llm is not None,
            answer=answer.answer,
            insufficient=answer.insufficient,
            insufficient_reason=answer.insufficient_reason,
            missing_information=answer.missing_information,
            citations=[citation_entry(citation) for citation in answer.citations],
            dropped_markers=list(answer.dropped_markers),
            uncited_sentences=answer.uncited_sentences,
            latency_ms={stage: answer.latency_ms.get(stage) for stage in LATENCY_STAGES},
            model_used=llm.model_used if llm else None,
            retry_count=llm.retry_count if llm else 0,
            fallback_used=False,
            prompt_tokens=llm.prompt_tokens if llm else None,
            output_tokens=llm.output_tokens if llm else None,
            thoughts_tokens=llm.thoughts_tokens if llm else None,
            prompt_version=answer.prompt_version,
        )
        return fields, (llm.retry_count + 1 if llm else 0)

    def _retrieval_fields(self, chunks, duplicates_dropped: int) -> dict:
        top1 = chunks[0].score
        return {
            "retrieved": [chunk_entry(hit) for hit in chunks],
            "top1_score": top1,
            "gate_fired": top1 < self._config.threshold,
            "duplicates_dropped": duplicates_dropped,
        }

    # --- run.json ---------------------------------------------------------------------------------------------

    def _open(self, environment: RunEnvironment) -> tuple[dict, dict]:
        config = self._config.to_dict()
        manifest = self._store.read_manifest()
        stamp = self._stamp()
        if manifest is None:
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "run_id": self._run_id,
                "config": config,
                "git_commit": environment.git_commit,
                "git_dirty": environment.git_dirty,
                "git_dirty_files": list(environment.git_dirty_files),
                "started_at": stamp,
                "finished_at": None,
                "invocations": [],
            }
        else:
            self._check_resumable(manifest)
        invocation = {
            "started_at": stamp, "finished_at": None, "git_commit": environment.git_commit,
            "git_dirty": environment.git_dirty, "git_dirty_files": list(environment.git_dirty_files),
            "max_llm_calls": self._max_llm_calls, "selected": None, "skipped": None, "ok": None, "errors": None,
            "llm_requests": None, "stopped": None, "detail": None,
        }
        manifest["invocations"].append(invocation)
        self._store.write_manifest(manifest)  # written first: a killed process still leaves its invocation behind
        return manifest, invocation

    def _check_resumable(self, manifest: dict | None) -> None:
        """A recorded run continues only with the settings it started with (git state and times are not settings)."""
        if manifest is None:
            return
        config, recorded = self._config.to_dict(), manifest["config"]
        differing = sorted(key for key in config.keys() | recorded.keys() if config.get(key) != recorded.get(key))
        if manifest.get("run_id") != self._run_id or differing:
            raise RunConfigMismatch(
                f"run {self._run_id} was started with different settings, so it cannot be resumed: "
                + "; ".join(f"{key}: recorded {recorded.get(key)!r}, now {config.get(key)!r}" for key in differing)
                + " (start a new run instead)"
            )

    def _close(self, manifest: dict, invocation: dict, tally: _Tally, selected: int) -> None:
        stamp = self._stamp()
        invocation.update(
            finished_at=stamp, selected=selected, skipped=tally.skipped, ok=tally.ok, errors=tally.errors,
            llm_requests=tally.requests, stopped=tally.stopped, detail=tally.detail,
        )
        if self._stats is not None:
            invocation.update(self._stats())
        manifest["finished_at"] = stamp
        self._store.write_manifest(manifest)

    # --- helpers ----------------------------------------------------------------------------------------------

    def _key(self, case: dict) -> tuple[str, str, str]:
        return case["id"], self._config.arm, self._config.mode

    def _ok_keys(self) -> set[tuple[str, str, str]]:
        return {record_key(record) for record in latest_records(self._store.read_records()).values()
                if record["status"] == "ok"}

    def _stamp(self) -> str:
        return self._now().isoformat(timespec="milliseconds")
