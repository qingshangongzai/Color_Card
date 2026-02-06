# 第三方库导入
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

# 项目模块导入
from .theme_colors import get_picker_border_color, get_picker_fill_color


class ColorPicker(QWidget):
    """可拖动的圆形取色点"""
    color_changed = Signal(int, tuple)  # 信号：索引, RGB颜色
    position_changed = Signal(int, QPoint)  # 信号：索引, 新位置
    drag_started = Signal(int)  # 信号：开始拖动
    drag_finished = Signal(int)  # 信号：结束拖动

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.radius = 12
        self.setFixedSize(self.radius * 2, self.radius * 2)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self._dragging = False
        self._drag_offset = QPoint()
        self._color = get_picker_fill_color()
        self._is_active = False

    def set_color(self, color):
        """设置取色点显示的颜色"""
        self._color = QColor(color)
        self.update()

    def set_active(self, active):
        """设置是否为活动状态（高亮显示）"""
        self._is_active = active
        self.update()

    def is_dragging(self):
        """是否正在拖动"""
        return self._dragging

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 外圈（白色边框）
        outer_pen = QPen(Qt.GlobalColor.white, 3)
        painter.setPen(outer_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(1, 1, self.width() - 2, self.height() - 2)

        # 内圈（显示当前颜色）
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(4, 4, self.width() - 8, self.height() - 8)

        # 中心十字箭头（深色，类似Adobe Color风格）
        center = self.radius
        cross_size = 5
        pen_width = 2
        painter.setPen(QPen(get_picker_border_color(), pen_width))
        # 水平线
        painter.drawLine(center - cross_size, center, center + cross_size, center)
        # 垂直线
        painter.drawLine(center, center - cross_size, center, center + cross_size)

        # 活动状态高亮
        if self._is_active:
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(2, 2, self.width() - 4, self.height() - 4)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.set_active(True)
            self.drag_started.emit(self.index)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and self.parent():
            # 计算新位置
            new_pos = self.mapToParent(event.pos()) - self._drag_offset

            # 获取父控件（ImageCanvas）的图片显示区域
            parent = self.parent()
            if hasattr(parent, 'get_image_display_rect'):
                display_rect = parent.get_image_display_rect()
                if display_rect:
                    disp_x, disp_y, disp_w, disp_h = display_rect
                    # 限制取色点中心在图片显示区域内
                    center_x = new_pos.x() + self.radius
                    center_y = new_pos.y() + self.radius

                    # 限制中心点在图片区域内
                    center_x = max(disp_x, min(center_x, disp_x + disp_w))
                    center_y = max(disp_y, min(center_y, disp_y + disp_h))

                    # 转换回左上角坐标
                    new_pos.setX(center_x - self.radius)
                    new_pos.setY(center_y - self.radius)
            else:
                # 回退：限制在父控件范围内
                parent_rect = parent.rect()
                new_pos.setX(max(0, min(new_pos.x(), parent_rect.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), parent_rect.height() - self.height())))

            self.move(new_pos)
            self.position_changed.emit(self.index, new_pos + QPoint(self.radius, self.radius))
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.drag_finished.emit(self.index)
            event.accept()
