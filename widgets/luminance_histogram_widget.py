"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: luminance_histogram_widget
功能描述: 明度直方图组件，显示图片的明度分布和Zone分区

作者: 青山公仔
创建日期: 2026-02-04
"""

# 第三方库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

# 项目模块导入
from .base_histogram import BaseHistogram
from color_utils import calculate_histogram, get_zone_bounds


class LuminanceHistogramWidget(BaseHistogram):
    """明度直方图组件 - 参考Lightroom风格设计，显示图片的明度分布和Zone分区"""

    zone_pressed = Signal(int)   # 信号：Zone被按下 (0-7)
    zone_released = Signal()     # 信号：Zone被释放
    zone_changed = Signal(int)   # 信号：当前Zone变化 (0-7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)
        self.setStyleSheet("background-color: #141414; border-radius: 4px;")

        self._highlight_zones = []  # 高亮显示的区域列表
        self._pressed_zone = -1     # 当前按下的Zone
        self._current_zone = -1     # 当前选中的Zone

        # 启用鼠标跟踪
        self.setMouseTracking(True)

    def set_image(self, image):
        """设置图片并计算直方图"""
        histogram = calculate_histogram(image)
        self.set_data(histogram)

    def set_highlight_zones(self, zones):
        """设置高亮显示的区域

        Args:
            zones: 区域编号列表，如 ["3-4", "5-6"]
        """
        self._highlight_zones = zones
        self.update()

    def set_current_zone(self, zone: int):
        """设置当前选中的Zone (0-7)"""
        if 0 <= zone <= 7 and zone != self._current_zone:
            self._current_zone = zone
            self.zone_changed.emit(zone)
            self.update()

    def clear_highlight(self):
        """清除高亮"""
        self._highlight_zones = []
        self.update()

    def clear(self):
        """清除直方图数据"""
        super().clear()
        self._highlight_zones = []
        self._pressed_zone = -1
        self._current_zone = -1
        self.update()

    def get_zone_from_luminance(self, luminance: int) -> int:
        """根据明度值获取Zone (0-7)"""
        return min(7, luminance // 32)

    def get_zone_label(self, zone: int) -> str:
        """获取Zone的显示标签"""
        labels = ["0", "1", "2", "3", "4", "5", "6", "7"]
        return labels[zone] if 0 <= zone <= 7 else "--"

    def _draw_histogram(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制直方图曲线 - LR风格"""
        if self._max_count == 0:
            return

        # 绘制Zone背景色块（类似LR的风格）
        self._draw_zone_background(painter, x, y, width, height)

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

        # 按下状态或选中状态的Zone背景色（更亮一些）
        zone_active_colors = [
            QColor(50, 50, 60),   # Zone 0: 极暗
            QColor(55, 55, 65),   # Zone 1: 暗
            QColor(60, 60, 70),   # Zone 2: 偏暗
            QColor(65, 65, 75),   # Zone 3: 中灰
            QColor(70, 70, 80),   # Zone 4: 偏亮
            QColor(75, 75, 85),   # Zone 5: 亮
            QColor(80, 80, 90),   # Zone 6: 很亮
            QColor(85, 85, 95),   # Zone 7: 极亮
        ]

        for i in range(8):
            zone_x = x + i * zone_width
            # 如果是按下的Zone或当前选中的Zone，使用高亮背景色
            if i == self._pressed_zone or i == self._current_zone:
                bg_color = zone_active_colors[i]
            else:
                bg_color = zone_bg_colors[i]

            # 绘制Zone背景
            painter.fillRect(
                int(zone_x), y,
                int(zone_width + 0.5), height,
                bg_color
            )

            # 如果当前Zone被按下或选中，绘制边框
            if i == self._pressed_zone or i == self._current_zone:
                painter.setPen(QPen(QColor(0, 150, 255), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(int(zone_x), y, int(zone_width), height)

        # 绘制Zone分隔线
        pen = QPen(QColor(80, 80, 80), 1)
        painter.setPen(pen)
        for i in range(1, 8):
            line_x = int(x + i * zone_width)
            painter.drawLine(line_x, y, line_x, y + height)

    def _draw_custom_overlay(self, painter: QPainter, x: int, y: int, width: int, height: int):
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

    def _draw_labels(self, painter: QPainter, x: int, y: int, width: int, height: int):
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
        self._draw_bottom_baseline(painter, x, y, width, height)

        # 绘制左侧Y轴标签（最大值）
        self._draw_max_label(painter, x, y)

    def _get_zone_from_pos(self, pos):
        """根据鼠标位置获取对应的Zone (0-7)

        Args:
            pos: 鼠标位置 (QPoint)

        Returns:
            Zone编号 (0-7)，如果不在有效区域返回 -1
        """
        draw_width = self.width() - self._margin_left - self._margin_right
        draw_height = self.height() - self._margin_top - self._margin_bottom

        # 检查是否在绘图区域内
        if not (self._margin_left <= pos.x() <= self._margin_left + draw_width and
                self._margin_top <= pos.y() <= self._margin_top + draw_height):
            return -1

        # 计算Zone (0-7)
        zone_width = draw_width / 8.0
        zone_index = int((pos.x() - self._margin_left) / zone_width)

        return max(0, min(7, zone_index))

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            zone = self._get_zone_from_pos(event.pos())
            if zone >= 0:
                self._pressed_zone = zone
                self._current_zone = zone
                self.zone_pressed.emit(zone)
                self.zone_changed.emit(zone)
                self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self._pressed_zone >= 0:
            zone = self._get_zone_from_pos(event.pos())
            if zone >= 0 and zone != self._pressed_zone:
                self._pressed_zone = zone
                self._current_zone = zone
                self.zone_pressed.emit(zone)
                self.zone_changed.emit(zone)
                self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton and self._pressed_zone >= 0:
            self._pressed_zone = -1
            self.zone_released.emit()
            self.update()
        event.accept()
