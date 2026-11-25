"""Colours, fonts and the Qt stylesheet of the desktop window, from the Knowledge Assistant design system tokens.

Plain data plus one function that writes QSS: no Qt import, so it tests without a display. Light and dark values
match the design system's tokens.json; the light banner colours are the app's original ones.
"""
from __future__ import annotations

LIGHT: dict[str, str] = {
    "surface": "#f4f6f4", "surface-raised": "#ffffff", "surface-sunken": "#e9ece9",
    "ink": "#1b2320", "ink-muted": "#535e59", "line": "#d6dbd7", "line-strong": "#7d8883",
    "accent": "#1d5c53", "accent-soft": "#d9ebe6", "on-accent": "#ffffff", "link": "#24508f",
    "warning-bg": "#fff3cd", "warning-ink": "#664d03", "warning-line": "#e0a800",
    "danger-bg": "#f8d7da", "danger-ink": "#58151c", "danger-line": "#c0392b",
}

DARK: dict[str, str] = {
    "surface": "#121816", "surface-raised": "#1a2220", "surface-sunken": "#0d1211",
    "ink": "#e4eae7", "ink-muted": "#a0aca6", "line": "#2e3935", "line-strong": "#6d7a74",
    "accent": "#6cc0b0", "accent-soft": "#1b3631", "on-accent": "#0b1b18", "link": "#93b6ee",
    "warning-bg": "#33290a", "warning-ink": "#f5d77a", "warning-line": "#c99700",
    "danger-bg": "#3a1519", "danger-ink": "#ffb4ba", "danger-line": "#e5675c",
}

# Font families in preference order. Nothing is downloaded: a face that is not installed falls through to the
# next one, and Segoe UI covers Vietnamese diacritics on Windows.
SANS = ["Be Vietnam Pro", "Segoe UI", "Arial"]
SERIF = ["Source Serif 4", "Georgia", "Times New Roman"]
MONO = ["JetBrains Mono", "Cascadia Mono", "Consolas", "Courier New"]

SIDEBAR_WIDTH = 264
VIEWER_WIDTH = 380
WINDOW_SIZE = (1200, 780)


def colors(dark: bool) -> dict[str, str]:
    return DARK if dark else LIGHT


def css_families(families: list[str]) -> str:
    """A CSS font-family list in single quotes, so it can sit inside a double-quoted HTML style attribute."""
    return ", ".join(f"'{f}'" for f in families)


def stylesheet(c: dict[str, str]) -> str:
    """The window's QSS. Widgets opt in through object names; everything else takes the base rules."""
    return f"""
QMainWindow, QWidget#root {{ background: {c['surface']}; color: {c['ink']}; }}
QWidget {{ color: {c['ink']}; font-size: 10.5pt; }}
QMenuBar {{ background: {c['surface']}; color: {c['ink']}; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {c['accent-soft']}; color: {c['ink']}; }}
QMenu {{ background: {c['surface-raised']}; color: {c['ink']}; border: 1px solid {c['line-strong']}; }}
QStatusBar {{ background: {c['surface']}; color: {c['ink-muted']}; }}
QSplitter::handle {{ background: {c['line']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

QWidget#sources {{ background: {c['surface']}; }}
QLabel#paneLabel {{ color: {c['ink-muted']}; font-size: 8.5pt; font-weight: 600; letter-spacing: 1px; }}
QLabel#count, QLabel#hint, QLabel#viewerPath, QLabel#viewerPos {{ color: {c['ink-muted']}; }}
QLineEdit#filter {{ background: {c['surface-raised']}; border: 1px solid {c['line-strong']}; border-radius: 6px;
    padding: 4px 8px; color: {c['ink']}; }}
QListWidget#sourceList {{ background: {c['surface']}; border: none; outline: 0; }}
QListWidget#sourceList::item {{ border-radius: 3px; color: {c['ink']}; min-height: 26px; }}
QListWidget#sourceList::item:selected {{ background: {c['accent-soft']}; color: {c['ink']}; }}
QListWidget#sourceList::item:hover {{ background: {c['surface-sunken']}; }}

QTextBrowser#thread {{ background: {c['surface']}; border: none; }}
QFrame#composeBox {{ background: {c['surface-raised']}; border: 1px solid {c['line-strong']}; border-radius: 6px; }}
QPlainTextEdit#composer {{ background: transparent; border: none; color: {c['ink']}; }}
QProgressBar#busy {{ background: {c['surface-sunken']}; border: none; border-radius: 3px; }}
QProgressBar#busy::chunk {{ background: {c['accent']}; border-radius: 3px; }}

QPushButton {{ background: {c['surface-raised']}; color: {c['ink']}; border: 1px solid {c['line-strong']};
    border-radius: 6px; padding: 6px 16px; font-weight: 600; }}
QPushButton:focus {{ border: 2px solid {c['accent']}; }}
QPushButton#send {{ background: {c['accent']}; color: {c['on-accent']}; border-color: {c['accent']}; }}
QPushButton#send:disabled {{ background: {c['line']}; color: {c['ink-muted']}; border-color: {c['line']}; }}
QPushButton#textButton {{ background: transparent; border: none; color: {c['accent']}; padding: 2px 4px; }}
QPushButton#textButton:disabled {{ color: {c['ink-muted']}; }}

QFrame#viewer {{ background: {c['surface-raised']}; border-left: 1px solid {c['line']}; }}
QLabel#viewerDoc {{ font-size: 13pt; font-weight: 600; }}
QLabel#viewerRelated {{ font-weight: 600; }}
QLabel#viewerSource {{ color: {c['ink-muted']}; }}
QTextBrowser#excerpt {{ background: {c['surface-raised']}; border: none; }}
QToolTip {{ background: {c['surface-raised']}; color: {c['ink']}; border: 1px solid {c['line-strong']}; padding: 6px; }}
"""
