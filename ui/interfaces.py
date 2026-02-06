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
from .color_wheel import HSBColorWheel, InteractiveColorWheel
from .histograms import LuminanceHistogramWidget, RGBHistogramWidget
from .scheme_widgets import SchemeColorPanel


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
        main_splitter.setMinimumHeight(400)
        layout.addWidget(main_splitter, stretch=1)

        # 上半部分：水平分割器（图片 + 右侧组件）
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setMinimumHeight(250)

        # 左侧：图片画布
        self.image_canvas = ImageCanvas()
        self.image_canvas.setMinimumWidth(300)
        top_splitter.addWidget(self.image_canvas)

        # 右侧：垂直分割器（HSB色环 + RGB直方图）
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setMinimumWidth(180)
        right_splitter.setMaximumWidth(350)

        # HSB色环
        self.hsb_color_wheel = HSBColorWheel()
        self.hsb_color_wheel.setMinimumHeight(150)
        right_splitter.addWidget(self.hsb_color_wheel)

        # RGB直方图
        self.rgb_histogram_widget = RGBHistogramWidget()
        self.rgb_histogram_widget.setMinimumHeight(100)
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
        splitter.setMinimumHeight(300)
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
    # 信号：直方图缩放模式改变
    histogram_scaling_mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('settings')
        self._config_manager = get_config_manager()
        self._hex_visible = self._config_manager.get('settings.hex_visible', True)
        self._color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self._color_sample_count = self._config_manager.get('settings.color_sample_count', 5)
        self._luminance_sample_count = self._config_manager.get('settings.luminance_sample_count', 5)
        self._histogram_scaling_mode = self._config_manager.get('settings.histogram_scaling_mode', 'linear')
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

        # 直方图缩放模式卡片
        self.histogram_scaling_card = self._create_histogram_scaling_card()
        self.display_group.addSettingCard(self.histogram_scaling_card)

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

    def _create_histogram_scaling_card(self):
        """创建直方图缩放模式选择卡片"""
        card = PushSettingCard(
            "",
            FluentIcon.DOCUMENT,
            "直方图缩放模式",
            "选择直方图的缩放方式（线性/自适应）",
            self.display_group
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


class ColorSchemeInterface(QWidget):
    """配色方案界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('colorSchemeInterface')
        self._current_scheme = 'monochromatic'
        self._base_hue = 0.0
        self._base_saturation = 100.0
        self._base_brightness = 100.0
        self._brightness_adjustment = 0

        # 获取配置管理器
        from core import get_config_manager
        self._config_manager = get_config_manager()

        self.setup_ui()
        self.setup_connections()
        self._load_settings()
        # 根据初始配色方案设置卡片数量
        self._update_card_count()
        self._generate_scheme_colors()

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
        scheme_label = QLabel("配色方案:")
        top_layout.addWidget(scheme_label)

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
        self.wheel_container.setStyleSheet("background-color: #2a2a2a; border-radius: 8px;")

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

        brightness_label = QLabel("明度调整:")
        brightness_layout.addWidget(brightness_label)

        self.brightness_slider = Slider(Qt.Orientation.Horizontal, brightness_container)
        self.brightness_slider.setRange(-50, 50)
        self.brightness_slider.setValue(0)
        self.brightness_slider.setFixedWidth(200)
        brightness_layout.addWidget(self.brightness_slider)

        self.brightness_value_label = QLabel("0")
        self.brightness_value_label.setFixedWidth(25)
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
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)

    def _load_settings(self):
        """加载显示设置"""
        # 从配置管理器读取设置
        hex_visible = self._config_manager.get('settings.hex_visible', True)
        color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])

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

    def on_brightness_changed(self, value):
        """明度调整回调"""
        self._brightness_adjustment = value
        self.brightness_value_label.setText(str(value))
        # 更新色轮的全局明度
        self.color_wheel.set_global_brightness(value)
        self._generate_scheme_colors()

    def _generate_scheme_colors(self):
        """生成配色方案颜色"""
        from core import get_scheme_preview_colors, adjust_brightness, hsb_to_rgb, rgb_to_hsb

        # 根据配色方案类型确定颜色数量
        scheme_counts = {
            'monochromatic': 4,      # 同色系：4个
            'analogous': 4,          # 邻近色：4个
            'complementary': 5,      # 互补色：5个
            'split_complementary': 3, # 分离补色：3个
            'double_complementary': 4  # 双补色：4个
        }
        count = scheme_counts.get(self._current_scheme, 5)

        # 生成基础配色
        colors = get_scheme_preview_colors(self._current_scheme, self._base_hue, count)

        # 转换为HSB并应用明度调整
        hsb_colors = []
        for rgb in colors:
            h, s, b = rgb_to_hsb(*rgb)
            hsb_colors.append((h, s, b))

        if self._brightness_adjustment != 0:
            hsb_colors = adjust_brightness(hsb_colors, self._brightness_adjustment)
            colors = [hsb_to_rgb(h, s, b) for h, s, b in hsb_colors]

        # 更新色块面板
        self.color_panel.set_colors(colors)

        # 更新色环上的配色方案点
        self.color_wheel.set_scheme_colors(hsb_colors)


# 导入需要在类定义之后导入的模块
from qfluentwidgets import Slider
