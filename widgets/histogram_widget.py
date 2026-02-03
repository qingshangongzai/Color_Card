from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient

from color_utils import calculate_histogram, get_zone_bounds


class HistogramWidget(QWidget):
    """明度直方图组件 - 参考Lightroom风格设计"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)
        # 使用更深的背景色，接近LR的风格
        self.setStyleSheet("background-color: #141414; border-radius: 4px;")

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

        # 绘制深色背景
        painter.fillRect(self.rect(), QColor(20, 20, 20))

        # 计算绘图区域（留边距）
        margin_left = 35
        margin_right = 15
        margin_top = 15
        margin_bottom = 30

        draw_width = self.width() - margin_left - margin_right
        draw_height = self.height() - margin_top - margin_bottom

        if draw_width <= 0 or draw_height <= 0:
            return

        # 绘制Zone背景色块（类似LR的风格）
        self._draw_zone_background(painter, margin_left, margin_top, draw_width, draw_height)

        # 绘制直方图
        self._draw_histogram(painter, margin_left, margin_top, draw_width, draw_height)

        # 绘制高亮区域（黄色半透明覆盖）
        self._draw_highlight(painter, margin_left, margin_top, draw_width, draw_height)

        # 绘制刻度标签
        self._draw_labels(painter, margin_left, margin_top, draw_width, draw_height)

    def _draw_zone_background(self, painter, x, y, width, height):
        """绘制Zone背景色块 - LR风格"""
        zone_width = width / 8.0

        # Zone颜色配置 - 使用更 subtle 的背景色
        zone_bg_colors = [
            QColor(30, 30, 30),   # Zone 0: 极暗
            QColor(35, 35, 35),   # Zone 1: 暗
            QColor(40, 40, 40),   # Zone 2: 偏暗
            QColor(45, 45, 45),   # Zone 3: 中灰
            QColor(50, 50, 50),   # Zone 4: 偏亮
            QColor(55, 55, 55),   # Zone 5: 亮
            QColor(60, 60, 60),   # Zone 6: 很亮
            QColor(65, 65, 65),   # Zone 7: 极亮
        ]

        for i in range(8):
            zone_x = x + i * zone_width
            # 绘制Zone背景
            painter.fillRect(
                int(zone_x), y,
                int(zone_width + 0.5), height,
                zone_bg_colors[i]
            )

        # 绘制Zone分隔线
        pen = QPen(QColor(80, 80, 80), 1)
        painter.setPen(pen)
        for i in range(1, 8):
            line_x = int(x + i * zone_width)
            painter.drawLine(line_x, y, line_x, y + height)

    def _draw_histogram(self, painter, x, y, width, height):
        """绘制直方图曲线 - LR风格"""
        if self._max_count == 0:
            return

        # 使用渐变填充，从浅灰到白色
        gradient = QLinearGradient(x, y + height, x, y)
        gradient.setColorAt(0, QColor(120, 120, 120))
        gradient.setColorAt(1, QColor(200, 200, 200))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)

        # 每个明度值对应的宽度
        bar_width = width / 256.0

        # 绘制直方图柱子
        for i in range(256):
            # 计算柱子高度 - 使用相对最大值的比例
            bar_height = (self._histogram[i] / self._max_count) * height

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

    def _draw_highlight(self, painter, x, y, width, height):
        """绘制高亮区域 - LR风格的黄色覆盖"""
        if not self._highlight_zones:
            return

        zone_width = width / 8.0

        for zone in self._highlight_zones:
            min_lum, max_lum = get_zone_bounds(zone)
            zone_index = min_lum // 32

            # 计算区域位置
            start_x = int(x + zone_index * zone_width)
            end_x = int(x + (zone_index + 1) * zone_width)
            zone_width_px = end_x - start_x

            # 绘制黄色半透明覆盖层
            highlight_color = QColor(255, 200, 50, 60)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(highlight_color)
            painter.drawRect(start_x, y, zone_width_px, height)

            # 绘制黄色边框
            painter.setPen(QPen(QColor(255, 200, 50, 150), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(start_x, y, zone_width_px, height)

            # 绘制区域编号文字
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)

            text_color = QColor(255, 220, 100)
            painter.setPen(text_color)

            # 在区域中间显示编号
            text = zone
            text_rect = painter.boundingRect(
                start_x, y + height // 2 - 12,
                zone_width_px, 24,
                Qt.AlignmentFlag.AlignCenter, text
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_labels(self, painter, x, y, width, height):
        """绘制刻度标签 - Zone 0-8 风格"""
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        # 绘制底部刻度线和数值 - Zone 0 到 8
        zone_width = width / 8.0

        for i in range(9):  # 0, 1, 2, 3, 4, 5, 6, 7, 8
            tick_x = int(x + i * zone_width)

            # 绘制刻度线
            painter.setPen(QColor(100, 100, 100))
            painter.drawLine(tick_x, y + height, tick_x, y + height + 4)

            # 绘制刻度值 (0-8)
            text = str(i)
            text_rect = painter.boundingRect(
                tick_x - 15, y + height + 6,
                30, 18,
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
            font.setPointSize(7)
            painter.setFont(font)
            max_text = str(self._max_count)
            painter.drawText(5, y + 10, max_text)

    def clear(self):
        """清除直方图数据"""
        self._histogram = [0] * 256
        self._max_count = 0
        self._highlight_zones = []
        self.update()
