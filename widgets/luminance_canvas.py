"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: luminance_canvas
功能描述: 明度画布组件，支持图片显示、明度提取、区域选择

作者: 青山公仔
创建日期: 2026-02-04
"""

# 标准库导入
import io

# 第三方库导入
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget
from qfluentwidgets import Action, FluentIcon, RoundMenu

# 项目模块导入
from color_utils import get_luminance, get_zone
from .color_picker import ColorPicker


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
    image_cleared = Signal()  # 信号：图片已清空（用于同步到其他面板）
    picker_dragging = Signal(int, bool)  # 信号：索引, 是否正在拖动

    def __init__(self, parent=None, picker_count=5):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #2a2a2a; border-radius: 8px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._original_pixmap = None
        self._image = None
        self._pickers = []
        self._picker_positions = []
        self._picker_rel_positions = []  # 存储相对于图片的归一化坐标 (0.0-1.0)
        self._picker_zones = []  # 存储每个取色器的区域编号
        self._loader = None
        self._pending_image_path = None
        self._picker_count = picker_count

        # Zone高亮相关
        self._highlighted_zone = -1  # 当前高亮显示的Zone (-1表示无)
        self._zone_highlight_pixmap = None  # 高亮遮罩缓存

        # Zone高亮颜色配置 (Zone 0-7)
        self._zone_highlight_colors = [
            QColor(0, 102, 255, 100),    # Zone 0: 深蓝色 (极暗)
            QColor(0, 128, 255, 100),    # Zone 1: 蓝色 (暗)
            QColor(0, 153, 255, 100),    # Zone 2: 浅蓝色 (偏暗)
            QColor(0, 204, 102, 100),    # Zone 3: 绿色 (中灰)
            QColor(102, 255, 102, 100),  # Zone 4: 浅绿色 (偏亮)
            QColor(255, 204, 0, 100),    # Zone 5: 黄色 (亮)
            QColor(255, 128, 0, 100),    # Zone 6: 橙色 (很亮)
            QColor(255, 51, 102, 100),   # Zone 7: 红色 (极亮)
        ]

        # 创建取色点（初始隐藏）
        for i in range(self._picker_count):
            picker = ColorPicker(i, self)
            picker.position_changed.connect(self.on_picker_moved)
            picker.drag_started.connect(self.on_picker_drag_started)
            picker.drag_finished.connect(self.on_picker_drag_finished)
            picker.hide()  # 初始隐藏
            self._pickers.append(picker)
            self._picker_positions.append(QPoint(100 + i * 100, 100))
            self._picker_rel_positions.append(QPointF(0.5, 0.5))  # 默认在图片中心
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
            center_x = 0.5  # 使用相对坐标，中心为 0.5
            center_y = 0.5
            for i, picker in enumerate(self._pickers):
                offset_x = (i - 2) * 0.05  # 使用相对偏移（5%）
                self._picker_rel_positions[i] = QPointF(center_x + offset_x, center_y)

            self.update_picker_positions()
            self.update()

            # 延迟提取区域，让UI先响应，用户可以立即切换面板
            QTimer.singleShot(300, self.extract_all_zones)

    def update_picker_positions(self):
        """更新所有取色点的位置"""
        # 如果有图片，使用相对坐标计算画布坐标
        if self._image and not self._image.isNull():
            display_rect = self.get_display_rect()
            if display_rect:
                disp_x, disp_y, disp_w, disp_h = display_rect
                
                for i, picker in enumerate(self._pickers):
                    rel_pos = self._picker_rel_positions[i]
                    
                    # 将相对坐标转换为画布坐标
                    canvas_x = disp_x + rel_pos.x() * disp_w
                    canvas_y = disp_y + rel_pos.y() * disp_h
                    
                    # 更新画布坐标存储
                    self._picker_positions[i] = QPoint(int(canvas_x), int(canvas_y))
                    
                    # 更新取色点显示位置
                    picker.move(self._picker_positions[i].x() - picker.radius, 
                               self._picker_positions[i].y() - picker.radius)
        else:
            # 没有图片时，直接使用存储的画布坐标
            for i, picker in enumerate(self._pickers):
                pos = self._picker_positions[i]
                picker.move(pos.x() - picker.radius, pos.y() - picker.radius)

    def set_picker_count(self, count):
        """设置取色点数量

        Args:
            count: 取色点数量 (2-5)
        """
        if count < 2 or count > 5:
            return

        if count == self._picker_count:
            return

        old_count = self._picker_count
        self._picker_count = count

        if count > old_count:
            # 增加取色点
            for i in range(old_count, count):
                picker = ColorPicker(i, self)
                picker.position_changed.connect(self.on_picker_moved)
                picker.drag_started.connect(self.on_picker_drag_started)
                picker.drag_finished.connect(self.on_picker_drag_finished)
                # 如果有图片，显示取色点
                if self._image and not self._image.isNull():
                    picker.show()
                else:
                    picker.hide()
                self._pickers.append(picker)
                # 新取色点位置在最后一个取色点旁边
                if old_count > 0:
                    last_rel_pos = self._picker_rel_positions[-1]
                    new_rel_pos = QPointF(last_rel_pos.x() + 0.05, last_rel_pos.y())
                else:
                    new_rel_pos = QPointF(0.5, 0.5)  # 默认在中心
                self._picker_positions.append(QPoint(100, 100))  # 临时画布坐标
                self._picker_rel_positions.append(new_rel_pos)
                self._picker_zones.append("0-1")
        else:
            # 减少取色点
            for i in range(old_count - 1, count - 1, -1):
                picker = self._pickers.pop()
                picker.deleteLater()
                self._picker_positions.pop()
                self._picker_rel_positions.pop()
                self._picker_zones.pop()

        self.update_picker_positions()

        # 如果有图片，重新提取区域
        if self._image and not self._image.isNull():
            self.extract_all_zones()

    def on_picker_drag_started(self, index):
        """取色点开始拖动"""
        picker = self._pickers[index]
        picker.set_active(True)
        self.picker_dragging.emit(index, True)

    def on_picker_drag_finished(self, index):
        """取色点结束拖动"""
        picker = self._pickers[index]
        picker.set_active(False)
        self.picker_dragging.emit(index, False)

    def on_picker_moved(self, index, new_pos):
        """取色点移动时的回调"""
        # 更新画布坐标
        self._picker_positions[index] = new_pos
        
        # 如果有图片，将画布坐标转换为相对坐标并存储
        if self._image and not self._image.isNull():
            display_rect = self.get_display_rect()
            if display_rect:
                disp_x, disp_y, disp_w, disp_h = display_rect
                
                # 将画布坐标转换为相对坐标
                rel_x = (new_pos.x() - disp_x) / disp_w
                rel_y = (new_pos.y() - disp_y) / disp_h
                
                # 限制在图片范围内
                rel_x = max(0.0, min(1.0, rel_x))
                rel_y = max(0.0, min(1.0, rel_y))
                
                # 更新相对坐标
                self._picker_rel_positions[index] = QPointF(rel_x, rel_y)
        
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

                # 绘制Zone高亮遮罩（在图片上方）
                self._draw_zone_highlight(painter, display_rect)

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
            # 窗口大小改变时，更新取色点位置并重新提取区域
            self.update_picker_positions()
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
        
        # 重置相对坐标到默认位置
        for i in range(len(self._picker_rel_positions)):
            self._picker_rel_positions[i] = QPointF(0.5, 0.5)

        # 恢复光标为手型
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.update()

        # 发送图片已清空信号，用于同步到其他面板
        self.image_cleared.emit()

    def get_image(self):
        """获取当前图片"""
        return self._image

    def get_picker_zones(self):
        """获取所有取色器的区域编号"""
        return self._picker_zones.copy()

    def highlight_zone(self, zone):
        """高亮显示指定Zone的亮度范围

        Args:
            zone: Zone编号 (0-7)
        """
        if not (0 <= zone <= 7):
            return

        if self._image is None or self._image.isNull():
            return

        self._highlighted_zone = zone
        self._zone_highlight_pixmap = None  # 清除缓存，重新生成
        self.update()

    def clear_zone_highlight(self):
        """清除Zone高亮显示"""
        self._highlighted_zone = -1
        self._zone_highlight_pixmap = None
        self.update()

    def _generate_zone_highlight_pixmap(self, display_rect):
        """生成Zone高亮遮罩图

        Args:
            display_rect: 图片显示区域 (x, y, w, h)

        Returns:
            QPixmap: 高亮遮罩图
        """
        if self._image is None or self._image.isNull():
            return None

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 创建透明遮罩图
        highlight_pixmap = QPixmap(self.size())
        highlight_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(highlight_pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 获取当前Zone的颜色
        zone_color = self._zone_highlight_colors[self._highlighted_zone]

        # 计算亮度范围
        min_lum = self._highlighted_zone * 32
        max_lum = (self._highlighted_zone + 1) * 32 - 1

        # 计算缩放比例
        scale_x = self._image.width() / disp_w
        scale_y = self._image.height() / disp_h

        # 采样步长（性能优化）
        sample_step = 4

        # 遍历显示区域的像素
        for dy in range(0, disp_h, sample_step):
            for dx in range(0, disp_w, sample_step):
                # 计算对应的原始图片坐标
                img_x = int(dx * scale_x)
                img_y = int(dy * scale_y)

                # 边界检查
                img_x = min(img_x, self._image.width() - 1)
                img_y = min(img_y, self._image.height() - 1)

                # 获取像素颜色并计算亮度
                color = self._image.pixelColor(img_x, img_y)
                luminance = get_luminance(color.red(), color.green(), color.blue())

                # 如果亮度在当前Zone范围内，绘制遮罩
                if min_lum <= luminance <= max_lum:
                    painter.fillRect(
                        disp_x + dx,
                        disp_y + dy,
                        sample_step,
                        sample_step,
                        zone_color
                    )

        painter.end()
        return highlight_pixmap

    def _draw_zone_highlight(self, painter, display_rect):
        """绘制Zone高亮遮罩

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        if self._highlighted_zone < 0:
            return

        # 如果缓存不存在，生成遮罩图
        if self._zone_highlight_pixmap is None:
            self._zone_highlight_pixmap = self._generate_zone_highlight_pixmap(display_rect)

        # 绘制遮罩图
        if self._zone_highlight_pixmap:
            painter.drawPixmap(0, 0, self._zone_highlight_pixmap)

        # 绘制Zone信息提示
        self._draw_zone_highlight_info(painter, display_rect)

    def _draw_zone_highlight_info(self, painter, display_rect):
        """绘制Zone高亮信息提示

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        if self._highlighted_zone < 0:
            return

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 准备文字
        zone_labels = ["0-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7", "7-8"]
        zone_names = [
            "黑色", "阴影", "暗部", "中间调",
            "亮部", "高光", "白色", "极白"
        ]
        label = zone_labels[self._highlighted_zone]
        name = zone_names[self._highlighted_zone]

        # 计算亮度范围
        min_lum = self._highlighted_zone * 32
        max_lum = (self._highlighted_zone + 1) * 32 - 1

        text = f"{label} ({name}) | 亮度: {min_lum}-{max_lum}"

        # 设置字体
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)

        # 计算文字尺寸
        text_rect = painter.boundingRect(QRect(), Qt.AlignmentFlag.AlignLeft, text)
        text_width = text_rect.width()
        text_height = text_rect.height()

        # 背景框位置和尺寸
        padding = 10
        box_width = text_width + padding * 2
        box_height = text_height + padding * 2
        box_x = disp_x + (disp_w - box_width) // 2
        box_y = disp_y + 20

        # 绘制半透明背景框
        bg_color = QColor(0, 0, 0, 180)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(box_x, box_y, box_width, box_height, 6, 6)

        # 绘制文字
        text_color = self._zone_highlight_colors[self._highlighted_zone]
        # 使用不透明版本的颜色
        text_color.setAlpha(255)
        painter.setPen(text_color)
        painter.drawText(
            box_x + padding,
            box_y + padding + text_height - 4,
            text
        )
