from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor, QFont

from qfluentwidgets import RoundMenu, Action, FluentIcon

from .color_picker import ColorPicker
from color_utils import rgb_to_luminance, get_zone_from_luminance


class LuminanceCanvas(QWidget):
    """明度提取画布 - 支持取色点拖动和Zone标注显示"""
    luminance_picked = Signal(int, int, int)  # 信号：索引, Zone, 明度值
    image_loaded = Signal(str)  # 信号：图片路径
    open_image_requested = Signal()  # 信号：请求打开图片
    change_image_requested = Signal()  # 信号：请求更换图片
    clear_image_requested = Signal()  # 信号：请求清空图片

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #2a2a2a; border-radius: 8px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._original_pixmap = None
        self._image = None
        self._pickers = []
        self._picker_positions = []
        self._active_picker_index = -1
        self._picker_zones = [-1] * 5  # 存储每个取色点的Zone

        # 创建5个取色点（初始隐藏）
        for i in range(5):
            picker = ColorPicker(i, self)
            picker.position_changed.connect(self.on_picker_moved)
            picker.drag_started.connect(self.on_picker_drag_started)
            picker.drag_finished.connect(self.on_picker_drag_finished)
            picker.hide()  # 初始隐藏
            self._pickers.append(picker)
            self._picker_positions.append(QPoint(100 + i * 100, 100))
            
        self.update_picker_positions()

    def set_image(self, image_path):
        """加载并显示图片"""
        # 加载原始高分辨率图片
        self._original_pixmap = QPixmap(image_path)
        self._image = QImage(image_path)

        if self._original_pixmap and not self._original_pixmap.isNull():
            # 显示取色点
            for picker in self._pickers:
                picker.show()

            # 改变光标为默认
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # 重新初始化取色点位置到图片中心区域
            center_x = self.width() // 2
            center_y = self.height() // 2
            for i, picker in enumerate(self._pickers):
                offset_x = (i - 2) * 50
                self._picker_positions[i] = QPoint(center_x + offset_x, center_y)

            self.update_picker_positions()
            self.extract_all_luminance()
            self.update()

            # 发送图片加载信号
            self.image_loaded.emit(image_path)

    def update_picker_positions(self):
        """更新所有取色点的位置"""
        for i, picker in enumerate(self._pickers):
            pos = self._picker_positions[i]
            picker.move(pos.x() - picker.radius, pos.y() - picker.radius)

    def on_picker_drag_started(self, index):
        """取色点开始拖动"""
        self._active_picker_index = index
        # 设置其他取色点为非活动状态
        for i, picker in enumerate(self._pickers):
            picker.set_active(i == index)

    def on_picker_drag_finished(self, index):
        """取色点结束拖动"""
        self._active_picker_index = -1
        # 所有取色点恢复默认状态
        for picker in self._pickers:
            picker.set_active(False)

    def on_picker_moved(self, index, new_pos):
        """取色点移动时的回调"""
        self._picker_positions[index] = new_pos
        self.extract_luminance(index)
        self.update()

    def canvas_to_image_pos(self, canvas_pos):
        """将画布坐标转换为原始图片坐标"""
        if self._image is None or self._image.isNull():
            return None

        display_rect = self.get_display_rect()
        if display_rect is None:
            return None

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 将画布坐标转换为图片坐标
        img_x = canvas_pos.x() - disp_x
        img_y = canvas_pos.y() - disp_y

        # 检查坐标是否在图片显示范围内
        if 0 <= img_x < disp_w and 0 <= img_y < disp_h:
            # 计算在原始图片中的坐标
            scale_x = self._image.width() / disp_w
            scale_y = self._image.height() / disp_h

            orig_x = int(img_x * scale_x)
            orig_y = int(img_y * scale_y)

            # 确保坐标在原始图片范围内
            orig_x = max(0, min(orig_x, self._image.width() - 1))
            orig_y = max(0, min(orig_y, self._image.height() - 1))

            return QPoint(orig_x, orig_y)

        return None

    def get_display_rect(self):
        """计算图片在画布中的显示区域"""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return None

        # 计算缩放后的尺寸（保持比例）
        scaled_size = self._original_pixmap.size()
        scaled_size.scale(self.size(), Qt.AspectRatioMode.KeepAspectRatio)

        # 居中显示
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2

        return x, y, scaled_size.width(), scaled_size.height()

    def extract_luminance(self, index):
        """提取指定取色点的明度信息"""
        if self._image is None or self._image.isNull():
            return

        pos = self._picker_positions[index]
        image_pos = self.canvas_to_image_pos(pos)

        if image_pos:
            # 获取像素颜色
            color = self._image.pixelColor(image_pos.x(), image_pos.y())
            rgb = (color.red(), color.green(), color.blue())
            
            # 计算明度和Zone
            luminance = rgb_to_luminance(*rgb)
            zone = get_zone_from_luminance(luminance)
            
            # 存储Zone信息
            self._picker_zones[index] = zone

            # 发送信号
            self.luminance_picked.emit(index, zone, luminance)

    def extract_all_luminance(self):
        """提取所有取色点的明度"""
        for i in range(len(self._pickers)):
            self.extract_luminance(i)

    def get_zone_label(self, zone):
        """获取Zone的显示标签"""
        if zone < 0:
            return "--"
        return str(zone)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 绘制背景
        painter.fillRect(self.rect(), QColor(42, 42, 42))

        # 绘制图片（使用原始高分辨率图片，实时缩放显示）
        if self._original_pixmap and not self._original_pixmap.isNull():
            display_rect = self.get_display_rect()
            if display_rect:
                x, y, w, h = display_rect
                target_rect = QRect(x, y, w, h)
                painter.drawPixmap(target_rect, self._original_pixmap, self._original_pixmap.rect())
                
                # 绘制Zone标注（白色框+黑字）
                self._draw_zone_labels(painter)
        else:
            # 没有图片时显示提示文字
            painter.setPen(QColor(150, 150, 150))
            font = QFont()
            font.setPointSize(14)
            painter.setFont(font)
            text = "点击导入图片"
            text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_zone_labels(self, painter):
        """绘制Zone标注 - 白色背景框 + 黑色文字"""
        if not self._image or self._image.isNull():
            return
            
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        for i, pos in enumerate(self._picker_positions):
            zone = self._picker_zones[i]
            if zone < 0:
                continue
                
            label = self.get_zone_label(zone)
            
            # 计算文字大小
            text_rect = painter.boundingRect(0, 0, 0, 0, Qt.AlignmentFlag.AlignCenter, label)
            padding = 4
            box_width = text_rect.width() + padding * 2
            box_height = text_rect.height() + padding * 2
            
            # 计算标注位置（取色点右上方）
            box_x = pos.x() + 15
            box_y = pos.y() - 25
            
            # 确保不超出画布边界
            if box_x + box_width > self.width():
                box_x = pos.x() - box_width - 15
            if box_y < 0:
                box_y = pos.y() + 15
                
            # 绘制白色背景框
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255))
            painter.drawRoundedRect(box_x, box_y, box_width, box_height, 3, 3)
            
            # 绘制黑色文字
            painter.setPen(QColor(0, 0, 0))
            text_x = box_x + padding
            text_y = box_y + padding
            painter.drawText(text_x, text_y, text_rect.width(), text_rect.height(), 
                           Qt.AlignmentFlag.AlignCenter, label)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 如果没有图片，点击打开文件对话框
            if self._original_pixmap is None or self._original_pixmap.isNull():
                self.open_image_requested.emit()
            event.accept()

    def resizeEvent(self, event):
        """窗口大小改变时重新调整图片"""
        super().resizeEvent(event)
        if self._image and not self._image.isNull():
            # 窗口大小改变时，只需重新提取明度（因为显示区域变了）
            self.extract_all_luminance()
            self.update()

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        # 只有在有图片时才显示右键菜单
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return

        menu = RoundMenu("")

        change_action = Action(FluentIcon.PHOTO, "更换图片")
        change_action.triggered.connect(self.change_image_requested.emit)
        menu.addAction(change_action)

        clear_action = Action(FluentIcon.DELETE, "清空图片")
        clear_action.triggered.connect(self.clear_image_requested.emit)
        menu.addAction(clear_action)

        menu.exec(event.globalPos())

    def clear_image(self):
        """清空图片"""
        self._original_pixmap = None
        self._image = None
        self._picker_zones = [-1] * 5

        # 隐藏取色点
        for picker in self._pickers:
            picker.hide()
            picker.set_active(False)

        # 恢复光标为手型
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.update()
        
    def get_image(self):
        """获取当前图片"""
        return self._image
