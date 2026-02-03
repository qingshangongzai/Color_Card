from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, Signal, QRect, QTimer, QThread
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor, QFont

from qfluentwidgets import RoundMenu, Action, FluentIcon

from .color_picker import ColorPicker
from color_utils import get_luminance, get_zone

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


class LuminanceCanvas(QWidget):
    """明度提取画布，支持取色点拖动和区域标注"""
    luminance_picked = Signal(int, str)  # 信号：索引, 区域编号
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
        self._picker_zones = []  # 存储每个取色器的区域编号
        self._loader = None
        self._pending_image_path = None

        # 创建5个取色点（初始隐藏）
        for i in range(5):
            picker = ColorPicker(i, self)
            picker.position_changed.connect(self.on_picker_moved)
            picker.drag_started.connect(self.on_picker_drag_started)
            picker.drag_finished.connect(self.on_picker_drag_finished)
            picker.hide()  # 初始隐藏
            self._pickers.append(picker)
            self._picker_positions.append(QPoint(100 + i * 100, 100))
            self._picker_zones.append("0-1")

        self.update_picker_positions()

    def set_image(self, image_path):
        """异步加载并显示图片"""
        # 保存图片路径
        self._pending_image_path = image_path

        # 如果已有加载线程在运行，先停止
        if self._loader is not None and self._loader.isRunning():
            self._loader.quit()
            self._loader.wait()

        # 创建并启动加载线程
        self._loader = ImageLoader(image_path)
        self._loader.loaded.connect(self._on_image_loaded)
        self._loader.error.connect(self._on_image_load_error)
        self._loader.finished.connect(self._cleanup_loader)
        self._loader.start()

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
        self._setup_after_load()

    def _on_image_load_error(self, error_msg):
        """图片加载失败的回调"""
        print(f"明度面板图片加载失败: {error_msg}")

    def set_image_data(self, pixmap, image):
        """直接使用已加载的图片数据（避免重复加载）"""
        self._original_pixmap = pixmap
        self._image = image
        self._setup_after_load()

    def _setup_after_load(self):
        """图片加载完成后的设置"""
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
            self.update()

            # 延迟提取区域，让UI先响应，用户可以立即切换面板
            QTimer.singleShot(300, self.extract_all_zones)

    def update_picker_positions(self):
        """更新所有取色点的位置"""
        for i, picker in enumerate(self._pickers):
            pos = self._picker_positions[i]
            picker.move(pos.x() - picker.radius, pos.y() - picker.radius)

    def on_picker_drag_started(self, index):
        """取色点开始拖动"""
        picker = self._pickers[index]
        picker.set_active(True)

    def on_picker_drag_finished(self, index):
        """取色点结束拖动"""
        picker = self._pickers[index]
        picker.set_active(False)

    def on_picker_moved(self, index, new_pos):
        """取色点移动时的回调"""
        self._picker_positions[index] = new_pos
        self.extract_zone(index)
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

    def extract_zone(self, index):
        """提取指定取色点的区域编号"""
        if self._image is None or self._image.isNull():
            return

        pos = self._picker_positions[index]
        image_pos = self.canvas_to_image_pos(pos)

        if image_pos:
            # 获取像素颜色
            color = self._image.pixelColor(image_pos.x(), image_pos.y())
            luminance = get_luminance(color.red(), color.green(), color.blue())
            zone = get_zone(luminance)

            # 更新区域编号
            self._picker_zones[index] = zone

            # 发送信号
            self.luminance_picked.emit(index, zone)

    def extract_all_zones(self):
        """提取所有取色点的区域编号"""
        for i in range(len(self._pickers)):
            self.extract_zone(i)

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

                # 绘制区域标注
                self._draw_zone_labels(painter, display_rect)
        else:
            # 没有图片时显示提示文字
            painter.setPen(QColor(150, 150, 150))
            font = QFont()
            font.setPointSize(14)
            painter.setFont(font)
            text = "点击导入图片"
            text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_zone_labels(self, painter, display_rect):
        """绘制区域标注（白色小方框+黑色文字）"""
        disp_x, disp_y, disp_w, disp_h = display_rect

        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        for i, pos in enumerate(self._picker_positions):
            # 检查取色器是否在图片显示区域内
            img_x = pos.x() - disp_x
            img_y = pos.y() - disp_y

            if 0 <= img_x < disp_w and 0 <= img_y < disp_h:
                zone = self._picker_zones[i]

                # 计算文字尺寸
                text_rect = painter.boundingRect(QRect(), Qt.AlignmentFlag.AlignCenter, zone)
                text_width = text_rect.width()
                text_height = text_rect.height()

                # 方框尺寸（稍大于文字）
                box_width = text_width + 8
                box_height = text_height + 4

                # 方框位置（取色器上方）
                box_x = pos.x() - box_width // 2
                box_y = pos.y() - 35  # 取色器上方35像素

                # 绘制白色填充方框
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255))
                painter.drawRect(box_x, box_y, box_width, box_height)

                # 绘制黑色文字
                painter.setPen(QColor(0, 0, 0))
                text_x = box_x + (box_width - text_width) // 2
                text_y = box_y + (box_height - text_height) // 2
                painter.drawText(text_x, text_y + text_height - 2, zone)

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
            # 窗口大小改变时，只需重新提取区域（因为显示区域变了）
            self.extract_all_zones()
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

        # 隐藏取色点
        for picker in self._pickers:
            picker.hide()

        # 重置区域编号
        self._picker_zones = ["0-1"] * len(self._pickers)

        # 恢复光标为手型
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.update()

    def get_image(self):
        """获取当前图片"""
        return self._image

    def get_picker_zones(self):
        """获取所有取色器的区域编号"""
        return self._picker_zones.copy()
