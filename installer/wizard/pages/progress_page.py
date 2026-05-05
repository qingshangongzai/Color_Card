# 第三方库导入
from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from qfluentwidgets import ProgressBar, IndeterminateProgressBar

# 项目模块导入
from installer.wizard.base_page import BasePage


class ProgressPage(BasePage):
    """进度页面

    显示安装进度和当前操作。
    """

    def __init__(self, parent=None):
        """初始化页面

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._install_service = None

    def setup_ui(self):
        """设置页面UI"""
        layout = self._content_layout
        layout.setSpacing(20)

        layout.addStretch(1)

        title_label = QLabel("正在安装...")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        self._progress_bar = ProgressBar()
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        self._percent_label = QLabel("0%")
        self._percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._percent_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self._percent_label)

        self._status_label = QLabel("准备安装...")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self._status_label)

        self._file_label = QLabel("")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_label.setStyleSheet("font-size: 11px;")
        self._file_label.setWordWrap(True)
        layout.addWidget(self._file_label)

        layout.addStretch(1)

    def set_install_service(self, service):
        """设置安装服务

        Args:
            service: InstallService 实例
        """
        self._install_service = service
        if service:
            service.progress_updated.connect(self._on_progress_updated)
            service.install_completed.connect(self._on_install_completed)

    def _on_progress_updated(self, percent: int, message: str):
        """进度更新

        Args:
            percent: 进度百分比
            message: 当前操作消息
        """
        self._progress_bar.setValue(percent)
        self._percent_label.setText(f"{percent}%")

        # 解析消息（格式："操作 | 文件路径"）
        if '|' in message:
            parts = message.split('|', 1)
            self._status_label.setText(parts[0].strip())
            self._file_label.setText(parts[1].strip() if len(parts) > 1 else "")
        else:
            self._status_label.setText(message)
            self._file_label.setText("")

    def _on_install_completed(self, success: bool, message: str):
        if success:
            self.next_requested.emit()
        else:
            self._status_label.setText(f"安装失败：{message}")
            self._progress_bar.setValue(0)

    def on_enter(self):
        """进入页面时的处理"""
        # 重置进度
        self._progress_bar.setValue(0)
        self._percent_label.setText("0%")
        self._status_label.setText("准备安装...")
        self._file_label.setText("")

        # 启动安装
        if self._install_service and self._wizard:
            config = self._wizard.get_config()
            self._install_service.install(config)

    def can_back(self) -> bool:
        """是否可以返回上一页

        Returns:
            bool: 是否可以返回上一页
        """
        # 安装过程中不允许返回
        return False

    def _update_styles(self):
        super()._update_styles()

        text_color = QColor(40, 40, 40)
        secondary_color = QColor(120, 120, 120)

        for child in self._content_widget.findChildren(QLabel):
            if "正在安装" in child.text():
                child.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {text_color.name()};")
            elif child.text().endswith('%'):
                child.setStyleSheet(f"font-size: 14px; color: {text_color.name()};")
            elif "准备安装" in child.text() or "安装失败" in child.text():
                child.setStyleSheet(f"font-size: 12px; color: {text_color.name()};")
            else:
                child.setStyleSheet(f"font-size: 11px; color: {secondary_color.name()};")
