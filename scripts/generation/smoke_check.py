"""RAG-003 live smoke checks on the DEV set only (never the eval set): "smoke check, not evaluation data".

    python scripts/generation/smoke_check.py --out validation/generation/smoke-2026-09-26.md          # dry run
    python scripts/generation/smoke_check.py --out validation/generation/smoke-2026-09-26.md --live   # spends quota

Steps (Arm A, dev questions Q-DEV-001 EN, Q-DEV-002 VI, Q-DEV-005 out of corpus):
  a1, a2  one cited answer each, through the same code the CLI runs (scripts/ask.py main)
  b       Q-DEV-005 normally: refused by the retrieval gate, 0 LLM requests; also once as a real `ask.py` process
  c       Q-DEV-005 with --gate-off: the LLM's own "insufficient" answer (owner decision D2: missing_information, related-only citations)
  d       ONE direct call to the fallback model with Q-DEV-001's exact request: proves JSON mode + schema on it

Budget: at most 5 LLM requests and 0 embedding requests. Steps a-c run with 1 attempt and no fallback, so one step is
one request; a query whose embedding is not cached stops the run before any LLM call; the first provider error
(a 429 included) stops the run, its body is saved redacted, and nothing is retried in a loop. Without --live nothing
is spent: the script prints the plan and checks the embedding cache.
"""
import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import ask  # noqa: E402  (scripts/ask.py: the CLI whose code path the steps exercise)
from knowledge_assistant.application.generation.answer_question import parse_answer_json  # noqa: E402
from knowledge_assistant.composition import build_answer_service, open_embedder  # noqa: E402
from knowledge_assistant.config import get_answer_settings, get_retrieval_settings  # noqa: E402
from knowledge_assistant.core.exceptions import GenerationError, LLMError  # noqa: E402
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM  # noqa: E402

DEV_FILE = PROJECT_ROOT / "data" / "evaluation" / "questions" / "dev-v1.jsonl"  # the only question file read here
SMOKE_IDS = ("Q-DEV-001", "Q-DEV-002", "Q-DEV-005")
LLM_BUDGET = 5


class BudgetExceeded(Exception):
    """A request would go over the LLM budget; it is refused before it is sent."""


class Budget:
    def __init__(self, limit: int) -> None:
        self.limit, self.used = limit, 0

    def spend(self) -> None:
        if self.used >= self.limit:
            raise BudgetExceeded(f"LLM budget of {self.limit} requests reached; the next request was not sent")
        self.used += 1


class BudgetedLLM:
    """Counts every request against the budget before it is sent and keeps requests and responses for the report."""

    def __init__(self, inner, budget: Budget) -> None:
        self.inner, self.budget = inner, budget
        self.requests: list = []
        self.responses: list = []

    def generate(self, request):
        self.budget.spend()
        self.requests.append(request)
        response = self.inner.generate(request)
        self.responses.append(response)
        return response


def load_dev_cases(path: Path) -> dict[str, dict]:
    cases = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        if case["split"] != "dev" or not case["id"].startswith("Q-DEV-"):  # eval-set firewall
            raise SystemExit(f"refusing non-dev case {case['id']}")
        cases[case["id"]] = case
    return cases


def run_cli_process(question: str) -> tuple[int, str]:
    """`python scripts/ask.py <question> --json` as a real process; 1 attempt and no fallback even if it did call the LLM."""
    env = {**os.environ, "ANSWER_MAX_ATTEMPTS": "1", "ALLOW_FALLBACK": "false"}
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "ask.py"), question, "--arm", "A", "--json"],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=PROJECT_ROOT,
    )
    return proc.returncode, proc.stdout + (f"\nstderr:\n{proc.stderr}" if proc.stderr.strip() else "")


def _block(text: str) -> str:
    return f"````text\n{text.rstrip()}\n````"


