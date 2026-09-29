"""The passage text of a chunk: what the LLM sees and what retrieval deduplicates on (RAG-002)."""
import hashlib

from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, DocumentChunk


def passage_body(chunk: DocumentChunk) -> str:
    """The chunk text with Markdown links reduced to their text: `embed_text` without its contextual heading line
    (ADR-0003 D5 puts "heading path + blank line" first; the passage header already shows the heading path)."""
    header = HEADING_PATH_SEPARATOR.join(chunk.heading_path) + "\n\n"
    if chunk.heading_path and chunk.embed_text.startswith(header):
        return chunk.embed_text[len(header):]
    return chunk.embed_text


def passage_hash(chunk: DocumentChunk) -> str:
    """Dedup key (owner decision 2026-09-26): SHA-256 of `passage_body`. Unlike `content_hash` (hash of the raw
    `display_text`), two chunks whose text differs only in a link URL get the same key."""
    return hashlib.sha256(passage_body(chunk).encode("utf-8")).hexdigest()
