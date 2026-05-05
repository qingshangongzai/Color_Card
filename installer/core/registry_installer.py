# 标准库导入
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Windows 注册表支持
if sys.platform == 'win32':
    import winreg

# 项目模块导入
from core import get_logger
from version import version_manager

logger = get_logger("installer.registry_installer")

# 应用 GUID
APP_ID = "{8EBD3944-B989-4878-B943-DE4558FDF22C}"

# 注册表路径
REGISTRY_KEY = r"Software\Color Card"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"


class RegistryInstaller:
    """注册表安装器

    负责写入和删除安装信息到 Windows 注册表。
    """

    def __init__(self, test_mode: bool = False):
        """初始化注册表安装器

        Args:
            test_mode: 测试模式，不实际写入注册表
        """
        self._test_mode = test_mode

    def write_install_info(self, config: dict[str, Any]) -> bool:
        """写入安装信息到注册表

        Args:
            config: 安装配置
                - install_path: 安装路径

        Returns:
            bool: 是否成功
        """
        if self._test_mode:
            logger.info("测试模式：跳过注册表写入")
            return True

        if sys.platform != 'win32':
            logger.warning("非 Windows 平台：跳过注册表写入")
            return True

        try:
            # 创建或打开注册表键
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                REGISTRY_KEY,
                0,
                winreg.KEY_WRITE
            )

            with key:
                # 写入安装信息
                winreg.SetValueEx(key, "AppId", 0, winreg.REG_SZ, APP_ID)
                winreg.SetValueEx(key, "InstallPath", 0, winreg.REG_SZ, str(config['install_path']))
                winreg.SetValueEx(key, "Version", 0, winreg.REG_SZ, version_manager.version)
                winreg.SetValueEx(key, "CompanyName", 0, winreg.REG_SZ, version_manager.app_info['company'])

            logger.info(f"注册表写入成功: {REGISTRY_KEY}")
            return True

        except (OSError, PermissionError) as e:
            logger.error(f"注册表写入失败: {str(e)}")
            return False

    def write_uninstall_entry(self, config: dict[str, Any]) -> bool:
        """写入控制面板卸载条目

        Args:
            config: 安装配置
                - install_path: 安装路径
                - install_size_kb: 安装大小（KB）

        Returns:
            bool: 是否成功
        """
        if self._test_mode:
            logger.info("测试模式：跳过卸载条目写入")
            return True

        if sys.platform != 'win32':
            logger.warning("非 Windows 平台：跳过卸载条目写入")
            return True

        try:
            install_path = Path(config['install_path'])
            exe_path = install_path / "Color Card.exe"

            # 创建或打开卸载键
            uninstall_key_path = f"{UNINSTALL_KEY}\\{APP_ID}"
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                uninstall_key_path,
                0,
                winreg.KEY_WRITE
            )

            with key:
                # 写入卸载信息
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ,
                                  f"{version_manager.app_info['name']} - {version_manager.app_info['name_en']}")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version_manager.version)
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, version_manager.app_info['company'])
                winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ,
                                  datetime.now().strftime("%Y%m%d"))
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_path))
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                                  f'"{str(exe_path)}" --uninstall')
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe_path))

                # 写入安装大小（如果提供）
                if 'install_size_kb' in config:
                    winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD,
                                      int(config['install_size_kb']))

            logger.info(f"卸载条目写入成功: {uninstall_key_path}")
            return True

        except (OSError, PermissionError) as e:
            logger.error(f"卸载条目写入失败: {str(e)}")
            return False

    def remove_install_info(self) -> bool:
        """删除安装信息

        Returns:
            bool: 是否成功
        """
        if sys.platform != 'win32':
            return True

        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            logger.info(f"注册表删除成功: {REGISTRY_KEY}")
            return True
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"注册表删除失败: {str(e)}")
            return False

    def remove_uninstall_entry(self) -> bool:
        """删除卸载条目

        Returns:
            bool: 是否成功
        """
        if sys.platform != 'win32':
            return True

        try:
            uninstall_key_path = f"{UNINSTALL_KEY}\\{APP_ID}"
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, uninstall_key_path)
            logger.info(f"卸载条目删除成功: {uninstall_key_path}")
            return True
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"卸载条目删除失败: {str(e)}")
            return False

    def get_install_path(self) -> Path | None:
        """从注册表获取安装路径

        Returns:
            Path | None: 安装路径，未找到返回 None
        """
        if sys.platform != 'win32':
            return None

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            with key:
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                return Path(install_path) if install_path else None
        except (OSError, FileNotFoundError):
            return None
