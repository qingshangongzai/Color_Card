# 标准库导入
import shutil
import sys
from pathlib import Path
# 第三方库导入
from PySide6.QtCore import QObject, Signal, QThread

# 项目模块导入
from core import get_logger
from installer.core.registry_installer import RegistryInstaller
from installer.core.shortcut_installer import ShortcutInstaller

# 获取应用信息
try:
    from version import version_manager
    APP_NAME = version_manager.app_info['name']
except ImportError:
    APP_NAME = "取色卡"

logger = get_logger("installer.uninstall_service")


class UninstallWorker(QThread):
    """卸载工作线程

    在后台执行卸载任务，避免阻塞UI。
    """

    progress_updated = Signal(int, str)  # 进度百分比, 当前操作
    uninstall_completed = Signal(bool, str)  # 成功标志, 消息

    def __init__(self, install_path: Path, delete_config: bool):
        """初始化工作线程

        Args:
            install_path: 安装路径
            delete_config: 是否删除用户配置
        """
        super().__init__()
        self._install_path = install_path
        self._delete_config = delete_config
        self._registry_installer = RegistryInstaller()
        self._shortcut_installer = ShortcutInstaller()

    def run(self):
        """执行卸载"""
        try:
            # 1. 删除快捷方式
            self.progress_updated.emit(10, "正在删除快捷方式... |")
            if not self._remove_shortcuts(APP_NAME):
                self.uninstall_completed.emit(False, "快捷方式删除失败")
                return

            # 2. 删除注册表项
            self.progress_updated.emit(30, "正在删除注册表项... |")
            if not self._remove_registry():
                self.uninstall_completed.emit(False, "注册表删除失败")
                return

            # 3. 删除用户配置（可选）
            if self._delete_config:
                self.progress_updated.emit(50, "正在删除用户配置... |")
                if not self._remove_user_config():
                    logger.warning("用户配置删除失败，继续卸载")

            # 4. 创建自删除批处理脚本
            self.progress_updated.emit(70, "正在准备清理脚本... |")
            if not self._create_self_delete_batch():
                logger.warning("自删除脚本创建失败")

            # 5. 删除安装文件（通过批处理脚本执行）
            self.progress_updated.emit(90, "正在清理安装文件... |")

            # 完成
            self.progress_updated.emit(100, "卸载完成！ |")
            self.uninstall_completed.emit(True, "卸载成功")

        except (OSError, PermissionError, RuntimeError) as e:
            logger.error(f"卸载过程异常: {str(e)}")
            self.uninstall_completed.emit(False, f"卸载失败: {str(e)}")

    def _remove_shortcuts(self, app_name: str) -> bool:
        """删除快捷方式

        Args:
            app_name: 应用名称

        Returns:
            bool: 是否成功
        """
        try:
            # 删除桌面快捷方式
            if not self._shortcut_installer.remove_desktop_shortcut(app_name):
                return False

            # 删除开始菜单快捷方式
            if not self._shortcut_installer.remove_start_menu_shortcuts(app_name):
                return False

            return True

        except (OSError, PermissionError, RuntimeError) as e:
            logger.error(f"快捷方式删除失败: {str(e)}")
            return False

    def _remove_registry(self) -> bool:
        """删除注册表项

        Returns:
            bool: 是否成功
        """
        try:
            # 删除安装信息
            if not self._registry_installer.remove_install_info():
                logger.warning("安装信息删除失败")

            # 删除卸载条目
            if not self._registry_installer.remove_uninstall_entry():
                logger.warning("卸载条目删除失败")

            return True

        except (OSError, PermissionError, RuntimeError) as e:
            logger.error(f"注册表删除失败: {str(e)}")
            return False

    def _remove_user_config(self) -> bool:
        """删除用户配置

        Returns:
            bool: 是否成功
        """
        try:
            # 用户配置目录
            config_dir = Path.home() / ".color_card"

            if not config_dir.exists():
                return True

            # 关闭日志系统，释放文件占用
            try:
                from core import get_logger_manager
                logger_manager = get_logger_manager()
                logger_manager.shutdown()
            except (OSError, RuntimeError):
                pass

            # 删除用户配置目录
            shutil.rmtree(config_dir)
            logger.info(f"用户配置删除成功: {config_dir}")

            return True

        except (OSError, PermissionError) as e:
            logger.error(f"用户配置删除失败: {str(e)}")
            return False

    def _create_self_delete_batch(self) -> bool:
        """创建自删除批处理脚本

        Returns:
            bool: 是否成功
        """
        try:
            # 批处理脚本路径
            batch_path = self._install_path / "uninstall_cleanup.bat"

            # 用GBK编码写入，确保cmd.exe正确解析中文路径
            batch_content = f"""@echo off
cd /d "%TEMP%"
ping 127.0.0.1 -n 4 > nul
rd /s /q "{self._install_path}" 2>nul
if exist "{self._install_path}" (
    ping 127.0.0.1 -n 4 > nul
    rd /s /q "{self._install_path}" 2>nul
)
(goto) 2>nul & del "%~f0"
"""

            # 写入批处理脚本
            batch_path.write_text(batch_content, encoding='gbk')

            logger.info(f"自删除脚本创建成功: {batch_path}")
            return True

        except (OSError, PermissionError) as e:
            logger.error(f"自删除脚本创建失败: {str(e)}")
            return False


class UninstallService(QObject):
    """卸载服务

    管理卸载流程，提供进度更新和完成信号。
    """

    progress_updated = Signal(int, str)  # 进度百分比, 当前操作
    uninstall_completed = Signal(bool, str)  # 成功标志, 消息

    def __init__(self):
        """初始化卸载服务"""
        super().__init__()
        self._worker = None

    def uninstall(self, install_path: Path, delete_config: bool):
        """执行卸载

        Args:
            install_path: 安装路径
            delete_config: 是否删除用户配置
        """
        # 创建工作线程
        self._worker = UninstallWorker(install_path, delete_config)

        # 连接信号
        self._worker.progress_updated.connect(self.progress_updated.emit)
        self._worker.uninstall_completed.connect(self._on_uninstall_completed)

        # 启动线程
        self._worker.start()

    def _on_uninstall_completed(self, success: bool, message: str):
        """卸载完成处理

        Args:
            success: 是否成功
            message: 结果消息
        """
        # 清理工作线程
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

        # 发射完成信号
        self.uninstall_completed.emit(success, message)
