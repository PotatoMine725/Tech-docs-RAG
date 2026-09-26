"""Main window: renders AskViewModel state; holds no business logic."""
from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow,
                               QProgressBar, QPushButton, QTextBrowser, QVBoxLayout, QWidget)

from ..viewmodels.ask_viewmodel import ARMS, AskViewModel, ViewState

_BANNERS = {
    ViewState.INSUFFICIENT: ("Not enough information in the documents",
                             "background:#fff3cd;color:#664d03;border:2px solid #e0a800;padding:6px;font-weight:bold;"),
    ViewState.ERROR: ("Could not get an answer",
                      "background:#f8d7da;color:#58151c;border:2px solid #c0392b;padding:6px;font-weight:bold;"),
}


class MainWindow(QMainWindow):
    def __init__(self, vm: AskViewModel) -> None:
        super().__init__()
        self.vm = vm
        self.setWindowTitle("Knowledge Assistant")
        self.resize(820, 700)

        self.question = QLineEdit(placeholderText="Ask a question (English or Vietnamese) and press Enter")
        self.ask_button = QPushButton("Ask")
        self.arm_box = QComboBox()
        self.arm_box.addItems([f"Arm {a}" for a in ARMS])
        self.busy = QProgressBar(maximum=0, textVisible=False)  # indeterminate
        self.busy.setFixedHeight(6)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.answer = QTextBrowser()
        self.answer.setPlaceholderText("The answer appears here.")
        self.citations_label = QLabel("Citations")
        self.citations = QListWidget()
        self.detail = QTextBrowser(openExternalLinks=True)
        self.detail.setPlaceholderText("Click a citation to see the original English excerpt and source URL.")
        self.status = QLabel()
        self.copy_button = QPushButton("Copy answer")

        top = QHBoxLayout()
        top.addWidget(self.question, 1)
        top.addWidget(self.arm_box)
        top.addWidget(self.ask_button)
        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.copy_button)
        lay = QVBoxLayout()
        lay.addLayout(top)
        for w in (self.busy, self.banner, self.answer, self.citations_label, self.citations, self.detail):
            lay.addWidget(w)
        lay.addLayout(bottom)
        lay.setStretchFactor(self.answer, 3)
        lay.setStretchFactor(self.citations, 1)
        lay.setStretchFactor(self.detail, 2)
        root = QWidget()
        root.setLayout(lay)
        self.setCentralWidget(root)

        self.question.returnPressed.connect(self._send)
        self.ask_button.clicked.connect(self._send)
        self.arm_box.currentIndexChanged.connect(lambda i: vm.set_arm(ARMS[i]))
        self.citations.currentRowChanged.connect(vm.select_citation)
        self.copy_button.clicked.connect(self._copy)
        vm.subscribe(self.render)
        self.render()

    def _send(self) -> None:
        self.vm.submit(self.question.text())

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.vm.copy_text)

    def render(self) -> None:
        vm, r, st = self.vm, self.vm.result, self.vm.state
        busy = st is ViewState.BUSY
        self.busy.setVisible(busy)
        self.ask_button.setEnabled(not busy)
        self.question.setEnabled(not busy)
        self.arm_box.setEnabled(not busy)
        self.copy_button.setEnabled(vm.can_copy)
        self.status.setText(vm.status_line)

        banner = _BANNERS.get(st)
        self.banner.setVisible(banner is not None)
        if banner:
            self.banner.setText(banner[0])
            self.banner.setStyleSheet(banner[1])

        if st is ViewState.ERROR:
            self.answer.setHtml(f"<p style='color:#58151c'>{html.escape(vm.error_message)}</p>")
        elif st is ViewState.INSUFFICIENT and r:
            missing = f"<p><b>Not covered:</b> {html.escape(r.missing_information)}</p>" if r.missing_information else ""
            self.answer.setHtml(f"<p><i>{html.escape(r.answer)}</i></p>{missing}")
        elif st is ViewState.ANSWER and r:
            self.answer.setPlainText(r.answer)
        else:
            self.answer.clear()

        cites = r.citations if r and st in (ViewState.ANSWER, ViewState.INSUFFICIENT) else ()
        self.citations.blockSignals(True)
        self.citations.clear()
        for c in cites:
            tag = "   (related, not an answer)" if c.related_only else ""
            self.citations.addItem(f"[{c.marker}] {c.document_name} — {c.location}{tag}")
        self.citations.blockSignals(False)
        self.citations_label.setText(
            "Related content (not an answer)" if st is ViewState.INSUFFICIENT and cites else "Citations")
        self.citations_label.setVisible(bool(cites))
        self.citations.setVisible(bool(cites))

        sel = vm.selected
        if sel:
            note = "<p><b>Related, not an answer.</b></p>" if sel.related_only else ""
            self.detail.setHtml(
                f"{note}<p><b>{html.escape(sel.document_name)}</b> — {html.escape(sel.location)}</p>"
                f"<blockquote>{html.escape(sel.excerpt)}</blockquote>"
                f"<p>Source: <a href='{html.escape(sel.source_url)}'>{html.escape(sel.source_url)}</a></p>")
        else:
            self.detail.clear()
