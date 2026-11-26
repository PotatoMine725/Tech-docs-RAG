"""ONNX cross-encoder reranker (ADR-0009) with a fake tokenizer and session: sigmoid scores, ordering, sliding windows
with MaxP, the position cap, declared inputs only, configuration errors. No model file is needed."""
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


class PrefixTokenizer(FakeTokenizer):
    """A window re-tokenized inside a pair is not always the length it had in the passage alone (SentencePiece puts a
    "▁" in front of a text's first word): here a word starting with "X" is one token inside a text but two when it
    opens the text, so a window cut at such a word comes out one token longer than the count it was sized by."""

    def encode(self, text, add_special_tokens=True):
        offsets = list(super().encode(text).offsets)
        if offsets and text[offsets[0][0]] == "X" and offsets[0][1] - offsets[0][0] > 1:
            start, end = offsets[0]
            offsets[:1] = [(start, start + 1), (start + 1, end)]
        return SimpleNamespace(ids=[len(text[a:b]) for a, b in offsets], offsets=offsets)


class StickyDriftTokenizer(FakeTokenizer):
    """Every passage comes out `extra` tokens longer inside a pair, however short it is cut: no window can fit."""

    def __init__(self, extra):
        self.extra = extra

    def encode_batch(self, pairs):
        out = super().encode_batch(pairs)
        for e in out:
            e.ids[-1:-1] = [3] * self.extra
            e.type_ids += [1] * self.extra
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


class MarkerSession(FakeSession):
    """logit = 4 per 7-letter word ("PRESENT") in the pair, minus 2: only windows holding the marker score high."""

    def run(self, outputs, feed):
        self.feeds.append(feed)
        return [((feed["input_ids"] == 7).sum(axis=1, keepdims=True) * 4.0 - 2.0).astype(np.float32)]


def _settings(max_tokens=512, overlap=128, batch_size=20):
    return RerankSettings(model_dir=None, variant="int8", candidates=20, max_tokens=max_tokens, window_overlap=overlap,
                          batch_size=batch_size, threads=0)


def _reranker(max_tokens=512, overlap=128, inputs=("input_ids", "attention_mask"), batch_size=20, session=None,
              positions=None, tokenizer=None):
    session = session or FakeSession(inputs)
    reranker = OnnxCrossEncoderReranker(_settings(max_tokens, overlap, batch_size), session=session,
                                        tokenizer=tokenizer or FakeTokenizer(), positions=positions)
    return reranker, session


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


def test_windows_overlap_and_the_last_ends_at_the_text_end():
    reranker, _ = _reranker(overlap=2)
    text = "w1 w2 w3 w4 w5 w6 w7"
    assert reranker.windows(text, 4) == ["w1 w2 w3 w4", "w3 w4 w5 w6", "w5 w6 w7"]
    assert reranker.windows("w1 w2 w3 w4", 4) == ["w1 w2 w3 w4"]
    # size 3, overlap 2 -> stride 1; cut on offsets, so inner whitespace is kept
    assert reranker.windows("a  b\nc d e", 3) == ["a  b\nc", "b\nc d", "c d e"]


def test_maxp_finds_evidence_past_the_first_window():
    """The head-cut failure (2026-11-25): evidence after token 256 was invisible. With windows it scores."""
    reranker, session = _reranker(max_tokens=9, overlap=2, session=MarkerSession())  # window 9 - 1 - 4 = 4
    late = "a b c d e f g PRESENT"  # the marker is the 8th token: outside the first window
    early = "a b c d e f g h"
    results = reranker.rerank("q", [early, late])
    assert [r.index for r in results] == [1, 0]
    assert results[0].score == pytest.approx(1 / (1 + math.exp(-2.0)))  # best window: one marker
    assert reranker.windows_scored == 3 + 3
    assert sum(len(f["input_ids"]) for f in session.feeds) == 6


@pytest.mark.parametrize("question_words", [1, 5, 9])
@pytest.mark.parametrize("max_tokens, positions", [(20, 512), (1000, 20)])
def test_pairs_fill_the_smaller_of_max_tokens_and_positions_whatever_the_question(question_words, max_tokens,
                                                                                    positions):
    reranker, session = _reranker(max_tokens=max_tokens, overlap=4, positions=positions)
    reranker.rerank(" ".join(["q"] * question_words), [" ".join(["p"] * 50)])
    assert max(f["input_ids"].shape[1] for f in session.feeds) == 20  # window = 20 - question - 4 specials


