"""EVAL-003b: judge the generated answers of one evaluation run with the LLM judge. Scoring input only; no tables.

    python scripts/evaluation/judge_run.py --run-id ID [--max-llm-calls N] [--cases ID,ID] [--estimate-only]
        [--allow-unfinished]

Reads `data/evaluation/results/<run_id>/run.json` and `records.jsonl` (latest line per case, `latest_records`) and
appends one line per judge call to `judgements.jsonl` in the same folder. Which records get a call, the two checks
(answer / refusal) and the strict parsing are in `application/evaluation/judge.py`. Re-running spends nothing on
records already judged ok (cache key: case, arm, sha256 of the answer, judge prompt version); judge_error lines are
retried. The judge prompt's file hash and the judge model are checked against earlier ok lines: a mismatch refuses
the run.

The judge is JUDGE_MODEL from config (gemini-3.5-flash-lite), temperature 0, no fallback model, its own 13-RPM
throttle. It runs as a separate step AFTER generation, never at the same time as run_eval.py on the same key: the
throttle windows are per process, so two processes could exceed the model's 15 RPM together. The script refuses a run
whose last run_eval.py invocation has no finish time (it may still be running); pass --allow-unfinished only when you
know that invocation was killed. It never opens the embedder or the vector store: 0 embedding requests.

Exit codes: 0 every record that needs a judgement has an ok one; 1 finished, some judge errors (a re-run retries
them); 2 stopped early (quota or --max-llm-calls); 3 refused (unknown run, retrieval-mode run, settings mismatch,
missing key).
"""
import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import sys  # noqa: E402
from dataclasses import replace  # noqa: E402
from pathlib import Path  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.evaluation.judge import (  # noqa: E402
    JudgeConfig,
    JudgeRecords,
    parse_template,
)
from knowledge_assistant.application.evaluation.run_evaluation import FULL  # noqa: E402
from knowledge_assistant.config import get_answer_settings, get_judge_settings  # noqa: E402
from knowledge_assistant.core.exceptions import ConfigurationError, EvaluationError  # noqa: E402
from knowledge_assistant.infrastructure.gemini_retry import redact_key  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini.gemini_llm import build_throttles  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini.provider_error_log import FirstProviderErrors  # noqa: E402
from knowledge_assistant.infrastructure.persistence.jsonl_record_store import JsonlRecordStore  # noqa: E402

RESULTS_DIR = Path("data/evaluation/results")
EXIT_OK, EXIT_ERRORS, EXIT_STOPPED, EXIT_ABORTED = 0, 1, 2, 3


def judge_llm_settings(judge):
    """The adapter settings for the judge: the judge model, no fallback, the judge's attempts, timeout and limits."""
    return replace(get_answer_settings(), model=judge.model, allow_fallback=False, max_attempts=judge.max_attempts,
                   timeout_s=judge.timeout_s, limits=judge.limits)


def build_llm(judge, store, run_id):
    settings = judge_llm_settings(judge)
    return GeminiLLM(settings, throttles=build_throttles(settings), on_provider_error=FirstProviderErrors(store, run_id))


def run_split(manifest: dict, records: list[dict]) -> str:
    """The run's split: from each record (EVAL-003a fix) or, for runs that predate the field, from run.json."""
    split = manifest["config"]["split"]
    other = sorted({record["split"] for record in records if record.get("split") not in (None, split)})
    if other:
        raise EvaluationError(f"records carry split {other}, run.json says {split!r}")
    return split


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-llm-calls", type=int, default=200, help="judge requests per invocation, retries included")
    parser.add_argument("--cases", help="comma-separated case ids (default: every record of the run)")
    parser.add_argument("--estimate-only", action="store_true", help="print what would be judged and stop")
    parser.add_argument("--allow-unfinished", action="store_true",
                        help="judge although the last run_eval.py invocation has no finish time (it was killed)")
    args = parser.parse_args(argv)
    if args.max_llm_calls < 0:
        parser.error("--max-llm-calls must be >= 0")
    return args


