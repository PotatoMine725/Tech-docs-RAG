"""Local EmbeddingGemma v1 embedder behind core.interfaces.embedding (embedding benchmark 2026-11-21).

ONNX Runtime on the CPU, no network. Same prompts as the benchmark: documents get ``title: none | text: ``, queries
``task: search result | query: ``. The ONNX graph returns the pooled, projected, normalized `sentence_embedding`;
a smaller `dim` keeps the first `dim` values (Matryoshka) and normalizes again.

onnxruntime / tokenizers / numpy are optional dependencies (`pip install -e .[local]`), imported on first use, so the
Gemini-only setup does not need them. The model is loaded on the first `embed`, not in the constructor.
"""
from __future__ import annotations

import threading
from typing import Any

from knowledge_assistant.config import LocalEmbeddingSettings, get_local_embedding_settings
from knowledge_assistant.core.exceptions import ConfigurationError, EmbeddingError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask

PREFIXES = {
    EmbeddingTask.DOCUMENT: "title: none | text: ",
    EmbeddingTask.QUERY: "task: search result | query: ",
}
ONNX_FILES = {"fp32": "model", "fp16": "model_fp16", "int8": "model_quantized", "int4": "model_q4"}
OUTPUT = "sentence_embedding"


class EmbeddingGemmaEmbedder:
    def __init__(
        self,
        settings: LocalEmbeddingSettings | None = None,
        session: Any = None,
        tokenizer: Any = None,
    ) -> None:
        """`session` / `tokenizer` are for tests: anything with ONNX Runtime's `run`/`get_inputs` and the tokenizers
        library's `encode_batch`."""
        self._settings = settings or get_local_embedding_settings()
        self._session = session
        self._tokenizer = tokenizer
        self._load_lock = threading.Lock()
        self.batches = 0
        self.texts = 0

    @property
    def model_id(self) -> str:
        return self._settings.model_id

    def stats(self) -> dict[str, float]:
        return {"batches": self.batches, "texts": self.texts, "api_requests": 0}

    def _index_groups(self, texts: list[str]) -> list[list[int]]:
        """Indices sorted by token count (stable), cut into groups of `batch_size`. Similar lengths share a batch, so
        little padding is computed (the benchmark's encode_all sorts the same way). Token count, not character
        count: on arm A, character sorting gave 6.85 texts/s and token sorting 8.08, back to back
        (docs/reports/2026-11-23-local-reindex.md). The prefix is the same for every text, so it is left out."""
        if not texts:
            return []
        _, tokenizer = self._load()
        lengths = [len(e.ids) for e in tokenizer.encode_batch(texts)]
        order = sorted(range(len(texts)), key=lengths.__getitem__)
        size = self._settings.batch_size
        return [order[i : i + size] for i in range(0, len(order), size)]

    def plan_calls(self, texts: list[str]) -> list[list[str]]:
        """Token-length-sorted groups of at most `batch_size` texts; together they hold every text once, NOT in input
        order. `embed(group)` runs one ONNX batch (a group plans to itself), so the cache commits after each."""
        return [[texts[i] for i in group] for group in self._index_groups(texts)]

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        """Vectors in input order, whatever order the batches ran in."""
        if not texts:
            return []
        np = _numpy()
        session, tokenizer = self._load()
        prefix = PREFIXES[task]
        vectors: list[list[float]] = [[] for _ in texts]
        for group in self._index_groups(texts):
            batch = [texts[i] for i in group]
            encoded = tokenizer.encode_batch([prefix + text for text in batch])
            ids = [e.ids[: self._settings.max_tokens] for e in encoded]
            width = max(len(x) for x in ids)
            input_ids = np.zeros((len(ids), width), dtype=self._int_type)
            mask = np.zeros((len(ids), width), dtype=self._int_type)
            for row, x in enumerate(ids):
                input_ids[row, : len(x)] = x
                mask[row, : len(x)] = 1
            feed = {"input_ids": input_ids}
            if self._has_mask:
                feed["attention_mask"] = mask
            try:
                (out,) = session.run([OUTPUT], feed)
            except Exception as error:  # ONNX Runtime raises its own exception types
                raise EmbeddingError(f"local embedding failed: {error}") from error
            finished = self._finish(np.asarray(out, dtype=np.float32))
            if len(finished) != len(group):
                raise EmbeddingError(f"local model returned {len(finished)} vectors for {len(group)} texts")
            for i, vector in zip(group, finished):
                vectors[i] = vector
            self.batches += 1
            self.texts += len(batch)
        return vectors

    def _finish(self, out: Any) -> list[list[float]]:
        np = _numpy()
        if out.ndim != 2 or out.shape[1] < self._settings.dim:
            raise EmbeddingError(f"unexpected embedding shape {tuple(out.shape)}")
        out = out[:, : self._settings.dim]
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        if not np.all(np.isfinite(out)) or np.any(norms < 1e-12):
            raise EmbeddingError("local model returned a zero or non-finite vector")
        return (out / norms).tolist()

    def _load(self) -> tuple[Any, Any]:
        with self._load_lock:
            if self._session is None or self._tokenizer is None:
                self._session, self._tokenizer = self._open()
            if not hasattr(self, "_int_type"):
                np = _numpy()
                inputs = {i.name: i for i in self._session.get_inputs()}
                if "input_ids" not in inputs:
                    raise ConfigurationError(f"ONNX model has no input_ids input ({sorted(inputs)})")
                self._has_mask = "attention_mask" in inputs
                self._int_type = np.int64 if "int64" in str(inputs["input_ids"].type) else np.int32
        return self._session, self._tokenizer

    def _open(self) -> tuple[Any, Any]:
        model_dir = self._settings.model_dir
        if model_dir is None:
            raise ConfigurationError(
                "EMBEDDING_PROVIDER=embeddinggemma needs LOCAL_EMBEDDING_MODEL_DIR (folder with tokenizer.json and onnx/)"
            )
        onnx_path = model_dir / "onnx" / f"{ONNX_FILES[self._settings.variant]}.onnx"
        tokenizer_path = model_dir / "tokenizer.json"
        for path in (onnx_path, tokenizer_path):
            if not path.is_file():
                raise ConfigurationError(f"local embedding model file not found: {path}")
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as error:
            raise ConfigurationError(
                "local embedding needs onnxruntime, tokenizers and numpy: pip install -e .[local]"
            ) from error
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.intra_op_num_threads = self._settings.threads
        options.inter_op_num_threads = 1
        try:
            session = ort.InferenceSession(str(onnx_path), options, providers=["CPUExecutionProvider"])
            tokenizer = Tokenizer.from_file(str(tokenizer_path))
        except Exception as error:  # corrupt or incompatible files raise the libraries' own exception types
            raise ConfigurationError(f"cannot load the local embedding model from {model_dir}: {error}") from error
        if OUTPUT not in [o.name for o in session.get_outputs()]:
            raise ConfigurationError(f"{onnx_path.name} has no {OUTPUT} output; use the onnx-community export")
        return session, tokenizer


def _numpy() -> Any:
    try:
        import numpy
    except ImportError as error:
        raise ConfigurationError("local embedding needs numpy: pip install -e .[local]") from error
    return numpy
