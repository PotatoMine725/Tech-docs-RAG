class KnowledgeAssistantError(Exception):
    """Base class for domain exceptions."""


class ConfigurationError(KnowledgeAssistantError):
    """Required configuration (e.g. GEMINI_API_KEY) is missing."""


class ParserNotFoundError(KnowledgeAssistantError):
    """No parser registered for a document format."""
