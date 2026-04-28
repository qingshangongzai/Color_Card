"""色彩分析界面模块

包含色彩分析界面的主要实现，包括图片显示、颜色提取、主色调自动提取、
高饱和度/高明度区域显示等功能。
"""

# 标准库导入
import uuid
from datetime import datetime
from pathlib import Path

# 第三方库导入
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QSplitter, QStackedWidget,
    QSizePolicy, QVBoxLayout, QWidget
)
from qfluentwidgets import (
    FluentIcon, InfoBar, InfoBarPosition, PrimaryPushButton,
    PushButton
)

# 项目模块导入
from core import get_color_info, get_config_manager, get_color_service, log_user_action
from utils import tr, get_locale_manager, get_default_image_directory, get_last_directory, set_last_directory
from dialogs import EditPaletteDialog
from .canvases import ImageCanvas
from .cards import ColorCardPanel
from .color_wheel import HSBColorWheel
from .histograms import RGBHistogramWidget, HueHistogramWidget


class ColorAnalysisInterface(QWidget):
    """色彩分析界面"""

    # 图片同步信号（替代中介者）
    image_sync_requested = Signal(object)  # ImageData
    clear_sync_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_manager = get_config_manager()
        self._color_service = None
        self._setup_basic_ui()
        self._setup_delayed_ui()
        get_locale_manager().language_changed.connect(self._on_language_changed)

    def _apply_splitter_style(self, splitter):
        """应用分割器样式（隐藏 Mac 上的分割线）"""
        splitter.setStyleSheet("""
            QSplitter { border: none; background: transparent; }
            QSplitter::handle { background: transparent; border: none; }
        """)

    def _get_color_service(self):
        """延迟获取颜色服务（保留延迟加载）

        Returns:
            ColorService: 颜色服务实例
        """
        if self._color_service is None:
            self._color_service = get_color_service()
            self._setup_color_service_connections()
        return self._color_service

    def _setup_color_service_connections(self):
        """设置颜色服务信号连接（使用 QueuedConnection 确保线程安全）"""
        self._color_service.extraction_finished.connect(
            self._on_extraction_finished,
            Qt.ConnectionType.QueuedConnection
        )
        self._color_service.extraction_error.connect(
            self._on_extraction_error,
            Qt.ConnectionType.QueuedConnection
        )
        self._color_service.extraction_started.connect(
            self._on_extraction_started,
            Qt.ConnectionType.QueuedConnection
        )

    def closeEvent(self, event):
        """关闭时断开信号连接"""
        if self._color_service:
            try:
                self._color_service.extraction_finished.disconnect(self._on_extraction_finished)
                self._color_service.extraction_error.disconnect(self._on_extraction_error)
                self._color_service.extraction_started.disconnect(self._on_extraction_started)
            except (TypeError, RuntimeError):
                pass
        super().closeEvent(event)

    def _setup_basic_ui(self):
        """设置基本界面（快速）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 主分割器（垂直）
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setMinimumHeight(300)
        self.main_splitter.setHandleWidth(0)
        self._apply_splitter_style(self.main_splitter)
        layout.addWidget(self.main_splitter, stretch=1)

        # 上半部分：水平分割器（图片 + 右侧组件）
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setMinimumHeight(180)
        self.top_splitter.setHandleWidth(0)
        self._apply_splitter_style(self.top_splitter)
        self.main_splitter.addWidget(self.top_splitter)

        # 右侧：垂直分割器（HSB色环 + 直方图堆叠窗口）
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setMinimumWidth(180)
        self.right_splitter.setMaximumWidth(350)
        self.right_splitter.setMinimumHeight(150)
        self.right_splitter.setHandleWidth(0)
        self._apply_splitter_style(self.right_splitter)
        self.top_splitter.addWidget(self.right_splitter)

        # 设置左右比例（图片区域:右侧组件区域）
        self.top_splitter.setSizes([550, 280])

        # 收藏工具栏
        favorite_toolbar = QWidget()
        favorite_toolbar.setMaximumHeight(50)
        favorite_toolbar.setStyleSheet("background: transparent;")
        favorite_toolbar_layout = QHBoxLayout(favorite_toolbar)
        favorite_toolbar_layout.setContentsMargins(0, 8, 0, 8)
        favorite_toolbar_layout.setSpacing(10)

        self.favorite_button = PrimaryPushButton(FluentIcon.HEART, tr('color_analysis.favorite'), self)
        self.favorite_button.setFixedHeight(32)
        self.favorite_button.clicked.connect(self._on_favorite_clicked)
        favorite_toolbar_layout.addWidget(self.favorite_button)

        # 主色调提取按钮
        self.extract_dominant_button = PushButton(FluentIcon.PALETTE, tr('color_analysis.extract_dominant'), self)
        self.extract_dominant_button.setFixedHeight(32)
        self.extract_dominant_button.clicked.connect(self._on_extract_dominant_clicked)
        favorite_toolbar_layout.addWidget(self.extract_dominant_button)

        # 高饱和度区域显示按钮
        self.high_saturation_button = PushButton(FluentIcon.VIEW, tr('color_analysis.show_high_saturation'), self)
        self.high_saturation_button.setFixedHeight(32)
        self.high_saturation_button.pressed.connect(self._on_high_saturation_pressed)
        self.high_saturation_button.released.connect(self._on_high_saturation_released)
        favorite_toolbar_layout.addWidget(self.high_saturation_button)

        # 高明度区域显示按钮
        self.high_brightness_button = PushButton(FluentIcon.BRIGHTNESS, tr('color_analysis.show_high_brightness'), self)
        self.high_brightness_button.setFixedHeight(32)
        self.high_brightness_button.pressed.connect(self._on_high_brightness_pressed)
        self.high_brightness_button.released.connect(self._on_high_brightness_released)
        favorite_toolbar_layout.addWidget(self.high_brightness_button)

        favorite_toolbar_layout.addStretch()

        self.main_splitter.addWidget(favorite_toolbar)

        # 下半部分：色卡面板
        self.color_card_panel = ColorCardPanel()
        self.color_card_panel.setMinimumHeight(130)
        self.main_splitter.addWidget(self.color_card_panel)

        self.main_splitter.setSizes([350, 36, 180])

    def _setup_delayed_ui(self):
        """延迟初始化（复杂组件）"""
        # 左侧：图片画布
        self.image_canvas = ImageCanvas()
        self.image_canvas.setMinimumWidth(300)
        self.image_canvas.setMinimumHeight(150)
        self.top_splitter.insertWidget(0, self.image_canvas)

        # HSB色环
        self.hsb_color_wheel = HSBColorWheel()
        self.hsb_color_wheel.setMinimumHeight(100)
        self.hsb_color_wheel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.right_splitter.addWidget(self.hsb_color_wheel)

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

        self.right_splitter.addWidget(self.histogram_stack)
        self.right_splitter.setSizes([200, 100])

        # 设置信号连接
        self._setup_connections()

    def _setup_connections(self):
        """设置信号连接"""
        self.image_canvas.color_picked.connect(self.on_color_picked)
        self.image_canvas.image_loaded.connect(self.on_image_loaded)
        self.image_canvas.open_image_requested.connect(self.open_image)
        self.image_canvas.change_image_requested.connect(self.open_image)
        self.image_canvas.clear_image_requested.connect(self.clear_image)
        self.image_canvas.image_cleared.connect(self.on_image_cleared)

    def open_image(self):
        """打开图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr('color_analysis.select_image'),
            get_last_directory("image_import", get_default_image_directory()),
            tr('color_analysis.image_filter')
        )

        if file_path:
            log_user_action(
                action="open_image",
                params={"path": file_path, "source": "color_analysis"},
                result="success"
            )
            set_last_directory("image_import", str(Path(file_path).parent))
            self.image_canvas.set_image(file_path)

    def on_image_loaded(self, image_path):
        """图片加载完成回调"""
        # 图片数据处理已在 _setup_after_load 中完成
        image_data = self.image_canvas._image_data
        if image_data is not None:
            # 直接发射同步信号
            self.image_sync_requested.emit(image_data)

            # 更新RGB直方图和色相直方图
            self.rgb_histogram_widget.set_image(image_data.display_image)
            self.hue_histogram_widget.set_image(image_data.display_image)

    def on_color_picked(self, index, rgb):
        """颜色提取回调"""
        colorspace_info = self.image_canvas.get_colorspace_info()
        colorspace_name = colorspace_info.name if colorspace_info else 'sRGB'
        color_info = get_color_info(*rgb, colorspace_name=colorspace_name)
        self.color_card_panel.update_color(index, color_info)
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
        log_user_action(action="clear_image", params={"source": "color_analysis"})
        self.clear_all(emit_signal=True)

    def on_image_cleared(self):
        """图片已清空回调"""
        # 直接发射同步信号
        self.clear_sync_requested.emit()

    def set_image_data(self, image_data):
        """设置图片数据（从其他面板同步）

        Args:
            image_data: ImageData 对象
        """
        # emit_sync=False 防止循环同步
        self.image_canvas.set_image_data(image_data, emit_sync=False)
        self.rgb_histogram_widget.set_image(image_data.display_image)
        self.hue_histogram_widget.set_image(image_data.display_image)

        # 延迟更新HSB色环采样点，等待颜色提取完成
        # extract_all 使用 100ms 延迟，这里使用 300ms 确保颜色已提取
        QTimer.singleShot(300, self._update_hsb_wheel_samples)

    def _update_hsb_wheel_samples(self):
        """更新HSB色环采样点"""
        # 从色卡面板获取当前颜色并更新色环
        for i, card in enumerate(self.color_card_panel.cards):
            if card._current_color_info:
                rgb = card._current_color_info.get('rgb')
                if rgb:
                    self.hsb_color_wheel.update_sample_point(i, rgb)

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
            QTimer.singleShot(0, lambda: InfoBar.warning(
                title=tr('messages.favorite_failed.title'),
                content=tr('messages.favorite_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            ))
            return

        # 复制颜色数据，避免引用问题
        colors = [color.copy() for color in colors]

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
            "source": "color_analysis"
        }

        self._config_manager.add_favorite(favorite_data)
        self._config_manager.save()

        log_user_action(
            action="save_favorite",
            params={
                "name": favorite_data['name'],
                "color_count": len(colors),
                "source": "color_analysis"
            }
        )

        window = self.window()
        if window and hasattr(window, 'refresh_palette_management'):
            window.refresh_palette_management()

        QTimer.singleShot(0, lambda: InfoBar.success(
            title=tr('messages.favorite_success.title'),
            content=tr('messages.favorite_success.content').format(name=favorite_data['name']),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        ))

    def _on_extract_dominant_clicked(self):
        """主色调提取按钮点击回调"""
        image = self.image_canvas.get_image()
        if not image or image.isNull():
            QTimer.singleShot(0, lambda: InfoBar.warning(
                title=tr('messages.extract_failed.title'),
                content=tr('messages.extract_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            ))
            return

        count = self._config_manager.get('settings.color_sample_count', 5)
        log_user_action(
            action="extract_dominant",
            params={"count": count, "source": "color_analysis"}
        )

        original_pixels = self.image_canvas.get_original_pixels()
        self._get_color_service().extract_dominant_colors(
            image, count=count, original_pixels=original_pixels
        )

    def _on_extraction_started(self):
        """提取开始回调"""
        QTimer.singleShot(0, lambda: InfoBar.info(
            title=tr('messages.extracting.title'),
            content=tr('messages.extracting.content'),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        ))

        self.extract_dominant_button.setEnabled(False)
        self.extract_dominant_button.setText(tr('color_analysis.extracting'))

    def _reset_extract_button(self):
        """恢复提取按钮状态"""
        self.extract_dominant_button.setEnabled(True)
        self.extract_dominant_button.setText(tr('color_analysis.extract_dominant'))

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

        QTimer.singleShot(0, lambda: InfoBar.success(
            title=tr('messages.extract_success.title'),
            content=tr('messages.extract_success.content').format(count=len(dominant_colors)),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        ))

    def _on_extraction_error(self, error_message):
        """主色调提取失败回调

        Args:
            error_message: 错误信息
        """
        self._reset_extract_button()

        QTimer.singleShot(0, lambda: InfoBar.error(
            title=tr('messages.extract_error.title'),
            content=tr('messages.extract_error.content').format(error=error_message),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self.window()
        ))

    def _on_high_saturation_pressed(self):
        """高饱和度区域按钮按下回调"""
        image = self.image_canvas.get_image()
        if not image or image.isNull():
            QTimer.singleShot(0, lambda: InfoBar.warning(
                title=tr('messages.display_failed.title'),
                content=tr('messages.display_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            ))
            return

        self.image_canvas.toggle_high_saturation_highlight(True)

    def _on_high_saturation_released(self):
        """高饱和度区域按钮释放回调"""
        self.image_canvas.toggle_high_saturation_highlight(False)

    def _on_high_brightness_pressed(self):
        """高明度区域按钮按下回调"""
        image = self.image_canvas.get_image()
        if not image or image.isNull():
            QTimer.singleShot(0, lambda: InfoBar.warning(
                title=tr('messages.display_failed.title'),
                content=tr('messages.display_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            ))
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
        self.favorite_button.setText(tr('color_analysis.favorite'))
        self.extract_dominant_button.setText(tr('color_analysis.extract_dominant'))
        self.high_saturation_button.setText(tr('color_analysis.show_high_saturation'))
        self.high_brightness_button.setText(tr('color_analysis.show_high_brightness'))

    def _on_language_changed(self):
        """语言切换回调"""
        self.update_texts()
