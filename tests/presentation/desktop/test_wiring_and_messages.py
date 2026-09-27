"""GUI-001: wiring facts (shared LLM, fallback on, lazy) and backlog N2 (insufficient text comes from messages.json)."""
import json
from pathlib import Path

from knowledge_assistant.presentation.desktop import wiring
from knowledge_assistant.presentation.desktop.viewmodels.fake_ask_question import FakeAskQuestion

ROOT = Path(__file__).resolve().parents[3]


def test_fake_insufficient_messages_are_the_ones_in_config_messages_json():
    expected = json.loads((ROOT / "config" / "messages.json").read_text(encoding="utf-8"))["insufficient"]
    fake = FakeAskQuestion(sleep=lambda s: None)
    assert fake.ask("insufficient topic", "A").answer == expected["en"]
    assert fake.ask("chủ đề insufficient", "A").answer == expected["vi"]


def test_fake_takes_its_messages_from_the_argument_when_given():
    fake = FakeAskQuestion(sleep=lambda s: None, messages={"en": "EN-X", "vi": "VI-X"})
    assert fake.ask("insufficient", "A").answer == "EN-X"


def test_the_fake_module_has_no_hard_coded_insufficient_sentence():
    text = (ROOT / "src/knowledge_assistant/presentation/desktop/viewmodels/fake_ask_question.py").read_text(encoding="utf-8")
    assert "does not contain enough information" not in text and "không chứa đủ thông tin" not in text


def test_real_port_shares_one_llm_forces_fallback_and_builds_lazily(monkeypatch):
    monkeypatch.setenv("ALLOW_FALLBACK", "false")
    made, built = [], []

    class SpyLLM:
        def __init__(self, settings):
            self.settings = settings
            made.append(self)

    monkeypatch.setattr(wiring, "GeminiLLM", SpyLLM)
    monkeypatch.setattr(wiring, "build_answer_service", lambda arm, llm, embedder: built.append((arm, llm)) or object())
    port = wiring.build_real_port()
    assert len(made) == 1 and made[0].settings.allow_fallback is True and built == []
    port._service("A")
    port._service("B")
    assert [a for a, _ in built] == ["A", "B"] and all(llm is made[0] for _, llm in built)


def test_fake_fallback_scenario_shows_the_fallback_marker_in_the_status_line():
    from knowledge_assistant.presentation.desktop.viewmodels.ask_viewmodel import AskViewModel

    vm = AskViewModel(FakeAskQuestion(sleep=lambda s: None), lambda fn, ok, err: ok(fn()))
    vm.submit("what is dependency injection, fallback please")
    assert vm.status_line.endswith("model: fake-fallback-model (fallback)")
    vm.submit("what is dependency injection")
    assert vm.status_line.endswith("model: fake-model")
