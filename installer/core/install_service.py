from __future__ import annotations
# 标准库导入
from pathlib import Path
from typing import Any

# 第三方库导入
from PySide6.QtCore import QObject, Signal, QThread

# 项目模块导入
from core import get_logger
from installer.core.file_installer import FileInstaller
from installer.core.registry_installer import RegistryInstaller
from installer.core.permission_checker import is_frozen, get_exe_path, close_app_processes

try:
    from version import version_manager
    APP_NAME = version_manager.app_info['name']
except ImportError:
    APP_NAME = "取色卡"

logger = get_logger("installer.install_service")


class InstallWorker(QThread):
    """安装工作线程

    在后台执行安装任务，避免阻塞UI。
    """

    progress_updated = Signal(int, str)
    install_completed = Signal(bool, str)

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self._config = config
        self._file_installer = FileInstaller()
        self._registry_installer = RegistryInstaller()

    def run(self):
        try:
            install_path = Path(self._config['install_path'])

            self.progress_updated.emit(0, "正在准备安装... |")
            if not self._copy_files(install_path):
                self.install_completed.emit(False, "文件复制失败")
                return

            self.progress_updated.emit(80, "正在写入注册表... |")
            if not self._write_registry(install_path):
                self.install_completed.emit(False, "注册表写入失败")
                return

            self.progress_updated.emit(90, "正在创建快捷方式... |")
            if not self._create_shortcuts(install_path):
                self.install_completed.emit(False, "快捷方式创建失败")
                return

            self.progress_updated.emit(100, "安装完成！ |")
            self.install_completed.emit(True, "安装成功")

        except (OSError, PermissionError, RuntimeError) as e:
            logger.error(f"安装过程异常: {str(e)}")
            self.install_completed.emit(False, f"安装失败: {str(e)}")

    def _close_old_app(self, install_path: Path) -> None:
        """关闭旧版本程序（覆盖安装场景）

        Args:
            install_path: 安装路径
        """
        exe_path = install_path / "Color Card.exe"
        if not exe_path.exists():
            return
        close_app_processes("Color Card.exe")
        logger.info("已关闭旧版本程序")

    def _copy_files(self, install_path: Path) -> bool:
        """复制程序文件

        Args:
            install_path: 安装路径

        Returns:
            bool: 是否成功
        """
        try:
            self._close_old_app(install_path)

            if is_frozen():
                src_exe = get_exe_path()
            else:
                return True

            def progress_callback(percent: int, message: str):
                mapped_percent = int(percent * 0.8)
                self.progress_updated.emit(mapped_percent, message)

            return self._file_installer.copy_executable(
                src_exe,
                install_path,
                "Color Card.exe",
                progress_callback
            )

        except (OSError, PermissionError) as e:
            logger.error(f"文件复制失败: {str(e)}")
            return False

    def _write_registry(self, install_path: Path) -> bool:
        """写入注册表

        Args:
            install_path: 安装路径

        Returns:
            bool: 是否成功
        """
        try:
            self._registry_installer.remove_inno_entry()

            install_size_kb = FileInstaller.calculate_size(install_path)
            config = {
                'install_path': str(install_path),
                'install_size_kb': install_size_kb
            }

            if not self._registry_installer.write_install_info(config):
                return False
            if not self._registry_installer.write_uninstall_entry(config):
                return False

            return True

        except (OSError, PermissionError) as e:
            logger.error(f"注册表写入失败: {str(e)}")
            return False

    def _create_shortcuts(self, install_path: Path) -> bool:
        """创建快捷方式

        Args:
            install_path: 安装路径

        Returns:
            bool: 是否成功
        """
        try:
            from installer.core.shortcut_installer import ShortcutInstaller

            shortcut_installer = ShortcutInstaller()
            exe_path = install_path / "Color Card.exe"

            if self._config.get('create_desktop_shortcut', True):
                if not shortcut_installer.create_desktop_shortcut(exe_path, APP_NAME):
                    return False

            if self._config.get('create_start_menu', True):
                if not shortcut_installer.create_start_menu_shortcut(exe_path, APP_NAME):
                    return False

            if not shortcut_installer.create_uninstall_shortcut(exe_path, APP_NAME):
                return False

            return True

        except (ImportError, OSError, PermissionError) as e:
            logger.error(f"快捷方式创建失败: {str(e)}")
            return False


class InstallService(QObject):
    """安装服务

    管理安装流程，提供进度更新和完成信号。
    """

    progress_updated = Signal(int, str)
    install_completed = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self._worker = None

    def install(self, config: dict[str, Any]):
        """执行安装

        Args:
            config: 安装配置
                - install_path: 安装路径
                - create_desktop_shortcut: 是否创建桌面快捷方式
                - create_start_menu: 是否创建开始菜单快捷方式
        """
        self._worker = InstallWorker(config)
        self._worker.progress_updated.connect(self.progress_updated.emit)
        self._worker.install_completed.connect(self._on_install_completed)
        self._worker.start()

    def _on_install_completed(self, success: bool, message: str):
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        self.install_completed.emit(success, message)
