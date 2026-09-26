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


class LLMError(KnowledgeAssistantError):
    """The LLM provider could not answer, after retries and the fallback (ADR-0004 amendment 2026-09-26, RAG-003).

    Provider and transport exceptions never leave the infrastructure layer: they are wrapped into one of the three
    subtypes below, whose `kind` is the GUI's `AskQuestionError.kind` (quota | unavailable | other), 1:1. This base
    class is `other`. `model` is the answer model, `retry_count` its retries, `provider_body` the answer model's error
    body with any key redacted (for logs). The message is safe to show and log: it never contains the API key.
    """

    kind = "other"

    def __init__(
        self,
        message: str,
        *,
        model: str | None = None,
        retry_count: int = 0,
        fallback_attempted: bool = False,
        provider_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.model = model
        self.retry_count = retry_count
        self.fallback_attempted = fallback_attempted
        self.provider_body = provider_body


class LLMQuotaError(LLMError):
    """HTTP 429: the per-minute rate limit persisted through every attempt, or the daily quota is used up."""

    kind = "quota"

    def __init__(self, message: str, *, daily: bool = False, **details) -> None:
        super().__init__(message, **details)
        self.daily = daily  # True: retrying is pointless until the daily reset


class LLMUnavailableError(LLMError):
    """503 / other server error / timeout / connection error that persisted through every attempt."""

    kind = "unavailable"


class LLMRequestError(LLMError):
    """Any other provider failure (bad request, invalid key, unknown model, unparsable reply): never retried."""

    kind = "other"
