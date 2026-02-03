from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QImage


class LuminanceHistogram(QWidget):
    """明度直方图组件 - 显示图片的明度分布和Zone分区"""
    
    zone_changed = Signal(int)  # 信号：当前Zone变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMaximumHeight(200)
        self.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        
        self._histogram_data = [0] * 256  # 256个亮度值的像素计数
        self._max_count = 0
        self._current_zone = -1  # 当前选中的Zone
        self._image = None
        
        # Zone颜色配置
        self._zone_colors = [
            QColor(20, 20, 20),      # Zone 0: 极暗
            QColor(60, 60, 60),      # Zone 1: 暗
            QColor(100, 100, 100),   # Zone 2: 偏暗
            QColor(140, 140, 140),   # Zone 3: 中灰
            QColor(180, 180, 180),   # Zone 4: 偏亮
            QColor(210, 210, 210),   # Zone 5: 亮
            QColor(235, 235, 235),   # Zone 6: 很亮
            QColor(255, 255, 255),   # Zone 7: 极亮
        ]
        self._highlight_color = QColor(0, 150, 255)  # 高亮颜色
        
    def set_image(self, image: QImage):
        """设置图片并计算直方图"""
        self._image = image
        self._calculate_histogram()
        self.update()
        
    def _calculate_histogram(self):
        """计算明度直方图"""
        self._histogram_data = [0] * 256
        self._max_count = 0
        
        if self._image is None or self._image.isNull():
            return
            
        width = self._image.width()
        height = self._image.height()
        
        # 遍历所有像素计算明度
        for y in range(height):
            for x in range(width):
                color = self._image.pixelColor(x, y)
                # 使用 Rec. 709 标准计算亮度值（与 color_utils.py 保持一致）
                luminance = int(0.2126 * color.red() +
                              0.7152 * color.green() +
                              0.0722 * color.blue())
                luminance = max(0, min(255, luminance))
                self._histogram_data[luminance] += 1
                
        self._max_count = max(self._histogram_data) if self._histogram_data else 1
        
    def set_current_zone(self, zone: int):
        """设置当前选中的Zone (0-7)"""
        if 0 <= zone <= 7 and zone != self._current_zone:
            self._current_zone = zone
            self.zone_changed.emit(zone)
            self.update()
            
    def clear(self):
        """清空直方图"""
        self._histogram_data = [0] * 256
        self._max_count = 0
        self._current_zone = -1
        self._image = None
        self.update()
        
    def get_zone_from_luminance(self, luminance: int) -> int:
        """根据明度值获取Zone (0-7)"""
        return min(7, luminance // 32)
        
    def get_zone_label(self, zone: int) -> str:
        """获取Zone的显示标签"""
        labels = ["0", "1", "2", "3", "4", "5", "6", "7"]
        return labels[zone] if 0 <= zone <= 7 else "--"
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        if self._max_count == 0:
            # 没有数据时显示提示
            painter.setPen(QColor(100, 100, 100))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "导入图片以查看直方图")
            return
            
        # 计算绘制区域
        margin_left = 30
        margin_right = 10
        margin_top = 25
        margin_bottom = 25
        
        chart_width = self.width() - margin_left - margin_right
        chart_height = self.height() - margin_top - margin_bottom
        
        # 绘制Zone背景分区
        zone_width = chart_width / 8
        for i in range(8):
            x = margin_left + i * zone_width
            # 如果是当前选中的Zone，使用高亮颜色
            if i == self._current_zone:
                painter.fillRect(
                    int(x), margin_top,
                    int(zone_width), chart_height,
                    QColor(0, 100, 150, 80)
                )
            else:
                # 轻微显示Zone背景
                painter.fillRect(
                    int(x), margin_top,
                    int(zone_width), chart_height,
                    QColor(40, 40, 40, 30)
                )
                
        # 绘制直方图柱状图
        bar_width = chart_width / 256
        
        for i in range(256):
            count = self._histogram_data[i]
            if count > 0:
                # 使用对数缩放使细节更明显
                normalized = count / self._max_count
                bar_height = normalized * chart_height
                
                x = margin_left + i * bar_width
                y = margin_top + chart_height - bar_height
                
                # 根据Zone选择颜色
                zone = self.get_zone_from_luminance(i)
                if zone == self._current_zone:
                    color = self._highlight_color
                else:
                    # 在Zone内渐变
                    zone_start = zone * 32
                    zone_progress = (i - zone_start) / 32
                    base_color = self._zone_colors[zone]
                    color = base_color
                    
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRect(int(x), int(y), max(1, int(bar_width) + 1), int(bar_height))
                
        # 绘制Zone分隔线
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        for i in range(1, 8):
            x = margin_left + i * zone_width
            painter.drawLine(int(x), margin_top, int(x), margin_top + chart_height)
            
        # 绘制边框
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(margin_left, margin_top, chart_width, chart_height)
        
        # 绘制Zone标签
        painter.setPen(QColor(150, 150, 150))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        
        for i in range(8):
            x = margin_left + i * zone_width + zone_width / 2
            label = self.get_zone_label(i)
            text_rect = painter.boundingRect(0, 0, 0, 0, Qt.AlignmentFlag.AlignCenter, label)
            text_x = int(x - text_rect.width() / 2)
            text_y = self.height() - 8
            painter.drawText(text_x, text_y, label)
            
        # 绘制Y轴标签（最小值和最大值）
        painter.setPen(QColor(100, 100, 100))
        font.setPointSize(7)
        painter.setFont(font)
        painter.drawText(5, margin_top + 5, "max")
        painter.drawText(5, margin_top + chart_height, "0")
        
        # 绘制标题
        painter.setPen(QColor(200, 200, 200))
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(margin_left, 18, "Zone System Histogram")
        
        # 如果当前有选中的Zone，显示信息
        if self._current_zone >= 0:
            painter.setPen(self._highlight_color)
            font.setPointSize(10)
            painter.setFont(font)
            zone_text = f"Zone {self._current_zone}"
            painter.drawText(self.width() - 80, 18, zone_text)
