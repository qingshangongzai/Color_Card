# 标准库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)
from qfluentwidgets import (
    ComboBox, FluentIcon, InfoBar, InfoBarPosition,
    PushButton, PushSettingCard, ScrollArea, SettingCardGroup, SubtitleLabel, SwitchButton, qconfig, isDarkTheme
)

# 项目模块导入
from core import get_config_manager

from dialogs import AboutDialog, UpdateAvailableDialog
from version import version_manager
from .theme_colors import get_title_color, get_text_color, get_interface_background_color, get_card_background_color, get_border_color
from utils.platform import is_windows_10


AVAILABLE_COLOR_MODES = ['HSB', 'LAB', 'HSL', 'CMYK', 'RGB']


class SettingsInterface(QWidget):
    """设置界面"""

    hex_display_changed = Signal(bool)
    color_modes_changed = Signal(list)
    color_sample_count_changed = Signal(int)
    luminance_sample_count_changed = Signal(int)
    histogram_scaling_mode_changed = Signal(str)
    color_wheel_mode_changed = Signal(str)
    histogram_mode_changed = Signal(str)
    saturation_threshold_changed = Signal(int)
    brightness_threshold_changed = Signal(int)
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
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.title_label = SubtitleLabel("设置")
        layout.addWidget(self.title_label)

        self.card_display_group = SettingCardGroup("色卡显示设置", self.content_widget)

        self.hex_display_card = self._create_switch_card(
            FluentIcon.PALETTE,
            "显示16进制颜色值",
            "在色彩提取面板的色卡中显示16进制颜色值和复制按钮",
            self._hex_visible
        )
        self.card_display_group.addSettingCard(self.hex_display_card)

        self.color_mode_card = self._create_color_mode_card()
        self.card_display_group.addSettingCard(self.color_mode_card)

        layout.addWidget(self.card_display_group)

        self.sampling_group = SettingCardGroup("采样设置", self.content_widget)

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

        self.histogram_group = SettingCardGroup("直方图设置", self.content_widget)

        self.histogram_scaling_card = self._create_histogram_scaling_card()
        self.histogram_group.addSettingCard(self.histogram_scaling_card)

        self.histogram_mode_card = self._create_histogram_mode_card()
        self.histogram_group.addSettingCard(self.histogram_mode_card)

        layout.addWidget(self.histogram_group)

        self.highlight_group = SettingCardGroup("区域高亮设置", self.content_widget)

        self.saturation_threshold_card = self._create_threshold_card(
            FluentIcon.BRIGHTNESS,
            "高饱和度阈值",
            "设置高饱和度区域的饱和度阈值",
            self._saturation_threshold,
            self._on_saturation_threshold_changed
        )
        self.highlight_group.addSettingCard(self.saturation_threshold_card)

        self.brightness_threshold_card = self._create_threshold_card(
            FluentIcon.VIEW,
            "高明度阈值",
            "设置高明度区域的明度阈值",
            self._brightness_threshold,
            self._on_brightness_threshold_changed
        )
        self.highlight_group.addSettingCard(self.brightness_threshold_card)

        layout.addWidget(self.highlight_group)

        self.color_wheel_group = SettingCardGroup("色环显示设置", self.content_widget)

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

        self.color_scheme_group = SettingCardGroup("配色生成方案", self.content_widget)

        self.color_wheel_mode_card = self._create_color_wheel_mode_card()
        self.color_scheme_group.addSettingCard(self.color_wheel_mode_card)

        layout.addWidget(self.color_scheme_group)

        self.help_group = SettingCardGroup("帮助", self.content_widget)

        self.update_card = PushSettingCard(
            "检查更新",
            FluentIcon.DOWNLOAD,
            "版本更新",
            "检查软件是否有新版本可用",
            self.help_group
        )
        self.update_card.clicked.connect(self.on_check_update)
        self.update_card.button.setFixedWidth(130)
        self.help_group.addSettingCard(self.update_card)

        self.about_card = PushSettingCard(
            "查看",
            FluentIcon.INFO,
            "关于 Color Card",
            "查看项目、文档等信息",
            self.help_group
        )
        self.about_card.clicked.connect(self.on_show_about)
        self.about_card.button.setFixedWidth(130)
        self.help_group.addSettingCard(self.about_card)

        layout.addWidget(self.help_group)

        layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll_area)

    def _create_switch_card(self, icon, title, content, initial_checked):
        """创建自定义开关卡片"""
        card = PushSettingCard("", icon, title, content, self.content_widget)
        card.button.setVisible(False)

        switch = SwitchButton(self.content_widget)
        switch.setChecked(initial_checked)
        switch.setOnText("开")
        switch.setOffText("关")
        switch.checkedChanged.connect(self._on_hex_display_changed)

        card.hBoxLayout.addWidget(switch, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        card.switch_button = switch

        return card

    def _create_spin_box_card(self, icon, title, content, initial_value, min_value, max_value, callback):
        """创建自定义下拉列表卡片"""
        card = PushSettingCard("", icon, title, content, self.content_widget)
        card.button.setVisible(False)

        combo_box = ComboBox(self.content_widget)
        for i in range(min_value, max_value + 1):
            combo_box.addItem(str(i))
        combo_box.setCurrentText(str(initial_value))
        combo_box.setFixedWidth(80)
        combo_box.currentTextChanged.connect(lambda text: callback(int(text)))

        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        card.combo_box = combo_box

        return card

    def _create_threshold_card(self, icon, title, content, initial_value, callback):
        """创建阈值选择卡片（粗略档位：60%, 70%, 80%）"""
        card = PushSettingCard("", icon, title, content, self.content_widget)
        card.button.setVisible(False)

        combo_box = ComboBox(self.content_widget)
        combo_box.addItem("60%")
        combo_box.addItem("70%")
        combo_box.addItem("80%")
        if initial_value == 60:
            combo_box.setCurrentIndex(0)
        elif initial_value == 80:
            combo_box.setCurrentIndex(2)
        else:
            combo_box.setCurrentIndex(1)
        combo_box.setFixedWidth(80)
        combo_box.currentTextChanged.connect(lambda text: callback(int(text.replace('%', ''))))

        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

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
        card.button.setVisible(False)

        combo_container = QWidget(self.content_widget)
        combo_layout = QHBoxLayout(combo_container)
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(10)

        self.mode_combo_1 = ComboBox(combo_container)
        self.mode_combo_1.addItems(AVAILABLE_COLOR_MODES)
        self.mode_combo_1.setCurrentText(self._color_modes[0])
        self.mode_combo_1.setFixedWidth(80)
        self.mode_combo_1.currentTextChanged.connect(self._on_color_mode_changed)

        separator = QLabel("+", combo_container)
        separator.setStyleSheet("color: gray;")

        self.mode_combo_2 = ComboBox(combo_container)
        self.mode_combo_2.addItems(AVAILABLE_COLOR_MODES)
        self.mode_combo_2.setCurrentText(self._color_modes[1])
        self.mode_combo_2.setFixedWidth(80)
        self.mode_combo_2.currentTextChanged.connect(self._on_color_mode_changed)

        combo_layout.addWidget(self.mode_combo_1)
        combo_layout.addWidget(separator)
        combo_layout.addWidget(self.mode_combo_2)

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

        if mode1 == mode2:
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

        combo_box = ComboBox(self.content_widget)
        combo_box.addItem("线性缩放")
        combo_box.setItemData(0, "linear")
        combo_box.addItem("自适应缩放")
        combo_box.setItemData(1, "adaptive")

        for i in range(combo_box.count()):
            if combo_box.itemData(i) == self._histogram_scaling_mode:
                combo_box.setCurrentIndex(i)
                break

        combo_box.setFixedWidth(120)
        combo_box.currentIndexChanged.connect(self._on_histogram_scaling_mode_changed)

        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

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

        combo_box = ComboBox(self.content_widget)
        combo_box.addItem("RGB 通道")
        combo_box.setItemData(0, "rgb")
        combo_box.addItem("色相分布")
        combo_box.setItemData(1, "hue")

        for i in range(combo_box.count()):
            if combo_box.itemData(i) == self._histogram_mode:
                combo_box.setCurrentIndex(i)
                break

        combo_box.setFixedWidth(120)
        combo_box.currentIndexChanged.connect(self._on_histogram_mode_changed)

        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

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

        combo_box = ComboBox(self.content_widget)
        combo_box.addItem("RGB 光学")
        combo_box.setItemData(0, "RGB")
        combo_box.addItem("RYB 美术")
        combo_box.setItemData(1, "RYB")

        for i in range(combo_box.count()):
            if combo_box.itemData(i) == self._color_wheel_mode:
                combo_box.setCurrentIndex(i)
                break

        combo_box.setFixedWidth(120)
        combo_box.currentIndexChanged.connect(self._on_color_wheel_mode_changed)

        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

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
