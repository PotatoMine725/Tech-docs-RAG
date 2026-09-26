"""GeminiLLM retry, backoff, fallback, throttle and error classification (RAG-003, ADR-0004 amendment). No network.

Policy under test (owner, 2026-09-26): up to 3 attempts on the answer model (429 per-minute, 503, timeouts, connection
errors) with exponential backoff, jitter and retry-after (each wait capped at 120 s); then the fallback model gets ONE
attempt; a daily-quota 429 skips the retries; ALLOW_FALLBACK=false never calls the fallback.
"""
import logging
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from knowledge_assistant.config import get_answer_settings
from knowledge_assistant.core.exceptions import (
    GenerationError,
    LLMError,
    LLMQuotaError,
    LLMRequestError,
    LLMUnavailableError,
)
from knowledge_assistant.core.interfaces.llm import LLMRequest
from knowledge_assistant.infrastructure.embeddings.throttle import SlidingWindowThrottle
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM
from knowledge_assistant.infrastructure.llm.gemini.gemini_llm import build_throttles
from tests.fakes import FakeClock, api_error

PRIMARY, FALLBACK = "primary-model", "fallback-model"
DAILY = "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
PER_MINUTE = "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"


def reply(text='{"ok": true}', finish="STOP", usage=(120, 30, 5)):
    metadata = None if usage is None else SimpleNamespace(
        prompt_token_count=usage[0], candidates_token_count=usage[1], thoughts_token_count=usage[2]
    )
    return SimpleNamespace(
        text=text, candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=finish))], usage_metadata=metadata
    )


class ScriptedModels:
    """client.models: `script[model]` holds outcomes consumed one per call of that model.

    An exception is raised, anything else is returned as the response; when a model's script is used up it succeeds.
    """

    def __init__(self, script: dict[str, list] | None = None, clock: FakeClock | None = None, call_seconds: float = 0.0):
        self.script = {model: list(outcomes) for model, outcomes in (script or {}).items()}
        self.calls: list[str] = []
        self._clock = clock
        self._call_seconds = call_seconds  # how long the fake HTTP call "takes" on the shared test clock

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        if self._clock is not None:
            self._clock.now += self._call_seconds
        outcomes = self.script.get(model, [])
        outcome = outcomes.pop(0) if outcomes else reply()
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def make_llm(models, *, clock=None, throttle_rpm=None, allow_fallback=True, attempts=3, jitter=0.0, **settings_changes):
    """(llm, clock). `throttle_rpm=(answer, fallback)` puts per-minute throttles on the same test clock as the sleeps."""
    clock = clock or FakeClock()
    changes = dict(model=PRIMARY, fallback_model=FALLBACK, allow_fallback=allow_fallback, max_attempts=attempts)
    settings = replace(get_answer_settings(), **{**changes, **settings_changes})
    throttles = None
    if throttle_rpm is not None:
        throttles = {
            model: SlidingWindowThrottle(rpm, 250_000, clock=clock, sleep=clock.sleep)
            for model, rpm in zip((PRIMARY, FALLBACK), throttle_rpm)
        }
    llm = GeminiLLM(
        settings,
        client=SimpleNamespace(models=models),
        clock=clock,
        sleep=clock.sleep,
        jitter=lambda: jitter,
        throttles=throttles,
    )
    return llm, clock


REQUEST = LLMRequest("PROMPT")


# --- retry on the answer model -----------------------------------------------------------------------------------


def test_503_then_success_is_retried_once_with_a_one_second_backoff():
    models = ScriptedModels({PRIMARY: [api_error(503)]})
    llm, clock = make_llm(models)
    response = llm.generate(REQUEST)
    assert models.calls == [PRIMARY, PRIMARY]
    assert (response.model_used, response.retry_count, response.fallback_used) == (PRIMARY, 1, False)
    assert clock.sleeps == [1.0]
    assert response.retry_wait_ms == 1000.0


def test_two_failures_then_success_uses_all_three_attempts_with_doubling_backoff():
    models = ScriptedModels({PRIMARY: [api_error(503), api_error(503)]})
    llm, clock = make_llm(models)
    response = llm.generate(REQUEST)
    assert models.calls == [PRIMARY] * 3
    assert clock.sleeps == [1.0, 2.0]
    assert (response.retry_count, response.retry_wait_ms, response.fallback_used) == (2, 3000.0, False)


