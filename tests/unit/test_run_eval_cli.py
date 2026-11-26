"""scripts/evaluation/run_eval.py with fakes: the guards around the live quota (EVAL-003a, owner addendum 2026-09-27).

A made-up mini project in tmp_path holds the question files, the snapshot with their hashes and the results folder, so
nothing here reads the frozen question files or touches Gemini. Case ids and questions are invented (`Q-TEST-...`).
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import shlex
from datetime import date
from pathlib import Path

import pytest

from knowledge_assistant.config import get_answer_settings, get_retrieval_settings
from knowledge_assistant.core.exceptions import LLMQuotaError
from tests.eval_fakes import (
    ENVIRONMENT,
    ScriptedLLM,
    ScriptedRetriever,
    answer_json,
    make_answerer,
    make_case,
    response,
)
from tests.fakes import FakeEmbedder, InMemoryVectorStore

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("run_eval_script", ROOT / "scripts" / "evaluation" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)

THRESHOLD = get_retrieval_settings().insufficient_score_threshold
CONFIGURED_MODEL = get_answer_settings().model  # the run's answer model: a double that answers as another model is a purity bug
TAG_COMMIT = "1" * 40
TODAY = date(2026, 9, 27)


def scripted(*outcomes) -> ScriptedLLM:
    return ScriptedLLM(*outcomes, model=CONFIGURED_MODEL)


def _write_jsonl(path: Path, cases: list[dict]) -> str:
    data = ("".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases)).encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    (root / "data" / "evaluation" / "questions").mkdir(parents=True)
    (root / "docs" / "snapshots" / "evaluation").mkdir(parents=True)
    dev = [dict(make_case(n), split="dev") for n in (1, 2, 3)]
    other = [dict(make_case(n), id=f"Q-TEST-X{n:02d}", split="eval", question=f"Another question number {n}?")
             for n in (1, 2)]
    questions = root / "data" / "evaluation" / "questions"
    hashes = {"dev-v1.jsonl": _write_jsonl(questions / "dev-v1.jsonl", dev),
              "eval-v1.jsonl": _write_jsonl(questions / "eval-v1.jsonl", other)}
    (root / "docs" / "snapshots" / "evaluation" / "eval-v1.md").write_text(
        "\n".join(f"| `data/evaluation/questions/{name}` SHA-256 | `{digest}` (n cases) |" for name, digest in hashes.items()),
        encoding="utf-8")
    return root


class FakeServices:
    """Stands in for `open_services`: records what it was asked for and hands out the scripted doubles."""

    def __init__(self, llm=None, retriever=None):
        self.llm = llm or scripted()
        self.retriever = retriever or ScriptedRetriever()
        self.calls: list[dict] = []

    @contextlib.contextmanager
    def __call__(self, arm, mode, settings, on_provider_error):
        self.calls.append({"arm": arm, "mode": mode, "settings": settings, "hook": on_provider_error})
        yield run_eval.Services(
            retriever=self.retriever,
            answerer=make_answerer(self.retriever, self.llm, THRESHOLD) if mode == "full" else None,
            missing_embeddings=lambda texts: [],
            stats=lambda: {"embedding_requests": 0, "embedding_cache_hits": len(self.retriever.calls),
                           "embedding_cache_misses": 0},
            throttles=None,
        )


def go(project, *argv, services=None, git_state=None):
    out, err = io.StringIO(), io.StringIO()
    code = run_eval.main(
        list(argv), services=services or FakeServices(), root=project, today=lambda: TODAY,
        git_state=git_state or (lambda root, tag=None: (ENVIRONMENT, TAG_COMMIT)), out=out, err=err,
    )
    return code, out.getvalue(), err.getvalue()


def results(project, run_id):
    directory = project / "data" / "evaluation" / "results" / run_id
    return directory, [json.loads(line) for line in (directory / "records.jsonl").read_text(encoding="utf-8").splitlines()]


DEFAULT_ID = "20260927-dev-A-full-abc1234"


# --- a normal run -----------------------------------------------------------------------------------------------

def test_a_dev_run_prints_the_estimate_then_progress_then_the_summary_and_writes_the_run_files(project):
    code, out, err = go(project, "--arm", "A", "--mode", "full", "--split", "dev")
    assert (code, err) == (0, "")
    assert out.index("cases: 3 selected") < out.index("[1/3] Q-TEST-001 en ok") < out.index("[3/3] Q-TEST-003 en ok")
    assert "LLM requests: 0 to 3" not in out and "LLM requests: 3 to 3" in out  # cached questions: exact
    assert "13 RPM" in out and "of 500" in out
    assert "3 ok, 0 error" in out and "answerable cases refused by the gate: 0" in out
    directory, records = results(project, DEFAULT_ID)
    assert [r["status"] for r in records] == ["ok"] * 3
    assert not (directory / "errors.jsonl").exists()
    manifest = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    assert (config["arm"], config["mode"], config["split"], config["allow_fallback"]) == ("A", "full", "dev", False)
    assert (config["top_k"], config["overfetch"], config["threshold"]) == (5, 10, THRESHOLD)
    assert config["prompt_version"] == "answer_v2" and len(config["prompt_sha256"]) == 64
    assert config["throttle_rpm"] == 13 and config["answer_model"] and config["embedding_dim"]
    assert (config["freeze_tag"], config["freeze_tag_commit"]) == ("eval-freeze-v1", TAG_COMMIT)
    assert set(config["question_files"]) == {"eval-v1.jsonl", "dev-v1.jsonl"}  # both files, whichever split runs
    assert (manifest["git_commit"], manifest["git_dirty"]) == ("abc1234", False)
    assert manifest["invocations"][0]["embedding_requests"] == 0


def test_the_default_run_id_is_date_split_arm_mode_and_short_sha(project):
    for split, arm, mode, expected in (("dev", "B", "retrieval", "20260927-dev-B-retrieval-abc1234"),
                                       ("eval", "A", "retrieval", "20260927-eval-A-retrieval-abc1234")):
        assert go(project, "--arm", arm, "--mode", mode, "--split", split)[0] == 0  # the made-up files of tmp_path
        assert (project / "data" / "evaluation" / "results" / expected / "run.json").is_file()
    assert run_eval.default_run_id(TODAY, "dev", "A", "full", "abc1234def") == DEFAULT_ID  # the sha is cut to 7


def test_cases_selects_a_subset_in_file_order_and_an_unknown_id_is_refused(project):
    code, out, _ = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--cases", "Q-TEST-003,Q-TEST-001")
    assert code == 0 and "[1/2] Q-TEST-001" in out and "[2/2] Q-TEST-003" in out
    code, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--cases", "Q-TEST-001,Q-TEST-404",
                      "--run-id", "other")
    assert code == 3 and "Q-TEST-404" in err
    assert not (project / "data" / "evaluation" / "results" / "other").exists()


def test_an_estimate_only_run_prints_the_estimate_and_writes_and_calls_nothing(project):
    services = FakeServices()
    code, out, _ = go(project, "--arm", "A", "--mode", "full", "--split", "dev", "--estimate-only", services=services)
    assert code == 0 and "cases: 3 selected" in out and "[1/3]" not in out
    assert services.llm.requests == [] and not (project / "data" / "evaluation" / "results").exists()


# --- integrity ----------------------------------------------------------------------------------------------------

def test_a_changed_question_file_aborts_before_any_service_is_opened_or_anything_is_written(project):
    dev = project / "data" / "evaluation" / "questions" / "dev-v1.jsonl"
    dev.write_bytes(dev.read_bytes() + b"\n")
    services = FakeServices()
    code, out, err = go(project, "--arm", "A", "--mode", "full", "--split", "eval", services=services)  # the OTHER split
    assert code == 3 and "dev-v1.jsonl" in err and "SHA-256" in err and "amendment" in err
    assert services.calls == [] and not (project / "data" / "evaluation" / "results").exists()


def test_a_missing_freeze_tag_aborts(project):
    def no_tag(root, tag=None):
        raise run_eval.IntegrityError("git tag eval-freeze-v1 does not exist")

    code, _, err = go(project, "--arm", "A", "--mode", "full", "--split", "dev", git_state=no_tag)
    assert code == 3 and "eval-freeze-v1" in err


def test_a_case_from_another_split_in_the_file_is_refused(project):
    questions = project / "data" / "evaluation" / "questions"
    cases = [json.loads(line) for line in (questions / "dev-v1.jsonl").read_text(encoding="utf-8").splitlines()]
    cases[1]["split"] = "eval"
    digest = _write_jsonl(questions / "dev-v1.jsonl", cases)
    snapshot = project / "docs" / "snapshots" / "evaluation" / "eval-v1.md"
    text = snapshot.read_text(encoding="utf-8")
    old = next(line for line in text.splitlines() if "dev-v1.jsonl" in line)
    snapshot.write_text(text.replace(old, f"| `data/evaluation/questions/dev-v1.jsonl` SHA-256 | `{digest}` |"), encoding="utf-8")
    code, _, err = go(project, "--arm", "A", "--mode", "full", "--split", "dev")
    assert code == 3 and "Q-TEST-002" in err and "split" in err


# --- resume, budget, quota ---------------------------------------------------------------------------------------

def test_an_existing_default_run_is_never_resumed_silently(project):
    assert go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev")[0] == 0
    code, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev")
    assert code == 3 and "already exists" in err and "--run-id" in err


def test_max_llm_calls_stops_with_exit_2_and_the_printed_resume_command_finishes_the_run(project):
    services = FakeServices()
    code, out, _ = go(project, "--arm", "A", "--mode", "full", "--split", "dev", "--max-llm-calls", "1", services=services)
    assert code == 2 and "STOPPED (max_llm_calls)" in out
    command = next(line for line in out.splitlines() if line.startswith("resume with: "))
    argv = shlex.split(command.removeprefix("resume with: python scripts/evaluation/run_eval.py"))
    assert argv == ["--arm", "A", "--mode", "full", "--split", "dev", "--questions", "v1", "--corpus", "corpus1",
                    "--run-id", DEFAULT_ID, "--max-llm-calls", "1"]
    assert len(services.llm.requests) == 1

    resumed = FakeServices()
    for _ in range(2):  # one request per invocation: two more invocations finish the three cases
        code, out, _ = go(project, *argv, services=resumed)
    assert code == 0 and len(resumed.llm.requests) == 2 and "skipped (already ok)" in out
    assert [r["status"] for r in results(project, DEFAULT_ID)[1]] == ["ok"] * 3


def test_a_quota_error_stops_the_run_prints_the_resume_command_and_leaves_the_other_cases_alone(project):
    quota = LLMQuotaError("daily quota exhausted; resume after the 14:00 UTC+7 reset", model="m", provider_body="{}", daily=True)
    services = FakeServices(llm=scripted("ok", quota))
    code, out, err = go(project, "--arm", "A", "--mode", "full", "--split", "dev", "--cases", "Q-TEST-001,Q-TEST-003",
                        services=services)
    assert code == 2 and "STOPPED (quota)" in out and "daily quota exhausted" in out
    assert f"--run-id {DEFAULT_ID}" in out and "--cases Q-TEST-001,Q-TEST-003" in out
    directory, records = results(project, DEFAULT_ID)
    assert [(r["case_id"], r["status"]) for r in records] == [("Q-TEST-001", "ok"), ("Q-TEST-003", "error")]
    assert json.loads((directory / "errors.jsonl").read_text(encoding="utf-8").splitlines()[0])["error_kind"] == "quota"


def test_resuming_with_other_settings_aborts_with_exit_3(project, monkeypatch):
    assert go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "r1")[0] == 0
    monkeypatch.setenv("INSUFFICIENT_SCORE_THRESHOLD", "0.9")
    code, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "r1")
    assert code == 3 and "threshold" in err and "different settings" in err


def test_ctrl_c_stops_cleanly_keeps_what_was_recorded_and_prints_the_resume_command(project):
    services = FakeServices(llm=scripted("ok", KeyboardInterrupt()))
    code, out, _ = go(project, "--arm", "A", "--mode", "full", "--split", "dev", services=services)
    assert code == 2 and "INTERRUPTED" in out and f"--run-id {DEFAULT_ID}" in out
    directory, records = results(project, DEFAULT_ID)
    assert [(r["case_id"], r["status"]) for r in records] == [("Q-TEST-001", "ok")]
    [invocation] = json.loads((directory / "run.json").read_text(encoding="utf-8"))["invocations"]
    assert invocation["stopped"] == "aborted" and "KeyboardInterrupt" in invocation["detail"]
    assert invocation["finished_at"] is not None


def test_a_run_with_failed_cases_exits_1(project):
    from knowledge_assistant.core.exceptions import LLMUnavailableError

    services = FakeServices(llm=scripted("ok", LLMUnavailableError("down", model="m"), "ok"))
    code, out, _ = go(project, "--arm", "A", "--mode", "full", "--split", "dev", services=services)
    assert code == 1 and "2 ok, 1 error" in out and "STOPPED" not in out


def test_a_fallback_answer_aborts_the_run_with_exit_3(project):
    services = FakeServices(llm=scripted("ok", response(answer_json(), fallback_used=True)))
    code, _, err = go(project, "--arm", "A", "--mode", "full", "--split", "dev", services=services)
    assert code == 3 and "allows only" in err


# --- model purity and the throttle wiring ------------------------------------------------------------------------

def test_full_mode_forces_the_fallback_off_even_when_the_environment_turns_it_on(project, monkeypatch):
    monkeypatch.setenv("ALLOW_FALLBACK", "true")
    services = FakeServices()
    code, _, _ = go(project, "--arm", "A", "--mode", "full", "--split", "dev", services=services)
    assert code == 0 and services.calls[0]["settings"].allow_fallback is False
    manifest = json.loads((project / "data" / "evaluation" / "results" / DEFAULT_ID / "run.json").read_text(encoding="utf-8"))
    assert manifest["config"]["allow_fallback"] is False


class _Embedder(FakeEmbedder):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def missing(self, texts, task):
        return []

    def stats(self):
        return {"hits": 4, "misses": 0, "api_requests": 0}


def test_the_real_wiring_builds_the_throttles_once_and_shares_them(monkeypatch):
    """`open_services` (not the fake): one build_throttles() call, its mapping passed to the one GeminiLLM."""
    built, llms = [], []
    throttles = {"a-model": object()}

    class SpyLLM(ScriptedLLM):
        requests_by_model = {"a-model": 2}

        def __init__(self, settings, throttles, on_provider_error):
            super().__init__()
            self.requests = 0  # the real adapter counts HTTP requests in an int
            llms.append({"settings": settings, "throttles": throttles, "hook": on_provider_error})

    monkeypatch.setattr(run_eval, "open_embedder", lambda: _Embedder())
    monkeypatch.setattr(run_eval, "open_vector_store", lambda arm: InMemoryVectorStore())
    monkeypatch.setattr(run_eval, "build_throttles", lambda settings: built.append(settings) or throttles)
    monkeypatch.setattr(run_eval, "create_llm", SpyLLM)
    settings = run_eval.replace(run_eval.get_answer_settings(), allow_fallback=False)
    hook = object()
    with run_eval.open_services("A", "full", settings, hook) as services:
        assert len(built) == 1 and len(llms) == 1
        assert llms[0]["throttles"] is throttles and services.throttles is throttles  # one mapping, shareable with a judge
        assert llms[0]["settings"].allow_fallback is False and llms[0]["hook"] is hook
        assert services.answerer is not None and services.answerer.threshold == THRESHOLD
        assert services.missing_embeddings(["q"]) == []
        assert services.stats() == {"embedding_requests": 0, "embedding_cache_hits": 4, "embedding_cache_misses": 0,
                                    "llm_http_requests": 0, "llm_http_requests_by_model": {"a-model": 2}}
    with run_eval.open_services("A", "retrieval", settings, hook) as services:  # retrieval: no LLM, no throttles
        assert len(built) == 1 and len(llms) == 1 and services.answerer is None and services.throttles is None


class _SpyReranker:
    """Absolute scores (so a retriever uses it); records how many passages each call saw."""

    model_id = "spy"
    absolute_scores = True

    def __init__(self):
        self.calls = []

    def rerank(self, query, passages, top_n=None):
        from knowledge_assistant.core.interfaces.reranker import RerankResult

        self.calls.append(len(passages))
        return [RerankResult(index=i, score=1 - i / 100) for i in range(len(passages))][:top_n]


def _low_score_store():
    """Six chunks scoring far below the gate threshold, so `answerer.ask` stops at the gate and needs no LLM reply."""
    from tests.fakes import make_chunk

    chunks = [make_chunk(f"{i:02d}", i, f"Passage body {i}.", ("Doc", f"Part {i}")) for i in range(1, 7)]
    store = InMemoryVectorStore({c.chunk_id: 0.3 - n / 100 for n, c in enumerate(chunks)})
    store.upsert(chunks, [[1.0, 0.0]] * len(chunks))
    return store


def test_full_mode_builds_one_reranker_and_both_retrievers_of_an_arm_share_it(monkeypatch):
    """The reranker model is about 1.6 GB: `open_services` hands one instance to the run's retriever and to the answer
    service's retriever (same pattern as the GUI), so the model loads once per process, not twice."""
    import knowledge_assistant.composition as composition

    built, spy = [], _SpyReranker()

    def create_reranker():
        built.append(1)
        return spy

    monkeypatch.setattr(run_eval, "open_embedder", lambda: _Embedder())
    monkeypatch.setattr(run_eval, "open_vector_store", lambda arm: _low_score_store())
    monkeypatch.setattr(run_eval, "build_throttles", lambda settings: {})
    monkeypatch.setattr(run_eval, "create_llm", lambda settings, throttles, on_provider_error: ScriptedLLM())
    monkeypatch.setattr(composition, "create_reranker", create_reranker)  # what an unshared service would build its own with
    monkeypatch.setattr(run_eval, "create_reranker", create_reranker, raising=False)
    settings = run_eval.replace(run_eval.get_answer_settings(), allow_fallback=False)
    with run_eval.open_services("A", "full", settings, object()) as services:
        assert len(built) == 1  # one reranker for the two retrievers
        services.retriever.retrieve("Question?")
        assert services.answerer.ask("Question?").insufficient_reason == "retrieval_gate"
        assert len(spy.calls) == 2  # each retriever reranked with the one shared instance
    with run_eval.open_services("A", "retrieval", settings, object()) as services:  # retrieval mode: one retriever
        assert len(built) == 2 and services.answerer is None


