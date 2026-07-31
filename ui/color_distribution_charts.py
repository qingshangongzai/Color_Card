"""色彩分布分析图表控件

三个纯绘制控件：色轮密度图、分区调色条、主色卡条。
控件只负责渲染，所有成品文案由对话框翻译后经视图模型注入，控件内不调 tr；
颜色统一取自 utils.theme_colors，随主题自适应，不硬编码。
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from core.color_distribution import (
    WHEEL_CHROMA_BINS, WHEEL_CHROMA_MAX, WHEEL_HUE_BINS
)
from utils.theme_colors import get_histogram_grid_color, get_tone_chart_text_color


def _hsb_qcolor(hue: float, s: float, v: float) -> QColor:
    """HSB 色相角（度）+ 饱和度/明度构造 QColor，与主项目色环一致"""
    return QColor.fromHsvF((hue % 360.0) / 360.0, max(0.0, min(1.0, s)),
                           max(0.0, min(1.0, v)))


def _gray_qcolor(v: float) -> QColor:
    """中性灰 QColor（明度 0~1）"""
    return QColor.fromHsvF(0.0, 0.0, max(0.0, min(1.0, v)))


class _ChartBase(QWidget):
    """图表控件基类：主题色取自 theme_colors，随主题重绘"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(220, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._data = None

    def update_theme(self) -> None:
        """主题变化时重绘（绘制时读取实时主题色）"""
        self.update()

    @staticmethod
    def _text_color() -> QColor:
        return get_tone_chart_text_color()

    @staticmethod
    def _grid_color() -> QColor:
        return get_histogram_grid_color()


