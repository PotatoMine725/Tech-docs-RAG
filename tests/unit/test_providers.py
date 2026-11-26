"""Config-driven provider selection: embedding, generation and reranking are chosen independently."""
import pytest

from knowledge_assistant.composition import create_embedder, create_llm, create_reranker, embedding_cache_path
from knowledge_assistant.config import get_active_embedding_model_id, get_local_embedding_settings
from knowledge_assistant.core.exceptions import ConfigurationError
from knowledge_assistant.infrastructure.embeddings.embeddinggemma_embedder import EmbeddingGemmaEmbedder
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM
from knowledge_assistant.infrastructure.rerank.noop_reranker import NoOpReranker


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("EMBEDDING_PROVIDER", "LLM_PROVIDER", "RERANK_PROVIDER", "LOCAL_EMBEDDING_VARIANT",
                 "LOCAL_EMBEDDING_DIM", "LOCAL_EMBEDDING_MODEL_DIR"):
        monkeypatch.delenv(name, raising=False)


def test_defaults_are_gemini_and_no_reranker():
    assert isinstance(create_embedder(), GeminiEmbedder)
    assert isinstance(create_llm(), GeminiLLM)
    assert isinstance(create_reranker(), NoOpReranker)
    assert get_active_embedding_model_id() == "gemini-embedding-001@768"


def test_gemini_max_attempts_override_still_applies():
    assert create_embedder(max_attempts=1)._settings.max_attempts == 1


def test_local_embedder_is_selected_independently_of_the_llm(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "EmbeddingGemma")
    monkeypatch.setenv("LOCAL_EMBEDDING_VARIANT", "int4")
    embedder = create_embedder()
    assert isinstance(embedder, EmbeddingGemmaEmbedder)
    assert isinstance(create_llm(), GeminiLLM)
    assert get_active_embedding_model_id() == embedder.model_id == "embeddinggemma-300m-int4-t2048@768"
    assert embedding_cache_path() == get_local_embedding_settings().cache_path


@pytest.mark.parametrize("name,value", [
    ("EMBEDDING_PROVIDER", "openai"),
    ("LOCAL_EMBEDDING_VARIANT", "q2"),
    ("LOCAL_EMBEDDING_DIM", "300"),
    ("RERANK_PROVIDER", "cohere"),
])
def test_unknown_values_fail_loudly(monkeypatch, name, value):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "embeddinggemma")
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError, match=name):
        get_active_embedding_model_id()
        create_reranker()


def test_llamacpp_is_reserved_but_not_built_yet(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "llamacpp")
    with pytest.raises(ConfigurationError, match="not implemented"):
        create_llm()


def test_noop_reranker_keeps_order_and_respects_top_n():
    reranker = create_reranker()
    results = reranker.rerank("q", ["a", "b", "c"], top_n=2)
    assert [r.index for r in results] == [0, 1]
    assert results[0].score > results[1].score
    assert [r.index for r in reranker.rerank("q", ["a", "b"])] == [0, 1]
    assert reranker.rerank("q", []) == []


def test_bad_rerank_settings_do_not_break_retrieval_when_reranking_is_off(monkeypatch):
    from knowledge_assistant.composition import create_retriever
    from tests.fakes import FakeEmbedder, InMemoryVectorStore

    monkeypatch.setenv("RERANK_CANDIDATES", "0")  # invalid, but ignored while RERANK_PROVIDER is none
    retriever = create_retriever("A", FakeEmbedder(), InMemoryVectorStore({}))
    assert retriever.rerank_candidates == 20
