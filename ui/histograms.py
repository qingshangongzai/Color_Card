# 第三方库导入
import math
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QMouseEvent
from PySide6.QtWidgets import QWidget

# 项目模块导入
from core import get_zone_bounds, HistogramService
from .theme_colors import (
    get_histogram_background_color, get_histogram_grid_color, get_histogram_axis_color,
    get_histogram_text_color, get_histogram_highlight_color, get_histogram_highlight_border_color,
    get_histogram_highlight_text_color, get_zone_colors, get_zone_colors_highlight,
    get_histogram_blue_color, get_histogram_green_color, get_histogram_red_color
)


class BaseHistogram(QWidget):
    """直方图基类，提供通用的直方图绘制功能
    
    功能：
        - 绘制柱状图
        - 支持数据归一化
        - 自定义颜色
        
    子类需要实现：
        - _draw_histogram(painter, x, y, width, height): 绘制直方图
        - _draw_custom_overlay(painter, x, y, width, height): 绘制自定义叠加内容
        - _draw_labels(painter, x, y, width, height): 绘制刻度标签
        
    信号：
        data_changed: 数据变化时发射（子类可扩展）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._histogram: List[int] = []
        self._max_count = 0
        self._scaling_mode = "linear"  # "linear" 或 "adaptive"
        self._is_loading = False  # 加载状态标志

        # 绘图边距
        self._margin_left = 35
        self._margin_right = 15
        self._margin_top = 15
        self._margin_bottom = 30

        # 背景色
        self._background_color = get_histogram_background_color()

    def set_loading(self, loading: bool):
        """设置加载状态

        Args:
            loading: True 显示加载提示，False 隐藏加载提示
        """
        self._is_loading = loading
        self.update()

    def _draw_loading_indicator(self, painter: QPainter):
        """绘制加载中提示"""
        if not self._is_loading:
            return

        # 计算绘制区域
        widget_width = self.width()
        widget_height = self.height()

        # 加载提示文字
        text = "加载中..."

        # 设置字体
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        # 计算文字尺寸
        text_rect = painter.fontMetrics().boundingRect(text)
        text_width = text_rect.width()
        text_height = text_rect.height()

        # 居中位置
        text_x = (widget_width - text_width) // 2
        text_y = (widget_height + text_height) // 2 - 5  # 微调垂直位置

        # 绘制文字（使用直方图文本颜色）
        text_color = get_histogram_text_color()
        painter.setPen(text_color)
        painter.drawText(text_x, text_y, text)

    def set_data(self, data: List[int]):
        """设置直方图数据
        
        Args:
            data: 长度为 256 的整数列表
        """
        self._histogram = data
        self._max_count = max(data) if data else 0
        self.update()
        
    def clear(self):
        """清空数据"""
        self._histogram = []
        self._max_count = 0
        self.update()

    def set_scaling_mode(self, mode: str):
        """设置直方图缩放模式

        Args:
            mode: "linear" 线性缩放，"adaptive" 自适应缩放（对数归一化）
        """
        if mode in ("linear", "adaptive"):
            self._scaling_mode = mode
            self.update()

    def _calculate_bar_height(self, count: int, max_count: int, height: int) -> float:
        """根据缩放模式计算柱子高度

        Args:
            count: 当前亮度值的像素数量
            max_count: 最大像素数量
            height: 绘图区域高度

        Returns:
            float: 柱子高度
        """
        if max_count == 0 or count == 0:
            return 0

        if self._scaling_mode == "linear":
            return (count / max_count) * height
        else:  # adaptive: 使用平方根缩放
            sqrt_max = math.sqrt(max_count)
            sqrt_count = math.sqrt(count)
            return (sqrt_count / sqrt_max) * height

    def paintEvent(self, event):
        """绘制直方图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景
        painter.fillRect(self.rect(), self._background_color)

        # 计算绘图区域
        draw_width = self.width() - self._margin_left - self._margin_right
        draw_height = self.height() - self._margin_top - self._margin_bottom

        if draw_width <= 0 or draw_height <= 0:
            return

        # 绘制直方图
        self._draw_histogram(painter, self._margin_left, self._margin_top, draw_width, draw_height)

        # 绘制自定义叠加内容
        self._draw_custom_overlay(painter, self._margin_left, self._margin_top, draw_width, draw_height)

        # 绘制刻度标签
        self._draw_labels(painter, self._margin_left, self._margin_top, draw_width, draw_height)

        # 绘制加载提示（如果有）
        self._draw_loading_indicator(painter)
        
    def _draw_histogram(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制直方图（子类必须实现）
        
        Args:
            painter: QPainter 对象
            x: 绘图区域左上角 X 坐标
            y: 绘图区域左上角 Y 坐标
            width: 绘图区域宽度
            height: 绘图区域高度
        """
        raise NotImplementedError("子类必须实现 _draw_histogram 方法")
        
    def _draw_custom_overlay(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制自定义叠加内容（子类重写）
        
        Args:
            painter: QPainter 对象
            x: 绘图区域左上角 X 坐标
            y: 绘图区域左上角 Y 坐标
            width: 绘图区域宽度
            height: 绘图区域高度
        """
        pass
        
    def _draw_labels(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制刻度标签（子类必须实现）
        
        Args:
            painter: QPainter 对象
            x: 绘图区域左上角 X 坐标
            y: 绘图区域左上角 Y 坐标
            width: 绘图区域宽度
            height: 绘图区域高度
        """
        raise NotImplementedError("子类必须实现 _draw_labels 方法")
        
    def _draw_bottom_baseline(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制底部基线（辅助方法）
        
        Args:
            painter: QPainter 对象
            x: 绘图区域左上角 X 坐标
            y: 绘图区域左上角 Y 坐标
            width: 绘图区域宽度
            height: 绘图区域高度
        """
        painter.setPen(QPen(get_histogram_grid_color(), 1))
        painter.drawLine(x, y + height, x + width, y + height)
        
    def _draw_max_label(self, painter: QPainter, x: int, y: int):
        """绘制左侧Y轴最大值标签（辅助方法）
        
        Args:
            painter: QPainter 对象
            x: 绘图区域左上角 X 坐标
            y: 绘图区域左上角 Y 坐标
        """
        if self._max_count > 0:
            painter.setPen(get_histogram_axis_color())
            font = QFont()
            font.setPointSize(7)
            painter.setFont(font)
            max_text = str(self._max_count)
            painter.drawText(5, y + 10, max_text)


class LuminanceHistogramWidget(BaseHistogram):
    """明度直方图组件 - 参考Lightroom风格设计，显示图片的明度分布和Zone分区"""
    zone_pressed = Signal(int)   # 信号：Zone被按下 (0-7)
    zone_released = Signal()     # 信号：Zone被释放
    zone_changed = Signal(int)   # 信号：当前Zone变化 (0-7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)
        bg_color = get_histogram_background_color()
        self.setStyleSheet(f"background-color: {bg_color.name()}; border-radius: 4px;")

        self._highlight_zones = []  # 高亮显示的区域列表
        self._pressed_zone = -1     # 当前按下的Zone
        self._current_zone = -1     # 当前选中的Zone

        # 启用鼠标跟踪
        self.setMouseTracking(True)

        # 创建直方图服务
        self._histogram_service = HistogramService(self)
        self._histogram_service.luminance_histogram_ready.connect(self._on_histogram_ready)
        self._histogram_service.error.connect(self._on_histogram_error)

    def set_image(self, image):
        """设置图片并异步计算直方图"""
        if image is None or image.isNull():
            self.clear()
            return
        self.set_loading(True)
        self._histogram_service.calculate_luminance_async(image)

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
        self._histogram_service.cancel_all()
        self.update()

    def _on_histogram_ready(self, histogram):
        """直方图计算完成回调"""
        self.set_loading(False)
        self.set_data(histogram)

    def _on_histogram_error(self, error_msg):
        """直方图计算错误回调"""
        print(f"明度直方图计算错误: {error_msg}")
        self.set_loading(False)
        self.clear()

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
        gradient.setColorAt(0, get_histogram_axis_color())
        gradient.setColorAt(1, get_histogram_text_color())

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)

        # 每个明度值对应的宽度
        bar_width = width / 256.0

        # 绘制直方图柱子
        for i in range(256):
            # 计算柱子高度 - 使用基类的计算方法
            bar_height = self._calculate_bar_height(self._histogram[i], self._max_count, height)

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

    def _draw_zone_background(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制Zone背景色块 - LR风格"""
        zone_width = width / 8.0

        # Zone颜色配置 - 使用更 subtle 的背景色
        # Adobe标准: 黑色(0-10%), 阴影(10-30%), 中间调(30-70%), 高光(70-90%), 白色(90-100%)
        zone_bg_colors = get_zone_colors()

        # 按下状态或选中状态的Zone背景色（更亮一些）
        zone_active_colors = get_zone_colors_highlight()

        for i in range(8):
            zone_x = x + i * zone_width

            # 如果是按下的Zone，使用高亮背景色
            if i == self._pressed_zone:
                bg_color = zone_active_colors[i]
            else:
                bg_color = zone_bg_colors[i]

            # 绘制Zone背景
            painter.fillRect(
                int(zone_x), y,
                int(zone_width + 0.5), height,
                bg_color
            )

            # 如果当前Zone被按下，绘制蓝色边框
            if i == self._pressed_zone:
                from .theme_colors import get_accent_color
                painter.setPen(QPen(get_accent_color(), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(int(zone_x), y, int(zone_width), height)

        # 绘制Zone分隔线
        pen = QPen(get_histogram_grid_color(), 1)
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
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(get_histogram_highlight_color())
            painter.drawRect(start_x, y, zone_width_px, height)

            # 绘制黄色边框
            painter.setPen(QPen(get_histogram_highlight_border_color(), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(start_x, y, zone_width_px, height)

            # 绘制区域编号文字
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)

            painter.setPen(get_histogram_highlight_text_color())

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
            painter.setPen(get_histogram_text_color())
            painter.drawLine(tick_x, y + height, tick_x, y + height + 4)

            # 绘制刻度值 (0-8)
            text = str(i)
            text_rect = painter.boundingRect(
                tick_x - 15, y + height + 6,
                30, 18,
                Qt.AlignmentFlag.AlignCenter, text
            )
            painter.setPen(get_histogram_axis_color())
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


class RGBHistogramWidget(BaseHistogram):
    """RGB直方图组件 - 显示图片的RGB三通道分布

    支持RGB通道切换功能，可以单独显示红色、绿色或蓝色通道，
    也可以同时显示三个通道。

    信号：
        display_mode_changed: 显示模式改变时发射，参数为新的模式字符串
    """

    # 显示模式改变信号
    display_mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setMaximumHeight(180)

        # RGB三通道数据
        self._histogram_r = [0] * 256
        self._histogram_g = [0] * 256
        self._histogram_b = [0] * 256

        # 显示模式："rgb"-显示全部通道, "r"-仅红色, "g"-仅绿色, "b"-仅蓝色
        self._display_mode = "rgb"

        # 调整边距以适应标题和图例
        self._margin_top = 25  # 顶部留空间给标题
        self._margin_right = 10

        # 通道按钮参数
        self._btn_size = 12  # 按钮尺寸 12x12
        self._btn_spacing = 4  # 按钮间距
        self._btn_margin_right = 10  # 距离右边距
        self._btn_margin_top = 5  # 距离顶部边距

        # 创建直方图服务
        self._histogram_service = HistogramService(self)
        self._histogram_service.rgb_histogram_ready.connect(self._on_histogram_ready)
        self._histogram_service.error.connect(self._on_histogram_error)

    def set_image(self, image):
        """设置图片并异步计算RGB直方图

        Args:
            image: QImage 对象
        """
        if image is None or image.isNull():
            self.clear()
            return
        self.set_loading(True)
        self._histogram_service.calculate_rgb_async(image)

    def _on_histogram_ready(self, r_hist, g_hist, b_hist):
        """RGB直方图计算完成回调"""
        self.set_loading(False)
        self._histogram_r = r_hist
        self._histogram_g = g_hist
        self._histogram_b = b_hist

        # 计算最大值用于归一化
        max_r = max(self._histogram_r) if self._histogram_r else 0
        max_g = max(self._histogram_g) if self._histogram_g else 0
        max_b = max(self._histogram_b) if self._histogram_b else 0
        self._max_count = max(max_r, max_g, max_b)
        self.update()

    def _on_histogram_error(self, error_msg):
        """直方图计算错误回调"""
        print(f"RGB直方图计算错误: {error_msg}")
        self.set_loading(False)
        self.clear()

    def clear(self):
        """清除直方图数据"""
        self._histogram_r = [0] * 256
        self._histogram_g = [0] * 256
        self._histogram_b = [0] * 256
        self._histogram_service.cancel_all()
        super().clear()

    def set_display_mode(self, mode: str):
        """设置RGB直方图的显示模式

        Args:
            mode: 显示模式，可选值为：
                - "rgb": 显示R、G、B三个通道（默认）
                - "r": 只显示红色通道
                - "g": 只显示绿色通道
                - "b": 只显示蓝色通道
        """
        if mode in ("rgb", "r", "g", "b") and mode != self._display_mode:
            self._display_mode = mode
            self.display_mode_changed.emit(mode)
            self.update()

    def _draw_histogram(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制RGB直方图

        根据当前显示模式绘制通道：
        - "rgb": 绘制R、G、B三个通道
        - "r": 只绘制红色通道
        - "g": 只绘制绿色通道
        - "b": 只绘制蓝色通道

        三条曲线叠加显示：R（红色）、G（绿色）、B（蓝色）
        """
        if self._max_count == 0:
            return

        # 每个亮度值对应的宽度
        bar_width = width / 256.0

        # 根据显示模式筛选要绘制的通道
        # 通道按顺序从后往前绘制，确保重叠区域可见
        channels = []
        if self._display_mode == "rgb":
            # 显示全部三个通道
            channels = [
                (self._histogram_b, get_histogram_blue_color(180)),   # 蓝色通道（最底层）
                (self._histogram_g, get_histogram_green_color(180)),  # 绿色通道
                (self._histogram_r, get_histogram_red_color(180)),    # 红色通道（最顶层）
            ]
        elif self._display_mode == "r":
            # 只显示红色通道
            channels = [(self._histogram_r, get_histogram_red_color(180))]
        elif self._display_mode == "g":
            # 只显示绿色通道
            channels = [(self._histogram_g, get_histogram_green_color(180))]
        elif self._display_mode == "b":
            # 只显示蓝色通道
            channels = [(self._histogram_b, get_histogram_blue_color(180))]

        for histogram, color in channels:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)

            # 绘制直方图柱子
            for i in range(256):
                # 计算柱子高度 - 使用基类的计算方法
                bar_height = self._calculate_bar_height(histogram[i], self._max_count, height)

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

    def _draw_custom_overlay(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制通道切换按钮"""
        self._draw_channel_buttons(painter)

    def _draw_channel_buttons(self, painter: QPainter):
        """绘制RGB通道切换按钮

        在直方图右上角绘制三个圆形按钮：
        - R：红色按钮
        - G：绿色按钮
        - B：蓝色按钮
        """
        # 获取颜色
        r_color = get_histogram_red_color()
        g_color = get_histogram_green_color()
        b_color = get_histogram_blue_color()

        # 计算按钮位置（从右往左排列）
        btn_y = self._btn_margin_top
        start_x = self.width() - self._btn_margin_right - self._btn_size

        # 绘制B按钮（最右边）
        btn_x_b = start_x
        self._draw_channel_button(painter, btn_x_b, btn_y, self._btn_size, b_color,
                                   self._display_mode == "b", "b")

        # 绘制G按钮（中间）
        btn_x_g = start_x - self._btn_size - self._btn_spacing
        self._draw_channel_button(painter, btn_x_g, btn_y, self._btn_size, g_color,
                                   self._display_mode == "g", "g")

        # 绘制R按钮（最左边）
        btn_x_r = start_x - 2 * (self._btn_size + self._btn_spacing)
        self._draw_channel_button(painter, btn_x_r, btn_y, self._btn_size, r_color,
                                   self._display_mode == "r", "r")

    def _draw_channel_button(self, painter: QPainter, x: int, y: int, size: int,
                              color: QColor, is_checked: bool, channel: str):
        """绘制单个通道按钮

        Args:
            painter: QPainter对象
            x: 按钮左上角X坐标
            y: 按钮左上角Y坐标
            size: 按钮尺寸
            color: 按钮颜色
            is_checked: 是否选中
            channel: 通道标识（"r"/"g"/"b"）
        """
        # 保存按钮位置用于点击检测
        if not hasattr(self, '_btn_rects'):
            self._btn_rects = {}
        self._btn_rects[channel] = (x, y, size, size)

        # 绘制圆形按钮
        center_x = x + size // 2
        center_y = y + size // 2
        radius = size // 2

        if is_checked:
            # 选中状态：实心圆
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(center_x - radius, center_y - radius,
                               size, size)
        else:
            # 未选中状态：空心圆
            pen = QPen(color, 1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center_x - radius, center_y - radius,
                               size, size)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件 - 检测按钮点击"""
        if not hasattr(self, '_btn_rects'):
            super().mousePressEvent(event)
            return

        pos = event.pos()
        clicked_channel = None

        # 检测点击了哪个按钮
        for channel, (x, y, w, h) in self._btn_rects.items():
            if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
                clicked_channel = channel
                break

        if clicked_channel:
            # 处理按钮点击
            self._handle_channel_button_click(clicked_channel)
            event.accept()
        else:
            # 点击非按钮区域，传递给父类
            super().mousePressEvent(event)

    def _handle_channel_button_click(self, channel: str):
        """处理通道按钮点击

        Args:
            channel: 点击的通道（"r"/"g"/"b"）
        """
        # 如果点击的是当前选中的通道，则取消选中（恢复全通道）
        if self._display_mode == channel:
            self.set_display_mode("rgb")
        else:
            # 切换到点击的通道
            self.set_display_mode(channel)

    def _draw_labels(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制刻度标签 - Zone 0-8 风格"""
        # 绘制标题
        self._draw_title(painter)

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        # 绘制底部刻度线和数值 - Zone 0 到 8
        zone_width = width / 8.0

        for i in range(9):  # 0, 1, 2, 3, 4, 5, 6, 7, 8
            tick_x = int(x + i * zone_width)

            # 绘制刻度线
            painter.setPen(get_histogram_text_color())
            painter.drawLine(tick_x, y + height, tick_x, y + height + 4)

            # 绘制刻度值 (0-8)
            text = str(i)
            text_rect = painter.boundingRect(
                tick_x - 15, y + height + 6,
                30, 18,
                Qt.AlignmentFlag.AlignCenter, text
            )
            painter.setPen(get_histogram_axis_color())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        # 绘制底部基线
        self._draw_bottom_baseline(painter, x, y, width, height)

        # 绘制左侧Y轴标签（最大值）
        self._draw_max_label(painter, x, y)

    def _draw_title(self, painter: QPainter):
        """绘制标题"""
        from .theme_colors import get_wheel_text_color
        painter.setPen(get_wheel_text_color())
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(10, 18, "RGB直方图")


class HueHistogramWidget(BaseHistogram):
    """色相分布直方图

    显示图片中各色相的像素分布，排除黑白灰（饱和度/亮度过低的颜色）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._histogram = [0] * 360  # 0-359 色相值
        self.setMinimumHeight(120)
        self.setMaximumHeight(180)

        # 调整边距
        self._margin_top = 25
        self._margin_right = 10

        # 创建直方图服务
        self._histogram_service = HistogramService(self)
        self._histogram_service.hue_histogram_ready.connect(self._on_histogram_ready)
        self._histogram_service.error.connect(self._on_histogram_error)

    def set_image(self, image):
        """计算并显示图片的色相分布

        Args:
            image: QImage 对象
        """
        if image is None or image.isNull():
            self.clear()
            return
        self.set_loading(True)
        self._histogram_service.calculate_hue_async(image)

    def _on_histogram_ready(self, histogram):
        """色相直方图计算完成回调"""
        self.set_loading(False)
        self._histogram = histogram
        self._max_count = max(self._histogram) if self._histogram else 1
        self.update()

    def _on_histogram_error(self, error_msg):
        """直方图计算错误回调"""
        print(f"色相直方图计算错误: {error_msg}")
        self.set_loading(False)
        self.clear()

    def clear(self):
        """清除直方图数据"""
        self._histogram = [0] * 360
        self._histogram_service.cancel_all()
        super().clear()

    def _draw_histogram(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制色相直方图

        使用彩虹色条显示0-360°色相分布
        """
        if self._max_count == 0:
            return

        bar_width = width / 360.0

        for hue, count in enumerate(self._histogram):
            bar_height = self._calculate_bar_height(count, self._max_count, height)

            if bar_height > 0:
                bar_x = x + hue * bar_width
                bar_y = y + height - bar_height

                # 计算柱子宽度
                if hue == 359:
                    current_bar_width = max(1, int(x + width - bar_x))
                else:
                    next_bar_x = x + (hue + 1) * bar_width
                    current_bar_width = max(1, int(next_bar_x - bar_x + 0.5))

                # 根据色相值计算颜色（固定饱和度和亮度）
                color = QColor.fromHsv(hue, 255, 255)
                painter.fillRect(int(bar_x), int(bar_y), current_bar_width, int(bar_height), color)

    def _draw_labels(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制刻度标签"""
        # 绘制标题
        self._draw_title(painter)

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        # 绘制底部刻度线 - 0°, 90°, 180°, 270°, 360°
        labels = [("0°", 0), ("90°", 90), ("180°", 180), ("270°", 270), ("360°", 360)]

        for label, hue in labels:
            tick_x = int(x + hue * width / 360.0)

            # 绘制刻度线
            painter.setPen(get_histogram_text_color())
            painter.drawLine(tick_x, y + height, tick_x, y + height + 4)

            # 绘制刻度值
            text_rect = painter.boundingRect(
                tick_x - 15, y + height + 6,
                30, 18,
                Qt.AlignmentFlag.AlignCenter, label
            )
            painter.setPen(get_histogram_axis_color())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

        # 绘制底部基线
        self._draw_bottom_baseline(painter, x, y, width, height)

        # 绘制左侧Y轴标签（最大值）
        self._draw_max_label(painter, x, y)

    def _draw_title(self, painter: QPainter):
        """绘制标题"""
        from .theme_colors import get_wheel_text_color
        painter.setPen(get_wheel_text_color())
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(10, 18, "色相分布")
