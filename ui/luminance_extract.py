"""明度提取界面模块

提供图片明度提取和分析功能，包含明度画布和直方图显示。
"""

# 标准库导入
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFileDialog, QSplitter, QVBoxLayout, QWidget

# 项目模块导入
from core import LuminanceService
from utils import tr, get_locale_manager
from .canvases import LuminanceCanvas
from .histograms import LuminanceHistogramWidget


class LuminanceExtractInterface(QWidget):
    """明度提取界面"""

    # 信号：图片已独立导入（用于同步到色彩提取面板）
    image_imported = Signal(str, object, object)  # 图片路径, QPixmap, QImage

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging_index = -1
        self._luminance_service = LuminanceService(self)
        self.setup_ui()
        self.setup_connections()
        self._setup_service_connections()
        get_locale_manager().language_changed.connect(self._on_language_changed)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setMinimumHeight(300)
        splitter.setHandleWidth(0)  # 隐藏分隔条
        layout.addWidget(splitter, stretch=1)

        self.luminance_canvas = LuminanceCanvas()
        self.luminance_canvas.setMinimumHeight(200)
        splitter.addWidget(self.luminance_canvas)

        self.histogram_widget = LuminanceHistogramWidget()
        self.histogram_widget.setMinimumHeight(120)
        self.histogram_widget.setMaximumHeight(250)
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

        # 连接图片加载信号到同步回调（用于独立导入时同步到色彩面板）
        self.luminance_canvas.image_loaded.connect(self._on_image_loaded_sync)

        # 连接直方图点击信号
        self.histogram_widget.zone_pressed.connect(self.on_histogram_zone_pressed)
        self.histogram_widget.zone_released.connect(self.on_histogram_zone_released)

    def _setup_service_connections(self):
        """设置LuminanceService信号连接"""
        self._luminance_service.calculation_finished.connect(self._on_luminance_calculation_finished)
        self._luminance_service.calculation_error.connect(self._on_luminance_calculation_error)

    def _on_luminance_calculation_finished(self, result: dict):
        """明度计算完成回调

        Args:
            result: 计算结果字典，包含distribution等信息
        """
        # 可以在这里处理计算结果，如更新UI显示
        pass

    def _on_luminance_calculation_error(self, error_msg: str):
        """明度计算错误回调

        Args:
            error_msg: 错误信息
        """
        print(f"明度计算错误: {error_msg}")

    def open_image(self):
        """打开图片文件（独立导入）"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr('luminance_extract.select_image'),
            "",
            tr('luminance_extract.image_filter')
        )

        if file_path:
            self._load_image(file_path)

    def change_image(self):
        """更换图片"""
        self.open_image()

    def _load_image(self, file_path: str):
        """加载图片并同步到色彩提取面板

        Args:
            file_path: 图片文件路径
        """
        self.luminance_canvas.set_image(file_path)

    def _on_image_loaded_sync(self, file_path: str):
        """图片加载完成后的同步回调

        Args:
            file_path: 图片文件路径
        """
        # 更新直方图
        self.histogram_widget.set_image(self.luminance_canvas.get_image())
        # 导入图片时不显示高亮
        self.histogram_widget.clear_highlight()

        # 发送信号，同步到色彩提取面板
        pixmap = self.luminance_canvas._original_pixmap
        image = self.luminance_canvas._image
        if pixmap and not pixmap.isNull() and image and not image.isNull():
            self.image_imported.emit(file_path, pixmap, image)

    def set_image(self, image_path):
        """设置图片（由主窗口调用同步）"""
        self.luminance_canvas.set_image(image_path)
        self.histogram_widget.set_image(self.luminance_canvas.get_image())
        # 导入图片时不显示高亮
        self.histogram_widget.clear_highlight()

    def set_image_data(self, pixmap, image, emit_sync=True):
        """设置图片数据（直接使用已加载的图片，避免重复加载）

        Args:
            pixmap: QPixmap 对象
            image: QImage 对象
            emit_sync: 是否发射同步信号（默认True，从其他面板同步时设为False）
        """
        self.luminance_canvas.set_image_data(pixmap, image, emit_sync=emit_sync)
        # 延迟更新直方图，避免与区域提取同时执行
        QTimer.singleShot(400, lambda: self._update_histogram_with_image(image))

    def _update_histogram_with_image(self, image):
        """更新直方图（延迟执行）"""
        self.histogram_widget.set_image(image)
        # 导入图片时不显示高亮
        self.histogram_widget.clear_highlight()

    def on_image_loaded(self, file_path):
        """图片加载完成回调（由主窗口同步时调用）"""
        # 直方图更新已在 _on_image_loaded_sync 中处理
        pass

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

    def clear_all(self, emit_signal: bool = True):
        """清空所有相关内容（图片、直方图）

        Args:
            emit_signal: 是否发射清空信号（默认True，从其他面板同步时设为False）
        """
        self.luminance_canvas.clear_image(emit_signal)
        self.histogram_widget.clear()

    def clear_image(self):
        """清空图片（供外部调用，会发射信号同步到其他面板）"""
        self.clear_all(emit_signal=True)

    def on_image_cleared(self):
        """图片已清空回调（同步清除色彩面板）"""
        window = self.window()
        if window and hasattr(window, '_image_mediator'):
            window._image_mediator.clear_image('luminance')

    def on_histogram_zone_pressed(self, zone):
        """直方图Zone被按下时调用

        Args:
            zone: Zone编号 (0-7)
        """
        # 在画布上高亮显示该Zone的亮度范围
        self.luminance_canvas.highlight_zone(zone)

    def on_histogram_zone_released(self):
        """直方图Zone被释放时调用"""
        self.luminance_canvas.clear_zone_highlight()

    def _on_language_changed(self):
        """语言切换回调"""
        self.update_texts()

    def update_texts(self):
        """更新界面文本（语言切换时调用）"""
        pass
