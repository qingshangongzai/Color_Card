"""明度分析对话框"""

from __future__ import annotations

import math
import sys


import numpy as np
from PySide6.QtCharts import (
    QBarSeries, QBarSet, QChart, QChartView, QLineSeries,
    QPieSeries, QValueAxis
)
from PySide6.QtCore import QMargins, QRectF, QThread, Signal, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
)
from qfluentwidgets import CardWidget, qconfig, StrongBodyLabel, BodyLabel

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

    def __init__(self, img_array: np.ndarray, service: ToneAnalysisService, sample_step: int = 2):
        super().__init__()
        self._img_array = img_array
        self._service = service
        self._sample_step = sample_step

    def run(self):
        """执行分析"""
        result = self._service.analyze_from_array(self._img_array, self._sample_step)
        gray = self._service.get_gray_image(self._img_array)
        self.analysis_complete.emit(result, gray, self._img_array)


class ImageDisplayWidget(QWidget):
    """图片显示组件"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # 原图标签
        self._original_label = QLabel()
        self._original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._original_label.setStyleSheet("background: transparent;")
        self._original_label.setMinimumSize(100, 100)

        # 灰度图标签
        self._grayscale_label = QLabel()
        self._grayscale_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grayscale_label.setStyleSheet("background: transparent;")
        self._grayscale_label.setMinimumSize(100, 100)

        layout.addWidget(self._original_label)
        layout.addWidget(self._grayscale_label)

        # 保存原始图片数据用于重绘
        self._img_rgb: np.ndarray | None = None
        self._gray: np.ndarray | None = None

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
        display_size = min(available_width, available_height)
        display_size = max(display_size, 100)

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

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建图表
        self._chart = QChart()
        self._chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self._chart.legend().setVisible(False)
        self._chart.setMargins(QMargins(0, 0, 0, 0))
        self._chart.setBackgroundRoundness(0)
        self._chart.setBackgroundVisible(False)

        # 创建图表视图
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumSize(120, 120)
        self._chart_view.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
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


class HistogramChartView(QChartView):
    """自定义图表视图，支持自定义Y轴刻度标签"""

    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)
        self._max_value: float = 0.0
        self._cv: float = 0.0
        self._scaling_mode: str = "linear"

    def set_scale_params(self, max_value: float, cv: float, scaling_mode: str) -> None:
        """设置缩放参数

        Args:
            max_value: 真实最大值
            cv: 变异系数
            scaling_mode: 缩放模式
        """
        self._max_value = max_value
        self._cv = cv
        self._scaling_mode = scaling_mode

    def _inverse_scale(self, normalized: float) -> float:
        """反向缩放：从归一化值计算真实值"""
        if self._max_value == 0:
            return 0.0

        if self._scaling_mode == "linear" or self._cv < 0.8:
            return normalized * self._max_value
        elif self._cv > 2.0:
            return (normalized ** 2) * self._max_value
        else:
            t = (self._cv - 0.8) / (2.0 - 0.8)
            exponent = 0.75 - t * 0.2
            return (normalized ** (1.0 / exponent)) * self._max_value

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """绘制前景（自定义Y轴刻度标签）"""
        super().drawForeground(painter, rect)

        if self._max_value == 0:
            return

        # 获取Y轴
        axes = self.chart().axes(Qt.Orientation.Vertical)
        if not axes:
            return

        # 获取图表的绘图区域
        plot_area = self.chart().plotArea()

        # 设置字体
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        # 获取文本颜色
        text_color = get_tone_chart_text_color()
        painter.setPen(text_color)

        # 绘制Y轴刻度标签
        tick_values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        for tick in tick_values:
            # 计算Y坐标（从底部向上）
            y = plot_area.bottom() - tick * plot_area.height()

            # 计算真实值
            real_value = self._inverse_scale(tick)

            # 格式化标签：显示完整数字，使用千分位分隔
            if real_value >= 1000:
                label = f"{int(real_value):,}"
            else:
                label = f"{int(real_value)}"

            # 计算文本宽度，右对齐
            text_rect = painter.fontMetrics().boundingRect(label)
            x = int(plot_area.left() - text_rect.width() - 5)

            # 绘制标签（在Y轴左侧，右对齐）
            painter.drawText(x, int(y + 4), label)


class HistogramWidget(QWidget):
    """直方图组件，支持线连接和柱状图两种显示模式，支持缩放模式切换"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._histogram_style = "bar"  # "line" 或 "bar"
        self._scaling_mode = "adaptive"  # "linear" 或 "adaptive"
        self._hist_data: np.ndarray | None = None
        self._result_data: ToneAnalysisResult | None = None
        self._cv: float = 0.0  # 变异系数

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建图表
        self._chart = QChart()
        self._chart.legend().setVisible(True)
        self._chart.legend().setAlignment(Qt.AlignmentFlag.AlignTop)
        self._chart.setBackgroundVisible(False)
        self._chart.layout().setContentsMargins(0, 0, 0, 0)
        # 增加左边距，为Y轴标签留出空间
        self._chart.setMargins(QMargins(50, 0, 0, 0))

        # 使用自定义图表视图（支持自定义Y轴刻度标签）
        self._chart_view = HistogramChartView(self._chart)
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
        max_value = max(bar_values)

        # 计算CV值（用于自适应缩放）
        self._cv = self._calculate_cv(bar_values)

        # 应用缩放模式，获取归一化比例(0-1)
        normalized_values = self._apply_scaling(bar_values)

        # 创建X轴（均匀九段分区）
        axis_x = QValueAxis()
        axis_x.setRange(0, 255)
        axis_x.setTickCount(10)  # 10个刻度 = 9段
        axis_x.setLabelFormat("%d")
        axis_x.setTitleText("")

        # 创建Y轴，范围0-1（归一化），刻度标签显示真实值
        axis_y = QValueAxis()
        axis_y.setRange(0, 1.0)
        axis_y.setTickCount(6)  # 6个刻度点
        axis_y.setTitleText("")
        # 隐藏原始刻度标签，使用自定义绘制
        axis_y.setLabelsVisible(False)

        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        # 设置自定义图表视图的缩放参数
        self._chart_view.set_scale_params(max_value, self._cv, self._scaling_mode)

        # 根据样式绘制直方图（使用归一化比例）
        if self._histogram_style == "line":
            self._create_line_series(normalized_values, axis_x, axis_y)
        else:
            self._create_bar_series(normalized_values, axis_x, axis_y)

        # 添加参考线（使用归一化比例）
        self._add_reference_lines_normalized(result, axis_x, axis_y)

        # 更新主题颜色
        self._update_theme_colors()

    def _create_bar_series(self, normalized_values: list[float],
                           axis_x: QValueAxis, axis_y: QValueAxis) -> QBarSeries:
        """创建柱状图系列

        Args:
            normalized_values: 归一化比例列表(0-1)
            axis_x: X轴
            axis_y: Y轴

        Returns:
            QBarSeries: 柱状图系列
        """
        bar_series = QBarSeries()
        bar_set = QBarSet("")

        # 直接使用归一化比例作为Y值
        for ratio in normalized_values:
            bar_set.append(ratio)

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

    def _create_line_series(self, normalized_values: list[float],
                            axis_x: QValueAxis, axis_y: QValueAxis) -> QLineSeries:
        """创建线连接系列

        Args:
            normalized_values: 归一化比例列表(0-1)
            axis_x: X轴
            axis_y: Y轴

        Returns:
            QLineSeries: 线连接系列
        """
        line_series = QLineSeries()
        line_series.setName("")

        # 添加数据点（直接使用归一化比例）
        for i, ratio in enumerate(normalized_values):
            line_series.append(i, ratio)

        self._chart.addSeries(line_series)

        # 设置线条颜色
        line_color = get_tone_chart_bar_color()
        line_series.setPen(QPen(QColor(line_color.name()), 1.5))

        line_series.attachAxis(axis_x)
        line_series.attachAxis(axis_y)

        # 隐藏线系列的图例项
        self._chart.legend().markers(line_series)[0].setVisible(False)

        return line_series

    def _apply_scaling(self, values: list[float]) -> list[float]:
        """应用缩放模式到数据，返回归一化比例(0-1)

        Args:
            values: 原始数据值列表

        Returns:
            list[float]: 归一化比例列表(0-1)
        """
        max_value = max(values)
        if max_value == 0:
            return [0.0] * len(values)

        if self._scaling_mode == "linear":
            return [v / max_value for v in values]

        # adaptive: 自适应缩放（使用已计算的CV值）
        scaled_values = []
        for value in values:
            if value == 0:
                scaled_values.append(0.0)
                continue

            if self._cv < 0.8:
                normalized = value / max_value
            elif self._cv > 2.0:
                normalized = math.sqrt(value) / math.sqrt(max_value)
            else:
                t = (self._cv - 0.8) / (2.0 - 0.8)
                exponent = 0.75 - t * 0.2
                normalized = (value / max_value) ** exponent

            scaled_values.append(normalized)

        return scaled_values

    def _calculate_cv(self, values: list[float]) -> float:
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
        variance = sum((x - mean_val) ** 2 for x in non_zero) / len(non_zero)
        return math.sqrt(variance) / mean_val

    def _add_reference_lines_normalized(self, result: ToneAnalysisResult,
                                         axis_x: QValueAxis, axis_y: QValueAxis) -> None:
        """添加均值和中位数参考线（使用归一化比例）

        Args:
            result: 分析结果
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
        mean_line.append(mean_index, 1.1)

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
        median_line.append(median_index, 1.1)

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
    """Qt 图表组件"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 顶部区域：原图 + 灰度图 + 饼图
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        self._image_display = ImageDisplayWidget()
        self._pie_chart = PieChartWidget()

        top_layout.addWidget(self._image_display, stretch=1)
        top_layout.addWidget(self._pie_chart, stretch=1)

        layout.addWidget(top_widget, stretch=4)

        # 底部：直方图
        self._histogram = HistogramWidget()
        layout.addWidget(self._histogram, stretch=5)

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

    def __init__(self, title: str, value: str, parent: QWidget | None = None,
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

    def __init__(self, img_array: np.ndarray | None, image_key: str | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._img_array = img_array
        self._image_key = image_key
        self._service = ToneAnalysisService()
        self._worker: AnalysisWorker | None = None

        self.setWindowTitle(tr('tone_analysis.dialog_title'))
        self.setMinimumSize(900, 600)
        self.resize(1100, 750)

        # 显示标题栏的最大化和最小化按钮（FramelessDialog默认隐藏）
        self.titleBar.minBtn.show()
        self.titleBar.maxBtn.show()
        self.titleBar.setDoubleClickEnabled(True)

        # 恢复最大化按钮样式（FramelessDialog初始化时禁用了）
        if sys.platform == 'win32':
            import win32con
            import win32gui
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

        # 样式准备好后允许显示
        self._enable_show()

    def _setup_ui(self) -> None:
        """设置界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 40, 20, 10)
        main_layout.setSpacing(8)

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

        main_layout.addWidget(content_widget)

    def start_analysis(self) -> None:
        """开始分析"""
        # 获取采样模式设置
        config_manager = get_config_manager()
        sampling_mode = config_manager.get('settings.histogram_sampling_mode', 'fast')
        sample_step = 1 if sampling_mode == 'fine' else 2

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
            # 注意：HistogramService 的缓存键包含采样模式后缀（_fast 或 _fine）
            histogram_cache = get_histogram_cache()
            histogram_key = f"{self._image_key}_{sampling_mode}"
            cached_data = histogram_cache.get_with_metadata(histogram_key, "luminance")
            if cached_data is not None and 'mean' in cached_data['metadata']:
                self._quick_analysis_from_histogram(cached_data)
                return

        # 没有缓存，启动线程计算
        self._worker = AnalysisWorker(self._img_array, self._service, sample_step)
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

        # 始终显示置信度百分比
        return f'{base_name} ({int(avg_confidence * 100)}%)'

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

    def closeEvent(self, event) -> None:
        """关闭事件"""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)
        super().closeEvent(event)
