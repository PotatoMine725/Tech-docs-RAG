"""Retrieval modes (ADR-0007): dense unchanged, sparse, hybrid RRF (k=60), and the dense gate score in every mode."""
import pytest

from knowledge_assistant.application.retrieval.retrieve import (
    RetrievalResult,
    Retriever,
    reciprocal_rank_fusion,
)
from knowledge_assistant.core.exceptions import RetrievalError
from knowledge_assistant.core.models import RetrievedChunk
from tests.fakes import FakeEmbedder, InMemoryVectorStore, make_chunk


class FakeKeywordIndex:
    """Returns a fixed ranked list; records the queries."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.queries = []

    def search(self, query, top_k):
        self.queries.append((query, top_k))
        return [RetrievedChunk(chunk=c, rank=i, score=10.0 - i) for i, c in enumerate(self.chunks[:top_k], start=1)]


CHUNKS = [make_chunk(f"{i:02d}", 0, f"body {i}") for i in range(1, 9)]


def _store(order_scores):
    store = InMemoryVectorStore(order_scores)
    store.upsert(CHUNKS, [[1.0, 0.0]] * len(CHUNKS))
    return store


DENSE_SCORES = {c.chunk_id: 0.9 - n / 100 for n, c in enumerate(CHUNKS)}  # dense order 01..08


def test_rrf_sums_reciprocal_ranks_and_breaks_ties_by_chunk_id():
    a, b, c = CHUNKS[:3]
    hit = lambda chunk, rank: RetrievedChunk(chunk=chunk, rank=rank, score=0.0)  # noqa: E731
    fused = reciprocal_rank_fusion([[hit(a, 1), hit(b, 2)], [hit(b, 1), hit(c, 2)]], k=60)
    assert [h.chunk.chunk_id for h in fused] == [b.chunk_id, a.chunk_id, c.chunk_id]
    assert fused[0].score == pytest.approx(1 / 62 + 1 / 61)
    assert fused[1].score == pytest.approx(1 / 61)
    assert fused[2].score == pytest.approx(1 / 62)
    tie = reciprocal_rank_fusion([[hit(c, 1)], [hit(a, 1)]], k=60)
    assert [h.chunk.chunk_id for h in tie] == [a.chunk_id, c.chunk_id]
    assert [h.rank for h in tie] == [1, 2]


def test_dense_mode_is_unchanged_and_never_touches_a_keyword_index():
    keywords = FakeKeywordIndex(CHUNKS)
    plain = Retriever(FakeEmbedder(), _store(DENSE_SCORES), top_k=5).retrieve("q")
    with_index = Retriever(FakeEmbedder(), _store(DENSE_SCORES), top_k=5, keyword_index=keywords).retrieve("q")
    assert (plain.chunks, plain.duplicates_dropped, plain.gate_score) == (
        with_index.chunks, with_index.duplicates_dropped, with_index.gate_score)
    assert keywords.queries == []
    assert plain.gate_score == plain.chunks[0].score == pytest.approx(0.9)


def test_sparse_mode_ranks_by_keyword_but_gates_on_dense_top1():
    keywords = FakeKeywordIndex(list(reversed(CHUNKS)))  # keyword order 08..01
    result = Retriever(FakeEmbedder(), _store(DENSE_SCORES), top_k=3, overfetch=2, keyword_index=keywords,
                       mode="sparse").retrieve("raw question?")
    assert [h.chunk.source_id for h in result.chunks] == ["08", "07", "06"]
    assert keywords.queries == [("raw question?", 5)]  # original question, top_k + overfetch
    assert result.gate_score == pytest.approx(0.9)  # dense top-1, not the BM25 score


def test_sparse_mode_without_any_keyword_match_is_a_retrieval_error():
    with pytest.raises(RetrievalError, match="keyword"):
        Retriever(FakeEmbedder(), _store(DENSE_SCORES), keyword_index=FakeKeywordIndex([]), mode="sparse").retrieve("q")


def test_hybrid_fuses_both_lists_and_gates_on_dense_top1():
    keywords = FakeKeywordIndex([CHUNKS[7], CHUNKS[1], CHUNKS[6]])  # 08, 02, 07
    result = Retriever(FakeEmbedder(), _store(DENSE_SCORES), top_k=3, overfetch=5, keyword_index=keywords,
                       mode="hybrid").retrieve("q")
    # dense ranks: 01..08 -> 1..8; keyword ranks: 08 -> 1, 02 -> 2, 07 -> 3
    # 02: 1/62 + 1/62; 08: 1/68 + 1/61; 07: 1/67 + 1/63; 01: 1/61
    assert [h.chunk.source_id for h in result.chunks] == ["02", "08", "07"]
    assert result.chunks[0].score == pytest.approx(2 / 62)
    assert result.gate_score == pytest.approx(0.9)
    assert [h.rank for h in result.chunks] == [1, 2, 3]


def test_hybrid_still_drops_same_passage_duplicates():
    same = "Repeated paragraph."
    twins = [make_chunk("17", 0, same, ("A", "One")), make_chunk("23", 4, same, ("B", "Two"))]
    others = [make_chunk("01", 0, "a"), make_chunk("02", 0, "b")]
    store = InMemoryVectorStore({twins[0].chunk_id: 0.9, twins[1].chunk_id: 0.89, others[0].chunk_id: 0.8,
                                 others[1].chunk_id: 0.7})
    store.upsert(twins + others, [[1.0, 0.0]] * 4)
    result = Retriever(FakeEmbedder(), store, top_k=3, keyword_index=FakeKeywordIndex([twins[1], others[1]]),
                       mode="hybrid").retrieve("q")
    ids = [h.chunk.chunk_id for h in result.chunks]
    assert len({h.chunk.embed_text for h in result.chunks}) == 3
    assert result.duplicates_dropped == 1
    assert twins[0].chunk_id in ids or twins[1].chunk_id in ids


@pytest.mark.parametrize("kwargs, message", [
    ({"mode": "bm25"}, "mode"), ({"mode": "hybrid"}, "keyword index"), ({"mode": "sparse"}, "keyword index"),
    ({"rrf_k": 0, "mode": "dense"}, "rrf_k"),
])
def test_invalid_mode_settings_are_refused(kwargs, message):
    with pytest.raises(ValueError, match=message):
        Retriever(FakeEmbedder(), _store(DENSE_SCORES), **kwargs)


def test_result_without_gate_score_falls_back_to_rank_one_score():
    hit = RetrievedChunk(chunk=CHUNKS[0], rank=1, score=0.42)
    assert RetrievalResult((hit,), 0, {}).gate_score == 0.42
    assert RetrievalResult((hit,), 0, {}, gate_score=0.7).gate_score == 0.7
