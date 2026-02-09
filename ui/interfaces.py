# 标准库导入
import uuid
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QSplitter, QStackedWidget,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget
)
from qfluentwidgets import (
    ComboBox, FluentIcon, InfoBar, InfoBarPosition, PrimaryPushButton,
    PushButton, PushSettingCard, ScrollArea, SettingCardGroup, SpinBox, SubtitleLabel, SwitchButton, qconfig, isDarkTheme
)

# 项目模块导入
from core import get_color_info, get_config_manager, extract_dominant_colors, find_dominant_color_positions


class DominantColorExtractor(QThread):
    """主色调提取线程

    在后台线程中执行主色调提取，避免阻塞UI。
    支持取消操作。
    """

    # 信号：提取完成
    extraction_finished = Signal(list, list)  # dominant_colors, positions
    # 信号：提取失败
    extraction_error = Signal(str)  # error_message
    # 信号：提取进度（可选）
    extraction_progress = Signal(int)  # progress_percent

    def __init__(self, image, count: int = 5, parent=None):
        """
        Args:
            image: QImage 对象
            count: 提取颜色数量
            parent: 父对象
        """
        super().__init__(parent)
        self._image = image
        self._count = count
        self._is_cancelled = False

    def cancel(self):
        """请求取消提取"""
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._is_cancelled

    def run(self):
        """在子线程中执行主色调提取"""
        try:
            if self._check_cancelled() or not self._image or self._image.isNull():
                return

            # 提取主色调
            dominant_colors = extract_dominant_colors(self._image, count=self._count)

            if self._check_cancelled():
                return

            if not dominant_colors:
                self.extraction_error.emit("无法从图片中提取主色调")
                return

            # 找到每种主色调在图片中的位置
            positions = find_dominant_color_positions(self._image, dominant_colors)

            if self._check_cancelled():
                return

            # 发送成功信号
            self.extraction_finished.emit(dominant_colors, positions)

        except Exception as e:
            if not self._check_cancelled():
                self.extraction_error.emit(str(e))


from dialogs import AboutDialog, ColorblindPreviewDialog, ContrastCheckDialog, NameDialog, UpdateAvailableDialog
from version import version_manager
from .canvases import ImageCanvas, LuminanceCanvas
from .cards import ColorCardPanel
from .color_wheel import HSBColorWheel, InteractiveColorWheel
from .histograms import LuminanceHistogramWidget, RGBHistogramWidget, HueHistogramWidget
from .scheme_widgets import SchemeColorPanel
from .color_management_widgets import ColorManagementSchemeList
from .theme_colors import get_canvas_empty_bg_color, get_title_color, get_text_color, get_interface_background_color, get_card_background_color, get_border_color
from utils.platform import is_windows_10


# 可选的色彩模式列表
AVAILABLE_COLOR_MODES = ['HSB', 'LAB', 'HSL', 'CMYK', 'RGB']


class ColorExtractInterface(QWidget):
    """色彩提取界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging_index = -1  # 当前正在拖动的采样点索引
        self._config_manager = get_config_manager()
        self._extractor = None  # 主色调提取线程
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 主分割器（垂直）
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setMinimumHeight(300)
        main_splitter.setHandleWidth(0)  # 隐藏分隔条
        layout.addWidget(main_splitter, stretch=1)

        # 上半部分：水平分割器（图片 + 右侧组件）
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setMinimumHeight(180)
        top_splitter.setHandleWidth(0)  # 隐藏分隔条

        # 左侧：图片画布
        self.image_canvas = ImageCanvas()
        self.image_canvas.setMinimumWidth(300)
        self.image_canvas.setMinimumHeight(150)
        top_splitter.addWidget(self.image_canvas)

        # 右侧：垂直分割器（HSB色环 + 直方图堆叠窗口）
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setMinimumWidth(180)
        right_splitter.setMaximumWidth(350)
        right_splitter.setMinimumHeight(150)
        right_splitter.setHandleWidth(0)  # 隐藏分隔条

        # HSB色环
        self.hsb_color_wheel = HSBColorWheel()
        self.hsb_color_wheel.setMinimumHeight(100)
        self.hsb_color_wheel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_splitter.addWidget(self.hsb_color_wheel)

        # 直方图堆叠窗口（RGB/色相切换）
        self.histogram_stack = QStackedWidget()
        self.histogram_stack.setMinimumHeight(60)
        self.histogram_stack.setMaximumHeight(150)
        self.histogram_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # RGB直方图
        self.rgb_histogram_widget = RGBHistogramWidget()
        self.histogram_stack.addWidget(self.rgb_histogram_widget)

        # 色相直方图
        self.hue_histogram_widget = HueHistogramWidget()
        self.histogram_stack.addWidget(self.hue_histogram_widget)

        right_splitter.addWidget(self.histogram_stack)
        right_splitter.setSizes([200, 100])
        top_splitter.addWidget(right_splitter)

        # 设置左右比例（图片区域:右侧组件区域）
        top_splitter.setSizes([550, 280])
        main_splitter.addWidget(top_splitter)

        # 收藏工具栏
        favorite_toolbar = QWidget()
        favorite_toolbar.setMaximumHeight(50)
        favorite_toolbar.setStyleSheet("background: transparent;")
        favorite_toolbar_layout = QHBoxLayout(favorite_toolbar)
        favorite_toolbar_layout.setContentsMargins(0, 8, 0, 8)
        favorite_toolbar_layout.setSpacing(10)

        self.favorite_button = PrimaryPushButton(FluentIcon.HEART, "收藏当前配色", self)
        self.favorite_button.setFixedHeight(32)
        self.favorite_button.clicked.connect(self._on_favorite_clicked)
        favorite_toolbar_layout.addWidget(self.favorite_button)

        # 主色调提取按钮
        self.extract_dominant_button = PushButton(FluentIcon.PALETTE, "自动提取主色调", self)
        self.extract_dominant_button.setFixedHeight(32)
        self.extract_dominant_button.clicked.connect(self._on_extract_dominant_clicked)
        favorite_toolbar_layout.addWidget(self.extract_dominant_button)

        favorite_toolbar_layout.addStretch()

        main_splitter.addWidget(favorite_toolbar)

        # 下半部分：色卡面板
        self.color_card_panel = ColorCardPanel()
        self.color_card_panel.setMinimumHeight(130)
        main_splitter.addWidget(self.color_card_panel)

        main_splitter.setSizes([350, 36, 180])

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

        # 更新RGB直方图和色相直方图
        self.rgb_histogram_widget.set_image(image)
        self.hue_histogram_widget.set_image(image)

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
        # 清除HSB色环和直方图
        self.hsb_color_wheel.clear_sample_points()
        self.rgb_histogram_widget.clear()
        self.hue_histogram_widget.clear()

    def on_image_cleared(self):
        """图片已清空回调（同步清除明度面板）"""
        # 同步清除明度提取面板
        window = self.window()
        if window and hasattr(window, 'sync_clear_to_luminance'):
            window.sync_clear_to_luminance()

    def set_histogram_mode(self, mode: str):
        """设置直方图显示模式

        Args:
            mode: 'rgb' 或 'hue'
        """
        if mode == 'hue':
            self.histogram_stack.setCurrentIndex(1)
        else:
            self.histogram_stack.setCurrentIndex(0)

    def _on_favorite_clicked(self):
        """收藏按钮点击回调"""
        colors = []
        for card in self.color_card_panel.cards:
            if card._current_color_info:
                colors.append(card._current_color_info)

        if not colors:
            InfoBar.warning(
                title="无法收藏",
                content="请先提取颜色后再收藏",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 弹出命名对话框
        default_name = f"配色方案 {len(self._config_manager.get_favorites()) + 1}"
        dialog = NameDialog(
            title="命名配色方案",
            default_name=default_name,
            parent=self.window()
        )

        if dialog.exec() != NameDialog.DialogCode.Accepted:
            return

        favorite_name = dialog.get_name()

        favorite_data = {
            "id": str(uuid.uuid4()),
            "name": favorite_name,
            "colors": colors,
            "created_at": datetime.now().isoformat(),
            "source": "color_extract"
        }

        self._config_manager.add_favorite(favorite_data)
        self._config_manager.save()

        # 刷新色彩管理面板
        window = self.window()
        if window and hasattr(window, 'refresh_color_management'):
            window.refresh_color_management()

        InfoBar.success(
            title="收藏成功",
            content=f"已收藏配色方案：{favorite_name}",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

    def _on_extract_dominant_clicked(self):
        """主色调提取按钮点击回调"""
        image = self.image_canvas.get_image()
        if not image or image.isNull():
            InfoBar.warning(
                title="无法提取",
                content="请先导入图片",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 获取当前设置的采样点数量
        count = self._config_manager.get('settings.color_sample_count', 5)

        # 取消之前的提取线程（如果存在）
        if self._extractor is not None and self._extractor.isRunning():
            self._extractor.cancel()
            self._extractor = None

        # 显示正在提取的提示
        InfoBar.info(
            title="正在提取",
            content="正在分析图片主色调，请稍候...",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

        # 禁用提取按钮，防止重复点击
        self.extract_dominant_button.setEnabled(False)
        self.extract_dominant_button.setText("提取中...")

        # 创建并启动提取线程
        self._extractor = DominantColorExtractor(image, count=count, parent=self)
        self._extractor.extraction_finished.connect(self._on_extraction_finished)
        self._extractor.extraction_error.connect(self._on_extraction_error)
        self._extractor.finished.connect(self._on_extraction_finished_cleanup)
        self._extractor.start()

    def _on_extraction_finished(self, dominant_colors, positions):
        """主色调提取完成回调

        Args:
            dominant_colors: 主色调列表 [(r, g, b), ...]
            positions: 颜色位置列表 [(rel_x, rel_y), ...]
        """
        count = self._config_manager.get('settings.color_sample_count', 5)

        # 更新取色点位置
        self.image_canvas.set_picker_positions_by_colors(dominant_colors, positions)

        # 更新HSB色环上的采样点
        for i, rgb in enumerate(dominant_colors):
            if i < count:
                self.hsb_color_wheel.update_sample_point(i, rgb)

        InfoBar.success(
            title="提取完成",
            content=f"已成功提取 {len(dominant_colors)} 个主色调",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

    def _on_extraction_error(self, error_message):
        """主色调提取失败回调

        Args:
            error_message: 错误信息
        """
        InfoBar.error(
            title="提取失败",
            content=f"提取过程中发生错误: {error_message}",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self.window()
        )

    def _on_extraction_finished_cleanup(self):
        """主色调提取完成后的清理工作"""
        # 恢复提取按钮状态
        self.extract_dominant_button.setEnabled(True)
        self.extract_dominant_button.setText("自动提取主色调")

        # 清理线程引用
        if self._extractor is not None:
            self._extractor.deleteLater()
            self._extractor = None


class LuminanceExtractInterface(QWidget):
    """明度提取界面"""

    # 信号：图片已独立导入（用于同步到色彩提取面板）
    image_imported = Signal(str, object, object)  # 图片路径, QPixmap, QImage

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

    def open_image(self):
        """打开图片文件（独立导入）"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
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


