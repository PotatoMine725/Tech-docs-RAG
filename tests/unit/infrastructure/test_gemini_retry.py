"""Retry, retry-after, quota classification and key redaction shared by the Gemini embedder and LLM (RAG-003).

These helpers were moved out of gemini_embedder.py (ADR-0004 amendment 2026-09-26); the embedder's own tests
still pass unchanged and prove the move kept its behavior.
"""
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from knowledge_assistant.infrastructure.gemini_retry import (
    MAX_RETRY_WAIT_S,
    backoff_wait_s,
    classify_failure,
    raw_body,
    redact_key,
    retry_after_s,
)
from tests.fakes import api_error

DAILY = "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
PER_MINUTE = "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"


def test_daily_quota_429_is_a_quota_failure_that_is_not_retryable():
    failure = classify_failure(api_error(429, quota_id=DAILY))
    assert (failure.kind, failure.retryable, failure.daily_quota_id) == ("quota", False, DAILY)
    assert failure.reason == "HTTP 429 RESOURCE_EXHAUSTED"


def test_per_minute_429_is_a_retryable_quota_failure_with_the_server_delay():
    failure = classify_failure(api_error(429, retry_delay="17s", quota_id=PER_MINUTE))
    assert (failure.kind, failure.retryable, failure.daily_quota_id) == ("quota", True, None)
    assert failure.retry_after_s == 17.0


@pytest.mark.parametrize("code", [500, 503, 504])
def test_transient_server_errors_are_retryable_unavailable_failures(code):
    failure = classify_failure(api_error(code))
    assert (failure.kind, failure.retryable) == ("unavailable", True)


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_other_client_errors_are_not_retryable(code):
    failure = classify_failure(errors.ClientError(code, {"error": {"code": code, "status": "X", "message": "m"}}))
    assert (failure.kind, failure.retryable) == ("other", False)


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        httpx.ConnectTimeout("slow"),
        httpx.ReadError("reset"),
        httpx.RemoteProtocolError("server disconnected"),
        TimeoutError("timed out"),
        ConnectionResetError("reset"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_timeouts_and_connection_errors_are_retryable_unavailable_failures(error):
    failure = classify_failure(error)
    assert (failure.kind, failure.retryable) == ("unavailable", True)
    assert failure.reason == type(error).__name__


@pytest.mark.parametrize(
    ("error", "connection"),
    [
        (httpx.ConnectError("refused"), True),
        (httpx.ReadError("reset"), True),
        (httpx.RemoteProtocolError("closed"), True),
        (ConnectionResetError("reset"), True),
        (httpx.ReadTimeout("slow"), False),
        (httpx.ConnectTimeout("slow"), False),
        (TimeoutError("timed out"), False),
    ],
    ids=lambda v: type(v).__name__ if not isinstance(v, bool) else str(v),
)
def test_connection_errors_are_told_apart_from_timeouts(error, connection):
    """The embedder retries timeouts but, by owner decision (ADR-0005 amendment 2), not connection errors."""
    assert classify_failure(error).connection_error is connection


def test_an_api_error_is_never_a_connection_error():
    assert classify_failure(api_error(503)).connection_error is False


@pytest.mark.parametrize("error", [httpx.UnsupportedProtocol("no scheme"), errors.UnknownApiResponseError("not json")])
def test_other_provider_side_exceptions_are_not_retryable(error):
    failure = classify_failure(error)
    assert (failure.kind, failure.retryable) == ("other", False)


def test_a_programming_error_is_not_a_provider_failure():
    assert classify_failure(KeyError("bug")) is None
    assert classify_failure(ValueError("bug")) is None


def test_failure_body_is_the_redacted_raw_body(monkeypatch):
    key = "AIza" + "x" * 35
    monkeypatch.setenv("GEMINI_API_KEY", key)
    error = errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": f"key {key}"}})
    body = classify_failure(error).body
    assert key not in body and "[REDACTED]" in body and "RESOURCE_EXHAUSTED" in body


def test_backoff_is_exponential_plus_jitter():
    assert backoff_wait_s(1, None, 0.0) == 1.0
    assert backoff_wait_s(2, None, 0.0) == 2.0
    assert backoff_wait_s(3, None, 0.25) == 4.25


def test_backoff_honours_a_longer_server_delay_and_ignores_a_shorter_one():
    assert backoff_wait_s(1, 17.0, 0.0) == 17.0
    assert backoff_wait_s(3, 1.0, 0.0) == 4.0


def test_any_single_wait_is_capped_at_120_s():
    assert MAX_RETRY_WAIT_S == 120.0
    assert backoff_wait_s(1, 36000.0, 0.0) == 120.0
    assert backoff_wait_s(30, None, 0.9) == 120.0


def test_retry_after_prefers_the_http_header_then_retry_info():
    with_header = api_error(503)
    with_header.response = SimpleNamespace(headers={"retry-after": "7"})
    assert retry_after_s(with_header) == 7.0
    assert retry_after_s(api_error(429, retry_delay="2.5s")) == 2.5
    assert retry_after_s(api_error(503)) is None


def test_redact_key_removes_the_configured_key_and_key_shaped_text(monkeypatch):
    key = "AIza" + "y" * 35
    monkeypatch.setenv("GEMINI_API_KEY", "custom-secret-value")
    text = redact_key(f"a custom-secret-value b {key} c")
    assert "custom-secret-value" not in text and key not in text and text.count("[REDACTED]") == 2


def test_raw_body_is_stable_json():
    assert raw_body(api_error(503)).startswith('{"error"')
