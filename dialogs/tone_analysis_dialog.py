"""明度分析对话框"""

import math
from typing import List, Optional

import numpy as np
import win32con
import win32gui
from PySide6.QtCharts import (
    QBarSeries, QBarSet, QChart, QChartView, QLineSeries,
    QPieSeries, QValueAxis
)
from PySide6.QtCore import QMargins, QThread, Signal, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import CardWidget, qconfig, StrongBodyLabel, BodyLabel, ScrollArea

from core import (
    ToneAnalysisService, ToneAnalysisResult, get_tone_analysis_cache, get_config_manager,
    get_histogram_cache
)
from dialogs import BaseFramelessDialog
from utils import tr
from utils.theme_colors import (
    get_text_color,
    get_tone_chart_text_color,
    get_tone_chart_bar_color,
    get_tone_chart_mean_line_color, get_tone_chart_median_line_color
)


class AnalysisWorker(QThread):
    """分析工作线程"""
    analysis_complete = Signal(object, object, object)  # result, gray, img_array

    def __init__(self, img_array: np.ndarray, service: ToneAnalysisService):
        super().__init__()
        self._img_array = img_array
        self._service = service

    def run(self):
        """执行分析"""
        result = self._service.analyze_from_array(self._img_array)
        gray = self._service.get_gray_image(self._img_array)
        self.analysis_complete.emit(result, gray, self._img_array)


