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
from utils import tr, get_supported_languages, set_language, get_locale_manager

from dialogs import AboutDialog, UpdateAvailableDialog
from version import version_manager
from .theme_colors import get_title_color, get_text_color, get_interface_background_color, get_card_background_color, get_border_color
from utils.platform import is_windows_10


AVAILABLE_COLOR_MODES = ['HSB', 'LAB', 'HSL', 'CMYK', 'RGB']


class SettingsInterface(QWidget):
    """设置界面"""

    language_changed = Signal(str)
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
        self._language = self._config_manager.get('settings.language', 'ZW_JT')
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)
        get_locale_manager().language_changed.connect(self._on_language_changed)

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

        self.title_label = SubtitleLabel(tr('settings.title'))
        layout.addWidget(self.title_label)

        # 语言设置分组
        self.language_group = SettingCardGroup(tr('settings.language'), self.content_widget)

        self.language_card = self._create_language_card()
        self.language_group.addSettingCard(self.language_card)

        layout.addWidget(self.language_group)

        self.card_display_group = SettingCardGroup(tr('settings.card_display'), self.content_widget)

        self.hex_display_card = self._create_switch_card(
            FluentIcon.PALETTE,
            tr('settings.hex_display'),
            tr('settings.hex_display_desc'),
            self._hex_visible
        )
        self.card_display_group.addSettingCard(self.hex_display_card)

        self.color_mode_card = self._create_color_mode_card()
        self.card_display_group.addSettingCard(self.color_mode_card)

        layout.addWidget(self.card_display_group)

        self.sampling_group = SettingCardGroup(tr('settings.sampling'), self.content_widget)

        self.color_sample_count_card = self._create_spin_box_card(
            FluentIcon.PALETTE,
            tr('settings.color_sample_count'),
            tr('settings.color_sample_count_desc'),
            self._color_sample_count,
            2,
            6,
            self._on_color_sample_count_changed
        )
        self.sampling_group.addSettingCard(self.color_sample_count_card)

        self.luminance_sample_count_card = self._create_spin_box_card(
            FluentIcon.BRIGHTNESS,
            tr('settings.luminance_sample_count'),
            tr('settings.luminance_sample_count_desc'),
            self._luminance_sample_count,
            2,
            6,
            self._on_luminance_sample_count_changed
        )
        self.sampling_group.addSettingCard(self.luminance_sample_count_card)

        layout.addWidget(self.sampling_group)

        self.histogram_group = SettingCardGroup(tr('settings.histogram'), self.content_widget)

        self.histogram_scaling_card = self._create_histogram_scaling_card()
        self.histogram_group.addSettingCard(self.histogram_scaling_card)

        self.histogram_mode_card = self._create_histogram_mode_card()
        self.histogram_group.addSettingCard(self.histogram_mode_card)

        layout.addWidget(self.histogram_group)

        self.highlight_group = SettingCardGroup(tr('settings.highlight'), self.content_widget)

        self.saturation_threshold_card = self._create_threshold_card(
            FluentIcon.BRIGHTNESS,
            tr('settings.saturation_threshold'),
            tr('settings.saturation_threshold_desc'),
            self._saturation_threshold,
            self._on_saturation_threshold_changed
        )
        self.highlight_group.addSettingCard(self.saturation_threshold_card)

        self.brightness_threshold_card = self._create_threshold_card(
            FluentIcon.VIEW,
            tr('settings.brightness_threshold'),
            tr('settings.brightness_threshold_desc'),
            self._brightness_threshold,
            self._on_brightness_threshold_changed
        )
        self.highlight_group.addSettingCard(self.brightness_threshold_card)

        layout.addWidget(self.highlight_group)

        self.color_wheel_group = SettingCardGroup(tr('settings.color_wheel'), self.content_widget)

        self.color_wheel_labels_card = self._create_switch_card(
            FluentIcon.PALETTE,
            tr('settings.color_wheel_labels'),
            tr('settings.color_wheel_labels_desc'),
            self._color_wheel_labels_visible
        )
        self.color_wheel_labels_card.switch_button.checkedChanged.connect(
            self._on_color_wheel_labels_visible_changed
        )
        self.color_wheel_group.addSettingCard(self.color_wheel_labels_card)

        layout.addWidget(self.color_wheel_group)

        self.color_scheme_group = SettingCardGroup(tr('settings.color_scheme'), self.content_widget)

        self.color_wheel_mode_card = self._create_color_wheel_mode_card()
        self.color_scheme_group.addSettingCard(self.color_wheel_mode_card)

        layout.addWidget(self.color_scheme_group)

        self.help_group = SettingCardGroup(tr('settings.help'), self.content_widget)

        self.update_card = PushSettingCard(
            tr('settings.check_update'),
            FluentIcon.DOWNLOAD,
            tr('settings.version_update'),
            tr('settings.version_update_desc'),
            self.help_group
        )
        self.update_card.clicked.connect(self.on_check_update)
        self.update_card.button.setFixedWidth(130)
        self.help_group.addSettingCard(self.update_card)

        self.about_card = PushSettingCard(
            tr('settings.about'),
            FluentIcon.INFO,
            tr('settings.about_title'),
            tr('settings.about_desc'),
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

    def _create_language_card(self):
        """创建语言选择卡片"""
        card = PushSettingCard(
            "",
            FluentIcon.LANGUAGE,
            tr('settings.language_title'),
            tr('settings.language_desc'),
            self.content_widget
        )
        card.button.setVisible(False)

        combo_box = ComboBox(self.content_widget)
        supported_languages = get_supported_languages()
        for code, name in supported_languages.items():
            combo_box.addItem(name)
            combo_box.setItemData(combo_box.count() - 1, code)
        
        # 设置当前语言
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == self._language:
                combo_box.setCurrentIndex(i)
                break
        
        combo_box.setFixedWidth(120)
        combo_box.currentIndexChanged.connect(self._on_language_combo_changed)

        card.hBoxLayout.addWidget(combo_box, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        card.combo_box = combo_box

        return card

    def _on_language_combo_changed(self, index):
        """语言选择下拉框切换回调"""
        combo_box = self.language_card.combo_box
        language_code = combo_box.itemData(index)
        self._language = language_code
        self._config_manager.set('settings.language', language_code)
        self._config_manager.save()
        
        # 切换语言
        set_language(language_code)
        
        self.language_changed.emit(language_code)

    def _on_language_changed(self, language_code):
        """语言切换回调（来自LocaleManager）"""
        self._update_texts()

    def _update_texts(self):
        """更新所有界面文本"""
        # 更新标题
        self.title_label.setText(tr('settings.title'))

        # 更新分组标题
        self.language_group.titleLabel.setText(tr('settings.language'))
        self.card_display_group.titleLabel.setText(tr('settings.card_display'))
        self.sampling_group.titleLabel.setText(tr('settings.sampling'))
        self.histogram_group.titleLabel.setText(tr('settings.histogram'))
        self.highlight_group.titleLabel.setText(tr('settings.highlight'))
        self.color_wheel_group.titleLabel.setText(tr('settings.color_wheel'))
        self.color_scheme_group.titleLabel.setText(tr('settings.color_scheme'))
        self.help_group.titleLabel.setText(tr('settings.help'))

        # 更新语言卡片
        self.language_card.titleLabel.setText(tr('settings.language_title'))
        self.language_card.contentLabel.setText(tr('settings.language_desc'))

        # 更新16进制显示卡片
        self.hex_display_card.titleLabel.setText(tr('settings.hex_display'))
        self.hex_display_card.contentLabel.setText(tr('settings.hex_display_desc'))
        self.hex_display_card.switch_button.setOnText(tr('settings.switch_on'))
        self.hex_display_card.switch_button.setOffText(tr('settings.switch_off'))

        # 更新色彩模式卡片
        self.color_mode_card.titleLabel.setText(tr('settings.color_mode'))
        self.color_mode_card.contentLabel.setText(tr('settings.color_mode_desc'))

        # 更新采样卡片
        self.color_sample_count_card.titleLabel.setText(tr('settings.color_sample_count'))
        self.color_sample_count_card.contentLabel.setText(tr('settings.color_sample_count_desc'))
        self.luminance_sample_count_card.titleLabel.setText(tr('settings.luminance_sample_count'))
        self.luminance_sample_count_card.contentLabel.setText(tr('settings.luminance_sample_count_desc'))

        # 更新直方图卡片
        self.histogram_scaling_card.titleLabel.setText(tr('settings.histogram_scaling'))
        self.histogram_scaling_card.contentLabel.setText(tr('settings.histogram_scaling_desc'))
        self.histogram_scaling_card.combo_box.setItemText(0, tr('settings.linear_scaling'))
        self.histogram_scaling_card.combo_box.setItemText(1, tr('settings.adaptive_scaling'))

        self.histogram_mode_card.titleLabel.setText(tr('settings.histogram_mode'))
        self.histogram_mode_card.contentLabel.setText(tr('settings.histogram_mode_desc'))
        self.histogram_mode_card.combo_box.setItemText(0, tr('settings.rgb_channel'))
        self.histogram_mode_card.combo_box.setItemText(1, tr('settings.hue_distribution'))

        # 更新高亮卡片
        self.saturation_threshold_card.titleLabel.setText(tr('settings.saturation_threshold'))
        self.saturation_threshold_card.contentLabel.setText(tr('settings.saturation_threshold_desc'))
        self.brightness_threshold_card.titleLabel.setText(tr('settings.brightness_threshold'))
        self.brightness_threshold_card.contentLabel.setText(tr('settings.brightness_threshold_desc'))

        # 更新色环卡片
        self.color_wheel_labels_card.titleLabel.setText(tr('settings.color_wheel_labels'))
        self.color_wheel_labels_card.contentLabel.setText(tr('settings.color_wheel_labels_desc'))
        self.color_wheel_labels_card.switch_button.setOnText(tr('settings.switch_on'))
        self.color_wheel_labels_card.switch_button.setOffText(tr('settings.switch_off'))

        # 更新配色方案卡片
        self.color_wheel_mode_card.titleLabel.setText(tr('settings.color_scheme_mode'))
        self.color_wheel_mode_card.contentLabel.setText(tr('settings.color_scheme_mode_desc'))
        self.color_wheel_mode_card.combo_box.setItemText(0, tr('settings.rgb_optical'))
        self.color_wheel_mode_card.combo_box.setItemText(1, tr('settings.ryb_artistic'))

        # 更新帮助卡片
        self.update_card.titleLabel.setText(tr('settings.version_update'))
        self.update_card.contentLabel.setText(tr('settings.version_update_desc'))
        self.update_card.button.setText(tr('settings.check_update'))

        self.about_card.titleLabel.setText(tr('settings.about_title'))
        self.about_card.contentLabel.setText(tr('settings.about_desc'))
        self.about_card.button.setText(tr('settings.about'))

    def _create_switch_card(self, icon, title, content, initial_checked):
        """创建自定义开关卡片"""
        card = PushSettingCard("", icon, title, content, self.content_widget)
        card.button.setVisible(False)

        switch = SwitchButton(self.content_widget)
        switch.setChecked(initial_checked)
        switch.setOnText(tr('settings.switch_on'))
        switch.setOffText(tr('settings.switch_off'))
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
            tr('settings.color_mode'),
            tr('settings.color_mode_desc'),
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
            tr('settings.histogram_scaling'),
            tr('settings.histogram_scaling_desc'),
            self.content_widget
        )
        card.button.setVisible(False)

        combo_box = ComboBox(self.content_widget)
        combo_box.addItem(tr('settings.linear_scaling'))
        combo_box.setItemData(0, "linear")
        combo_box.addItem(tr('settings.adaptive_scaling'))
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
            tr('settings.histogram_mode'),
            tr('settings.histogram_mode_desc'),
            self.content_widget
        )
        card.button.setVisible(False)

        combo_box = ComboBox(self.content_widget)
        combo_box.addItem(tr('settings.rgb_channel'))
        combo_box.setItemData(0, "rgb")
        combo_box.addItem(tr('settings.hue_distribution'))
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
            tr('settings.color_scheme_mode'),
            tr('settings.color_scheme_mode_desc'),
            self.content_widget
        )
        card.button.setVisible(False)

        combo_box = ComboBox(self.content_widget)
        combo_box.addItem(tr('settings.rgb_optical'))
        combo_box.setItemData(0, "RGB")
        combo_box.addItem(tr('settings.ryb_artistic'))
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
