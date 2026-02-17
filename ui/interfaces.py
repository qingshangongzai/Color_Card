# 标准库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)
from qfluentwidgets import (
    ComboBox, FluentIcon, InfoBar, InfoBarPosition,
    PushButton, PushSettingCard, ScrollArea, SettingCardGroup, SpinBox, SubtitleLabel, SwitchButton, qconfig, isDarkTheme
)

# 项目模块导入
from core import get_config_manager

from dialogs import AboutDialog, UpdateAvailableDialog
from version import version_manager
from .preview_widgets import PreviewToolbar, MixedPreviewPanel
from .theme_colors import get_title_color, get_text_color, get_interface_background_color, get_card_background_color, get_border_color
from utils.platform import is_windows_10


# 可选的色彩模式列表
AVAILABLE_COLOR_MODES = ['HSB', 'LAB', 'HSL', 'CMYK', 'RGB']


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
    # 信号：饱和度阈值改变
    saturation_threshold_changed = Signal(int)
    # 信号：明度阈值改变
    brightness_threshold_changed = Signal(int)
    # 信号：色环标签显示开关状态改变
    color_wheel_labels_visible_changed = Signal(bool)

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
        self._saturation_threshold = self._config_manager.get('settings.saturation_threshold', 70)
        self._brightness_threshold = self._config_manager.get('settings.brightness_threshold', 70)
        self._color_wheel_labels_visible = self._config_manager.get('settings.color_wheel_labels_visible', True)
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

        # 区域高亮设置分组
        self.highlight_group = SettingCardGroup("区域高亮设置", self.content_widget)

        # 高饱和度阈值卡片
        self.saturation_threshold_card = self._create_threshold_card(
            FluentIcon.BRIGHTNESS,
            "高饱和度阈值",
            "设置高饱和度区域的饱和度阈值",
            self._saturation_threshold,
            self._on_saturation_threshold_changed
        )
        self.highlight_group.addSettingCard(self.saturation_threshold_card)

        # 高明度阈值卡片
        self.brightness_threshold_card = self._create_threshold_card(
            FluentIcon.VIEW,
            "高明度阈值",
            "设置高明度区域的明度阈值",
            self._brightness_threshold,
            self._on_brightness_threshold_changed
        )
        self.highlight_group.addSettingCard(self.brightness_threshold_card)

        layout.addWidget(self.highlight_group)

        # 色环显示设置分组
        self.color_wheel_group = SettingCardGroup("色环显示设置", self.content_widget)

        # 色环标签显示开关卡片
        self.color_wheel_labels_card = self._create_switch_card(
            FluentIcon.PALETTE,
            "显示色环标签",
            "在色环周围显示色相名称标签",
            self._color_wheel_labels_visible
        )
        self.color_wheel_labels_card.switch_button.checkedChanged.connect(
            self._on_color_wheel_labels_visible_changed
        )
        self.color_wheel_group.addSettingCard(self.color_wheel_labels_card)

        layout.addWidget(self.color_wheel_group)

        # 配色生成方案设置分组
        self.color_scheme_group = SettingCardGroup("配色生成方案", self.content_widget)

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

    def _create_threshold_card(self, icon, title, content, initial_value, callback):
        """创建阈值选择卡片（粗略档位：60%, 70%, 80%）"""
        card = PushSettingCard("", icon, title, content, self.content_widget)
        card.button.setVisible(False)

        # 创建ComboBox控件
        combo_box = ComboBox(self.content_widget)
        # 添加粗略档位选项
        combo_box.addItem("60%")
        combo_box.addItem("70%")
        combo_box.addItem("80%")
        # 设置默认值
        if initial_value == 60:
            combo_box.setCurrentIndex(0)
        elif initial_value == 80:
            combo_box.setCurrentIndex(2)
        else:
            combo_box.setCurrentIndex(1)  # 默认70%
        combo_box.setFixedWidth(80)
        combo_box.currentTextChanged.connect(lambda text: callback(int(text.replace('%', ''))))

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

    def _on_saturation_threshold_changed(self, value):
        """饱和度阈值改变"""
        self._saturation_threshold = value
        self._config_manager.set('settings.saturation_threshold', value)
        self._config_manager.save()
        self.saturation_threshold_changed.emit(value)

    def _on_brightness_threshold_changed(self, value):
        """明度阈值改变"""
        self._brightness_threshold = value
        self._config_manager.set('settings.brightness_threshold', value)
        self._config_manager.save()
        self.brightness_threshold_changed.emit(value)

    def _on_color_wheel_labels_visible_changed(self, checked):
        """色环标签显示开关状态改变"""
        self._color_wheel_labels_visible = checked
        self._config_manager.set('settings.color_wheel_labels_visible', checked)
        self._config_manager.save()
        self.color_wheel_labels_visible_changed.emit(checked)

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


