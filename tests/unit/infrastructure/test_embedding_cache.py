import pytest

from knowledge_assistant.core.exceptions import EmbeddingError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder, cache_key
from tests.fakes import FakeEmbedder

DOC = EmbeddingTask.DOCUMENT
QUERY = EmbeddingTask.QUERY


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "cache" / "embeddings.sqlite"


def test_second_call_with_same_texts_makes_no_inner_call(db_path):
    inner = FakeEmbedder()
    with CachingEmbedder(inner, db_path, batch_size=10) as cache:
        first = cache.embed(["a", "b"], DOC)
        second = cache.embed(["a", "b"], DOC)
    assert len(inner.calls) == 1
    assert first == second
    assert cache.hits == 2 and cache.misses == 2


def test_mixed_batch_sends_only_misses_and_keeps_order(db_path):
    inner = FakeEmbedder()
    with CachingEmbedder(inner, db_path, batch_size=10) as cache:
        cache.embed(["b"], DOC)
        result = cache.embed(["a", "b", "c"], DOC)
    assert inner.calls[-1] == (["a", "c"], DOC)
    assert result == [pytest.approx(inner.vector(t), abs=1e-6) for t in ["a", "b", "c"]]


def test_duplicate_texts_in_one_call_are_sent_once(db_path):
    inner = FakeEmbedder()
    with CachingEmbedder(inner, db_path, batch_size=10) as cache:
        result = cache.embed(["x", "y", "x"], DOC)
    assert inner.calls == [(["x", "y"], DOC)]
    assert result[0] == result[2]


def test_misses_are_sent_in_batches_and_each_batch_is_stored(db_path):
    class FailsOnThirdCall(FakeEmbedder):
        def embed(self, texts, task):
            if len(self.calls) == 2:
                raise EmbeddingError("quota")
            return super().embed(texts, task)

    inner = FailsOnThirdCall()
    with CachingEmbedder(inner, db_path, batch_size=2) as cache:
        with pytest.raises(EmbeddingError):
            cache.embed(["1", "2", "3", "4", "5"], DOC)
    assert [len(texts) for texts, _ in inner.calls] == [2, 2]

    resumed = FakeEmbedder()
    with CachingEmbedder(resumed, db_path, batch_size=2) as cache:
        cache.embed(["1", "2", "3", "4", "5"], DOC)
    assert resumed.calls == [(["5"], DOC)]


def test_task_and_model_id_are_part_of_the_key(db_path):
    assert cache_key("m@8", DOC, "t") != cache_key("m@8", QUERY, "t")
    assert cache_key("m@8", DOC, "t") != cache_key("m@768", DOC, "t")

    inner = FakeEmbedder()
    with CachingEmbedder(inner, db_path, batch_size=10) as cache:
        cache.embed(["t"], DOC)
        cache.embed(["t"], QUERY)
    other = FakeEmbedder(model_id="other-model@8")
    with CachingEmbedder(other, db_path, batch_size=10) as cache:
        cache.embed(["t"], DOC)
    assert len(inner.calls) == 2
    assert len(other.calls) == 1


def test_cache_survives_reopening_the_file(db_path):
    with CachingEmbedder(FakeEmbedder(), db_path, batch_size=10) as cache:
        first = cache.embed(["persist me"], DOC)
    inner = FakeEmbedder()
    with CachingEmbedder(inner, db_path, batch_size=10) as cache:
        again = cache.embed(["persist me"], DOC)
    assert inner.calls == []
    assert again == first


def test_first_call_returns_the_same_float32_values_as_a_cache_hit(db_path):
    with CachingEmbedder(FakeEmbedder(), db_path, batch_size=10) as cache:
        miss = cache.embed(["same"], DOC)
        hit = cache.embed(["same"], DOC)
    assert miss == hit


def test_stats_expose_counters(db_path):
    with CachingEmbedder(FakeEmbedder(), db_path, batch_size=1) as cache:
        cache.embed(["abcd", "efgh"], DOC)
        cache.embed(["abcd"], DOC)
        stats = cache.stats()
    assert stats == {"hits": 1, "misses": 2, "inner_calls": 2, "estimated_tokens": 2}


def test_wrong_vector_count_from_inner_raises(db_path):
    class Short(FakeEmbedder):
        def embed(self, texts, task):
            return super().embed(texts, task)[:-1]

    with CachingEmbedder(Short(), db_path, batch_size=10) as cache:
        with pytest.raises(EmbeddingError):
            cache.embed(["a", "b"], DOC)
