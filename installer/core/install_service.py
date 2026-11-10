# 标准库导入
import shutil
import time
from pathlib import Path
from typing import Any

# 第三方库导入
from PySide6.QtCore import QObject, Signal, QThread

# 项目模块导入
from installer.core.constants import APP_EXE_NAME, PAYLOAD_ZIP_NAME
from installer.core.file_installer import FileInstaller
from installer.core.permission_checker import close_app_processes
from installer.core.registry_installer import RegistryInstaller
from utils import get_base_path

try:
    from version import version_manager
    APP_NAME = version_manager.app_info['name']
except ImportError:
    APP_NAME = "取色卡"

# 清空安装目录的有限重试：进程关闭后句柄释放与杀软扫描存在延迟
CLEAR_RETRY_TIMES = 3
CLEAR_RETRY_INTERVAL_SECONDS = 0.5


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
            if not self._deploy_files(install_path):
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
            self.install_completed.emit(False, f"安装失败: {str(e)}")

    def _close_old_app(self, install_path: Path) -> None:
        """关闭旧版本程序（覆盖安装场景）

        Args:
            install_path: 安装路径
        """
        exe_path = install_path / APP_EXE_NAME
        if not exe_path.exists():
            return
        close_app_processes(APP_EXE_NAME)

    def _deploy_files(self, install_path: Path) -> bool:
        """部署程序文件：关闭旧版 → 清空前护栏 → 清空 → 解压载荷铺开

        失败时通过 install_completed 信号发出具体原因并返回 False，调用方
        直接结束安装流程，不再重复发出失败信号。

        Args:
            install_path: 安装路径

        Returns:
            bool: 是否成功
        """
        try:
            self._close_old_app(install_path)

            if not self._ensure_safe_to_clear(install_path):
                self.install_completed.emit(False, "目标目录包含非应用文件，请确认安装路径")
                return False

            # 载荷检查放在清空之前，避免载荷缺失时已把旧安装清掉
            payload_path = Path(get_base_path()) / PAYLOAD_ZIP_NAME
            if not payload_path.exists():
                self.install_completed.emit(False, "安装包载荷缺失")
                return False

            if not self._clear_install_path(install_path):
                return False

            def progress_callback(percent: int, message: str):
                mapped_percent = int(percent * 0.8)
                self.progress_updated.emit(mapped_percent, message)

            if not self._file_installer.extract_payload(payload_path, install_path, progress_callback):
                self.install_completed.emit(False, "程序文件解压失败")
                return False

            return True

        except OSError as e:
            self.install_completed.emit(False, f"文件部署失败: {e}")
            return False

    def _ensure_safe_to_clear(self, install_path: Path) -> bool:
        """检查目标目录是否可安全清空

        满足任一条件即通过：注册表记录的安装路径与目标一致（Windows 下
        pathlib 比较大小写不敏感）、目录内存在应用标记主程序、目录不存在
        或为空。

        Args:
            install_path: 安装路径

        Returns:
            bool: 是否可安全清空
        """
        if not install_path.exists():
            return True

        if not any(install_path.iterdir()):
            return True

        registry_path = self._registry_installer.get_install_path()
        if registry_path is not None and registry_path == install_path:
            return True

        return (install_path / APP_EXE_NAME).exists()

    def _clear_install_path(self, install_path: Path) -> bool:
        """清空安装目录（整目录删除，随后由载荷解压重建）

        删除做有限重试，覆盖进程关闭后句柄释放延迟与杀软扫描；重试耗尽仍
        失败则发出失败信号并中止，不进入解压。目录不存在直接跳过。

        Args:
            install_path: 安装路径

        Returns:
            bool: 是否成功
        """
        if not install_path.exists():
            return True

        for remaining in range(CLEAR_RETRY_TIMES, 0, -1):
            try:
                shutil.rmtree(install_path)
                return True
            except OSError:
                # 最后一次失败不再等待，直接进入失败分支
                if remaining > 1:
                    time.sleep(CLEAR_RETRY_INTERVAL_SECONDS)

        self.install_completed.emit(False, "无法清空目标目录，请关闭相关程序后重试")
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

        except OSError:
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
            exe_path = install_path / APP_EXE_NAME

            if self._config.get('create_desktop_shortcut', True):
                if not shortcut_installer.create_desktop_shortcut(exe_path, APP_NAME):
                    return False

            if self._config.get('create_start_menu', True):
                if not shortcut_installer.create_start_menu_shortcut(exe_path, APP_NAME):
                    return False

            # 卸载快捷方式与注册表 UninstallString 同样指向主程序
            if not shortcut_installer.create_uninstall_shortcut(exe_path, APP_NAME):
                return False

            return True

        except (ImportError, OSError):
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