def test_default_provider_none_leaves_the_retrieval_path_unchanged(monkeypatch):
    """RERANK_PROVIDER unset: the no-op reranker is built once, is never called, and scores stay the dense ones."""
    monkeypatch.delenv("RERANK_PROVIDER", raising=False)
    monkeypatch.setattr(run_eval, "open_embedder", lambda: _Embedder())
    monkeypatch.setattr(run_eval, "open_vector_store", lambda arm: _low_score_store())
    settings = run_eval.replace(run_eval.get_answer_settings(), allow_fallback=False)
    with run_eval.open_services("A", "retrieval", settings, object()) as services:
        result = services.retriever.retrieve("Question?")
        assert result.rerank_score is None and [c.score for c in result.chunks][:2] == [0.3, 0.29]


# --- corpus as a run dimension, question set v2 (ADR-0008) ---------------------------------------------------------

@pytest.fixture
def no_corpus_env(monkeypatch):
    monkeypatch.delenv("CORPUS", raising=False)


def test_resuming_with_another_corpus_aborts_and_the_environment_is_restored(project, no_corpus_env):
    import os

    assert go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "r1")[0] == 0
    _, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "r1",
                   "--corpus", "corpus2", "--cases", "Q-TEST-001")
    assert "another corpus" in err  # the v1 case is corpus 1: refused before the run is even opened
    assert "CORPUS" not in os.environ