def main(argv=None, *, llm_factory=build_llm, root: Path = PROJECT_ROOT, out=None, err=None) -> int:
    args = parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr

    def emit(text: str) -> None:
        print(text, file=out, flush=True)

    try:
        return _run(args, emit, llm_factory, root)
    except (EvaluationError, ConfigurationError) as error:
        print(f"ABORTED: {redact_key(str(error))}", file=err, flush=True)
        return EXIT_ABORTED


def _run(args, emit, llm_factory, root: Path) -> int:
    directory = root / RESULTS_DIR / args.run_id
    store = JsonlRecordStore(directory, redact=redact_key)
    manifest = store.read_manifest()
    if manifest is None:
        raise EvaluationError(f"no run {args.run_id} ({RESULTS_DIR.as_posix()}/{args.run_id}/run.json missing)")
    if manifest["config"]["mode"] != FULL:
        raise EvaluationError(f"run {args.run_id} is a {manifest['config']['mode']}-mode run: no answers to judge")
    invocations = manifest.get("invocations") or []
    if invocations and invocations[-1].get("finished_at") is None and not args.allow_unfinished:
        raise EvaluationError(f"the last run_eval.py invocation of {args.run_id} has no finish time: it may still be "
                              "running (the judge never runs at the same time). If it was killed, resume it with "
                              "run_eval.py or pass --allow-unfinished")
    records = store.read_records()
    if args.cases:
        wanted = {item.strip() for item in args.cases.split(",") if item.strip()}
        unknown = sorted(wanted - {record["case_id"] for record in records})
        if unknown:
            raise EvaluationError(f"no record for case id(s) {', '.join(unknown)} in run {args.run_id}")
        records = [record for record in records if record["case_id"] in wanted]
    split = run_split(manifest, records)

    judge = get_judge_settings()
    prompt_file = judge.prompts_dir / f"{judge.prompt_version}.md"
    prompt_bytes = prompt_file.read_bytes()
    config = JudgeConfig(model=judge.model, prompt_version=judge.prompt_version,
                         prompt_sha256=hashlib.sha256(prompt_bytes).hexdigest(),
                         max_output_tokens=judge.max_output_tokens)
    templates = parse_template(prompt_bytes.decode("utf-8"))
    emit(f"judge run {args.run_id} (split {split}, arm {manifest['config']['arm']}): model {config.model} (fallback off, "
         f"temperature 0, throttle {judge.limits.throttle_rpm} RPM), prompt {config.prompt_version} "
         f"({config.prompt_sha256[:12]})")

    llm = None if args.estimate_only else llm_factory(judge, store, args.run_id)
    judging = JudgeRecords(args.run_id, split, config, templates, llm, store, args.max_llm_calls, progress=emit)
    plan = judging.plan(records)
    emit(f"records needing a judgement: {plan.need_judge} ({plan.cached} already judged ok, {plan.to_call} to call); "
         f"labelled without a judge: {plan.no_call}; not scored (error or retrieval records): {plan.not_scored}")
    emit(f"estimate: at least {plan.to_call} judge request(s) (retries extra), about "
         f"{plan.to_call / judge.limits.throttle_rpm:.1f} min at {judge.limits.throttle_rpm} RPM, "
         f"{plan.to_call} of {judge.limits.rpd} requests per day")
    if args.estimate_only:
        return EXIT_OK
    if plan.to_call == 0:
        emit("nothing to judge: every record that needs a judgement is judged ok")
        return EXIT_OK
    summary = judging.run(records)
    emit(f"judged {summary.ok} ok, {summary.errors} judge_error, {summary.cached} cached; judge requests this invocation: "
         f"{summary.llm_requests} (HTTP {llm.requests}, by model {dict(llm.requests_by_model)}); embedding requests: 0")
    if summary.stopped:
        emit(f"STOPPED ({summary.stopped}): {summary.stop_detail}")
        emit(f"resume with: python scripts/evaluation/judge_run.py --run-id {args.run_id}")
        return EXIT_STOPPED
    return EXIT_ERRORS if summary.remaining else EXIT_OK


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    load_dotenv(find_dotenv())  # walks up from this file, so a git worktree inside the repo finds the repo's .env
    sys.exit(main())
