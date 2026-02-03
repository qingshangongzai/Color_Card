from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QPoint, Signal, QRect, QThread, QTimer
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor, QFont

from qfluentwidgets import RoundMenu, Action, FluentIcon, IndeterminateProgressRing

from .color_picker import ColorPicker
from .zoom_viewer import ZoomViewer

from PIL import Image
import io


class ImageLoader(QThread):
    """图片加载工作线程（使用PIL在子线程读取图片数据）"""
    loaded = Signal(bytes, int, int, str)  # 信号：图片数据(bytes), 宽度, 高度, 格式
    error = Signal(str)  # 信号：错误信息

    def __init__(self, image_path):
        super().__init__()
        self._image_path = image_path

    def run(self):
        """在子线程中使用PIL加载图片"""
        try:
            # 使用PIL打开图片（PIL是线程安全的）
            with Image.open(self._image_path) as pil_image:
                # 转换为RGB模式（处理RGBA、P模式等）
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')

                # 获取图片尺寸
                width, height = pil_image.size

                # 将图片保存为内存中的BMP格式（无压缩，便于快速转换）
                buffer = io.BytesIO()
                pil_image.save(buffer, format='BMP')
                image_data = buffer.getvalue()

                self.loaded.emit(image_data, width, height, 'BMP')
        except Exception as e:
            self.error.emit(str(e))


class ImageCanvas(QWidget):
    """图片显示画布，支持取色点拖动"""
    color_picked = Signal(int, tuple)  # 信号：索引, RGB颜色
    image_loaded = Signal(str)  # 信号：图片路径
    image_data_loaded = Signal(object, object)  # 信号：QPixmap, QImage（用于同步到其他面板）
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
        self._zoom_viewer = None
        self._active_picker_index = -1
        self._loader = None
        self._pending_image_path = None

        # 创建加载指示器
        self._loading_indicator = IndeterminateProgressRing(self)
        self._loading_indicator.setFixedSize(64, 64)
        self._loading_indicator.hide()

        # 创建放大视图
        self._zoom_viewer = ZoomViewer(self)

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
        self._update_loading_indicator_position()

    def set_image(self, image_path):
        """异步加载并显示图片"""
        # 保存图片路径
        self._pending_image_path = image_path

        # 如果已有加载线程在运行，先停止
        if self._loader is not None and self._loader.isRunning():
            self._loader.quit()
            self._loader.wait()

        # 显示加载指示器
        self._loading_indicator.start()
        self._loading_indicator.show()
        self._update_loading_indicator_position()

        # 创建并启动加载线程
        self._loader = ImageLoader(image_path)
        self._loader.loaded.connect(self._on_image_loaded)
        self._loader.error.connect(self._on_image_load_error)
        self._loader.finished.connect(self._cleanup_loader)
        self._loader.start()

    def _update_loading_indicator_position(self):
        """更新加载指示器位置到中心"""
        x = (self.width() - self._loading_indicator.width()) // 2
        y = (self.height() - self._loading_indicator.height()) // 2
        self._loading_indicator.move(x, y)

    def _cleanup_loader(self):
        """清理加载线程"""
        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None

    def _on_image_loaded(self, image_data, width, height, fmt):
        """图片加载完成的回调（在主线程中创建QImage/QPixmap）"""
        # 从字节数据创建QImage（在主线程中安全执行）
        self._image = QImage.fromData(image_data, fmt)
        self._original_pixmap = QPixmap.fromImage(self._image)

        # 隐藏加载指示器
        self._loading_indicator.stop()
        self._loading_indicator.hide()

        # 设置放大视图的图片
        self._zoom_viewer.set_image(self._image)

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
        self.update()

        # 发送图片加载信号
        if self._pending_image_path:
            self.image_loaded.emit(self._pending_image_path)
            # 同时发送图片数据信号，用于同步到其他面板
            self.image_data_loaded.emit(self._original_pixmap, self._image)

        # 延迟提取颜色，让UI先响应，用户可以立即切换面板
        QTimer.singleShot(300, self.extract_all_colors)

    def _on_image_load_error(self, error_msg):
        """图片加载失败的回调"""
        # 隐藏加载指示器
        self._loading_indicator.stop()
        self._loading_indicator.hide()

        # 恢复光标
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 可以在这里添加错误提示，暂时只打印
        print(f"图片加载失败: {error_msg}")

    def update_picker_positions(self):
        """更新所有取色点的位置"""
        for i, picker in enumerate(self._pickers):
            pos = self._picker_positions[i]
            picker.move(pos.x() - picker.radius, pos.y() - picker.radius)

    def on_picker_drag_started(self, index):
        """取色点开始拖动"""
        self._active_picker_index = index
        self._zoom_viewer.show()
        self.update_zoom_viewer()

    def on_picker_drag_finished(self, index):
        """取色点结束拖动"""
        self._zoom_viewer.hide()
        self._active_picker_index = -1

    def on_picker_moved(self, index, new_pos):
        """取色点移动时的回调"""
        self._picker_positions[index] = new_pos
        self.extract_color(index)
        self.update_zoom_viewer()

    def update_zoom_viewer(self):
        """更新放大视图的位置和内容"""
        if self._active_picker_index < 0 or self._image is None:
            return

        picker_pos = self._picker_positions[self._active_picker_index]

        # 更新放大视图位置
        self._zoom_viewer.update_position(picker_pos)

        # 计算原始图片中的坐标
        image_pos = self.canvas_to_image_pos(picker_pos)
        if image_pos:
            self._zoom_viewer.set_center_position(image_pos)

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

    def extract_color(self, index):
        """提取指定取色点的颜色"""
        if self._image is None or self._image.isNull():
            return

        pos = self._picker_positions[index]
        image_pos = self.canvas_to_image_pos(pos)

        if image_pos:
            # 获取像素颜色
            color = self._image.pixelColor(image_pos.x(), image_pos.y())
            rgb = (color.red(), color.green(), color.blue())

            # 更新取色点显示的颜色
            self._pickers[index].set_color(color)

            # 发送信号
            self.color_picked.emit(index, rgb)

    def extract_all_colors(self):
        """提取所有取色点的颜色"""
        for i in range(len(self._pickers)):
            self.extract_color(i)

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
        else:
            # 没有图片时显示提示文字
            painter.setPen(QColor(150, 150, 150))
            font = QFont()
            font.setPointSize(14)
            painter.setFont(font)
            text = "点击导入图片"
            text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

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
        self._update_loading_indicator_position()
        if self._image and not self._image.isNull():
            # 窗口大小改变时，只需重新提取颜色（因为显示区域变了）
            self.extract_all_colors()
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

        # 隐藏取色点和放大视图
        for picker in self._pickers:
            picker.hide()
        self._zoom_viewer.hide()

        # 恢复光标为手型
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.update()
