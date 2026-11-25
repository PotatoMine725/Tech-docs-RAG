"""Local multilingual cross-encoder reranker on ONNX Runtime, CPU only (ADR-0009).

Scores (question, passage) pairs jointly; the score is sigmoid(logit) of the model's single relevance logit, a fixed
0..1 scale, so `absolute_scores` is true and a gate can read it.

Length: the question is cut to MAX_QUERY_TOKENS; each passage then gets min(`max_passage_tokens`, positions left), so
the pair never exceeds the model's positions (`config.json` `max_position_embeddings`, minus XLM-R's offset of 2:
512 for mMiniLM, 8192 for gte and bge-m3). Cuts are made on the tokenizer's character offsets. Only the inputs the
ONNX graph declares are fed (XLM-R exports have no `token_type_ids`).

onnxruntime / tokenizers / numpy are the optional `[local]` extra, imported on first use; the model loads on the
first `rerank`. Supported exports: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 (int8 = `model_quint8_avx2.onnx`),
onnx-community gte-multilingual-reranker-base and bge-reranker-v2-m3-ONNX (int8 = `model_int8.onnx`).
"""
from __future__ import annotations

import json
import math
import threading
from pathlib import Path
from typing import Any

from knowledge_assistant.config import RerankSettings, get_rerank_settings
from knowledge_assistant.core.exceptions import ConfigurationError, RetrievalError
from knowledge_assistant.core.interfaces.reranker import RerankResult

ONNX_FILES = {"fp32": ("model.onnx",), "int8": ("model_int8.onnx", "model_quint8_avx2.onnx")}
DEFAULT_POSITIONS = 512  # when the export has no readable config.json
MAX_QUERY_TOKENS = 128
SPECIAL_TOKENS = 4  # XLM-R pair: <s> q </s></s> p </s>


def max_positions(model_dir: Path) -> int:
    """Usable input length of the export: `max_position_embeddings` (minus 2 for XLM-R's padding offset), capped by
    the tokenizer's `model_max_length` when that is smaller."""
    try:
        config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_POSITIONS
    positions = int(config.get("max_position_embeddings", DEFAULT_POSITIONS))
    if config.get("model_type") == "xlm-roberta":
        positions -= 2
    try:
        limit = json.loads((model_dir / "tokenizer_config.json").read_text(encoding="utf-8")).get("model_max_length")
    except (OSError, ValueError):
        limit = None
    return min(positions, int(limit)) if isinstance(limit, (int, float)) and limit > 0 else positions


def onnx_file(model_dir: Path, variant: str) -> Path:
    """The first existing file of the variant in `model_dir/onnx`."""
    for name in ONNX_FILES[variant]:
        path = model_dir / "onnx" / name
        if path.is_file():
            return path
    raise ConfigurationError(f"no {variant} ONNX file ({', '.join(ONNX_FILES[variant])}) in {model_dir / 'onnx'}")


