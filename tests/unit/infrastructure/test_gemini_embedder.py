import math
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from knowledge_assistant.config import EmbeddingSettings, get_embedding_settings
from knowledge_assistant.core.exceptions import ConfigurationError, EmbeddingError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder, l2_normalize
from knowledge_assistant.infrastructure.embeddings.throttle import SlidingWindowThrottle, estimate_tokens


def make_settings(**overrides) -> EmbeddingSettings:
    values = dict(
        model="test-embedding-model",
        dim=4,
        batch_size=2,
        requests_per_minute=100,
        tokens_per_minute=10_000,
        max_attempts=4,
        timeout_s=5,
        cache_path="unused",
    )
    values.update(overrides)
    return EmbeddingSettings(**values)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeModels:
    """Stands in for client.models; `script` holds exceptions to raise, in order, before succeeding."""

    def __init__(self, dim: int = 4, script: list[Exception] | None = None, raw: list[float] | None = None):
        self.dim = dim
        self.script = list(script or [])
        self.raw = raw
        self.calls: list[dict] = []

    def embed_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": list(contents), "config": config})
        if self.script:
            raise self.script.pop(0)
        values = self.raw or [3.0, 4.0] + [0.0] * (self.dim - 2)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=list(values)) for _ in contents])


def make_embedder(models: FakeModels, clock: FakeClock | None = None, **overrides) -> GeminiEmbedder:
    settings = make_settings(**overrides)
    clock = clock or FakeClock()
    throttle = SlidingWindowThrottle(
        settings.requests_per_minute, settings.tokens_per_minute, clock=clock, sleep=clock.sleep
    )
    return GeminiEmbedder(
        settings, client=SimpleNamespace(models=models), throttle=throttle, sleep=clock.sleep, jitter=lambda: 0.0
    )


def server_error(code: int = 503, retry_delay: str | None = None) -> errors.APIError:
    error = {"code": code, "status": "UNAVAILABLE", "message": "overloaded"}
    if retry_delay:
        error["details"] = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay}]
    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {"error": error})


# --- config -----------------------------------------------------------------


def test_model_id_combines_configured_model_and_dim():
    assert make_embedder(FakeModels()).model_id == "test-embedding-model@4"


def test_default_settings_come_from_config_and_env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_DIM", "1536")
    monkeypatch.setenv("EMBEDDING_MODEL", "some-model")
    settings = get_embedding_settings()
    assert (settings.model, settings.dim, settings.model_id) == ("some-model", 1536, "some-model@1536")


def test_missing_api_key_raises_configuration_error_without_a_call(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        GeminiEmbedder(make_settings()).embed(["x"], EmbeddingTask.DOCUMENT)


# --- request shape ----------------------------------------------------------


def test_task_types_and_dim_are_sent_and_texts_are_batched():
    models = FakeModels()
    embedder = make_embedder(models)
    embedder.embed(["a", "b", "c"], EmbeddingTask.DOCUMENT)
    embedder.embed(["q"], EmbeddingTask.QUERY)
    assert [c["contents"] for c in models.calls] == [["a", "b"], ["c"], ["q"]]
    assert [c["config"].task_type for c in models.calls] == ["RETRIEVAL_DOCUMENT"] * 2 + ["RETRIEVAL_QUERY"]
    assert {c["config"].output_dimensionality for c in models.calls} == {4}
    assert {c["model"] for c in models.calls} == {"test-embedding-model"}


def test_batches_are_capped_at_half_the_tokens_per_minute():
    models = FakeModels()
    text = "x" * 400  # 100 estimated tokens
    make_embedder(models, batch_size=10, tokens_per_minute=500).embed([text] * 5, EmbeddingTask.DOCUMENT)
    assert [len(c["contents"]) for c in models.calls] == [2, 2, 1]  # 250-token cap per call


# --- normalization and dimension -------------------------------------------


def test_vectors_below_full_size_are_l2_normalized():
    [vector] = make_embedder(FakeModels()).embed(["a"], EmbeddingTask.DOCUMENT)
    assert vector == pytest.approx([0.6, 0.8, 0.0, 0.0])
    assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0)


def test_full_size_vectors_are_returned_unchanged():
    raw = [3.0, 4.0] + [0.0] * 3070
    [vector] = make_embedder(FakeModels(dim=3072, raw=raw), dim=3072).embed(["a"], EmbeddingTask.DOCUMENT)
    assert vector == raw


def test_wrong_dimension_raises():
    with pytest.raises(EmbeddingError, match="dimension"):
        make_embedder(FakeModels(dim=5), dim=4).embed(["a"], EmbeddingTask.DOCUMENT)


def test_zero_vector_cannot_be_normalized():
    with pytest.raises(EmbeddingError):
        l2_normalize([0.0, 0.0])


# --- retry -------------------------------------------------------------------


def test_503_twice_then_success_takes_three_attempts_with_backoff():
    clock = FakeClock()
    models = FakeModels(script=[server_error(503), server_error(503)])
    embedder = make_embedder(models, clock)
    assert len(embedder.embed(["a"], EmbeddingTask.DOCUMENT)) == 1
    assert len(models.calls) == 3
    assert clock.sleeps == [1.0, 2.0]
    assert embedder.stats()["api_requests"] == 3 and embedder.stats()["retries"] == 2


def test_always_failing_raises_embedding_error_after_max_attempts():
    clock = FakeClock()
    models = FakeModels(script=[server_error(503)] * 10)
    with pytest.raises(EmbeddingError, match="after 4 attempts"):
        make_embedder(models, clock, max_attempts=4).embed(["a"], EmbeddingTask.DOCUMENT)
    assert len(models.calls) == 4
    assert clock.sleeps == [1.0, 2.0, 4.0]


