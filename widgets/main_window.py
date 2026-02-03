from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from qfluentwidgets import FluentWindow, NavigationItemPosition, qrouter, FluentIcon

from .image_canvas import ImageCanvas
from .color_card import ColorCardPanel
from .luminance_canvas import LuminanceCanvas
from .histogram_widget import HistogramWidget
from color_utils import get_color_info


class ColorExtractInterface(QWidget):
    """色彩提取界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter, stretch=1)

        self.image_canvas = ImageCanvas()
        splitter.addWidget(self.image_canvas)

        self.color_card_panel = ColorCardPanel()
        self.color_card_panel.setMaximumHeight(280)
        splitter.addWidget(self.color_card_panel)

        splitter.setSizes([500, 200])
    
    def setup_connections(self):
        """设置信号连接"""
        self.image_canvas.color_picked.connect(self.on_color_picked)
        self.image_canvas.image_loaded.connect(self.on_image_loaded)
        self.image_canvas.open_image_requested.connect(self.open_image)
        self.image_canvas.change_image_requested.connect(self.open_image)
        self.image_canvas.clear_image_requested.connect(self.clear_image)
    
    def open_image(self):
        """打开图片文件"""
        from PySide6.QtWidgets import QFileDialog
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
        window = self.window()
        if window:
            window.setWindowTitle(f"Color Extractor - {file_path.split('/')[-1]}")
            # 同步图片到明度提取面板
            if hasattr(window, 'sync_image_to_luminance'):
                window.sync_image_to_luminance(file_path)
    
    def on_color_picked(self, index, rgb):
        """颜色提取回调"""
        color_info = get_color_info(*rgb)
        self.color_card_panel.update_color(index, color_info)

    def clear_image(self):
        """清空图片"""
        self.image_canvas.clear_image()
        self.color_card_panel.clear_colors()

        # 重置窗口标题
        window = self.window()
        if window:
            window.setWindowTitle("Color Extractor - 图片颜色提取器")


class LuminanceExtractInterface(QWidget):
    """明度提取界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
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

        self.histogram_widget = HistogramWidget()
        splitter.addWidget(self.histogram_widget)

        splitter.setSizes([400, 150])

    def setup_connections(self):
        """设置信号连接"""
        self.luminance_canvas.luminance_picked.connect(self.on_luminance_picked)
        self.luminance_canvas.image_loaded.connect(self.on_image_loaded)
        self.luminance_canvas.open_image_requested.connect(self.open_image)
        self.luminance_canvas.change_image_requested.connect(self.change_image)
        self.luminance_canvas.clear_image_requested.connect(self.clear_image)

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
        self.update_histogram_highlight()

    def on_image_loaded(self, file_path):
        """图片加载完成回调"""
        # 更新直方图
        self.histogram_widget.set_image(self.luminance_canvas.get_image())
        self.update_histogram_highlight()

    def on_luminance_picked(self, index, zone):
        """明度提取回调"""
        self.update_histogram_highlight()

    def update_histogram_highlight(self):
        """更新直方图高亮区域"""
        zones = self.luminance_canvas.get_picker_zones()
        # 去重
        unique_zones = list(set(zones))
        self.histogram_widget.set_highlight_zones(unique_zones)

    def clear_image(self):
        """清空图片"""
        self.luminance_canvas.clear_image()
        self.histogram_widget.clear()


class MainWindow(FluentWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Extractor - 图片颜色提取器")
        self.setMinimumSize(800, 550)
        self.resize(940, 660)

        self.create_sub_interface()
        self.setup_navigation()

    def create_sub_interface(self):
        """创建子界面"""
        # 色彩提取界面
        self.color_extract_interface = ColorExtractInterface(self)
        self.color_extract_interface.setObjectName('colorExtract')
        qrouter.setDefaultRouteKey(self.stackedWidget, 'colorExtract')
        self.stackedWidget.addWidget(self.color_extract_interface)

        # 明度提取界面
        self.luminance_extract_interface = LuminanceExtractInterface(self)
        self.luminance_extract_interface.setObjectName('luminanceExtract')
        self.stackedWidget.addWidget(self.luminance_extract_interface)

    def setup_navigation(self):
        """设置导航栏"""
        # 色彩提取
        self.addSubInterface(
            self.color_extract_interface,
            FluentIcon.PALETTE,
            "色彩提取",
            position=NavigationItemPosition.TOP
        )

        # 明度提取
        self.addSubInterface(
            self.luminance_extract_interface,
            FluentIcon.BRIGHTNESS,
            "明度提取",
            position=NavigationItemPosition.TOP
        )

    def open_image(self):
        """打开图片（从色彩提取界面调用）"""
        self.color_extract_interface.open_image()

    def open_image_for_luminance(self):
        """为明度提取打开图片（实际同步到色彩提取）"""
        # 调用色彩提取的打开图片功能，然后同步到明度提取
        self.color_extract_interface.open_image()

    def sync_image_to_luminance(self, image_path):
        """同步图片到明度提取面板"""
        if image_path:
            self.luminance_extract_interface.set_image(image_path)
