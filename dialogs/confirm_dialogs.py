# 第三方库导入
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import PrimaryPushButton, PushButton, RadioButton, qconfig

# 项目模块导入
from dialogs import BaseFramelessDialog
from utils import tr


class ImportModeDialog(BaseFramelessDialog):
    """导入模式选择对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('dialogs.confirm.import_mode_title'))
        self.setFixedSize(400, 220)

        self._setup_title_bar()
        self._update_styles()
        self._setup_ui()

        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

    def _setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel(tr('dialogs.confirm.import_mode_title'))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 内容提示
        content_label = QLabel(tr('dialogs.confirm.import_mode_hint'))
        content_label.setWordWrap(True)
        layout.addWidget(content_label)

        # 选项区域
        self._append_radio = RadioButton(tr('dialogs.confirm.append_option'))
        self._append_radio.setChecked(True)
        layout.addWidget(self._append_radio)

        replace_radio = RadioButton(tr('dialogs.confirm.replace_option'))
        layout.addWidget(replace_radio)

        layout.addStretch()

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 取消按钮（次按钮）
        cancel_button = PushButton(tr('dialogs.confirm.cancel_btn'))
        cancel_button.setFixedWidth(80)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # 确认按钮（主按钮）
        confirm_button = PrimaryPushButton(tr('dialogs.confirm.confirm_btn'))
        confirm_button.setFixedWidth(80)
        confirm_button.clicked.connect(self.accept)
        button_layout.addWidget(confirm_button)

        layout.addLayout(button_layout)

    def is_append_mode(self):
        """是否选择追加模式"""
        return self._append_radio.isChecked()


class DeleteConfirmDialog(BaseFramelessDialog):
    """删除确认对话框"""

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self._name = name
        self.setWindowTitle(tr('dialogs.confirm.delete_title'))
        self.setFixedSize(400, 180)

        self._setup_title_bar()
        self._update_styles()
        self._setup_ui()

        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

    def _setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel(tr('dialogs.confirm.delete_title'))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 内容
        content_text = tr('dialogs.confirm.delete_content').format(name=self._name)
        content_label = QLabel(content_text)
        content_label.setWordWrap(True)
        layout.addWidget(content_label)

        layout.addStretch()

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 取消按钮（次按钮）
        cancel_button = PushButton(tr('dialogs.confirm.cancel_btn'))
        cancel_button.setFixedWidth(80)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # 删除按钮（主按钮）
        delete_button = PrimaryPushButton(tr('dialogs.confirm.delete_btn'))
        delete_button.setFixedWidth(80)
        delete_button.clicked.connect(self.accept)
        button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)
