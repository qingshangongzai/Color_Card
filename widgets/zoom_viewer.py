from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QImage, QColor, QPen, QBrush, QPainterPath


class ZoomViewer(QWidget):
    """放大视图组件，拖动取色点时显示周围像素的放大效果"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._image = None
        self._center_pos = QPoint(0, 0)
        self._zoom_factor = 4
        self._source_rect_size = 25

        self.hide()

    def set_image(self, image):
        """设置源图片"""
        self._image = image
        self.update()

    def update_position(self, picker_pos):
        """更新放大视图位置（显示在取色点上方）"""
        # 显示在取色点上方，留出一点间距
        x = picker_pos.x() - self.width() // 2
        y = picker_pos.y() - self.height() - 15

        # 确保不超出父控件边界
        if self.parent():
            parent_rect = self.parent().rect()
            x = max(0, min(x, parent_rect.width() - self.width()))
            y = max(0, min(y, parent_rect.height() - self.height()))

        self.move(x, y)

    def set_center_position(self, image_pos):
        """设置要放大的中心位置（原始图片坐标）"""
        self._center_pos = image_pos
        self.update()

    def paintEvent(self, event):
        if self._image is None or self._image.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 创建圆形裁剪路径
        path = QPainterPath()
        path.addEllipse(2, 2, self.width() - 4, self.height() - 4)
        painter.setClipPath(path)

        # 计算源区域（原始图片中需要放大的区域）
        half_size = self._source_rect_size // 2
        src_x = self._center_pos.x() - half_size
        src_y = self._center_pos.y() - half_size

        # 确保源区域在图片范围内
        src_x = max(0, min(src_x, self._image.width() - self._source_rect_size))
        src_y = max(0, min(src_y, self._image.height() - self._source_rect_size))

        # 绘制放大的图片
        source_rect = self._image.copy(src_x, src_y, self._source_rect_size, self._source_rect_size)
        painter.drawImage(self.rect(), source_rect)

        # 绘制中心十字准星（深色）
        painter.setClipping(False)
        center_x = self.width() // 2
        center_y = self.height() // 2
        cross_size = 8

        pen = QPen(QColor(40, 40, 40), 2)
        painter.setPen(pen)

        # 水平线
        painter.drawLine(center_x - cross_size, center_y, center_x + cross_size, center_y)
        # 垂直线
        painter.drawLine(center_x, center_y - cross_size, center_x, center_y + cross_size)

        # 绘制白色边框
        painter.setPen(QPen(Qt.GlobalColor.white, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(1, 1, self.width() - 2, self.height() - 2)

        # 绘制阴影效果
        painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
        painter.drawEllipse(0, 0, self.width(), self.height())