def test_a_window_that_re_tokenizes_longer_is_cut_back_so_no_pair_exceeds_the_limit():
    """Windows are cut on the passage-alone tokens but the pair re-tokenizes them (boundary tokens can differ by a
    token or two): such a pair is cut back at its end, never fed longer than min(max_tokens, positions)."""
    reranker, session = _reranker(max_tokens=12, overlap=2, tokenizer=PrefixTokenizer())  # window 12 - 1 - 4 = 7
    words = ["a"] * 20
    words[5], words[10] = "Xbb", "Xcc"  # windows start at tokens 0, 5, 10, 15: two open with an "X" word
    assert len(reranker.windows(" ".join(words), 7)) == 4
    reranker.rerank("q", [" ".join(words)])
    assert max(f["input_ids"].shape[1] for f in session.feeds) <= 12
    assert sum(len(f["input_ids"]) for f in session.feeds) == 4  # all four windows are still scored


@pytest.mark.parametrize("max_tokens", [16, 20])
def test_a_long_question_leaves_room_for_the_window_at_a_small_limit(max_tokens):
    reranker, session = _reranker(max_tokens=max_tokens, overlap=0)
    reranker.rerank(" ".join(["q"] * 128), [" ".join(["p"] * 40)])
    assert max(f["input_ids"].shape[1] for f in session.feeds) <= max_tokens


def test_a_pair_that_cannot_fit_even_one_token_is_an_error_not_a_loop():
    # question 11 tokens (16 - 4 specials - 1), window 1 token, but every window re-tokenizes 2 tokens longer
    reranker, _ = _reranker(max_tokens=16, overlap=0, tokenizer=StickyDriftTokenizer(extra=2))
    with pytest.raises(RetrievalError, match="does not fit"):
        reranker.rerank(" ".join(["q"] * 128), [" ".join(["p"] * 40)])


def test_a_passage_that_fits_is_one_window():
    reranker, session = _reranker(max_tokens=20)
    reranker.rerank("q", [" ".join(["p"] * 15)])
    assert reranker.windows_scored == 1


def test_long_question_is_capped(monkeypatch):
    import knowledge_assistant.infrastructure.rerank.onnx_cross_encoder as module

    monkeypatch.setattr(module, "MAX_QUERY_TOKENS", 3)
    reranker, session = _reranker(max_tokens=9, overlap=0)
    reranker.rerank("a b c d e f", ["x y"])
    assert session.feeds[0]["input_ids"].shape[1] == 3 + 2 + 4  # question cut to 3; window 9 - 3 - 4 = 2


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
    with pytest.raises(ConfigurationError, match="RERANK_MODEL_DIR"):
        OnnxCrossEncoderReranker(_settings()).rerank("q", ["a"])
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
                 "RERANK_MAX_TOKENS", "RERANK_WINDOW_OVERLAP", "RERANK_BATCH_SIZE", "RERANK_THREADS"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_config_defaults_and_selection(clean_env, tmp_path):
    assert isinstance(create_reranker(), NoOpReranker) and get_rerank_model_id() == "none"
    settings = get_rerank_settings()
    assert (settings.variant, settings.candidates, settings.max_tokens, settings.window_overlap) == ("int8", 10, 512,
                                                                                                      128)
    model = tmp_path / "mmarco"
    model.mkdir()
    (model / "REVISION").write_text("cross-encoder/x@1427fd652930e4ba\n", encoding="utf-8")
    clean_env.setenv("RERANK_PROVIDER", "Cross-Encoder")
    clean_env.setenv("RERANK_MODEL_DIR", str(model))
    clean_env.setenv("RERANK_VARIANT", "fp32")
    assert isinstance(create_reranker(), OnnxCrossEncoderReranker)
    assert get_rerank_model_id() == "mmarco-1427fd65-fp32-t512o128"


@pytest.mark.parametrize("name, value", [("RERANK_PROVIDER", "bge"), ("RERANK_VARIANT", "int4"),
                                         ("RERANK_CANDIDATES", "0"), ("RERANK_MAX_TOKENS", "8"),
                                         ("RERANK_WINDOW_OVERLAP", "-1"), ("RERANK_WINDOW_OVERLAP", "256")])
def test_bad_settings_fail(clean_env, name, value):
    clean_env.setenv("RERANK_PROVIDER", "cross-encoder")
    clean_env.setenv(name, value)
    with pytest.raises(ConfigurationError):
        get_rerank_model_id()
