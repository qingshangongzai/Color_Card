"""直方图显示组件

使用 Matplotlib 绘制 gamma 校正后的明度直方图。
"""

from typing import Optional

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class HistogramWidget(QWidget):
    """直方图显示组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._histogram: Optional[np.ndarray] = None
        self._peak: Optional[int] = None
        self._P10: Optional[int] = None
        self._P90: Optional[int] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(figsize=(4, 3), dpi=100)
        self._canvas = FigureCanvas(self._figure)
        layout.addWidget(self._canvas)

        self._ax = self._figure.add_subplot(111)
        self._setup_axes()

    def _setup_axes(self) -> None:
        """设置坐标轴"""
        self._ax.set_xlim(0, 255)
        self._ax.set_ylim(0, 1)
        self._ax.set_xlabel("亮度", fontsize=9)
        self._ax.set_ylabel("占比", fontsize=9)
        self._ax.tick_params(axis='both', labelsize=8)

        self._ax.axvspan(0, 85, alpha=0.15, color='#1a1a2e', label='暗部')
        self._ax.axvspan(86, 170, alpha=0.15, color='#4a4a6a', label='中间调')
        self._ax.axvspan(171, 255, alpha=0.15, color='#f0f0f0', label='亮部')

        self._ax.axvline(x=85, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        self._ax.axvline(x=170, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)

        self._figure.tight_layout()

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

        self._update_plot()

    def _update_plot(self) -> None:
        """更新绑图"""
        if self._histogram is None:
            return

        self._ax.clear()
        self._setup_axes()

        hist_normalized = self._histogram / self._histogram.sum()

        x = np.arange(256)
        self._ax.fill_between(x, hist_normalized, alpha=0.7, color='#3498db')
        self._ax.plot(x, hist_normalized, color='#2980b9', linewidth=1)

        if self._peak is not None:
            self._ax.axvline(x=self._peak, color='#e74c3c', linewidth=2, label=f'波峰: {self._peak}')

        if self._P10 is not None:
            self._ax.axvline(x=self._P10, color='#27ae60', linewidth=1.5, linestyle='--', label=f'P10: {self._P10}')

        if self._P90 is not None:
            self._ax.axvline(x=self._P90, color='#f39c12', linewidth=1.5, linestyle='--', label=f'P90: {self._P90}')

        if any([self._peak, self._P10, self._P90]):
            self._ax.legend(loc='upper right', fontsize=7)

        self._canvas.draw()

    def clear(self) -> None:
        """清空直方图"""
        self._histogram = None
        self._peak = None
        self._P10 = None
        self._P90 = None

        self._ax.clear()
        self._setup_axes()
        self._canvas.draw()