class ImageDisplayWidget(QWidget):
    """图片显示组件"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # 原图标签
        self._original_label = QLabel()
        self._original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._original_label.setStyleSheet("background: transparent;")
        self._original_label.setMinimumSize(200, 200)

        # 灰度图标签
        self._grayscale_label = QLabel()
        self._grayscale_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grayscale_label.setStyleSheet("background: transparent;")
        self._grayscale_label.setMinimumSize(200, 200)

        layout.addWidget(self._original_label)
        layout.addWidget(self._grayscale_label)

        # 保存原始图片数据用于重绘
        self._img_rgb: Optional[np.ndarray] = None
        self._gray: Optional[np.ndarray] = None

    def set_images(self, img_rgb: np.ndarray, gray: np.ndarray) -> None:
        """设置图片"""
        self._img_rgb = img_rgb
        self._gray = gray
        self._update_display()

    def _update_display(self) -> None:
        """根据当前大小更新图片显示"""
        if self._img_rgb is None or self._gray is None:
            return

        h, w = self._img_rgb.shape[:2]

        # 计算可用显示空间（减去间距和边距）
        available_width = (self.width() - 30) // 2
        available_height = self.height() - 20
        display_size = min(available_width, available_height, 280)
        display_size = max(display_size, 100)  # 最小显示尺寸

        # 原图
        q_image = QImage(self._img_rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image).scaled(
            display_size, display_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._original_label.setPixmap(pixmap)

        # 灰度图
        gray_q_image = QImage(self._gray.data, w, h, w, QImage.Format.Format_Grayscale8)
        gray_pixmap = QPixmap.fromImage(gray_q_image).scaled(
            display_size, display_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._grayscale_label.setPixmap(gray_pixmap)

    def resizeEvent(self, event) -> None:
        """窗口大小变化时重新显示图片"""
        super().resizeEvent(event)
        self._update_display()


class PieChartWidget(QWidget):
    """QtCharts 饼图组件"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建图表
        self._chart = QChart()
        self._chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self._chart.legend().setVisible(False)  # 隐藏默认图例
        self._chart.setMargins(QMargins(0, 0, 0, 0))
        self._chart.setBackgroundRoundness(0)
        self._chart.setBackgroundVisible(False)

        # 创建图表视图
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumSize(200, 200)
        self._chart_view.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(self._chart_view, stretch=1)

        # 创建自定义图例区域
        self._legend_widget = QWidget(self)
        legend_layout = QHBoxLayout(self._legend_widget)
        legend_layout.setSpacing(20)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._legend_widget)

    def set_data(self, labels: list, values: list, colors: list, title: str = "") -> None:
        """设置饼图数据

        Args:
            labels: 标签列表
            values: 数值列表
            colors: 颜色列表 (十六进制字符串)
            title: 图表标题
        """
        self._chart.removeAllSeries()

        # 清除旧图例
        while self._legend_widget.layout().count():
            item = self._legend_widget.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 创建饼图系列
        series = QPieSeries()
        series.setHoleSize(0.0)  # 实心饼图
        series.setPieSize(0.95)  # 饼图占图表区域的比例

        for i, (label, value, color) in enumerate(zip(labels, values, colors)):
            slice_item = series.append(label, value)
            slice_item.setColor(QColor(color))
            slice_item.setBorderColor(QColor("transparent"))
            slice_item.setLabelVisible(False)  # 不显示标签

        self._chart.addSeries(series)
        self._chart.setTitle(title)

        # 添加自定义图例
        for i, (label, value, color) in enumerate(zip(labels, values, colors)):
            legend_item = self._create_legend_item(label, value, color)
            self._legend_widget.layout().addWidget(legend_item)

        # 更新主题颜色
        self._update_theme_colors()

    def _create_legend_item(self, label: str, value: float, color: str) -> QWidget:
        """创建图例项"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # 颜色圆圈
        color_label = QLabel()
        color_label.setFixedSize(12, 12)
        color_label.setStyleSheet(f"background-color: {color}; border-radius: 6px;")

        # 文字标签
        text_label = QLabel(f"{label}: {value:.1f}%")
        text_label.setStyleSheet("font-size: 12px;")

        layout.addWidget(color_label)
        layout.addWidget(text_label)

        return widget

    def _update_theme_colors(self) -> None:
        """更新主题颜色"""
        text_color = get_tone_chart_text_color()

        self._chart.setTitleBrush(QColor(text_color.name()))

        # 更新图例文字颜色
        text_hex = text_color.name()
        for i in range(self._legend_widget.layout().count()):
            item = self._legend_widget.layout().itemAt(i)
            if item and item.widget():
                labels = item.widget().findChildren(QLabel)
                for lbl in labels:
                    if lbl.text():  # 文字标签有内容
                        lbl.setStyleSheet(f"color: {text_hex}; font-size: 12px;")


class HistogramWidget(QWidget):
    """直方图组件，支持线连接和柱状图两种显示模式，支持缩放模式切换"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._histogram_style = "bar"  # "line" 或 "bar"
        self._scaling_mode = "adaptive"  # "linear" 或 "adaptive"
        self._hist_data: Optional[np.ndarray] = None
        self._result_data: Optional[ToneAnalysisResult] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建图表
        self._chart = QChart()
        self._chart.legend().setVisible(True)
        self._chart.legend().setAlignment(Qt.AlignmentFlag.AlignTop)
        self._chart.setBackgroundVisible(False)

        # 图表视图
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._chart_view)

    def set_histogram_style(self, style: str) -> None:
        """设置直方图显示样式

        Args:
            style: 样式类型，"line" 为线连接，"bar" 为柱状图

        Raises:
            ValueError: 当样式类型无效时
        """
        if style not in ("line", "bar"):
            raise ValueError(f"无效的直方图样式: {style}")

        if style != self._histogram_style:
            self._histogram_style = style
            # 如有数据，重新绘制
            if self._hist_data is not None and self._result_data is not None:
                self.set_histogram(self._hist_data, self._result_data)

    def set_scaling_mode(self, mode: str) -> None:
        """设置直方图缩放模式

        Args:
            mode: "linear" 线性缩放，"adaptive" 自适应缩放

        Raises:
            ValueError: 当模式类型无效时
        """
        if mode not in ("linear", "adaptive"):
            raise ValueError(f"无效的缩放模式: {mode}")

        if mode != self._scaling_mode:
            self._scaling_mode = mode
            # 如有数据，重新绘制
            if self._hist_data is not None and self._result_data is not None:
                self.set_histogram(self._hist_data, self._result_data)

    def set_histogram(self, hist: np.ndarray, result: ToneAnalysisResult) -> None:
        """设置直方图数据

        Args:
            hist: 直方图数据
            result: 分析结果
        """
        # 保存数据用于样式切换时重绘
        self._hist_data = hist
        self._result_data = result

        self._chart.removeAllSeries()

        # 计算原始数据
        bar_values = [float(hist[i]) for i in range(256)]

        # 应用缩放模式
        scaled_values = self._apply_scaling(bar_values)
        max_value = max(scaled_values)

        # 创建X轴（均匀九段分区）
        axis_x = QValueAxis()
        axis_x.setRange(0, 256)
        axis_x.setTickCount(10)  # 10个刻度 = 9段
        axis_x.setLabelFormat("%d")
        axis_x.setTitleText("")

        axis_y = QValueAxis()
        axis_y.setTitleText("")

        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        # 根据样式绘制直方图
        if self._histogram_style == "line":
            self._create_line_series(scaled_values, max_value, axis_x, axis_y)
        else:
            self._create_bar_series(scaled_values, max_value, axis_x, axis_y)

        # 添加参考线（使用缩放后的最大值）
        self._add_reference_lines(result, max_value, axis_x, axis_y)

        # 更新主题颜色
        self._update_theme_colors()

    def _create_bar_series(self, bar_values: List[float], max_value: float,
                           axis_x: QValueAxis, axis_y: QValueAxis) -> QBarSeries:
        """创建柱状图系列

        Args:
            bar_values: 柱状图数据值列表
            max_value: 最大值
            axis_x: X轴
            axis_y: Y轴

        Returns:
            QBarSeries: 柱状图系列
        """
        bar_series = QBarSeries()
        bar_set = QBarSet("")

        for value in bar_values:
            bar_set.append(value)

        bar_series.append(bar_set)
        bar_series.setName("")
        self._chart.addSeries(bar_series)

        # 设置柱状图颜色
        bar_color = get_tone_chart_bar_color()
        bar_set.setColor(QColor(bar_color.name()))
        bar_set.setBorderColor(QColor(bar_color.name()))

        bar_series.attachAxis(axis_x)
        bar_series.attachAxis(axis_y)

        # 隐藏柱状图系列的图例项
        self._chart.legend().markers(bar_series)[0].setVisible(False)

        return bar_series

    def _create_line_series(self, bar_values: List[float], max_value: float,
                            axis_x: QValueAxis, axis_y: QValueAxis) -> QLineSeries:
        """创建线连接系列

        Args:
            bar_values: 数据值列表
            max_value: 最大值
            axis_x: X轴
            axis_y: Y轴

        Returns:
            QLineSeries: 线连接系列
        """
        line_series = QLineSeries()
        line_series.setName("")

        # 添加数据点
        for i, value in enumerate(bar_values):
            line_series.append(i, value)

        self._chart.addSeries(line_series)

        # 设置线条颜色
        line_color = get_tone_chart_bar_color()
        line_series.setPen(QPen(QColor(line_color.name()), 1.5))

        line_series.attachAxis(axis_x)
        line_series.attachAxis(axis_y)

        # 隐藏线系列的图例项
        self._chart.legend().markers(line_series)[0].setVisible(False)

        return line_series

    def _apply_scaling(self, values: List[float]) -> List[float]:
        """应用缩放模式到数据

        Args:
            values: 原始数据值列表

        Returns:
            List[float]: 缩放后的数据值列表
        """
        if self._scaling_mode == "linear":
            return values

        # adaptive: 自适应缩放
        max_value = max(values)
        if max_value == 0:
            return values

        # 计算CV值
        cv = self._calculate_cv(values)

        scaled_values = []
        for value in values:
            if value == 0:
                scaled_values.append(0)
                continue

            if cv < 0.8:
                # 分布平坦：线性缩放
                normalized = value / max_value
            elif cv > 2.0:
                # 分布集中：平方根缩放
                normalized = math.sqrt(value) / math.sqrt(max_value)
            else:
                # 中间态：动态指数
                t = (cv - 0.8) / (2.0 - 0.8)
                exponent = 0.75 - t * 0.2
                normalized = (value / max_value) ** exponent

            scaled_values.append(normalized * max_value)

        return scaled_values

    def _calculate_cv(self, values: List[float]) -> float:
        """计算变异系数（CV）

        CV = 标准差 / 平均值
        用于衡量数据分布的离散程度

        Args:
            values: 数据值列表

        Returns:
            float: 变异系数
        """
        non_zero = [v for v in values if v > 0]
        if len(non_zero) < 2:
            return 0.0

        mean_val = sum(non_zero) / len(non_zero)
        if mean_val == 0:
            return 0.0

        variance = sum((x - mean_val) ** 2 for x in non_zero) / len(non_zero)
        return math.sqrt(variance) / mean_val

    def _add_reference_lines(self, result: ToneAnalysisResult, max_value: float,
                             axis_x: QValueAxis, axis_y: QValueAxis) -> None:
        """添加均值和中位数参考线

        Args:
            result: 分析结果
            max_value: 最大值
            axis_x: X轴
            axis_y: Y轴
        """
        # 添加均值参考线
        mean_line = QLineSeries()
        mean_line.setName(f'{tr("tone_analysis.mean_brightness")}: {result.mean:.1f}')
        mean_color = get_tone_chart_mean_line_color()
        mean_line.setPen(QPen(QColor(mean_color.name()), 2))

        mean_index = int(result.mean)
        mean_line.append(mean_index, 0)
        mean_line.append(mean_index, max_value * 1.1)

        self._chart.addSeries(mean_line)
        mean_line.attachAxis(axis_x)
        mean_line.attachAxis(axis_y)

        # 添加中位数参考线
        median_line = QLineSeries()
        median_line.setName(f'{tr("tone_analysis.median")}: {result.median:.1f}')
        median_color = get_tone_chart_median_line_color()
        median_line.setPen(QPen(QColor(median_color.name()), 2))

        median_index = int(result.median)
        median_line.append(median_index, 0)
        median_line.append(median_index, max_value * 1.1)

        self._chart.addSeries(median_line)
        median_line.attachAxis(axis_x)
        median_line.attachAxis(axis_y)

    def _update_theme_colors(self) -> None:
        """更新主题颜色"""
        text_color = get_tone_chart_text_color()

        self._chart.setTitleBrush(QColor(text_color.name()))

        # 更新坐标轴颜色
        for axis in self._chart.axes():
            axis.setLabelsColor(QColor(text_color.name()))
            axis.setTitleBrush(QColor(text_color.name()))

        # 更新图例颜色
        self._chart.legend().setLabelColor(QColor(text_color.name()))


