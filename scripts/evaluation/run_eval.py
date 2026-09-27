"""EVAL-003a: run the evaluation questions through one arm and record what came out. Generation only: no scoring.

    python scripts/evaluation/run_eval.py --arm A|B --mode retrieval|full --split dev|eval
        [--run-id ID] [--max-llm-calls N] [--cases ID,ID] [--estimate-only]

`retrieval` mode embeds the questions and searches (no LLM); `full` mode runs the whole pipeline. Both write
`data/evaluation/results/<run_id>/`: `run.json` (settings, git state, one entry per invocation), `records.jsonl` (one
line per case, flushed as it is written) and `errors.jsonl` (failed cases, the first real 429 and 5xx bodies with the
key redacted, and any model-purity violation). Read `records.jsonl` with `records.latest_records`: a retried case
leaves its error line and its ok line.

Before it does anything else the script checks BOTH frozen question files against the hashes in
docs/snapshots/evaluation/eval-v1.md and records the eval-freeze-v1 tag. Then it prints an estimate (uncached query
embeddings, LLM requests, time at the throttle rate, share of the daily quota) and starts. Full mode always runs with
the fallback model OFF, whatever ALLOW_FALLBACK says: every answer comes from the one answer model, and a record from
any other model aborts the run.

Resume: pass an existing --run-id. Cases already ok are skipped, cases with an error are retried, and the run refuses to
continue if its recorded settings differ from the current ones. Without --run-id the id is
<YYYYMMDD>-<split>-<arm>-<mode>-<git short sha>, and an existing run with that id is NOT resumed silently.
--max-llm-calls (default 200) counts LLM requests, retries included, per invocation. A quota error (LLM or embedding)
stops the run after recording that one case; the other cases stay untouched and the resume command is printed.

Exit codes: 0 every selected case ok; 1 finished, some cases failed (a resume retries them); 2 stopped early
(quota, --max-llm-calls or Ctrl-C; resume command printed); 3 refused or aborted (hash mismatch, settings mismatch,
unknown case, model-purity violation, missing key or index).
"""
import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")  # a Windows memory failure at numpy import was seen with many threads

import argparse  # noqa: E402
import contextlib  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import shlex  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from collections.abc import Callable  # noqa: E402
from dataclasses import dataclass, replace  # noqa: E402
from datetime import date  # noqa: E402
from pathlib import Path  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.evaluation.integrity import verify_frozen_files  # noqa: E402
from knowledge_assistant.application.evaluation.run_evaluation import (  # noqa: E402
    ARMS,
    FULL,
    MODES,
    SPLITS,
    RunConfig,
    RunEnvironment,
    RunEvaluation,
)
from knowledge_assistant.application.generation.answer_question import AnswerQuestion  # noqa: E402
from knowledge_assistant.application.retrieval.retrieve import Retriever  # noqa: E402
from knowledge_assistant.composition import build_answer_service, open_embedder, open_vector_store  # noqa: E402
from knowledge_assistant.config import (  # noqa: E402
    get_answer_settings,
    get_embedding_settings,
    get_retrieval_settings,
)
from knowledge_assistant.core.exceptions import (  # noqa: E402
    ConfigurationError,
    EvaluationError,
    IntegrityError,
    VectorStoreError,
)
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask  # noqa: E402
from knowledge_assistant.infrastructure.gemini_retry import redact_key  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini.gemini_llm import build_throttles  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini.provider_error_log import FirstProviderErrors  # noqa: E402
from knowledge_assistant.infrastructure.persistence.jsonl_record_store import JsonlRecordStore  # noqa: E402

SNAPSHOT = Path("docs/snapshots/evaluation/eval-v1.md")
QUESTIONS_DIR = Path("data/evaluation/questions")
RESULTS_DIR = Path("data/evaluation/results")
SPLIT_FILES = {"eval": "eval-v1.jsonl", "dev": "dev-v1.jsonl"}
FREEZE_TAG = "eval-freeze-v1"
EXIT_OK, EXIT_ERRORS, EXIT_STOPPED, EXIT_ABORTED = 0, 1, 2, 3


@dataclass
class Services:
    """What the run needs from the outside world. `throttles` is the one per-model throttle mapping of this process;
    a judge (EVAL-003b) that runs in the same process must build its GeminiLLM with it."""

    retriever: Retriever
    answerer: AnswerQuestion | None
    missing_embeddings: Callable[[list[str]], list[str]]
    stats: Callable[[], dict]
    throttles: dict | None


