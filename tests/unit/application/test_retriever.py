"""Retriever: query embedding, over-fetch + passage-hash dedup (RAG-002 addendum 1, owner 2026-09-26), and the fields the
EVAL-003b-pre metric code needs (addendum 2). Synthetic data only; no eval-set question or span is used."""
from dataclasses import replace

import pytest

from knowledge_assistant.application.evaluation.metrics.retrieval import (
    RankedChunk,
    evidence_hit_at_k,
    reciprocal_rank,
    section_hit_at_k,
    source_hit_at_k,
)
from knowledge_assistant.application.evaluation.metrics.spans import EXPECTED, ExpectedSpan
from knowledge_assistant.application.retrieval.retrieve import Retriever, dedupe_by_passage
from knowledge_assistant.core.exceptions import RetrievalError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.core.models import RetrievedChunk
from tests.fakes import FakeEmbedder, InMemoryVectorStore, make_chunk


def _store(chunks, scores):
    store = InMemoryVectorStore(scores)
    store.upsert(chunks, [[1.0, 0.0]] * len(chunks))
    return store


def test_query_is_embedded_as_query_and_store_is_overfetched():
    embedder = FakeEmbedder()
    chunks = [make_chunk("01", i, f"text {i}") for i in range(20)]
    store = _store(chunks, {c.chunk_id: 1.0 - i / 100 for i, c in enumerate(chunks)})
    result = Retriever(embedder, store, top_k=5, overfetch=10).retrieve("question?")
    assert embedder.calls == [(["question?"], EmbeddingTask.QUERY)]
    assert store.searches == [15]
    assert [hit.rank for hit in result.chunks] == [1, 2, 3, 4, 5]
    assert set(result.latency_ms) == {"embed_query", "retrieve"}


def test_no_duplicates_gives_unchanged_result():
    chunks = [make_chunk("01", i, f"text {i}") for i in range(8)]
    store = _store(chunks, {c.chunk_id: 0.9 - i / 100 for i, c in enumerate(chunks)})
    plain = store.search([1.0, 0.0], 5)
    result = Retriever(FakeEmbedder(), store, top_k=5).retrieve("q")
    assert list(result.chunks) == plain
    assert result.duplicates_dropped == 0


def test_duplicates_across_documents_collapse_to_one_slot_with_duplicate_ids():
    same = "Repeated paragraph copied into three documents."
    chunks = [
        make_chunk("17", 0, same, ("A", "One")), make_chunk("23", 4, same, ("B", "Two")),
        make_chunk("13", 2, same, ("C", "Three")),
        make_chunk("01", 0, "a"), make_chunk("02", 0, "b"), make_chunk("03", 0, "c"), make_chunk("04", 0, "d"),
    ]
    scores = {"17:header-1600:0000": 0.90, "23:header-1600:0004": 0.89, "13:header-1600:0002": 0.88,
              "01:header-1600:0000": 0.80, "02:header-1600:0000": 0.79, "03:header-1600:0000": 0.78,
              "04:header-1600:0000": 0.77}
    result = Retriever(FakeEmbedder(), _store(chunks, scores), top_k=5).retrieve("q")
    ids = [hit.chunk.chunk_id for hit in result.chunks]
    assert ids == ["17:header-1600:0000", "01:header-1600:0000", "02:header-1600:0000",
                   "03:header-1600:0000", "04:header-1600:0000"]
    assert result.chunks[0].duplicate_chunk_ids == ("23:header-1600:0004", "13:header-1600:0002")
    assert all(hit.duplicate_chunk_ids == () for hit in result.chunks[1:])
    assert [hit.rank for hit in result.chunks] == [1, 2, 3, 4, 5]  # re-numbered after the drop
    assert result.duplicates_dropped == 2


