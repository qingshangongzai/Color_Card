"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: main_window
功能描述: 主窗口实现，包含色彩提取界面和明度提取界面

作者: 青山公仔
创建日期: 2026-02-04
"""

# 第三方库导入
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QSplitter, QVBoxLayout, QWidget
)
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition, qrouter

# 项目模块导入
from color_utils import get_color_info
from config_manager import get_config_manager
from version import version_manager
from .color_card import ColorCardPanel
from .histogram_widget import HistogramWidget
from .hsb_color_wheel import HSBColorWheel
from .image_canvas import ImageCanvas
from .luminance_canvas import LuminanceCanvas
from .rgb_histogram_widget import RGBHistogramWidget
from .settings_interface import SettingsInterface


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
        self.color_card_panel.clear_colors()
        # 清除HSB色环和RGB直方图
        self.hsb_color_wheel.clear_sample_points()
        self.rgb_histogram_widget.clear()

    def on_image_cleared(self):
        """图片已清空回调（同步清除明度面板）"""
        # 同步清除明度提取面板
        window = self.window()
        if window and hasattr(window, 'sync_clear_to_luminance'):
            window.sync_clear_to_luminance()


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


class MainWindow(FluentWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self._version = version_manager.get_version()
        self.setWindowTitle(f"取色卡 · Color Card · {self._version}")
        self.setMinimumSize(800, 550)

        # 加载配置
        self._config_manager = get_config_manager()
        self._config = self._config_manager.load()

        # 防止清空同步的递归标志
        self._is_clearing = False

        # 应用窗口大小配置
        window_config = self._config.get('window', {})
        width = window_config.get('width', 940)
        height = window_config.get('height', 660)
        is_maximized = window_config.get('is_maximized', False)
        self.resize(width, height)

        self.create_sub_interface()
        self.setup_navigation()

        # 如果之前是最大化状态，恢复最大化
        if is_maximized:
            self.showMaximized()

    def closeEvent(self, event):
        """窗口关闭事件，保存配置"""
        # 保存窗口最大化状态
        is_maximized = self.isMaximized()
        self._config_manager.set('window.is_maximized', is_maximized)

        # 保存窗口大小（如果最大化，保存正常尺寸而非最大化尺寸）
        if is_maximized:
            normal_geometry = self.normalGeometry()
            self._config_manager.set('window.width', normal_geometry.width())
            self._config_manager.set('window.height', normal_geometry.height())
        else:
            self._config_manager.set('window.width', self.width())
            self._config_manager.set('window.height', self.height())

        self._config_manager.save()
        event.accept()

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

        # 设置界面
        self.settings_interface = SettingsInterface(self)
        self.settings_interface.setObjectName('settings')
        self.stackedWidget.addWidget(self.settings_interface)

        # 连接设置信号
        self._setup_settings_connections()

    def setup_navigation(self):
        """设置导航栏"""
        # 隐藏返回按钮
        self.navigationInterface.setReturnButtonVisible(False)

        # 设置导航栏始终展开（禁用折叠）
        # 注意：必须先设置展开宽度，再设置不可折叠，否则展开时会使用默认宽度322
        self.navigationInterface.setExpandWidth(200)
        self.navigationInterface.setCollapsible(False)

        # 添加 Logo 到左上角
        self._setup_logo()

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

        # 设置（放在底部）
        self.addSubInterface(
            self.settings_interface,
            FluentIcon.SETTING,
            "设置",
            position=NavigationItemPosition.BOTTOM
        )

        # 设置默认选中的导航项
        self.navigationInterface.setCurrentItem(self.color_extract_interface.objectName())

    def _setup_logo(self):
        """在导航栏左上角设置 Logo"""
        logo_label = QLabel(self.navigationInterface.panel)
        logo_label.setObjectName('logoLabel')

        # 加载 Logo 图标
        logo_path = 'd:\\青山公仔\\应用\\Py测试\\color_card\\logo\\Color Card_logo.ico'

        # 使用 QIcon 加载 ICO 文件以获取最佳分辨率
        from PySide6.QtCore import QSize
        icon = QIcon(logo_path)

        # 获取设备像素比（支持高 DPI 屏幕）
        pixel_ratio = self.devicePixelRatio()

        # 获取所需尺寸（请求更大的图标以获得更好的质量）
        # 在高 DPI 屏幕上请求更高分辨率的图标
        icon_size = int(64 * pixel_ratio)
        pixmap = icon.pixmap(icon.actualSize(QSize(icon_size, icon_size)))

        if not pixmap.isNull():
            # 将图标缩放到目标显示尺寸（使用高质量缩放）
            target_size = int(28 * pixel_ratio)
            scaled_pixmap = pixmap.scaled(
                target_size, target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            # 设置设备像素比，确保在高 DPI 屏幕上正确显示
            scaled_pixmap.setDevicePixelRatio(pixel_ratio)

            logo_label.setPixmap(scaled_pixmap)
            logo_label.setFixedSize(40, 40)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 将 Logo 插入到导航栏顶部布局的开头（在返回按钮之前）
            top_layout = self.navigationInterface.panel.topLayout
            top_layout.insertWidget(0, logo_label, 0, Qt.AlignTop)

    def open_image(self):
        """打开图片（从色彩提取界面调用）"""
        self.color_extract_interface.open_image()

    def open_image_for_luminance(self):
        """为明度提取打开图片（实际同步到色彩提取）"""
        # 调用色彩提取的打开图片功能，然后同步到明度提取
        self.color_extract_interface.open_image()

    def sync_image_to_luminance(self, image_path):
        """同步图片路径到明度提取面板（保留用于兼容）"""
        if image_path:
            self.luminance_extract_interface.set_image(image_path)

    def sync_image_data_to_luminance(self, pixmap, image):
        """同步图片数据到明度提取面板（避免重复加载）"""
        self.luminance_extract_interface.set_image_data(pixmap, image)

    def sync_clear_to_luminance(self):
        """同步清除明度提取面板"""
        if self._is_clearing:
            return
        self._is_clearing = True
        try:
            self.luminance_extract_interface.luminance_canvas.clear_image()
            self.luminance_extract_interface.histogram_widget.clear()
            self._reset_window_title()
        finally:
            self._is_clearing = False

    def sync_clear_to_color(self):
        """同步清除色彩提取面板"""
        if self._is_clearing:
            return
        self._is_clearing = True
        try:
            self.color_extract_interface.image_canvas.clear_image()
            self.color_extract_interface.color_card_panel.clear_colors()
            self._reset_window_title()
        finally:
            self._is_clearing = False

    def _reset_window_title(self):
        """重置窗口标题"""
        self.setWindowTitle(f"取色卡 · Color Card · {self._version}")

    def _setup_settings_connections(self):
        """连接设置界面的信号"""
        # 连接16进制显示开关信号到色卡面板
        self.settings_interface.hex_display_changed.connect(
            self.color_extract_interface.color_card_panel.set_hex_visible
        )

        # 连接色彩模式改变信号到色卡面板
        self.settings_interface.color_modes_changed.connect(
            self.color_extract_interface.color_card_panel.set_color_modes
        )

        # 连接色彩提取采样点数改变信号
        self.settings_interface.color_sample_count_changed.connect(
            self._on_color_sample_count_changed
        )

        # 连接明度提取采样点数改变信号
        self.settings_interface.luminance_sample_count_changed.connect(
            self._on_luminance_sample_count_changed
        )

        # 应用加载的配置到色卡面板
        hex_visible = self._config_manager.get('settings.hex_visible', True)
        self.color_extract_interface.color_card_panel.set_hex_visible(hex_visible)

        # 应用加载的色彩模式配置到色卡面板
        color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self.color_extract_interface.color_card_panel.set_color_modes(color_modes)

        # 应用加载的采样点数量配置
        color_sample_count = self._config_manager.get('settings.color_sample_count', 5)
        self.color_extract_interface.image_canvas.set_picker_count(color_sample_count)
        self.color_extract_interface.color_card_panel.set_card_count(color_sample_count)

        luminance_sample_count = self._config_manager.get('settings.luminance_sample_count', 5)
        self.luminance_extract_interface.luminance_canvas.set_picker_count(luminance_sample_count)
        self.luminance_extract_interface.histogram_widget.clear()

    def _on_color_sample_count_changed(self, count):
        """色彩提取采样点数改变"""
        self.color_extract_interface.image_canvas.set_picker_count(count)
        self.color_extract_interface.color_card_panel.set_card_count(count)
        # 更新HSB色环的采样点数量
        self.color_extract_interface.hsb_color_wheel.set_sample_count(count)

    def _on_luminance_sample_count_changed(self, count):
        """明度提取采样点数改变"""
        self.luminance_extract_interface.luminance_canvas.set_picker_count(count)
        self.luminance_extract_interface.histogram_widget.clear()
