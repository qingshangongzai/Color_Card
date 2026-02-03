from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from qfluentwidgets import (
    SettingCardGroup, PushSettingCard,
    FluentIcon, PrimaryPushButton, InfoBar, InfoBarPosition,
    isDarkTheme
)

from .about_dialog import AboutDialog


def get_title_color():
    """获取标题颜色"""
    if isDarkTheme():
        return QColor(255, 255, 255)
    else:
        return QColor(40, 40, 40)


class SettingsInterface(QWidget):
    """设置界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('settings')
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