def test_a_run_takes_only_its_corpus_cases_and_records_the_corpus(project, no_corpus_env):
    questions = project / "data" / "evaluation" / "questions"
    cases = [json.loads(line) for line in (questions / "dev-v1.jsonl").read_text(encoding="utf-8").splitlines()]
    cases[1]["corpus"] = "corpus2"
    digest = _write_jsonl(questions / "dev-v1.jsonl", cases)
    snapshot = project / "docs" / "snapshots" / "evaluation" / "eval-v1.md"
    lines = [line for line in snapshot.read_text(encoding="utf-8").splitlines() if "dev-v1" not in line]
    snapshot.write_text("\n".join(lines + [f"| `data/evaluation/questions/dev-v1.jsonl` SHA-256 | `{digest}` |"]),
                        encoding="utf-8")
    services = FakeServices()
    code, out, _ = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "c2",
                      "--corpus", "corpus2", services=services)
    assert code == 0 and "1 cases of corpus2" in out
    manifest = json.loads((project / "data/evaluation/results/c2/run.json").read_text(encoding="utf-8"))
    assert manifest["config"]["corpus"] == "corpus2"
    assert [r["case_id"] for r in results(project, "c2")[1]] == [cases[1]["id"]]
    code, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "c2",
                      "--corpus", "corpus1")
    assert code == 3 and ("corpus" in err)


