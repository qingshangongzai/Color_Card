"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: base_histogram
功能描述: 直方图基类，提供通用的直方图绘制功能

作者: 青山公仔
创建日期: 2026-02-05
"""

# 第三方库导入
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


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
        
        # 绘图边距
        self._margin_left = 35
        self._margin_right = 15
        self._margin_top = 15
        self._margin_bottom = 30
        
        # 背景色
        self._background_color = QColor(20, 20, 20)
        
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
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(x, y + height, x + width, y + height)
        
    def _draw_max_label(self, painter: QPainter, x: int, y: int):
        """绘制左侧Y轴最大值标签（辅助方法）
        
        Args:
            painter: QPainter 对象
            x: 绘图区域左上角 X 坐标
            y: 绘图区域左上角 Y 坐标
        """
        if self._max_count > 0:
            painter.setPen(QColor(120, 120, 120))
            font = QFont()
            font.setPointSize(7)
            painter.setFont(font)
            max_text = str(self._max_count)
            painter.drawText(5, y + 10, max_text)
