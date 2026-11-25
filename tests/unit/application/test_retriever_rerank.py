"""Retriever + reranker (ADR-0009): candidates, top_k cut, scores, gate input unchanged, `none` never called.
Synthetic data only."""
import pytest

from knowledge_assistant.application.retrieval.retrieve import Retriever, rerank_passage
from knowledge_assistant.core.interfaces.reranker import RerankResult
from knowledge_assistant.infrastructure.rerank.noop_reranker import NoOpReranker
from tests.fakes import FakeEmbedder, InMemoryVectorStore, make_chunk


class ReverseReranker:
    """Scores the last candidate highest; records what it was given."""

    model_id = "reverse"
    absolute_scores = True

    def __init__(self):
        self.calls = []

    def rerank(self, query, passages, top_n=None):
        self.calls.append((query, list(passages), top_n))
        n = len(passages)
        ranked = [RerankResult(index=i, score=(i + 1) / (n + 1)) for i in reversed(range(n))]
        return ranked if top_n is None else ranked[:top_n]


class RecordingNoOp(NoOpReranker):
    def rerank(self, query, passages, top_n=None):
        raise AssertionError("a reranker without absolute scores must not be called")


def _setup(n=30):
    chunks = [make_chunk("01", i, f"text {i}", ("Doc", f"Section {i}")) for i in range(n)]
    store = InMemoryVectorStore({c.chunk_id: 0.9 - i / 100 for i, c in enumerate(chunks)})
    store.upsert(chunks, [[1.0, 0.0]] * n)
    return chunks, store


def test_reranker_sees_the_candidates_and_returns_top_k_by_its_score():
    chunks, store = _setup()
    reranker = ReverseReranker()
    result = Retriever(FakeEmbedder(), store, top_k=5, overfetch=10, reranker=reranker,
                       rerank_candidates=20).retrieve("q")
    assert store.searches == [30]  # candidates + overfetch
    (query, passages, top_n), = reranker.calls
    assert (query, len(passages), top_n) == ("q", 20, 5)
    assert passages[0] == "Doc > Section 0\n\ntext 0"
    assert [h.chunk.chunk_id for h in result.chunks] == [chunks[i].chunk_id for i in (19, 18, 17, 16, 15)]
    assert [h.rank for h in result.chunks] == [1, 2, 3, 4, 5]
    assert result.chunks[0].score == pytest.approx(20 / 21)
    assert result.rerank_score == pytest.approx(20 / 21)
    assert result.gate_score == pytest.approx(0.9)  # still the dense top-1 cosine (gate unchanged, ADR-0009)
    assert "rerank" in result.latency_ms


def test_none_reranker_is_not_called_and_changes_nothing():
    _, store = _setup()
    plain = Retriever(FakeEmbedder(), store, top_k=5).retrieve("q")
    with_none = Retriever(FakeEmbedder(), store, top_k=5, reranker=RecordingNoOp()).retrieve("q")
    assert with_none.chunks == plain.chunks
    assert with_none.rerank_score is None and "rerank" not in with_none.latency_ms
    assert store.searches == [15, 15]


def test_candidates_never_fewer_than_top_k():
    _, store = _setup()
    reranker = ReverseReranker()
    Retriever(FakeEmbedder(), store, top_k=8, reranker=reranker, rerank_candidates=3).retrieve("q")
    assert len(reranker.calls[0][1]) == 8


def test_rerank_candidates_must_be_positive():
    _, store = _setup()
    with pytest.raises(ValueError, match="rerank_candidates"):
        Retriever(FakeEmbedder(), store, reranker=ReverseReranker(), rerank_candidates=0)


def test_rerank_passage_without_heading_is_the_body():
    chunk = make_chunk("01", 0, "body only", ())
    assert rerank_passage(chunk) == "body only"
