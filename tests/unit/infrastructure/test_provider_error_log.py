"""The first real 429 and 5xx bodies of a run are kept as evidence (EVAL-003a, owner addendum 2026-09-27).

RAG-003's open question: no real 429/503 had been seen on the LLM path, so `daily_quota_id` (built from the documented
error shape) was never checked against a real body. A 429 that a retry then fixes never reaches the caller as an error,
so the adapter reports every failed attempt to an optional hook and `FirstProviderErrors` keeps the first of each kind.
"""
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

from google.genai import errors

from knowledge_assistant.config import get_answer_settings
from knowledge_assistant.infrastructure.gemini_retry import Failure
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM
from knowledge_assistant.infrastructure.llm.gemini.provider_error_log import FirstProviderErrors
from tests.eval_fakes import MemoryRecordStore
from tests.fakes import FakeClock, api_error
from tests.unit.infrastructure.test_gemini_llm_resilience import FALLBACK, PRIMARY, REQUEST, ScriptedModels

FIXED_NOW = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
KEY = "AIza" + "x" * 35  # the shape of a Google API key


def make_llm(models, on_provider_error):
    """(llm, clock): the adapter on a fake client and a fake clock, with the hook under test."""
    clock = FakeClock()
    settings = replace(get_answer_settings(), model=PRIMARY, fallback_model=FALLBACK, allow_fallback=True, max_attempts=3)
    llm = GeminiLLM(settings, client=SimpleNamespace(models=models), clock=clock, sleep=clock.sleep,
                    jitter=lambda: 0.0, on_provider_error=on_provider_error)
    return llm, clock


def _failure(status, body='{"error": {"code": 0}}', **details) -> Failure:
    return Failure(kind="quota" if status == 429 else "unavailable", retryable=True, reason=f"HTTP {status}",
                   status=status, body=body, **details)


def _log(store):
    return FirstProviderErrors(store, run_id="run-1", now=lambda: FIXED_NOW)


def test_the_adapter_reports_every_failed_attempt_to_the_hook_before_the_retry():
    seen = []
    models = ScriptedModels({PRIMARY: [api_error(429), api_error(503)]})
    llm, _ = make_llm(models, lambda model, failure: seen.append((model, failure.status)))
    response = llm.generate(REQUEST)
    assert seen == [(PRIMARY, 429), (PRIMARY, 503)]  # both failed attempts, although the third call succeeded
    assert response.retry_count == 2


def test_the_first_429_and_the_first_5xx_body_are_saved_and_later_ones_are_not():
    store = MemoryRecordStore()
    log = _log(store)
    log(PRIMARY, _failure(429, '{"first": 429}', daily_quota_id=None, retry_after_s=7.0))
    log(PRIMARY, _failure(429, '{"second": 429}'))
    log(PRIMARY, _failure(503, '{"first": 503}'))
    log(PRIMARY, _failure(500, '{"second": 5xx}'))
    assert [(e["category"], e["body"]) for e in store.errors] == [("429", '{"first": 429}'), ("5xx", '{"first": 503}')]
    first = store.errors[0]
    assert first == {
        "type": "first_provider_error", "run_id": "run-1", "at": "2026-09-27T10:00:00.000+00:00", "category": "429",
        "status": 429, "model": PRIMARY, "reason": "HTTP 429", "retry_after_s": 7.0, "daily_quota_id": None,
        "body": '{"first": 429}',
    }


def test_failures_without_a_body_or_outside_429_and_5xx_are_not_evidence():
    store = MemoryRecordStore()
    log = _log(store)
    log(PRIMARY, Failure(kind="unavailable", retryable=True, reason="ReadTimeout"))  # transport error: no body
    log(PRIMARY, _failure(400))
    assert store.errors == []


def test_a_429_that_a_retry_fixed_is_still_saved_through_the_real_adapter():
    store = MemoryRecordStore()
    models = ScriptedModels({PRIMARY: [api_error(429, retry_delay="9s", quota_id="GenerateRequestsPerMinutePerProjectPerModel")]})
    llm, _ = make_llm(models, _log(store))
    response = llm.generate(REQUEST)
    assert response.retry_count == 1  # the caller saw a success ...
    [entry] = store.errors  # ... and the evidence is in the error log anyway
    assert (entry["category"], entry["status"], entry["model"], entry["retry_after_s"]) == ("429", 429, PRIMARY, 9.0)
    assert "GenerateRequestsPerMinutePerProjectPerModel" in entry["body"]
    assert entry["daily_quota_id"] is None  # a per-minute id is not a daily quota


def test_an_api_key_in_the_provider_body_never_reaches_the_error_log():
    store = MemoryRecordStore()
    leaking = errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": f"bad {KEY}"}})
    llm, _ = make_llm(ScriptedModels({PRIMARY: [leaking]}), _log(store))
    llm.generate(REQUEST)
    [entry] = store.errors
    assert KEY not in entry["body"] and "[REDACTED]" in entry["body"]


def test_a_hook_that_raises_changes_neither_retry_nor_result(caplog):
    def broken(model, failure):
        raise OSError("disk full")

    scripted = [api_error(429), api_error(503)]
    plain_models = ScriptedModels({PRIMARY: list(scripted)})
    plain, _ = make_llm(plain_models, None)
    expected = plain.generate(REQUEST)

    models = ScriptedModels({PRIMARY: list(scripted)})
    llm, _ = make_llm(models, broken)
    with caplog.at_level("WARNING"):
        response = llm.generate(REQUEST)
    assert response.retry_count == expected.retry_count == 2
    assert response.text == expected.text
    assert llm.requests == plain.requests == 3
    assert "provider-error hook failed" in caplog.text and "OSError" in caplog.text
    assert "disk full" not in caplog.text  # no body, no message: it may carry a path or a key
