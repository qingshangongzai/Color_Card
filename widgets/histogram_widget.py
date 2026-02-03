from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from color_utils import calculate_histogram, get_zone_bounds


class HistogramWidget(QWidget):
    """明度直方图组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMaximumHeight(200)
        self.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")

        self._histogram = [0] * 256
        self._max_count = 0
        self._highlight_zones = []  # 高亮显示的区域列表

    def set_image(self, image):
        """设置图片并计算直方图"""
        self._histogram = calculate_histogram(image)
        self._max_count = max(self._histogram) if self._histogram else 0
        self.update()

    def set_highlight_zones(self, zones):
        """设置高亮显示的区域

        Args:
            zones: 区域编号列表，如 ["3-4", "5-6"]
        """
        self._highlight_zones = zones
        self.update()

    def clear_highlight(self):
        """清除高亮"""
        self._highlight_zones = []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景
        painter.fillRect(self.rect(), QColor(26, 26, 26))

        # 计算绘图区域（留边距）
        margin_left = 30
        margin_right = 10
        margin_top = 10
        margin_bottom = 25

        draw_width = self.width() - margin_left - margin_right
        draw_height = self.height() - margin_top - margin_bottom

        if draw_width <= 0 or draw_height <= 0:
            return

        # 绘制8个区域的分隔线
        self._draw_zone_lines(painter, margin_left, margin_top, draw_width, draw_height)

        # 绘制直方图
        self._draw_histogram(painter, margin_left, margin_top, draw_width, draw_height)

        # 绘制高亮区域
        self._draw_highlight(painter, margin_left, margin_top, draw_width, draw_height)

        # 绘制刻度标签
        self._draw_labels(painter, margin_left, margin_top, draw_width, draw_height)

    def _draw_zone_lines(self, painter, x, y, width, height):
        """绘制区域分隔线"""
        pen = QPen(QColor(60, 60, 60), 1)
        painter.setPen(pen)

        # 8个区域，画7条分隔线
        for i in range(1, 8):
            line_x = x + (width * i) // 8
            painter.drawLine(line_x, y, line_x, y + height)

    def _draw_histogram(self, painter, x, y, width, height):
        """绘制直方图曲线"""
        if self._max_count == 0:
            return

        # 使用白色/灰色绘制直方图
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(180, 180, 180))

        # 每个明度值对应的宽度
        bar_width = width / 256

        for i in range(256):
            # 计算柱子高度
            bar_height = (self._histogram[i] / self._max_count) * height

            # 绘制柱子
            bar_x = x + i * bar_width
            bar_y = y + height - bar_height

            painter.drawRect(int(bar_x), int(bar_y), max(1, int(bar_width) + 1), int(bar_height))

    def _draw_highlight(self, painter, x, y, width, height):
        """绘制高亮区域"""
        if not self._highlight_zones:
            return

        # 高亮颜色（黄色半透明）
        highlight_color = QColor(255, 200, 0, 80)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(highlight_color)

        for zone in self._highlight_zones:
            min_lum, max_lum = get_zone_bounds(zone)

            # 计算区域在直方图中的位置
            start_x = x + (min_lum * width) // 256
            end_x = x + ((max_lum + 1) * width) // 256
            zone_width = end_x - start_x

            # 绘制高亮矩形
            painter.drawRect(start_x, y, zone_width, height)

            # 绘制区域编号文字
            font = QFont()
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)

            text_color = QColor(255, 220, 100)
            painter.setPen(text_color)

            text_rect = painter.boundingRect(
                start_x, y + height // 2 - 10,
                zone_width, 20,
                Qt.AlignmentFlag.AlignCenter, zone
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, zone)

    def _draw_labels(self, painter, x, y, width, height):
        """绘制刻度标签"""
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor(150, 150, 150))

        # 绘制底部刻度（0, 32, 64, 96, 128, 160, 192, 224, 255）
        tick_values = [0, 32, 64, 96, 128, 160, 192, 224, 255]

        for value in tick_values:
            tick_x = x + (value * width) // 256

            # 绘制刻度线
            painter.drawLine(tick_x, y + height, tick_x, y + height + 3)

            # 绘制刻度值
            text = str(value)
            text_rect = painter.boundingRect(
                tick_x - 15, y + height + 5,
                30, 15,
                Qt.AlignmentFlag.AlignCenter, text
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        # 绘制左侧Y轴标签（最大值）
        if self._max_count > 0:
            max_text = str(self._max_count)
            painter.drawText(5, y + 10, max_text)

    def clear(self):
        """清除直方图数据"""
        self._histogram = [0] * 256
        self._max_count = 0
        self._highlight_zones = []
        self.update()
