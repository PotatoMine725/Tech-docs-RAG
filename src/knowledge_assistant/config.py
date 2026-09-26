import os
from dataclasses import dataclass
from pathlib import Path

# src/knowledge_assistant/config.py -> repo root. Relative paths resolve from here, never from the cwd,
# so a script started in another directory reads and writes the same files (ADR-0005 D16).
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(value: str | Path) -> Path:
    """A relative path (default or env value) is taken from the repo root; an absolute one is kept."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_chroma_path() -> Path:
    """OD-7 (ADR-0005): repo-local, git-ignored, rebuilt by script."""
    return resolve_project_path(os.getenv("CHROMA_PATH", "data/chroma"))


def get_chunks_dir() -> Path:
    """Chunk files written by scripts/ingestion/build_chunks.py (arm-a.jsonl, arm-b.jsonl)."""
    return resolve_project_path(os.getenv("CHUNKS_DIR", "data/processed/chunks"))


def get_logs_dir() -> Path:
    """Run logs (indexing, evaluation); git-ignored."""
    return resolve_project_path(os.getenv("LOGS_DIR", "data/logs"))


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
    cache_path: Path

    @property
    def model_id(self) -> str:
        """Cache / collection key: model name plus output size."""
        return f"{self.model}@{self.dim}"


def get_embedding_settings() -> EmbeddingSettings:
    """Defaults per ADR-0005; each value can be overridden by an environment variable."""
    return EmbeddingSettings(
        model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
        dim=int(os.getenv("EMBEDDING_DIM", "768")),
        batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "45")),
        requests_per_minute=int(os.getenv("EMBEDDING_RPM", "90")),
        tokens_per_minute=int(os.getenv("EMBEDDING_TPM", "25000")),
        max_attempts=int(os.getenv("EMBEDDING_MAX_ATTEMPTS", "5")),
        timeout_s=float(os.getenv("EMBEDDING_TIMEOUT_S", "60")),
        cache_path=resolve_project_path(os.getenv("EMBEDDING_CACHE_PATH", "data/cache/embeddings.sqlite")),
    )