@contextlib.contextmanager
def open_services(arm: str, mode: str, settings, on_provider_error):
    """The query embedder (Gemini behind the on-disk cache), the arm's existing collection and, in full mode, the LLM
    with its throttles, built ONCE here. `settings` is the answer settings the run was configured with."""
    retrieval = get_retrieval_settings()
    with open_embedder() as embedder:
        store = open_vector_store(arm)
        retriever = Retriever(embedder, store, retrieval.top_k, retrieval.overfetch)
        answerer = llm = throttles = None
        if mode == FULL:
            throttles = build_throttles(settings)
            llm = GeminiLLM(settings, throttles=throttles, on_provider_error=on_provider_error)
            answerer = build_answer_service(arm, llm, embedder, store=store)

        def stats() -> dict:
            embedding = embedder.stats()
            data = {
                "embedding_requests": embedding.get("api_requests", 0),
                "embedding_cache_hits": embedding["hits"],
                "embedding_cache_misses": embedding["misses"],
            }
            if llm is not None:
                data.update(llm_http_requests=llm.requests, llm_http_requests_by_model=dict(llm.requests_by_model))
            return data

        yield Services(retriever, answerer, lambda texts: embedder.missing(texts, EmbeddingTask.QUERY), stats, throttles)


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        raise IntegrityError(f"`git {' '.join(args)}` failed: {completed.stderr.strip() or 'no output'}")
    return completed.stdout.strip()


def collect_git_state(root: Path) -> tuple[RunEnvironment, str]:
    """(where this invocation runs, the commit the freeze tag points to). Dirty = tracked files that differ from HEAD."""
    commit = _git(root, "rev-parse", "HEAD")
    dirty = tuple(line for line in _git(root, "diff", "--name-only", "HEAD").splitlines() if line)
    try:
        tag_commit = _git(root, "rev-parse", f"{FREEZE_TAG}^{{commit}}")
    except IntegrityError as error:
        raise IntegrityError(f"the git tag {FREEZE_TAG} is missing ({error}); it marks the frozen question files") from error
    return RunEnvironment(commit, bool(dirty), dirty), tag_commit


def default_run_id(today: date, split: str, arm: str, mode: str, commit: str) -> str:
    return f"{today:%Y%m%d}-{split}-{arm}-{mode}-{commit[:7]}"


def load_cases(data: bytes, split: str) -> list[dict]:
    """The cases of one split. A case marked with another split is refused: the eval set never enters a dev run."""
    cases = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    for case in cases:
        if case.get("split") != split:
            raise EvaluationError(f"{case.get('id')} has split {case.get('split')!r}, not {split!r}; refusing to run it")
    return cases


def select_cases(cases: list[dict], wanted: str | None, split: str) -> list[dict]:
    if not wanted:
        return cases
    ids = [item.strip() for item in wanted.split(",") if item.strip()]
    unknown = [item for item in ids if item not in {case["id"] for case in cases}]
    if unknown:
        raise EvaluationError(f"unknown case id(s) for split {split}: {', '.join(unknown)}")
    return [case for case in cases if case["id"] in set(ids)]


def resume_command(run_id: str, args: argparse.Namespace) -> str:
    parts = ["python", "scripts/evaluation/run_eval.py", "--arm", args.arm, "--mode", args.mode, "--split", args.split,
             "--run-id", run_id]
    if args.cases:
        parts += ["--cases", args.cases]
    if args.mode == FULL:
        parts += ["--max-llm-calls", str(args.max_llm_calls)]
    return " ".join(shlex.quote(part) for part in parts)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--split", choices=SPLITS, required=True)
    parser.add_argument("--run-id", help="resume this run if it exists; default <date>-<split>-<arm>-<mode>-<sha>")
    parser.add_argument("--max-llm-calls", type=int, default=200, help="LLM requests per invocation, retries included")
    parser.add_argument("--cases", help="comma-separated case ids (default: every case of the split)")
    parser.add_argument("--estimate-only", action="store_true", help="print the estimate and stop; spends nothing")
    args = parser.parse_args(argv)
    if args.max_llm_calls < 0:
        parser.error("--max-llm-calls must be >= 0")
    return args


def main(argv=None, *, services=open_services, git_state=collect_git_state, root: Path = PROJECT_ROOT,
         today: Callable[[], date] = date.today, out=None, err=None) -> int:
    args = parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr

    def emit(text: str) -> None:
        print(text, file=out, flush=True)

    try:
        return _run(args, emit, services, git_state, root, today)
    except (EvaluationError, ConfigurationError, VectorStoreError) as error:
        print(f"ABORTED: {redact_key(str(error))}", file=err, flush=True)
        return EXIT_ABORTED


