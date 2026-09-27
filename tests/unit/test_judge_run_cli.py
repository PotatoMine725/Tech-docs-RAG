"""EVAL-003b: scripts/evaluation/judge_run.py with a fake LLM factory and made-up run folders (no network)."""
import io
import json

import pytest

from knowledge_assistant.config import get_judge_settings
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM
from scripts.evaluation import judge_run
from tests.eval_fakes import ScriptedLLM
from tests.judge_fakes import JUDGE_MODEL, answer_verdict, make_record, ok_response


class CountingLLM(ScriptedLLM):
    """ScriptedLLM with the adapter's counters, which the script prints."""

    def __init__(self, *outcomes, model=JUDGE_MODEL):
        super().__init__(*outcomes, model=model)
        self.requests_by_model: dict = {}

    def generate(self, request):
        self.requests_by_model[self.model] = self.requests_by_model.get(self.model, 0) + 1
        return super().generate(request)


@pytest.fixture
def judge_env(monkeypatch):
    monkeypatch.setenv("JUDGE_MODEL", JUDGE_MODEL)
    for name in ("JUDGE_PROMPT_VERSION", "PROMPTS_DIR", "JUDGE_MAX_OUTPUT_TOKENS"):
        monkeypatch.delenv(name, raising=False)


def write_run(root, run_id="run-1", mode="full", records=None, finished=True, split_in_records=True):
    directory = root / "data" / "evaluation" / "results" / run_id
    directory.mkdir(parents=True)
    invocation = {"started_at": "t0", "finished_at": "t1" if finished else None}
    manifest = {"run_id": run_id, "config": {"arm": "A", "mode": mode, "split": "dev"}, "invocations": [invocation]}
    (directory / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
    records = records if records is not None else [make_record(1), make_record(2)]
    if not split_in_records:
        records = [{k: v for k, v in record.items() if k != "split"} for record in records]
    (directory / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return directory


def run(root, *argv, llm=None):
    out, err = io.StringIO(), io.StringIO()
    made = []

    def factory(judge, store, run_id):
        made.append(judge)
        return llm

    code = judge_run.main(list(argv), llm_factory=factory, root=root, out=out, err=err)
    return code, out.getvalue(), err.getvalue(), made


def test_judges_every_answered_record_then_spends_nothing_on_a_rerun(tmp_path, judge_env):
    directory = write_run(tmp_path)
    llm = CountingLLM(ok_response(answer_verdict()), ok_response(answer_verdict()))
    code, out, _, _ = run(tmp_path, "--run-id", "run-1", llm=llm)
    assert code == judge_run.EXIT_OK and len(llm.requests) == 2
    lines = [json.loads(line) for line in (directory / "judgements.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [line["status"] for line in lines] == ["ok", "ok"] and "embedding requests: 0" in out
    again = CountingLLM()
    code, out, _, made = run(tmp_path, "--run-id", "run-1", llm=again)
    assert code == judge_run.EXIT_OK and again.requests == [] and "nothing to judge" in out


def test_estimate_only_builds_no_llm(tmp_path, judge_env):
    write_run(tmp_path)
    code, out, _, made = run(tmp_path, "--run-id", "run-1", "--estimate-only")
    assert code == judge_run.EXIT_OK and made == [] and "2 to call" in out


def test_split_comes_from_run_json_when_records_predate_the_field(tmp_path, judge_env):
    directory = write_run(tmp_path, split_in_records=False)
    run(tmp_path, "--run-id", "run-1", "--cases", "Q-TEST-001", llm=CountingLLM(ok_response(answer_verdict())))
    line = json.loads((directory / "judgements.jsonl").read_text(encoding="utf-8"))
    assert (line["split"], line["case_id"]) == ("dev", "Q-TEST-001")


@pytest.mark.parametrize(("kwargs", "argv", "message"), [
    ({"mode": "retrieval"}, [], "retrieval-mode run"),
    ({"finished": False}, [], "may still be running"),
    ({}, ["--cases", "Q-TEST-404"], "Q-TEST-404"),
])
def test_refusals(tmp_path, judge_env, kwargs, argv, message):
    write_run(tmp_path, **kwargs)
    llm = CountingLLM()
    code, _, err, _ = run(tmp_path, "--run-id", "run-1", *argv, llm=llm)
    assert code == judge_run.EXIT_ABORTED and message in err and llm.requests == []


def test_unknown_run_is_refused(tmp_path, judge_env):
    code, _, err, _ = run(tmp_path, "--run-id", "nope")
    assert code == judge_run.EXIT_ABORTED and "no run nope" in err


def test_allow_unfinished_overrides_the_guard(tmp_path, judge_env):
    write_run(tmp_path, finished=False)
    code, _, _, _ = run(tmp_path, "--run-id", "run-1", "--allow-unfinished",
                        llm=CountingLLM(ok_response(answer_verdict()), ok_response(answer_verdict())))
    assert code == judge_run.EXIT_OK


def test_budget_stop_prints_the_resume_command(tmp_path, judge_env):
    write_run(tmp_path)
    code, out, _, _ = run(tmp_path, "--run-id", "run-1", "--max-llm-calls", "1",
                          llm=CountingLLM(ok_response(answer_verdict())))
    assert code == judge_run.EXIT_STOPPED and "resume with:" in out


def test_judge_errors_give_exit_1(tmp_path, judge_env):
    write_run(tmp_path)
    code, _, _, _ = run(tmp_path, "--run-id", "run-1", llm=CountingLLM(ok_response("nope"), ok_response("{")))
    assert code == judge_run.EXIT_ERRORS


def test_real_adapter_is_the_judge_model_with_no_fallback(monkeypatch, tmp_path):
    for name in ("JUDGE_MODEL", "ALLOW_FALLBACK", "JUDGE_THROTTLE_RPM", "JUDGE_LIMIT_RPM"):
        monkeypatch.delenv(name, raising=False)
    judge = get_judge_settings()
    settings = judge_run.judge_llm_settings(judge)
    assert (settings.model, settings.allow_fallback, settings.limits.throttle_rpm) == ("gemini-3.5-flash-lite", False, 13)
    llm = judge_run.build_llm(judge, object(), "run-1")  # no client is created until the first call
    assert isinstance(llm, GeminiLLM) and llm.model == "gemini-3.5-flash-lite"
