# 第三方库导入
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QSplitter, QVBoxLayout, QWidget
)
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition, qrouter, FluentTitleBar, ToolButton, setTheme, Theme, isDarkTheme

# 项目模块导入
from core import get_color_info
from core import get_config_manager, ImageMediator
from version import version_manager
from .color_extract import ColorExtractInterface
from .luminance_extract import LuminanceExtractInterface
from .color_generation import ColorGenerationInterface
from .palette_management import PaletteManagementInterface
from .preset_color import PresetColorInterface
from .interfaces import SettingsInterface, ColorPreviewInterface
from .cards import ColorCardPanel
from .histograms import LuminanceHistogramWidget, RGBHistogramWidget
from .color_wheel import HSBColorWheel, InteractiveColorWheel
from .canvases import ImageCanvas, LuminanceCanvas


class CustomTitleBar(FluentTitleBar):
    """自定义标题栏，添加深色模式切换按钮和全屏切换按钮"""

    def __init__(self, parent):
        super().__init__(parent)

        # 创建深色模式切换按钮
        self.themeButton = ToolButton(self)
        self.themeButton.setFixedSize(40, 32)
        self.themeButton.setToolTip("切换深色/浅色模式")
        self.themeButton.setStyleSheet("""
            ToolButton {
                background-color: transparent !important;
                border: none !important;
            }
            ToolButton:hover {
                background-color: rgba(128, 128, 128, 30) !important;
            }
            ToolButton:pressed {
                background-color: rgba(128, 128, 128, 50) !important;
            }
        """)
        self._update_theme_icon()

        # 连接点击事件
        self.themeButton.clicked.connect(self._toggle_theme)

        # 创建全屏切换按钮
        self.fullscreenButton = ToolButton(self)
        self.fullscreenButton.setFixedSize(40, 32)
        self.fullscreenButton.setToolTip("全屏/退出全屏 (F11)")
        self.fullscreenButton.setStyleSheet("""
            ToolButton {
                background-color: transparent !important;
                border: none !important;
            }
            ToolButton:hover {
                background-color: rgba(128, 128, 128, 30) !important;
            }
            ToolButton:pressed {
                background-color: rgba(128, 128, 128, 50) !important;
            }
        """)
        self._update_fullscreen_icon()

        # 连接点击事件
        self.fullscreenButton.clicked.connect(self._toggle_fullscreen)

        # 将按钮插入到最小化按钮之前（深色模式按钮在前，全屏按钮在后）
        index = self.buttonLayout.indexOf(self.minBtn)
        self.buttonLayout.insertWidget(index, self.themeButton)
        self.buttonLayout.insertWidget(index + 1, self.fullscreenButton)

    def _toggle_theme(self):
        """切换主题"""
        if isDarkTheme():
            setTheme(Theme.LIGHT)
            theme_value = 'light'
        else:
            setTheme(Theme.DARK)
            theme_value = 'dark'
        self._update_theme_icon()
        # 重新应用按钮样式以覆盖 Fluent 主题样式
        self._apply_theme_button_style()
        # 保存主题配置
        from core import get_config_manager
        config_manager = get_config_manager()
        config_manager.set('settings.theme', theme_value)
        config_manager.save()

    def _apply_theme_button_style(self):
        """应用主题按钮的无背景样式"""
        style_sheet = """
            ToolButton {
                background-color: transparent !important;
                border: none !important;
            }
            ToolButton:hover {
                background-color: rgba(128, 128, 128, 30) !important;
            }
            ToolButton:pressed {
                background-color: rgba(128, 128, 128, 50) !important;
            }
        """
        self.themeButton.setStyleSheet(style_sheet)
        self.fullscreenButton.setStyleSheet(style_sheet)

    def _update_theme_icon(self):
        """根据当前主题更新按钮图标"""
        # 使用 CONSTRACT（对比度）图标作为主题切换按钮
        self.themeButton.setIcon(FluentIcon.CONSTRACT)

    def _toggle_fullscreen(self):
        """切换全屏/窗口模式"""
        window = self.parent()
        if window.isFullScreen():
            window.showNormal()
        else:
            window.showFullScreen()
        self._update_fullscreen_icon()

    def _update_fullscreen_icon(self):
        """根据当前全屏状态更新按钮图标"""
        window = self.parent()
        if window.isFullScreen():
            self.fullscreenButton.setIcon(FluentIcon.BACK_TO_WINDOW)
        else:
            self.fullscreenButton.setIcon(FluentIcon.FULL_SCREEN)


