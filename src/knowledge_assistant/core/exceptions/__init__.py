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