def test_timeouts_are_retried():
    models = FakeModels(script=[httpx.ReadTimeout("slow")])
    make_embedder(models).embed(["a"], EmbeddingTask.DOCUMENT)
    assert len(models.calls) == 2


def test_429_honours_retry_delay_when_longer_than_backoff():
    clock = FakeClock()
    models = FakeModels(script=[server_error(429, retry_delay="17s")])
    make_embedder(models, clock).embed(["a"], EmbeddingTask.DOCUMENT)
    assert clock.sleeps == [17.0]


def test_non_retryable_error_fails_immediately():
    models = FakeModels(script=[server_error(400)])
    with pytest.raises(EmbeddingError, match="400"):
        make_embedder(models).embed(["a"], EmbeddingTask.DOCUMENT)
    assert len(models.calls) == 1


# --- throttle ----------------------------------------------------------------


def test_throttle_waits_when_requests_per_minute_are_used_up():
    clock = FakeClock()
    throttle = SlidingWindowThrottle(3, 10_000, clock=clock, sleep=clock.sleep)
    for _ in range(3):
        assert throttle.acquire(1) == 0.0
        clock.now += 1.0
    assert throttle.acquire(1) == pytest.approx(57.0)  # first request at t=0 leaves the window at t=60
    assert clock.now == pytest.approx(60.0)


def test_throttle_waits_when_tokens_per_minute_are_used_up():
    clock = FakeClock()
    throttle = SlidingWindowThrottle(100, 1_000, clock=clock, sleep=clock.sleep)
    throttle.acquire(600)
    clock.now = 10.0
    throttle.acquire(300)
    clock.now = 20.0
    assert throttle.acquire(300) == pytest.approx(40.0)  # waits until the 600 leaves at t=60
    clock.now = 65.0
    assert throttle.acquire(500) == pytest.approx(5.0)  # 300 + 300 in window; waits until t=70


def test_n_requests_over_the_limit_wait_the_expected_total_time():
    clock = FakeClock()
    models = FakeModels()
    embedder = make_embedder(models, clock, batch_size=1, requests_per_minute=2)
    embedder.embed(["a", "b", "c", "d", "e"], EmbeddingTask.DOCUMENT)
    # 2 per 60 s window: requests at t=0, 0, 60, 60, 120
    assert clock.now == pytest.approx(120.0)
    assert embedder.stats()["throttle_wait_s"] == pytest.approx(120.0)


def test_request_larger_than_the_token_limit_raises_instead_of_waiting_forever():
    throttle = SlidingWindowThrottle(100, 100, clock=FakeClock(), sleep=lambda s: None)
    with pytest.raises(EmbeddingError):
        throttle.acquire(101)
    with pytest.raises(EmbeddingError):
        throttle.acquire(1, requests=101)


def test_every_text_in_a_batched_call_counts_as_one_quota_request():
    """V-1 (ADR-0005): one HTTP call with 3 texts moved AI Studio's RPM from 0 to 3."""
    clock = FakeClock()
    models = FakeModels()
    embedder = make_embedder(models, clock, batch_size=3, requests_per_minute=4)
    embedder.embed(["a", "b", "c", "d", "e", "f"], EmbeddingTask.DOCUMENT)
    # 3 + 3 > 4 per window, so the second call waits a full minute
    assert len(models.calls) == 2
    assert clock.now == pytest.approx(60.0)
    stats = embedder.stats()
    assert (stats["http_calls"], stats["api_requests"]) == (2, 6)


def test_throttle_holds_two_worst_case_calls_to_the_token_budget_over_60s():
    """Owner check: two raw 45-text calls of the largest chunk (~19.6K each, ~39K) exceed the 25K cap."""
    clock = FakeClock()
    throttle = SlidingWindowThrottle(90, 25_000, clock=clock, sleep=clock.sleep)
    worst_call = 45 * estimate_tokens("x" * 1738)  # 45 x 435 = 19,575
    assert throttle.acquire(worst_call, requests=45) == 0.0
    clock.now = 1.0
    assert throttle.acquire(worst_call, requests=45) == pytest.approx(59.0)  # waits until the first leaves


def test_production_settings_keep_every_60s_window_under_the_token_budget():
    """Real defaults (45 texts, 90 req, 25K tokens) on worst-case chunks: calls are split and spaced."""
    clock = FakeClock()
    models = FakeModels()
    settings = get_embedding_settings()
    embedder = make_embedder(
        models,
        clock,
        batch_size=settings.batch_size,
        requests_per_minute=settings.requests_per_minute,
        tokens_per_minute=settings.tokens_per_minute,
    )
    sent: list[tuple[float, int]] = []
    original = models.embed_content

    def recording(**kwargs):
        sent.append((clock.now, sum(estimate_tokens(t) for t in kwargs["contents"])))
        return original(**kwargs)

    models.embed_content = recording
    embedder.embed(["x" * 1738] * 90, EmbeddingTask.DOCUMENT)
    assert max(tokens for _, tokens in sent) <= settings.tokens_per_minute // 2
    for start, _ in sent:
        in_window = sum(tokens for t, tokens in sent if start <= t < start + 60)
        assert in_window <= settings.tokens_per_minute


def test_batches_never_exceed_the_per_minute_request_limit():
    models = FakeModels()
    make_embedder(models, batch_size=50, requests_per_minute=3).embed(list("abcdefg"), EmbeddingTask.DOCUMENT)
    assert [len(c["contents"]) for c in models.calls] == [3, 3, 1]


def test_estimate_tokens_is_chars_over_four_rounded_up():
    assert (estimate_tokens(""), estimate_tokens("abcd"), estimate_tokens("abcde")) == (1, 1, 2)