def test_a_run_recorded_before_the_corpus_key_resumes_as_corpus1(project, no_corpus_env):
    assert go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "old",
              "--cases", "Q-TEST-001")[0] == 0
    path = project / "data/evaluation/results/old/run.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    del manifest["config"]["corpus"]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "old")[0] == 0
    code, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--run-id", "old",
                      "--corpus", "corpus2")
    assert code == 3


def test_v1_has_no_corpus2_case(project, no_corpus_env):
    code, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--corpus", "corpus2")
    assert code == 3 and "no case of corpus2" in err


def _git(root, *args):
    import subprocess

    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                   capture_output=True)


def test_v2_files_must_equal_their_version_at_the_freeze_tag(project, no_corpus_env):
    questions = project / "data" / "evaluation" / "questions"
    dev = [dict(make_case(n), id=f"Q2-DEV-{n:03d}", split="dev", corpus="corpus2") for n in (1, 2)]
    _write_jsonl(questions / "dev-v2.jsonl", dev)
    _write_jsonl(questions / "eval-v2.jsonl", [dict(make_case(9), id="Q2-EVAL-001", split="eval")])
    code, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--questions", "v2",
                      "--corpus", "corpus2")
    assert code == 3 and "eval-freeze-v2.1" in err  # no git repo / no tag: refused
    _git(project, "init", "-q")
    _git(project, "add", "data")
    _git(project, "commit", "-qm", "freeze")
    _git(project, "tag", "eval-freeze-v2.1")
    services = FakeServices()
    code, out, _ = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--questions", "v2",
                      "--corpus", "corpus2", "--run-id", "v2", services=services)
    assert code == 0 and "2 cases of corpus2" in out and "eval-freeze-v2.1" in out
    _write_jsonl(questions / "dev-v2.jsonl", dev[:1])
    code, _, err = go(project, "--arm", "A", "--mode", "retrieval", "--split", "dev", "--questions", "v2",
                      "--corpus", "corpus2", "--run-id", "v2")
    assert code == 3 and "differs from its frozen version" in err
