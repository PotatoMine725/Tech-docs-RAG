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
