# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QSplitter, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon

# 项目模块导入
from core import get_color_info
from ..canvases import ImageCanvas
from ..widgets import ColorCardPanel, HSBColorWheel, RGBHistogramWidget


class ColorExtractInterface(QWidget):
    """色彩提取界面"""

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

        # 主分割器（垂直）
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(main_splitter, stretch=1)

        # 上半部分：水平分割器（图片 + 右侧组件）
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setMinimumHeight(300)

        # 左侧：图片画布
        self.image_canvas = ImageCanvas()
        self.image_canvas.setMinimumWidth(400)
        top_splitter.addWidget(self.image_canvas)

        # 右侧：垂直分割器（HSB色环 + RGB直方图）
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setMinimumWidth(200)
        right_splitter.setMaximumWidth(350)

        # HSB色环
        self.hsb_color_wheel = HSBColorWheel()
        right_splitter.addWidget(self.hsb_color_wheel)

        # RGB直方图
        self.rgb_histogram_widget = RGBHistogramWidget()
        right_splitter.addWidget(self.rgb_histogram_widget)

        right_splitter.setSizes([200, 150])
        top_splitter.addWidget(right_splitter)

        # 设置左右比例
        top_splitter.setSizes([600, 250])
        main_splitter.addWidget(top_splitter)

        # 下半部分：色卡面板
        self.color_card_panel = ColorCardPanel()
        self.color_card_panel.setMinimumHeight(200)
        main_splitter.addWidget(self.color_card_panel)

        main_splitter.setSizes([450, 220])

    def setup_connections(self):
        """设置信号连接"""
        self.image_canvas.color_picked.connect(self.on_color_picked)
        self.image_canvas.image_loaded.connect(self.on_image_loaded)
        self.image_canvas.image_data_loaded.connect(self.on_image_data_loaded)
        self.image_canvas.open_image_requested.connect(self.open_image)
        self.image_canvas.change_image_requested.connect(self.open_image)
        self.image_canvas.clear_image_requested.connect(self.clear_image)
        self.image_canvas.image_cleared.connect(self.on_image_cleared)

    def open_image(self):
        """打开图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if file_path:
            self.image_canvas.set_image(file_path)

    def on_image_loaded(self, file_path):
        """图片加载完成回调"""
        pass

    def on_image_data_loaded(self, pixmap, image):
        """图片数据加载完成回调（用于同步到其他面板）"""
        window = self.window()
        if window and hasattr(window, 'sync_image_data_to_luminance'):
            # 立即同步图片数据到明度面板（只设置图片，不计算）
            # 明度面板会自己延迟执行耗时操作
            window.sync_image_data_to_luminance(pixmap, image)

        # 更新RGB直方图
        self.rgb_histogram_widget.set_image(image)

    def on_color_picked(self, index, rgb):
        """颜色提取回调"""
        color_info = get_color_info(*rgb)
        self.color_card_panel.update_color(index, color_info)
        # 更新HSB色环上的采样点
        self.hsb_color_wheel.update_sample_point(index, rgb)

    def clear_image(self):
        """清空图片"""
        self.image_canvas.clear_image()
        self.color_card_panel.clear_all()
        # 清除HSB色环和RGB直方图
        self.hsb_color_wheel.clear_sample_points()
        self.rgb_histogram_widget.clear()

    def on_image_cleared(self):
        """图片已清空回调（同步清除明度面板）"""
        # 同步清除明度提取面板
        window = self.window()
        if window and hasattr(window, 'sync_clear_to_luminance'):
            window.sync_clear_to_luminance()