def run_smoke(cases, *, embedder, build_service, answer_llm, fallback_llm, emit, budget_limit=LLM_BUDGET,
              process_check=None, setup_lines=(), main_fn=ask.main) -> int:
    questions = {case_id: cases[case_id]["question"] for case_id in SMOKE_IDS}
    emit("# Smoke check: RAG-003\n")
    emit("> Label: **smoke check, not evaluation data**. Dev questions only (Q-DEV-001, Q-DEV-002, Q-DEV-005), one "
         "run per step. Latencies and token counts are single anecdotal observations, not evaluation results.\n")
    emit(f"Run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}.\n\n## Setup\n")
    for line in setup_lines:
        emit(line)
    missing = embedder.missing(list(questions.values()), EmbeddingTask.QUERY)
    emit(f"- embedding cache: {len(questions)} dev queries, {len(missing)} not cached → embed requests planned: 0")
    if missing:
        emit(f"\nSTOPPED before any LLM call: {len(missing)} query embedding(s) are not cached, so running would spend "
             "embedding requests (budget: 0). Nothing was sent.")
        return 1

    budget = Budget(budget_limit)
    answer = BudgetedLLM(answer_llm, budget)
    fallback = BudgetedLLM(fallback_llm, budget)

    def factory(arm, gate_off):
        return contextlib.nullcontext((build_service(arm, gate_off, answer), answer))

    def step(label, title, case_id, extra=()):
        before = budget.used
        out, err = io.StringIO(), io.StringIO()
        argv = [questions[case_id], "--arm", "A", *extra]
        code = main_fn(argv, factory=factory, out=out, err=err)
        spent = budget.used - before
        flags = " ".join(extra)
        emit(f"\n### {label}. {title}\n")
        emit(f"- {case_id} ({cases[case_id]['language']}): `ask.py \"<question>\" --arm A{' ' + flags if flags else ''}`; "
             f"exit code {code}; LLM requests this step: {spent} (used {budget.used} of {budget.limit})")
        emit(f"\nQuestion: {questions[case_id]}\n")
        emit(_block(out.getvalue() + (f"\nstderr:\n{err.getvalue()}" if err.getvalue().strip() else "")))
        return code, out.getvalue(), spent

    def stopped(label, code):
        emit(f"\nSTOPPED after step {label}: exit code {code} (the provider error above; its redacted body was saved "
             "to data/logs). Nothing was retried and no further request was sent.")
        return code

    try:
        for label, title, case_id in (("a1", "Answerable question, English (Arm A)", "Q-DEV-001"),
                                      ("a2", "Answerable question, Vietnamese (Arm A)", "Q-DEV-002")):
            code, _, _ = step(label, title, case_id)
            if code:
                return stopped(label, code)

        code, text, spent = step("b", "Out-of-corpus question, gate on: refused by the retrieval gate", "Q-DEV-005")
        if code:
            return stopped("b", code)
        refused = spent == 0 and "Insufficient information: yes (retrieval_gate)" in text
        emit(f"\n- gate refusal confirmed with 0 LLM requests: {'yes' if refused else 'NO'}")
        step_json = io.StringIO()
        main_fn([questions["Q-DEV-005"], "--arm", "A", "--json"], factory=factory, out=step_json, err=io.StringIO())
        emit("\nSame question with `--json` (also 0 LLM requests):\n")
        emit(_block(step_json.getvalue()))
        if refused and process_check is not None:
            code, output = process_check(questions["Q-DEV-005"])
            emit(f"\nThe same question as a real process (`python scripts/ask.py \"<question>\" --arm A --json`, "
                 f"ANSWER_MAX_ATTEMPTS=1, ALLOW_FALLBACK=false), exit code {code}:\n")
            emit(_block(output))

        code, text, spent = step("c", "Out-of-corpus question, gate off (diagnostic): the LLM's own insufficient path",
                                 "Q-DEV-005", ["--gate-off"])
        if code:
            return stopped("c", code)
        raw = json.loads(answer.responses[-1].text)
        related = len(re.findall(r"^\s+\[\d+\] ", text, re.MULTILINE))
        emit(f"\nOwner decision D2 check (facts from the model's JSON and the printed output):\n\n"
             f"- insufficient={str(raw['insufficient']).lower()}; printed as `Insufficient information: yes (llm)`: "
             f"{'yes' if 'Insufficient information: yes (llm)' in text else 'no'}\n"
             f"- missing_information non-empty: {'yes' if raw['missing_information'].strip() else 'no'}\n"
             f"- cited_passages from the model: {raw['cited_passages']}; related-only citations printed: {related}\n"
             f"- answer text shown is the localized message, not model text: "
             f"{'yes' if not raw['insufficient'] or raw['answer'] == '' else 'model gave answer text (see raw)'}")

        emit("\n### d. Direct call to the fallback model with Q-DEV-001's exact request\n")
        request = answer.requests[0]
        try:
            response = fallback.generate(request)
        except LLMError as error:
            saved = ask.save_error_body(error)
            emit(f"- STOPPED: {error.kind}: {ask.redact_key(str(error))}; provider body saved: {saved}")
            return 2
        except GenerationError as error:
            emit(f"- fallback output unusable: {error}\n- JSON valid: no\n"
                 f"- finish_reason: {getattr(fallback_llm, 'last_finish_reason', None)}; "
                 f"usage: {getattr(fallback_llm, 'last_usage', None)}\n- raw text: {error.raw_text!r}")
            return 0
        try:
            data = parse_answer_json(response.text)
            valid, note = "yes", f"insufficient={str(data['insufficient']).lower()}, cited_passages={data['cited_passages']}"
        except GenerationError as error:
            valid, note = "no", str(error)
        emit(f"- model used: `{response.model_used}`; fallback_used={response.fallback_used}; retry_count={response.retry_count}\n"
             f"- finish_reason: {getattr(fallback_llm, 'last_finish_reason', None)}\n"
             f"- tokens: prompt {response.prompt_tokens}, output {response.output_tokens}, "
             f"thoughts tokens {response.thoughts_tokens}\n"
             f"- latency: {response.latency_ms:.0f} ms (one call; anecdotal)\n"
             f"- JSON valid: {valid} (parsed and checked against the answer schema): {note}")
        emit("\nRaw text from the fallback model:\n")
        emit(_block(response.text))
    except BudgetExceeded as error:
        emit(f"\nSTOPPED: {error}.")
        return 3
    emit(f"\n## Totals\n\n- LLM requests: {budget.used} of {budget.limit}; embedding requests: 0 (dev queries cached)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="Markdown file to write (must not exist yet)")
    parser.add_argument("--live", action="store_true", help="spend quota: run the steps")
    args = parser.parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")

    cases = load_dev_cases(DEV_FILE)
    settings = get_answer_settings()
    threshold = get_retrieval_settings().insufficient_score_threshold
    setup = [
        f"- ANSWER_MODEL = `{settings.model}`; FALLBACK_MODEL = `{settings.fallback_model}`; prompt `{settings.prompt_version}`; "
        f"gate threshold {threshold}",
        "- steps a-c: ANSWER_MAX_ATTEMPTS=1 and ALLOW_FALLBACK=false (one step = one request); step d calls the fallback model directly",
        f"- planned LLM requests: 4 (a1, a2, c on `{settings.model}`; d on `{settings.fallback_model}`); b makes 0; budget {LLM_BUDGET}",
        f"- throttle: {settings.limits.throttle_rpm} RPM (answer model), {settings.fallback_limits.throttle_rpm} RPM (fallback)",
    ]
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; refusing to overwrite evidence (choose another --out)")

    lines: list[str] = []

    def emit(text: str) -> None:
        lines.append(text)
        print(text)

    with open_embedder(max_attempts=1) as embedder:
        if not args.live:
            for line in setup:
                print(line)
            missing = embedder.missing([cases[i]["question"] for i in SMOKE_IDS], EmbeddingTask.QUERY)
            print(f"- embedding cache: {len(SMOKE_IDS)} dev queries, {len(missing)} not cached")
            print("dry run: nothing was sent; re-run with --live to spend 4 LLM requests")
            return 0 if not missing else 1
        answer_llm = GeminiLLM(replace(settings, max_attempts=1, allow_fallback=False))
        fallback_llm = GeminiLLM(replace(
            settings, model=settings.fallback_model, max_attempts=1, allow_fallback=False, limits=settings.fallback_limits
        ))
        code = run_smoke(
            cases,
            embedder=embedder,
            build_service=lambda arm, gate_off, llm: build_answer_service(arm, llm, embedder, gate_off=gate_off),
            answer_llm=answer_llm,
            fallback_llm=fallback_llm,
            emit=emit,
            process_check=run_cli_process,
            setup_lines=setup,
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwrote {args.out} (exit code {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())
