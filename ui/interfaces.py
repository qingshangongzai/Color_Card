# 标准库导入
# 无

# 第三方库导入
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QScrollArea, QSplitter,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget
)
from qfluentwidgets import (
    ComboBox, FluentIcon, InfoBar, InfoBarPosition, PrimaryPushButton,
    PushSettingCard, SettingCardGroup, SpinBox, SwitchButton, isDarkTheme
)

# 项目模块导入
from core import get_color_info, get_config_manager
from dialogs import AboutDialog, UpdateAvailableDialog
from version import version_manager
from .canvases import ImageCanvas, LuminanceCanvas
from .cards import ColorCardPanel
from .color_wheel import HSBColorWheel
from .histograms import LuminanceHistogramWidget, RGBHistogramWidget


# 可选的色彩模式列表
AVAILABLE_COLOR_MODES = ['HSB', 'LAB', 'HSL', 'CMYK', 'RGB']


def get_title_color():
    """获取标题颜色"""
    if isDarkTheme():
        return QColor(255, 255, 255)
    else:
        return QColor(40, 40, 40)


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

        self.histogram_widget = LuminanceHistogramWidget()
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('settings')
        self._config_manager = get_config_manager()
        self._hex_visible = self._config_manager.get('settings.hex_visible', True)
        self._color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self._color_sample_count = self._config_manager.get('settings.color_sample_count', 5)
        self._luminance_sample_count = self._config_manager.get('settings.luminance_sample_count', 5)
        self.setup_ui()

    def setup_ui(self):
        """设置界面布局"""
        # 创建滚动区域
        self.scroll_area = QScrollArea(self)
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
        title_label = QLabel("设置")
        title_color = get_title_color()
        title_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {title_color.name()};")
        layout.addWidget(title_label)

        # 显示设置分组
        self.display_group = SettingCardGroup("显示设置", self.content_widget)

        # 16进制颜色值显示开关卡片
        self.hex_display_card = self._create_switch_card(
            FluentIcon.PALETTE,
            "显示16进制颜色值",
            "在色彩提取面板的色卡中显示16进制颜色值和复制按钮",
            self._hex_visible
        )
        self.display_group.addSettingCard(self.hex_display_card)

        # 色彩模式选择卡片
        self.color_mode_card = self._create_color_mode_card()
        self.display_group.addSettingCard(self.color_mode_card)

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
        self.display_group.addSettingCard(self.color_sample_count_card)

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
        self.display_group.addSettingCard(self.luminance_sample_count_card)

        layout.addWidget(self.display_group)

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
        card = PushSettingCard("", icon, title, content, self.display_group)
        card.button.setVisible(False)  # 隐藏默认按钮

        # 创建开关按钮
        switch = SwitchButton(self.content_widget)
        switch.setChecked(initial_checked)
        switch.checkedChanged.connect(self._on_hex_display_changed)

        # 将开关添加到卡片布局
        card.hBoxLayout.addWidget(switch, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        # 保存开关引用
        card.switch_button = switch

        return card

    def _create_spin_box_card(self, icon, title, content, initial_value, min_value, max_value, callback):
        """创建自定义下拉列表卡片"""
        card = PushSettingCard("", icon, title, content, self.display_group)
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
            self.display_group
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

    def on_check_update(self):
        """检查更新按钮点击"""
        current_version = version_manager.get_version()
        UpdateAvailableDialog.check_update(self, current_version)

    def on_show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()
