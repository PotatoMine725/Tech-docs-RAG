"""Desktop entry point. PySide6 is imported lazily so package imports do not require it.

Run:  python -m knowledge_assistant.presentation.desktop.app --fake
(the real use case is wired in GUI-001 proper)
"""
import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--fake" not in argv:
        print("Only --fake is available until GUI-001 wires the real use case.", file=sys.stderr)
        return 2

    from PySide6.QtWidgets import QApplication

    from .viewmodels.ask_viewmodel import AskViewModel
    from .viewmodels.fake_ask_question import FakeAskQuestion
    from .windows.main_window import MainWindow
    from .workers import QtExecutor

    app = QApplication(sys.argv[:1])
    vm = AskViewModel(FakeAskQuestion(), QtExecutor())
    window = MainWindow(vm)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