def test_jitter_is_added_to_the_backoff():
    llm, clock = make_llm(ScriptedModels({PRIMARY: [api_error(503), api_error(503)]}), jitter=0.5)
    llm.generate(REQUEST)
    assert clock.sleeps == [1.5, 2.5]


@pytest.mark.parametrize(
    "transient",
    [
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        api_error(503),
        api_error(500),
        api_error(429, retry_delay="1s", quota_id=PER_MINUTE),
    ],
    ids=["ConnectError", "ReadTimeout", "503", "500", "429-per-minute"],
)
def test_transient_failures_are_retried_and_the_retry_is_counted(transient):
    models = ScriptedModels({PRIMARY: [transient]})
    llm, _ = make_llm(models)
    response = llm.generate(REQUEST)
    assert models.calls == [PRIMARY, PRIMARY]
    assert (response.retry_count, response.fallback_used) == (1, False)


def test_per_minute_429_waits_for_the_server_retry_delay_when_it_is_longer_than_the_backoff():
    models = ScriptedModels({PRIMARY: [api_error(429, retry_delay="17s", quota_id=PER_MINUTE)]})
    llm, clock = make_llm(models)
    llm.generate(REQUEST)
    assert clock.sleeps == [17.0]


def test_a_retry_after_longer_than_120_s_is_capped():
    models = ScriptedModels({PRIMARY: [api_error(429, retry_delay="36000s", quota_id=PER_MINUTE)] * 2})
    llm, clock = make_llm(models)
    response = llm.generate(REQUEST)
    assert clock.sleeps == [120.0, 120.0]
    assert response.retry_wait_ms == 240_000.0


def test_every_wait_is_logged_with_model_attempt_and_reason(caplog):
    llm, _ = make_llm(ScriptedModels({PRIMARY: [api_error(503)]}))
    with caplog.at_level(logging.WARNING):
        llm.generate(REQUEST)
    [line] = [r.getMessage() for r in caplog.records if "retrying in" in r.getMessage()]
    assert PRIMARY in line and "HTTP 503" in line and "attempt 1/3" in line and "retrying in 1.0 s" in line


# --- fallback ----------------------------------------------------------------------------------------------------


def test_three_transient_failures_then_the_fallback_answers_once():
    models = ScriptedModels({PRIMARY: [api_error(503)] * 3})
    llm, clock = make_llm(models)
    response = llm.generate(REQUEST)
    assert models.calls == [PRIMARY, PRIMARY, PRIMARY, FALLBACK]
    assert response.fallback_used is True and response.model_used == FALLBACK
    assert response.retry_count == 2  # primary retries only; the fallback call is not a retry
    assert clock.sleeps == [1.0, 2.0]  # no wait before the fallback
    assert (llm.requests, llm.requests_by_model) == (4, {PRIMARY: 3, FALLBACK: 1})


def test_the_fallback_gets_exactly_one_attempt():
    models = ScriptedModels({PRIMARY: [api_error(503)] * 3, FALLBACK: [api_error(503)] * 5})
    llm, _ = make_llm(models)
    with pytest.raises(LLMUnavailableError) as raised:
        llm.generate(REQUEST)
    assert models.calls == [PRIMARY, PRIMARY, PRIMARY, FALLBACK]
    assert raised.value.fallback_attempted is True and raised.value.retry_count == 2


def test_daily_quota_skips_the_retries_and_goes_straight_to_one_fallback_call():
    models = ScriptedModels({PRIMARY: [api_error(429, quota_id=DAILY)]})
    llm, clock = make_llm(models)
    response = llm.generate(REQUEST)
    assert models.calls == [PRIMARY, FALLBACK]
    assert clock.sleeps == []
    assert (response.model_used, response.fallback_used, response.retry_count) == (FALLBACK, True, 0)


