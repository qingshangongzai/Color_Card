"""工具函数模块"""

from pathlib import Path

from .icon import load_icon_universal, get_icon_path, create_fallback_icon, get_base_path
from .platform import set_app_user_model_id, fix_windows_taskbar_icon_for_window, set_window_title_bar_theme
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


__all__ = [
    'load_icon_universal',
    'get_icon_path',
    'create_fallback_icon',
    'get_base_path',
    'set_app_user_model_id',
    'fix_windows_taskbar_icon_for_window',
    'set_window_title_bar_theme',
    'calculate_grid_columns',
    'LocaleManager',
    'get_locale_manager',
    'tr',
    'set_language',
    'get_current_language',
    'get_supported_languages',
    'get_default_image_directory',
]
