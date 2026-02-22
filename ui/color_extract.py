"""色彩提取界面模块

包含色彩提取界面的主要实现，包括图片显示、颜色提取、主色调自动提取、
高饱和度/高明度区域显示等功能。
"""

# 标准库导入
import uuid
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QSplitter, QStackedWidget,
    QSizePolicy, QVBoxLayout, QWidget
)
from qfluentwidgets import (
    FluentIcon, InfoBar, InfoBarPosition, PrimaryPushButton,
    PushButton
)

# 项目模块导入
from core import get_color_info, get_config_manager, ServiceFactory
from utils import tr, get_locale_manager
from dialogs import EditPaletteDialog
from .canvases import ImageCanvas
from .cards import ColorCardPanel
from .color_wheel import HSBColorWheel
from .histograms import RGBHistogramWidget, HueHistogramWidget


class ColorExtractInterface(QWidget):
    """色彩提取界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_manager = get_config_manager()
        self._color_service = None
        self.setup_ui()
        self.setup_connections()
        get_locale_manager().language_changed.connect(self._on_language_changed)

    def _get_color_service(self):
        """延迟获取颜色服务
        
        Returns:
            ColorService: 颜色服务实例
        """
        if self._color_service is None:
            self._color_service = ServiceFactory.get_color_service(self)
            self._setup_color_service_connections()
        return self._color_service

    def _setup_color_service_connections(self):
        """设置颜色服务信号连接"""
        self._color_service.extraction_finished.connect(self._on_extraction_finished)
        self._color_service.extraction_error.connect(self._on_extraction_error)
        self._color_service.extraction_started.connect(self._on_extraction_started)

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

        # RGB直方图（按钮已内置在组件内部）
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

        self.favorite_button = PrimaryPushButton(FluentIcon.HEART, tr('color_extract.favorite'), self)
        self.favorite_button.setFixedHeight(32)
        self.favorite_button.clicked.connect(self._on_favorite_clicked)
        favorite_toolbar_layout.addWidget(self.favorite_button)

        # 主色调提取按钮
        self.extract_dominant_button = PushButton(FluentIcon.PALETTE, tr('color_extract.extract_dominant'), self)
        self.extract_dominant_button.setFixedHeight(32)
        self.extract_dominant_button.clicked.connect(self._on_extract_dominant_clicked)
        favorite_toolbar_layout.addWidget(self.extract_dominant_button)

        # 高饱和度区域显示按钮
        self.high_saturation_button = PushButton(FluentIcon.BRIGHTNESS, tr('color_extract.show_high_saturation'), self)
        self.high_saturation_button.setFixedHeight(32)
        self.high_saturation_button.pressed.connect(self._on_high_saturation_pressed)
        self.high_saturation_button.released.connect(self._on_high_saturation_released)
        favorite_toolbar_layout.addWidget(self.high_saturation_button)

        # 高明度区域显示按钮
        self.high_brightness_button = PushButton(FluentIcon.VIEW, tr('color_extract.show_high_brightness'), self)
        self.high_brightness_button.setFixedHeight(32)
        self.high_brightness_button.pressed.connect(self._on_high_brightness_pressed)
        self.high_brightness_button.released.connect(self._on_high_brightness_released)
        favorite_toolbar_layout.addWidget(self.high_brightness_button)

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
            tr('color_extract.select_image'),
            "",
            tr('color_extract.image_filter')
        )

        if file_path:
            self.image_canvas.set_image(file_path)

    def on_image_loaded(self, file_path):
        """图片加载完成回调"""
        pass

    def on_image_data_loaded(self, pixmap, image):
        """图片数据加载完成回调（用于同步到其他面板）"""
        window = self.window()
        if window and hasattr(window, '_image_mediator'):
            window._image_mediator.set_image(pixmap, image, 'color')

        # 更新RGB直方图和色相直方图
        self.rgb_histogram_widget.set_image(image)
        self.hue_histogram_widget.set_image(image)

    def on_color_picked(self, index, rgb):
        """颜色提取回调"""
        color_info = get_color_info(*rgb)
        self.color_card_panel.update_color(index, color_info)
        # 更新HSB色环上的采样点
        self.hsb_color_wheel.update_sample_point(index, rgb)

    def clear_all(self, emit_signal: bool = True):
        """清空所有相关内容（图片、色卡、色环、直方图）

        Args:
            emit_signal: 是否发射清空信号（默认True，从其他面板同步时设为False）
        """
        # 取消颜色提取任务
        self._get_color_service().cancel_extraction()

        self.image_canvas.clear_image(emit_signal)
        self.color_card_panel.clear_all()
        # 清除HSB色环和直方图
        self.hsb_color_wheel.clear_sample_points()
        self.rgb_histogram_widget.clear()
        self.hue_histogram_widget.clear()

    def clear_image(self):
        """清空图片（供外部调用，会发射信号同步到其他面板）"""
        self.clear_all(emit_signal=True)

    def on_image_cleared(self):
        """图片已清空回调（同步清除明度面板）"""
        window = self.window()
        if window and hasattr(window, '_image_mediator'):
            window._image_mediator.clear_image('color')

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
                title=tr('messages.favorite_failed.title'),
                content=tr('messages.favorite_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 弹出编辑配色对话框
        default_name = f"{tr('messages.palette')} {len(self._config_manager.get_favorites()) + 1}"

        # 构造配色数据
        palette_data = {
            "name": default_name,
            "colors": colors
        }

        dialog = EditPaletteDialog(
            default_name=default_name,
            palette_data=palette_data,
            parent=self.window()
        )

        if dialog.exec() != EditPaletteDialog.DialogCode.Accepted:
            return

        new_palette_data = dialog.get_palette_data()
        if not new_palette_data:
            return

        favorite_data = {
            "id": str(uuid.uuid4()),
            "name": new_palette_data['name'],
            "colors": new_palette_data['colors'],
            "created_at": datetime.now().isoformat(),
            "source": "color_extract"
        }

        self._config_manager.add_favorite(favorite_data)
        self._config_manager.save()

        # 刷新配色管理面板
        window = self.window()
        if window and hasattr(window, 'refresh_palette_management'):
            window.refresh_palette_management()

        InfoBar.success(
            title=tr('messages.favorite_success.title'),
            content=tr('messages.favorite_success.content').format(name=favorite_data['name']),
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
                title=tr('messages.extract_failed.title'),
                content=tr('messages.extract_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 获取当前设置的采样点数量
        count = self._config_manager.get('settings.color_sample_count', 5)

        # 使用颜色服务开始提取
        self._get_color_service().extract_dominant_colors(image, count=count)

    def _on_extraction_started(self):
        """提取开始回调"""
        InfoBar.info(
            title=tr('messages.extracting.title'),
            content=tr('messages.extracting.content'),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

        self.extract_dominant_button.setEnabled(False)
        self.extract_dominant_button.setText(tr('color_extract.extracting'))

    def _reset_extract_button(self):
        """恢复提取按钮状态"""
        self.extract_dominant_button.setEnabled(True)
        self.extract_dominant_button.setText(tr('color_extract.extract_dominant'))

    def _on_extraction_finished(self, dominant_colors, positions):
        """主色调提取完成回调

        Args:
            dominant_colors: 主色调列表 [(r, g, b), ...]
            positions: 颜色位置列表 [(rel_x, rel_y), ...]
        """
        self._reset_extract_button()

        count = self._config_manager.get('settings.color_sample_count', 5)

        # 更新取色点位置
        self.image_canvas.set_picker_positions_by_colors(dominant_colors, positions)

        # 更新HSB色环上的采样点
        for i, rgb in enumerate(dominant_colors):
            if i < count:
                self.hsb_color_wheel.update_sample_point(i, rgb)

        InfoBar.success(
            title=tr('messages.extract_success.title'),
            content=tr('messages.extract_success.content').format(count=len(dominant_colors)),
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
        self._reset_extract_button()

        InfoBar.error(
            title=tr('messages.extract_error.title'),
            content=tr('messages.extract_error.content').format(error=error_message),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self.window()
        )

    def _on_high_saturation_pressed(self):
        """高饱和度区域按钮按下回调"""
        image = self.image_canvas.get_image()
        if not image or image.isNull():
            InfoBar.warning(
                title=tr('messages.display_failed.title'),
                content=tr('messages.display_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        self.image_canvas.toggle_high_saturation_highlight(True)

    def _on_high_saturation_released(self):
        """高饱和度区域按钮释放回调"""
        self.image_canvas.toggle_high_saturation_highlight(False)

    def _on_high_brightness_pressed(self):
        """高明度区域按钮按下回调"""
        image = self.image_canvas.get_image()
        if not image or image.isNull():
            InfoBar.warning(
                title=tr('messages.display_failed.title'),
                content=tr('messages.display_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        self.image_canvas.toggle_high_brightness_highlight(True)

    def _on_high_brightness_released(self):
        """高明度区域按钮释放回调"""
        self.image_canvas.toggle_high_brightness_highlight(False)

    def set_saturation_threshold(self, value: int):
        """设置饱和度阈值

        Args:
            value: 阈值百分比 (0-100)
        """
        self.image_canvas.set_saturation_threshold(value)

    def set_brightness_threshold(self, value: int):
        """设置明度阈值

        Args:
            value: 阈值百分比 (0-100)
        """
        self.image_canvas.set_brightness_threshold(value)

    def update_texts(self):
        """更新所有界面文本"""
        self.favorite_button.setText(tr('color_extract.favorite'))
        self.extract_dominant_button.setText(tr('color_extract.extract_dominant'))
        self.high_saturation_button.setText(tr('color_extract.show_high_saturation'))
        self.high_brightness_button.setText(tr('color_extract.show_high_brightness'))

    def _on_language_changed(self):
        """语言切换回调"""
        self.update_texts()
