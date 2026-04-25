# 标准库导入
import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

# Windows 注册表支持
if sys.platform == 'win32':
    import winreg

# 创建模块级日志记录器
_logger = logging.getLogger("color_card.app_mode")


class AppMode(Enum):
    """应用运行模式"""
    DEVELOPMENT = "development"
    INSTALLER = "installer"
    INSTALLED = "installed"
    PORTABLE = "portable"


class Platform(Enum):
    """平台类型"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


# 缓存检测结果
_mode_cache: Optional[AppMode] = None
_platform_cache: Optional[Platform] = None


def _check_registry_install() -> Optional[Path]:
    """从注册表检查安装路径

    Returns:
        Optional[Path]: 安装路径，未找到返回 None
    """
    if sys.platform != 'win32':
        return None

    # 尝试读取注册表
    registry_paths = [
        # 当前用户（优先）
        (winreg.HKEY_CURRENT_USER, r"Software\Color Card"),
        # 本地机器（需要管理员权限安装）
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Color Card"),
        # 32位程序在64位系统上
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Color Card"),
    ]

    for hkey, key_path in registry_paths:
        try:
            with winreg.OpenKey(hkey, key_path) as key:
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                if install_path and os.path.exists(install_path):
                    return Path(install_path)
        except (OSError, FileNotFoundError):
            continue

    return None


def detect_mode() -> AppMode:
    """检测应用运行模式

    Returns:
        AppMode: 运行模式枚举值
    """
    global _mode_cache
    if _mode_cache is not None:
        return _mode_cache

    # 调试信息
    is_nuitka = "__compiled__" in globals()
    _logger.debug(f"__compiled__={is_nuitka}")
    _logger.debug(f"sys.frozen={getattr(sys, 'frozen', False)}")
    _logger.debug(f"sys.argv[0]={sys.argv[0]}")
    _logger.debug(f"sys.executable={sys.executable}")

    # 非打包环境 = 开发模式（Nuitka 使用 __compiled__ 标记）
    if not getattr(sys, 'frozen', False) and "__compiled__" not in globals():
        _mode_cache = AppMode.DEVELOPMENT
        _logger.info(f"运行模式判定: 开发模式")
        return _mode_cache

    exe_path = Path(sys.argv[0]).resolve()
    temp = os.environ.get('TEMP', '').lower()

    _logger.debug(f"exe_path={exe_path}")
    _logger.debug(f"TEMP={temp}")

    # Nuitka 单文件模式：使用 __compiled__ 标记检测
    # Nuitka 单文件运行时也会解压到临时目录，但不能误判为安装程序模式
    if is_nuitka:
        # Nuitka 单文件模式下，配置目录应该使用用户主目录（与安装版相同）
        _mode_cache = AppMode.INSTALLED
        _logger.info(f"运行模式判定: 安装版（Nuitka 单文件）")
        return _mode_cache

    # 在临时目录运行 = 安装程序运行中（仅适用于非 Nuitka 环境）
    if temp and str(exe_path).lower().startswith(temp):
        _mode_cache = AppMode.INSTALLER
        _logger.info(f"运行模式判定: 安装程序模式")
        return _mode_cache

    # 检查注册表（Windows 安装版）
    if sys.platform == 'win32':
        reg_install_path = _check_registry_install()
        _logger.debug(f"注册表安装路径={reg_install_path}")
        if reg_install_path:
            # 检查当前 exe 是否在注册表记录的安装目录下
            try:
                exe_relative = exe_path.relative_to(reg_install_path)
                # 成功相对化，说明在安装目录内
                _mode_cache = AppMode.INSTALLED
                _logger.info(f"运行模式判定: 安装版（注册表匹配）")
                return _mode_cache
            except ValueError:
                # 不在注册表记录的安装目录中
                _logger.debug(f"不在注册表记录的安装目录中")
                pass

    # 在系统目录运行 = 安装版（备用检测）
    system_paths = [
        os.environ.get('PROGRAMFILES', '').lower(),
        os.environ.get('PROGRAMFILES(X86)', '').lower(),
        os.environ.get('LOCALAPPDATA', '').lower(),
    ]
    for path in system_paths:
        if path and path in str(exe_path).lower():
            _mode_cache = AppMode.INSTALLED
            _logger.info(f"运行模式判定: 安装版（系统目录匹配）")
            return _mode_cache

    # 其他情况 = 便携版
    _mode_cache = AppMode.PORTABLE
    _logger.info(f"运行模式判定: 便携版")
    return _mode_cache


def get_app_mode() -> AppMode:
    """获取应用运行模式（带缓存）

    Returns:
        AppMode: 运行模式枚举值
    """
    return detect_mode()


def get_config_dir() -> Path:
    """获取配置目录

    根据运行模式返回不同的配置目录：
    - 安装版/开发模式: ~/.color_card/
    - 便携版/安装程序: 程序目录/config/

    Returns:
        Path: 配置目录路径
    """
    mode = detect_mode()

    if mode in (AppMode.INSTALLED, AppMode.DEVELOPMENT):
        config_path = Path.home() / ".color_card"
        _logger.info(f"配置目录={config_path}（安装版/开发模式）")
        return config_path
    else:
        config_path = Path(sys.argv[0]).parent / "config"
        _logger.info(f"配置目录={config_path}（便携版/安装程序）")
        return config_path


def detect_platform() -> Platform:
    """检测运行平台

    Returns:
        Platform: 平台类型枚举值
    """
    global _platform_cache
    if _platform_cache is not None:
        return _platform_cache

    if sys.platform == 'win32':
        _platform_cache = Platform.WINDOWS
    elif sys.platform == 'darwin':
        _platform_cache = Platform.MACOS
    elif sys.platform.startswith('linux'):
        _platform_cache = Platform.LINUX
    else:
        _platform_cache = Platform.UNKNOWN

    return _platform_cache


def get_platform() -> Platform:
    """获取运行平台（带缓存）

    Returns:
        Platform: 平台类型枚举值
    """
    return detect_platform()