def _run(args, emit, services, git_state, root: Path, today) -> int:
    # 1. integrity first: both frozen files, whichever split runs
    files = {name: (root / QUESTIONS_DIR / name).read_bytes() for name in SPLIT_FILES.values()}
    hashes = verify_frozen_files((root / SNAPSHOT).read_text(encoding="utf-8"), files)
    environment, tag_commit = git_state(root)
    cases = select_cases(load_cases(files[SPLIT_FILES[args.split]], args.split), args.cases, args.split)

    # 2. the settings this run uses (full mode: the fallback model is forced off) and its identity
    settings = replace(get_answer_settings(), allow_fallback=False)
    retrieval, embedding = get_retrieval_settings(), get_embedding_settings()
    prompt_file = settings.prompts_dir / f"{settings.prompt_version}.md"
    config = RunConfig(
        arm=args.arm, mode=args.mode, split=args.split, answer_model=settings.model,
        fallback_model=settings.fallback_model, allow_fallback=settings.allow_fallback,
        embedding_model=embedding.model, embedding_dim=embedding.dim, throttle_rpm=settings.limits.throttle_rpm,
        threshold=retrieval.insufficient_score_threshold, prompt_version=settings.prompt_version,
        prompt_sha256=hashlib.sha256(prompt_file.read_bytes()).hexdigest(), top_k=retrieval.top_k,
        overfetch=retrieval.overfetch, freeze_tag=FREEZE_TAG, freeze_tag_commit=tag_commit, question_files=hashes,
    )
    run_id = args.run_id or default_run_id(today(), args.split, args.arm, args.mode, environment.git_commit)
    directory = root / RESULTS_DIR / run_id
    if args.run_id is None and directory.exists():
        raise EvaluationError(f"run {run_id} already exists; pass --run-id {run_id} to resume it, or choose another --run-id")
    store = JsonlRecordStore(directory, redact=redact_key)

    # 3. estimate, then run
    emit(f"run {run_id}: arm {args.arm}, mode {args.mode}, split {args.split} -> {RESULTS_DIR.as_posix()}/{run_id}/")
    emit(f"settings: answer model {config.answer_model} (fallback off), threshold {config.threshold}, top-k "
         f"{config.top_k}+{config.overfetch}, prompt {config.prompt_version}, freeze tag {FREEZE_TAG} ({tag_commit[:7]})")
    with services(args.arm, args.mode, settings, FirstProviderErrors(store, run_id)) as opened:
        evaluation = RunEvaluation(run_id, config, store, opened.retriever, opened.answerer,
                                   max_llm_calls=args.max_llm_calls, progress=emit, stats=opened.stats)
        estimate = evaluation.estimate(cases, opened.missing_embeddings)
        for line in estimate.lines(rpd=settings.limits.rpd):
            emit(f"estimate: {line}")
        if args.estimate_only:
            return EXIT_OK
        if estimate.to_run == 0:
            emit("nothing to run: every selected case is already ok")
            return EXIT_OK
        try:
            summary = evaluation.run(cases, environment)
        except KeyboardInterrupt:
            emit(f"INTERRUPTED; what was recorded is safe.\nresume with: {resume_command(run_id, args)}")
            return EXIT_STOPPED
        stats = opened.stats()

    emit(f"run {run_id}: {summary.ok} ok, {summary.errors} error, {summary.skipped} skipped of {summary.selected} "
         f"selected; {summary.remaining} without an ok record")
    emit(f"LLM requests this invocation: {summary.llm_requests}; embedding requests: {stats['embedding_requests']} "
         f"(cache hits {stats['embedding_cache_hits']}, misses {stats['embedding_cache_misses']})")
    refused = summary.answerable_refused_by_gate
    emit(f"answerable cases refused by the gate: {len(refused)}" + (f" ({', '.join(refused)})" if refused else ""))
    if summary.stopped:
        emit(f"STOPPED ({summary.stopped}): {summary.stop_detail}")
        emit(f"resume with: {resume_command(run_id, args)}")
        return EXIT_STOPPED
    return EXIT_ERRORS if summary.remaining else EXIT_OK


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    load_dotenv(find_dotenv())  # walks up from this file, so a git worktree inside the repo finds the repo's .env
    sys.exit(main())
