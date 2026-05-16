"""标注面板组件

提供影调类型选择按钮。
"""

from typing import Literal, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox
)


class LabelPanel(QWidget):
    """标注面板"""

    label_selected = Signal(str)
    clear_requested = Signal()

    TONE_TYPES = [
        ("高长调", "1"),
        ("高中调", "2"),
        ("高短调", "3"),
        ("中长调", "4"),
        ("中中调", "5"),
        ("中短调", "6"),
        ("低长调", "7"),
        ("低中调", "8"),
        ("低短调", "9"),
        ("全长调", "0"),
    ]

    PRIMARY_COLOR = "#3498db"
    SECONDARY_COLOR = "#27ae60"

    def __init__(
        self,
        panel_type: Literal["primary", "secondary"] = "primary",
        parent=None
    ):
        super().__init__(parent)

        self._panel_type = panel_type
        self._current_label: Optional[str] = None
        self._buttons: dict = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if self._panel_type == "primary":
            title = "首选标注"
            hint = "点击按钮或使用快捷键 1-0 选择影调类型"
        else:
            title = "次选标注 (可选)"
            hint = "当图片可能属于两种影调时填写"

        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)

        hint_label = QLabel(hint)
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        group_layout.addWidget(hint_label)

        grid = QGridLayout()
        grid.setSpacing(8)

        for i, (tone_type, shortcut) in enumerate(self.TONE_TYPES):
            btn = QPushButton(f"{tone_type} ({shortcut})")
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked, t=tone_type: self._on_button_clicked(t)
            )

            self._buttons[tone_type] = btn

            row = i // 5
            col = i % 5
            grid.addWidget(btn, row, col)

        group_layout.addLayout(grid)

        if self._panel_type == "secondary":
            clear_btn = QPushButton("清除次选")
            clear_btn.setMinimumHeight(28)
            clear_btn.setCursor(Qt.PointingHandCursor)
            clear_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)
            clear_btn.clicked.connect(self._on_clear_clicked)
            group_layout.addWidget(clear_btn)

        layout.addWidget(group)

    def _on_button_clicked(self, tone_type: str) -> None:
        """按钮点击处理"""
        self.set_current_label(tone_type)
        self.label_selected.emit(tone_type)

    def _on_clear_clicked(self) -> None:
        """清除按钮点击处理"""
        self.clear()
        self.clear_requested.emit()

    def set_current_label(self, label: Optional[str]) -> None:
        """设置当前标注

        Args:
            label: 影调类型
        """
        self._current_label = label

        highlight_color = (
            self.PRIMARY_COLOR
            if self._panel_type == "primary"
            else self.SECONDARY_COLOR
        )

        for tone_type, btn in self._buttons.items():
            if tone_type == label:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {highlight_color};
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet("")

    def get_current_label(self) -> Optional[str]:
        """获取当前标注"""
        return self._current_label

    def clear(self) -> None:
        """清空选择"""
        self._current_label = None
        for btn in self._buttons.values():
            btn.setStyleSheet("")
