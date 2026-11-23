"""Composition root: wires the layers for scripts (ask, smoke checks) and, later, the GUI and the eval runner.

The one module besides the scripts that names both application and infrastructure classes. Everything here is
plumbing: settings in, a ready `AnswerQuestion` out; no business rule lives here.
"""
from dataclasses import replace
from pathlib import Path

from knowledge_assistant.application.generation.answer_question import AnswerQuestion, load_messages
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder
from knowledge_assistant.application.ingestion.build_chunks import load_chunks
from knowledge_assistant.application.ingestion.index_corpus import chunker_config_of
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.config import (
    AnswerSettings,
    get_active_embedding_model_id,
    get_answer_settings,
    get_chroma_path,
    get_chunks_dir,
    get_embedding_provider,
    get_embedding_settings,
    get_llm_provider,
    get_local_embedding_settings,
    get_rerank_provider,
    get_retrieval_settings,
)
from knowledge_assistant.core.exceptions import ConfigurationError, VectorStoreError
from knowledge_assistant.core.interfaces.embedding import Embedder
from knowledge_assistant.core.interfaces.llm import LLM
from knowledge_assistant.core.interfaces.reranker import Reranker
from knowledge_assistant.core.interfaces.vector_store import VectorStore
from knowledge_assistant.infrastructure.embeddings.embeddinggemma_embedder import EmbeddingGemmaEmbedder
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder, PlannedEmbedder
from knowledge_assistant.infrastructure.rerank.noop_reranker import NoOpReranker
from knowledge_assistant.infrastructure.vector_store.chromadb.chroma_store import ChromaVectorStore

ARMS = ("A", "B")


def create_embedder(max_attempts: int | None = None) -> PlannedEmbedder:
    """The configured embedding provider (EMBEDDING_PROVIDER), without the cache. Building it is cheap: the local
    model loads on its first `embed`. `max_attempts` only applies to Gemini (the local model never retries)."""
    if get_embedding_provider() == "embeddinggemma":
        return EmbeddingGemmaEmbedder(get_local_embedding_settings())
    settings = get_embedding_settings()
    if max_attempts is not None:
        settings = replace(settings, max_attempts=max_attempts)
    return GeminiEmbedder(settings)


def embedding_cache_path() -> Path:
    """One SQLite cache for every provider: its keys include the model id, so vectors never mix."""
    if get_embedding_provider() == "embeddinggemma":
        return get_local_embedding_settings().cache_path
    return get_embedding_settings().cache_path


def open_embedder(max_attempts: int | None = None, inner: PlannedEmbedder | None = None) -> CachingEmbedder:
    """The query embedder: the configured provider behind the on-disk cache (a cached text costs nothing). Use it in
    a `with`. Pass `inner` to reuse one provider instance (the local model then loads once per process).

    `max_attempts` overrides the Gemini retry count, e.g. 1 for a live check that must not loop on a 429.
    """
    return CachingEmbedder(inner or create_embedder(max_attempts), embedding_cache_path())


def create_llm(settings: AnswerSettings | None = None, **provider_options) -> LLM:
    """The configured answer LLM (LLM_PROVIDER). `provider_options` go to the provider (Gemini: throttles,
    on_provider_error). The local llama.cpp provider is reserved, not built yet."""
    if get_llm_provider() == "llamacpp":
        raise ConfigurationError("LLM_PROVIDER=llamacpp is not implemented yet; use gemini")
    return GeminiLLM(settings, **provider_options)


def create_reranker() -> Reranker:
    """The configured reranker (RERANK_PROVIDER); only `none` exists until hybrid search."""
    get_rerank_provider()  # validates the value
    return NoOpReranker()


def open_vector_store(arm: str) -> ChromaVectorStore:
    """The existing collection of one experiment arm; never creates one."""
    chunk_file = get_chunks_dir() / f"arm-{arm.lower()}.jsonl"
    try:
        config = chunker_config_of(load_chunks(chunk_file))
    except FileNotFoundError as error:
        raise VectorStoreError(
            f"chunk file {chunk_file.name} not found; run scripts/ingestion/build_chunks.py, then "
            f"scripts/ingestion/build_index.py --arm {arm}"
        ) from error
    store = ChromaVectorStore(get_chroma_path(), config, get_active_embedding_model_id(), create=False)
    if not store.exists:
        raise VectorStoreError(f"collection {store.name} does not exist; run scripts/ingestion/build_index.py --arm {arm}")
    return store


def build_answer_service(
    arm: str,
    llm: LLM,
    embedder: Embedder,
    *,
    store: VectorStore | None = None,
    gate_off: bool = False,
) -> AnswerQuestion:
    """One `AnswerQuestion` for one arm. `gate_off=True` disables the retrieval gate so a low-scoring question still
    reaches the LLM: a diagnostic for checking the LLM's own "insufficient" path, never used for evaluation."""
    answer = get_answer_settings()
    retrieval = get_retrieval_settings()
    threshold = float("-inf") if gate_off else retrieval.insufficient_score_threshold
    return AnswerQuestion(
        Retriever(embedder, store or open_vector_store(arm), retrieval.top_k, retrieval.overfetch),
        llm,
        PromptBuilder.from_dir(answer.prompts_dir, answer.prompt_version),
        load_messages(answer.messages_path),
        threshold,
    )
