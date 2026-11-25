"""Notebook view-model: conversation turns, retry, recall, source viewer, source hit counts. No Qt."""
import json
from pathlib import Path

from knowledge_assistant.presentation.desktop import theme
from knowledge_assistant.presentation.desktop.viewmodels.ask_viewmodel import AskViewModel, Segment, ViewState
from knowledge_assistant.presentation.desktop.viewmodels.contracts import AnswerResult, Citation
from knowledge_assistant.presentation.desktop.viewmodels.fake_ask_question import FAKE_SOURCES, FakeAskQuestion
from knowledge_assistant.presentation.desktop.wiring import load_source_titles

ROOT = Path(__file__).resolve().parents[3]


def sync(fn, on_ok, on_err):
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001
        on_err(exc)
    else:
        on_ok(result)


def make_vm(executor=sync, sources=FAKE_SOURCES):
    return AskViewModel(FakeAskQuestion(sleep=lambda s: None), executor, sources)


class Port:
    def __init__(self, result):
        self.result = result

    def ask(self, question, arm):
        return self.result


def cite(marker, doc="Doc", related=False):
    return Citation(marker, doc, f"Part > {marker}", f"Excerpt {marker}.", f"https://example.invalid/{marker}", related)


def test_each_question_adds_a_turn_and_earlier_turns_stay():
    vm = make_vm()
    vm.submit("What is DI?")
    vm.submit("quota")
    vm.submit("insufficient topic")
    assert [t.state for t in vm.turns] == [ViewState.ANSWER, ViewState.ERROR, ViewState.INSUFFICIENT]
    assert vm.state is ViewState.INSUFFICIENT and vm.turns[0].result.citations


def test_submit_reports_whether_it_was_accepted():
    pending = []
    vm = make_vm(lambda fn, ok, err: pending.append((fn, ok, err)))
    assert vm.submit("   ") is False
    assert vm.submit("What is DI?") is True and vm.busy
    assert vm.submit("second") is False and len(vm.turns) == 1
    fn, ok, _ = pending[0]
    ok(fn())
    assert not vm.busy and vm.submit("second") is True


def test_retry_moves_the_question_to_the_end_and_asks_again():
    vm = make_vm()
    vm.submit("quota")
    vm.submit("What is DI?")
    assert vm.retry(0) is True
    assert [t.question for t in vm.turns] == ["What is DI?", "quota"] and vm.turns[-1].state is ViewState.ERROR
    assert vm.retry(9) is False and len(vm.turns) == 2


def test_retry_keeps_the_arm_it_was_asked_with_and_is_refused_while_busy():
    pending = []
    vm = make_vm(lambda fn, ok, err: pending.append((fn, ok, err)))
    vm.set_arm("B")
    vm.submit("What is DI?")
    fn, ok, _ = pending.pop()
    ok(fn())
    vm.set_arm("A")
    vm.submit("Another?")
    assert vm.retry(0) is False  # busy
    fn, ok, _ = pending.pop()
    ok(fn())
    vm.retry(0)
    fn, ok, _ = pending.pop()
    ok(fn())
    assert vm.turns[-1].arm == "B" and "Arm B" in vm.turns[-1].result.answer


def test_last_question_is_kept_for_recall():
    vm = make_vm()
    vm.submit("  What is DI?  ")
    assert vm.last_question == "What is DI?"


def test_viewer_opens_steps_and_closes():
    vm = make_vm()
    vm.submit("What is DI?")
    assert vm.selected is None and vm.viewer_position == ""
    assert vm.open_citation(0, 2) is True
    assert vm.selected.marker == 2 and vm.viewer_position == "2 of 2" and vm.viewer_turn == 0
    assert vm.can_step_back and not vm.can_step_forward
    vm.step_citation(1)  # past the end: stays
    assert vm.selected.marker == 2
    vm.step_citation(-1)
    assert vm.selected.marker == 1 and not vm.can_step_back
    vm.close_viewer()
    assert vm.selected is None and vm.viewer_turn is None


