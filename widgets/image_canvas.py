"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: image_canvas
功能描述: 图片画布组件，支持图片显示、拖拽打开、取色点拖动

作者: 青山公仔
创建日期: 2026-02-04
"""

# 标准库导入
from typing import Optional

# 第三方库导入
from PySide6.QtCore import QPoint, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget
from qfluentwidgets import IndeterminateProgressRing

# 项目模块导入
from .base_canvas import BaseCanvas
from .color_picker import ColorPicker
from .zoom_viewer import ZoomViewer


class ImageCanvas(BaseCanvas):
    """图片显示画布，支持取色点拖动"""

    color_picked = Signal(int, tuple)  # 信号：索引, RGB颜色
    picker_moved = Signal(int, tuple)  # 信号：索引, (rel_x, rel_y)
    picker_dragging = Signal(int, bool)  # 信号：索引, 是否正在拖动

    def __init__(self, parent: Optional[QWidget] = None, picker_count: int = 5) -> None:
        super().__init__(parent, picker_count)
        self.setMouseTracking(True)

        self._pickers: list = []
        self._zoom_viewer: Optional[ZoomViewer] = None
        self._active_picker_index: int = -1
        self._loading_indicator: Optional[IndeterminateProgressRing] = None

        # 创建加载指示器
        self._loading_indicator = IndeterminateProgressRing(self)
        self._loading_indicator.setFixedSize(64, 64)
        self._loading_indicator.hide()

        # 创建放大视图
        self._zoom_viewer = ZoomViewer(self)

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

        self.update_picker_positions()
        self._update_loading_indicator_position()

    def _update_loading_indicator_position(self) -> None:
        """更新加载指示器位置到中心"""
        if self._loading_indicator:
            x = (self.width() - self._loading_indicator.width()) // 2
            y = (self.height() - self._loading_indicator.height()) // 2
            self._loading_indicator.move(x, y)

    def set_image(self, image_path: str) -> None:
        """异步加载并显示图片"""
        # 显示加载指示器
        if self._loading_indicator:
            self._loading_indicator.start()
            self._loading_indicator.show()
            self._update_loading_indicator_position()

        super().set_image(image_path)

    def _on_image_loaded(self, image_data: bytes, width: int, height: int, fmt: str) -> None:
        """图片加载完成的回调"""
        super()._on_image_loaded(image_data, width, height, fmt)

        # 隐藏加载指示器
        if self._loading_indicator:
            self._loading_indicator.stop()
            self._loading_indicator.hide()

        # 改变光标为默认
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_image_load_error(self, error_msg: str) -> None:
        """图片加载失败的回调"""
        # 隐藏加载指示器
        if self._loading_indicator:
            self._loading_indicator.stop()
            self._loading_indicator.hide()

        # 恢复光标
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        print(f"图片加载失败: {error_msg}")

    def _setup_after_load(self) -> None:
        """图片加载完成后的设置"""
        if self._original_pixmap and not self._original_pixmap.isNull():
            # 设置放大视图的图片
            if self._zoom_viewer:
                self._zoom_viewer.set_image(self._image)

            # 显示取色点
            for picker in self._pickers:
                picker.show()

            # 初始化取色点位置
            self._init_picker_positions()
            self.update_picker_positions()
            self.update()

            # 发送图片加载信号
            if self._pending_image_path:
                self.image_loaded.emit(self._pending_image_path)
                # 同时发送图片数据信号，用于同步到其他面板
                self.image_data_loaded.emit(self._original_pixmap, self._image)

            # 延迟提取颜色，让UI先响应，用户可以立即切换面板
            QTimer.singleShot(300, self.extract_all)

    def _update_picker_position(self, index: int, canvas_x: int, canvas_y: int) -> None:
        """更新单个取色点的位置"""
        if index < len(self._pickers):
            picker = self._pickers[index]
            picker.move(canvas_x - picker.radius, canvas_y - picker.radius)

    def _on_picker_drag_started(self, index: int) -> None:
        """取色点开始拖动"""
        self._active_picker_index = index
        if self._zoom_viewer:
            self._zoom_viewer.show()
        self._update_zoom_viewer()
        self.picker_dragging.emit(index, True)

    def _on_picker_drag_finished(self, index: int) -> None:
        """取色点结束拖动"""
        if self._zoom_viewer:
            self._zoom_viewer.hide()
        self._active_picker_index = -1
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

    def _on_picker_removed(self, index: int) -> None:
        """移除取色点时的回调"""
        if index < len(self._pickers):
            picker = self._pickers.pop()
            picker.deleteLater()

    def _update_zoom_viewer(self) -> None:
        """更新放大视图的位置和内容"""
        if self._active_picker_index < 0 or self._image is None or not self._zoom_viewer:
            return

        picker_pos = self._picker_positions[self._active_picker_index]

        # 更新放大视图位置
        self._zoom_viewer.update_position(picker_pos)

        # 计算原始图片中的坐标
        image_pos = self.canvas_to_image_pos(picker_pos)
        if image_pos:
            self._zoom_viewer.set_center_position(image_pos)

    def extract_at(self, index: int) -> None:
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
            if index < len(self._pickers):
                self._pickers[index].set_color(color)

            # 发送信号
            self.color_picked.emit(index, rgb)

        # 更新放大视图
        self._update_zoom_viewer()

    def extract_all(self) -> None:
        """提取所有取色点的颜色"""
        for i in range(len(self._pickers)):
            self.extract_at(i)

    def resizeEvent(self, event) -> None:
        """窗口大小改变时重新调整图片"""
        super().resizeEvent(event)
        self._update_loading_indicator_position()

    def clear_image(self) -> None:
        """清空图片"""
        super().clear_image()

        # 隐藏取色点和放大视图
        for picker in self._pickers:
            picker.hide()
        if self._zoom_viewer:
            self._zoom_viewer.hide()
