"""The composition root wires the use case from settings; --gate-off turns only the retrieval gate off (RAG-003)."""
import json

import pytest

from knowledge_assistant.composition import build_answer_service, open_vector_store
from knowledge_assistant.config import get_retrieval_settings
from knowledge_assistant.core.exceptions import VectorStoreError
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, make_chunk

REPLY = json.dumps({"insufficient": False, "answer": "It says so [1].", "cited_passages": [1], "missing_information": ""})


def _store(top_score):
    chunks = [make_chunk(f"{i:02d}", i, f"Passage body {i}.", ("Doc", f"Part {i}")) for i in range(1, 7)]
    store = InMemoryVectorStore({c.chunk_id: top_score - n / 100 for n, c in enumerate(chunks)})
    store.upsert(chunks, [[1.0, 0.0]] * len(chunks))
    return store


def test_the_gate_threshold_comes_from_the_retrieval_settings():
    service = build_answer_service("A", FakeLLM(REPLY), FakeEmbedder(), store=_store(0.9))
    assert service.threshold == get_retrieval_settings().insufficient_score_threshold


def test_a_top_score_below_the_threshold_is_refused_without_an_llm_call():
    llm = FakeLLM(REPLY)
    result = build_answer_service("A", llm, FakeEmbedder(), store=_store(0.3)).ask("Question?")
    assert result.insufficient and result.insufficient_reason == "retrieval_gate"
    assert llm.requests == []


def test_gate_off_sends_the_same_low_score_question_to_the_llm():
    llm = FakeLLM(REPLY)
    service = build_answer_service("A", llm, FakeEmbedder(), store=_store(0.3), gate_off=True)
    result = service.ask("Question?")
    assert len(llm.requests) == 1
    assert not result.insufficient and result.retrieved[0].score < get_retrieval_settings().insufficient_score_threshold


class SpyReranker:
    """Absolute scores (so the retriever uses it); records its calls."""

    model_id = "spy"
    absolute_scores = True

    def __init__(self):
        self.calls = []

    def rerank(self, query, passages, top_n=None):
        from knowledge_assistant.core.interfaces.reranker import RerankResult

        self.calls.append(len(passages))
        return [RerankResult(index=i, score=1 - i / 100) for i in range(len(passages))][:top_n]


def test_a_reranker_passed_in_is_the_one_the_service_uses_and_none_is_built(monkeypatch):
    """The GUI builds one reranker for both arms; composition must hand it on, not build a second per service."""
    import knowledge_assistant.composition as composition

    monkeypatch.delenv("RERANK_PROVIDER", raising=False)
    monkeypatch.setattr(composition, "create_reranker", lambda: pytest.fail("a second reranker was built"))
    shared = SpyReranker()
    service = build_answer_service("A", FakeLLM(REPLY), FakeEmbedder(), store=_store(0.9), reranker=shared)
    assert service.ask("Question?").insufficient is False
    assert shared.calls == [6]  # the reranker saw the six candidates of the store


def test_without_a_reranker_the_service_builds_the_configured_one_as_before(monkeypatch):
    import knowledge_assistant.composition as composition

    monkeypatch.delenv("RERANK_PROVIDER", raising=False)
    built = []
    real = composition.create_reranker
    monkeypatch.setattr(composition, "create_reranker", lambda: built.append(real()) or built[-1])
    llm = FakeLLM(REPLY)
    result = build_answer_service("A", llm, FakeEmbedder(), store=_store(0.9)).ask("Question?")
    assert len(built) == 1 and not built[0].absolute_scores  # RERANK_PROVIDER=none: a NoOpReranker, never called
    assert not result.insufficient and len(llm.requests) == 1


def test_a_missing_collection_is_a_vector_store_error_naming_the_build_command(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("CHUNKS_DIR", str(tmp_path / "chunks"))  # no chunk file there either
    with pytest.raises(VectorStoreError, match="build_chunks|build_index"):
        open_vector_store("A")


def _chunk_dir(tmp_path, monkeypatch):
    from knowledge_assistant.application.ingestion.build_chunks import chunk_to_record

    chunks = [make_chunk(f"{i:02d}", i, f"Passage body {i} kestrel.", ("Doc", f"Part {i}")) for i in range(1, 7)]
    (tmp_path / "chunks").mkdir()
    (tmp_path / "chunks" / "arm-a.jsonl").write_text(
        "".join(json.dumps(chunk_to_record(c)) + "\n" for c in chunks), encoding="utf-8")
    monkeypatch.setenv("CHUNKS_DIR", str(tmp_path / "chunks"))
    monkeypatch.setenv("KEYWORD_INDEX_DIR", str(tmp_path / "keyword"))
    return chunks


def test_dense_mode_needs_no_keyword_index(tmp_path, monkeypatch):
    from knowledge_assistant.composition import create_retriever

    _chunk_dir(tmp_path, monkeypatch)
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    retriever = create_retriever("A", FakeEmbedder(), _store(0.9))
    assert retriever.mode == "dense"
    assert not (tmp_path / "keyword").exists()


def test_hybrid_mode_opens_the_arms_keyword_index_or_names_the_build_command(tmp_path, monkeypatch):
    from knowledge_assistant.application.ingestion.index_corpus import index_keywords
    from knowledge_assistant.composition import create_retriever
    from knowledge_assistant.core.exceptions import KeywordIndexError
    from knowledge_assistant.infrastructure.keyword_index.fts5_index import Fts5KeywordIndex

    chunks = _chunk_dir(tmp_path, monkeypatch)
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")
    with pytest.raises(KeywordIndexError, match="build_index"):
        create_retriever("A", FakeEmbedder(), _store(0.9))
    index_keywords(chunks, Fts5KeywordIndex(tmp_path / "keyword", "header-1600"))
    retriever = create_retriever("A", FakeEmbedder(), _store(0.9))
    assert (retriever.mode, retriever.rrf_k) == ("hybrid", 60)
    assert len(retriever.retrieve("kestrel?").chunks) == 5