class SettingsInterface(QWidget):
    """设置界面"""

    # 信号：16进制显示开关状态改变
    hex_display_changed = Signal(bool)
    # 信号：色彩模式改变
    color_modes_changed = Signal(list)
    # 信号：色彩提取采样点数改变
    color_sample_count_changed = Signal(int)
    # 信号：明度提取采样点数改变
    luminance_sample_count_changed = Signal(int)
    # 信号：直方图缩放模式改变
    histogram_scaling_mode_changed = Signal(str)
    # 信号：色轮模式改变
    color_wheel_mode_changed = Signal(str)
    # 信号：直方图模式改变
    histogram_mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('settings')
        self._config_manager = get_config_manager()
        self._hex_visible = self._config_manager.get('settings.hex_visible', True)
        self._color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self._color_sample_count = self._config_manager.get('settings.color_sample_count', 5)
        self._luminance_sample_count = self._config_manager.get('settings.luminance_sample_count', 5)
        self._histogram_scaling_mode = self._config_manager.get('settings.histogram_scaling_mode', 'linear')
        self._color_wheel_mode = self._config_manager.get('settings.color_wheel_mode', 'RGB')
        self._histogram_mode = self._config_manager.get('settings.histogram_mode', 'hue')
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面布局"""
        # 创建滚动区域
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # 创建内容容器
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 标题
        self.title_label = SubtitleLabel("设置")
        layout.addWidget(self.title_label)

        # 色卡显示设置分组
        self.card_display_group = SettingCardGroup("色卡显示设置", self.content_widget)

        # 16进制颜色值显示开关卡片
        self.hex_display_card = self._create_switch_card(
            FluentIcon.PALETTE,
            "显示16进制颜色值",
            "在色彩提取面板的色卡中显示16进制颜色值和复制按钮",
            self._hex_visible
        )
        self.card_display_group.addSettingCard(self.hex_display_card)

        # 色彩模式选择卡片
        self.color_mode_card = self._create_color_mode_card()
        self.card_display_group.addSettingCard(self.color_mode_card)

        layout.addWidget(self.card_display_group)

        # 采样设置分组
        self.sampling_group = SettingCardGroup("采样设置", self.content_widget)

        # 色彩提取采样点数卡片
        self.color_sample_count_card = self._create_spin_box_card(
            FluentIcon.PALETTE,
            "色彩提取采样点数",
            "设置色彩提取面板的采样点数量（2-5）",
            self._color_sample_count,
            2,
            5,
            self._on_color_sample_count_changed
        )
        self.sampling_group.addSettingCard(self.color_sample_count_card)

        # 明度提取采样点数卡片
        self.luminance_sample_count_card = self._create_spin_box_card(
            FluentIcon.BRIGHTNESS,
            "明度提取采样点数",
            "设置明度提取面板的采样点数量（2-5）",
            self._luminance_sample_count,
            2,
            5,
            self._on_luminance_sample_count_changed
        )
        self.sampling_group.addSettingCard(self.luminance_sample_count_card)

        layout.addWidget(self.sampling_group)

        # 直方图设置分组
        self.histogram_group = SettingCardGroup("直方图设置", self.content_widget)

        # 直方图缩放模式卡片
        self.histogram_scaling_card = self._create_histogram_scaling_card()
        self.histogram_group.addSettingCard(self.histogram_scaling_card)

        # 直方图模式卡片（RGB/色相）
        self.histogram_mode_card = self._create_histogram_mode_card()
        self.histogram_group.addSettingCard(self.histogram_mode_card)

        layout.addWidget(self.histogram_group)

        # 配色方案设置分组
        self.color_scheme_group = SettingCardGroup("配色方案设置", self.content_widget)

        # 色轮模式卡片
        self.color_wheel_mode_card = self._create_color_wheel_mode_card()
        self.color_scheme_group.addSettingCard(self.color_wheel_mode_card)

        layout.addWidget(self.color_scheme_group)

        # 帮助分组
        self.help_group = SettingCardGroup("帮助", self.content_widget)

        # 版本更新卡片
        self.update_card = PushSettingCard(
            "检查更新",
            FluentIcon.DOWNLOAD,
            "版本更新",
            "检查软件是否有新版本可用",
            self.help_group
        )
        self.update_card.clicked.connect(self.on_check_update)
        # 设置按钮固定宽度
        self.update_card.button.setFixedWidth(130)
        self.help_group.addSettingCard(self.update_card)

        # 关于卡片
        self.about_card = PushSettingCard(
            "查看",
            FluentIcon.INFO,
            "关于 Color Card",
            "查看项目、文档等信息",
            self.help_group
        )
        self.about_card.clicked.connect(self.on_show_about)
        # 设置按钮固定宽度，与检查更新按钮一致
        self.about_card.button.setFixedWidth(130)
        self.help_group.addSettingCard(self.about_card)

        layout.addWidget(self.help_group)

        # 添加弹性空间
        layout.addStretch()

        # 将内容容器设置到滚动区域
        self.scroll_area.setWidget(self.content_widget)

        # 设置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll_area)

    def _create_switch_card(self, icon, title, content, initial_checked):
        """创建自定义开关卡片"""
        card = PushSettingCard("", icon, title, content, self.content_widget)
        card.button.setVisible(False)  # 隐藏默认按钮

        # 创建开关按钮
        switch = SwitchButton(self.content_widget)
        switch.setChecked(initial_checked)
        switch.setOnText("开")
        switch.setOffText("关")
        switch.checkedChanged.connect(self._on_hex_display_changed)

        # 将开关添加到卡片布局
        card.hBoxLayout.addWidget(switch, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        # 保存开关引用
        card.switch_button = switch

        return card

    def _create_spin_box_card(self, icon, title, content, initial_value, min_value, max_value, callback):
        """创建自定义下拉列表卡片"""
        card = PushSettingCard("", icon, title, content, self.content_widget)
        card.button.setVisible(False)

        # 创建ComboBox控件
        combo_box = ComboBox(self.content_widget)
        # 添加数值选项
        for i in range(min_value, max_value + 1):
            combo_box.addItem(str(i))
        combo_box.setCurrentText(str(initial_value))
        combo_box.setFixedWidth(80)
        combo_box.currentTextChanged.connect(lambda text: callback(int(text)))

        # 将ComboBox添加到卡片布局
        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        # 保存ComboBox引用
        card.combo_box = combo_box

        return card

    def _create_color_mode_card(self):
        """创建色彩模式选择卡片"""
        card = PushSettingCard(
            "",
            FluentIcon.BRUSH,
            "色彩模式显示",
            "选择在色卡中显示的两种色彩模式",
            self.content_widget
        )
        card.button.setVisible(False)  # 隐藏默认按钮

        # 创建选择控件容器
        combo_container = QWidget(self.content_widget)
        combo_layout = QHBoxLayout(combo_container)
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(10)

        # 第一列选择
        self.mode_combo_1 = ComboBox(combo_container)
        self.mode_combo_1.addItems(AVAILABLE_COLOR_MODES)
        self.mode_combo_1.setCurrentText(self._color_modes[0])
        self.mode_combo_1.setFixedWidth(80)
        self.mode_combo_1.currentTextChanged.connect(self._on_color_mode_changed)

        # 分隔标签
        separator = QLabel("+", combo_container)
        separator.setStyleSheet("color: gray;")

        # 第二列选择
        self.mode_combo_2 = ComboBox(combo_container)
        self.mode_combo_2.addItems(AVAILABLE_COLOR_MODES)
        self.mode_combo_2.setCurrentText(self._color_modes[1])
        self.mode_combo_2.setFixedWidth(80)
        self.mode_combo_2.currentTextChanged.connect(self._on_color_mode_changed)

        combo_layout.addWidget(self.mode_combo_1)
        combo_layout.addWidget(separator)
        combo_layout.addWidget(self.mode_combo_2)

        # 将选择控件添加到卡片布局
        card.hBoxLayout.addWidget(combo_container, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        return card

    def _on_hex_display_changed(self, checked):
        """16进制显示开关状态改变"""
        self._hex_visible = checked
        self._config_manager.set('settings.hex_visible', checked)
        self._config_manager.save()
        self.hex_display_changed.emit(checked)

    def _on_color_mode_changed(self):
        """色彩模式选择改变"""
        mode1 = self.mode_combo_1.currentText()
        mode2 = self.mode_combo_2.currentText()

        # 如果两列选择相同，自动调整第二列
        if mode1 == mode2:
            # 找到下一个不同的模式
            for mode in AVAILABLE_COLOR_MODES:
                if mode != mode1:
                    self.mode_combo_2.setCurrentText(mode)
                    mode2 = mode
                    break

        self._color_modes = [mode1, mode2]
        self._config_manager.set('settings.color_modes', self._color_modes)
        self._config_manager.save()
        self.color_modes_changed.emit(self._color_modes)

    def _on_color_sample_count_changed(self, value):
        """色彩提取采样点数改变"""
        self._color_sample_count = value
        self._config_manager.set('settings.color_sample_count', value)
        self._config_manager.save()
        self.color_sample_count_changed.emit(value)

    def _on_luminance_sample_count_changed(self, value):
        """明度提取采样点数改变"""
        self._luminance_sample_count = value
        self._config_manager.set('settings.luminance_sample_count', value)
        self._config_manager.save()
        self.luminance_sample_count_changed.emit(value)

    def _create_histogram_scaling_card(self):
        """创建直方图缩放模式选择卡片"""
        card = PushSettingCard(
            "",
            FluentIcon.DOCUMENT,
            "直方图缩放模式",
            "选择直方图的缩放方式（线性/自适应）",
            self.content_widget
        )
        card.button.setVisible(False)

        # 创建ComboBox控件
        combo_box = ComboBox(self.content_widget)
        combo_box.addItem("线性缩放")
        combo_box.setItemData(0, "linear")
        combo_box.addItem("自适应缩放")
        combo_box.setItemData(1, "adaptive")

        # 设置当前值
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == self._histogram_scaling_mode:
                combo_box.setCurrentIndex(i)
                break

        combo_box.setFixedWidth(120)
        combo_box.currentIndexChanged.connect(self._on_histogram_scaling_mode_changed)

        # 将ComboBox添加到卡片布局
        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        # 保存ComboBox引用
        card.combo_box = combo_box

        return card

    def _on_histogram_scaling_mode_changed(self, index):
        """直方图缩放模式改变"""
        combo_box = self.histogram_scaling_card.combo_box
        mode = combo_box.itemData(index)
        self._histogram_scaling_mode = mode
        self._config_manager.set('settings.histogram_scaling_mode', mode)
        self._config_manager.save()
        self.histogram_scaling_mode_changed.emit(mode)

    def _create_histogram_mode_card(self):
        """创建直方图模式选择卡片"""
        card = PushSettingCard(
            "",
            FluentIcon.PALETTE,
            "直方图显示模式",
            "选择色彩提取面板的直方图类型（RGB通道/色相分布）",
            self.content_widget
        )
        card.button.setVisible(False)

        # 创建ComboBox控件
        combo_box = ComboBox(self.content_widget)
        combo_box.addItem("RGB 通道")
        combo_box.setItemData(0, "rgb")
        combo_box.addItem("色相分布")
        combo_box.setItemData(1, "hue")

        # 设置当前值
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == self._histogram_mode:
                combo_box.setCurrentIndex(i)
                break

        combo_box.setFixedWidth(120)
        combo_box.currentIndexChanged.connect(self._on_histogram_mode_changed)

        # 将ComboBox添加到卡片布局
        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        # 保存ComboBox引用
        card.combo_box = combo_box

        return card

    def _on_histogram_mode_changed(self, index):
        """直方图模式改变"""
        combo_box = self.histogram_mode_card.combo_box
        mode = combo_box.itemData(index)
        self._histogram_mode = mode
        self._config_manager.set('settings.histogram_mode', mode)
        self._config_manager.save()
        self.histogram_mode_changed.emit(mode)

    def _create_color_wheel_mode_card(self):
        """创建配色方案模式选择卡片"""
        card = PushSettingCard(
            "",
            FluentIcon.PALETTE,
            "配色方案模式",
            "选择配色方案使用的色彩逻辑（RGB: 光学混色，RYB: 美术混色）",
            self.content_widget
        )
        card.button.setVisible(False)

        # 创建ComboBox控件
        combo_box = ComboBox(self.content_widget)
        combo_box.addItem("RGB 光学")
        combo_box.setItemData(0, "RGB")
        combo_box.addItem("RYB 美术")
        combo_box.setItemData(1, "RYB")

        # 设置当前值
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == self._color_wheel_mode:
                combo_box.setCurrentIndex(i)
                break

        combo_box.setFixedWidth(120)
        combo_box.currentIndexChanged.connect(self._on_color_wheel_mode_changed)

        # 将ComboBox添加到卡片布局
        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        # 保存ComboBox引用
        card.combo_box = combo_box

        return card

    def _on_color_wheel_mode_changed(self, index):
        """色轮模式改变"""
        combo_box = self.color_wheel_mode_card.combo_box
        mode = combo_box.itemData(index)
        self._color_wheel_mode = mode
        self._config_manager.set('settings.color_wheel_mode', mode)
        self._config_manager.save()
        self.color_wheel_mode_changed.emit(mode)

    def set_hex_visible(self, visible):
        """设置16进制显示开关状态"""
        self._hex_visible = visible
        if hasattr(self.hex_display_card, 'switch_button'):
            self.hex_display_card.switch_button.setChecked(visible)

    def is_hex_visible(self):
        """获取16进制显示开关状态"""
        return self._hex_visible

    def set_color_modes(self, modes):
        """设置色彩模式选择"""
        if len(modes) >= 2:
            self._color_modes = [modes[0], modes[1]]
            self.mode_combo_1.setCurrentText(modes[0])
            self.mode_combo_2.setCurrentText(modes[1])

    def get_color_modes(self):
        """获取当前色彩模式"""
        return self._color_modes

    def get_color_wheel_mode(self):
        """获取当前色轮模式"""
        return self._color_wheel_mode

    def set_color_wheel_mode(self, mode):
        """设置色轮模式

        Args:
            mode: 'RGB' 或 'RYB'
        """
        self._color_wheel_mode = mode
        if hasattr(self.color_wheel_mode_card, 'combo_box'):
            combo_box = self.color_wheel_mode_card.combo_box
            for i in range(combo_box.count()):
                if combo_box.itemData(i) == mode:
                    combo_box.setCurrentIndex(i)
                    break

    def on_check_update(self):
        """检查更新按钮点击"""
        current_version = version_manager.get_version()
        UpdateAvailableDialog.check_update(self, current_version)

    def on_show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()

    def _update_styles(self):
        """更新样式以适配主题"""
        title_color = get_title_color()
        self.title_label.setStyleSheet(f"color: {title_color.name()};")
        
        # 只在 Win10 上应用强制样式（Win11 上 qfluentwidgets 能正常工作）
        if is_windows_10():
            bg_color = get_interface_background_color()
            card_bg = get_card_background_color()
            border_color = get_border_color()
            text_color = get_text_color()
            secondary_text = get_text_color(secondary=True)
            
            self.setStyleSheet(f"""
                SettingsInterface {{
                    background-color: transparent;
                }}
                ScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
                ScrollArea > QWidget > QWidget {{
                    background-color: transparent;
                }}
                SettingCardGroup {{
                    background-color: {card_bg.name()};
                    border: none;
                }}
                SettingCardGroup::title {{
                    color: {text_color.name()};
                    font-size: 14px;
                    font-weight: bold;
                }}
                PushSettingCard {{
                    background-color: {card_bg.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 8px;
                }}
                PushSettingCard:hover {{
                    background-color: {card_bg.lighter(110).name() if not isDarkTheme() else card_bg.darker(110).name()};
                }}
                PushSettingCard QLabel#titleLabel {{
                    color: {text_color.name()};
                    font-size: 13px;
                }}
                PushSettingCard QLabel#contentLabel {{
                    color: {secondary_text.name()};
                    font-size: 11px;
                }}
                ComboBox {{
                    background-color: {card_bg.name()};
                    color: {text_color.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 4px;
                }}
                SwitchButton {{
                    background-color: transparent;
                }}
                SpinBox {{
                    background-color: {card_bg.name()};
                    color: {text_color.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 4px;
                }}
            """)


class ColorSchemeInterface(QWidget):
    """配色方案界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('colorSchemeInterface')
        self._current_scheme = 'monochromatic'
        self._base_hue = 0.0
        self._base_saturation = 100.0
        self._base_brightness = 100.0
        self._brightness_value = 100  # 全局明度值 (10-100)，直接对应HSB的B值
        self._scheme_colors = []  # 配色方案颜色列表 [(h, s, b), ...]
        self._color_wheel_mode = 'RGB'  # 色轮模式：RGB 或 RYB
        self._colors_generated = False  # 颜色是否已生成（延迟生成优化）

        self._config_manager = get_config_manager()

        self.setup_ui()
        self.setup_connections()
        self._load_settings()
        # 根据初始配色方案设置卡片数量
        self._update_card_count()
        # 延迟生成配色方案颜色，避免阻塞启动
        # 颜色将在首次显示时生成
        self._update_styles()
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_styles)

    def showEvent(self, event):
        """界面显示事件，延迟生成配色方案颜色"""
        super().showEvent(event)
        # 首次显示时生成配色方案颜色
        if not self._colors_generated:
            self._colors_generated = True
            QTimer.singleShot(0, self._generate_scheme_colors)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部控制栏（居中显示）
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setSpacing(15)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 配色方案选择下拉框
        self.scheme_label = QLabel("配色方案:")
        top_layout.addWidget(self.scheme_label)

        self.scheme_combo = ComboBox(self)
        self.scheme_combo.addItem("同色系")
        self.scheme_combo.addItem("邻近色")
        self.scheme_combo.addItem("互补色")
        self.scheme_combo.addItem("分离补色")
        self.scheme_combo.addItem("双补色")
        self.scheme_combo.setItemData(0, "monochromatic")
        self.scheme_combo.setItemData(1, "analogous")
        self.scheme_combo.setItemData(2, "complementary")
        self.scheme_combo.setItemData(3, "split_complementary")
        self.scheme_combo.setItemData(4, "double_complementary")
        self.scheme_combo.setFixedWidth(150)
        top_layout.addWidget(self.scheme_combo)

        # 随机按钮
        self.random_btn = PrimaryPushButton(FluentIcon.SYNC, "随机", self)
        self.random_btn.setFixedWidth(100)
        top_layout.addWidget(self.random_btn)

        # 收藏按钮
        self.favorite_button = PrimaryPushButton(FluentIcon.HEART, "收藏", self)
        self.favorite_button.setFixedWidth(80)
        self.favorite_button.clicked.connect(self._on_favorite_clicked)
        top_layout.addWidget(self.favorite_button)

        layout.addWidget(top_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # 使用分割器分隔上下区域（避免重叠）
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setMinimumHeight(300)
        splitter.setHandleWidth(0)  # 隐藏分隔条
        layout.addWidget(splitter, stretch=1)

        # 上半部分：色轮和明度调整
        upper_widget = QWidget()
        upper_layout = QVBoxLayout(upper_widget)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(15)

        # 色轮容器（与图片显示组件样式一致）
        self.wheel_container = QWidget(self)
        self.wheel_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.wheel_container.setMinimumSize(300, 200)
        bg_color = get_canvas_empty_bg_color()
        self.wheel_container.setStyleSheet(f"background-color: {bg_color.name()}; border-radius: 8px;")

        wheel_container_layout = QVBoxLayout(self.wheel_container)
        wheel_container_layout.setContentsMargins(10, 10, 10, 10)

        # 可交互色环（在容器内自适应，占满整个容器）
        self.color_wheel = InteractiveColorWheel(self.wheel_container)
        wheel_container_layout.addWidget(self.color_wheel, stretch=1)

        upper_layout.addWidget(self.wheel_container, stretch=1)

        # 明度调整滑块（色轮下方，整体居中但控件紧凑排列）
        brightness_container = QWidget()
        brightness_layout = QHBoxLayout(brightness_container)
        brightness_layout.setSpacing(5)
        brightness_layout.setContentsMargins(0, 0, 0, 0)

        self.brightness_label = QLabel("明度调整:")
        brightness_layout.addWidget(self.brightness_label)

        self.brightness_slider = Slider(Qt.Orientation.Horizontal, brightness_container)
        self.brightness_slider.setRange(10, 100)
        self.brightness_slider.setValue(100)
        self.brightness_slider.setFixedWidth(200)
        brightness_layout.addWidget(self.brightness_slider)

        self.brightness_value_label = QLabel("100")
        self.brightness_value_label.setFixedWidth(30)
        brightness_layout.addWidget(self.brightness_value_label)

        upper_layout.addWidget(brightness_container, alignment=Qt.AlignmentFlag.AlignCenter)

        splitter.addWidget(upper_widget)

        # 下方：色块面板
        self.color_panel = SchemeColorPanel(self)
        self.color_panel.setMinimumHeight(150)
        splitter.addWidget(self.color_panel)

        splitter.setSizes([400, 200])

    def setup_connections(self):
        """设置信号连接"""
        self.scheme_combo.currentIndexChanged.connect(self.on_scheme_changed)
        self.random_btn.clicked.connect(self.on_random_clicked)
        self.color_wheel.base_color_changed.connect(self.on_base_color_changed)
        self.color_wheel.scheme_color_changed.connect(self.on_scheme_color_changed)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)

    def _update_styles(self):
        """更新样式以适配主题"""
        if isDarkTheme():
            label_color = "#ffffff"
            value_color = "#ffffff"
        else:
            label_color = "#333333"
            value_color = "#333333"
        
        self.scheme_label.setStyleSheet(f"color: {label_color};")
        self.brightness_label.setStyleSheet(f"color: {label_color};")
        self.brightness_value_label.setStyleSheet(f"color: {value_color};")

    def _load_settings(self):
        """加载显示设置"""
        # 从配置管理器读取设置
        hex_visible = self._config_manager.get('settings.hex_visible', True)
        color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self._color_wheel_mode = self._config_manager.get('settings.color_wheel_mode', 'RGB')

        # 应用设置到色块面板
        self.color_panel.update_settings(hex_visible, color_modes)

    def _update_card_count(self):
        """根据当前配色方案更新卡片数量"""
        scheme_counts = {
            'monochromatic': 4,      # 同色系：4个
            'analogous': 4,          # 邻近色：4个
            'complementary': 5,      # 互补色：5个
            'split_complementary': 3, # 分离补色：3个
            'double_complementary': 4  # 双补色：4个
        }
        count = scheme_counts.get(self._current_scheme, 5)
        self.color_panel.set_card_count(count)

    def update_display_settings(self, hex_visible=None, color_modes=None):
        """更新显示设置（由设置界面调用）

        Args:
            hex_visible: 是否显示16进制颜色值
            color_modes: 色彩模式列表
        """
        if hex_visible is not None:
            self.color_panel.set_hex_visible(hex_visible)

        if color_modes is not None and len(color_modes) >= 2:
            self.color_panel.set_color_modes(color_modes)

    def on_scheme_changed(self, index):
        """配色方案改变回调"""
        self._current_scheme = self.scheme_combo.currentData()

        # 根据配色方案类型调整卡片数量
        self._update_card_count()

        self._generate_scheme_colors()

    def on_random_clicked(self):
        """随机按钮点击回调"""
        import random
        self._base_hue = random.uniform(0, 360)
        self._base_saturation = random.uniform(60, 100)
        self.color_wheel.set_base_color(self._base_hue, self._base_saturation, self._base_brightness)
        self._generate_scheme_colors()

    def on_base_color_changed(self, h, s, b):
        """基准颜色改变回调"""
        self._base_hue = h
        self._base_saturation = s
        self._generate_scheme_colors()

    def on_scheme_color_changed(self, index, h, s, b):
        """配色方案采样点颜色改变回调

        Args:
            index: 采样点索引
            h: 色相
            s: 饱和度
            b: 亮度
        """
        from core import hsb_to_rgb

        # 更新配色方案数据
        if 0 <= index < len(self._scheme_colors):
            self._scheme_colors[index] = (h, s, b)

            # 转换为RGB并更新色块面板
            rgb = hsb_to_rgb(h, s, b)
            self.color_panel.set_colors([hsb_to_rgb(*c) for c in self._scheme_colors])

    def on_brightness_changed(self, value):
        """明度调整回调"""
        self._brightness_value = value
        self.brightness_value_label.setText(str(value))
        # 更新色轮的全局明度
        self.color_wheel.set_global_brightness(value)
        self._generate_scheme_colors()

    def set_color_wheel_mode(self, mode: str):
        """设置色轮模式

        Args:
            mode: 'RGB' 或 'RYB'
        """
        if self._color_wheel_mode != mode:
            self._color_wheel_mode = mode
            self._generate_scheme_colors()

    def _generate_scheme_colors(self):
        """生成配色方案颜色"""
        from core import (
            get_scheme_preview_colors, get_scheme_preview_colors_ryb,
            adjust_brightness, hsb_to_rgb, rgb_to_hsb
        )

        # 根据配色方案类型确定颜色数量
        scheme_counts = {
            'monochromatic': 4,      # 同色系：4个
            'analogous': 4,          # 邻近色：4个
            'complementary': 5,      # 互补色：5个
            'split_complementary': 3, # 分离补色：3个
            'double_complementary': 4  # 双补色：4个
        }
        count = scheme_counts.get(self._current_scheme, 5)

        # 根据色轮模式选择对应的配色生成函数，传入基准饱和度
        if self._color_wheel_mode == 'RYB':
            colors = get_scheme_preview_colors_ryb(self._current_scheme, self._base_hue, count, self._base_saturation)
        else:
            colors = get_scheme_preview_colors(self._current_scheme, self._base_hue, count, self._base_saturation)

        # 转换为HSB并应用全局明度值
        self._scheme_colors = []
        for i, rgb in enumerate(colors):
            h, s, b = rgb_to_hsb(*rgb)
            # 使用全局明度值，忽略原始配色方案中的B值
            self._scheme_colors.append((h, s, self._brightness_value))

        # 转换为RGB颜色用于显示
        colors = [hsb_to_rgb(h, s, b) for h, s, b in self._scheme_colors]

        # 更新色块面板
        self.color_panel.set_colors(colors)

        # 更新色环上的配色方案点
        self.color_wheel.set_scheme_colors(self._scheme_colors)

    def _on_favorite_clicked(self):
        """收藏按钮点击回调"""
        colors = []
        for card in self.color_panel.cards:
            if card._current_color_info:
                colors.append(card._current_color_info)

        if not colors:
            InfoBar.warning(
                title="无法收藏",
                content="没有可收藏的配色方案",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 弹出命名对话框
        default_name = f"配色方案 {len(self._config_manager.get_favorites()) + 1}"
        dialog = NameDialog(
            title="命名配色方案",
            default_name=default_name,
            parent=self.window()
        )

        if dialog.exec() != NameDialog.DialogCode.Accepted:
            return

        favorite_name = dialog.get_name()

        favorite_data = {
            "id": str(uuid.uuid4()),
            "name": favorite_name,
            "colors": colors,
            "created_at": datetime.now().isoformat(),
            "source": "color_scheme"
        }

        self._config_manager.add_favorite(favorite_data)
        self._config_manager.save()

        # 刷新色彩管理面板
        window = self.window()
        if window and hasattr(window, 'refresh_color_management'):
            window.refresh_color_management()

        InfoBar.success(
            title="收藏成功",
            content=f"已收藏配色方案：{favorite_name}",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )


class ColorManagementInterface(QWidget):
    """色彩管理界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('colorManagementInterface')
        self._config_manager = get_config_manager()
        self.setup_ui()
        self._load_favorites()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = SubtitleLabel("色彩管理")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.import_button = PushButton(FluentIcon.DOWN, "导入", self)
        self.import_button.clicked.connect(self._on_import_clicked)
        header_layout.addWidget(self.import_button)

        self.export_button = PushButton(FluentIcon.UP, "导出", self)
        self.export_button.clicked.connect(self._on_export_clicked)
        header_layout.addWidget(self.export_button)

        self.clear_all_button = PushButton(FluentIcon.DELETE, "清空所有", self)
        self.clear_all_button.setMinimumWidth(100)
        self.clear_all_button.clicked.connect(self._on_clear_all_clicked)
        header_layout.addWidget(self.clear_all_button)

        layout.addLayout(header_layout)

        self.color_management_list = ColorManagementSchemeList(self)
        self.color_management_list.favorite_deleted.connect(self._on_favorite_deleted)
        self.color_management_list.favorite_renamed.connect(self._on_favorite_renamed)
        self.color_management_list.favorite_preview.connect(self._on_favorite_preview)
        self.color_management_list.favorite_contrast.connect(self._on_favorite_contrast)
        self.color_management_list.favorite_color_changed.connect(self._on_favorite_color_changed)
        layout.addWidget(self.color_management_list, stretch=1)

    def _load_favorites(self):
        """加载收藏列表"""
        favorites = self._config_manager.get_favorites()
        self.color_management_list.set_favorites(favorites)

    def _on_clear_all_clicked(self):
        """清空所有按钮点击"""
        from qfluentwidgets import MessageBox, FluentIcon as FIcon

        msg_box = MessageBox(
            "确认清空",
            "确定要清空所有收藏的配色方案吗？此操作不可撤销。",
            self
        )
        msg_box.yesButton.setText("确定")
        msg_box.cancelButton.setText("取消")
        if msg_box.exec():
            self._config_manager.clear_favorites()
            self._config_manager.save()
            self._load_favorites()

    def _on_favorite_deleted(self, favorite_id):
        """收藏删除回调"""
        self._config_manager.delete_favorite(favorite_id)
        self._config_manager.save()
        self._load_favorites()

    def _on_favorite_renamed(self, favorite_id, current_name):
        """收藏重命名回调

        Args:
            favorite_id: 收藏项ID
            current_name: 当前名称
        """
        dialog = NameDialog(
            title="重命名配色方案",
            default_name=current_name,
            parent=self.window()
        )

        if dialog.exec() != NameDialog.DialogCode.Accepted:
            return

        new_name = dialog.get_name()

        # 更新收藏名称
        if self._config_manager.rename_favorite(favorite_id, new_name):
            self._config_manager.save()
            self._load_favorites()

            InfoBar.success(
                title="重命名成功",
                content=f"已重命名为：{new_name}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
        else:
            InfoBar.error(
                title="重命名失败",
                content="无法找到该配色方案",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )

    def _on_import_clicked(self):
        """导入按钮点击"""
        from qfluentwidgets import MessageBox

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入收藏",
            "",
            "JSON 文件 (*.json);;所有文件 (*)"
        )

        if not file_path:
            return

        # 询问导入模式 - 使用两个独立的对话框
        msg_box = MessageBox(
            "选择导入模式",
            "请选择导入方式：\n\n点击「是」追加到现有收藏\n点击「否」替换现有收藏",
            self
        )
        msg_box.yesButton.setText("追加")
        msg_box.cancelButton.setText("替换")

        # 获取结果：1=追加, 0=替换
        result = msg_box.exec()

        # 确定导入模式
        if result == 1:  # 点击了"追加"
            mode = 'append'
        else:  # 点击了"替换"
            mode = 'replace'

        success, count, error_msg = self._config_manager.import_favorites(file_path, mode)

        if success:
            self._config_manager.save()
            self._load_favorites()
            InfoBar.success(
                title="导入成功",
                content=f"成功导入 {count} 个配色方案",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            InfoBar.error(
                title="导入失败",
                content=error_msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )

    def _on_export_clicked(self):
        """导出按钮点击"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出收藏",
            "color_card_favorites.json",
            "JSON 文件 (*.json);;所有文件 (*)"
        )

        if not file_path:
            return

        # 确保文件扩展名为 .json
        if not file_path.endswith('.json'):
            file_path += '.json'

        success = self._config_manager.export_favorites(file_path)

        if success:
            InfoBar.success(
                title="导出成功",
                content=f"收藏已导出到：{file_path}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            InfoBar.error(
                title="导出失败",
                content="导出过程中发生错误，请检查文件路径和权限",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )

    def _on_favorite_preview(self, favorite_data):
        """收藏预览回调（色盲模拟）

        Args:
            favorite_data: 收藏项数据
        """
        scheme_name = favorite_data.get('name', '未命名')
        colors = favorite_data.get('colors', [])

        if not colors:
            InfoBar.warning(
                title="无法预览",
                content="该配色方案没有颜色数据",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 显示色盲模拟预览对话框
        dialog = ColorblindPreviewDialog(
            scheme_name=scheme_name,
            colors=colors,
            parent=self.window()
        )
        dialog.exec()

    def _on_favorite_contrast(self, favorite_data):
        """收藏对比度检查回调

        Args:
            favorite_data: 收藏项数据
        """
        scheme_name = favorite_data.get('name', '未命名')
        colors = favorite_data.get('colors', [])

        if not colors:
            InfoBar.warning(
                title="无法检查",
                content="该配色方案没有颜色数据",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 显示对比度检查对话框
        dialog = ContrastCheckDialog(
            scheme_name=scheme_name,
            colors=colors,
            parent=self.window()
        )
        dialog.exec()

    def _on_favorite_color_changed(self, favorite_id: str, color_index: int, color_info: dict):
        """收藏颜色变化回调

        Args:
            favorite_id: 收藏项ID
            color_index: 颜色索引
            color_info: 新的颜色信息
        """
        # 更新配置中的颜色数据
        if self._config_manager.update_favorite_color(favorite_id, color_index, color_info):
            self._config_manager.save()

            InfoBar.success(
                title="颜色已更新",
                content=f"配色方案中的颜色已更新为 {color_info.get('hex', '#------')}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )

    def update_display_settings(self, hex_visible=None, color_modes=None):
        """更新显示设置

        Args:
            hex_visible: 是否显示16进制颜色值
            color_modes: 色彩模式列表
        """
        self.color_management_list.update_display_settings(hex_visible, color_modes)

    def _update_styles(self):
        """更新样式以适配主题"""
        title_color = get_title_color()
        self.title_label.setStyleSheet(f"color: {title_color.name()};")
        
        # 只在 Win10 上应用强制样式（Win11 上 qfluentwidgets 能正常工作）
        if is_windows_10():
            bg_color = get_interface_background_color()
            card_bg = get_card_background_color()
            border_color = get_border_color()
            text_color = get_text_color()
            
            self.setStyleSheet(f"""
                ColorManagementInterface {{
                    background-color: {bg_color.name()};
                }}
                ScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
                ScrollArea > QWidget > QWidget {{
                    background-color: transparent;
                }}
                ColorManagementSchemeCard,
                CardWidget {{
                    background-color: {card_bg.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 8px;
                }}
                PushButton {{
                    background-color: {card_bg.name()};
                    color: {text_color.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 4px;
                }}
                PushButton:hover {{
                    background-color: {card_bg.lighter(110).name() if not isDarkTheme() else card_bg.darker(110).name()};
                }}
                QLabel {{
                    color: {text_color.name()};
                }}
            """)


class PresetColorInterface(QWidget):
    """内置色彩界面（支持 Open Color、Nice Color Palettes、Tailwind Colors、Material Design、ColorBrewer 和 Radix Colors）"""

    favorite_requested = Signal(dict)  # 信号：收藏数据字典

    # 每组显示的配色方案数量
    PALETTES_PER_GROUP = 50

    # Open Color 分组定义
    OPEN_COLOR_GROUPS = [
        (["gray", "red", "pink", "grape"], "灰/红/粉/紫组"),
        (["violet", "indigo", "blue", "cyan"], "紫/蓝/青组"),
        (["teal", "green", "lime", "yellow", "orange"], "绿/黄/橙组"),
    ]

    # Tailwind Colors 分组定义
    TAILWIND_GROUPS = [
        (["slate", "gray", "zinc", "neutral", "stone"], "灰色系"),
        (["red", "orange", "amber", "yellow"], "暖色系"),
        (["lime", "green", "emerald", "teal"], "绿色系"),
        (["cyan", "sky", "blue", "indigo"], "青蓝色系"),
        (["violet", "purple", "fuchsia", "pink", "rose"], "紫色系"),
    ]

    # Material Design Colors 分组定义
    MATERIAL_GROUPS = [
        (["red", "pink", "purple", "deep_purple"], "红/粉/紫组"),
        (["indigo", "blue", "light_blue", "cyan"], "蓝/青组"),
        (["teal", "green", "light_green", "lime"], "绿色系"),
        (["yellow", "amber", "orange", "deep_orange"], "黄/橙组"),
        (["brown", "grey", "blue_grey"], "棕/灰组"),
    ]

    # ColorBrewer 分组定义
    COLORBREWER_GROUPS = [
        (["brewer_blues", "brewer_greens", "brewer_greys", "brewer_oranges", "brewer_purples", "brewer_reds"], "顺序色-单色系"),
        (["brewer_bugn", "brewer_bupu", "brewer_gnbu", "brewer_orrd", "brewer_pubu", "brewer_pubugn"], "顺序色-蓝绿紫"),
        (["brewer_purd", "brewer_rdpu", "brewer_ylgn", "brewer_ylgnbu", "brewer_ylorbr", "brewer_ylorrd"], "顺序色-暖色系"),
        (["brewer_brbg", "brewer_piyg", "brewer_prgn", "brewer_puor", "brewer_rdbu"], "发散色-对比"),
        (["brewer_rdgy", "brewer_rdylbu", "brewer_rdylgn", "brewer_spectral"], "发散色-光谱"),
        (["brewer_set1", "brewer_set2", "brewer_set3", "brewer_paired", "brewer_dark2", "brewer_accent"], "定性色-分类"),
        (["brewer_pastel1", "brewer_pastel2"], "定性色-粉彩"),
    ]

    # Radix Colors 分组定义
    RADIX_GROUPS = [
        (["radix_gray", "radix_mauve", "radix_slate", "radix_sage", "radix_olive", "radix_sand"], "中性色系"),
        (["radix_tomato", "radix_red", "radix_ruby", "radix_crimson"], "红色系"),
        (["radix_pink", "radix_plum", "radix_purple"], "粉紫色系"),
        (["radix_violet", "radix_iris", "radix_indigo"], "紫蓝色系"),
        (["radix_blue", "radix_cyan", "radix_sky"], "蓝色系"),
        (["radix_teal", "radix_jade", "radix_mint"], "青绿色系"),
        (["radix_green", "radix_grass"], "绿色系"),
        (["radix_brown", "radix_bronze", "radix_gold"], "金属色系"),
        (["radix_yellow", "radix_amber", "radix_orange"], "黄橙色系"),
        (["radix_lime"], "亮绿色系"),
    ]

    # Nord 分组定义
    NORD_GROUPS = [
        (["nord0", "nord1", "nord2", "nord3"], "分组1"),
        (["nord4", "nord5", "nord6", "nord7"], "分组2"),
        (["nord8", "nord9", "nord10", "nord11"], "分组3"),
        (["nord12", "nord13", "nord14", "nord15"], "分组4"),
    ]

    # Dracula 分组定义
    DRACULA_GROUPS = [
        (["dracula_bg", "dracula_current_line", "dracula_foreground", "dracula_comment"], "基础色系"),
        (["dracula_cyan", "dracula_green", "dracula_orange", "dracula_pink"], "主题色-1"),
        (["dracula_purple", "dracula_red", "dracula_yellow"], "主题色-2"),
    ]

    # Rose Pine 分组定义
    ROSE_PINE_GROUPS = [
        (["rose_pine_main", "rose_pine_moon", "rose_pine_dawn"], "全部系列"),
    ]

    # Solarized 分组定义
    SOLARIZED_GROUPS = [
        (["solarized_dark", "solarized_light"], "全部系列"),
    ]

    # Catppuccin 分组定义
    CATPPUCCIN_GROUPS = [
        (["catppuccin_latte", "catppuccin_frappe", "catppuccin_macchiato", "catppuccin_mocha"], "全部系列"),
    ]

    # Gruvbox 分组定义
    GRUVBOX_GROUPS = [
        (["gruvbox_dark", "gruvbox_light"], "全部系列"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('presetColorInterface')
        self._config_manager = get_config_manager()
        self._current_source = 'open_color'
        self._current_group_index = 0
        self.setup_ui()
        self._load_settings()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 头部信息
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = SubtitleLabel("内置色彩")
        header_layout.addWidget(self.title_label)

        # 添加说明标签
        self.desc_label = QLabel("基于 Open Color 开源配色方案")
        self.desc_label.setStyleSheet("font-size: 12px; color: gray;")
        header_layout.addWidget(self.desc_label)

        header_layout.addStretch()

        # 控件容器（用于对齐）
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setSpacing(10)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        # 数据源切换下拉列表
        self.source_combo = ComboBox(self)
        self.source_combo.addItem("Open Color 配色")
        self.source_combo.setItemData(0, "open_color")
        self.source_combo.addItem("Tailwind Colors 配色")
        self.source_combo.setItemData(1, "tailwind")
        self.source_combo.addItem("Material Design 配色")
        self.source_combo.setItemData(2, "material")
        self.source_combo.addItem("Nice Palettes 配色")
        self.source_combo.setItemData(3, "nice_palette")
        self.source_combo.addItem("ColorBrewer 配色")
        self.source_combo.setItemData(4, "colorbrewer")
        self.source_combo.addItem("Radix Colors 配色")
        self.source_combo.setItemData(5, "radix")
        self.source_combo.addItem("Nord 配色")
        self.source_combo.setItemData(6, "nord")
        self.source_combo.addItem("Dracula 配色")
        self.source_combo.setItemData(7, "dracula")
        self.source_combo.addItem("Rosé Pine 配色")
        self.source_combo.setItemData(8, "rose_pine")
        self.source_combo.addItem("Solarized 配色")
        self.source_combo.setItemData(9, "solarized")
        self.source_combo.addItem("Catppuccin 配色")
        self.source_combo.setItemData(10, "catppuccin")
        self.source_combo.addItem("Gruvbox 配色")
        self.source_combo.setItemData(11, "gruvbox")
        self.source_combo.setFixedWidth(180)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        controls_layout.addWidget(self.source_combo)

        # 分组下拉列表
        self.group_combo = ComboBox(self)
        self.group_combo.setFixedWidth(150)
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        controls_layout.addWidget(self.group_combo)

        header_layout.addWidget(controls_container)

        layout.addLayout(header_layout)

        # 预设色彩列表
        self.preset_color_list = PresetColorList(self)
        self.preset_color_list.favorite_requested.connect(self.favorite_requested)
        layout.addWidget(self.preset_color_list, stretch=1)

        # 初始化分组下拉列表
        self._setup_open_color_group_combo()

    def _setup_open_color_group_combo(self):
        """设置 Open Color 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.OPEN_COLOR_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_nice_palette_group_combo(self):
        """设置 Nice Palettes 分组下拉列表"""
        from core.color_data import get_nice_palette_count
        total_count = get_nice_palette_count()
        group_count = (total_count + self.PALETTES_PER_GROUP - 1) // self.PALETTES_PER_GROUP

        self.group_combo.clear()
        for i in range(group_count):
            start = i * self.PALETTES_PER_GROUP + 1
            end = min((i + 1) * self.PALETTES_PER_GROUP, total_count)
            self.group_combo.addItem(f"第 {start}-{end} 组")
            self.group_combo.setItemData(i, i)

    def _setup_tailwind_group_combo(self):
        """设置 Tailwind Colors 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.TAILWIND_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_material_group_combo(self):
        """设置 Material Design Colors 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.MATERIAL_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_colorbrewer_group_combo(self):
        """设置 ColorBrewer 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.COLORBREWER_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_radix_group_combo(self):
        """设置 Radix Colors 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.RADIX_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_nord_group_combo(self):
        """设置 Nord 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.NORD_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_dracula_group_combo(self):
        """设置 Dracula 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.DRACULA_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_rose_pine_group_combo(self):
        """设置 Rose Pine 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.ROSE_PINE_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_solarized_group_combo(self):
        """设置 Solarized 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.SOLARIZED_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_catppuccin_group_combo(self):
        """设置 Catppuccin 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.CATPPUCCIN_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _setup_gruvbox_group_combo(self):
        """设置 Gruvbox 分组下拉列表"""
        self.group_combo.clear()
        for i, (_, name) in enumerate(self.GRUVBOX_GROUPS):
            self.group_combo.addItem(name)
            self.group_combo.setItemData(i, i)

    def _on_source_changed(self, index):
        """数据源切换回调"""
        source = self.source_combo.currentData()
        self._current_source = source

        if source == 'open_color':
            self.desc_label.setText("基于 Open Color 开源配色方案")
            self._setup_open_color_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.OPEN_COLOR_GROUPS[0][0]
            self.preset_color_list.set_data_source('open_color', series_keys)
        elif source == 'nice_palette':
            self.desc_label.setText("基于 Nice Color Palettes 配色方案")
            self._setup_nice_palette_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            start_index = self._current_group_index * self.PALETTES_PER_GROUP
            self.preset_color_list.set_data_source('nice_palette', start_index)
        elif source == 'tailwind':
            self.desc_label.setText("基于 Tailwind CSS Colors 配色方案")
            self._setup_tailwind_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.TAILWIND_GROUPS[0][0]
            self.preset_color_list.set_data_source('tailwind', series_keys)
        elif source == 'material':
            self.desc_label.setText("基于 Google Material Design 配色方案")
            self._setup_material_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.MATERIAL_GROUPS[0][0]
            self.preset_color_list.set_data_source('material', series_keys)
        elif source == 'colorbrewer':
            self.desc_label.setText("基于 ColorBrewer 专业配色方案")
            self._setup_colorbrewer_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.COLORBREWER_GROUPS[0][0]
            self.preset_color_list.set_data_source('colorbrewer', series_keys)
        elif source == 'radix':
            self.desc_label.setText("基于 Radix UI Colors 配色方案")
            self._setup_radix_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.RADIX_GROUPS[0][0]
            self.preset_color_list.set_data_source('radix', series_keys)
        elif source == 'nord':
            self.desc_label.setText("基于 Nord 北极配色方案")
            self._setup_nord_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.NORD_GROUPS[0][0]
            self.preset_color_list.set_data_source('nord', series_keys)
        elif source == 'dracula':
            self.desc_label.setText("基于 Dracula 暗色配色方案")
            self._setup_dracula_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.DRACULA_GROUPS[0][0]
            self.preset_color_list.set_data_source('dracula', series_keys)
        elif source == 'rose_pine':
            self.desc_label.setText("基于 Rosé Pine 自然灵感配色方案")
            self._setup_rose_pine_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.ROSE_PINE_GROUPS[0][0]
            self.preset_color_list.set_data_source('rose_pine', series_keys)
        elif source == 'solarized':
            self.desc_label.setText("基于 Solarized 精准科学配色方案")
            self._setup_solarized_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.SOLARIZED_GROUPS[0][0]
            self.preset_color_list.set_data_source('solarized', series_keys)
        elif source == 'catppuccin':
            self.desc_label.setText("基于 Catppuccin 舒缓配色方案")
            self._setup_catppuccin_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.CATPPUCCIN_GROUPS[0][0]
            self.preset_color_list.set_data_source('catppuccin', series_keys)
        elif source == 'gruvbox':
            self.desc_label.setText("基于 Gruvbox 复古风格配色方案")
            self._setup_gruvbox_group_combo()
            self._current_group_index = 0
            self.group_combo.setCurrentIndex(0)
            series_keys = self.GRUVBOX_GROUPS[0][0]
            self.preset_color_list.set_data_source('gruvbox', series_keys)

    def _on_group_changed(self, index):
        """分组切换回调"""
        if index < 0:
            return

        self._current_group_index = index

        if self._current_source == 'open_color':
            if 0 <= index < len(self.OPEN_COLOR_GROUPS):
                series_keys = self.OPEN_COLOR_GROUPS[index][0]
                self.preset_color_list.set_data_source('open_color', series_keys)
        elif self._current_source == 'nice_palette':
            start_index = self._current_group_index * self.PALETTES_PER_GROUP
            self.preset_color_list.set_data_source('nice_palette', start_index)
        elif self._current_source == 'tailwind':
            if 0 <= index < len(self.TAILWIND_GROUPS):
                series_keys = self.TAILWIND_GROUPS[index][0]
                self.preset_color_list.set_data_source('tailwind', series_keys)
        elif self._current_source == 'material':
            if 0 <= index < len(self.MATERIAL_GROUPS):
                series_keys = self.MATERIAL_GROUPS[index][0]
                self.preset_color_list.set_data_source('material', series_keys)
        elif self._current_source == 'colorbrewer':
            if 0 <= index < len(self.COLORBREWER_GROUPS):
                series_keys = self.COLORBREWER_GROUPS[index][0]
                self.preset_color_list.set_data_source('colorbrewer', series_keys)
        elif self._current_source == 'radix':
            if 0 <= index < len(self.RADIX_GROUPS):
                series_keys = self.RADIX_GROUPS[index][0]
                self.preset_color_list.set_data_source('radix', series_keys)
        elif self._current_source == 'nord':
            if 0 <= index < len(self.NORD_GROUPS):
                series_keys = self.NORD_GROUPS[index][0]
                self.preset_color_list.set_data_source('nord', series_keys)
        elif self._current_source == 'dracula':
            if 0 <= index < len(self.DRACULA_GROUPS):
                series_keys = self.DRACULA_GROUPS[index][0]
                self.preset_color_list.set_data_source('dracula', series_keys)
        elif self._current_source == 'rose_pine':
            if 0 <= index < len(self.ROSE_PINE_GROUPS):
                series_keys = self.ROSE_PINE_GROUPS[index][0]
                self.preset_color_list.set_data_source('rose_pine', series_keys)
        elif self._current_source == 'solarized':
            if 0 <= index < len(self.SOLARIZED_GROUPS):
                series_keys = self.SOLARIZED_GROUPS[index][0]
                self.preset_color_list.set_data_source('solarized', series_keys)
        elif self._current_source == 'catppuccin':
            if 0 <= index < len(self.CATPPUCCIN_GROUPS):
                series_keys = self.CATPPUCCIN_GROUPS[index][0]
                self.preset_color_list.set_data_source('catppuccin', series_keys)
        elif self._current_source == 'gruvbox':
            if 0 <= index < len(self.GRUVBOX_GROUPS):
                series_keys = self.GRUVBOX_GROUPS[index][0]
                self.preset_color_list.set_data_source('gruvbox', series_keys)

    def _load_settings(self):
        """加载显示设置"""
        hex_visible = self._config_manager.get('settings.hex_visible', True)
        color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self.preset_color_list.update_display_settings(hex_visible, color_modes)

    def update_display_settings(self, hex_visible=None, color_modes=None):
        """更新显示设置

        Args:
            hex_visible: 是否显示16进制颜色值
            color_modes: 色彩模式列表
        """
        self.preset_color_list.update_display_settings(hex_visible, color_modes)

    def _update_styles(self):
        """更新样式以适配主题"""
        title_color = get_title_color()
        self.title_label.setStyleSheet(f"color: {title_color.name()};")

        if is_windows_10():
            bg_color = get_interface_background_color()
            self.setStyleSheet(f"""
                PresetColorInterface {{
                    background-color: {bg_color.name()};
                }}
            """)


# 导入需要在类定义之后导入的模块
from qfluentwidgets import Slider
from .preset_color_widgets import PresetColorList
