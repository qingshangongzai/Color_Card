from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from color_utils import calculate_rgb_histogram


class RGBHistogramWidget(QWidget):
    """RGB直方图组件 - 显示图片的RGB三通道分布"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setMaximumHeight(180)

        self._histogram_r = [0] * 256
        self._histogram_g = [0] * 256
        self._histogram_b = [0] * 256
        self._max_count = 0

    def set_image(self, image):
        """设置图片并计算RGB直方图

        Args:
            image: QImage 对象
        """
        self._histogram_r, self._histogram_g, self._histogram_b = calculate_rgb_histogram(image)

        # 计算最大值用于归一化
        max_r = max(self._histogram_r) if self._histogram_r else 0
        max_g = max(self._histogram_g) if self._histogram_g else 0
        max_b = max(self._histogram_b) if self._histogram_b else 0
        self._max_count = max(max_r, max_g, max_b)

        self.update()

    def clear(self):
        """清除直方图数据"""
        self._histogram_r = [0] * 256
        self._histogram_g = [0] * 256
        self._histogram_b = [0] * 256
        self._max_count = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制深色背景（参考明度直方图风格）
        painter.fillRect(self.rect(), QColor(20, 20, 20))

        # 计算绘图区域（留边距）
        margin_left = 35
        margin_right = 10
        margin_top = 25  # 顶部留空间给标题
        margin_bottom = 20

        draw_width = self.width() - margin_left - margin_right
        draw_height = self.height() - margin_top - margin_bottom

        if draw_width <= 0 or draw_height <= 0:
            return

        # 绘制标题
        self._draw_title(painter)

        # 绘制RGB直方图
        self._draw_histogram(painter, margin_left, margin_top, draw_width, draw_height)

        # 绘制刻度标签
        self._draw_labels(painter, margin_left, margin_top, draw_width, draw_height)

    def _draw_title(self, painter):
        """绘制标题"""
        painter.setPen(QColor(200, 200, 200))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(10, 18, "RGB直方图")

    def _draw_histogram(self, painter, x, y, width, height):
        """绘制RGB直方图

        三条曲线叠加显示：R（红色）、G（绿色）、B（蓝色）
        """
        if self._max_count == 0:
            return

        # 每个亮度值对应的宽度
        bar_width = width / 256.0

        # 绘制三个通道的直方图（从后往前绘制，确保重叠区域可见）
        channels = [
            (self._histogram_b, QColor(0, 100, 255, 180)),   # 蓝色通道（最底层）
            (self._histogram_g, QColor(0, 200, 0, 180)),     # 绿色通道
            (self._histogram_r, QColor(255, 50, 50, 180)),   # 红色通道（最顶层）
        ]

        for histogram, color in channels:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)

            # 绘制直方图柱子
            for i in range(256):
                # 计算柱子高度 - 使用相对最大值的比例
                bar_height = (histogram[i] / self._max_count) * height

                if bar_height > 0:
                    # 绘制柱子
                    bar_x = x + i * bar_width
                    bar_y = y + height - bar_height

                    # 计算柱子宽度
                    if i == 255:
                        current_bar_width = max(1, int(x + width - bar_x))
                    else:
                        next_bar_x = x + (i + 1) * bar_width
                        current_bar_width = max(1, int(next_bar_x - bar_x + 0.5))

                    painter.drawRect(int(bar_x), int(bar_y), current_bar_width, int(bar_height))

    def _draw_labels(self, painter, x, y, width, height):
        """绘制刻度标签"""
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)

        # 绘制底部刻度线和数值
        tick_positions = [0, 64, 128, 192, 255]

        for value in tick_positions:
            tick_x = int(x + value * width / 256.0)

            # 绘制刻度线
            painter.setPen(QColor(100, 100, 100))
            painter.drawLine(tick_x, y + height, tick_x, y + height + 3)

            # 绘制刻度值
            text = str(value)
            text_rect = painter.boundingRect(
                tick_x - 15, y + height + 5,
                30, 14,
                Qt.AlignmentFlag.AlignCenter, text
            )
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        # 绘制底部基线
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(x, y + height, x + width, y + height)

        # 绘制左侧Y轴标签（最大值）
        if self._max_count > 0:
            painter.setPen(QColor(120, 120, 120))
            font.setPointSize(6)
            painter.setFont(font)
            max_text = str(self._max_count)
            painter.drawText(2, y + 8, max_text)

        # 绘制图例（R、G、B标识）
        legend_y = y - 5
        legend_items = [
            ("R", QColor(255, 50, 50)),
            ("G", QColor(0, 200, 0)),
            ("B", QColor(0, 100, 255))
        ]

        legend_x = x + width - 60
        for text, color in legend_items:
            painter.setPen(color)
            painter.drawText(legend_x, legend_y, text)
            legend_x += 20
