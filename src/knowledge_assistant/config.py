import os
from dataclasses import dataclass
from pathlib import Path

from knowledge_assistant.core.exceptions import ConfigurationError

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
class ModelLimits:
    """Free-tier limits of one model (AI Studio, read by the owner 2026-09-26) and the client-side throttle.

    The throttle sits below RPM so a run never trips the provider limit. TPM and RPD are not enforced by the
    adapter (13 requests a minute of a ~3K-token prompt is far below 250K TPM); they are here so a runner can plan
    a run against the daily quota.
    """

    rpm: int
    tpm: int
    rpd: int
    throttle_rpm: int


@dataclass(frozen=True)
class AnswerSettings:
    """Answer generation (ADR-0004 D11-D13 + amendment 2026-09-26). Model names are pinned here only, never a
    `-latest` alias. `max_attempts` counts the first try (3 = 1 + 2 retries); the fallback model then gets one
    attempt, unless `allow_fallback` is false (the evaluation runner sets ALLOW_FALLBACK=false)."""

    model: str
    fallback_model: str
    allow_fallback: bool
    max_attempts: int
    timeout_s: float
    prompt_version: str  # file name (without .md) in `prompts_dir`
    prompts_dir: Path
    messages_path: Path
    limits: ModelLimits  # of `model`
    fallback_limits: ModelLimits  # of `fallback_model`


_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _env_bool(name: str, default: bool) -> bool:
    """Strict: a typo such as "flase" fails instead of silently keeping the default (the fallback would stay on)."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    word = value.strip().lower()
    if word in _TRUE:
        return True
    if word in _FALSE:
        return False
    raise ConfigurationError(f"{name}={value!r} is not a boolean; use true or false")


def _model_limits(prefix: str, rpm: int, tpm: int, rpd: int, throttle_rpm: int) -> ModelLimits:
    limits = ModelLimits(
        rpm=int(os.getenv(f"{prefix}_LIMIT_RPM", rpm)),
        tpm=int(os.getenv(f"{prefix}_LIMIT_TPM", tpm)),
        rpd=int(os.getenv(f"{prefix}_LIMIT_RPD", rpd)),
        throttle_rpm=int(os.getenv(f"{prefix}_THROTTLE_RPM", throttle_rpm)),
    )
    if not 1 <= limits.throttle_rpm <= limits.rpm:
        raise ConfigurationError(
            f"{prefix}_THROTTLE_RPM={limits.throttle_rpm} must be between 1 and {prefix}_LIMIT_RPM={limits.rpm}"
        )
    return limits


def get_answer_settings() -> AnswerSettings:
    max_attempts = int(os.getenv("ANSWER_MAX_ATTEMPTS", "3"))
    if max_attempts < 1:
        raise ConfigurationError(f"ANSWER_MAX_ATTEMPTS={max_attempts} must be at least 1")
    return AnswerSettings(
        model=os.getenv("ANSWER_MODEL", "gemini-3.5-flash-lite"),
        fallback_model=os.getenv("FALLBACK_MODEL", "gemini-3.5-flash"),
        allow_fallback=_env_bool("ALLOW_FALLBACK", True),
        max_attempts=max_attempts,
        timeout_s=float(os.getenv("ANSWER_TIMEOUT_S", "60")),
        prompt_version=os.getenv("ANSWER_PROMPT_VERSION", "answer_v2"),
        prompts_dir=resolve_project_path(os.getenv("PROMPTS_DIR", "config/prompts")),
        messages_path=resolve_project_path(os.getenv("MESSAGES_PATH", "config/messages.json")),
        limits=_model_limits("ANSWER", rpm=15, tpm=250_000, rpd=500, throttle_rpm=13),
        fallback_limits=_model_limits("FALLBACK", rpm=5, tpm=250_000, rpd=20, throttle_rpm=4),
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
