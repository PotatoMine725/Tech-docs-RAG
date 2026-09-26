"""ChromaDB adapter for core.interfaces.vector_store (ADR-0003 D6/D7, ADR-0005 D16/D17).

One persistent collection per arm. Its name carries the chunker config and the embedding model id,
so changing either can never silently reuse an old collection; its metadata records both exactly
and is checked on every open.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.errors import NotFoundError

from knowledge_assistant.core.exceptions import VectorStoreError
from knowledge_assistant.core.models import DocumentChunk, RetrievedChunk

DISTANCE = "cosine"  # ADR-0005 D17; score = 1 - cosine distance
SETTINGS = Settings(anonymized_telemetry=False)  # one Settings for every client on a path (Chroma rejects a mismatch)
UPSERT_BATCH = 500  # well under the client's max batch size
NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def collection_name(chunker_config: str, embedding_model_id: str) -> str:
    """`kb_{chunker_config}_{model_id}`; characters Chroma forbids (e.g. '@') become '-'."""
    name = NAME_CHARS.sub("-", f"kb_{chunker_config}_{embedding_model_id}")
    return name.strip("-._") or "kb"


def chunk_to_metadata(chunk: DocumentChunk) -> dict[str, str | int]:
    """Every D6 field except `embed_text` (stored as the document). Chroma metadata takes no None and no lists:
    `heading_path` becomes a JSON array string, and a None `source_url` is left out."""
    metadata: dict[str, str | int] = {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "document_name": chunk.document_name,
        "heading_path": json.dumps(list(chunk.heading_path), ensure_ascii=False),
        "location_type": chunk.location_type,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "display_text": chunk.display_text,
        "content_hash": chunk.content_hash,
        "chunker_config": chunk.chunker_config,
    }
    if chunk.source_url is not None:
        metadata["source_url"] = chunk.source_url
    return metadata


def chunk_from_metadata(metadata: dict, embed_text: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=str(metadata["chunk_id"]),
        source_id=str(metadata["source_id"]),
        document_name=str(metadata["document_name"]),
        source_url=metadata.get("source_url"),
        heading_path=tuple(json.loads(metadata["heading_path"])),
        location_type=str(metadata["location_type"]),
        char_start=int(metadata["char_start"]),
        char_end=int(metadata["char_end"]),
        display_text=str(metadata["display_text"]),
        embed_text=embed_text,
        content_hash=str(metadata["content_hash"]),
        chunker_config=str(metadata["chunker_config"]),
    )


class ChromaVectorStore:
    """`create=False` opens read-only: a missing collection then behaves as empty (for dry runs)."""

    def __init__(
        self, path: str | Path, chunker_config: str, embedding_model_id: str, create: bool = True
    ) -> None:
        self.chunker_config = chunker_config
        self.embedding_model_id = embedding_model_id
        self.name = collection_name(chunker_config, embedding_model_id)
        self._client = chromadb.PersistentClient(path=str(path), settings=SETTINGS)
        try:
            self._collection = self._client.get_collection(self.name, embedding_function=None)
        except NotFoundError:
            self._collection = None
            if create:
                self._collection = self._client.create_collection(
                    self.name,
                    metadata={
                        "hnsw:space": DISTANCE,
                        "chunker_config": chunker_config,
                        "embedding_model_id": embedding_model_id,
                        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    },
                    embedding_function=None,
                )
        if self._collection is not None:
            self._check_metadata(self._collection.metadata or {})

    def _check_metadata(self, metadata: dict) -> None:
        expected = {
            "hnsw:space": DISTANCE,
            "chunker_config": self.chunker_config,
            "embedding_model_id": self.embedding_model_id,
        }
        wrong = {key: metadata.get(key) for key, value in expected.items() if metadata.get(key) != value}
        if wrong:
            raise VectorStoreError(f"collection {self.name} was built with different settings: {wrong}")

    @property
    def exists(self) -> bool:
        return self._collection is not None

    @property
    def metadata(self) -> dict:
        return dict(self._collection.metadata or {}) if self._collection is not None else {}

    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        if self._collection is None:
            raise VectorStoreError(f"collection {self.name} was opened read-only and does not exist")
        if len(chunks) != len(embeddings):
            raise ValueError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")
        for chunk in chunks:
            if chunk.chunker_config != self.chunker_config:
                raise VectorStoreError(
                    f"chunk {chunk.chunk_id} is {chunk.chunker_config}, store is {self.chunker_config}"
                )
        for start in range(0, len(chunks), UPSERT_BATCH):
            part = chunks[start : start + UPSERT_BATCH]
            self._collection.upsert(
                ids=[chunk.chunk_id for chunk in part],
                embeddings=embeddings[start : start + UPSERT_BATCH],
                documents=[chunk.embed_text for chunk in part],
                metadatas=[chunk_to_metadata(chunk) for chunk in part],
            )

    def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        size = self.count()
        if size == 0 or top_k <= 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, size),
            include=["documents", "metadatas", "distances"],
        )
        hits = zip(result["documents"][0], result["metadatas"][0], result["distances"][0])
        ordered = sorted(hits, key=lambda hit: hit[2])
        return [
            RetrievedChunk(chunk=chunk_from_metadata(metadata, document), rank=rank, score=1.0 - float(distance))
            for rank, (document, metadata, distance) in enumerate(ordered, start=1)
        ]

    def count(self) -> int:
        return self._collection.count() if self._collection is not None else 0

    def get_ids(self) -> set[str]:
        if self._collection is None:
            return set()
        return set(self._collection.get(include=[])["ids"])
