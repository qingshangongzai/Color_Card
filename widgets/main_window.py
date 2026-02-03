from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from qfluentwidgets import FluentWindow, NavigationItemPosition, qrouter, FluentIcon

from .image_canvas import ImageCanvas
from .color_card import ColorCardPanel
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
        self.color_extract_interface = ColorExtractInterface(self)
        self.color_extract_interface.setObjectName('colorExtract')
        qrouter.setDefaultRouteKey(self.stackedWidget, 'colorExtract')
        self.stackedWidget.addWidget(self.color_extract_interface)
    
    def setup_navigation(self):
        """设置导航栏"""
        self.addSubInterface(
            self.color_extract_interface,
            FluentIcon.PALETTE,
            "色彩提取",
            position=NavigationItemPosition.TOP
        )
    
    def open_image(self):
        """打开图片"""
        self.color_extract_interface.open_image()
