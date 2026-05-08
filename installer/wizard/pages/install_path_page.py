from __future__ import annotations
# 标准库导入
import os
import shutil
from pathlib import Path

# 第三方库导入
from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from qfluentwidgets import LineEdit, PushButton, PrimaryPushButton, CheckBox

# 项目模块导入
from installer.wizard.base_page import BasePage
from installer.core.permission_checker import is_admin, requires_admin


class InstallPathPage(BasePage):
    """路径选择页面

    选择安装位置和快捷方式选项。
    """

    elevation_requested = Signal(str, bool, bool)  # 参数：安装路径, 桌面快捷方式, 开始菜单快捷方式

    def __init__(self, parent=None):
        """初始化页面

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._required_space_mb = 150  # 所需空间 MB
        self._pending_path = ''  # 外部预填路径（setup_ui 前设置）

    def setup_ui(self):
        """设置页面UI"""
        layout = self._content_layout
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("选择安装位置")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        # 路径选择区域
        path_layout = QHBoxLayout()
        path_layout.setSpacing(10)

        path_label = QLabel("安装路径：")
        path_layout.addWidget(path_label)

        self._path_edit = LineEdit()
        self._path_edit.setPlaceholderText("选择安装目录")
        self._path_edit.textChanged.connect(self._on_path_changed)
        path_layout.addWidget(self._path_edit, 1)

        self._browse_button = PushButton("浏览...")
        self._browse_button.setFixedWidth(80)
        self._browse_button.clicked.connect(self._browse_path)
        path_layout.addWidget(self._browse_button)

        layout.addLayout(path_layout)

        # 空间信息
        self._space_label = QLabel()
        self._space_label.setStyleSheet("font-size: 12px;")
        self._update_space_info()
        layout.addWidget(self._space_label)

        layout.addStretch(1)

        # 快捷方式选项
        options_layout = QVBoxLayout()
        options_layout.setSpacing(10)

        self._desktop_checkbox = CheckBox("创建桌面快捷方式")
        self._desktop_checkbox.setChecked(True)
        self._desktop_checkbox.stateChanged.connect(self._on_option_changed)
        options_layout.addWidget(self._desktop_checkbox)

        self._start_menu_checkbox = CheckBox("创建开始菜单快捷方式")
        self._start_menu_checkbox.setChecked(True)
        self._start_menu_checkbox.stateChanged.connect(self._on_option_changed)
        options_layout.addWidget(self._start_menu_checkbox)

        layout.addLayout(options_layout)

        layout.addStretch(1)

        # 导航按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch(1)

        self._back_button = PushButton("上一步")
        self._back_button.setFixedSize(100, 32)
        self._back_button.clicked.connect(self.back_requested.emit)
        button_layout.addWidget(self._back_button)

        self._install_button = PrimaryPushButton("安装")
        self._install_button.setFixedSize(100, 32)
        self._install_button.clicked.connect(self._start_install)
        button_layout.addWidget(self._install_button)

        layout.addLayout(button_layout)

        self._set_default_path()

    def set_default_path(self, path: str):
        """从外部设置默认路径（升级场景预填旧路径）

        Args:
            path: 默认路径
        """
        self._pending_path = path

    def _set_default_path(self):
        """设置默认安装路径"""
        # 优先使用外部预填路径
        if self._pending_path:
            self._path_edit.setText(self._pending_path)
            return

        program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        default_path = os.path.join(program_files, '取色卡')
        self._path_edit.setText(default_path)

    def _browse_path(self):
        """浏览选择安装路径"""
        current_path = self._path_edit.text()
        if not current_path or not os.path.exists(current_path):
            current_path = os.environ.get('ProgramFiles', 'C:\\Program Files')

        folder = QFileDialog.getExistingDirectory(
            self,
            "选择安装目录",
            current_path,
            QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self._path_edit.setText(folder)

    def _on_path_changed(self, path: str):
        """路径改变时更新空间信息

        Args:
            path: 新路径
        """
        self._update_space_info()
        # 保存到配置
        self._config['install_path'] = path

    def _update_space_info(self):
        """更新空间信息显示"""
        path = self._path_edit.text()

        # 获取可用空间
        available_mb = 0
        if path:
            try:
                # 获取路径所在驱动器的可用空间
                drive = os.path.splitdrive(path)[0]
                if drive:
                    usage = shutil.disk_usage(drive)
                    available_mb = usage.free // (1024 * 1024)
            except (OSError, ValueError):
                available_mb = 0

        # 更新显示
        self._space_label.setText(
            f"所需空间：{self._required_space_mb} MB    可用空间：{available_mb} MB"
        )

    def _on_option_changed(self):
        """快捷方式选项改变"""
        self._config['create_desktop_shortcut'] = self._desktop_checkbox.isChecked()
        self._config['create_start_menu'] = self._start_menu_checkbox.isChecked()

    def _start_install(self):
        """开始安装"""
        path = self._path_edit.text()
        if not path:
            return

        # 验证路径
        if not self._validate_path(path):
            return

        # 获取快捷方式选项
        create_desktop = self._desktop_checkbox.isChecked()
        create_start_menu = self._start_menu_checkbox.isChecked()

        # 检测是否需要管理员权限
        if requires_admin(path) and not is_admin():
            # 显示确认对话框
            from installer.wizard.elevation_dialog import ElevationDialog
            dialog = ElevationDialog(self.window())
            dialog.set_message(
                "安装到该位置需要管理员权限。\n"
                "点击「确定」后，Windows 将请求您的确认。"
            )
            if dialog.exec():
                # 用户确认，发射提权请求
                self.elevation_requested.emit(path, create_desktop, create_start_menu)
            return

        # 保存配置
        self._config['install_path'] = path
        self._config['create_desktop_shortcut'] = create_desktop
        self._config['create_start_menu'] = create_start_menu

        # 进入下一页
        self.next_requested.emit()

    def _validate_path(self, path: str) -> bool:
        """验证路径有效性

        Args:
            path: 安装路径

        Returns:
            bool: 是否有效
        """
        # 检查路径是否为空
        if not path or not path.strip():
            return False

        # 检查是否为系统关键目录
        critical_paths = [
            os.environ.get('SystemRoot', 'C:\\Windows'),
            os.environ.get('SystemRoot', 'C:\\Windows') + '\\System32',
        ]

        for critical in critical_paths:
            if critical and path.lower().startswith(critical.lower()):
                return False

        return True

    def can_next(self) -> bool:
        """是否可以进入下一页

        Returns:
            bool: 是否可以进入下一页
        """
        path = self._path_edit.text()
        return self._validate_path(path)

    def on_enter(self):
        """进入页面时的处理"""
        self._update_space_info()

    def _update_styles(self):
        super()._update_styles()

        text_color = QColor(40, 40, 40)
        secondary_color = QColor(120, 120, 120)

        for child in self._content_widget.findChildren(QLabel):
            if "选择安装位置" in child.text():
                child.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {text_color.name()};")
            elif "所需空间" in child.text():
                child.setStyleSheet(f"font-size: 12px; color: {secondary_color.name()};")
