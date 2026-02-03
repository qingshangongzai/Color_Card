import sys
from io import StringIO

# 临时重定向 stdout 以屏蔽 QFluentWidgets 的推广提示
_old_stdout = sys.stdout
sys.stdout = StringIO()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from qfluentwidgets import FluentWindow, setTheme, Theme, setThemeColor

# 恢复 stdout
sys.stdout = _old_stdout

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
