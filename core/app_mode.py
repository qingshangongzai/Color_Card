# 标准库导入
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional


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


def detect_mode() -> AppMode:
    """检测应用运行模式

    Returns:
        AppMode: 运行模式枚举值
    """
    global _mode_cache
    if _mode_cache is not None:
        return _mode_cache

    # 非打包环境 = 开发模式
    if not getattr(sys, 'frozen', False):
        _mode_cache = AppMode.DEVELOPMENT
        return _mode_cache

    exe_path = sys.executable.lower()
    temp = os.environ.get('TEMP', '').lower()

    # 在临时目录运行 = 安装程序运行中
    if temp and exe_path.startswith(temp):
        _mode_cache = AppMode.INSTALLER
        return _mode_cache

    # 在系统目录运行 = 安装版
    system_paths = [
        os.environ.get('PROGRAMFILES', '').lower(),
        os.environ.get('PROGRAMFILES(X86)', '').lower(),
        os.environ.get('LOCALAPPDATA', '').lower(),
    ]
    for path in system_paths:
        if path and path in exe_path:
            _mode_cache = AppMode.INSTALLED
            return _mode_cache

    # 其他情况 = 便携版
    _mode_cache = AppMode.PORTABLE
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
        return Path.home() / ".color_card"
    else:
        return Path(sys.executable).parent / "config"


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


def is_portable_mode() -> bool:
    """是否为便携模式

    Returns:
        bool: 便携模式返回True
    """
    return detect_mode() == AppMode.PORTABLE


def is_installed_mode() -> bool:
    """是否为安装版模式

    Returns:
        bool: 安装版返回True
    """
    return detect_mode() == AppMode.INSTALLED


def is_development_mode() -> bool:
    """是否为开发模式

    Returns:
        bool: 开发模式返回True
    """
    return detect_mode() == AppMode.DEVELOPMENT
