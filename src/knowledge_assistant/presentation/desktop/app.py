"""Desktop entry point. PySide6 is imported lazily so package imports do not require it.

Run the real app:   python -m knowledge_assistant.presentation.desktop.app
Offline demo:       python -m knowledge_assistant.presentation.desktop.app --fake
The real app reads GEMINI_API_KEY from the environment or .env (never printed) and needs the Chroma indexes.
"""
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    fake = "--fake" in argv

    from PySide6.QtCore import QThreadPool
    from PySide6.QtWidgets import QApplication

    from .viewmodels.ask_viewmodel import AskViewModel
    from .windows.main_window import MainWindow
    from .workers import QtExecutor

    if fake:
        from .viewmodels.fake_ask_question import FakeAskQuestion

        port = FakeAskQuestion()
    else:
        from dotenv import load_dotenv

        from .wiring import build_real_port

        load_dotenv(Path(__file__).resolve().parents[4] / ".env")
        port = build_real_port()

    app = QApplication(sys.argv[:1])
    # one question at a time (the view-model disables input while busy); a private pool keeps the global one free
    vm = AskViewModel(port, QtExecutor(QThreadPool()))
    window = MainWindow(vm, title="Knowledge Assistant (fake data)" if fake else "Knowledge Assistant")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
