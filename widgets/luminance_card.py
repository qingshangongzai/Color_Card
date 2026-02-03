from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QFont

from qfluentwidgets import isDarkTheme


def get_zone_background_color():
    """获取Zone框背景颜色"""
    if isDarkTheme():
        return QColor(70, 70, 70)
    else:
        return QColor(255, 255, 255)


def get_zone_text_color():
    """获取Zone框文字颜色"""
    if isDarkTheme():
        return QColor(255, 255, 255)
    else:
        return QColor(0, 0, 0)


def get_secondary_text_color():
    """获取次要文字颜色"""
    if isDarkTheme():
        return QColor(160, 160, 160)
    else:
        return QColor(120, 120, 120)


class ZoneValueLabel(QWidget):
    """显示Zone值的标签 - 主题适配背景框 + 主题适配文字"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 30)
        self._zone = -1
        self._luminance = 0

    def set_zone(self, zone: int, luminance: int = 0):
        """设置Zone值"""
        self._zone = zone
        self._luminance = luminance
        self.update()

    def clear(self):
        """清空显示"""
        self._zone = -1
        self._luminance = 0
        self.update()

    def get_zone_label(self) -> str:
        """获取Zone显示标签"""
        if self._zone < 0:
            return "--"
        return str(self._zone)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 主题适配背景框
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(get_zone_background_color())
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)

        # 主题适配文字
        painter.setPen(get_zone_text_color())
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)

        label = self.get_zone_label()
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, label)


class LuminanceCard(QWidget):
    """单个明度信息卡 - 简化版，只显示Zone"""
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Zone显示框
        self.zone_label = ZoneValueLabel()
        layout.addWidget(self.zone_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 索引标签
        index_label = QLabel(f"#{self.index + 1}")
        secondary_color = get_secondary_text_color()
        index_label.setStyleSheet(f"color: {secondary_color.name()}; font-size: 11px;")
        index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(index_label)

        layout.addStretch()

    def set_zone(self, zone: int, luminance: int = 0):
        """设置Zone信息"""
        self.zone_label.set_zone(zone, luminance)

    def clear(self):
        """清空显示"""
        self.zone_label.clear()


class LuminanceCardPanel(QWidget):
    """明度信息卡面板（包含5个Zone卡）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        self.cards = []
        for i in range(5):
            card = LuminanceCard(i)
            self.cards.append(card)
            layout.addWidget(card)

    def update_zone(self, index: int, zone: int, luminance: int = 0):
        """更新指定索引的Zone"""
        if 0 <= index < len(self.cards):
            self.cards[index].set_zone(zone, luminance)

    def clear_all(self):
        """清空所有卡片"""
        for card in self.cards:
            card.clear()
