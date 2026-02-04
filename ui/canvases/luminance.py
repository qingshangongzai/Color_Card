# 标准库导入
from typing import List, Optional, Tuple

# 第三方库导入
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

# 项目模块导入
from core import get_luminance, get_zone
from .base import BaseCanvas
from ..widgets import ColorPicker


class LuminanceCanvas(BaseCanvas):
    """明度提取画布，支持取色点拖动和区域标注"""

    luminance_picked = Signal(int, str)  # 信号：索引, 区域编号
    picker_dragging = Signal(int, bool)  # 信号：索引, 是否正在拖动

    def __init__(self, parent: Optional[QWidget] = None, picker_count: int = 5) -> None:
        super().__init__(parent, picker_count)

        self._pickers: List[ColorPicker] = []
        self._picker_zones: List[str] = []  # 存储每个取色器的区域编号

        # Zone高亮相关
        self._highlighted_zone: int = -1  # 当前高亮显示的Zone (-1表示无)
        self._zone_highlight_pixmap: Optional[QPixmap] = None  # 高亮遮罩缓存

        # Zone高亮颜色配置 (Zone 0-7)
        self._zone_highlight_colors: List[QColor] = [
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
            picker.drag_started.connect(self._on_picker_drag_started)
            picker.drag_finished.connect(self._on_picker_drag_finished)
            picker.hide()  # 初始隐藏
            self._pickers.append(picker)
            self._picker_positions.append(QPoint(100 + i * 100, 100))
            self._picker_rel_positions.append(QPointF(0.5, 0.5))  # 默认在图片中心
            self._picker_zones.append("0-1")

        self.update_picker_positions()

    def _on_image_load_error(self, error_msg: str) -> None:
        """图片加载失败的回调"""
        print(f"明度面板图片加载失败: {error_msg}")

    def _setup_after_load(self) -> None:
        """图片加载完成后的设置"""
        if self._original_pixmap and not self._original_pixmap.isNull():
            # 显示取色点
            for picker in self._pickers:
                picker.show()

            # 改变光标为默认
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # 初始化取色点位置
            self._init_picker_positions()
            self.update_picker_positions()
            self.update()

            # 延迟提取区域，让UI先响应，用户可以立即切换面板
            from PySide6.QtCore import QTimer
            QTimer.singleShot(300, self.extract_all)

    def _update_picker_position(self, index: int, canvas_x: int, canvas_y: int) -> None:
        """更新单个取色点的位置"""
        if index < len(self._pickers):
            picker = self._pickers[index]
            picker.move(canvas_x - picker.radius, canvas_y - picker.radius)

    def _on_picker_drag_started(self, index: int) -> None:
        """取色点开始拖动"""
        if index < len(self._pickers):
            picker = self._pickers[index]
            picker.set_active(True)
        self.picker_dragging.emit(index, True)

    def _on_picker_drag_finished(self, index: int) -> None:
        """取色点结束拖动"""
        if index < len(self._pickers):
            picker = self._pickers[index]
            picker.set_active(False)
        self.picker_dragging.emit(index, False)

    def _on_picker_added(self, index: int) -> None:
        """添加取色点时的回调"""
        picker = ColorPicker(index, self)
        picker.position_changed.connect(self.on_picker_moved)
        picker.drag_started.connect(self._on_picker_drag_started)
        picker.drag_finished.connect(self._on_picker_drag_finished)
        # 如果有图片，显示取色点
        if self._image and not self._image.isNull():
            picker.show()
        else:
            picker.hide()
        self._pickers.append(picker)
        self._picker_zones.append("0-1")

    def _on_picker_removed(self, index: int) -> None:
        """移除取色点时的回调"""
        if index < len(self._pickers):
            picker = self._pickers.pop()
            picker.deleteLater()
            self._picker_zones.pop()

    def extract_at(self, index: int) -> None:
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

    def extract_all(self) -> None:
        """提取所有取色点的区域编号"""
        for i in range(len(self._pickers)):
            self.extract_at(i)

    def _draw_overlay(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制叠加内容"""
        # 绘制Zone高亮遮罩（在图片上方）
        self._draw_zone_highlight(painter, display_rect)

        # 绘制区域标注
        self._draw_zone_labels(painter, display_rect)

    def _draw_zone_labels(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
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

    def clear_image(self) -> None:
        """清空图片"""
        super().clear_image()

        # 隐藏取色点
        for picker in self._pickers:
            picker.hide()

        # 重置区域编号
        self._picker_zones = ["0-1"] * len(self._pickers)

    def get_picker_zones(self) -> List[str]:
        """获取所有取色器的区域编号

        Returns:
            list: 区域编号列表
        """
        return self._picker_zones.copy()

    def highlight_zone(self, zone: int) -> None:
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

    def clear_zone_highlight(self) -> None:
        """清除Zone高亮显示"""
        self._highlighted_zone = -1
        self._zone_highlight_pixmap = None
        self.update()

    def _generate_zone_highlight_pixmap(self, display_rect: Tuple[int, int, int, int]) -> Optional[QPixmap]:
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

    def _draw_zone_highlight(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
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

    def _draw_zone_highlight_info(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
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