def test_daily_quota_on_both_models_raises_the_quota_error_after_one_call_each():
    models = ScriptedModels({PRIMARY: [api_error(429, quota_id=DAILY)], FALLBACK: [api_error(429, quota_id=DAILY)]})
    llm, clock = make_llm(models)
    with pytest.raises(LLMQuotaError) as raised:
        llm.generate(REQUEST)
    assert models.calls == [PRIMARY, FALLBACK] and clock.sleeps == []
    assert raised.value.daily is True and raised.value.kind == "quota"
    assert "14:00 UTC+7" in str(raised.value)


def test_a_per_minute_429_that_survives_every_attempt_is_a_quota_error_that_is_not_daily():
    per_minute = api_error(429, retry_delay="1s", quota_id=PER_MINUTE)
    models = ScriptedModels({PRIMARY: [per_minute] * 3, FALLBACK: [per_minute]})
    llm, _ = make_llm(models)
    with pytest.raises(LLMQuotaError) as raised:
        llm.generate(REQUEST)
    assert models.calls == [PRIMARY] * 3 + [FALLBACK]
    assert raised.value.daily is False


def test_when_both_models_fail_the_error_describes_the_answer_model_not_the_fallback():
    daily = api_error(429, quota_id=DAILY)
    cases = [  # (primary script, fallback script, expected error type)
        ([daily], [api_error(503)], LLMQuotaError),
        ([api_error(503)] * 3, [api_error(429, quota_id=DAILY)], LLMUnavailableError),
        ([api_error(503)] * 3, [api_error(400)], LLMUnavailableError),
    ]
    for primary, fallback, expected in cases:
        models = ScriptedModels({PRIMARY: primary, FALLBACK: fallback})
        llm, _ = make_llm(models)
        with pytest.raises(expected) as raised:
            llm.generate(REQUEST)
        assert type(raised.value) is expected
        assert FALLBACK in str(raised.value)  # the fallback's failure is told, not hidden
        assert isinstance(raised.value.__cause__, errors.APIError)  # the answer model's provider error


def test_a_fallback_model_equal_to_the_answer_model_is_not_called_twice():
    models = ScriptedModels({PRIMARY: [api_error(503)] * 3})
    llm, _ = make_llm(models, fallback_model=PRIMARY)
    with pytest.raises(LLMUnavailableError):
        llm.generate(REQUEST)
    assert models.calls == [PRIMARY] * 3


# --- ALLOW_FALLBACK=false ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcomes", "expected", "calls"),
    [
        ([api_error(503)] * 3, LLMUnavailableError, 3),
        ([api_error(429, retry_delay="1s", quota_id=PER_MINUTE)] * 3, LLMQuotaError, 3),
        ([httpx.ConnectError("refused")] * 3, LLMUnavailableError, 3),
        ([api_error(429, quota_id=DAILY)], LLMQuotaError, 1),
    ],
    ids=["503", "429-per-minute", "ConnectError", "429-daily"],
)
def test_with_the_fallback_disabled_the_classified_error_is_raised_and_the_fallback_is_never_called(
    outcomes, expected, calls
):
    models = ScriptedModels({PRIMARY: outcomes})
    llm, _ = make_llm(models, allow_fallback=False)
    with pytest.raises(expected) as raised:
        llm.generate(REQUEST)
    assert models.calls == [PRIMARY] * calls
    assert FALLBACK not in models.calls and raised.value.fallback_attempted is False


def test_the_fallback_is_off_when_allow_fallback_is_false_in_the_environment(monkeypatch):
    monkeypatch.setenv("ALLOW_FALLBACK", "false")
    models = ScriptedModels({PRIMARY: [api_error(503)] * 3})
    llm = GeminiLLM(
        replace(get_answer_settings(), model=PRIMARY, fallback_model=FALLBACK),
        client=SimpleNamespace(models=models),
        sleep=lambda seconds: None,
        jitter=lambda: 0.0,
    )
    with pytest.raises(LLMUnavailableError):
        llm.generate(REQUEST)
    assert FALLBACK not in models.calls


# --- errors that are not retried -------------------------------------------------------------------------------------


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_a_non_retryable_error_fails_at_once_without_retry_or_fallback(code):
    error = errors.ClientError(code, {"error": {"code": code, "status": "INVALID_ARGUMENT", "message": "bad"}})
    models = ScriptedModels({PRIMARY: [error]})
    llm, clock = make_llm(models)
    with pytest.raises(LLMRequestError) as raised:
        llm.generate(REQUEST)
    assert models.calls == [PRIMARY] and clock.sleeps == []
    assert raised.value.kind == "other" and raised.value.fallback_attempted is False


