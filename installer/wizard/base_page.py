from __future__ import annotations
# 第三方库导入
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor


class BasePage(QWidget):
    """向导页面基类

    提供统一的页面接口和内容区域布局。
    """

    next_requested = Signal()
    back_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._wizard = None
        self._config = {}

        # 创建主布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(30, 30, 30, 15)
        self._main_layout.setSpacing(15)

        # 创建内容区域（子类填充）
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(15)
        self._main_layout.addWidget(self._content_widget, 1)

        self._update_styles()

    def set_wizard(self, wizard):
        self._wizard = wizard

    def set_config(self, config: dict):
        self._config = config

    def setup_ui(self):
        pass

    def _update_styles(self):
        text_color = QColor(40, 40, 40)
        self.setStyleSheet(f"""
            QWidget {{
                color: {text_color.name()};
                background-color: transparent;
            }}
        """)

    def on_enter(self):
        pass

    def can_next(self) -> bool:
        return True

    def can_back(self) -> bool:
        return True
