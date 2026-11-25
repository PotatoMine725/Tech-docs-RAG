"""ONNX cross-encoder reranker (ADR-0009) with a fake tokenizer and session: sigmoid scores, ordering, passage
truncation by offsets, declared inputs only, configuration errors. No model file is needed."""
import math
from types import SimpleNamespace

import numpy as np
import pytest

from knowledge_assistant.composition import create_reranker
from knowledge_assistant.config import RerankSettings, get_rerank_model_id, get_rerank_settings
from knowledge_assistant.core.exceptions import ConfigurationError, RetrievalError
from knowledge_assistant.infrastructure.rerank.noop_reranker import NoOpReranker
from knowledge_assistant.infrastructure.rerank.onnx_cross_encoder import OnnxCrossEncoderReranker, onnx_file


class FakeTokenizer:
    """Whitespace tokens; ids = word lengths; a pair is [0] q [2 2] p [2] with type ids 0/1."""

    def no_padding(self):
        pass

    def no_truncation(self):
        pass

    def token_to_id(self, token):
        return 1 if token == "<pad>" else None

    def encode(self, text, add_special_tokens=True):
        offsets, pos = [], 0
        for word in text.split():
            start = text.index(word, pos)
            offsets.append((start, start + len(word)))
            pos = start + len(word)
        return SimpleNamespace(ids=[len(text[a:b]) for a, b in offsets], offsets=offsets)

    def encode_batch(self, pairs):
        out = []
        for query, passage in pairs:
            q, p = self.encode(query).ids, self.encode(passage).ids
            ids = [0, *q, 2, 2, *p, 2]
            out.append(SimpleNamespace(ids=ids, type_ids=[0] * (len(q) + 3) + [1] * (len(p) + 1)))
        return out


class FakeSession:
    """logit = number of non-pad tokens (longer passage = more relevant); records the feeds."""

    def __init__(self, inputs=("input_ids", "attention_mask")):
        self._inputs = inputs
        self.feeds = []

    def get_inputs(self):
        return [SimpleNamespace(name=n) for n in self._inputs]

    def run(self, outputs, feed):
        assert outputs == ["logits"]
        self.feeds.append(feed)
        return [feed["attention_mask"].sum(axis=1, keepdims=True).astype(np.float32) - 8.0]


def _reranker(max_passage_tokens=256, inputs=("input_ids", "attention_mask"), batch_size=20):
    settings = RerankSettings(model_dir=None, variant="int8", candidates=20, max_passage_tokens=max_passage_tokens,
                              batch_size=batch_size, threads=0)
    session = FakeSession(inputs)
    return OnnxCrossEncoderReranker(settings, session=session, tokenizer=FakeTokenizer()), session


def test_scores_are_sigmoid_of_logits_best_first_and_absolute():
    reranker, _ = _reranker()
    results = reranker.rerank("q", ["a", "a b c", "a b"])
    assert [r.index for r in results] == [1, 2, 0]
    length = 1 + 1 + 2 + 3 + 1  # [0] q [2 2] a b c [2]
    assert results[0].score == pytest.approx(1 / (1 + math.exp(-(length - 8))))
    assert reranker.absolute_scores and not NoOpReranker().absolute_scores
    assert [r.index for r in reranker.rerank("q", ["a", "a b c", "a b"], top_n=1)] == [1]
    assert reranker.rerank("q", []) == []


def test_ties_keep_input_order():
    reranker, _ = _reranker()
    assert [r.index for r in reranker.rerank("q", ["x y", "a b", "c d"])] == [0, 1, 2]


def test_passage_is_cut_to_the_token_limit_but_the_question_is_not():
    reranker, session = _reranker(max_passage_tokens=2)
    assert reranker.truncate("one two three four") == "one two"
    reranker.rerank("a long question here", ["one two three four"])
    assert session.feeds[0]["input_ids"].shape == (1, 1 + 4 + 2 + 2 + 1)


@pytest.mark.parametrize("question_words", [1, 5, 9])
def test_pair_never_exceeds_the_model_positions_and_the_passage_gets_what_is_left(question_words):
    settings = RerankSettings(model_dir=None, variant="int8", candidates=20, max_passage_tokens=1000, batch_size=20,
                              threads=0)
    session = FakeSession()
    reranker = OnnxCrossEncoderReranker(settings, session=session, tokenizer=FakeTokenizer(), positions=20)
    reranker.rerank(" ".join(["q"] * question_words), [" ".join(["p"] * 50)])
    width = session.feeds[0]["input_ids"].shape[1]
    assert width == 20  # question + 4 specials + (20 - question - 4) passage tokens: the passage budget shrinks


