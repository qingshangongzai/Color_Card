"""影调标注工具

用于标注图片影调类型，收集数据用于算法优化。

使用方法:
    python -m tools.tone_labeler.main

或者:
    cd tools/tone_labeler
    python main.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from tools.tone_labeler.main_window import MainWindow


def main():
    """程序入口"""
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            padding: 6px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: white;
        }
        QPushButton:hover {
            background-color: #f0f0f0;
        }
        QPushButton:pressed {
            background-color: #e0e0e0;
        }
        QToolBar {
            spacing: 6px;
            padding: 4px;
            background-color: #fafafa;
            border-bottom: 1px solid #ddd;
        }
        QStatusBar {
            background-color: #fafafa;
            border-top: 1px solid #ddd;
        }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
