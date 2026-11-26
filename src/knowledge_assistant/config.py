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


CORPORA = ("corpus1", "corpus2")  # corpus 2 = ADR-0008; each corpus has its own chunks, collections and keyword index


def get_corpus() -> str:
    """Which corpus the ingestion scripts, the stores and the evaluation runner work on (CORPUS; default corpus1)."""
    value = (os.getenv("CORPUS") or "corpus1").strip().lower()
    if value not in CORPORA:
        raise ConfigurationError(f"CORPUS={value!r} is not one of {', '.join(CORPORA)}")
    return value


def corpus_scoped(path: Path, corpus: str | None = None) -> Path:
    """Corpus 1 keeps the path as is (every existing index and run stays where it is); another corpus gets the sibling
    `<name>-<corpus>`, also when the base comes from an environment override, so two corpora never share a Chroma
    directory, a keyword-index file or a chunk file (collection names are keyed by chunker config, which both share)."""
    corpus = corpus or get_corpus()
    return path if corpus == "corpus1" else path.with_name(f"{path.name}-{corpus}")


def get_chroma_path(corpus: str | None = None) -> Path:
    """OD-7 (ADR-0005): repo-local, git-ignored, rebuilt by script. Scoped per corpus (`corpus_scoped`)."""
    return corpus_scoped(resolve_project_path(os.getenv("CHROMA_PATH", "data/chroma")), corpus)


def get_chunks_dir(corpus: str | None = None) -> Path:
    """Chunk files written by scripts/ingestion/build_chunks.py (arm-a.jsonl, arm-b.jsonl). Scoped per corpus; the
    corpus-2 chunks hold non-redistributable text and are git-ignored (ADR-0008)."""
    return corpus_scoped(resolve_project_path(os.getenv("CHUNKS_DIR", "data/processed/chunks")), corpus)


def get_normalized_path(corpus: str | None = None) -> Path:
    """The ingested document text (normalized.jsonl) that chunking reads. Scoped per corpus like the chunks."""
    documents = corpus_scoped(resolve_project_path("data/processed/documents"), corpus)
    return documents / "normalized.jsonl"


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


EMBEDDING_PROVIDERS = ("gemini", "embeddinggemma")
LOCAL_EMBEDDING_VARIANTS = ("fp32", "fp16", "int8", "int4")
LOCAL_EMBEDDING_DIMS = (768, 512, 256, 128)  # Matryoshka sizes EmbeddingGemma was trained for


def _choice(name: str, default: str, allowed: tuple[str, ...]) -> str:
    value = (os.getenv(name) or default).strip().lower()
    if value not in allowed:
        raise ConfigurationError(f"{name}={value!r} is not one of {', '.join(allowed)}")
    return value


def get_embedding_provider() -> str:
    """Which embedder answers queries and builds the index: `gemini` (cloud, default) or `embeddinggemma` (local)."""
    return _choice("EMBEDDING_PROVIDER", "gemini", EMBEDDING_PROVIDERS)


@dataclass(frozen=True)
class LocalEmbeddingSettings:
    """Local EmbeddingGemma v1 (300M) on ONNX Runtime, CPU only (embedding benchmark 2026-11-21, owner decision:
    v1, FP32 default, INT4 as the low-RAM option, embedder budget <= 1 GB).

    `model_dir` holds `tokenizer.json` and `onnx/<variant file>.onnx` (the onnx-community export layout). Nothing is
    downloaded by the app. `threads` 0 lets ONNX Runtime pick (all physical cores).
    """

    model_dir: Path | None
    variant: str
    dim: int
    batch_size: int
    threads: int
    max_tokens: int
    cache_path: Path

    @property
    def model_id(self) -> str:
        """Cache / collection key: export revision, variant, token limit and size. Any of them changes the vectors
        (INT4 is close to, not equal to, FP32), so each combination gets its own cache entries and collection."""
        return f"embeddinggemma-300m{self._revision_tag()}-{self.variant}-t{self.max_tokens}@{self.dim}"

    def _revision_tag(self) -> str:
        """`-<8 hex>` from the export's REVISION file (``<repo>@<commit>``, written when the model was downloaded);
        empty when there is none."""
        if self.model_dir is None:
            return ""
        try:
            revision = (self.model_dir / "REVISION").read_text(encoding="utf-8").strip()
        except OSError:
            return ""
        commit = revision.rpartition("@")[2]
        return f"-{commit[:8]}" if commit else ""


