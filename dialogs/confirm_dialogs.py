# 第三方库导入
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import CheckBox, PrimaryPushButton, PushButton, RadioButton, qconfig
# 项目模块导入
from dialogs import BaseFramelessDialog
from utils import tr


class ConfirmDialog(BaseFramelessDialog):
    """通用确认对话框"""

    def __init__(self, title: str, content: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._content = content
        self.setWindowTitle(title)
        self.setFixedSize(400, 180)

        self._setup_title_bar()
        self._update_styles()
        self._setup_ui()

        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        # 样式准备好后允许显示
        self._enable_show()

    def _setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel(self._title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 内容
        content_label = QLabel(self._content)
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

        # 确认按钮（主按钮）
        confirm_button = PrimaryPushButton(tr('dialogs.confirm.confirm_btn'))
        confirm_button.setFixedWidth(80)
        confirm_button.clicked.connect(self.accept)
        button_layout.addWidget(confirm_button)

        layout.addLayout(button_layout)


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

        # 样式准备好后允许显示
        self._enable_show()

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

        # 样式准备好后允许显示
        self._enable_show()

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


class CloseConfirmDialog(BaseFramelessDialog):
    """关闭窗口时的询问框：最小化到托盘或直接退出"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._action: str | None = None
        self.setWindowTitle(tr('dialogs.close_confirm.title'))
        self.setMinimumWidth(400)

        self._setup_title_bar()
        self._update_styles()
        self._setup_ui()
        # 按内容计算高度，避免固定高度在不同语言换行时留下大块空白
        self.adjustSize()

        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        # 样式准备好后允许显示
        self._enable_show()

    @property
    def action(self) -> str | None:
        """用户选择的动作（tray / quit）；取消关闭时为 None"""
        return self._action

    @property
    def remember(self) -> bool:
        """是否勾选了“记住我的选择”"""
        return self._remember_checkbox.isChecked()

    def _setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 36, 20, 16)
        layout.setSpacing(12)

        # 标题
        title_label = QLabel(tr('dialogs.close_confirm.title'))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 内容
        content_label = QLabel(tr('dialogs.close_confirm.content'))
        content_label.setWordWrap(True)
        layout.addWidget(content_label)

        layout.addStretch()

        # 记住我的选择
        self._remember_checkbox = CheckBox(tr('dialogs.close_confirm.remember'))
        layout.addWidget(self._remember_checkbox)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 直接退出（次按钮）
        exit_button = PushButton(tr('dialogs.close_confirm.exit'))
        exit_button.setMinimumWidth(96)
        exit_button.clicked.connect(self._choose_quit)
        button_layout.addWidget(exit_button)

        # 最小化到托盘（主按钮）
        minimize_button = PrimaryPushButton(tr('dialogs.close_confirm.minimize'))
        minimize_button.setMinimumWidth(112)
        minimize_button.clicked.connect(self._choose_tray)
        button_layout.addWidget(minimize_button)

        layout.addLayout(button_layout)

    def _choose_tray(self):
        """选择最小化到托盘"""
        self._action = 'tray'
        self.accept()

    def _choose_quit(self):
        """选择直接退出"""
        self._action = 'quit'
        self.accept()
