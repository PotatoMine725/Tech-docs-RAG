"""Main window: a three-pane notebook (sources | conversation | source viewer). Renders AskViewModel; no logic.

Fewer actions: the composer has focus and sends on Enter; citations are chips in the answer that show the excerpt
on hover and open the source viewer on click; Copy and Retry sit on each answer; Ctrl+K focuses the composer and
Esc closes the viewer. The arm choice lives in the Settings menu.
"""
from __future__ import annotations

import html

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import (QAction, QActionGroup, QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QKeySequence,
                           QShortcut)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QSplitter, QStyle, QStyledItemDelegate,
                               QStyleOptionViewItem, QTextBrowser, QToolTip,
                               QVBoxLayout, QWidget)

from .. import theme
from ..viewmodels.ask_viewmodel import ARMS, AskViewModel, Turn, ViewState

_INSUFFICIENT_TITLE = "Not enough information in the documents"
HIT_ROLE = Qt.ItemDataRole.UserRole + 1  # source list: how many citations of the latest cited answer name the row


class SourceItemDelegate(QStyledItemDelegate):
    """Paints a source row as its name, elided, plus a right-aligned "N cited" badge that is never elided away."""

    PAD = 6

    def __init__(self, colors) -> None:
        super().__init__()
        self._colors = colors  # callable -> the window's current colour tokens

    def paint(self, painter, option, index) -> None:  # noqa: D102 - Qt override
        hits = index.data(HIT_ROLE) or 0
        if not hits:
            super().paint(painter, option, index)
            return
        badge = f"{hits} cited"
        metrics = QFontMetrics(option.font)
        badge_w = metrics.horizontalAdvance(badge) + 2 * self.PAD
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else None
        if style:  # background, selection and hover, without text
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        rect = option.rect.adjusted(self.PAD, 0, -self.PAD, 0)
        text_rect = (style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget) if style
                     else rect)  # where an unbadged row puts its name, so every name starts at the same x
        name_rect = text_rect.adjusted(0, 0, -(text_rect.right() - rect.right()) - badge_w - self.PAD, 0)
        badge_rect = rect.adjusted(rect.width() - badge_w, 3, 0, -3)
        c = self._colors()
        painter.save()
        painter.setPen(QColor(c["ink"]))
        name = metrics.elidedText(index.data(Qt.ItemDataRole.UserRole), Qt.TextElideMode.ElideRight, name_rect.width())
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(c["accent-soft"]))
        painter.drawRoundedRect(badge_rect, 3, 3)
        painter.setPen(QColor(c["accent"]))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge)
        painter.restore()


def _font(families: list[str], point: float | None = None, weight: QFont.Weight | None = None) -> QFont:
    f = QFont()
    f.setFamilies(families)
    if point:
        f.setPointSizeF(point)
    if weight is not None:
        f.setWeight(weight)
    return f


