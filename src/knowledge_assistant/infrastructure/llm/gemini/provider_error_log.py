"""Keep the first real HTTP 429 and the first real 5xx body of an evaluation run (EVAL-003a).

Used as `GeminiLLM(on_provider_error=...)`: the adapter calls it for every failed attempt, also the ones a retry then
fixes, which never reach the caller as an error. The body is the provider's own JSON with the key already redacted
(`classify_failure`) and redacted again by the record store. It is evidence for RAG-003's open question: no real 429 or
503 had been seen on the LLM path, so the daily-quota detection was only checked against the documented error shape.
Transport errors (timeouts, connection resets) have no body and are not kept.
"""
from collections.abc import Callable
from datetime import datetime, timezone

from knowledge_assistant.core.interfaces.record_store import RecordStore
from knowledge_assistant.infrastructure.gemini_retry import Failure


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FirstProviderErrors:
    def __init__(self, store: RecordStore, run_id: str, now: Callable[[], datetime] = _utc_now) -> None:
        self._store = store
        self._run_id = run_id
        self._now = now
        self._seen: set[str] = set()  # per instance, so once per process; a resumed invocation keeps its own first

    def __call__(self, model: str, failure: Failure) -> None:
        if failure.status is None or failure.body is None:
            return
        category = "429" if failure.status == 429 else "5xx" if failure.status >= 500 else None
        if category is None or category in self._seen:
            return
        self._seen.add(category)
        self._store.append_error({
            "type": "first_provider_error",
            "run_id": self._run_id,
            "at": self._now().isoformat(timespec="milliseconds"),
            "category": category,
            "status": failure.status,
            "model": model,
            "reason": failure.reason,
            "retry_after_s": failure.retry_after_s,
            "daily_quota_id": failure.daily_quota_id,
            "body": failure.body,
        })
