from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from qfluentwidgets import (
    SettingCardGroup, PushSettingCard,
    FluentIcon, PrimaryPushButton, InfoBar, InfoBarPosition,
    isDarkTheme, SwitchButton, ComboBox
)

from .about_dialog import AboutDialog
from config_manager import get_config_manager


# 可选的色彩模式列表
AVAILABLE_COLOR_MODES = ['HSB', 'LAB', 'HSL', 'CMYK', 'RGB']


def get_title_color():
    """获取标题颜色"""
    if isDarkTheme():
        return QColor(255, 255, 255)
    else:
        return QColor(40, 40, 40)


class SettingsInterface(QWidget):
    """设置界面"""

    # 信号：16进制显示开关状态改变
    hex_display_changed = Signal(bool)
    # 信号：色彩模式改变
    color_modes_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('settings')
        self._config_manager = get_config_manager()
        self._hex_visible = self._config_manager.get('settings.hex_visible', True)
        self._color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self.setup_ui()

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 标题
        title_label = QLabel("设置")
        title_color = get_title_color()
        title_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {title_color.name()};")
        layout.addWidget(title_label)

        # 显示设置分组
        self.display_group = SettingCardGroup("显示设置", self)

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

        layout.addWidget(self.display_group)

        # 帮助分组
        self.help_group = SettingCardGroup("帮助", self)

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

    def _create_switch_card(self, icon, title, content, initial_checked):
        """创建自定义开关卡片"""
        card = PushSettingCard("", icon, title, content, self.display_group)
        card.button.setVisible(False)  # 隐藏默认按钮

        # 创建开关按钮
        switch = SwitchButton(self)
        switch.setChecked(initial_checked)
        switch.checkedChanged.connect(self._on_hex_display_changed)

        # 将开关添加到卡片布局
        card.hBoxLayout.addWidget(switch, 0, Qt.AlignmentFlag.AlignRight)
        card.hBoxLayout.addSpacing(16)

        # 保存开关引用
        card.switch_button = switch

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
        combo_container = QWidget(card)
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
        InfoBar.info(
            title="提示",
            content="当前已是最新版本",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def on_show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()
