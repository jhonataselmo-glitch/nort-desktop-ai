import sys
from PySide6.QtWidgets import QApplication
from nort.ui.main import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NORT Desktop AI")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
