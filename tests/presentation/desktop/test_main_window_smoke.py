"""Widget smoke test: offscreen Qt, real thread-pool executor, fake port (no network)."""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from knowledge_assistant.presentation.desktop.viewmodels.ask_viewmodel import AskViewModel, ViewState  # noqa: E402
from knowledge_assistant.presentation.desktop.viewmodels.fake_ask_question import FakeAskQuestion  # noqa: E402
from knowledge_assistant.presentation.desktop.windows.main_window import MainWindow  # noqa: E402
from knowledge_assistant.presentation.desktop.workers import QtExecutor  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, until, timeout=5.0):
    end = time.time() + timeout
    while not until() and time.time() < end:
        app.processEvents()
        time.sleep(0.01)
    assert until()


def test_ask_flow_stays_responsive_and_renders(app):
    vm = AskViewModel(FakeAskQuestion(default_seconds=0.3), QtExecutor())
    win = MainWindow(vm)
    win.show()

    win.question.setText("What is dependency injection?")
    win.question.returnPressed.emit()  # Enter
    assert vm.state is ViewState.BUSY  # submit returned at once: work is off the GUI thread
    assert win.busy.isVisible() and not win.ask_button.isEnabled()

    pump(app, lambda: vm.state is not ViewState.BUSY)
    assert vm.state is ViewState.ANSWER
    assert win.citations.count() == 2 and win.copy_button.isEnabled()
    assert "Arm A" in win.answer.toPlainText() and not win.banner.isVisible()

    win.citations.setCurrentRow(0)
    assert "https://example.invalid/docs/dependency-injection-guide" in win.detail.toHtml()


def test_insufficient_and_error_look_different(app):
    vm = AskViewModel(FakeAskQuestion(default_seconds=0), QtExecutor())
    win = MainWindow(vm)
    win.show()

    win.question.setText("related topic")
    win.question.returnPressed.emit()
    pump(app, lambda: vm.state is ViewState.INSUFFICIENT)
    assert win.banner.isVisible() and "Not enough information" in win.banner.text()
    assert "related, not an answer" in win.citations.item(0).text()
    assert not win.copy_button.isEnabled()

    win.question.setText("quota")
    win.question.returnPressed.emit()
    pump(app, lambda: vm.state is ViewState.ERROR)
    assert "Quota used up" in win.banner.text()
    assert "quota" in win.answer.toPlainText() and win.citations.count() == 0

    for q, title, text in (("503 please", "Model service unavailable", "temporarily unavailable"),
                           ("noindex", "Search index not found", "index was not found")):
        win.question.setText(q)
        win.question.returnPressed.emit()
        assert vm.state is ViewState.BUSY
        pump(app, lambda: vm.state is ViewState.ERROR)
        assert win.banner.text() == title and text in win.answer.toPlainText()