class ChartsWidget(QWidget):
    """Qt 图表组件（替代 MatplotlibWidget）"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 顶部区域：原图 + 灰度图 + 饼图
        top_widget = QWidget()
        top_widget.setMinimumHeight(200)
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        self._image_display = ImageDisplayWidget()
        self._pie_chart = PieChartWidget()

        top_layout.addWidget(self._image_display, stretch=1)
        top_layout.addWidget(self._pie_chart, stretch=1)

        layout.addWidget(top_widget)

        # 底部：直方图
        self._histogram = HistogramWidget()
        self._histogram.setMinimumHeight(250)
        layout.addWidget(self._histogram, stretch=1)

    def set_histogram_style(self, style: str) -> None:
        """设置直方图显示样式

        Args:
            style: 样式类型，"line" 或 "bar"
        """
        self._histogram.set_histogram_style(style)

    def set_scaling_mode(self, mode: str) -> None:
        """设置直方图缩放模式

        Args:
            mode: 缩放模式，"linear" 或 "adaptive"
        """
        self._histogram.set_scaling_mode(mode)

    def display_analysis(self, img_rgb: np.ndarray, gray: np.ndarray,
                         hist: np.ndarray, result: ToneAnalysisResult) -> None:
        """显示分析结果

        Args:
            img_rgb: RGB 图片数组
            gray: 灰度数组
            hist: 直方图数据
            result: 分析结果
        """
        self._image_display.set_images(img_rgb, gray)

        labels = [
            tr('tone_analysis.shadows'),
            tr('tone_analysis.midtones'),
            tr('tone_analysis.highlights')
        ]
        values = [result.shadows, result.midtones, result.highlights]
        colors = ['#4a90d9', '#51cf66', '#ffd93d']
        self._pie_chart.set_data(labels, values, colors, "")

        self._histogram.set_histogram(hist, result)

    def update_theme(self) -> None:
        """更新主题"""
        self._pie_chart._update_theme_colors()
        self._histogram._update_theme_colors()


class StatCard(CardWidget):
    """统计信息卡片"""

    def __init__(self, title: str, value: str, parent: Optional[QWidget] = None,
                 hint: str = ""):
        super().__init__(parent)
        self._title = title
        self._value = value
        self._hint = hint

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self._title_label = BodyLabel(self)
        layout.addWidget(self._title_label)

        self._value_label = StrongBodyLabel(value, self)
        layout.addWidget(self._value_label)

        self._update_styles()

    def _update_styles(self) -> None:
        """更新样式"""
        text_color = get_text_color()
        secondary_color = get_text_color(secondary=True)

        # 设置标题文本（带提示文本时使用小字体）
        if self._hint:
            self._title_label.setText(
                f'<span style="color: {secondary_color.name()};">{self._title}</span>'
                f'<span style="color: {secondary_color.name()}; font-size: 11px;"> {self._hint}</span>'
            )
        else:
            self._title_label.setText(self._title)
            self._title_label.setStyleSheet(f"color: {secondary_color.name()};")

        self._value_label.setStyleSheet(f"color: {text_color.name()};")


class ToneAnalysisDialog(BaseFramelessDialog):
    """明度分析对话框"""

    def __init__(self, img_array: Optional[np.ndarray], image_key: Optional[str] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._img_array = img_array
        self._image_key = image_key
        self._service = ToneAnalysisService()
        self._worker: Optional[AnalysisWorker] = None

        self.setWindowTitle(tr('tone_analysis.dialog_title'))
        self.setMinimumSize(900, 600)
        self.resize(1100, 750)

        # 显示标题栏的最大化和最小化按钮（FramelessDialog默认隐藏）
        self.titleBar.minBtn.show()
        self.titleBar.maxBtn.show()
        self.titleBar.setDoubleClickEnabled(True)

        # 恢复Win32最大化按钮样式（FramelessDialog初始化时禁用了）
        hWnd = int(self.winId())
        style = win32gui.GetWindowLong(hWnd, win32con.GWL_STYLE)
        win32gui.SetWindowLong(hWnd, win32con.GWL_STYLE, style | win32con.WS_MAXIMIZEBOX)

        self._setup_title_bar()
        self._setup_ui()
        self._update_styles()

        self._theme_connection = qconfig.themeChangedFinished.connect(self._on_theme_changed)

        # 如果图片已提供，自动开始分析
        if self._img_array is not None:
            self.start_analysis()

    def _setup_ui(self) -> None:
        """设置界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 40, 20, 10)
        main_layout.setSpacing(8)

        # 创建滚动区域
        self._scroll_area = ScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(ScrollArea.Shape.NoFrame)

        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # 加载中标签
        self._loading_label = BodyLabel(tr('tone_analysis.loading'), self)
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self._loading_label)

        # Qt 图表组件（初始隐藏）
        self._charts_widget = ChartsWidget(self)
        self._charts_widget.hide()
        content_layout.addWidget(self._charts_widget, stretch=1)

        # 统计卡片区域（初始隐藏）
        self._stats_widget = QWidget(self)
        self._stats_widget.hide()
        stats_layout = QGridLayout(self._stats_widget)
        stats_layout.setSpacing(12)

        self._stat_cards = []
        content_layout.addWidget(self._stats_widget)

        self._scroll_area.setWidget(content_widget)
        main_layout.addWidget(self._scroll_area)

    def start_analysis(self) -> None:
        """开始分析"""
        # 如果有缓存键，先尝试从缓存获取
        if self._image_key:
            # 首先尝试从 ToneAnalysisCache 获取完整结果
            cache = get_tone_analysis_cache()
            cached_result = cache.get(self._image_key)
            if cached_result is not None:
                # 使用缓存结果直接显示
                gray = self._service.get_gray_image(self._img_array)
                self._display_result(cached_result, gray, self._img_array)
                return

            # 尝试从 HistogramCache 获取直方图数据快速构建结果
            histogram_cache = get_histogram_cache()
            cached_data = histogram_cache.get_with_metadata(self._image_key, "luminance")
            if cached_data is not None and 'mean' in cached_data['metadata']:
                self._quick_analysis_from_histogram(cached_data)
                return

        # 没有缓存，启动线程计算
        self._worker = AnalysisWorker(self._img_array, self._service)
        self._worker.analysis_complete.connect(self._on_analysis_complete)
        self._worker.start()

    def _quick_analysis_from_histogram(self, cached_data: dict) -> None:
        """从直方图缓存快速分析

        利用 HistogramCache 中的直方图和统计信息快速构建分析结果，
        避免重复的 QImage→NumPy 转换和计算。

        Args:
            cached_data: 缓存数据，包含 histogram 和 metadata
        """
        histogram = np.array(cached_data['histogram'])
        metadata = cached_data['metadata']

        # 从元数据获取统计信息
        mean = metadata.get('mean', 0.0)
        median = metadata.get('median', 0.0)
        std = metadata.get('std', 0.0)
        min_val = metadata.get('min_val', 0)
        max_val = metadata.get('max_val', 0)

        # 使用 analyze_from_histogram 快速构建结果
        result = self._service.analyze_from_histogram(
            histogram=histogram,
            mean=mean,
            median=median,
            std=std,
            min_val=min_val,
            max_val=max_val
        )

        # 计算灰度图用于显示
        gray = self._service.get_gray_image(self._img_array)

        # 存入 ToneAnalysisCache 供下次使用
        cache = get_tone_analysis_cache()
        cache.set(self._image_key, result)

        # 显示结果
        self._display_result(result, gray, self._img_array)

    def _on_analysis_complete(self, result: ToneAnalysisResult, gray: np.ndarray, img_array: np.ndarray) -> None:
        """分析完成回调

        Args:
            result: 分析结果
            gray: 灰度数组
            img_array: 图片数组
        """
        # 存入缓存
        if self._image_key:
            cache = get_tone_analysis_cache()
            cache.set(self._image_key, result)

        self._display_result(result, gray, img_array)

        if self._worker:
            self._worker.deleteLater()
            self._worker = None

    def _display_result(self, result: ToneAnalysisResult, gray: np.ndarray, img_array: np.ndarray) -> None:
        """显示分析结果

        Args:
            result: 分析结果
            gray: 灰度数组
            img_array: 图片数组
        """
        self._loading_label.hide()

        # 应用当前直方图样式设置
        config_manager = get_config_manager()
        histogram_style = config_manager.get('settings.luminance_histogram_style', 'line')
        self._charts_widget.set_histogram_style(histogram_style)

        # 应用当前直方图缩放模式设置
        scaling_mode = config_manager.get('settings.histogram_scaling_mode', 'adaptive')
        self._charts_widget.set_scaling_mode(scaling_mode)

        self._charts_widget.display_analysis(
            img_array, gray, result.histogram, result
        )
        self._charts_widget.show()

        self._create_stat_cards(result)
        self._stats_widget.show()

    def _create_stat_cards(self, result: ToneAnalysisResult) -> None:
        """创建统计卡片

        Args:
            result: 分析结果
        """
        for card in self._stat_cards:
            card.deleteLater()
        self._stat_cards.clear()

        stats_layout = self._stats_widget.layout()

        # 获取影调类型的本地化名称（带置信度描述）
        tone_type_display = self._get_tone_type_display(result)

        stats = [
            (tr('tone_analysis.tone_type'), tone_type_display, tr('tone_analysis.tone_type_hint')),
            (tr('tone_analysis.mean_brightness'), f'{result.mean:.1f}', ""),
            (tr('tone_analysis.median'), f'{result.median:.1f}', ""),
            (tr('tone_analysis.std_deviation'), f'{result.std:.1f}', ""),
            (tr('tone_analysis.brightness_range'), f'{result.min_val} - {result.max_val}', ""),
            (tr('tone_analysis.shadows'), f'{result.shadows:.1f}%', ""),
            (tr('tone_analysis.midtones'), f'{result.midtones:.1f}%', ""),
            (tr('tone_analysis.highlights'), f'{result.highlights:.1f}%', ""),
        ]

        columns = 4
        for i, (title, value, hint) in enumerate(stats):
            row = i // columns
            col = i % columns
            card = StatCard(title, value, self._stats_widget, hint)
            stats_layout.addWidget(card, row, col)
            self._stat_cards.append(card)

    def _get_tone_type_display(self, result: ToneAnalysisResult) -> str:
        """获取影调类型的显示文本（含置信度描述）

        Args:
            result: 分析结果

        Returns:
            str: 影调类型显示文本
        """
        # 计算综合置信度
        avg_confidence = (result.tone_key_confidence + result.tone_range_confidence) / 2

        # 获取基础影调名称
        tone_type_key = f'tone_analysis.tone_types.{result.tone_key.value}_{result.tone_range.value}'
        base_name = tr(tone_type_key)

        # 根据置信度决定显示格式
        if avg_confidence >= 0.8:
            # 高置信度：直接显示分类
            return base_name
        elif avg_confidence >= 0.5:
            # 中等置信度：显示置信度百分比
            return f'{base_name} ({int(avg_confidence * 100)}%)'
        else:
            # 低置信度：显示过渡描述
            return self._get_transition_description(result, avg_confidence)

    def _get_transition_description(self, result: ToneAnalysisResult, confidence: float) -> str:
        """获取过渡区域描述

        Args:
            result: 分析结果
            confidence: 综合置信度

        Returns:
            str: 过渡描述文本
        """
        # 获取相邻的基调/跨度描述
        key_alternatives = []
        range_alternatives = []

        # 基调过渡描述
        if result.tone_key_confidence < 0.6:
            if result.tone_key.value == 'high':
                key_alternatives.append(tr('tone_analysis.tone_key.mid'))
            elif result.tone_key.value == 'low':
                key_alternatives.append(tr('tone_analysis.tone_key.mid'))
            else:  # mid
                if result.peak_position < 128:
                    key_alternatives.append(tr('tone_analysis.tone_key.low'))
                else:
                    key_alternatives.append(tr('tone_analysis.tone_key.high'))

        # 跨度过渡描述
        if result.tone_range_confidence < 0.6:
            if result.tone_range.value == 'long':
                range_alternatives.append(tr('tone_analysis.tone_range.medium'))
            elif result.tone_range.value == 'short':
                range_alternatives.append(tr('tone_analysis.tone_range.medium'))
            else:  # medium
                # 根据实际spread判断倾向
                spread = result.max_val - result.min_val
                mid_point = (180 + 100) / 2
                if spread < mid_point:
                    range_alternatives.append(tr('tone_analysis.tone_range.short'))
                else:
                    range_alternatives.append(tr('tone_analysis.tone_range.long'))

        # 构建过渡描述
        parts = []
        base_key = tr(f'tone_analysis.tone_key.{result.tone_key.value}')
        base_range = tr(f'tone_analysis.tone_range.{result.tone_range.value}')
        parts.append(f'{base_key}{base_range}')

        if key_alternatives:
            parts.append(f'/{key_alternatives[0]}')
        if range_alternatives:
            parts.append(f'·{range_alternatives[0]}')

        return ''.join(parts)

    def _on_theme_changed(self) -> None:
        """主题变化回调"""
        self._update_styles()
        self._charts_widget.update_theme()
        for card in self._stat_cards:
            card._update_styles()

    def _update_styles(self) -> None:
        """更新样式"""
        super()._update_styles()
        self._scroll_area.setStyleSheet("background: transparent; border: none;")

    def closeEvent(self, event) -> None:
        """关闭事件"""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)
        super().closeEvent(event)
