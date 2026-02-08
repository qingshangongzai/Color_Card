# 标准库导入
from typing import List, Tuple

# 第三方库导入
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QApplication
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from qfluentwidgets import CardWidget, PushButton, ToolButton, FluentIcon, InfoBar, InfoBarPosition

# 项目模块导入
from core import get_color_info
from .cards import BaseCard, BaseCardPanel, COLOR_MODE_CONFIG, ColorModeContainer, get_text_color, get_placeholder_color, get_border_color


class SchemeColorInfoCard(BaseCard):
    """配色方案颜色信息卡片（与ColorCard样式一致）"""

    clicked = Signal(int)

    def __init__(self, index: int, parent=None):
        self._hex_value = "--"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
        self._hex_visible = True
        super().__init__(index, parent)

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 设置sizePolicy，允许垂直压缩
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 设置色卡最小高度，确保基本显示
        self.setMinimumHeight(120)

        # 颜色块
        self.color_block = QWidget()
        self.color_block.setMinimumHeight(40)
        self.color_block.setMaximumHeight(80)
        self._update_placeholder_style()
        layout.addWidget(self.color_block)

        # 数值区域（两列布局）
        values_container = QWidget()
        values_container.setMinimumHeight(50)
        values_layout = QHBoxLayout(values_container)
        values_layout.setContentsMargins(0, 0, 0, 0)
        values_layout.setSpacing(10)

        # 第一列色彩模式
        self.mode_container_1 = ColorModeContainer(self._color_modes[0])
        values_layout.addWidget(self.mode_container_1)

        # 第二列色彩模式
        self.mode_container_2 = ColorModeContainer(self._color_modes[1])
        values_layout.addWidget(self.mode_container_2)

        layout.addWidget(values_container)

        # 16进制颜色值显示区域
        self.hex_container = QWidget()
        self.hex_container.setMinimumHeight(28)
        self.hex_container.setMaximumHeight(35)
        hex_layout = QHBoxLayout(self.hex_container)
        hex_layout.setContentsMargins(0, 0, 0, 0)
        hex_layout.setSpacing(5)

        # 16进制值显示按钮
        self.hex_button = PushButton("--")
        self.hex_button.setFixedHeight(28)
        self.hex_button.setEnabled(False)
        self._update_hex_button_style()

        # 复制按钮
        self.copy_button = ToolButton(FluentIcon.COPY)
        self.copy_button.setFixedSize(28, 28)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_hex_to_clipboard)

        hex_layout.addWidget(self.hex_button, stretch=1)
        hex_layout.addWidget(self.copy_button)

        layout.addWidget(self.hex_container)
        layout.addStretch()

        # 设置点击事件
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _update_placeholder_style(self):
        """更新占位符样式"""
        placeholder_color = get_placeholder_color()
        self.color_block.setStyleSheet(
            f"background-color: {placeholder_color.name()}; border-radius: 4px;"
        )

    def _update_hex_button_style(self):
        """更新16进制按钮样式"""
        primary_color = get_text_color(secondary=False)
        self.hex_button.setStyleSheet(
            f"""
            PushButton {{
                font-size: 12px;
                font-weight: bold;
                color: {primary_color.name()};
                background-color: transparent;
                border: 1px solid {get_border_color().name()};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            PushButton:disabled {{
                color: {get_text_color(secondary=True).name()};
                background-color: transparent;
            }}
            """
        )

    def _copy_hex_to_clipboard(self):
        """复制16进制颜色值到剪贴板"""
        if self._hex_value and self._hex_value != "--":
            clipboard = QApplication.clipboard()
            clipboard.setText(self._hex_value)
            # 显示复制成功提示
            InfoBar.success(
                title="已复制",
                content=f"颜色值 {self._hex_value} 已复制到剪贴板",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )

    def set_color_modes(self, modes):
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        self.mode_container_1.set_mode(modes[0])
        self.mode_container_2.set_mode(modes[1])

        # 如果有当前颜色信息，更新显示
        if self._current_color_info:
            self.update_color_display()

    def set_color(self, rgb: Tuple[int, int, int]):
        """设置颜色

        Args:
            rgb: RGB颜色元组 (r, g, b)
        """
        self._current_color_info = get_color_info(rgb[0], rgb[1], rgb[2])

        # 更新颜色块
        r, g, b = self._current_color_info['rgb']
        color_str = f"rgb({r}, {g}, {b})"
        border_color = get_border_color()
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
        )

        # 更新色彩模式值
        self.update_color_display()

        # 更新16进制值
        self._hex_value = self._current_color_info['hex']
        self.hex_button.setText(self._hex_value)
        self.hex_button.setEnabled(True)
        self.copy_button.setEnabled(True)

    def update_color_display(self):
        """根据当前模式更新颜色值显示"""
        if not self._current_color_info:
            return

        self.mode_container_1.update_values(self._current_color_info)
        self.mode_container_2.update_values(self._current_color_info)

    def clear(self):
        """清空颜色，恢复默认状态"""
        self._current_color_info = None

        # 重置颜色块
        self._update_placeholder_style()

        # 重置所有值
        self.mode_container_1.clear_values()
        self.mode_container_2.clear_values()

        # 重置16进制值
        self._hex_value = "--"
        self.hex_button.setText("--")
        self.hex_button.setEnabled(False)
        self.copy_button.setEnabled(False)

    def set_hex_visible(self, visible):
        """设置16进制显示区域的可见性"""
        self._hex_visible = visible
        self.hex_container.setVisible(visible)

    def mousePressEvent(self, event):
        """处理鼠标点击"""
        self.clicked.emit(self.index)
        super().mousePressEvent(event)


class SchemeColorPanel(BaseCardPanel):
    """配色方案色块面板（支持动态卡片数量）"""

    color_clicked = Signal(int)

    def __init__(self, parent=None, card_count=5):
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        super().__init__(parent, card_count)

    def _create_card(self, index):
        """创建色卡实例"""
        card = SchemeColorInfoCard(index)
        card.set_color_modes(self._color_modes)
        card.set_hex_visible(self._hex_visible)
        card.clicked.connect(self.on_card_clicked)
        return card

    def on_card_clicked(self, index):
        """卡片点击回调"""
        self.color_clicked.emit(index)

    def set_color_modes(self, modes):
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self.cards:
            card.set_color_modes(self._color_modes)

    def set_hex_visible(self, visible):
        """设置是否显示16进制颜色值"""
        self._hex_visible = visible
        for card in self.cards:
            card.set_hex_visible(visible)

    def set_colors(self, colors: List[Tuple[int, int, int]]):
        """设置颜色列表

        Args:
            colors: RGB颜色列表
        """
        for i, card in enumerate(self.cards):
            if i < len(colors):
                card.set_color(colors[i])
            else:
                card.clear()

    def update_settings(self, hex_visible, color_modes):
        """统一更新显示设置

        Args:
            hex_visible: 是否显示16进制颜色值
            color_modes: 色彩模式列表
        """
        self.set_hex_visible(hex_visible)
        self.set_color_modes(color_modes)
