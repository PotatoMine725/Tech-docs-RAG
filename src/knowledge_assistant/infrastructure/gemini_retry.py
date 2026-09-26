"""Retry, retry-after, quota classification and key redaction shared by the Gemini embedder and the Gemini LLM adapter.

Moved out of gemini_embedder.py (RAG-003, ADR-0004 amendment 2026-09-26) so both adapters retry and classify errors
the same way. `classify_failure` is the only place that knows which google.genai / httpx exceptions are provider
failures; an adapter turns a `Failure` into its own core error type, so no such exception leaves infrastructure.
"""
import json
import re
from dataclasses import dataclass

import httpx
from google.genai import errors

from knowledge_assistant.config import get_gemini_api_key

RETRYABLE_STATUS = {429, 500, 503, 504}
BACKOFF_BASE_S = 1.0  # 1, 2, 4, 8 ... seconds
MAX_RETRY_WAIT_S = 120.0  # a server retry-after above this is cut, so a run never hangs silently
DAILY_RESET = "14:00 UTC+7"  # free-tier daily quota reset (ADR-0005 D19)
DAILY_QUOTA = re.compile(r"per[ _-]?day|daily", re.IGNORECASE)
API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_\-]{35}")  # Google API key shape

# Worth another attempt: the request may well succeed a moment later.
TRANSIENT_TRANSPORT = (
    httpx.TimeoutException,
    httpx.NetworkError,  # ConnectError, ReadError, WriteError, CloseError
    httpx.RemoteProtocolError,  # the server closed the connection mid-response
    TimeoutError,
    ConnectionError,
)
# The request never got a response: refused, reset or closed. A subset of TRANSIENT_TRANSPORT (timeouts are not in it).
CONNECTION_ERRORS = (httpx.NetworkError, httpx.RemoteProtocolError, ConnectionError)
# Every exception the SDK or its HTTP client can raise for a provider or transport problem.
PROVIDER_ERRORS = (
    errors.APIError,
    errors.UnknownApiResponseError,
    httpx.HTTPError,
    httpx.StreamError,
    httpx.InvalidURL,
    TimeoutError,
    ConnectionError,
)


def error_details(error: errors.APIError) -> list[dict]:
    """The google.rpc detail objects of an API error body ({"error": {"details": [...]}})."""
    body = error.details.get("error", error.details) if isinstance(error.details, dict) else {}
    details = body.get("details", []) if isinstance(body, dict) else []
    return [item for item in details if isinstance(item, dict)] if isinstance(details, list) else []


def redact_key(text: str) -> str:
    """Remove the configured key and anything shaped like a Google API key before text is logged."""
    api_key = get_gemini_api_key()
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return API_KEY_PATTERN.sub("[REDACTED]", text)


def raw_body(error: errors.APIError) -> str:
    try:
        return json.dumps(error.details, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return repr(error.details)


def retry_after_s(error: errors.APIError) -> float | None:
    """Server-suggested wait: HTTP Retry-After header, or google.rpc.RetryInfo retryDelay."""
    headers = getattr(error.response, "headers", None)
    if headers is not None:
        value = headers.get("retry-after")
        if value:
            try:
                return float(value)
            except ValueError:
                pass
    for item in error_details(error):
        delay = item.get("retryDelay")
        match = re.fullmatch(r"(\d+(?:\.\d+)?)s", str(delay)) if delay else None
        if match:
            return float(match.group(1))
    return None


def daily_quota_id(error: errors.APIError) -> str | None:
    """The per-day quota a 429 names in its google.rpc.QuotaFailure violations, if any.

    Per-minute 429s carry a QuotaFailure too (e.g. "...PerMinute..."); only a per-day quota id or
    metric counts. Built from the documented error shape; not yet seen in a real response.
    """
    for item in error_details(error):
        if "QuotaFailure" not in str(item.get("@type", "")):
            continue
        for violation in item.get("violations") or []:
            if not isinstance(violation, dict):
                continue
            for field in ("quotaId", "quotaMetric"):
                value = str(violation.get(field) or "")
                if DAILY_QUOTA.search(value):
                    return value
    return None


def backoff_wait_s(attempt: int, retry_after: float | None, jitter: float) -> float:
    """Seconds to wait after failed attempt number `attempt` (1-based): exponential backoff plus jitter, or the
    server's retry-after when that is longer; one wait never exceeds MAX_RETRY_WAIT_S."""
    backoff = BACKOFF_BASE_S * 2 ** (attempt - 1) + jitter
    return min(max(backoff, retry_after or 0.0), MAX_RETRY_WAIT_S)


@dataclass(frozen=True)
class Failure:
    """A provider or transport failure, classified. `kind` is quota | unavailable | other (the GUI's kinds)."""

    kind: str
    retryable: bool  # another attempt on the same model may succeed (a daily-quota 429 never does)
    reason: str  # "HTTP 503 UNAVAILABLE" or the exception class name; no body text, safe to log
    status: int | None = None
    daily_quota_id: str | None = None
    retry_after_s: float | None = None
    body: str | None = None  # raw error body with the key redacted, for logs; API errors only
    connection_error: bool = False  # refused / reset / closed, as opposed to a timeout or an API error


def classify_failure(error: Exception) -> Failure | None:
    """None when `error` is not a provider or transport exception (a bug: the caller must not swallow it)."""
    if isinstance(error, errors.APIError):
        code = error.code
        daily = daily_quota_id(error) if code == 429 else None
        kind = "quota" if code == 429 else "unavailable" if code >= 500 else "other"
        return Failure(
            kind=kind,
            retryable=code in RETRYABLE_STATUS and daily is None,
            reason=f"HTTP {code} {error.status}",
            status=code,
            daily_quota_id=daily,
            retry_after_s=retry_after_s(error),
            body=redact_key(raw_body(error)),
        )
    if isinstance(error, TRANSIENT_TRANSPORT):
        return Failure(
            kind="unavailable",
            retryable=True,
            reason=type(error).__name__,
            connection_error=isinstance(error, CONNECTION_ERRORS),
        )
    if isinstance(error, PROVIDER_ERRORS):
        return Failure(kind="other", retryable=False, reason=type(error).__name__)
    return None