def test_unusable_output_is_a_generation_error_and_is_neither_retried_nor_sent_to_the_fallback():
    models = ScriptedModels({PRIMARY: [reply(text='{"answer": "cut', finish="MAX_TOKENS")]})
    llm, clock = make_llm(models)
    with pytest.raises(GenerationError):
        llm.generate(REQUEST)
    assert models.calls == [PRIMARY] and clock.sleeps == []


def test_a_programming_error_is_not_swallowed_as_an_llm_error():
    llm, _ = make_llm(ScriptedModels({PRIMARY: [KeyError("bug")]}))
    with pytest.raises(KeyError):
        llm.generate(REQUEST)


# --- classification: no raw provider exception escapes ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("make_error", "expected"),
    [
        (lambda: api_error(429, retry_delay="1s", quota_id=PER_MINUTE), LLMQuotaError),
        (lambda: api_error(429, quota_id=DAILY), LLMQuotaError),
        (lambda: api_error(503), LLMUnavailableError),
        (lambda: httpx.ConnectError("refused"), LLMUnavailableError),
        (lambda: httpx.ReadTimeout("slow"), LLMUnavailableError),
        (lambda: httpx.RemoteProtocolError("server disconnected"), LLMUnavailableError),
        (lambda: httpx.UnsupportedProtocol("no scheme"), LLMRequestError),
        (lambda: errors.UnknownApiResponseError("not json"), LLMRequestError),
    ],
    ids=["429-per-minute", "429-daily", "503", "ConnectError", "ReadTimeout", "RemoteProtocolError",
         "UnsupportedProtocol", "UnknownApiResponse"],
)
@pytest.mark.parametrize("allow_fallback", [True, False], ids=["fallback-on", "fallback-off"])
def test_no_raw_google_or_httpx_exception_escapes_and_the_kind_matches(make_error, expected, allow_fallback):
    models = ScriptedModels({PRIMARY: [make_error() for _ in range(5)], FALLBACK: [make_error() for _ in range(5)]})
    llm, _ = make_llm(models, allow_fallback=allow_fallback)
    with pytest.raises(LLMError) as raised:
        llm.generate(REQUEST)
    error = raised.value
    assert type(error) is expected
    assert not isinstance(error, (errors.APIError, httpx.HTTPError, TimeoutError, ConnectionError))
    assert error.model == PRIMARY
    assert isinstance(error.__cause__, (errors.APIError, httpx.HTTPError, errors.UnknownApiResponseError))


def test_the_llm_error_kinds_are_the_gui_kinds():
    kinds = {LLMQuotaError.kind, LLMUnavailableError.kind, LLMRequestError.kind}
    assert kinds == {"quota", "unavailable", "other"}
    assert LLMError.kind == "other"
    assert all(issubclass(cls, LLMError) for cls in (LLMQuotaError, LLMUnavailableError, LLMRequestError))


# --- the key never leaves the adapter --------------------------------------------------------------------------------


def test_the_key_is_redacted_from_error_text_provider_body_and_logs(monkeypatch, caplog):
    key = "AIza" + "z" * 35
    monkeypatch.setenv("GEMINI_API_KEY", key)
    leaky = errors.ClientError(
        429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": f"bad key {key}"}}
    )
    models = ScriptedModels({PRIMARY: [leaky] * 3, FALLBACK: [leaky]})
    llm, _ = make_llm(models)
    with caplog.at_level(logging.DEBUG), pytest.raises(LLMQuotaError) as raised:
        llm.generate(REQUEST)
    assert key not in str(raised.value)
    assert key not in raised.value.provider_body and "[REDACTED]" in raised.value.provider_body
    assert key not in caplog.text


def test_only_the_first_429_body_of_a_run_is_logged_raw(caplog):
    per_minute = api_error(429, retry_delay="1s", quota_id=PER_MINUTE)
    llm, _ = make_llm(ScriptedModels({PRIMARY: [per_minute] * 2}))
    with caplog.at_level(logging.WARNING):
        llm.generate(REQUEST)
    raw = [r.getMessage() for r in caplog.records if "raw error body" in r.getMessage()]
    assert len(raw) == 1 and "RESOURCE_EXHAUSTED" in raw[0]


