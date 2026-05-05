# 标准库导入
import sys
from pathlib import Path

# 第三方库导入
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from qfluentwidgets import PrimaryPushButton, PushButton, qconfig, setThemeColor

# 项目模块导入
from dialogs import BaseFramelessDialog
from utils.icon import load_icon_universal
from utils.platform import fix_windows_taskbar_icon_for_window

# 获取应用信息
try:
    from version import version_manager
    APP_NAME = version_manager.app_info['name']
except ImportError:
    APP_NAME = "取色卡"


class ElevationDialog(BaseFramelessDialog):
    """提权确认对话框"""

    def __init__(self, parent=None):
        """初始化对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("需要管理员权限")
        self.setFixedSize(400, 180)

        setThemeColor('#0078d4')

        self.setWindowIcon(load_icon_universal())

        self._setup_title_bar()
        self._update_styles()
        self.setup_ui()

        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        self._enable_show()
        fix_windows_taskbar_icon_for_window(self)

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)

        # 标题
        self.title_label = QLabel("需要管理员权限")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 描述
        self.desc_label = QLabel(
            "该操作需要管理员权限。\n"
            "点击「确定」后，Windows 将请求您的确认。"
        )
        self.desc_label.setStyleSheet("font-size: 13px;")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.desc_label)

        layout.addStretch()

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_button = PrimaryPushButton("确定")
        self.ok_button.setFixedWidth(80)
        self.ok_button.clicked.connect(self._on_ok)
        button_layout.addWidget(self.ok_button)

        button_layout.addSpacing(12)

        self.cancel_button = PushButton("取消")
        self.cancel_button.setFixedWidth(80)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def set_message(self, message: str):
        """设置描述信息

        Args:
            message: 描述信息
        """
        self.desc_label.setText(message)

    def _on_ok(self):
        """确定按钮点击"""
        self.accept()