class ColorPreviewInterface(QWidget):
    """配色预览界面 - 预览收藏的配色在不同场景下的效果"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('colorPreviewInterface')
        self._config_manager = get_config_manager()
        self._favorites = []
        self._current_index = 0
        self._current_colors: list[str] = []
        self._current_scene = "mobile_ui"  # 默认使用UI场景（有内置SVG模板）
        self._current_svg_path = ""  # 当前加载的 SVG 文件路径
        self._hex_visible = self._config_manager.get('settings.hex_visible', True)
        self.setup_ui()
        self._load_favorites()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部工具栏（包含标题、导入导出按钮、场景选择器、颜色圆点栏）
        self.toolbar = PreviewToolbar(self)
        self.toolbar.scene_changed.connect(self._on_scene_changed)
        self.toolbar.get_dot_bar().order_changed.connect(self._on_color_order_changed)
        self.toolbar.get_dot_bar().color_deleted.connect(self._on_color_deleted)
        self.toolbar.import_svg_requested.connect(self._on_import_svg)
        self.toolbar.export_svg_requested.connect(self._on_export_svg)
        self.toolbar.import_config_requested.connect(self._on_import_config)
        self.toolbar.export_config_requested.connect(self._on_export_config)
        self.toolbar.set_hex_visible(self._hex_visible)
        layout.addWidget(self.toolbar)

        # 预览区域
        self.preview_panel = MixedPreviewPanel(self)
        # 默认显示UI场景（有内置SVG模板）
        self.preview_panel.set_scene("mobile_ui")
        layout.addWidget(self.preview_panel, stretch=1)

    def _load_favorites(self):
        """加载收藏的配色列表（仅用于显示可用收藏，不自动加载任何配色）"""
        self._favorites = self._config_manager.get_favorites()
        # 默认不加载任何配色，提示用户从配色管理面板导入
        self._current_colors = []
        self._update_preview()

    def _load_current_scheme(self):
        """加载当前配色"""
        if not self._favorites or self._current_index >= len(self._favorites):
            return

        favorite = self._favorites[self._current_index]
        colors_data = favorite.get('colors', [])

        # 提取颜色值
        self._current_colors = []
        for color_info in colors_data:
            hex_value = color_info.get('hex', '')
            if hex_value:
                if not hex_value.startswith('#'):
                    hex_value = '#' + hex_value
                self._current_colors.append(hex_value)

        if not self._current_colors:
            self._current_colors = ["#E8E8E8"]

        self._update_preview()

    def _update_preview(self):
        """更新预览显示"""
        self.toolbar.set_colors(self._current_colors)
        self.preview_panel.set_colors(self._current_colors)

    def set_colors(self, colors: list[str]):
        """设置要预览的配色（由外部调用）

        Args:
            colors: 颜色值列表（HEX格式）
        """
        self._current_colors = colors.copy() if colors else []
        self._update_preview()

    def _on_scene_changed(self, scene: str):
        """场景切换回调"""
        self._current_scene = scene
        self.preview_panel.set_scene(scene)

    def _on_color_order_changed(self, colors: list[str]):
        """颜色顺序变化回调"""
        self._current_colors = colors
        self.preview_panel.set_colors(colors)

    def _on_color_deleted(self, colors: list[str]):
        """颜色删除回调"""
        self._current_colors = colors
        self.preview_panel.set_colors(colors)

    def set_hex_visible(self, visible: bool):
        """设置HEX值显示开关

        Args:
            visible: 是否显示HEX值
        """
        self._hex_visible = visible
        self.toolbar.set_hex_visible(visible)

    def _on_import_svg(self):
        """导入 SVG 文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入 SVG 文件",
            "",
            "SVG 文件 (*.svg);;所有文件 (*)"
        )

        if not file_path:
            return

        # 加载 SVG 文件
        svg_preview = self.preview_panel.get_svg_preview()
        if svg_preview is None:
            InfoBar.warning(
                title="无法导入",
                content="当前场景不支持直接导入 SVG，请切换到自定义场景",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )
            return

        if svg_preview.load_svg(file_path):
            self._current_svg_path = file_path
            # 保存路径到预览面板，切换场景后可以恢复
            self.preview_panel.set_custom_svg_path(file_path)
            # 应用当前配色
            svg_preview.set_colors(self._current_colors)

            InfoBar.success(
                title="导入成功",
                content=f"已加载 SVG 文件",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
        else:
            InfoBar.error(
                title="导入失败",
                content="无法加载 SVG 文件",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )

    def _on_export_svg(self):
        """导出 SVG 文件"""
        svg_preview = self.preview_panel.get_svg_preview()

        if svg_preview is None:
            InfoBar.warning(
                title="无法导出",
                content="当前场景不支持导出 SVG",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        if not svg_preview.has_svg():
            InfoBar.warning(
                title="无法导出",
                content="请先导入 SVG 文件",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 SVG 文件",
            "colored_preview.svg",
            "SVG 文件 (*.svg);;所有文件 (*)"
        )

        if not file_path:
            return

        # 确保文件扩展名为 .svg
        if not file_path.endswith('.svg'):
            file_path += '.svg'

        try:
            # 获取应用配色后的 SVG 内容
            svg_content = svg_preview.get_svg_content()

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            InfoBar.success(
                title="导出成功",
                content=f"已保存到: {file_path}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )
        except Exception as e:
            InfoBar.error(
                title="导出失败",
                content=f"保存文件时发生错误: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self.window()
            )

    def _on_import_config(self):
        """导入用户SVG模板到当前场景类型"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入 SVG 模板",
            "",
            "SVG 文件 (*.svg);;所有文件 (*)"
        )

        if not file_path:
            return

        from datetime import datetime
        from pathlib import Path

        # 添加到用户模板索引
        template_data = {
            "path": file_path,
            "name": Path(file_path).stem,
            "added_at": datetime.now().strftime("%Y-%m-%d")
        }

        success = self._config_manager.add_scene_template(self._current_scene, template_data)
        self._config_manager.save()

        if success:
            # 重新加载当前场景
            self.preview_panel.set_scene(self._current_scene)
            self.preview_panel.set_colors(self._current_colors)

            InfoBar.success(
                title="导入成功",
                content=f"已添加模板到 {self._current_scene} 场景",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )
        else:
            InfoBar.warning(
                title="导入失败",
                content="该模板已存在",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )

    def _on_export_config(self):
        """导出当前配色下的SVG"""
        from datetime import datetime
        
        svg_preview = self.preview_panel.get_svg_preview()

        if not svg_preview or not svg_preview.has_svg():
            InfoBar.warning(
                title="无法导出",
                content="当前没有可导出的SVG",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 生成默认文件名（与配色数据导出格式保持一致）
        default_name = f"color_card_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 SVG",
            default_name,
            "SVG 文件 (*.svg);;所有文件 (*)"
        )

        if not file_path:
            return

        # 确保文件扩展名为 .svg
        if not file_path.endswith('.svg'):
            file_path += '.svg'

        try:
            svg_content = svg_preview.get_svg_content()

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            InfoBar.success(
                title="导出成功",
                content=f"已保存到: {file_path}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )
        except Exception as e:
            InfoBar.error(
                title="导出失败",
                content=f"保存文件时发生错误: {str(e)}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self.window()
            )

    def refresh_favorites(self):
        """刷新收藏列表（由主窗口调用）"""
        self._load_favorites()

    def _update_styles(self):
        """更新样式以适配主题"""
        pass