class OnnxCrossEncoderReranker:
    def __init__(self, settings: RerankSettings | None = None, session: Any = None, tokenizer: Any = None,
                 positions: int | None = None) -> None:
        """`session` / `tokenizer` / `positions` are for tests (ONNX Runtime's `run`/`get_inputs`, the tokenizers
        library's API, the model's input length)."""
        self._settings = settings or get_rerank_settings()
        self._positions = positions
        self._session = session
        self._tokenizer = tokenizer
        self._inputs: set[str] | None = None
        self._lock = threading.Lock()

    @property
    def model_id(self) -> str:
        return self._settings.model_id

    @property
    def absolute_scores(self) -> bool:
        return True

    def truncate(self, text: str, limit: int | None = None) -> str:
        """`text` cut after its first `limit` tokens (default `max_passage_tokens`), at that token's end offset."""
        _, tokenizer = self._load()
        limit = self._settings.max_passage_tokens if limit is None else limit
        offsets = tokenizer.encode(text, add_special_tokens=False).offsets
        return text if len(offsets) <= limit else text[: offsets[limit - 1][1]]

    def rerank(self, query: str, passages: list[str], top_n: int | None = None) -> list[RerankResult]:
        if not passages:
            return []
        scores = self.score(query, passages)
        order = sorted(range(len(passages)), key=lambda i: (-scores[i], i))
        count = len(order) if top_n is None else max(0, min(top_n, len(order)))
        return [RerankResult(index=i, score=scores[i]) for i in order[:count]]

    def score(self, query: str, passages: list[str]) -> list[float]:
        """sigmoid(logit) per passage, in input order."""
        import numpy as np

        session, tokenizer = self._load()
        query = self.truncate(query, MAX_QUERY_TOKENS)
        room = self.positions - len(tokenizer.encode(query, add_special_tokens=False).ids) - SPECIAL_TOKENS
        pairs = [(query, self.truncate(p, max(1, min(self._settings.max_passage_tokens, room)))) for p in passages]
        scores: list[float] = []
        size = self._settings.batch_size
        for start in range(0, len(pairs), size):
            encoded = tokenizer.encode_batch(pairs[start : start + size])
            width = max(len(e.ids) for e in encoded)
            ids = np.full((len(encoded), width), self._pad_id, dtype=np.int64)
            mask = np.zeros((len(encoded), width), dtype=np.int64)
            types = np.zeros((len(encoded), width), dtype=np.int64)
            for row, e in enumerate(encoded):
                ids[row, : len(e.ids)] = e.ids
                mask[row, : len(e.ids)] = 1
                types[row, : len(e.ids)] = e.type_ids
            feed = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
            try:
                (logits,) = session.run(["logits"], {k: v for k, v in feed.items() if k in self._inputs})
            except Exception as error:  # ONNX Runtime raises its own exception types
                raise RetrievalError(f"reranking failed: {error}") from error
            logits = np.asarray(logits, dtype=np.float64).reshape(len(encoded), -1)[:, 0]
            if not np.all(np.isfinite(logits)):
                raise RetrievalError("reranker returned a non-finite score")
            scores += [1.0 / (1.0 + math.exp(-x)) for x in logits.tolist()]
        return scores

    @property
    def positions(self) -> int:
        if self._positions is None:
            model_dir = self._settings.model_dir
            self._positions = max_positions(model_dir) if model_dir is not None else DEFAULT_POSITIONS
        return self._positions

    def _load(self) -> tuple[Any, Any]:
        with self._lock:
            if self._session is None or self._tokenizer is None:
                self._session, self._tokenizer = self._open()
            if self._inputs is None:
                self._inputs = {i.name for i in self._session.get_inputs()}
                if not {"input_ids", "attention_mask"} <= self._inputs:
                    raise ConfigurationError(f"reranker ONNX model inputs {sorted(self._inputs)} lack input_ids/mask")
                self._tokenizer.no_padding()
                self._tokenizer.no_truncation()
                pad = self._tokenizer.token_to_id("<pad>")
                self._pad_id = 0 if pad is None else pad
        return self._session, self._tokenizer

    def _open(self) -> tuple[Any, Any]:
        model_dir = self._settings.model_dir
        if model_dir is None:
            raise ConfigurationError("RERANK_PROVIDER=cross-encoder needs RERANK_MODEL_DIR (tokenizer.json and onnx/)")
        onnx_path, tokenizer_path = onnx_file(model_dir, self._settings.variant), model_dir / "tokenizer.json"
        if not tokenizer_path.is_file():
            raise ConfigurationError(f"reranker tokenizer not found: {tokenizer_path}")
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as error:
            raise ConfigurationError("the local reranker needs onnxruntime, tokenizers and numpy: "
                                     "pip install -e .[local]") from error
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.intra_op_num_threads = self._settings.threads
        options.inter_op_num_threads = 1
        try:
            session = ort.InferenceSession(str(onnx_path), options, providers=["CPUExecutionProvider"])
            tokenizer = Tokenizer.from_file(str(tokenizer_path))
        except Exception as error:  # corrupt or incompatible files raise the libraries' own exception types
            raise ConfigurationError(f"cannot load the reranker from {model_dir}: {error}") from error
        if "logits" not in [o.name for o in session.get_outputs()]:
            raise ConfigurationError(f"{onnx_path.name} has no `logits` output")
        return session, tokenizer
