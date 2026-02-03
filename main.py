import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from qfluentwidgets import FluentWindow, setTheme, Theme, setThemeColor

from widgets import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    setTheme(Theme.AUTO)
    setThemeColor('#0078d4')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
