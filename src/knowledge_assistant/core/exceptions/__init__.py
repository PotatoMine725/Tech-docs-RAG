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