def test_link_only_difference_is_a_duplicate_although_content_hash_differs():
    """Doc 17's case: display_text differs only in a link URL, so content_hash differs, but the passage is the same."""
    first = make_chunk("17", 6, "See the guide for version 10.")
    second = replace(make_chunk("17", 92, "See the guide for version 10."),
                     display_text="See the [guide](https://x.invalid/v7) for version 10.", content_hash="other")
    assert first.content_hash != second.content_hash
    result = Retriever(FakeEmbedder(), _store([first, second, make_chunk("01", 0, "z")],
                                              {first.chunk_id: 0.8, second.chunk_id: 0.8}), top_k=5).retrieve("q")
    assert [hit.chunk.chunk_id for hit in result.chunks][0] == "17:header-1600:0006"
    assert result.chunks[0].duplicate_chunk_ids == ("17:header-1600:0092",)
    assert result.duplicates_dropped == 1


def test_duplicate_keeps_highest_score_even_if_store_order_differs():
    low, high = make_chunk("05", 0, "dup"), make_chunk("09", 0, "dup")
    hits = [RetrievedChunk(low, 1, 0.70), RetrievedChunk(high, 2, 0.75)]  # store order is not trusted
    kept, dropped = dedupe_by_passage(hits, 5)
    assert [hit.chunk.chunk_id for hit in kept] == [high.chunk_id]
    assert kept[0].rank == 1 and kept[0].score == 0.75 and dropped == 1


def test_equal_scores_break_ties_by_chunk_id_and_are_stable():
    a, b = make_chunk("23", 0, "dup"), make_chunk("17", 0, "dup")
    other = make_chunk("02", 0, "x")
    for order in ([a, b, other], [b, a, other], [other, a, b]):
        store = _store(order, {a.chunk_id: 0.8, b.chunk_id: 0.8, other.chunk_id: 0.8})
        result = Retriever(FakeEmbedder(), store, top_k=5).retrieve("q")
        assert [hit.chunk.chunk_id for hit in result.chunks] == ["02:header-1600:0000", "17:header-1600:0000"]
        assert result.chunks[1].duplicate_chunk_ids == ("23:header-1600:0000",)
        assert result.duplicates_dropped == 1


def test_empty_store_raises_retrieval_error():
    with pytest.raises(RetrievalError):
        Retriever(FakeEmbedder(), InMemoryVectorStore(), top_k=5).retrieve("q")


def test_retriever_result_feeds_the_evaluation_metrics():
    """Addendum 2: a RetrievedChunk carries chunk_id, source id, heading path, offsets and content_hash, and maps onto
    the metric code's RankedChunk without loss of what the metrics read."""
    chunks = [
        make_chunk("07", 3, "Unrelated text about gadgets.", char_start=0),
        make_chunk("07", 4, "A widget registry is created at startup. It is frozen.", ("Widgets", "Registry"),
                   char_start=500),
        make_chunk("12", 0, "Other document.", char_start=0),
    ]
    scores = {chunks[0].chunk_id: 0.9, chunks[1].chunk_id: 0.8, chunks[2].chunk_id: 0.7}
    result = Retriever(FakeEmbedder(), _store(chunks, scores), top_k=3).retrieve("q")
    hit = result.chunks[1]
    assert (hit.chunk.chunk_id, hit.chunk.source_id, hit.chunk.heading_path, hit.chunk.char_start,
            hit.chunk.char_end, hit.chunk.content_hash) == (
        "07:header-1600:0004", "07", ("Widgets", "Registry"), 500, 554, chunks[1].content_hash)

    ranked = [RankedChunk(h.chunk.source_id, h.chunk.char_start, h.chunk.char_end, h.chunk.display_text)
              for h in result.chunks]
    spans = [ExpectedSpan("S1", EXPECTED, "07", "Widgets > Registry", 1, 500, 560)]
    assert source_hit_at_k(ranked, spans, 1) == 1
    assert section_hit_at_k(ranked, spans, 1) == 0
    assert section_hit_at_k(ranked, spans, 2) == 1
    assert reciprocal_rank(ranked, spans) == 0.5
    assert evidence_hit_at_k(ranked, {"P1": ["created at startup"]}, 2) == 1
    assert evidence_hit_at_k(ranked, {"P1": ["created at startup"]}, 1) == 0