def test_long_question_is_capped(monkeypatch):
    import knowledge_assistant.infrastructure.rerank.onnx_cross_encoder as module

    monkeypatch.setattr(module, "MAX_QUERY_TOKENS", 3)
    reranker, session = _reranker(max_passage_tokens=2)
    reranker.rerank("a b c d e f", ["x y z"])
    assert session.feeds[0]["input_ids"].shape[1] == 3 + 2 + 4


def test_positions_come_from_the_export_config(tmp_path):
    from knowledge_assistant.infrastructure.rerank.onnx_cross_encoder import max_positions

    assert max_positions(tmp_path) == 512
    (tmp_path / "config.json").write_text('{"model_type": "xlm-roberta", "max_position_embeddings": 514}')
    assert max_positions(tmp_path) == 512
    (tmp_path / "config.json").write_text('{"model_type": "new", "max_position_embeddings": 8192}')
    (tmp_path / "tokenizer_config.json").write_text('{"model_max_length": 32768}')
    assert max_positions(tmp_path) == 8192
    (tmp_path / "tokenizer_config.json").write_text('{"model_max_length": 1024}')
    assert max_positions(tmp_path) == 1024


def test_only_declared_inputs_are_fed_and_padding_uses_the_pad_id():
    reranker, session = _reranker(inputs=("input_ids", "attention_mask", "token_type_ids"))
    reranker.rerank("q", ["a", "a b c"])
    feed = session.feeds[0]
    assert set(feed) == {"input_ids", "attention_mask", "token_type_ids"}
    assert feed["input_ids"][0, -1] == 1 and feed["attention_mask"][0, -1] == 0
    assert feed["token_type_ids"][1].tolist() == [0, 0, 0, 0, 1, 1, 1, 1]
    reranker, session = _reranker()
    reranker.rerank("q", ["a"])
    assert set(session.feeds[0]) == {"input_ids", "attention_mask"}


def test_batches_cover_every_passage():
    reranker, session = _reranker(batch_size=2)
    assert len(reranker.rerank("q", ["a", "b", "c", "d", "e"])) == 5
    assert len(session.feeds) == 3


def test_non_finite_logit_is_an_error():
    reranker, session = _reranker()
    session.run = lambda outputs, feed: [np.array([[np.nan]], dtype=np.float32)]
    with pytest.raises(RetrievalError, match="non-finite"):
        reranker.rerank("q", ["a"])


def test_missing_model_dir_or_file_fails_loudly(tmp_path):
    settings = RerankSettings(model_dir=None, variant="int8", candidates=20, max_passage_tokens=256, batch_size=20,
                              threads=0)
    with pytest.raises(ConfigurationError, match="RERANK_MODEL_DIR"):
        OnnxCrossEncoderReranker(settings).rerank("q", ["a"])
    with pytest.raises(ConfigurationError, match="no int8 ONNX file"):
        onnx_file(tmp_path, "int8")
    (tmp_path / "onnx").mkdir()
    (tmp_path / "onnx" / "model_quint8_avx2.onnx").write_bytes(b"")
    assert onnx_file(tmp_path, "int8").name == "model_quint8_avx2.onnx"
    (tmp_path / "onnx" / "model_int8.onnx").write_bytes(b"")
    assert onnx_file(tmp_path, "int8").name == "model_int8.onnx"


@pytest.fixture
def clean_env(monkeypatch):
    for name in ("RERANK_PROVIDER", "RERANK_MODEL_DIR", "RERANK_VARIANT", "RERANK_CANDIDATES",
                 "RERANK_MAX_PASSAGE_TOKENS", "RERANK_BATCH_SIZE", "RERANK_THREADS"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_config_defaults_and_selection(clean_env, tmp_path):
    assert isinstance(create_reranker(), NoOpReranker) and get_rerank_model_id() == "none"
    settings = get_rerank_settings()
    assert (settings.variant, settings.candidates, settings.max_passage_tokens) == ("int8", 20, 256)
    model = tmp_path / "mmarco"
    model.mkdir()
    (model / "REVISION").write_text("cross-encoder/x@1427fd652930e4ba\n", encoding="utf-8")
    clean_env.setenv("RERANK_PROVIDER", "Cross-Encoder")
    clean_env.setenv("RERANK_MODEL_DIR", str(model))
    clean_env.setenv("RERANK_VARIANT", "fp32")
    assert isinstance(create_reranker(), OnnxCrossEncoderReranker)
    assert get_rerank_model_id() == "mmarco-1427fd65-fp32-p256"


@pytest.mark.parametrize("name, value", [("RERANK_PROVIDER", "bge"), ("RERANK_VARIANT", "int4"),
                                         ("RERANK_CANDIDATES", "0"), ("RERANK_MAX_PASSAGE_TOKENS", "0")])
def test_bad_settings_fail(clean_env, name, value):
    clean_env.setenv("RERANK_PROVIDER", "cross-encoder")
    clean_env.setenv(name, value)
    with pytest.raises(ConfigurationError):
        get_rerank_model_id()
