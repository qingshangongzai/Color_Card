"""直方图显示组件

借鉴主程序 LuminanceHistogramWidget 的 Lightroom 风格设计，
使用 Qt 自绘实现明度分布和 Zone 分区显示。
"""

from typing import Optional

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


# ========== 主题颜色常量 ==========
_BG_COLOR = QColor(42, 42, 42)
_TEXT_COLOR = QColor(150, 150, 150)
_AXIS_COLOR = QColor(120, 120, 120)
_GRID_COLOR = QColor(80, 80, 80)
_LINE_COLOR = QColor(200, 200, 200)
_PEAK_COLOR = QColor(231, 76, 60)
_P10_COLOR = QColor(39, 174, 96)
_P90_COLOR = QColor(243, 156, 18)

_ZONE_COLORS = [
    QColor(30, 30, 30),
    QColor(35, 35, 35),
    QColor(40, 40, 40),
    QColor(45, 45, 45),
    QColor(50, 50, 50),
    QColor(55, 55, 55),
    QColor(60, 60, 60),
    QColor(65, 65, 65),
    QColor(70, 70, 70),
]


class HistogramWidget(QWidget):
    """明度直方图显示组件 - Lightroom 风格"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._histogram: Optional[np.ndarray] = None
        self._peak: Optional[int] = None
        self._P10: Optional[int] = None
        self._P90: Optional[int] = None

        self.setMinimumHeight(180)
        self.setMaximumHeight(220)
        self.setStyleSheet(f"background-color: {_BG_COLOR.name()}; border-radius: 4px;")

        self._margin_left = 35
        self._margin_right = 15
        self._margin_top = 5
        self._margin_bottom = 30

    def set_histogram(
        self,
        histogram: np.ndarray,
        peak: Optional[int] = None,
        P10: Optional[int] = None,
        P90: Optional[int] = None
    ) -> None:
        """设置直方图数据

        Args:
            histogram: 直方图数据 (256,)
            peak: 波峰位置
            P10: 第10百分位数
            P90: 第90百分位数
        """
        self._histogram = histogram
        self._peak = peak
        self._P10 = P10
        self._P90 = P90
        self.update()

    def clear(self) -> None:
        """清空直方图"""
        self._histogram = None
        self._peak = None
        self._P10 = None
        self._P90 = None
        self.update()

    def paintEvent(self, event):
        """绘制直方图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), _BG_COLOR)

        draw_width = self.width() - self._margin_left - self._margin_right
        draw_height = self.height() - self._margin_top - self._margin_bottom

        if draw_width <= 0 or draw_height <= 0:
            return

        x = self._margin_left
        y = self._margin_top

        self._draw_zone_background(painter, x, y, draw_width, draw_height)

        if self._histogram is not None:
            self._draw_histogram_curve(painter, x, y, draw_width, draw_height)
            self._draw_markers(painter, x, y, draw_width, draw_height)

        self._draw_labels(painter, x, y, draw_width, draw_height)

    def _draw_zone_background(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制 Zone 背景色块"""
        zone_width = width / 9.0

        for i in range(9):
            zone_x = x + i * zone_width
            painter.fillRect(
                int(zone_x), y,
                int(zone_width + 0.5), height,
                _ZONE_COLORS[i]
            )

        pen = QPen(_GRID_COLOR, 1)
        painter.setPen(pen)
        for i in range(1, 9):
            line_x = int(x + i * zone_width)
            painter.drawLine(line_x, y, line_x, y + height)

    def _draw_histogram_curve(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制线连接样式直方图"""
        hist_sum = self._histogram.sum()
        if hist_sum == 0:
            return

        hist_normalized = self._histogram / hist_sum
        max_val = float(hist_normalized.max())

        bar_width = width / 256.0

        points = []
        for i in range(256):
            bar_height = (hist_normalized[i] / max_val) * height
            point_x = x + i * bar_width
            point_y = y + height - bar_height
            points.append((point_x, point_y))

        fill_path = QPainterPath()
        fill_path.moveTo(points[0][0], y + height)
        for px, py in points:
            fill_path.lineTo(px, py)
        fill_path.lineTo(points[-1][0], y + height)
        fill_path.closeSubpath()

        gradient = QLinearGradient(x, y, x, y + height)
        gradient.setColorAt(0, _LINE_COLOR)
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(fill_path, gradient)

        line_path = QPainterPath()
        line_path.moveTo(points[0][0], points[0][1])
        for px, py in points[1:]:
            line_path.lineTo(px, py)

        painter.setPen(QPen(_LINE_COLOR, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(line_path)

    def _draw_markers(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制标记线（波峰、P10、P90）"""
        if self._peak is not None:
            peak_x = x + (self._peak / 255.0) * width
            painter.setPen(QPen(_PEAK_COLOR, 2))
            painter.drawLine(int(peak_x), y, int(peak_x), y + height)

        if self._P10 is not None:
            p10_x = x + (self._P10 / 255.0) * width
            painter.setPen(QPen(_P10_COLOR, 1.5, Qt.PenStyle.DashLine))
            painter.drawLine(int(p10_x), y, int(p10_x), y + height)

        if self._P90 is not None:
            p90_x = x + (self._P90 / 255.0) * width
            painter.setPen(QPen(_P90_COLOR, 1.5, Qt.PenStyle.DashLine))
            painter.drawLine(int(p90_x), y, int(p90_x), y + height)

    def _draw_labels(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制刻度标签"""
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        zone_width = width / 9.0

        for i in range(10):
            tick_x = int(x + i * zone_width)

            painter.setPen(_TEXT_COLOR)
            painter.drawLine(tick_x, y + height, tick_x, y + height + 4)

            text = str(i)
            text_rect = painter.boundingRect(
                tick_x - 15, y + height + 6,
                30, 18,
                Qt.AlignmentFlag.AlignCenter, text
            )
            painter.setPen(_AXIS_COLOR)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.setPen(QPen(_GRID_COLOR, 1))
        painter.drawLine(x, y + height, x + width, y + height)

        if self._histogram is not None:
            max_count = int(self._histogram.max())
            if max_count > 0:
                painter.setPen(_AXIS_COLOR)
                font = QFont()
                font.setPointSize(7)
                painter.setFont(font)
                painter.drawText(5, y + 10, str(max_count))
