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


@dataclass(frozen=True)
class AnswerSettings:
    """Answer generation (ADR-0004 D11, RAG-002). The model name is pinned here only, never a `-latest` alias."""

    model: str
    timeout_s: float
    prompt_version: str  # file name (without .md) in `prompts_dir`
    prompts_dir: Path
    messages_path: Path


def get_answer_settings() -> AnswerSettings:
    return AnswerSettings(
        model=os.getenv("ANSWER_MODEL", "gemini-3.5-flash-lite"),
        timeout_s=float(os.getenv("ANSWER_TIMEOUT_S", "60")),
        prompt_version=os.getenv("ANSWER_PROMPT_VERSION", "answer_v1"),
        prompts_dir=resolve_project_path(os.getenv("PROMPTS_DIR", "config/prompts")),
        messages_path=resolve_project_path(os.getenv("MESSAGES_PATH", "config/messages.json")),
    )


@dataclass(frozen=True)
class RetrievalSettings:
    """top_k = 5 for both arms (ADR-0003 D7). The threshold is the OD-9 retrieval gate, tuned on the dev set, Arm A,
    used for both arms (retrieval-spec.md; RAG-002, 2026-09-26)."""

    top_k: int
    overfetch: int  # extra hits fetched so same-content duplicates can be dropped (RAG-002 addendum 1)
    insufficient_score_threshold: float


def get_retrieval_settings() -> RetrievalSettings:
    return RetrievalSettings(
        top_k=int(os.getenv("TOP_K", "5")),
        overfetch=int(os.getenv("RETRIEVAL_OVERFETCH", "10")),
        insufficient_score_threshold=float(os.getenv("INSUFFICIENT_SCORE_THRESHOLD", "0.686")),
    )
