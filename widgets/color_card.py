from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class ColorValueLabel(QWidget):
    """显示单个颜色值的标签"""
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        self.label = QLabel(label_text)
        self.label.setStyleSheet("color: #888; font-size: 11px;")
        self.value = QLabel("--")
        self.value.setStyleSheet("color: #333; font-size: 12px; font-weight: bold;")

        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addStretch()

    def set_value(self, value):
        self.value.setText(str(value))


class ColorCard(QWidget):
    """单个色卡组件"""
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 颜色块
        self.color_block = QWidget()
        self.color_block.setFixedHeight(80)
        self.color_block.setStyleSheet("background-color: #cccccc; border-radius: 4px;")
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
        layout.addStretch()

    def set_color(self, color_info):
        """设置颜色信息"""
        # 更新颜色块
        r, g, b = color_info['rgb']
        color_str = f"rgb({r}, {g}, {b})"
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid #ddd;"
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

    def clear_color(self):
        """清空颜色，恢复默认状态"""
        # 重置颜色块
        self.color_block.setStyleSheet("background-color: #cccccc; border-radius: 4px;")

        # 重置所有值为 "--"
        self.h_label.set_value("--")
        self.s_label.set_value("--")
        self.b_label.set_value("--")
        self.l_label.set_value("--")
        self.a_label.set_value("--")
        self.b_lab_label.set_value("--")


class ColorCardPanel(QWidget):
    """色卡面板（包含5个色卡）"""
    def __init__(self, parent=None):
        super().__init__(parent)
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
