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


def test_model_id_names_variant_token_limit_and_dim(tmp_path):
    assert make(tmp_path, model_dir=None)[0].model_id == "embeddinggemma-300m-fp32-t2048@768"
    assert make(tmp_path, model_dir=None, variant="int4", dim=256, max_tokens=512)[0].model_id == \
        "embeddinggemma-300m-int4-t512@256"


def test_model_id_includes_the_export_revision(tmp_path):
    (tmp_path / "REVISION").write_text("onnx-community/embeddinggemma-300m-ONNX@5090578d9565bb06\n", encoding="utf-8")
    assert make(tmp_path, model_dir=tmp_path)[0].model_id == "embeddinggemma-300m-5090578d-fp32-t2048@768"


def test_a_corrupt_model_file_is_a_configuration_error(tmp_path):
    (tmp_path / "onnx").mkdir()
    (tmp_path / "onnx" / "model.onnx").write_bytes(b"not a model")
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    settings = replace(get_local_embedding_settings(), model_dir=tmp_path)
    with pytest.raises(ConfigurationError, match="cannot load"):
        EmbeddingGemmaEmbedder(settings).embed(["x"], EmbeddingTask.QUERY)


def test_task_prompts_match_the_benchmark(tmp_path):
    embedder, _, tokenizer = make(tmp_path)
    embedder.embed(["doc"], EmbeddingTask.DOCUMENT)
    embedder.embed(["q"], EmbeddingTask.QUERY)
    prompted = [t for t in tokenizer.seen if " | " in t]  # the plan also tokenizes the bare texts to sort them
    assert prompted == ["title: none | text: doc", "task: search result | query: q"]


def test_batches_are_zero_padded_with_a_matching_mask(tmp_path):
    embedder, session, _ = make(tmp_path, batch_size=2)
    embedder.embed(["a", "abcd"], EmbeddingTask.QUERY)
    feed = session.feeds[0]
    short, long = (len("task: search result | query: " + t) for t in ("a", "abcd"))
    assert feed["input_ids"].dtype == np.int64 and feed["input_ids"].shape == (2, long)
    assert feed["attention_mask"][0].tolist() == [1] * short + [0] * (long - short)
    assert feed["attention_mask"][1].tolist() == [1] * long
    assert feed["input_ids"][0, short:].tolist() == [0] * (long - short) and all(feed["input_ids"][0, :short] > 0)


def test_long_texts_are_truncated_to_max_tokens(tmp_path):
    embedder, session, _ = make(tmp_path, max_tokens=25, batch_size=2)
    embedder.embed(["a", "a much longer text than the limit allows"], EmbeddingTask.QUERY)
    assert session.feeds[0]["input_ids"].shape[1] == 25


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


def test_plan_calls_groups_texts_of_similar_length_and_covers_every_text_once(tmp_path):
    embedder, _, _ = make(tmp_path, batch_size=2)
    texts = ["cccccc", "a", "eeeeeeeeee", "bbb", "dddddddd"]
    groups = embedder.plan_calls(texts)
    assert groups == [["a", "bbb"], ["cccccc", "dddddddd"], ["eeeeeeeeee"]]
    assert all(embedder.plan_calls(group) == [group] for group in groups)  # a group plans to itself: one batch


def test_embed_returns_input_order_and_sorted_batches_pad_less(tmp_path):
    texts = ["x" * 40, "y", "z" * 38, "w" * 2]
    sorted_embedder, sorted_session, _ = make(tmp_path, batch_size=2)
    vectors = sorted_embedder.embed(texts, EmbeddingTask.DOCUMENT)
    expected = [sorted_embedder.embed([t], EmbeddingTask.DOCUMENT)[0] for t in texts]
    assert vectors == expected

    def padded_cells(session):
        return sum(f["attention_mask"].size for f in session.feeds[:2])

    def real_cells(session):
        return sum(int(f["attention_mask"].sum()) for f in session.feeds[:2])

    assert real_cells(sorted_session) == sum(len("title: none | text: " + t) for t in texts)
    in_input_order = 2 * (20 + 40) + 2 * (20 + 38)  # the old contiguous batches: [x40, y], [z38, w2]
    assert padded_cells(sorted_session) < in_input_order


def test_the_cache_stores_sorted_groups_and_returns_input_order(tmp_path):
    embedder, session, _ = make(tmp_path, batch_size=2)
    texts = ["long text here", "a", "medium", "bb"]
    with CachingEmbedder(embedder, tmp_path / "c.sqlite") as cache:
        result = cache.embed(texts, EmbeddingTask.DOCUMENT)
    direct = [embedder.embed([t], EmbeddingTask.DOCUMENT)[0] for t in texts]
    assert result == [pytest.approx(v, abs=1e-6) for v in direct]
    assert len(session.feeds) == 2 + len(texts)


def test_plan_sorts_by_token_count_not_characters(tmp_path):
    class WordTokenizer(FakeTokenizer):
        def encode_batch(self, texts):
            return [SimpleNamespace(ids=[1] * len(t.split())) for t in texts]

    settings = replace(get_local_embedding_settings(), cache_path=tmp_path / "c.sqlite", batch_size=1)
    embedder = EmbeddingGemmaEmbedder(settings, session=FakeSession(), tokenizer=WordTokenizer())
    assert embedder.plan_calls(["a b c", "longwordwithoutspaces"]) == [["longwordwithoutspaces"], ["a b c"]]


def test_planning_nothing_loads_no_model(tmp_path):
    settings = replace(get_local_embedding_settings(), model_dir=Path(tmp_path) / "absent")
    assert EmbeddingGemmaEmbedder(settings).plan_calls([]) == []  # all cache hits: the model is never opened
