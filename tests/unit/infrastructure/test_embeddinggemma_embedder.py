"""Local EmbeddingGemma embedder with a fake ONNX session and tokenizer: prompts, padding, truncation, normalization."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from knowledge_assistant.config import get_local_embedding_settings
from knowledge_assistant.core.exceptions import ConfigurationError, EmbeddingError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.embeddings.embeddinggemma_embedder import EmbeddingGemmaEmbedder
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder


class FakeTokenizer:
    def __init__(self):
        self.seen = []

    def encode_batch(self, texts):
        self.seen.extend(texts)
        return [SimpleNamespace(ids=[(ord(c) % 50) + 1 for c in t]) for t in texts]


class FakeSession:
    def __init__(self, dim=768, int_type="tensor(int64)", output=None):
        self.dim, self.int_type, self.output, self.feeds = dim, int_type, output, []

    def get_inputs(self):
        return [SimpleNamespace(name="input_ids", type=self.int_type), SimpleNamespace(name="attention_mask", type=self.int_type)]

    def run(self, names, feed):
        assert names == ["sentence_embedding"]
        self.feeds.append(feed)
        if self.output is not None:
            return [self.output]
        lengths = feed["attention_mask"].sum(axis=1).astype(np.float32)
        out = np.ones((len(lengths), self.dim), dtype=np.float32)
        out[:, 0] = lengths * 10  # depends on the text, so vectors differ
        return [out]


def make(tmp_path, **overrides):
    settings = replace(get_local_embedding_settings(), cache_path=tmp_path / "c.sqlite", **overrides)
    session, tokenizer = FakeSession(), FakeTokenizer()
    return EmbeddingGemmaEmbedder(settings, session=session, tokenizer=tokenizer), session, tokenizer


def test_model_id_names_variant_and_dim(tmp_path):
    assert make(tmp_path)[0].model_id == "embeddinggemma-300m-fp32@768"
    assert make(tmp_path, variant="int4", dim=256)[0].model_id == "embeddinggemma-300m-int4@256"


def test_task_prompts_match_the_benchmark(tmp_path):
    embedder, _, tokenizer = make(tmp_path)
    embedder.embed(["doc"], EmbeddingTask.DOCUMENT)
    embedder.embed(["q"], EmbeddingTask.QUERY)
    assert tokenizer.seen == ["title: none | text: doc", "task: search result | query: q"]


def test_batches_are_padded_with_a_mask_and_truncated(tmp_path):
    embedder, session, _ = make(tmp_path, max_tokens=25, batch_size=2)
    embedder.embed(["a", "a much longer text than the limit allows"], EmbeddingTask.QUERY)
    feed = session.feeds[0]
    assert feed["input_ids"].dtype == np.int64 and feed["input_ids"].shape[1] == 25
    assert feed["attention_mask"].sum(axis=1).tolist() == [len("task: search result | query: a"[:25]), 25]


def test_vectors_are_unit_length_and_truncated_to_dim(tmp_path):
    embedder, _, _ = make(tmp_path, dim=256)
    vectors = embedder.embed(["x", "longer text"], EmbeddingTask.DOCUMENT)
    assert all(len(v) == 256 for v in vectors)
    assert all(abs(np.linalg.norm(v) - 1.0) < 1e-5 for v in vectors)
    assert vectors[0] != vectors[1]


def test_plan_calls_splits_by_batch_size_and_the_cache_commits_per_group(tmp_path):
    embedder, session, _ = make(tmp_path, batch_size=3)
    texts = [f"t{i}" for i in range(7)]
    assert [len(g) for g in embedder.plan_calls(texts)] == [3, 3, 1]
    with CachingEmbedder(embedder, tmp_path / "c.sqlite") as cache:
        first = cache.embed(texts, EmbeddingTask.DOCUMENT)
        again = cache.embed(texts, EmbeddingTask.DOCUMENT)
    assert len(session.feeds) == 3 and first == again and embedder.stats()["texts"] == 7


def test_a_zero_vector_is_an_embedding_error(tmp_path):
    settings = replace(get_local_embedding_settings(), cache_path=tmp_path / "c.sqlite")
    session = FakeSession(output=np.zeros((1, 768), dtype=np.float32))
    with pytest.raises(EmbeddingError):
        EmbeddingGemmaEmbedder(settings, session=session, tokenizer=FakeTokenizer()).embed(["x"], EmbeddingTask.QUERY)


def test_missing_model_dir_is_a_configuration_error_naming_the_variable(tmp_path):
    settings = replace(get_local_embedding_settings(), model_dir=None)
    with pytest.raises(ConfigurationError, match="LOCAL_EMBEDDING_MODEL_DIR"):
        EmbeddingGemmaEmbedder(settings).embed(["x"], EmbeddingTask.QUERY)


def test_missing_model_file_is_a_configuration_error(tmp_path):
    settings = replace(get_local_embedding_settings(), model_dir=Path(tmp_path))
    with pytest.raises(ConfigurationError, match="not found"):
        EmbeddingGemmaEmbedder(settings).embed(["x"], EmbeddingTask.QUERY)


def test_construction_loads_nothing(tmp_path):
    settings = replace(get_local_embedding_settings(), model_dir=Path(tmp_path) / "absent")
    EmbeddingGemmaEmbedder(settings)  # no error: the model loads on the first embed
