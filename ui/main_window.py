# 第三方库导入
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QSplitter, QVBoxLayout, QWidget
)
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition, qrouter

# 项目模块导入
from core import get_color_info
from core import get_config_manager
from version import version_manager
from .interfaces import ColorExtractInterface, LuminanceExtractInterface, SettingsInterface, ColorSchemeInterface
from .cards import ColorCardPanel
from .histograms import LuminanceHistogramWidget, RGBHistogramWidget
from .color_wheel import HSBColorWheel
from .canvases import ImageCanvas, LuminanceCanvas


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

        # 配色方案界面
        self.color_scheme_interface = ColorSchemeInterface(self)
        self.color_scheme_interface.setObjectName('colorScheme')
        self.stackedWidget.addWidget(self.color_scheme_interface)

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

        # 配色方案
        self.addSubInterface(
            self.color_scheme_interface,
            FluentIcon.PALETTE,
            "配色方案",
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
            self.color_extract_interface.color_card_panel.clear_all()
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

        # 连接16进制显示开关信号到配色方案面板
        self.settings_interface.hex_display_changed.connect(
            self.color_scheme_interface.update_display_settings
        )

        # 连接色彩模式改变信号到配色方案面板
        self.settings_interface.color_modes_changed.connect(
            lambda modes: self.color_scheme_interface.update_display_settings(color_modes=modes)
        )

        # 连接色彩提取采样点数改变信号
        self.settings_interface.color_sample_count_changed.connect(
            self._on_color_sample_count_changed
        )

        # 连接明度提取采样点数改变信号
        self.settings_interface.luminance_sample_count_changed.connect(
            self._on_luminance_sample_count_changed
        )

        # 连接直方图缩放模式改变信号
        self.settings_interface.histogram_scaling_mode_changed.connect(
            self._on_histogram_scaling_mode_changed
        )

        # 连接色轮模式改变信号到配色方案界面
        self.settings_interface.color_wheel_mode_changed.connect(
            self.color_scheme_interface.set_color_wheel_mode
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

        # 应用加载的直方图缩放模式配置
        histogram_scaling_mode = self._config_manager.get('settings.histogram_scaling_mode', 'linear')
        self.color_extract_interface.rgb_histogram_widget.set_scaling_mode(histogram_scaling_mode)
        self.luminance_extract_interface.histogram_widget.set_scaling_mode(histogram_scaling_mode)

        # 应用加载的色轮模式配置到配色方案界面
        color_wheel_mode = self._config_manager.get('settings.color_wheel_mode', 'RGB')
        self.color_scheme_interface.set_color_wheel_mode(color_wheel_mode)

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
        # 如果有图片，重新计算直方图
        image = self.luminance_extract_interface.luminance_canvas.get_image()
        if image and not image.isNull():
            self.luminance_extract_interface.histogram_widget.set_image(image)

    def _on_histogram_scaling_mode_changed(self, mode):
        """直方图缩放模式改变"""
        self.color_extract_interface.rgb_histogram_widget.set_scaling_mode(mode)
        self.luminance_extract_interface.histogram_widget.set_scaling_mode(mode)
