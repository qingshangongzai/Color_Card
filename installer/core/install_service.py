# 标准库导入
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# 第三方库导入
from PySide6.QtCore import QObject, Signal, QThread

# 项目模块导入
from core import get_logger
from installer.core.file_installer import FileInstaller
from installer.core.registry_installer import RegistryInstaller
from installer.core.permission_checker import is_frozen

# 获取应用信息
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

    progress_updated = Signal(int, str)  # 进度百分比, 当前操作
    install_completed = Signal(bool, str)  # 成功标志, 消息

    def __init__(self, config: dict[str, Any], test_mode: bool = False):
        """初始化工作线程

        Args:
            config: 安装配置
            test_mode: 测试模式
        """
        super().__init__()
        self._config = config
        self._test_mode = test_mode
        self._file_installer = FileInstaller()
        self._registry_installer = RegistryInstaller(test_mode)

    def run(self):
        """执行安装"""
        try:
            # 开发环境检测
            is_dev = not is_frozen()

            # 测试模式重定向安装路径
            if self._test_mode:
                self._config['install_path'] = Path(tempfile.gettempdir()) / 'color_card_test'
                logger.info(f"测试模式：安装路径重定向到 {self._config['install_path']}")

            install_path = Path(self._config['install_path'])

            # 开发环境：检查 test_dist/ 是否存在
            skip_file_copy = False
            if is_dev:
                src_dir = FileInstaller.get_source_dir()
                project_root = Path(__file__).parent.parent.parent
                # 如果源目录是项目根目录（test_dist 不存在），跳过文件复制
                if src_dir == project_root:
                    skip_file_copy = True
                    logger.info("开发环境：test_dist/ 不存在，跳过文件复制")
                    self.progress_updated.emit(0, "开发环境测试，跳过文件复制 |")

            if not skip_file_copy:
                # 1. 复制文件
                self.progress_updated.emit(0, "正在准备安装... |")
                if not self._copy_files(install_path):
                    self.install_completed.emit(False, "文件复制失败")
                    return

            # 2. 写入注册表
            if not self._test_mode:
                self.progress_updated.emit(80, "正在写入注册表... |")
                if not self._write_registry(install_path):
                    self.install_completed.emit(False, "注册表写入失败")
                    return

            # 3. 创建快捷方式
            if not self._test_mode:
                self.progress_updated.emit(90, "正在创建快捷方式... |")
                if not self._create_shortcuts(install_path):
                    self.install_completed.emit(False, "快捷方式创建失败")
                    return

            # 完成
            self.progress_updated.emit(100, "安装完成！ |")
            self.install_completed.emit(True, "安装成功")

        except Exception as e:
            logger.error(f"安装过程异常: {str(e)}")
            self.install_completed.emit(False, f"安装失败: {str(e)}")

    def _copy_files(self, install_path: Path) -> bool:
        """复制程序文件

        Args:
            install_path: 安装路径

        Returns:
            bool: 是否成功
        """
        try:
            # 获取可执行文件路径
            if is_frozen():
                # 打包后：使用当前可执行文件
                src_exe = Path(sys.executable)
            else:
                # 开发环境：使用 test_dist/ColorCard.exe（如果存在）
                project_root = Path(__file__).parent.parent.parent
                test_exe = project_root / 'test_dist' / 'ColorCard.exe'
                if test_exe.exists():
                    src_exe = test_exe
                else:
                    # 如果不存在，使用当前 Python 解释器（仅用于测试）
                    logger.warning("未找到测试可执行文件，跳过文件复制")
                    return True

            # 复制可执行文件
            def progress_callback(percent: int, message: str):
                # 映射到 0-80% 的进度范围
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
            # 计算安装大小
            install_size_kb = FileInstaller.calculate_size(install_path)

            # 写入安装信息
            config = {
                'install_path': str(install_path),
                'install_size_kb': install_size_kb
            }

            if not self._registry_installer.write_install_info(config):
                return False

            if not self._registry_installer.write_uninstall_entry(config):
                return False

            return True

        except Exception as e:
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

            shortcut_installer = ShortcutInstaller(self._test_mode)
            exe_path = install_path / "Color Card.exe"

            # 创建桌面快捷方式
            if self._config.get('create_desktop_shortcut', True):
                if not shortcut_installer.create_desktop_shortcut(exe_path, APP_NAME):
                    return False

            # 创建开始菜单快捷方式
            if self._config.get('create_start_menu', True):
                if not shortcut_installer.create_start_menu_shortcut(exe_path, APP_NAME):
                    return False

            # 创建卸载快捷方式
            if not shortcut_installer.create_uninstall_shortcut(exe_path, APP_NAME):
                return False

            return True

        except Exception as e:
            logger.error(f"快捷方式创建失败: {str(e)}")
            return False


class InstallService(QObject):
    """安装服务

    管理安装流程，提供进度更新和完成信号。
    """

    progress_updated = Signal(int, str)  # 进度百分比, 当前操作
    install_completed = Signal(bool, str)  # 成功标志, 消息

    def __init__(self, test_mode: bool = False):
        """初始化安装服务

        Args:
            test_mode: 测试模式，不写入系统目录和注册表
        """
        super().__init__()
        self._test_mode = test_mode
        self._worker = None

    def install(self, config: dict[str, Any]):
        """执行安装

        Args:
            config: 安装配置
                - install_path: 安装路径
                - create_desktop_shortcut: 是否创建桌面快捷方式
                - create_start_menu: 是否创建开始菜单快捷方式
        """
        # 创建工作线程
        self._worker = InstallWorker(config, self._test_mode)

        # 连接信号
        self._worker.progress_updated.connect(self.progress_updated.emit)
        self._worker.install_completed.connect(self._on_install_completed)

        # 启动线程
        self._worker.start()

    def _on_install_completed(self, success: bool, message: str):
        """安装完成处理

        Args:
            success: 是否成功
            message: 结果消息
        """
        # 清理工作线程
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

        # 发射完成信号
        self.install_completed.emit(success, message)
