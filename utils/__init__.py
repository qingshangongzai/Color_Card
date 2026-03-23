"""工具函数模块"""

# 标准库导入
from pathlib import Path

# 第三方库导入
from PySide6.QtCore import QSettings

# 项目模块导入
from .icon import load_icon_universal, get_icon_path, create_fallback_icon, get_base_path
from .platform import set_app_user_model_id, fix_windows_taskbar_icon_for_window, force_window_to_front
from .layout import calculate_grid_columns
from .locale import (
    LocaleManager,
    get_locale_manager,
    tr,
    set_language,
    get_current_language,
    get_supported_languages,
)


def get_default_image_directory() -> str:
    """获取默认图片导入目录

    Returns:
        str: 用户图片文件夹路径
    """
    return str(Path.home() / "Pictures")


def get_default_data_directory() -> str:
    """获取默认数据文件目录（用于导入/导出配色数据）

    Returns:
        str: 用户文档文件夹路径
    """
    return str(Path.home() / "Documents")


def get_last_directory(key: str, default_dir: str) -> str:
    """获取用户上次选择的目录

    Args:
        key: 存储键名（区分不同功能）
        default_dir: 默认目录（首次使用或记录不存在时返回）

    Returns:
        str: 上次选择的目录或默认目录
    """
    settings = QSettings("ColorCard", "App")
    last_dir = settings.value(f"last_directory/{key}", default_dir)
    if last_dir and Path(last_dir).exists():
        return str(last_dir)
    return default_dir


def set_last_directory(key: str, directory: str):
    """记录用户选择的目录

    Args:
        key: 存储键名
        directory: 用户选择的目录路径
    """
    settings = QSettings("ColorCard", "App")
    settings.setValue(f"last_directory/{key}", directory)


__all__ = [
    'load_icon_universal',
    'get_icon_path',
    'create_fallback_icon',
    'get_base_path',
    'set_app_user_model_id',
    'fix_windows_taskbar_icon_for_window',
    'force_window_to_front',
    'calculate_grid_columns',
    'LocaleManager',
    'get_locale_manager',
    'tr',
    'set_language',
    'get_current_language',
    'get_supported_languages',
    'get_default_image_directory',
    'get_default_data_directory',
    'get_last_directory',
    'set_last_directory',
]
