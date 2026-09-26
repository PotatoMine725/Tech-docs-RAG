"""Composition root: wires the layers for scripts (ask, smoke checks) and, later, the GUI and the eval runner.

The one module besides the scripts that names both application and infrastructure classes. Everything here is
plumbing: settings in, a ready `AnswerQuestion` out; no business rule lives here.
"""
from dataclasses import replace

from knowledge_assistant.application.generation.answer_question import AnswerQuestion, load_messages
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder
from knowledge_assistant.application.ingestion.build_chunks import load_chunks
from knowledge_assistant.application.ingestion.index_corpus import chunker_config_of
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.config import (
    get_answer_settings,
    get_chroma_path,
    get_chunks_dir,
    get_embedding_settings,
    get_retrieval_settings,
)
from knowledge_assistant.core.exceptions import VectorStoreError
from knowledge_assistant.core.interfaces.embedding import Embedder
from knowledge_assistant.core.interfaces.llm import LLM
from knowledge_assistant.core.interfaces.vector_store import VectorStore
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder
from knowledge_assistant.infrastructure.vector_store.chromadb.chroma_store import ChromaVectorStore

ARMS = ("A", "B")


def open_embedder(max_attempts: int | None = None) -> CachingEmbedder:
    """The query embedder: Gemini behind the on-disk cache (a cached text costs no request). Use it in a `with`.

    `max_attempts` overrides the embedding retry count, e.g. 1 for a live check that must not loop on a 429.
    """
    settings = get_embedding_settings()
    if max_attempts is not None:
        settings = replace(settings, max_attempts=max_attempts)
    return CachingEmbedder(GeminiEmbedder(settings), settings.cache_path)


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
    store = ChromaVectorStore(get_chroma_path(), config, get_embedding_settings().model_id, create=False)
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