def get_local_embedding_settings() -> LocalEmbeddingSettings:
    model_dir = os.getenv("LOCAL_EMBEDDING_MODEL_DIR")
    dim = int(os.getenv("LOCAL_EMBEDDING_DIM", "768"))
    if dim not in LOCAL_EMBEDDING_DIMS:
        raise ConfigurationError(f"LOCAL_EMBEDDING_DIM={dim} must be one of {LOCAL_EMBEDDING_DIMS}")
    batch_size = int(os.getenv("LOCAL_EMBEDDING_BATCH_SIZE", "8"))
    threads = int(os.getenv("LOCAL_EMBEDDING_THREADS", "0"))
    max_tokens = int(os.getenv("LOCAL_EMBEDDING_MAX_TOKENS", "2048"))
    if batch_size < 1 or threads < 0 or max_tokens < 1:
        raise ConfigurationError("LOCAL_EMBEDDING_BATCH_SIZE and _MAX_TOKENS must be >= 1, _THREADS >= 0")
    return LocalEmbeddingSettings(
        model_dir=resolve_project_path(model_dir) if model_dir else None,
        variant=_choice("LOCAL_EMBEDDING_VARIANT", "fp32", LOCAL_EMBEDDING_VARIANTS),
        dim=dim,
        batch_size=batch_size,
        threads=threads,
        max_tokens=max_tokens,
        cache_path=resolve_project_path(os.getenv("EMBEDDING_CACHE_PATH", "data/cache/embeddings.sqlite")),
    )


def get_active_embedding_model_id() -> str:
    """The model id of the configured embedding provider: names the cache entries and the Chroma collection."""
    if get_embedding_provider() == "embeddinggemma":
        return get_local_embedding_settings().model_id
    return get_embedding_settings().model_id


LLM_PROVIDERS = ("gemini", "llamacpp")


def get_llm_provider() -> str:
    """Which LLM writes the answers: `gemini` (default). `llamacpp` is reserved for the local GGUF provider."""
    return _choice("LLM_PROVIDER", "gemini", LLM_PROVIDERS)


RERANK_PROVIDERS = ("none", "cross-encoder")
RERANK_VARIANTS = ("fp32", "int8")


def get_rerank_provider() -> str:
    """Reranking after retrieval (ADR-0009): `none` (default, keep the retriever's order) or `cross-encoder` (a local
    ONNX cross-encoder from RERANK_MODEL_DIR)."""
    return _choice("RERANK_PROVIDER", "none", RERANK_PROVIDERS)


@dataclass(frozen=True)
class RerankSettings:
    """Local ONNX cross-encoder reranker (ADR-0009), CPU only, loaded on the first `rerank`. `model_dir` holds
    `tokenizer.json` and `onnx/` (fp32 `model.onnx`; int8 `model_int8.onnx` or `model_quint8_avx2.onnx`). The retriever
    reranks its best `candidates` unique passages. Each (question, window) pair is at most `max_tokens` tokens (and
    never more than the model's positions): a window is `max_tokens` - question - 4 special tokens long, consecutive
    windows overlap by `window_overlap` tokens, and the passage score is its best window's (MaxP; owner decisions
    2026-11-25: no head cut, window from the model limit, nothing tuned on the test set). `threads` 0 lets ONNX
    Runtime pick. Nothing is downloaded by the app."""

    model_dir: Path | None
    variant: str
    candidates: int
    max_tokens: int
    window_overlap: int
    batch_size: int
    threads: int

    @property
    def model_id(self) -> str:
        """Folder name, export revision, variant, pair length and overlap: each changes the scores."""
        name = self.model_dir.name if self.model_dir else "unset"
        revision = ""
        if self.model_dir is not None:
            try:
                commit = (self.model_dir / "REVISION").read_text(encoding="utf-8").strip().rpartition("@")[2]
                revision = f"-{commit[:8]}" if commit else ""
            except OSError:
                pass
        return f"{name}{revision}-{self.variant}-t{self.max_tokens}o{self.window_overlap}"


