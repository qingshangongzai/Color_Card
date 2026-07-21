# 第三方库导入
from PySide6.QtWidgets import QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QColor
from qfluentwidgets import PrimaryPushButton, PushButton
# 项目模块导入
from installer.wizard.base_page import BasePage
from utils.icon import get_icon_path
from version import version_manager


class WelcomePage(BasePage):
    """欢迎页面

    显示应用Logo、欢迎信息和开始安装按钮。
    """

    def setup_ui(self):
        """设置页面UI"""
        layout = self._content_layout
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Logo
        logo_label = QLabel()
        icon_path = get_icon_path()
        if icon_path:
            icon = QIcon(icon_path)
            pixmap = icon.pixmap(icon.actualSize(QSize(96, 96)))
            if not pixmap.isNull():
                logo_label.setPixmap(pixmap)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        # 欢迎标题
        title_label = QLabel("欢迎安装 取色卡")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)

        # 版本号
        version_label = QLabel(f"Color Card v{version_manager.version}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(version_label)

        # 描述文字
        desc_label = QLabel("一站式配色工具和图片色彩分析工具")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(desc_label)

        # 添加弹性空间
        layout.addStretch(1)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch(1)

        self._start_button = PrimaryPushButton("开始安装")
        self._start_button.setFixedSize(100, 32)
        self._start_button.clicked.connect(self.next_requested.emit)
        button_layout.addWidget(self._start_button)

        self._exit_button = PushButton("退出")
        self._exit_button.setFixedSize(100, 32)
        self._exit_button.clicked.connect(self.close_requested.emit)
        button_layout.addWidget(self._exit_button)

        button_layout.addStretch(1)
        layout.addLayout(button_layout)

    def _update_styles(self):
        super()._update_styles()

        text_color = QColor(40, 40, 40)
        secondary_color = QColor(120, 120, 120)

        for child in self._content_widget.findChildren(QLabel):
            if "欢迎安装" in child.text():
                child.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {text_color.name()};")
            elif "Color Card v" in child.text():
                child.setStyleSheet(f"font-size: 14px; color: {text_color.name()};")
            elif "一站式" in child.text():
                child.setStyleSheet(f"font-size: 12px; color: {secondary_color.name()};")
