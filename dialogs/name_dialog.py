# 标准库导入

# 第三方库导入
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import LineEdit, PrimaryPushButton, PushButton, isDarkTheme, qconfig

# 项目模块导入
from ui.theme_colors import get_dialog_bg_color, get_text_color
from utils import fix_windows_taskbar_icon_for_window, load_icon_universal, set_window_title_bar_theme


class NameDialog(QDialog):
    """命名对话框

    用于收藏配色方案时输入自定义名称。
    """

    def __init__(self, title="命名配色方案", default_name="", parent=None):
        """初始化命名对话框

        Args:
            title: 对话框标题
            default_name: 默认名称
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 150)
        self._default_name = default_name
        self._name = ""

        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())

        # 设置窗口标志：只保留关闭按钮
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.CustomizeWindowHint
        )

        # 设置窗口背景色
        bg_color = get_dialog_bg_color()
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color.name()}; }}")

        self.setup_ui()

        # 修复任务栏图标
        QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(self))

        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_title_bar_theme)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 提示标签
        self.hint_label = QLabel("请输入配色方案名称：")
        self._update_label_style()
        layout.addWidget(self.hint_label)

        # 输入框
        self.name_input = LineEdit(self)
        self.name_input.setText(self._default_name)
        self.name_input.setPlaceholderText("输入名称...")
        self.name_input.setClearButtonEnabled(True)
        layout.addWidget(self.name_input)

        # 按钮区域
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        buttons_layout.addStretch()

        # 取消按钮
        self.cancel_button = PushButton("取消")
        self.cancel_button.setMinimumWidth(80)
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        # 确认按钮（主题色）
        self.confirm_button = PrimaryPushButton("确认")
        self.confirm_button.setMinimumWidth(80)
        self.confirm_button.clicked.connect(self._on_confirm)
        buttons_layout.addWidget(self.confirm_button)

        layout.addWidget(buttons_container)

        # 设置焦点到输入框并选中默认文本
        self.name_input.setFocus()
        self.name_input.selectAll()

    def _update_label_style(self):
        """更新标签样式"""
        text_color = get_text_color()
        self.hint_label.setStyleSheet(f"color: {text_color.name()}; font-size: 13px;")

    def _update_title_bar_theme(self):
        """更新标题栏主题以适配当前主题"""
        set_window_title_bar_theme(self, isDarkTheme())

    def _on_confirm(self):
        """确认按钮点击"""
        self._name = self.name_input.text().strip()
        if self._name:
            self.accept()
        else:
            # 如果名称为空，使用默认名称
            self._name = self._default_name
            self.accept()

    def get_name(self):
        """获取输入的名称

        Returns:
            str: 用户输入的名称
        """
        return self._name

    def showEvent(self, event):
        """窗口显示事件 - 在显示前设置标题栏主题避免闪烁"""
        self._update_title_bar_theme()
        super().showEvent(event)
