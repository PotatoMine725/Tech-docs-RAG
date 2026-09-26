import os
from dataclasses import dataclass


def get_chroma_path() -> str:
    """OD-7 (ADR-0005): repo-local, git-ignored, rebuilt by script."""
    return os.getenv("CHROMA_PATH", "data/chroma")


def get_gemini_api_key() -> str | None:
    """Read the key from the environment only; never log or print it."""
    return os.getenv("GEMINI_API_KEY") or None


@dataclass(frozen=True)
class EmbeddingSettings:
    """Embedding settings (ADR-0004 D10, ADR-0005). The model name is pinned here only."""

    model: str
    dim: int
    batch_size: int
    requests_per_minute: int
    tokens_per_minute: int
    max_attempts: int
    timeout_s: float
    cache_path: str

    @property
    def model_id(self) -> str:
        """Cache / collection key: model name plus output size."""
        return f"{self.model}@{self.dim}"


def get_embedding_settings() -> EmbeddingSettings:
    """Defaults per ADR-0005; each value can be overridden by an environment variable."""
    return EmbeddingSettings(
        model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
        dim=int(os.getenv("EMBEDDING_DIM", "768")),
        batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "40")),
        requests_per_minute=int(os.getenv("EMBEDDING_RPM", "90")),
        tokens_per_minute=int(os.getenv("EMBEDDING_TPM", "25000")),
        max_attempts=int(os.getenv("EMBEDDING_MAX_ATTEMPTS", "5")),
        timeout_s=float(os.getenv("EMBEDDING_TIMEOUT_S", "60")),
        cache_path=os.getenv("EMBEDDING_CACHE_PATH", "data/cache/embeddings.sqlite"),
    )
