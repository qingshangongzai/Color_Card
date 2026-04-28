# 标准库导入
import sys
from typing import List, Dict, Any, TYPE_CHECKING

# 第三方库导入
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QLabel
)
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition, qrouter, FluentTitleBar, ToolButton, setTheme, Theme, isDarkTheme

# 项目模块导入
from core import get_config_manager, get_logger
from utils import tr, get_locale_manager
from version import version_manager
from .color_wheel import HSBColorWheel, InteractiveColorWheel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

# 工具按钮统一样式
_TOOLBUTTON_STYLE = """
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


class CustomTitleBar(FluentTitleBar):
    """自定义标题栏，添加主题切换按钮和全屏切换按钮"""

    def __init__(self, parent):
        super().__init__(parent)

        # 主题模式：light/dark/auto
        self._theme_mode = 'auto'

        # 创建主题切换按钮
        self.themeButton = ToolButton(self)
        self.themeButton.setFixedSize(40, 32)
        self.themeButton.setStyleSheet(_TOOLBUTTON_STYLE)
        self._update_theme_icon()

        # 连接点击事件
        self.themeButton.clicked.connect(self._toggle_theme)

        # 创建全屏切换按钮
        self.fullscreenButton = ToolButton(self)
        self.fullscreenButton.setFixedSize(40, 32)
        self.fullscreenButton.setToolTip(tr('title_bar.toggle_fullscreen'))
        self.fullscreenButton.setStyleSheet(_TOOLBUTTON_STYLE)
        self._update_fullscreen_icon()

        # 连接点击事件
        self.fullscreenButton.clicked.connect(self._toggle_fullscreen)

        # 将按钮插入到最小化按钮之前（主题按钮在前，全屏按钮在后）
        index = self.buttonLayout.indexOf(self.minBtn)
        self.buttonLayout.insertWidget(index, self.themeButton)
        self.buttonLayout.insertWidget(index + 1, self.fullscreenButton)

    def init_theme(self, mode: str):
        """初始化主题模式

        Args:
            mode: 主题模式 (light/dark/auto)
        """
        self._theme_mode = mode
        self._update_theme_icon()

    def _toggle_theme(self):
        """切换主题（三态循环：浅色→深色→跟随系统→浅色）"""
        mode_cycle = ['light', 'dark', 'auto']
        current_index = mode_cycle.index(self._theme_mode)
        next_index = (current_index + 1) % len(mode_cycle)
        next_mode = mode_cycle[next_index]

        self._apply_theme_mode(next_mode)

    def _apply_theme_mode(self, mode: str):
        """应用主题模式

        Args:
            mode: 主题模式 (light/dark/auto)
        """
        self._theme_mode = mode

        if mode == 'light':
            setTheme(Theme.LIGHT)
        elif mode == 'dark':
            setTheme(Theme.DARK)
        else:  # auto
            setTheme(Theme.AUTO)

        self._update_theme_icon()
        self._apply_theme_button_style()

        # 保存配置
        from core import get_config_manager
        config_manager = get_config_manager()
        config_manager.set('settings.theme', mode)
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
        """根据当前主题模式更新按钮图标和提示"""
        if self._theme_mode == 'light':
            self.themeButton.setIcon(FluentIcon.BRIGHTNESS)
        elif self._theme_mode == 'dark':
            self.themeButton.setIcon(FluentIcon.QUIET_HOURS)
        else:  # auto
            self.themeButton.setIcon(FluentIcon.SYNC)

        tooltip_map = {
            'light': tr('title_bar.theme_light'),
            'dark': tr('title_bar.theme_dark'),
            'auto': tr('title_bar.theme_auto')
        }
        self.themeButton.setToolTip(tooltip_map[self._theme_mode])

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

    def update_texts(self):
        """更新界面文本"""
        self._update_theme_icon()
        self.fullscreenButton.setToolTip(tr('title_bar.toggle_fullscreen'))


class MainWindow(FluentWindow):
    """主窗口"""

    # 导航图标映射（类属性，避免每次创建）
    _NAV_ICON_MAP = {
        'colorAnalysis': FluentIcon.PHOTO,
        'luminanceAnalysis': FluentIcon.BRIGHTNESS,
        'gradientGeneration': FluentIcon.BRUSH,
        'colorGeneration': FluentIcon.PALETTE,
        'paletteManagement': FluentIcon.HEART,
        'presetColor': FluentIcon.BOOK_SHELF,
        'colorPreview': FluentIcon.VIEW,
        'settings': FluentIcon.SETTING,
    }

    def __init__(self):
        super().__init__()

        # Mac 平台：先隐藏系统标题栏按钮，再设置自定义标题栏
        # 这样 FluentWidget.setTitleBar 不会隐藏自定义按钮
        if sys.platform == 'darwin':
            self.setSystemTitleBarButtonVisible(False)

        # 设置自定义标题栏
        self.setTitleBar(CustomTitleBar(self))

        self._version = version_manager.get_version()
        self.setWindowTitle(f"取色卡 · Color Card · {self._version}")
        self.setMinimumSize(1095, 600)

        # 获取配置管理器（配置已在 main.py 中加载）
        self._config_manager = get_config_manager()
        self._config = self._config_manager._config

        # 应用窗口大小配置
        window_config = self._config.get('window', {})
        width = window_config.get('width', 1150)
        height = window_config.get('height', 660)
        is_maximized = window_config.get('is_maximized', False)
        is_fullscreen = window_config.get('is_fullscreen', False)
        self.resize(width, height)

        # 窗口居中显示（仅在非最大化/非全屏时）
        if not is_maximized and not is_fullscreen:
            self._center_window()

        # 界面类映射（用于延迟导入和创建）
        self._interface_classes = {
            'colorAnalysis': ('ui.color_analysis', 'ColorAnalysisInterface'),
            'luminanceAnalysis': ('ui.luminance_analysis', 'LuminanceAnalysisInterface'),
            'gradientGeneration': ('ui.gradient_generation', 'GradientGenerationInterface'),
            'colorGeneration': ('ui.color_generation', 'ColorGenerationInterface'),
            'paletteManagement': ('ui.palette_management', 'PaletteManagementInterface'),
            'presetColor': ('ui.preset_color', 'PresetColorInterface'),
            'colorPreview': ('ui.color_preview', 'ColorPreviewInterface'),
            'settings': ('ui.settings', 'SettingsInterface'),
        }

        # 界面实例缓存
        self._interfaces: Dict[str, 'QWidget'] = {}

        # 设置导航（按需创建界面）
        self.setup_navigation()

        # 设置跨面板图片同步
        self._setup_cross_panel_sync()

        # 连接语言切换信号
        get_locale_manager().language_changed.connect(self._on_language_changed)

        # 恢复窗口状态（全屏优先于最大化）
        if is_fullscreen:
            self.showFullScreen()
        elif is_maximized:
            self.showMaximized()

        # 设置 F11 快捷键切换全屏
        self._setup_fullscreen_shortcut()

    def _get_interface(self, interface_id: str) -> 'QWidget':
        """按需获取界面实例

        Args:
            interface_id: 界面标识符

        Returns:
            QWidget: 界面实例
        """
        if interface_id not in self._interfaces:
            # 动态导入并创建
            module_name, class_name = self._interface_classes[interface_id]
            module = __import__(module_name, fromlist=[class_name])
            interface_class = getattr(module, class_name)

            # 创建界面实例
            interface = interface_class(self)
            interface.setObjectName(interface_id)

            # 设置导航图标
            interface._nav_icon = self._NAV_ICON_MAP.get(interface_id)

            # 缓存并添加到堆叠窗口
            self._interfaces[interface_id] = interface
            self.stackedWidget.addWidget(interface)

            # 首次创建时执行初始化
            self._on_interface_created(interface_id, interface)

        return self._interfaces[interface_id]

    def _on_interface_created(self, interface_id: str, interface: 'QWidget'):
        """界面首次创建时的初始化

        Args:
            interface_id: 界面标识符
            interface: 界面实例
        """
        # 设置默认路由键（色彩分析界面）
        if interface_id == 'colorAnalysis':
            qrouter.setDefaultRouteKey(self.stackedWidget, interface_id)

        # 连接设置信号（设置界面创建时）
        if interface_id == 'settings':
            self._connect_settings_signals(interface)

        # 连接内置色彩界面的收藏和预览信号
        if interface_id == 'presetColor':
            interface.favorite_requested.connect(self._on_preset_color_favorite)
            interface.preview_in_panel_requested.connect(self._on_preset_color_preview)

        # 连接渐变生成界面的收藏信号
        if interface_id == 'gradientGeneration':
            interface.favorite_requested.connect(self._on_gradient_generation_favorite)

    def _connect_settings_signals(self, settings_interface: 'QWidget'):
        """连接设置界面的信号

        Args:
            settings_interface: 设置界面实例
        """
        # 连接16进制显示开关信号到色彩分析面板
        color_analysis_interface = self._get_interface('colorAnalysis')
        settings_interface.hex_display_changed.connect(
            color_analysis_interface.color_card_panel.set_hex_visible
        )

        # 连接色彩模式改变信号到色彩分析面板
        settings_interface.color_modes_changed.connect(
            color_analysis_interface.color_card_panel.set_color_modes
        )

        # 连接16进制显示开关信号到配色生成面板
        color_generation_interface = self._get_interface('colorGeneration')
        settings_interface.hex_display_changed.connect(
            color_generation_interface.update_display_settings
        )

        # 连接色彩模式改变信号到配色生成面板
        settings_interface.color_modes_changed.connect(
            lambda modes: color_generation_interface.update_display_settings(color_modes=modes)
        )

        # 连接色彩模式改变信号到渐变生成面板
        gradient_generation_interface = self._get_interface('gradientGeneration')
        settings_interface.color_modes_changed.connect(
            gradient_generation_interface.set_color_modes
        )

        # 连接HEX显示改变信号到渐变生成面板
        settings_interface.hex_display_changed.connect(
            gradient_generation_interface.set_hex_visible
        )

        # 连接色彩分析采样点数改变信号
        settings_interface.color_sample_count_changed.connect(
            self._on_color_sample_count_changed
        )

        # 连接明度分析采样点数改变信号
        settings_interface.luminance_sample_count_changed.connect(
            self._on_luminance_sample_count_changed
        )

        # 连接画布采样点数量改变信号（从右键菜单调整）
        color_analysis_interface.image_canvas.picker_count_changed.connect(
            self._on_canvas_picker_count_changed
        )

        luminance_analysis_interface = self._get_interface('luminanceAnalysis')
        luminance_analysis_interface.luminance_canvas.picker_count_changed.connect(
            self._on_luminance_canvas_picker_count_changed
        )

        # 连接直方图缩放模式改变信号
        settings_interface.histogram_scaling_mode_changed.connect(
            self._on_histogram_scaling_mode_changed
        )

        # 连接明度直方图样式改变信号到明度分析界面
        settings_interface.luminance_histogram_style_changed.connect(
            luminance_analysis_interface.set_histogram_style
        )

        # 连接色轮模式改变信号到配色生成界面
        settings_interface.color_wheel_mode_changed.connect(
            color_generation_interface.set_color_wheel_mode
        )

        # 连接渐变颜色空间改变信号到渐变生成界面
        settings_interface.gradient_color_space_changed.connect(
            gradient_generation_interface.set_color_space
        )

        # 连接渐变模式改变信号到渐变生成界面
        settings_interface.gradient_mode_changed.connect(
            gradient_generation_interface.set_gradient_mode
        )

        # 连接直方图模式改变信号到色彩分析界面
        settings_interface.histogram_mode_changed.connect(
            self._on_histogram_mode_changed
        )

        # 连接直方图采样模式改变信号
        settings_interface.histogram_sampling_mode_changed.connect(
            color_analysis_interface.rgb_histogram_widget.set_sampling_mode
        )
        settings_interface.histogram_sampling_mode_changed.connect(
            color_analysis_interface.hue_histogram_widget.set_sampling_mode
        )
        settings_interface.histogram_sampling_mode_changed.connect(
            luminance_analysis_interface.histogram_widget.set_sampling_mode
        )

        # 连接饱和度阈值改变信号到色彩分析界面
        settings_interface.saturation_threshold_changed.connect(
            self._on_saturation_threshold_changed
        )

        # 连接明度阈值改变信号到色彩分析界面
        settings_interface.brightness_threshold_changed.connect(
            self._on_brightness_threshold_changed
        )

        # 连接色环标签显示开关信号
        settings_interface.color_wheel_labels_visible_changed.connect(
            lambda visible: HSBColorWheel.set_labels_visible(visible)
        )
        settings_interface.color_wheel_labels_visible_changed.connect(
            lambda visible: InteractiveColorWheel.set_labels_visible(visible)
        )

        # 连接16进制显示开关信号到配色管理界面
        palette_management_interface = self._get_interface('paletteManagement')
        settings_interface.hex_display_changed.connect(
            lambda visible: palette_management_interface.update_display_settings(hex_visible=visible)
        )

        # 连接色彩模式改变信号到配色管理界面
        settings_interface.color_modes_changed.connect(
            lambda modes: palette_management_interface.update_display_settings(color_modes=modes)
        )

        # 连接16进制显示开关信号到内置色彩界面
        preset_color_interface = self._get_interface('presetColor')
        settings_interface.hex_display_changed.connect(
            lambda visible: preset_color_interface.update_display_settings(hex_visible=visible)
        )

        # 连接色彩模式改变信号到内置色彩界面
        settings_interface.color_modes_changed.connect(
            lambda modes: preset_color_interface.update_display_settings(color_modes=modes)
        )

        # 连接16进制显示开关信号到配色预览界面
        color_preview_interface = self._get_interface('colorPreview')
        settings_interface.hex_display_changed.connect(
            color_preview_interface.set_hex_visible
        )

        # 应用加载的配置到色卡面板
        hex_visible = self._config_manager.get('settings.hex_visible', True)
        color_analysis_interface.color_card_panel.set_hex_visible(hex_visible)

        # 应用加载的色彩模式配置到色卡面板
        color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        color_analysis_interface.color_card_panel.set_color_modes(color_modes)

        # 应用加载的采样点数量配置
        color_sample_count = self._config_manager.get('settings.color_sample_count', 5)
        color_analysis_interface.image_canvas.set_picker_count(color_sample_count)
        color_analysis_interface.color_card_panel.set_card_count(color_sample_count)

        luminance_sample_count = self._config_manager.get('settings.luminance_sample_count', 5)
        luminance_analysis_interface.luminance_canvas.set_picker_count(luminance_sample_count)
        luminance_analysis_interface.histogram_widget.clear()

        # 应用加载的直方图缩放模式配置
        histogram_scaling_mode = self._config_manager.get('settings.histogram_scaling_mode', 'linear')
        color_analysis_interface.rgb_histogram_widget.set_scaling_mode(histogram_scaling_mode)
        color_analysis_interface.hue_histogram_widget.set_scaling_mode(histogram_scaling_mode)
        luminance_analysis_interface.histogram_widget.set_scaling_mode(histogram_scaling_mode)

        # 应用加载的色轮模式配置到配色生成界面
        color_wheel_mode = self._config_manager.get('settings.color_wheel_mode', 'RGB')
        color_generation_interface.set_color_wheel_mode(color_wheel_mode)

        # 应用加载的直方图模式配置
        histogram_mode = self._config_manager.get('settings.histogram_mode', 'hue')
        color_analysis_interface.set_histogram_mode(histogram_mode)

        # 应用加载的直方图采样模式配置
        histogram_sampling_mode = self._config_manager.get('settings.histogram_sampling_mode', 'fast')
        color_analysis_interface.rgb_histogram_widget.set_sampling_mode(histogram_sampling_mode)
        color_analysis_interface.hue_histogram_widget.set_sampling_mode(histogram_sampling_mode)
        luminance_analysis_interface.histogram_widget.set_sampling_mode(histogram_sampling_mode)

        # 应用加载的阈值配置
        saturation_threshold = self._config_manager.get('settings.saturation_threshold', 70)
        color_analysis_interface.set_saturation_threshold(saturation_threshold)

        brightness_threshold = self._config_manager.get('settings.brightness_threshold', 70)
        color_analysis_interface.set_brightness_threshold(brightness_threshold)

    def closeEvent(self, event):
        """窗口关闭事件，保存配置并清理后台线程"""
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

        # 清理后台线程
        self._cleanup_background_threads()

        # 关闭所有明度分析对话框
        self._close_tone_analysis_dialogs()

        event.accept()

    def _cleanup_background_threads(self):
        """清理所有后台计算线程

        遍历所有直方图组件，取消正在进行的计算，
        避免窗口关闭时出现 "QThread: Destroyed while thread is still running" 警告。
        """
        from ui.histograms import BaseHistogram

        for histogram_widget in self.findChildren(BaseHistogram):
            if hasattr(histogram_widget, '_histogram_service'):
                try:
                    histogram_widget._histogram_service.cancel_all()
                except (RuntimeError, AttributeError):
                    # 对象可能已被销毁，忽略错误
                    pass

    def _close_tone_analysis_dialogs(self):
        """关闭所有明度分析对话框"""
        from dialogs import ToneAnalysisDialog
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if isinstance(widget, ToneAnalysisDialog):
                widget.close()

    def setup_navigation(self):
        """设置导航栏"""
        # 隐藏返回按钮
        self.navigationInterface.setReturnButtonVisible(False)

        # 禁用菜单按钮的悬停提示（通过拦截展开/折叠时的tooltip设置）
        self._disable_menu_button_tooltip()

        # 设置导航栏默认展开宽度
        self.navigationInterface.setExpandWidth(200)

        # 添加 Logo 到左上角
        self._setup_logo()

        # 色彩分析（启动时立即创建，作为默认界面）
        self.addSubInterface(
            self._get_interface('colorAnalysis'),
            FluentIcon.PHOTO,
            tr('navigation.color_analysis'),
            position=NavigationItemPosition.TOP
        )

        # 明度分析
        self.addSubInterface(
            self._get_interface('luminanceAnalysis'),
            FluentIcon.BRIGHTNESS,
            tr('navigation.luminance_analysis'),
            position=NavigationItemPosition.TOP
        )

        # 渐变生成
        self.addSubInterface(
            self._get_interface('gradientGeneration'),
            FluentIcon.BRUSH,
            tr('navigation.gradient_generation'),
            position=NavigationItemPosition.TOP
        )

        # 配色生成
        self.addSubInterface(
            self._get_interface('colorGeneration'),
            FluentIcon.PALETTE,
            tr('navigation.color_generation'),
            position=NavigationItemPosition.TOP
        )

        # 配色管理
        self.addSubInterface(
            self._get_interface('paletteManagement'),
            FluentIcon.HEART,
            tr('navigation.palette_management'),
            position=NavigationItemPosition.TOP
        )

        # 内置色彩
        self.addSubInterface(
            self._get_interface('presetColor'),
            FluentIcon.BOOK_SHELF,
            tr('navigation.preset_color'),
            position=NavigationItemPosition.TOP
        )

        # 配色预览
        self.addSubInterface(
            self._get_interface('colorPreview'),
            FluentIcon.VIEW,
            tr('navigation.color_preview'),
            position=NavigationItemPosition.TOP
        )

        # 设置（放在底部）
        self.addSubInterface(
            self._get_interface('settings'),
            FluentIcon.SETTING,
            tr('navigation.settings'),
            position=NavigationItemPosition.BOTTOM
        )

        # 设置默认选中的导航项
        self.navigationInterface.setCurrentItem('colorAnalysis')

        # 连接导航切换信号
        self.stackedWidget.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        """标签页切换回调"""
        current_widget = self.stackedWidget.widget(index)

        # 如果是配色预览界面，触发延迟加载
        if current_widget.objectName() == 'colorPreview':
            self._get_interface('colorPreview').on_tab_selected()

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
        """打开图片（从色彩分析界面调用）"""
        self._get_interface('colorAnalysis').open_image()

    def _setup_cross_panel_sync(self):
        """设置跨面板图片同步（简化版，替代中介者）"""
        # 延迟连接，确保界面已创建
        QTimer.singleShot(0, self._do_setup_sync)

    def _do_setup_sync(self):
        """实际执行信号连接"""
        try:
            color_interface = self._get_interface('colorAnalysis')
            luminance_interface = self._get_interface('luminanceAnalysis')

            # 色彩 → 明度
            color_interface.image_sync_requested.connect(
                lambda d: luminance_interface.set_image_data(d, emit_sync=False)
            )
            color_interface.clear_sync_requested.connect(
                lambda: luminance_interface.clear_all(emit_signal=False)
            )

            # 明度 → 色彩
            luminance_interface.image_sync_requested.connect(
                lambda d: color_interface.set_image_data(d)
            )
            luminance_interface.clear_sync_requested.connect(
                lambda: color_interface.clear_all(emit_signal=False)
            )

        except AttributeError as e:
            logger = get_logger("main_window")
            logger.warning(f"跨面板同步设置失败: {e}")

    def refresh_palette_management(self):
        """刷新配色管理面板"""
        if 'paletteManagement' in self._interfaces:
            self._get_interface('paletteManagement')._load_favorites()

    def refresh_color_preview(self):
        """刷新配色预览面板"""
        if 'colorPreview' in self._interfaces:
            self._get_interface('colorPreview').refresh_favorites()

    def show_color_preview(self, colors: List[str]):
        """跳转到配色预览页面并显示指定配色

        Args:
            colors: 颜色值列表（HEX格式）
        """
        # 设置配色到预览界面
        color_preview_interface = self._get_interface('colorPreview')
        color_preview_interface.set_colors(colors)

        # 切换到配色预览页面
        self.navigationInterface.setCurrentItem('colorPreview')
        self.stackedWidget.setCurrentWidget(color_preview_interface)

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

    def _on_gradient_generation_favorite(self, favorite_data: dict):
        """处理渐变生成界面的收藏请求

        Args:
            favorite_data: 收藏数据字典
        """
        # 保存到配置
        self._config_manager.add_favorite(favorite_data)
        self._config_manager.save()

        # 刷新配色管理界面和配色预览界面
        self.refresh_palette_management()
        self.refresh_color_preview()

    def _on_preset_color_preview(self, preview_data: Dict[str, Any]):
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

    def _on_color_sample_count_changed(self, count):
        """色彩分析采样点数改变"""
        color_analysis_interface = self._get_interface('colorAnalysis')
        # 先更新色卡数量，确保新色卡已创建
        color_analysis_interface.color_card_panel.set_card_count(count)
        # 再更新取色点数量（这会触发 extract_all，发射 color_picked 信号）
        color_analysis_interface.image_canvas.set_picker_count(count)
        # 更新HSB色环的采样点数量
        color_analysis_interface.hsb_color_wheel.set_sample_count(count)

    def _on_luminance_sample_count_changed(self, count):
        """明度分析采样点数改变"""
        luminance_analysis_interface = self._get_interface('luminanceAnalysis')
        luminance_analysis_interface.luminance_canvas.set_picker_count(count)
        luminance_analysis_interface.histogram_widget.clear()
        # 如果有图片，重新计算直方图
        image = luminance_analysis_interface.luminance_canvas.get_image()
        if image and not image.isNull():
            luminance_analysis_interface.histogram_widget.set_image(image)

    def _on_canvas_picker_count_changed(self, count):
        """画布采样点数量改变（从右键菜单调整）"""
        # 更新配置
        self._config_manager.set('settings.color_sample_count', count)
        # 更新设置界面显示
        settings_interface = self._get_interface('settings')
        settings_interface.color_sample_count_card.combo_box.setCurrentText(str(count))
        # 更新色卡面板（必须先于重新提取颜色）
        color_analysis_interface = self._get_interface('colorAnalysis')
        color_analysis_interface.color_card_panel.set_card_count(count)
        # 更新HSB色环
        color_analysis_interface.hsb_color_wheel.set_sample_count(count)
        # 重新提取所有颜色（新添加的采样点需要更新颜色）
        color_analysis_interface.image_canvas.extract_all()

    def _on_luminance_canvas_picker_count_changed(self, count):
        """明度画布采样点数量改变（从右键菜单调整）"""
        # 更新配置
        self._config_manager.set('settings.luminance_sample_count', count)
        # 更新设置界面显示
        settings_interface = self._get_interface('settings')
        settings_interface.luminance_sample_count_card.combo_box.setCurrentText(str(count))
        # 更新直方图
        luminance_analysis_interface = self._get_interface('luminanceAnalysis')
        luminance_analysis_interface.histogram_widget.clear()
        image = luminance_analysis_interface.luminance_canvas.get_image()
        if image and not image.isNull():
            luminance_analysis_interface.histogram_widget.set_image(image)

    def _on_histogram_scaling_mode_changed(self, mode):
        """直方图缩放模式改变"""
        color_analysis_interface = self._get_interface('colorAnalysis')
        color_analysis_interface.rgb_histogram_widget.set_scaling_mode(mode)
        color_analysis_interface.hue_histogram_widget.set_scaling_mode(mode)
        self._get_interface('luminanceAnalysis').histogram_widget.set_scaling_mode(mode)

    def _on_histogram_mode_changed(self, mode):
        """直方图显示模式改变"""
        self._get_interface('colorAnalysis').set_histogram_mode(mode)

    def _on_saturation_threshold_changed(self, value):
        """饱和度阈值改变"""
        self._get_interface('colorAnalysis').set_saturation_threshold(value)

    def _on_brightness_threshold_changed(self, value):
        """明度阈值改变"""
        self._get_interface('colorAnalysis').set_brightness_threshold(value)

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        self._update_navigation_texts()
        if hasattr(self, 'titleBar') and hasattr(self.titleBar, 'update_texts'):
            self.titleBar.update_texts()

    def _update_navigation_texts(self):
        """更新导航栏文本"""
        navigation_items = [
            ('colorAnalysis', tr('navigation.color_analysis')),
            ('luminanceAnalysis', tr('navigation.luminance_analysis')),
            ('gradientGeneration', tr('navigation.gradient_generation')),
            ('colorGeneration', tr('navigation.color_generation')),
            ('paletteManagement', tr('navigation.palette_management')),
            ('presetColor', tr('navigation.preset_color')),
            ('colorPreview', tr('navigation.color_preview')),
            ('settings', tr('navigation.settings')),
        ]
        for route_key, text in navigation_items:
            widget = self.navigationInterface.widget(route_key)
            if widget:
                widget.setText(text)

    def _center_window(self):
        """将窗口居中显示在屏幕上"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()

            center_x = screen_geometry.center().x() - window_geometry.width() // 2
            center_y = screen_geometry.center().y() - window_geometry.height() // 2

            self.move(center_x, center_y)

    def _disable_menu_button_tooltip(self):
        """禁用导航栏菜单按钮的悬停提示"""
        panel = self.navigationInterface.panel
        menu_button = panel.menuButton

        # 清空tooltip
        menu_button.setToolTip("")

        # 连接导航面板的展开/折叠信号，在状态变化后清空tooltip
        def clear_tooltip():
            menu_button.setToolTip("")

        panel.displayModeChanged.connect(clear_tooltip)