class Composer(QPlainTextEdit):
    """The question field: Enter sends, Shift+Enter adds a line, Up in an empty field recalls the last question."""

    submitted = Signal()
    recall = Signal()

    MAX_LINES = 6

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("composer")
        self.setPlaceholderText("Ask about your sources, in English or Vietnamese")
        self.setTabChangesFocus(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.textChanged.connect(self._fit)
        self._fit()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        key, mods = event.key(), event.modifiers()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not mods & Qt.KeyboardModifier.ShiftModifier:
            self.submitted.emit()
            return
        if key == Qt.Key.Key_Up and not self.toPlainText():
            self.recall.emit()
            return
        super().keyPressEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().changeEvent(event)
        if event.type() == event.Type.FontChange:  # the window's font arrives after construction: refit
            self._fit()

    def _fit(self) -> None:
        line = self.fontMetrics().lineSpacing()
        # QPlainTextEdit's document layout measures its height in lines, not pixels
        lines = max(1, min(self.MAX_LINES, int(self.document().size().height())))
        self.setFixedHeight(lines * line + 12)


class MainWindow(QMainWindow):
    def __init__(self, vm: AskViewModel, title: str = "Knowledge Assistant") -> None:
        super().__init__()
        self.vm = vm
        self.setWindowTitle(title)
        self.resize(*theme.WINDOW_SIZE)
        self.setFont(_font(theme.SANS, 10.5))

        self._build_menu()
        self._build_sources()
        self._build_conversation()
        self._build_viewer()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(True)
        for w in (self.sources_panel, self.center, self.viewer):
            self.splitter.addWidget(w)
        self.splitter.setCollapsible(1, False)
        self.splitter.setStretchFactor(1, 1)
        rest = theme.WINDOW_SIZE[0] - theme.SIDEBAR_WIDTH - theme.VIEWER_WIDTH
        self.splitter.setSizes([theme.SIDEBAR_WIDTH, rest, theme.VIEWER_WIDTH])
        self._viewer_width = theme.VIEWER_WIDTH
        root = QWidget(objectName="root")
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.splitter)
        self.setCentralWidget(root)
        self.statusBar().setSizeGripEnabled(False)

        QShortcut(QKeySequence("Ctrl+K"), self, self.composer.setFocus)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, vm.close_viewer)

        self._dark = None
        self._apply_theme()
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda *_: self._apply_theme())

        vm.subscribe(self.render)
        self.render()
        self.composer.setFocus()

    # ---- building -------------------------------------------------------
    def _build_menu(self) -> None:
        settings = self.menuBar().addMenu("Settings")
        arm_menu = settings.addMenu("Indexing arm")
        group = QActionGroup(self)
        self.arm_actions: list[QAction] = []
        for arm in ARMS:
            action = QAction(f"Arm {arm}", self, checkable=True)
            action.setChecked(arm == self.vm.arm)
            action.triggered.connect(lambda _=False, a=arm: self.vm.set_arm(a))
            group.addAction(action)
            arm_menu.addAction(action)
            self.arm_actions.append(action)

    def _build_sources(self) -> None:
        self.sources_panel = QWidget(objectName="sources")
        self.sources_panel.setMinimumWidth(180)
        head = QHBoxLayout()
        head.addWidget(QLabel("SOURCES", objectName="paneLabel"))
        head.addStretch(1)
        self.source_count = QLabel(objectName="count")
        self.source_count.setFont(_font(theme.MONO, 9))
        head.addWidget(self.source_count)
        self.source_filter = QLineEdit(objectName="filter", placeholderText="Filter sources")
        self.source_filter.setClearButtonEnabled(True)
        self.source_filter.textChanged.connect(self._filter_sources)
        self.source_list = QListWidget(objectName="sourceList")
        self.source_list.setTextElideMode(Qt.TextElideMode.ElideRight)  # one line each; the full name on hover
        self.source_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.source_list.setItemDelegate(SourceItemDelegate(lambda: self.c))
        self.source_list.itemClicked.connect(self._source_clicked)
        lay = QVBoxLayout(self.sources_panel)
        lay.setContentsMargins(12, 12, 8, 12)
        lay.setSpacing(8)
        lay.addLayout(head)
        lay.addWidget(self.source_filter)
        lay.addWidget(self.source_list, 1)

    def _build_conversation(self) -> None:
        self.center = QWidget()
        self.thread = QTextBrowser(objectName="thread")
        self.thread.setOpenLinks(False)
        self.thread.setOpenExternalLinks(False)
        self.thread.anchorClicked.connect(self._anchor_clicked)
        self.thread.highlighted.connect(self._anchor_hovered)
        self.thread.document().setDocumentMargin(24)

        self.busy = QProgressBar(objectName="busy", maximum=0, textVisible=False)  # indeterminate
        self.busy.setFixedHeight(6)

        self.composer = Composer()
        self.composer.submitted.connect(self._send)
        self.composer.recall.connect(self._recall)
        self.composer.textChanged.connect(self._update_send)
        self.send_button = QPushButton("Send", objectName="send")
        self.send_button.clicked.connect(self._send)
        box = QFrame(objectName="composeBox")
        row = QHBoxLayout(box)
        row.setContentsMargins(12, 6, 6, 6)
        row.addWidget(self.composer, 1)
        row.addWidget(self.send_button, 0, Qt.AlignmentFlag.AlignBottom)
        self.hint = QLabel(objectName="hint")
        self.hint.setFont(_font(theme.MONO, 8.5))
        # the one-line shortcut hint is clipped when narrow; left at its natural width it set the conversation's
        # minimum (~750 px) and the splitter squeezed the source list and the viewer to their minimums instead
        self.hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        bottom = QVBoxLayout()
        bottom.setContentsMargins(24, 8, 24, 12)
        bottom.setSpacing(6)
        bottom.addWidget(self.busy)
        bottom.addWidget(box)
        bottom.addWidget(self.hint)
        lay = QVBoxLayout(self.center)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.thread, 1)
        lay.addLayout(bottom)

    def _build_viewer(self) -> None:
        self.viewer = QFrame(objectName="viewer")
        self.viewer.setMinimumWidth(260)
        self.viewer_doc = QLabel(objectName="viewerDoc", wordWrap=True)
        self.viewer_close = QPushButton("Close", objectName="textButton")
        self.viewer_close.clicked.connect(self.vm.close_viewer)
        head = QHBoxLayout()
        head.addWidget(self.viewer_doc, 1)
        head.addWidget(self.viewer_close, 0, Qt.AlignmentFlag.AlignTop)
        self.viewer_path = QLabel(objectName="viewerPath", wordWrap=True)
        self.viewer_path.setFont(_font(theme.MONO, 9.5))
        self.viewer_prev = QPushButton("Previous", objectName="textButton")
        self.viewer_next = QPushButton("Next", objectName="textButton")
        self.viewer_pos = QLabel(objectName="viewerPos")
        self.viewer_pos.setFont(_font(theme.MONO, 9))
        self.viewer_prev.clicked.connect(lambda: self.vm.step_citation(-1))
        self.viewer_next.clicked.connect(lambda: self.vm.step_citation(1))
        nav = QHBoxLayout()
        nav.addWidget(self.viewer_prev)
        nav.addWidget(self.viewer_pos)
        nav.addWidget(self.viewer_next)
        nav.addStretch(1)
        self.viewer_related = QLabel("Related, not an answer.", objectName="viewerRelated")
        self.detail = QTextBrowser(objectName="excerpt")
        self.detail.setFont(_font(theme.SERIF, 11))
        self.detail.setOpenLinks(False)  # escaped excerpt text only: nothing in it is a link
        self.viewer_source = QLabel(objectName="viewerSource", wordWrap=True, openExternalLinks=True)
        self.viewer_source.setTextFormat(Qt.TextFormat.RichText)
        lay = QVBoxLayout(self.viewer)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)
        lay.addLayout(head)
        lay.addWidget(self.viewer_path)
        lay.addLayout(nav)
        lay.addWidget(self.viewer_related)
        lay.addWidget(self.detail, 1)
        lay.addWidget(self.viewer_source)

    # ---- theme ----------------------------------------------------------
    def _is_dark(self) -> bool:
        hints = QGuiApplication.styleHints()
        return hasattr(hints, "colorScheme") and hints.colorScheme() == Qt.ColorScheme.Dark

    def _apply_theme(self) -> None:
        dark = self._is_dark()
        if dark == self._dark:
            return
        self._dark = dark
        self.c = theme.colors(dark)
        self.setStyleSheet(theme.stylesheet(self.c))
        if hasattr(self, "vm"):
            self.render()

    # ---- events ---------------------------------------------------------
    def _send(self) -> None:
        if self.vm.submit(self.composer.toPlainText()):
            self.composer.clear()

    def _recall(self) -> None:
        if self.vm.last_question:
            self.composer.setPlainText(self.vm.last_question)
            self.composer.moveCursor(self.composer.textCursor().MoveOperation.End)

    def _update_send(self) -> None:
        self.send_button.setEnabled(self.vm.can_submit(self.composer.toPlainText()))

    def _anchor_clicked(self, url: QUrl) -> None:
        kind, _, rest = url.toString().partition(":")
        parts = rest.split(":")
        if kind == "cite" and len(parts) == 2:
            self.vm.open_citation(int(parts[0]), int(parts[1]))
        elif kind == "copy":
            QGuiApplication.clipboard().setText(self.vm.copy_text_for(int(parts[0])))
            self.statusBar().showMessage("Answer and sources copied", 2500)
        elif kind == "retry":
            self.vm.retry(int(parts[0]))

    def _anchor_hovered(self, url: QUrl) -> None:
        kind, _, rest = url.toString().partition(":")
        parts = rest.split(":")
        if kind != "cite" or len(parts) != 2:
            QToolTip.hideText()
            return
        t, m = int(parts[0]), int(parts[1])
        for c in self.vm.turns[t].citations:
            if c.marker == m:
                QToolTip.showText(QCursor.pos(), self._tooltip(c), self.thread)
                return

    def _source_clicked(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        if not self.vm.open_source(name):
            self.statusBar().showMessage("Not cited in the latest answer", 2500)

    def _filter_sources(self, text: str) -> None:
        needle = text.casefold().strip()
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            item.setHidden(bool(needle) and needle not in item.data(Qt.ItemDataRole.UserRole).casefold())

    # ---- rendering ------------------------------------------------------
    def render(self) -> None:
        vm = self.vm
        busy = vm.busy
        self.busy.setVisible(busy)
        self._update_send()
        self.hint.setText("   ·   ".join(p for p in (vm.scope_hint, "Enter send", "Shift+Enter new line",
                                                      "Ctrl+K focus") if p))
        self._render_sources()
        self._render_thread()
        self._render_viewer()

    def _render_sources(self) -> None:
        vm = self.vm
        self.source_count.setText(str(len(vm.sources)))
        hits = vm.hit_counts
        current = vm.selected.document_name if vm.selected else None
        lst = self.source_list
        lst.blockSignals(True)
        if lst.count() != len(vm.sources):
            lst.clear()
            for name in vm.sources:
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, name)
                item.setToolTip(name)
                lst.addItem(item)
            self._filter_sources(self.source_filter.text())
        lst.clearSelection()
        for i in range(lst.count()):
            item = lst.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            n = hits.get(name, 0)
            item.setData(HIT_ROLE, n)  # the delegate paints it as a badge the name's elision cannot hide
            label = f"{name} · {n} cited" if n else name
            item.setToolTip(label)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, label)  # screen readers hear the count the badge shows
            item.setSelected(name == current)
        lst.blockSignals(False)

    def _render_thread(self) -> None:
        sb = self.thread.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 4
        old = sb.value()
        self.thread.setHtml(self.thread_html())
        sb.setValue(sb.maximum() if at_bottom else old)

    def thread_html(self) -> str:
        c, vm = self.c, self.vm
        sans, mono = theme.css_families(theme.SANS), theme.css_families(theme.MONO)
        body = [f"<body style=\"font-family:{sans}; color:{c['ink']};\">"]
        if not vm.turns:
            body.append(f"<p style=\"color:{c['ink-muted']}; margin-top:48px;\" align=\"center\">"
                        "Ask a question about your sources. Answers cite the heading they came from.</p>")
        for i, turn in enumerate(vm.turns):
            body.append(self._question_html(turn))
            body.append(self._answer_html(i, turn, mono))
        body.append("</body>")
        return "".join(body)

    def _question_html(self, turn: Turn) -> str:
        c = self.c
        return (f"<table width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"margin-top:20px;\"><tr>"
                f"<td width=\"20%\"></td><td align=\"right\"><table cellpadding=\"8\" cellspacing=\"0\" "
                f"style=\"background-color:{c['surface-sunken']};\"><tr><td>{self._text(turn.question)}</td></tr>"
                f"</table></td></tr></table>")

    def _banner(self, title: str, bg: str, ink: str, line: str) -> str:
        return (f"<table width=\"100%\" cellspacing=\"0\" cellpadding=\"6\" style=\"margin-top:10px; "
                f"background-color:{bg}; border:2px solid {line}; border-style:solid; border-color:{line};\">"
                f"<tr><td style=\"color:{ink}; font-weight:700;\">{html.escape(title)}</td></tr></table>")

    def _chip(self, i: int, marker: int, open_: bool, mono: str) -> str:
        c = self.c
        bg, fg = (c["accent"], c["on-accent"]) if open_ else (c["accent-soft"], c["accent"])
        return (f"<a href=\"cite:{i}:{marker}\" style=\"text-decoration:none; font-family:{mono}; font-weight:600; "
                f"font-size:9pt; background-color:{bg}; color:{fg};\">&nbsp;{marker}&nbsp;</a>")

    def _answer_html(self, i: int, turn: Turn, mono: str) -> str:
        c, vm = self.c, self.vm
        out = ["<div style=\"margin-top:10px;\">"]
        open_marker = vm.selected.marker if vm.selected and vm.viewer_turn == i else None
        if turn.state is ViewState.BUSY:
            out.append(f"<p style=\"color:{c['ink-muted']};\"><i>{html.escape(vm.busy_text)}</i></p>")
        elif turn.state is ViewState.ERROR:
            out.append(self._banner(turn.error_title, c["danger-bg"], c["danger-ink"], c["danger-line"]))
            out.append(f"<p style=\"color:{c['danger-ink']};\">{self._text(turn.error_message)}</p>")
            out.append(self._meta(i, "", copy=False, mono=mono))
        elif turn.state is ViewState.INSUFFICIENT and turn.result:
            r = turn.result
            out.append(self._banner(_INSUFFICIENT_TITLE, c["warning-bg"], c["warning-ink"], c["warning-line"]))
            out.append(f"<p><i>{self._text(r.answer)}</i></p>")
            if r.missing_information:
                out.append(f"<p><b>Not covered:</b> {self._text(r.missing_information)}</p>")
            out.append(self._sources_row(i, turn, open_marker, mono))
            out.append(self._meta(i, vm.status_for(turn), copy=False, mono=mono))
        elif turn.state is ViewState.ANSWER and turn.result:
            parts = []
            for seg in vm.segments(turn):
                if seg.marker is None:
                    parts.append(self._text(seg.text))
                else:
                    parts.append(self._chip(i, seg.marker, seg.marker == open_marker, mono))
            out.append(f"<p style=\"line-height:150%;\">{''.join(parts)}</p>")
            out.append(self._sources_row(i, turn, open_marker, mono))
            out.append(self._meta(i, vm.status_for(turn), copy=True, mono=mono))
        out.append("</div>")
        return "".join(out)

    def _sources_row(self, i: int, turn: Turn, open_marker: int | None, mono: str) -> str:
        c = self.c
        if not turn.citations:
            return ""
        rows = []
        for cit in turn.citations:
            tag = (f" <span style=\"color:{c['ink-muted']};\">&nbsp;related, not an answer</span>"
                   if cit.related_only else "")
            rows.append(f"<div style=\"margin-top:3px;\">{self._chip(i, cit.marker, cit.marker == open_marker, mono)}"
                        f"&nbsp;<a href=\"cite:{i}:{cit.marker}\" style=\"text-decoration:none; color:{c['ink']};\">"
                        f"{html.escape(cit.document_name)}</a>&nbsp;&nbsp;<span style=\"font-family:{mono}; "
                        f"font-size:9pt; color:{c['ink-muted']};\">{html.escape(cit.location)}</span>{tag}</div>")
        return f"<div style=\"margin-top:8px;\">{''.join(rows)}</div>"

    def _meta(self, i: int, status: str, copy: bool, mono: str) -> str:
        c = self.c
        link = f"text-decoration:none; color:{c['accent']}; font-weight:600;"
        actions = []
        if copy:
            actions.append(f"<a href=\"copy:{i}\" style=\"{link}\">Copy</a>")
        actions.append(f"<a href=\"retry:{i}\" style=\"{link}\">Retry</a>")
        status_html = (f"<span style=\"font-family:{mono}; font-size:8.5pt; color:{c['ink-muted']};\">"
                       f"{html.escape(status)}</span>&nbsp;&nbsp;&nbsp;" if status else "")
        return f"<p style=\"margin-top:8px;\">{status_html}{'&nbsp;&nbsp;&nbsp;'.join(actions)}</p>"

    @staticmethod
    def _text(text: str) -> str:
        return html.escape(text).replace("\n", "<br>")

    def _tooltip(self, cit) -> str:
        c = self.c
        serif, mono = theme.css_families(theme.SERIF), theme.css_families(theme.MONO)
        excerpt = cit.excerpt if len(cit.excerpt) <= 320 else cit.excerpt[:317].rstrip() + "…"
        return (f"<div style=\"max-width:360px;\"><b>{html.escape(cit.document_name)}</b><br>"
                f"<span style=\"font-family:{mono}; color:{c['ink-muted']};\">{html.escape(cit.location)}</span>"
                f"<p style=\"font-family:{serif};\">{html.escape(excerpt)}</p></div>")

    def _render_viewer(self) -> None:
        vm, c = self.vm, self.c
        sel = vm.selected
        opening = sel is not None and self.viewer.isHidden()
        if sel is None and self.viewer.isVisible() and self.splitter.sizes()[2]:
            self._viewer_width = self.splitter.sizes()[2]  # closing: keep a width the user dragged
        before = self.splitter.sizes()  # showing the viewer redistributes every pane: keep what was there
        self.viewer.setVisible(sel is not None)
        if opening:
            self._fit_viewer(before[0], before[1])
        if sel is None:
            self.detail.clear()
            return
        self.viewer_doc.setText(sel.document_name)
        self.viewer_path.setText(sel.location)
        self.viewer_pos.setText(vm.viewer_position)
        self.viewer_prev.setEnabled(vm.can_step_back)
        self.viewer_next.setEnabled(vm.can_step_forward)
        self.viewer_related.setVisible(sel.related_only)
        serif = theme.css_families(theme.SERIF)
        self.detail.setHtml(
            f"<body style=\"font-family:{serif}; color:{c['ink']};\"><p style=\"line-height:160%;\">"
            f"<span style=\"background-color:{c['accent-soft']};\">{self._text(sel.excerpt)}</span></p></body>")
        link = vm.selected_link
        if link:
            url = html.escape(link, quote=True)
            self.viewer_source.setText(f"Source: <a href=\"{url}\" style=\"color:{c['link']};\">{url}</a>")
        else:  # not a web address: shown, never clickable
            self.viewer_source.setText(f"Source: {html.escape(sel.source_url)}" if sel.source_url else "")

    def _fit_viewer(self, side: int, center: int) -> None:
        """Give the viewer its width out of the conversation; the source list keeps the width it had (collapsed,
        dragged narrower or wider). Left to the splitter, showing the viewer shrinks every pane instead."""
        total = side + center
        self.splitter.refresh()  # apply the viewer's show now, so the sizes below are not redistributed later
        viewer = min(self._viewer_width, max(0, total - side - self.center.minimumSizeHint().width()))
        self.splitter.setSizes([side, total - side - viewer, viewer])

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(*theme.WINDOW_SIZE)
