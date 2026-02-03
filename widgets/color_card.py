from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from qfluentwidgets import isDarkTheme, PushButton, ToolButton, FluentIcon, InfoBar, InfoBarPosition


def get_text_color(secondary=False):
    """获取主题文本颜色"""
    if isDarkTheme():
        return QColor(160, 160, 160) if secondary else QColor(255, 255, 255)
    else:
        return QColor(120, 120, 120) if secondary else QColor(40, 40, 40)


def get_placeholder_color():
    """获取占位符颜色（空色块背景）"""
    if isDarkTheme():
        return QColor(60, 60, 60)
    else:
        return QColor(204, 204, 204)


def get_border_color():
    """获取边框颜色"""
    if isDarkTheme():
        return QColor(80, 80, 80)
    else:
        return QColor(221, 221, 221)


class ColorValueLabel(QWidget):
    """显示单个颜色值的标签"""
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        self.label = QLabel(label_text)
        self.value = QLabel("--")

        self._update_styles()

        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addStretch()

    def _update_styles(self):
        """更新样式以适配主题"""
        secondary_color = get_text_color(secondary=True)
        primary_color = get_text_color(secondary=False)

        self.label.setStyleSheet(
            f"color: {secondary_color.name()}; font-size: 11px;"
        )
        self.value.setStyleSheet(
            f"color: {primary_color.name()}; font-size: 12px; font-weight: bold;"
        )

    def set_value(self, value):
        self.value.setText(str(value))


class ColorCard(QWidget):
    """单个色卡组件"""
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self._hex_value = "--"
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 颜色块
        self.color_block = QWidget()
        self.color_block.setFixedHeight(80)
        self._update_placeholder_style()
        layout.addWidget(self.color_block)

        # 数值区域（两列布局）
        values_container = QWidget()
        values_layout = QHBoxLayout(values_container)
        values_layout.setContentsMargins(0, 0, 0, 0)
        values_layout.setSpacing(10)

        # HSB 值（左列）
        hsb_container = QWidget()
        hsb_layout = QVBoxLayout(hsb_container)
        hsb_layout.setContentsMargins(0, 0, 0, 0)
        hsb_layout.setSpacing(2)

        self.h_label = ColorValueLabel("H:")
        self.s_label = ColorValueLabel("S:")
        self.b_label = ColorValueLabel("B:")

        hsb_layout.addWidget(self.h_label)
        hsb_layout.addWidget(self.s_label)
        hsb_layout.addWidget(self.b_label)

        values_layout.addWidget(hsb_container)

        # LAB 值（右列）
        lab_container = QWidget()
        lab_layout = QVBoxLayout(lab_container)
        lab_layout.setContentsMargins(0, 0, 0, 0)
        lab_layout.setSpacing(2)

        self.l_label = ColorValueLabel("L:")
        self.a_label = ColorValueLabel("a:")
        self.b_lab_label = ColorValueLabel("b:")

        lab_layout.addWidget(self.l_label)
        lab_layout.addWidget(self.a_label)
        lab_layout.addWidget(self.b_lab_label)

        values_layout.addWidget(lab_container)

        layout.addWidget(values_container)

        # 16进制颜色值显示区域
        self.hex_container = QWidget()
        hex_layout = QHBoxLayout(self.hex_container)
        hex_layout.setContentsMargins(0, 5, 0, 0)
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

    def set_color(self, color_info):
        """设置颜色信息"""
        # 更新颜色块
        r, g, b = color_info['rgb']
        color_str = f"rgb({r}, {g}, {b})"
        border_color = get_border_color()
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
        )

        # 更新HSB值
        h, s, b_val = color_info['hsb']
        self.h_label.set_value(f"{h}°")
        self.s_label.set_value(f"{s}%")
        self.b_label.set_value(f"{b_val}%")

        # 更新LAB值
        l, a, b_lab = color_info['lab']
        self.l_label.set_value(l)
        self.a_label.set_value(a)
        self.b_lab_label.set_value(b_lab)

        # 更新16进制值
        self._hex_value = color_info['hex']
        self.hex_button.setText(self._hex_value)
        self.hex_button.setEnabled(True)
        self.copy_button.setEnabled(True)

    def clear_color(self):
        """清空颜色，恢复默认状态"""
        # 重置颜色块
        self._update_placeholder_style()

        # 重置所有值为 "--"
        self.h_label.set_value("--")
        self.s_label.set_value("--")
        self.b_label.set_value("--")
        self.l_label.set_value("--")
        self.a_label.set_value("--")
        self.b_lab_label.set_value("--")

        # 重置16进制值
        self._hex_value = "--"
        self.hex_button.setText("--")
        self.hex_button.setEnabled(False)
        self.copy_button.setEnabled(False)

    def set_hex_visible(self, visible):
        """设置16进制显示区域的可见性"""
        self.hex_container.setVisible(visible)


class ColorCardPanel(QWidget):
    """色卡面板（包含5个色卡）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hex_visible = True
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        self.cards = []
        for i in range(5):
            card = ColorCard(i)
            self.cards.append(card)
            layout.addWidget(card)

    def update_color(self, index, color_info):
        """更新指定索引的颜色"""
        if 0 <= index < len(self.cards):
            self.cards[index].set_color(color_info)

    def clear_colors(self):
        """清空所有色卡颜色"""
        for card in self.cards:
            card.clear_color()

    def set_hex_visible(self, visible):
        """设置是否显示16进制颜色值"""
        self._hex_visible = visible
        for card in self.cards:
            card.set_hex_visible(visible)

    def is_hex_visible(self):
        """获取16进制颜色值显示状态"""
        return self._hex_visible
