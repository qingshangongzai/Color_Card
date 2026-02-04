# 第三方库导入
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

# 项目模块导入
from ..canvases import LuminanceCanvas
from ..histograms import LuminanceHistogramWidget


class LuminanceExtractInterface(QWidget):
    """明度提取界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging_index = -1  # 当前正在拖动的采样点索引
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter, stretch=1)

        self.luminance_canvas = LuminanceCanvas()
        splitter.addWidget(self.luminance_canvas)

        self.histogram_widget = LuminanceHistogramWidget()
        splitter.addWidget(self.histogram_widget)

        splitter.setSizes([400, 150])

    def setup_connections(self):
        """设置信号连接"""
        self.luminance_canvas.luminance_picked.connect(self.on_luminance_picked)
        self.luminance_canvas.image_loaded.connect(self.on_image_loaded)
        self.luminance_canvas.open_image_requested.connect(self.open_image)
        self.luminance_canvas.change_image_requested.connect(self.change_image)
        self.luminance_canvas.clear_image_requested.connect(self.clear_image)
        self.luminance_canvas.image_cleared.connect(self.on_image_cleared)
        self.luminance_canvas.picker_dragging.connect(self.on_picker_dragging)

        # 连接直方图点击信号
        self.histogram_widget.zone_pressed.connect(self.on_histogram_zone_pressed)
        self.histogram_widget.zone_released.connect(self.on_histogram_zone_released)

    def open_image(self):
        """打开图片文件（由主窗口处理）"""
        # 实际打开操作由主窗口处理，然后同步到本界面
        window = self.window()
        if window and hasattr(window, 'open_image_for_luminance'):
            window.open_image_for_luminance()

    def change_image(self):
        """更换图片（由主窗口处理）"""
        window = self.window()
        if window and hasattr(window, 'open_image_for_luminance'):
            window.open_image_for_luminance()

    def set_image(self, image_path):
        """设置图片（由主窗口调用同步）"""
        self.luminance_canvas.set_image(image_path)
        self.histogram_widget.set_image(self.luminance_canvas.get_image())
        # 导入图片时不显示高亮
        self.histogram_widget.clear_highlight()

    def set_image_data(self, pixmap, image):
        """设置图片数据（直接使用已加载的图片，避免重复加载）"""
        self.luminance_canvas.set_image_data(pixmap, image)
        # 延迟更新直方图，避免与区域提取同时执行
        QTimer.singleShot(400, lambda: self._update_histogram_with_image(image))

    def _update_histogram_with_image(self, image):
        """更新直方图（延迟执行）"""
        self.histogram_widget.set_image(image)
        # 导入图片时不显示高亮
        self.histogram_widget.clear_highlight()

    def on_image_loaded(self, file_path):
        """图片加载完成回调"""
        # 更新直方图
        self.histogram_widget.set_image(self.luminance_canvas.get_image())
        # 导入图片时不显示高亮
        self.histogram_widget.clear_highlight()

    def on_luminance_picked(self, index, zone):
        """明度提取回调 - 拖动时实时更新黄框"""
        # 只在拖动过程中更新高亮
        if self._dragging_index == index:
            self.histogram_widget.set_highlight_zones([zone])

    def on_picker_dragging(self, index, is_dragging):
        """取色点拖动状态回调

        Args:
            index: 取色点索引
            is_dragging: 是否正在拖动
        """
        if is_dragging:
            # 记录正在拖动的采样点索引
            self._dragging_index = index
            # 显示当前拖动采样点的区域高亮
            zones = self.luminance_canvas.get_picker_zones()
            if 0 <= index < len(zones):
                self.histogram_widget.set_highlight_zones([zones[index]])
        else:
            # 拖动结束，清除记录和高亮
            self._dragging_index = -1
            self.histogram_widget.clear_highlight()

    def update_histogram_highlight(self):
        """更新直方图高亮区域（仅在拖动时使用）"""
        zones = self.luminance_canvas.get_picker_zones()
        # 去重
        unique_zones = list(set(zones))
        self.histogram_widget.set_highlight_zones(unique_zones)

    def clear_image(self):
        """清空图片"""
        self.luminance_canvas.clear_image()
        self.histogram_widget.clear()

    def on_image_cleared(self):
        """图片已清空回调（同步清除色彩面板）"""
        # 同步清除色彩提取面板
        window = self.window()
        if window and hasattr(window, 'sync_clear_to_color'):
            window.sync_clear_to_color()

    def on_histogram_zone_pressed(self, zone):
        """直方图Zone被按下时调用

        Args:
            zone: Zone编号 (0-7)
        """
        # 在画布上高亮显示该Zone的亮度范围
        self.luminance_canvas.highlight_zone(zone)

    def on_histogram_zone_released(self):
        """直方图Zone被释放时调用"""
        # 清除画布上的高亮显示
        self.luminance_canvas.clear_zone_highlight()
