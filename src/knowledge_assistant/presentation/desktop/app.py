"""Desktop entry point scaffold. PySide6 is imported lazily so package imports do not require it."""
import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Knowledge Assistant")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
