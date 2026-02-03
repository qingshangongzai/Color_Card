from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from qfluentwidgets import isDarkTheme, PushButton, ToolButton, FluentIcon, InfoBar, InfoBarPosition


# 色彩模式配置：模式名称 -> (显示名称, 标签列表, 单位列表, 格式化函数)
COLOR_MODE_CONFIG = {
    'HSB': (
        'HSB',
        ['H:', 'S:', 'B:'],
        ['°', '%', '%'],
        lambda values: [f"{values[0]}°", f"{values[1]}%", f"{values[2]}%"]
    ),
    'LAB': (
        'LAB',
        ['L:', 'A:', 'B:'],
        ['', '', ''],
        lambda values: [str(values[0]), str(values[1]), str(values[2])]
    ),
    'HSL': (
        'HSL',
        ['H:', 'S:', 'L:'],
        ['°', '%', '%'],
        lambda values: [f"{values[0]}°", f"{values[1]}%", f"{values[2]}%"]
    ),
    'CMYK': (
        'CMYK',
        ['C:', 'M:', 'Y:', 'K:'],
        ['%', '%', '%', '%'],
        lambda values: [f"{values[0]}%", f"{values[1]}%", f"{values[2]}%", f"{values[3]}%"]
    ),
    'RGB': (
        'RGB',
        ['R:', 'G:', 'B:'],
        ['', '', ''],
        lambda values: [str(values[0]), str(values[1]), str(values[2])]
    )
}


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


class ColorModeContainer(QWidget):
    """显示单个色彩模式的容器"""
    def __init__(self, mode='HSB', parent=None):
        super().__init__(parent)
        self._mode = mode
        self._labels = []
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 根据模式创建标签
        config = COLOR_MODE_CONFIG.get(self._mode, COLOR_MODE_CONFIG['HSB'])
        labels_text = config[1]

        self._labels = []
        for text in labels_text:
            label = ColorValueLabel(text)
            self._labels.append(label)
            layout.addWidget(label)

    def set_mode(self, mode):
        """设置色彩模式"""
        if self._mode == mode:
            return

        self._mode = mode

        # 清除现有标签
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重新创建标签
        config = COLOR_MODE_CONFIG.get(mode, COLOR_MODE_CONFIG['HSB'])
        labels_text = config[1]

        self._labels = []
        for text in labels_text:
            label = ColorValueLabel(text)
            self._labels.append(label)
            layout.addWidget(label)

    def update_values(self, color_info):
        """更新颜色值显示"""
        mode_key = self._mode.lower()
        if mode_key not in color_info:
            return

        values = color_info[mode_key]
        config = COLOR_MODE_CONFIG.get(self._mode, COLOR_MODE_CONFIG['HSB'])
        format_func = config[3]
        formatted_values = format_func(values)

        for i, label in enumerate(self._labels):
            if i < len(formatted_values):
                label.set_value(formatted_values[i])
            else:
                label.set_value("--")

    def clear_values(self):
        """清空所有值"""
        for label in self._labels:
            label.set_value("--")


class ColorCard(QWidget):
    """单个色卡组件"""
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self._hex_value = "--"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
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

        # 第一列色彩模式
        self.mode_container_1 = ColorModeContainer(self._color_modes[0])
        values_layout.addWidget(self.mode_container_1)

        # 第二列色彩模式
        self.mode_container_2 = ColorModeContainer(self._color_modes[1])
        values_layout.addWidget(self.mode_container_2)

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

    def set_color(self, color_info):
        """设置颜色信息"""
        self._current_color_info = color_info

        # 更新颜色块
        r, g, b = color_info['rgb']
        color_str = f"rgb({r}, {g}, {b})"
        border_color = get_border_color()
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
        )

        # 更新色彩模式值
        self.update_color_display()

        # 更新16进制值
        self._hex_value = color_info['hex']
        self.hex_button.setText(self._hex_value)
        self.hex_button.setEnabled(True)
        self.copy_button.setEnabled(True)

    def update_color_display(self):
        """根据当前模式更新颜色值显示"""
        if not self._current_color_info:
            return

        self.mode_container_1.update_values(self._current_color_info)
        self.mode_container_2.update_values(self._current_color_info)

    def clear_color(self):
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
        self.hex_container.setVisible(visible)


class ColorCardPanel(QWidget):
    """色卡面板（包含多个色卡）"""
    def __init__(self, parent=None, card_count=5):
        super().__init__(parent)
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._card_count = card_count
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        self.cards = []
        for i in range(self._card_count):
            card = ColorCard(i)
            self.cards.append(card)
            layout.addWidget(card)

    def set_color_modes(self, modes):
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self.cards:
            card.set_color_modes(self._color_modes)

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

    def set_card_count(self, count):
        """设置色卡数量

        Args:
            count: 色卡数量 (2-5)
        """
        if count < 2 or count > 5:
            return

        if count == self._card_count:
            return

        old_count = self._card_count
        self._card_count = count

        layout = self.layout()

        if count > old_count:
            # 增加色卡
            for i in range(old_count, count):
                card = ColorCard(i)
                card.set_color_modes(self._color_modes)
                card.set_hex_visible(self._hex_visible)
                self.cards.append(card)
                layout.addWidget(card)
        else:
            # 减少色卡
            for i in range(old_count - 1, count - 1, -1):
                card = self.cards.pop()
                layout.removeWidget(card)
                card.deleteLater()