class HueWheelWidget(_ChartBase):
    """色轮密度图：方位与主项目 HSB 色环一致（0°红在上，顺时针）

    角度 = HSB 色相，半径 = OKLCH chroma，透明度 = 像素量（对数归一）。
    四方位色名标注由对话框翻译后注入。
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(260, 240)
        self._axis_labels: list[str] = []

    def update_data(self, wheel_hist: np.ndarray, axis_labels: list[str]) -> None:
        """设置色轮直方图与四方位标注（0°/90°/180°/270°）"""
        self._data = wheel_hist
        self._axis_labels = axis_labels
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 26
        size = min(self.width(), self.height()) - 2 * margin
        if size <= 0:
            return
        radius = size / 2.0
        center = QPointF(self.width() / 2.0, self.height() / 2.0)

        if self._data is not None:
            self._paint_density(painter, center, radius)
        self._paint_grid(painter, center, radius)

    @staticmethod
    def _qt_angle(hue: float) -> float:
        """HSB 色相角 → Qt 弧度角（0°红在正上方，顺时针增大）"""
        return 90.0 - hue

    def _paint_density(self, painter: QPainter, center: QPointF, radius: float) -> None:
        hist = self._data
        max_count = float(hist.max())
        if max_count <= 0:
            return
        log_max = math.log1p(max_count)
        span = 360.0 / WHEEL_HUE_BINS
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(WHEEL_HUE_BINS):
            hue = (i + 0.5) * span
            for j in range(WHEEL_CHROMA_BINS):
                count = hist[i, j]
                if count <= 0:
                    continue
                alpha = int(30 + 225 * math.log1p(count) / log_max)
                sat = (j + 0.5) / WHEEL_CHROMA_BINS
                color = _hsb_qcolor(hue, 0.15 + 0.85 * sat, 0.95)
                color.setAlpha(alpha)

                r0 = radius * j / WHEEL_CHROMA_BINS
                r1 = radius * (j + 1) / WHEEL_CHROMA_BINS
                a0 = self._qt_angle(i * span)

                outer = QRectF(center.x() - r1, center.y() - r1, 2 * r1, 2 * r1)
                path = QPainterPath()
                path.arcMoveTo(outer, a0)
                path.arcTo(outer, a0, -span)
                if r0 > 0:
                    inner = QRectF(center.x() - r0, center.y() - r0, 2 * r0, 2 * r0)
                    path.arcTo(inner, a0 - span, span)
                else:
                    path.lineTo(center)
                path.closeSubpath()
                painter.fillPath(path, color)

    def _paint_grid(self, painter: QPainter, center: QPointF, radius: float) -> None:
        painter.setPen(QPen(self._grid_color(), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # chroma 刻度环与外圈
        for c in (0.1, 0.2, 0.3):
            r = radius * c / WHEEL_CHROMA_MAX
            painter.drawEllipse(center, r, r)
        painter.drawEllipse(center, radius, radius)

        # 色相辐条（每 30°，与 12 色名分段一致）
        for deg in range(0, 360, 30):
            qt = math.radians(self._qt_angle(deg))
            painter.drawLine(
                center,
                QPointF(center.x() + radius * math.cos(qt),
                        center.y() - radius * math.sin(qt)),
            )

        # 主方位标注（0°/90°/180°/270°，色名文案由对话框注入）
        if not self._axis_labels:
            return
        painter.setPen(QPen(self._text_color()))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        for label, deg in zip(self._axis_labels, (0, 90, 180, 270)):
            qt = math.radians(self._qt_angle(deg))
            x = center.x() + (radius + 13) * math.cos(qt)
            y = center.y() - (radius + 13) * math.sin(qt)
            painter.drawText(QRectF(x - 30, y - 8, 60, 16),
                             Qt.AlignmentFlag.AlignCenter, f"{label} {deg}°")


class ZoneToningBarWidget(_ChartBase):
    """分区调色条：每区按色名构成分段显示染色，下方标注风格名

    视图模型（对话框注入，文案已翻译）：
        {'style_text': str,
         'zones': [{'key','name_text','chroma','is_empty','status_text',
                    'composition':[{'hue','range','weight_pct','line1','line2'}]}, ...]}
    """

    _ZONE_V = {'dark': 0.45, 'mid': 0.68, 'bright': 0.9}

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)

    def update_data(self, zones_view: dict) -> None:
        self._data = zones_view
        self.update()

    def _segment_color(self, key: str, chroma: float, hue: float) -> QColor:
        # 放大显示彩度，让染色肉眼可辨
        sat = min(0.55, max(0.18, chroma * 5.0))
        return _hsb_qcolor(hue, sat, self._ZONE_V[key])

    @staticmethod
    def _range_text(item: dict) -> str:
        lo, hi = item['range']
        return f"{lo:.0f}°~{hi % 360:.0f}°"

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._data:
            return

        zones = self._data['zones']
        margin = 16
        style_h = 26
        chart_rect = self.rect().adjusted(margin, margin, -margin, -margin - style_h)
        spacing = chart_rect.width() / len(zones)
        block_w = spacing * 0.86

        font = QFont()
        for i, zone in enumerate(zones):
            x = chart_rect.left() + i * spacing + (spacing - block_w) / 2
            block_rect = QRect(int(x), chart_rect.top(),
                               int(block_w), chart_rect.height() - 22)
            self._paint_zone_block(painter, font, block_rect, zone)

            painter.setPen(QPen(self._text_color()))
            font.setPointSize(9)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(QRect(int(x), block_rect.bottom() + 3, int(block_w), 18),
                             Qt.AlignmentFlag.AlignCenter, zone['name_text'])

        painter.setPen(QPen(self._text_color()))
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(0, self.height() - style_h, self.width(), style_h),
                         Qt.AlignmentFlag.AlignCenter, self._data['style_text'])

    def _paint_zone_block(self, painter: QPainter, font: QFont,
                          block_rect: QRect, zone: dict) -> None:
        """单个分区色块：按色名构成占比纵向分段，无构成时显示分区状态"""
        comp = zone['composition']
        key = zone['key']
        painter.setPen(QPen(self._grid_color(), 1))

        if not comp:
            status = zone['status_text']
            if zone['is_empty']:
                # 无像素：空心块，与有内容的中性灰块区分开
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(block_rect, 6, 6)
                painter.setPen(QPen(self._text_color()))
                font.setPointSize(9)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(block_rect, Qt.AlignmentFlag.AlignCenter, status)
                return
            color = _gray_qcolor(self._ZONE_V[key])
            painter.setBrush(color)
            painter.drawRoundedRect(block_rect, 6, 6)
            self._draw_segment_text(painter, font, block_rect, color, status, '')
            return

        total_pct = sum(c['weight_pct'] for c in comp)
        heights = self._segment_heights(comp, total_pct, block_rect.height())
        y = block_rect.top()
        for idx, (item, seg_h) in enumerate(zip(comp, heights)):
            if idx == len(comp) - 1:
                seg_h = block_rect.bottom() - y + 1
            seg_rect = QRect(block_rect.left(), int(y), block_rect.width(), int(seg_h))
            # 水平渐变展示实测色相区间（HSB），尾部偏色肉眼可见
            lo, hi = item['range']
            grad = QLinearGradient(seg_rect.topLeft(), seg_rect.topRight())
            grad.setColorAt(0.0, self._segment_color(key, zone['chroma'], lo))
            grad.setColorAt(0.5, self._segment_color(key, zone['chroma'], item['hue']))
            grad.setColorAt(1.0, self._segment_color(key, zone['chroma'], hi))
            painter.setBrush(QBrush(grad))
            painter.drawRect(seg_rect)
            self._draw_segment_text(
                painter, font, seg_rect,
                self._segment_color(key, zone['chroma'], item['hue']),
                item['line1'], item['line2'],
            )
            y += seg_h

    @staticmethod
    def _segment_heights(comp: list[dict], total_pct: float, block_h: int) -> list[int]:
        """比例分配段高，小段保底 22px 保证占比小的颜色可见、文字可读"""
        heights = [block_h * c['weight_pct'] / total_pct for c in comp]
        min_h = min(22.0, block_h / max(1, len(comp)))
        small = [i for i, x in enumerate(heights) if x < min_h]
        big = [i for i in range(len(heights)) if i not in small]
        if small and big:
            remaining = block_h - min_h * len(small)
            big_total = sum(heights[i] for i in big)
            for i in big:
                heights[i] = remaining * heights[i] / big_total
            for i in small:
                heights[i] = min_h
        return [round(x) for x in heights]

    def _draw_segment_text(self, painter: QPainter, font: QFont, rect: QRect,
                           bg_color: QColor, line1: str, line2: str) -> None:
        """段内两行标注，空间不够时逐级省略"""
        if rect.height() < 16:
            return
        # 按背景明度选黑/白，保证可读（对比逻辑非主题色）
        text_color = QColor(255, 255, 255) if bg_color.lightness() < 128 else QColor(0, 0, 0)
        painter.setPen(QPen(text_color))
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        if line2 and rect.height() >= 36:
            half = rect.height() // 2
            painter.drawText(rect.adjusted(2, 0, -2, -half),
                             Qt.AlignmentFlag.AlignCenter, line1)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(rect.adjusted(2, half, -2, 0),
                             Qt.AlignmentFlag.AlignCenter, line2)
        else:
            painter.drawText(rect.adjusted(2, 0, -2, 0),
                             Qt.AlignmentFlag.AlignCenter,
                             f"{line1} {line2}".strip())
        painter.setPen(QPen(self._grid_color(), 1))


class DominantColorsBarWidget(_ChartBase):
    """主色卡色条（含 RGB 值与感知色名标注）

    视图模型（对话框注入）：[{'rgb':(r,g,b),'pct','display_name','index_label'}, ...]
    """

    def update_data(self, palette_view: list[dict]) -> None:
        self._data = palette_view
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._data:
            return

        margin_l = 44
        chart_rect = self.rect().adjusted(margin_l, 12, -12, -12)
        bar_height = chart_rect.height() / len(self._data)
        max_pct = max(item['pct'] for item in self._data)

        font = QFont()
        for i, item in enumerate(self._data):
            r, g, b = item['rgb']
            bar_width = (item['pct'] / max_pct) * chart_rect.width() * 0.62 if max_pct > 0 else 0

            bar_rect = QRect(
                chart_rect.left(),
                int(chart_rect.top() + i * bar_height + 4),
                int(bar_width),
                int(bar_height - 8)
            )
            painter.fillRect(bar_rect, QColor(r, g, b))
            painter.setPen(QPen(self._grid_color()))
            painter.drawRect(bar_rect)

            painter.setPen(QPen(self._text_color()))
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(
                QRect(chart_rect.left() - 40, int(chart_rect.top() + i * bar_height),
                      36, int(bar_height)),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                item['index_label']
            )
            painter.drawText(
                QRect(int(bar_rect.right() + 6), bar_rect.top(),
                      chart_rect.right() - bar_rect.right() - 6, bar_rect.height()),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{item['display_name']}  {item['pct']:.1f}%  RGB({r},{g},{b})"
            )
