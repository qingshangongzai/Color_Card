"""核心功能模块"""

from .color import (
    rgb_to_hsb,
    rgb_to_lab,
    rgb_to_hex,
    rgb_to_hsl,
    rgb_to_cmyk,
    get_color_info,
    get_luminance,
    get_zone,
    get_zone_bounds,
    calculate_histogram,
    calculate_rgb_histogram,
)

from .config import ConfigManager, get_config_manager

__all__ = [
    # 颜色函数
    'rgb_to_hsb',
    'rgb_to_lab',
    'rgb_to_hex',
    'rgb_to_hsl',
    'rgb_to_cmyk',
    'get_color_info',
    'get_luminance',
    'get_zone',
    'get_zone_bounds',
    'calculate_histogram',
    'calculate_rgb_histogram',
    # 配置
    'ConfigManager',
    'get_config_manager',
]