def get_rerank_settings() -> RerankSettings:
    model_dir = os.getenv("RERANK_MODEL_DIR")
    candidates = int(os.getenv("RERANK_CANDIDATES", "10"))  # K chosen on speed, ADR-0009
    max_tokens = int(os.getenv("RERANK_MAX_TOKENS", "512"))
    window_overlap = int(os.getenv("RERANK_WINDOW_OVERLAP", "128"))
    batch_size = int(os.getenv("RERANK_BATCH_SIZE", "8"))
    threads = int(os.getenv("RERANK_THREADS", "0"))
    if candidates < 1 or batch_size < 1 or threads < 0:
        raise ConfigurationError("RERANK_CANDIDATES and RERANK_BATCH_SIZE must be >= 1, RERANK_THREADS >= 0")
    if max_tokens < 16 or not 0 <= window_overlap < max_tokens // 2:
        raise ConfigurationError(f"RERANK_MAX_TOKENS={max_tokens} must be >= 16 and RERANK_WINDOW_OVERLAP="
                                 f"{window_overlap} between 0 and half of it")
    return RerankSettings(
        model_dir=resolve_project_path(model_dir) if model_dir else None,
        variant=_choice("RERANK_VARIANT", "int8", RERANK_VARIANTS),
        candidates=candidates,
        max_tokens=max_tokens,
        window_overlap=window_overlap,
        batch_size=batch_size,
        threads=threads,
    )


def get_rerank_model_id() -> str:
    """`none`, or the configured cross-encoder's model id (recorded in evaluation runs)."""
    return "none" if get_rerank_provider() == "none" else get_rerank_settings().model_id


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
    fallback_max_output_tokens: int  # output budget of the fallback call; the answer model uses the request's (1024)


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
    fallback_max_output_tokens = int(os.getenv("FALLBACK_MAX_OUTPUT_TOKENS", "2048"))
    if fallback_max_output_tokens < 1:
        raise ConfigurationError(f"FALLBACK_MAX_OUTPUT_TOKENS={fallback_max_output_tokens} must be at least 1")
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
        fallback_max_output_tokens=fallback_max_output_tokens,
    )


@dataclass(frozen=True)
class JudgeSettings:
    """LLM judge (EVAL-003b; ADR-0004 D12: the judge is `gemini-3.5-flash-lite`, the same model as the answers, so its
    verdicts get a manual spot-check). Temperature 0 and no fallback are fixed, not configurable: a judgement from any
    other model is rejected. The prompt version is the file name (without .md) in `prompts_dir`."""

    model: str
    prompt_version: str
    prompts_dir: Path
    max_attempts: int
    timeout_s: float
    max_output_tokens: int
    limits: ModelLimits  # of `model`; the throttle is 13 RPM like the answer model's


