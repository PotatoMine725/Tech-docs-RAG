class KnowledgeAssistantError(Exception):
    """Base class for domain exceptions."""


class ConfigurationError(KnowledgeAssistantError):
    """Required configuration (e.g. GEMINI_API_KEY) is missing."""


class ParserNotFoundError(KnowledgeAssistantError):
    """No parser registered for a document format."""


class DocumentParseError(KnowledgeAssistantError):
    """A document could not be read or normalized; it is never dropped silently."""


class EmbeddingError(KnowledgeAssistantError):
    """Embedding failed after all retries, or the provider returned an invalid result."""


class QuotaExhaustedError(EmbeddingError):
    """The provider's daily quota is used up: retrying is pointless until the daily reset."""


class VectorStoreError(KnowledgeAssistantError):
    """The vector store cannot serve the request, e.g. its collection was built with other settings."""


class RetrievalError(KnowledgeAssistantError):
    """Retrieval returned nothing usable, e.g. the collection is empty or the query embedding is missing."""


class GenerationError(KnowledgeAssistantError):
    """The LLM output is unusable (not the expected JSON, truncated, empty). Never turned into "insufficient"."""

    def __init__(self, message: str, raw_text: str | None = None) -> None:
        super().__init__(message)
        self.raw_text = raw_text
