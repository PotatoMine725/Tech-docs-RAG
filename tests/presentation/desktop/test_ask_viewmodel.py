"""View-model tests: synchronous executor, fake port, no Qt."""
import pytest

from knowledge_assistant.presentation.desktop.viewmodels.ask_viewmodel import AskViewModel, ViewState
from knowledge_assistant.presentation.desktop.viewmodels.fake_ask_question import FakeAskQuestion


def sync_executor(fn, on_ok, on_err):
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001
        on_err(exc)
    else:
        on_ok(result)


def make_vm(executor=sync_executor):
    return AskViewModel(FakeAskQuestion(sleep=lambda s: None), executor)


def test_starts_idle():
    assert make_vm().state is ViewState.IDLE


def test_english_answer_has_two_citations_and_status_line():
    vm = make_vm()
    vm.submit("What is dependency injection?")
    assert vm.state is ViewState.ANSWER
    assert len(vm.result.citations) == 2 and not vm.result.citations[0].related_only
    assert "1.1 s" in vm.status_line and "fake-model" in vm.status_line
    assert vm.can_copy and vm.copy_text == vm.result.answer


def test_vietnamese_question_gets_vietnamese_answer():
    vm = make_vm()
    vm.submit("Dependency injection là gì?")
    assert vm.state is ViewState.ANSWER and vm.result.language == "vi"
    assert "Nhánh A" in vm.result.answer
    assert vm.result.citations[0].excerpt.startswith("Dependency injection (DI)")  # excerpt stays English


def test_insufficient_result_gives_insufficient_state():
    vm = make_vm()
    vm.submit("insufficient topic")
    assert vm.state is ViewState.INSUFFICIENT
    assert vm.result.citations == () and vm.result.missing_information
    assert not vm.can_copy and vm.copy_text == ""


def test_insufficient_can_carry_related_only_citation_vi_and_en():
    for q, lang in (("related topic", "en"), ("related ở đâu?", "vi")):
        vm = make_vm()
        vm.submit(q)
        assert vm.state is ViewState.INSUFFICIENT and vm.result.language == lang
        assert [c.related_only for c in vm.result.citations] == [True]


@pytest.mark.parametrize("q,text", [("quota", "quota"), ("503 please", "unavailable"), ("noindex", "index")])
def test_errors_become_readable_messages(q, text):
    vm = make_vm()
    vm.submit(q)
    assert vm.state is ViewState.ERROR
    assert text in vm.error_message and "RESOURCE_EXHAUSTED" not in vm.error_message


def test_unknown_exception_is_reported_not_raised():
    class Boom:
        def ask(self, q, arm):
            raise RuntimeError("kaput")

    vm = AskViewModel(Boom(), sync_executor)
    vm.submit("x")
    assert vm.state is ViewState.ERROR and "kaput" in vm.error_message


def test_busy_until_executor_delivers_and_blank_or_double_submit_ignored():
    pending = []
    vm = make_vm(lambda fn, ok, err: pending.append((fn, ok, err)))
    vm.submit("   ")
    assert vm.state is ViewState.IDLE and not pending
    vm.submit("What is DI?")
    assert vm.state is ViewState.BUSY and vm.status_line == "Working…"
    vm.submit("second")  # ignored while busy
    assert len(pending) == 1
    fn, ok, _ = pending[0]
    ok(fn())
    assert vm.state is ViewState.ANSWER


def test_arm_is_passed_to_the_port():
    vm = make_vm()
    vm.set_arm("B")
    vm.submit("What is DI?")
    assert "Arm B" in vm.result.answer
    with pytest.raises(ValueError):
        vm.set_arm("C")


def test_select_citation_and_new_question_clears_it():
    vm = make_vm()
    vm.submit("What is DI?")
    vm.select_citation(1)
    assert vm.selected.marker == 2
    vm.select_citation(9)  # out of range: ignored
    assert vm.selected.marker == 2
    vm.submit("again")
    assert vm.selected is None


def test_listeners_notified_on_each_transition():
    vm = make_vm()
    seen = []
    vm.subscribe(lambda: seen.append(vm.state))
    vm.submit("What is DI?")
    assert seen == [ViewState.BUSY, ViewState.ANSWER]