def test_503_bodies_are_not_logged_raw(caplog):
    llm, _ = make_llm(ScriptedModels({PRIMARY: [api_error(503)]}))
    with caplog.at_level(logging.WARNING):
        llm.generate(REQUEST)
    assert not [r for r in caplog.records if "raw error body" in r.getMessage()]


# --- token accounting --------------------------------------------------------------------------------------------------


def test_token_counts_come_from_the_usage_metadata():
    llm, _ = make_llm(ScriptedModels({PRIMARY: [reply(usage=(1200, 80, 33))]}))
    response = llm.generate(REQUEST)
    assert (response.prompt_tokens, response.output_tokens, response.thoughts_tokens) == (1200, 80, 33)
    assert llm.last_usage == {"prompt_tokens": 1200, "output_tokens": 80, "thoughts_tokens": 33}


@pytest.mark.parametrize("usage", [None, (None, None, None), (100, 10, None)], ids=["no-metadata", "all-none", "no-thoughts"])
def test_tokens_the_provider_does_not_report_are_none_not_zero(usage):
    llm, _ = make_llm(ScriptedModels({PRIMARY: [reply(usage=usage)]}))
    response = llm.generate(REQUEST)
    expected = (None, None, None) if usage is None else usage
    assert (response.prompt_tokens, response.output_tokens, response.thoughts_tokens) == expected


def test_a_fallback_answer_carries_the_fallback_call_tokens_and_latency():
    models = ScriptedModels({PRIMARY: [api_error(503)] * 3, FALLBACK: [reply(usage=(900, 40, 7))]})
    llm, _ = make_llm(models)
    response = llm.generate(REQUEST)
    assert (response.prompt_tokens, response.output_tokens, response.thoughts_tokens) == (900, 40, 7)
    assert response.latency_ms == 0.0  # the fake clock does not move during a call


def test_model_latency_is_the_successful_call_only_and_excludes_the_backoff_wait():
    clock = FakeClock()
    models = ScriptedModels({PRIMARY: [api_error(503)]}, clock=clock, call_seconds=0.25)
    llm, _ = make_llm(models, clock=clock)
    response = llm.generate(REQUEST)
    assert response.latency_ms == pytest.approx(250.0)  # the second call; the failed call and the 1 s wait are not in it
    assert response.retry_wait_ms == 1000.0


# --- throttle ---------------------------------------------------------------------------------------------------------


def test_default_throttles_come_from_config_13_rpm_for_the_answer_model_and_4_for_the_fallback():
    clock = FakeClock()
    settings = get_answer_settings()
    throttles = build_throttles(settings, clock=clock, sleep=clock.sleep)
    assert set(throttles) == {settings.model, settings.fallback_model}
    for model, rpm in ((settings.model, 13), (settings.fallback_model, 4)):
        assert [throttles[model].acquire(0) for _ in range(rpm)] == [0.0] * rpm  # rpm calls fit the window
        assert throttles[model].acquire(0) == pytest.approx(60.0)  # the next one waits for the window to slide


def test_the_throttle_wait_is_reported_apart_from_the_backoff_wait():
    llm, _ = make_llm(ScriptedModels(), throttle_rpm=(1, 1))
    first = llm.generate(REQUEST)
    second = llm.generate(REQUEST)
    assert (first.throttle_wait_ms, first.retry_wait_ms) == (0.0, 0.0)
    assert second.throttle_wait_ms == pytest.approx(60_000.0)
    assert second.retry_wait_ms == 0.0


def test_every_attempt_is_throttled_and_the_fallback_has_its_own_window():
    models = ScriptedModels({PRIMARY: [api_error(503)] * 3})
    llm, clock = make_llm(models, throttle_rpm=(1, 1))
    response = llm.generate(REQUEST)
    assert response.fallback_used
    assert clock.sleeps == [1.0, 59.0, 2.0, 58.0]  # backoff, throttle, backoff, throttle; nothing before the fallback
    assert response.retry_wait_ms == pytest.approx(3000.0)
    assert response.throttle_wait_ms == pytest.approx(117_000.0)
