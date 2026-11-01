# 标准库导入
from pathlib import Path
# 第三方库导入
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar
)
from PySide6.QtCore import Qt
from qfluentwidgets import (
    CheckBox, PrimaryPushButton, PushButton, qconfig,
    setThemeColor
)

# 项目模块导入
from dialogs.base_frameless_dialog import BaseFramelessDialog
from installer.uninstaller.uninstall_service import UninstallService
from installer.core.permission_checker import is_admin, requires_admin, run_as_admin, close_app_processes
from utils.icon import load_icon_universal
from utils.platform import fix_windows_taskbar_icon_for_window

# 获取应用信息
try:
    from version import version_manager
    APP_NAME = version_manager.app_info['name']
except ImportError:
    APP_NAME = "取色卡"


class UninstallDialog(BaseFramelessDialog):
    """卸载对话框"""

    def __init__(self, parent=None):
        """初始化卸载对话框

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle(f"卸载 {APP_NAME}")
        self.setFixedSize(440, 230)

        # 设置主题色（与主程序一致）
        setThemeColor('#0078d4')

        # 设置窗口图标（任务栏图标）
        self.setWindowIcon(load_icon_universal())

        # 设置自定义标题栏
        self._setup_title_bar()

        # 初始化样式
        self._update_styles()

        # 设置界面
        self.setup_ui()

        # 监听主题变化
        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        # 允许窗口显示
        self._enable_show()

        # 修复 Windows 任务栏图标
        fix_windows_taskbar_icon_for_window(self)

        # 卸载服务
        self._uninstall_service = None

    def setup_ui(self):
        """设置界面"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(20)

        # 标题
        self.title_label = QLabel(f"确定要卸载 {APP_NAME} 吗？")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 描述
        self.desc_label = QLabel("卸载将删除程序文件和注册表项。")
        self.desc_label.setStyleSheet("font-size: 13px;")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.desc_label)

        # 添加弹性空间
        layout.addStretch()

        # 复选框 - 居中
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addStretch()
        self.delete_config_checkbox = CheckBox("删除用户配置和数据文件")
        checkbox_layout.addWidget(self.delete_config_checkbox)
        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)

        # 进度区域（初始隐藏）
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(10)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        progress_layout.addWidget(self.progress_bar)

        # 进度文本
        self.progress_label = QLabel("准备卸载...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_label)

        self.progress_widget.setVisible(False)
        layout.addWidget(self.progress_widget)

        # 按钮区域 - 居中
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.uninstall_button = PrimaryPushButton("卸载")
        self.uninstall_button.setFixedWidth(80)
        self.uninstall_button.clicked.connect(self._on_uninstall_clicked)
        button_layout.addWidget(self.uninstall_button)

        button_layout.addSpacing(12)

        self.cancel_button = PushButton("取消")
        self.cancel_button.setFixedWidth(80)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _close_main_app(self):
        """关闭主程序进程（排除当前卸载程序进程）"""
        close_app_processes("Color Card.exe")

    def start_uninstall(self, delete_config: bool = False):
        """直接开始卸载（提权重启后调用）

        Args:
            delete_config: 是否删除用户配置
        """
        self._execute_uninstall(delete_config)

    def _on_uninstall_clicked(self):
        """卸载按钮点击"""
        # 获取安装路径
        install_path = self._get_install_path()
        if not install_path:
            self._on_uninstall_completed(False, "未找到安装路径")
            return

        # 检测是否需要管理员权限
        if requires_admin(install_path) and not is_admin():
            # 显示确认对话框
            from installer.wizard.elevation_dialog import ElevationDialog
            dialog = ElevationDialog(self.window())
            dialog.setWindowTitle("需要管理员权限")
            dialog.set_message(
                "卸载该程序需要管理员权限。\n"
                "点击「确定」后，Windows 将请求您的确认。"
            )
            if dialog.exec():
                delete_config = self.delete_config_checkbox.isChecked()
                run_as_admin(is_uninstall=True, delete_config=delete_config)
            return

        delete_config = self.delete_config_checkbox.isChecked()
        self._execute_uninstall(delete_config)

    def _execute_uninstall(self, delete_config: bool):
        """执行卸载操作

        Args:
            delete_config: 是否删除用户配置
        """
        # 关闭主程序
        self._close_main_app()

        # 获取安装路径
        install_path = self._get_install_path()
        if not install_path:
            self._on_uninstall_completed(False, "未找到安装路径")
            return

        # 隐藏标题、描述、复选框、按钮
        self.title_label.setVisible(False)
        self.desc_label.setVisible(False)
        self.delete_config_checkbox.setVisible(False)
        self.uninstall_button.setVisible(False)
        self.cancel_button.setVisible(False)

        # 显示进度区域
        self.progress_widget.setVisible(True)

        # 调整对话框大小为更紧凑的尺寸
        self.setFixedSize(440, 120)

        # 创建卸载服务
        self._uninstall_service = UninstallService()

        # 连接信号
        self._uninstall_service.progress_updated.connect(self._on_progress_updated)
        self._uninstall_service.uninstall_completed.connect(self._on_uninstall_completed)

        # 执行卸载
        self._uninstall_service.uninstall(install_path, delete_config)

    def _get_install_path(self) -> Path | None:
        """获取安装路径

        Returns:
            Path | None: 安装路径
        """
        # 从注册表获取安装路径
        from installer.core.registry_installer import RegistryInstaller

        registry_installer = RegistryInstaller()
        return registry_installer.get_install_path()

    def _on_progress_updated(self, percent: int, message: str):
        """进度更新

        Args:
            percent: 进度百分比
            message: 当前操作
        """
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def _on_uninstall_completed(self, success: bool, message: str):
        """卸载完成

        Args:
            success: 是否成功
            message: 结果消息
        """
        if success:
            self.progress_label.setText("卸载完成！")
            # 延迟关闭对话框
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, self.accept)
        else:
            self.progress_label.setText(f"卸载失败: {message}")
            # 重新启用按钮
            self.uninstall_button.setEnabled(True)
            self.cancel_button.setEnabled(True)

    def closeEvent(self, event):
        """关闭事件"""
        # 断开信号连接
        if self._uninstall_service:
            try:
                self._uninstall_service.progress_updated.disconnect()
                self._uninstall_service.uninstall_completed.disconnect()
            except (TypeError, RuntimeError):
                pass

        super().closeEvent(event)