class MainWindow(FluentWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        # 设置自定义标题栏
        self.setTitleBar(CustomTitleBar(self))

        self._version = version_manager.get_version()
        self.setWindowTitle(f"取色卡 · Color Card · {self._version}")
        self.setMinimumSize(935, 600)

        # 加载配置
        self._config_manager = get_config_manager()
        self._config = self._config_manager.load()

        # 创建图片状态中介者
        self._image_mediator = ImageMediator(self)

        # 应用窗口大小配置
        window_config = self._config.get('window', {})
        width = window_config.get('width', 940)
        height = window_config.get('height', 660)
        is_maximized = window_config.get('is_maximized', False)
        is_fullscreen = window_config.get('is_fullscreen', False)
        self.resize(width, height)

        # 创建所有子界面（避免切换时闪烁），但耗时初始化已延迟
        self.create_sub_interface()
        self.setup_navigation()

        # 恢复窗口状态（全屏优先于最大化）
        if is_fullscreen:
            self.showFullScreen()
        elif is_maximized:
            self.showMaximized()

        # 设置 F11 快捷键切换全屏
        self._setup_fullscreen_shortcut()

    def closeEvent(self, event):
        """窗口关闭事件，保存配置"""
        # 保存窗口状态（全屏和最大化需要区分保存）
        is_fullscreen = self.isFullScreen()
        is_maximized = self.isMaximized()
        self._config_manager.set('window.is_fullscreen', is_fullscreen)
        self._config_manager.set('window.is_maximized', is_maximized)

        # 保存窗口大小（如果最大化或全屏，保存正常尺寸而非当前尺寸）
        if is_maximized or is_fullscreen:
            normal_geometry = self.normalGeometry()
            self._config_manager.set('window.width', normal_geometry.width())
            self._config_manager.set('window.height', normal_geometry.height())
        else:
            self._config_manager.set('window.width', self.width())
            self._config_manager.set('window.height', self.height())

        self._config_manager.save()
        event.accept()

    def create_sub_interface(self):
        """创建子界面（耗时初始化已延迟到各界面内部）"""
        # 色彩提取界面
        self.color_extract_interface = ColorExtractInterface(self)
        self.color_extract_interface.setObjectName('colorExtract')
        qrouter.setDefaultRouteKey(self.stackedWidget, 'colorExtract')
        self.stackedWidget.addWidget(self.color_extract_interface)

        # 明度提取界面
        self.luminance_extract_interface = LuminanceExtractInterface(self)
        self.luminance_extract_interface.setObjectName('luminanceExtract')
        self.stackedWidget.addWidget(self.luminance_extract_interface)

        # 连接明度提取面板的图片导入信号（独立导入时同步到色彩面板）
        self.luminance_extract_interface.image_imported.connect(
            self.on_luminance_image_imported
        )

        # 配色生成界面
        self.color_generation_interface = ColorGenerationInterface(self)
        self.color_generation_interface.setObjectName('colorGeneration')
        self.stackedWidget.addWidget(self.color_generation_interface)

        # 配色管理界面
        self.palette_management_interface = PaletteManagementInterface(self)
        self.palette_management_interface.setObjectName('paletteManagement')
        self.stackedWidget.addWidget(self.palette_management_interface)

        # 内置色彩界面
        self.preset_color_interface = PresetColorInterface(self)
        self.preset_color_interface.setObjectName('presetColor')
        self.stackedWidget.addWidget(self.preset_color_interface)

        # 配色预览界面
        self.color_preview_interface = ColorPreviewInterface(self)
        self.color_preview_interface.setObjectName('colorPreview')
        self.stackedWidget.addWidget(self.color_preview_interface)

        # 设置界面
        self.settings_interface = SettingsInterface(self)
        self.settings_interface.setObjectName('settings')
        self.stackedWidget.addWidget(self.settings_interface)

        # 连接中介者信号
        self._setup_mediator_connections()

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
            FluentIcon.PHOTO,
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

        # 配色生成
        self.addSubInterface(
            self.color_generation_interface,
            FluentIcon.PALETTE,
            "配色生成",
            position=NavigationItemPosition.TOP
        )

        # 配色管理
        self.addSubInterface(
            self.palette_management_interface,
            FluentIcon.HEART,
            "配色管理",
            position=NavigationItemPosition.TOP
        )

        # 内置色彩
        self.addSubInterface(
            self.preset_color_interface,
            FluentIcon.BOOK_SHELF,
            "内置色彩",
            position=NavigationItemPosition.TOP
        )

        # 配色预览
        self.addSubInterface(
            self.color_preview_interface,
            FluentIcon.VIEW,
            "配色预览",
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

        # 加载 Logo 图标 - 使用工具函数获取路径，支持开发和打包环境
        from utils.icon import get_icon_path
        logo_path = get_icon_path()

        if not logo_path:
            return  # 找不到图标时不显示

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

    def _setup_mediator_connections(self):
        """连接图片中介者的信号"""
        self._image_mediator.image_updated.connect(self._on_mediator_image_updated)
        self._image_mediator.image_cleared.connect(self._on_mediator_image_cleared)

    def _on_mediator_image_updated(self, pixmap, image, source_id):
        """中介者图片更新回调

        Args:
            pixmap: QPixmap 对象
            image: QImage 对象
            source_id: 操作来源标识
        """
        if source_id == 'luminance':
            self.color_extract_interface.image_canvas.set_image_data(pixmap, image, emit_sync=False)
            self.color_extract_interface.rgb_histogram_widget.set_image(image)
            self.color_extract_interface.hue_histogram_widget.set_image(image)
        elif source_id == 'color':
            self.luminance_extract_interface.set_image_data(pixmap, image, emit_sync=False)

    def _on_mediator_image_cleared(self, source_id):
        """中介者图片清空回调

        Args:
            source_id: 操作来源标识
        """
        if source_id == 'luminance':
            # 从明度面板同步过来，不发射信号防止循环
            self.color_extract_interface.clear_all(emit_signal=False)
        elif source_id == 'color':
            # 从色彩面板同步过来，不发射信号防止循环
            self.luminance_extract_interface.clear_all(emit_signal=False)

    def on_luminance_image_imported(self, file_path, pixmap, image):
        """明度提取面板独立导入图片后的同步回调

        Args:
            file_path: 图片文件路径
            pixmap: QPixmap 对象
            image: QImage 对象
        """
        self._image_mediator.set_image(pixmap, image, 'luminance')

    def refresh_palette_management(self):
        """刷新配色管理面板"""
        if hasattr(self, 'palette_management_interface'):
            self.palette_management_interface._load_favorites()

    def refresh_color_preview(self):
        """刷新配色预览面板"""
        if hasattr(self, 'color_preview_interface'):
            self.color_preview_interface.refresh_favorites()

    def show_color_preview(self, colors: list):
        """跳转到配色预览页面并显示指定配色

        Args:
            colors: 颜色值列表（HEX格式）
        """
        # 设置配色到预览界面
        if hasattr(self, 'color_preview_interface'):
            self.color_preview_interface.set_colors(colors)

        # 切换到配色预览页面
        self.navigationInterface.setCurrentItem(self.color_preview_interface.objectName())
        self.stackedWidget.setCurrentWidget(self.color_preview_interface)

    def _on_preset_color_favorite(self, favorite_data: dict):
        """处理内置色彩界面的收藏请求

        Args:
            favorite_data: 收藏数据字典
        """
        # 保存到配置
        self._config_manager.add_favorite(favorite_data)
        self._config_manager.save()

        # 刷新配色管理界面和配色预览界面
        self.refresh_palette_management()
        self.refresh_color_preview()

    def _on_preset_color_preview(self, preview_data: dict):
        """处理内置色彩界面的预览请求

        Args:
            preview_data: 预览数据字典，包含 name、colors、source
        """
        # 提取颜色值列表（HEX格式）
        colors = []
        for color_info in preview_data.get('colors', []):
            hex_color = color_info.get('hex', '')
            if hex_color:
                colors.append(hex_color)

        if colors:
            # 跳转到配色预览页面并显示配色
            self.show_color_preview(colors)

    def _setup_fullscreen_shortcut(self):
        """设置 F11 快捷键切换全屏"""
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        """切换全屏/窗口模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        # 更新标题栏按钮图标
        if hasattr(self, 'titleBar') and hasattr(self.titleBar, '_update_fullscreen_icon'):
            self.titleBar._update_fullscreen_icon()

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

        # 连接16进制显示开关信号到配色生成面板
        self.settings_interface.hex_display_changed.connect(
            self.color_generation_interface.update_display_settings
        )

        # 连接色彩模式改变信号到配色生成面板
        self.settings_interface.color_modes_changed.connect(
            lambda modes: self.color_generation_interface.update_display_settings(color_modes=modes)
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

        # 连接色轮模式改变信号到配色生成界面
        self.settings_interface.color_wheel_mode_changed.connect(
            self.color_generation_interface.set_color_wheel_mode
        )

        # 连接直方图模式改变信号到色彩提取界面
        self.settings_interface.histogram_mode_changed.connect(
            self._on_histogram_mode_changed
        )

        # 连接饱和度阈值改变信号到色彩提取界面
        self.settings_interface.saturation_threshold_changed.connect(
            self._on_saturation_threshold_changed
        )

        # 连接明度阈值改变信号到色彩提取界面
        self.settings_interface.brightness_threshold_changed.connect(
            self._on_brightness_threshold_changed
        )

        # 连接色环标签显示开关信号
        self.settings_interface.color_wheel_labels_visible_changed.connect(
            lambda visible: HSBColorWheel.set_labels_visible(visible)
        )
        self.settings_interface.color_wheel_labels_visible_changed.connect(
            lambda visible: InteractiveColorWheel.set_labels_visible(visible)
        )

        # 连接16进制显示开关信号到配色管理界面
        self.settings_interface.hex_display_changed.connect(
            lambda visible: self.palette_management_interface.update_display_settings(hex_visible=visible)
        )

        # 连接色彩模式改变信号到配色管理界面
        self.settings_interface.color_modes_changed.connect(
            lambda modes: self.palette_management_interface.update_display_settings(color_modes=modes)
        )

        # 连接16进制显示开关信号到内置色彩界面
        self.settings_interface.hex_display_changed.connect(
            lambda visible: self.preset_color_interface.update_display_settings(hex_visible=visible)
        )

        # 连接色彩模式改变信号到内置色彩界面
        self.settings_interface.color_modes_changed.connect(
            lambda modes: self.preset_color_interface.update_display_settings(color_modes=modes)
        )

        # 连接16进制显示开关信号到配色预览界面
        self.settings_interface.hex_display_changed.connect(
            self.color_preview_interface.set_hex_visible
        )

        # 连接内置色彩界面的收藏信号
        self.preset_color_interface.favorite_requested.connect(self._on_preset_color_favorite)

        # 连接内置色彩界面的预览信号
        self.preset_color_interface.preview_in_panel_requested.connect(
            self._on_preset_color_preview
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
        self.color_extract_interface.hue_histogram_widget.set_scaling_mode(histogram_scaling_mode)
        self.luminance_extract_interface.histogram_widget.set_scaling_mode(histogram_scaling_mode)

        # 应用加载的色轮模式配置到配色生成界面
        color_wheel_mode = self._config_manager.get('settings.color_wheel_mode', 'RGB')
        self.color_generation_interface.set_color_wheel_mode(color_wheel_mode)

        # 应用加载的直方图模式配置
        histogram_mode = self._config_manager.get('settings.histogram_mode', 'hue')
        self.color_extract_interface.set_histogram_mode(histogram_mode)

        # 应用加载的阈值配置
        saturation_threshold = self._config_manager.get('settings.saturation_threshold', 70)
        self.color_extract_interface.set_saturation_threshold(saturation_threshold)

        brightness_threshold = self._config_manager.get('settings.brightness_threshold', 70)
        self.color_extract_interface.set_brightness_threshold(brightness_threshold)

    def _on_color_sample_count_changed(self, count):
        """色彩提取采样点数改变"""
        # 先更新色卡数量，确保新色卡已创建
        self.color_extract_interface.color_card_panel.set_card_count(count)
        # 再更新取色点数量（这会触发 extract_all，发射 color_picked 信号）
        self.color_extract_interface.image_canvas.set_picker_count(count)
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
        self.color_extract_interface.hue_histogram_widget.set_scaling_mode(mode)
        self.luminance_extract_interface.histogram_widget.set_scaling_mode(mode)

    def _on_histogram_mode_changed(self, mode):
        """直方图显示模式改变"""
        self.color_extract_interface.set_histogram_mode(mode)

    def _on_saturation_threshold_changed(self, value):
        """饱和度阈值改变"""
        self.color_extract_interface.set_saturation_threshold(value)

    def _on_brightness_threshold_changed(self, value):
        """明度阈值改变"""
        self.color_extract_interface.set_brightness_threshold(value)