def test_viewer_refuses_unknown_markers_and_closes_on_a_new_question():
    vm = make_vm()
    vm.submit("What is DI?")
    assert vm.open_citation(0, 7) is False and vm.open_citation(5, 1) is False
    vm.open_citation(0, 1)
    vm.submit("again")
    assert vm.selected is None


def test_viewer_can_open_an_earlier_turns_citation():
    vm = make_vm()
    vm.submit("What is DI?")
    vm.submit("quota")
    assert vm.open_citation(0, 1) and vm.selected.document_name == "Dependency Injection Guide"


def test_hit_counts_come_from_the_newest_cited_answer():
    vm = make_vm()
    assert vm.hit_counts == {}
    vm.submit("What is DI?")
    assert vm.hit_counts == {"Dependency Injection Guide": 2}
    vm.submit("quota")  # an error cites nothing: the counts still describe the last cited answer
    assert vm.hit_counts == {"Dependency Injection Guide": 2}
    vm.submit("related topic")
    assert vm.hit_counts == {"ASP.NET Core Middleware": 1}


def test_open_source_opens_its_first_citation_or_reports_none():
    vm = make_vm()
    assert vm.open_source("Dependency Injection Guide") is False
    vm.submit("What is DI?")
    assert vm.open_source("ASP.NET Core Middleware") is False and vm.selected is None
    assert vm.open_source("Dependency Injection Guide") is True and vm.selected.marker == 1


def test_scope_and_busy_text_follow_the_source_count():
    assert make_vm().scope_hint == "Searching all 2 sources"
    assert make_vm(sources=("One",)).scope_hint == "Searching 1 source"
    assert make_vm(sources=()).scope_hint == "" and make_vm(sources=()).busy_text == "Working…"
    assert make_vm(sources=("a", "b", "c")).busy_text == "Answering from 3 sources…"


def test_segments_turn_only_known_markers_into_chips():
    result = AnswerResult("q", "en", "A [1]. B [3][2]. Code a[0] stays.", False, citations=(cite(1), cite(2)))
    vm = AskViewModel(Port(result), sync)
    vm.submit("q")
    assert vm.segments(vm.turns[0]) == [
        Segment("A "), Segment("[1]", 1), Segment(". B [3]"), Segment("[2]", 2), Segment(". Code a[0] stays."),
    ]


def test_segments_are_empty_for_anything_but_an_answer():
    vm = make_vm()
    vm.submit("related topic")
    vm.submit("quota")
    assert vm.segments(vm.turns[0]) == [] and vm.segments(vm.turns[1]) == []


def test_copy_text_for_lists_the_sources_under_a_real_answer_only():
    vm = make_vm()
    vm.submit("What is DI?")
    vm.submit("insufficient topic")
    text = vm.copy_text_for(0)
    assert text.startswith(vm.turns[0].result.answer)
    assert text.endswith("Sources:\n[1] Dependency Injection Guide — Overview > What is DI\n"
                         "[2] Dependency Injection Guide — Usage > Registering services")
    assert vm.copy_text_for(1) == "" and vm.copy_text_for(7) == ""


def test_source_titles_are_the_document_names_citations_carry():
    titles = load_source_titles("corpus/manifest.json")  # corpus 1, whatever CORPUS_MANIFEST says
    names = {json.loads(line)["document_name"]
             for line in (ROOT / "data/processed/chunks/arm-a.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()}
    assert len(titles) == 24 and set(titles) == names
    assert list(titles) == sorted(titles, key=str.casefold)


def test_missing_manifest_gives_no_sources(tmp_path):
    assert load_source_titles(str(tmp_path / "nope.json")) == ()


def test_theme_has_the_same_tokens_in_both_schemes_and_a_stylesheet_for_each():
    assert theme.LIGHT.keys() == theme.DARK.keys()
    assert theme.LIGHT["warning-bg"] == "#fff3cd" and theme.LIGHT["danger-line"] == "#c0392b"  # the app's own
    for c in (theme.LIGHT, theme.DARK):
        qss = theme.stylesheet(c)
        assert c["accent"] in qss and qss.count("{") == qss.count("}")
    assert '"' not in theme.css_families(theme.SANS)  # it goes inside style="..." attributes of the thread HTML
