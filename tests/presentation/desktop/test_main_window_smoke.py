"""Widget smoke test: offscreen Qt, real thread-pool executor, fake port (no network)."""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from knowledge_assistant.presentation.desktop.viewmodels.ask_viewmodel import AskViewModel, ViewState  # noqa: E402
from knowledge_assistant.presentation.desktop.viewmodels.fake_ask_question import (  # noqa: E402
    FAKE_SOURCES,
    FakeAskQuestion,
)
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


def make(seconds=0.0):
    vm = AskViewModel(FakeAskQuestion(default_seconds=seconds), QtExecutor(), FAKE_SOURCES)
    win = MainWindow(vm)
    win.show()
    return vm, win


def ask(win, text):
    win.composer.setPlainText(text)
    QTest.keyClick(win.composer, Qt.Key.Key_Return)


def test_ask_flow_stays_responsive_and_renders(app):
    vm, win = make(0.3)
    assert not win.viewer.isVisible() and win.source_list.count() == 2
    assert "Searching all 2 sources" in win.hint.text()

    ask(win, "What is dependency injection?")  # Enter sends
    assert vm.state is ViewState.BUSY  # submit returned at once: work is off the GUI thread
    assert win.busy.isVisible() and not win.send_button.isEnabled()
    assert win.composer.isEnabled() and win.composer.toPlainText() == ""  # sent, and the field stays usable

    win.composer.setPlainText("draft of the next question")
    QTest.keyClick(win.composer, Qt.Key.Key_Return)  # refused while busy: the draft survives
    assert win.composer.toPlainText() == "draft of the next question" and len(vm.turns) == 1

    pump(app, lambda: vm.state is not ViewState.BUSY)
    assert vm.state is ViewState.ANSWER and not win.busy.isVisible()
    html = win.thread_html()
    assert "Arm A" in win.thread.toPlainText()
    # each citation: the chip in the answer, plus a chip and the document name in the Sources row
    assert html.count('href="cite:0:1"') == 3 and html.count('href="cite:0:2"') == 3
    assert 'href="copy:0"' in html and 'href="retry:0"' in html
    assert "Dependency Injection Guide  ·  2 cited" in [win.source_list.item(i).text() for i in range(2)]

    win.thread.anchorClicked.emit(QUrl("cite:0:2"))  # a chip click opens the viewer
    assert win.viewer.isVisible() and win.viewer_pos.text() == "2 of 2"
    assert "https://example.invalid/docs/dependency-injection-guide" in win.viewer_source.text()
    assert "Register services" in win.detail.toPlainText() and not win.viewer_related.isVisible()
    win.viewer_prev.click()
    assert win.viewer_pos.text() == "1 of 2" and not win.viewer_prev.isEnabled()
    QTest.keyClick(win, Qt.Key.Key_Escape)
    assert not win.viewer.isVisible()

    win.thread.anchorClicked.emit(QUrl("copy:0"))
    assert QGuiApplication.clipboard().text().startswith(vm.result.answer)
    assert "Sources:" in QGuiApplication.clipboard().text()


def test_shift_enter_adds_a_line_and_up_recalls(app):
    vm, win = make()
    win.composer.setPlainText("first line")
    win.composer.moveCursor(win.composer.textCursor().MoveOperation.End)
    QTest.keyClick(win.composer, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    assert win.composer.toPlainText() == "first line\n" and not vm.turns
    QTest.keyClick(win.composer, Qt.Key.Key_Return)
    pump(app, lambda: vm.state is ViewState.ANSWER)
    assert win.composer.toPlainText() == ""
    QTest.keyClick(win.composer, Qt.Key.Key_Up)
    assert win.composer.toPlainText() == "first line"


def test_insufficient_and_error_look_different(app):
    vm, win = make()

    ask(win, "related topic")
    pump(app, lambda: vm.state is ViewState.INSUFFICIENT)
    html = win.thread_html()
    assert "Not enough information in the documents" in html and "related, not an answer" in html
    assert 'href="copy:0"' not in html and 'href="retry:0"' in html
    win.thread.anchorClicked.emit(QUrl("cite:0:1"))
    assert win.viewer.isVisible() and win.viewer_related.isVisible()

    ask(win, "quota")
    pump(app, lambda: vm.state is ViewState.ERROR)
    assert not win.viewer.isVisible()  # a new question closes the viewer
    html = win.thread_html()
    assert "Quota used up" in html and "quota is used up" in html and 'href="copy:1"' not in html

    for i, (q, title, text) in enumerate((("503 please", "Model service unavailable", "temporarily unavailable"),
                                          ("noindex", "Search index not found", "index was not found")), start=2):
        ask(win, q)
        assert vm.state is ViewState.BUSY
        pump(app, lambda: vm.state is ViewState.ERROR)
        assert vm.error_title == title and title in win.thread_html() and text in win.thread.toPlainText()

    assert len(vm.turns) == 4  # earlier questions stay in the conversation
    win.thread.anchorClicked.emit(QUrl("retry:1"))  # Retry re-asks without retyping
    assert vm.state is ViewState.BUSY and vm.turns[-1].question == "quota" and len(vm.turns) == 4
    pump(app, lambda: vm.state is ViewState.ERROR)


def test_source_click_opens_the_cited_section_and_filter_hides_rows(app):
    vm, win = make()
    ask(win, "What is DI?")
    pump(app, lambda: vm.state is ViewState.ANSWER)
    rows = {win.source_list.item(i).data(Qt.ItemDataRole.UserRole): win.source_list.item(i) for i in range(2)}
    win.source_list.itemClicked.emit(rows["Dependency Injection Guide"])
    assert win.viewer.isVisible() and win.viewer_pos.text() == "1 of 2"
    win.source_list.itemClicked.emit(rows["ASP.NET Core Middleware"])  # not cited: says so, viewer unchanged
    assert win.viewer_pos.text() == "1 of 2"
    win.source_filter.setText("middle")
    assert rows["Dependency Injection Guide"].isHidden() and not rows["ASP.NET Core Middleware"].isHidden()


def test_arm_is_chosen_in_the_settings_menu(app):
    vm, win = make()
    win.arm_actions[1].trigger()
    assert vm.arm == "B"
    ask(win, "What is DI?")
    pump(app, lambda: vm.state is ViewState.ANSWER)
    assert "Arm B" in win.thread.toPlainText()