def get_judge_settings() -> JudgeSettings:
    max_attempts = int(os.getenv("JUDGE_MAX_ATTEMPTS", "3"))
    if max_attempts < 1:
        raise ConfigurationError(f"JUDGE_MAX_ATTEMPTS={max_attempts} must be at least 1")
    max_output_tokens = int(os.getenv("JUDGE_MAX_OUTPUT_TOKENS", "2048"))
    if max_output_tokens < 1:
        raise ConfigurationError(f"JUDGE_MAX_OUTPUT_TOKENS={max_output_tokens} must be at least 1")
    return JudgeSettings(
        model=os.getenv("JUDGE_MODEL", "gemini-3.5-flash-lite"),
        prompt_version=os.getenv("JUDGE_PROMPT_VERSION", "judge_v1"),
        prompts_dir=resolve_project_path(os.getenv("PROMPTS_DIR", "config/prompts")),
        max_attempts=max_attempts,
        timeout_s=float(os.getenv("JUDGE_TIMEOUT_S", "60")),
        max_output_tokens=max_output_tokens,
        limits=_model_limits("JUDGE", rpm=15, tpm=250_000, rpd=500, throttle_rpm=13),
    )


def get_pricing_path() -> Path:
    """Token prices for the cost estimate (EVAL-003b §4); null prices mean "not available", never a guess."""
    return resolve_project_path(os.getenv("PRICING_PATH", "config/pricing.json"))


@dataclass(frozen=True)
class RetrievalSettings:
    """top_k = 5 for both arms (ADR-0003 D7). The threshold is the OD-9 retrieval gate, tuned on the dev set, Arm A,
    used for both arms (retrieval-spec.md; RAG-002, 2026-09-26)."""

    top_k: int
    overfetch: int  # extra hits fetched so same-content duplicates can be dropped (RAG-002 addendum 1)
    insufficient_score_threshold: float  # compared with the dense top-1 score in every mode (ADR-0007 D6)
    mode: str = "dense"  # dense | sparse | hybrid (ADR-0007)
    rrf_k: int = 60  # Reciprocal Rank Fusion constant, hybrid mode only (ADR-0007 D5)


# OD-9 gate threshold per embedding provider: scores of different embedders are not comparable. Each value comes from
# the same rule (dev set, Arm A, lowest answerable top-1 - 0.05; retrieval-spec.md). gemini: RAG-002, 2026-09-26.
# embeddinggemma: tuned for fp32 @768 ONLY (2026-11-23, ADR-0006). It is still applied to any other variant
# (int4 ...) or dimension (512/256/128), whose scores differ: there it is an untested cutoff (TBD), so set
# INSUFFICIENT_SCORE_THRESHOLD after tuning that configuration with the same rule.
GATE_THRESHOLDS = {"gemini": 0.686, "embeddinggemma": 0.5417}

RETRIEVAL_MODES = ("dense", "sparse", "hybrid")  # same values as application.retrieval.retrieve.RETRIEVAL_MODES


def get_retrieval_settings() -> RetrievalSettings:
    """`INSUFFICIENT_SCORE_THRESHOLD`, when set, overrides the provider's default (the embeddinggemma default is tuned
    for fp32 @768 only, see GATE_THRESHOLDS). `RETRIEVAL_MODE` defaults to dense, the behaviour of every recorded run."""
    override = (os.getenv("INSUFFICIENT_SCORE_THRESHOLD") or "").strip()
    rrf_k = int(os.getenv("RRF_K", "60"))
    if rrf_k < 1:
        raise ConfigurationError(f"RRF_K={rrf_k} must be at least 1")
    return RetrievalSettings(
        top_k=int(os.getenv("TOP_K", "5")),
        overfetch=int(os.getenv("RETRIEVAL_OVERFETCH", "10")),
        insufficient_score_threshold=float(override) if override else GATE_THRESHOLDS[get_embedding_provider()],
        mode=_choice("RETRIEVAL_MODE", "dense", RETRIEVAL_MODES),
        rrf_k=rrf_k,
    )


def get_keyword_index_dir(corpus: str | None = None) -> Path:
    """The FTS5 keyword index files, one per arm (ADR-0007); git-ignored, rebuilt by build_index.py. Scoped per corpus."""
    return corpus_scoped(resolve_project_path(os.getenv("KEYWORD_INDEX_DIR", "data/keyword")), corpus)
