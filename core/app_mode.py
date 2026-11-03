"""应用运行模式检测（实现位于项目根目录 app_mode.py，供启动器等轻量入口复用）"""

# 项目模块导入
from app_mode import (
    AppMode,
    Platform,
    detect_mode,
    detect_platform,
    get_app_mode,
    get_config_dir,
    get_platform,
)

__all__ = [
    'AppMode',
    'Platform',
    'detect_mode',
    'detect_platform',
    'get_app_mode',
    'get_config_dir',
    'get_platform',
]
