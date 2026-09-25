from typing import Protocol

from knowledge_assistant.core.models import ParsedDocument


class DocumentNormalizer(Protocol):
    """Deterministic, in-memory text normalization between parsing and chunking (ADR-0003 D1)."""

    def normalize(self, document: ParsedDocument) -> ParsedDocument: ...
