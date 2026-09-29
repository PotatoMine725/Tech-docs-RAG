"""CachingEmbedder(GeminiEmbedder): the path RAG-001b indexes with (verify F1/F2). Fake client and clock."""

import sqlite3
from types import SimpleNamespace

import pytest

from knowledge_assistant.config import get_embedding_settings
from knowledge_assistant.core.exceptions import EmbeddingError, QuotaExhaustedError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder
from knowledge_assistant.infrastructure.embeddings.throttle import SlidingWindowThrottle, estimate_tokens
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder
from tests.fakes import FakeClock, FakeModels, api_error

DOC = EmbeddingTask.DOCUMENT


def production_embedder(models: FakeModels, clock: FakeClock) -> GeminiEmbedder:
    """Real default limits (45 texts, 90 req/min, 25K tokens/min, 5 attempts); dim 4 for the fake vectors."""
    defaults = get_embedding_settings()
    settings = type(defaults)(**{**defaults.__dict__, "dim": 4})
    throttle = SlidingWindowThrottle(
        settings.requests_per_minute, settings.tokens_per_minute, clock=clock, sleep=clock.sleep
    )
    return GeminiEmbedder(
        settings, client=SimpleNamespace(models=models), throttle=throttle, sleep=clock.sleep, jitter=lambda: 0.0
    )


def texts_of(n: int, tokens: int) -> list[str]:
    return [f"{i:04d}".ljust(tokens * 4, "x") for i in range(n)]


def stored_rows(path) -> int:
    with sqlite3.connect(str(path)) as db:
        return db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "embeddings.sqlite"


def test_a_failed_second_call_keeps_the_first_calls_paid_vectors_and_a_rerun_pays_only_the_rest(db_path):
    """45 texts of 352 est. tokens = 15,840 > 12,500, so the embedder plans two calls (35 + 10)."""
    texts = texts_of(45, 352)
    clock = FakeClock()
    failing = FakeModels(fail_from_call=2, failure=api_error(503), clock=clock)
    with CachingEmbedder(production_embedder(failing, clock), db_path) as cache:
        with pytest.raises(EmbeddingError, match="after 5 attempts"):
            cache.embed(texts, DOC)
    assert [len(c["contents"]) for c in failing.calls] == [35] + [10] * 5
    assert stored_rows(db_path) == 35

    clock = FakeClock()
    healthy = FakeModels(clock=clock)
    with CachingEmbedder(production_embedder(healthy, clock), db_path) as cache:
        assert len(cache.embed(texts, DOC)) == 45
        assert cache.stats()["api_requests"] == 10
    assert [c["contents"] for c in healthy.calls] == [texts[35:]]
    assert stored_rows(db_path) == 45


def test_daily_quota_stop_keeps_earlier_calls_and_makes_no_retry(db_path):
    """The 14:00 scenario: call 1 succeeds, call 2 hits the daily quota."""
    texts = texts_of(45, 352)
    clock = FakeClock()
    daily = api_error(429, retry_delay="30s", quota_id="EmbedContentRequestsPerDayPerProjectPerModel-FreeTier")
    models = FakeModels(fail_from_call=2, failure=daily, clock=clock)
    with CachingEmbedder(production_embedder(models, clock), db_path) as cache:
        with pytest.raises(QuotaExhaustedError):
            cache.embed(texts, DOC)
    assert len(models.calls) == 2
    assert clock.sleeps == []
    assert stored_rows(db_path) == 35


def test_through_the_cache_every_http_call_is_one_cache_group_and_windows_stay_under_the_token_budget(db_path):
    """Worst-case chunks (435 est. tokens) through the real pipeline, default limits."""
    settings = get_embedding_settings()
    texts = texts_of(120, 435)
    clock = FakeClock()
    models = FakeModels(clock=clock)
    with CachingEmbedder(production_embedder(models, clock), db_path) as cache:
        cache.embed(texts, DOC)
        stats = cache.stats()

    assert len(models.calls) == stats["inner_calls"]
    sent = [(c["at"], sum(estimate_tokens(t) for t in c["contents"])) for c in models.calls]
    assert max(tokens for _, tokens in sent) <= settings.tokens_per_minute // 2
    for start, _ in sent:
        assert sum(tokens for t, tokens in sent if start <= t < start + 60) <= settings.tokens_per_minute
    assert stored_rows(db_path) == 120
