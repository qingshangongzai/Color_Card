"""核心功能模块"""

from .color import (
    rgb_to_hsb,
    rgb_to_lab,
    rgb_to_hex,
    hex_to_rgb,
    rgb_to_hsl,
    rgb_to_cmyk,
    hsb_to_rgb,
    get_color_info,
    get_luminance,
    get_zone,
    get_zone_bounds,
    calculate_histogram,
    calculate_rgb_histogram,
    generate_monochromatic,
    generate_analogous,
    generate_complementary,
    generate_split_complementary,
    generate_double_complementary,
    adjust_brightness,
    get_scheme_preview_colors,
    # RYB 色彩空间支持
    rgb_hue_to_ryb_hue,
    ryb_hue_to_rgb_hue,
    generate_ryb_monochromatic,
    generate_ryb_analogous,
    generate_ryb_complementary,
    generate_ryb_split_complementary,
    generate_ryb_double_complementary,
    get_scheme_preview_colors_ryb,
    # MMCQ 主色调提取
    extract_dominant_colors,
    find_dominant_color_positions,
)

from .config import ConfigManager, get_config_manager

__all__ = [
    # 颜色函数
    'rgb_to_hsb',
    'rgb_to_lab',
    'rgb_to_hex',
    'hex_to_rgb',
    'rgb_to_hsl',
    'rgb_to_cmyk',
    'hsb_to_rgb',
    'get_color_info',
    'get_luminance',
    'get_zone',
    'get_zone_bounds',
    'calculate_histogram',
    'calculate_rgb_histogram',
    # 配色方案函数
    'generate_monochromatic',
    'generate_analogous',
    'generate_complementary',
    'generate_split_complementary',
    'generate_double_complementary',
    'adjust_brightness',
    'get_scheme_preview_colors',
    # RYB 色彩空间支持
    'rgb_hue_to_ryb_hue',
    'ryb_hue_to_rgb_hue',
    'generate_ryb_monochromatic',
    'generate_ryb_analogous',
    'generate_ryb_complementary',
    'generate_ryb_split_complementary',
    'generate_ryb_double_complementary',
    'get_scheme_preview_colors_ryb',
    # MMCQ 主色调提取
    'extract_dominant_colors',
    'find_dominant_color_positions',
    # 配置
    'ConfigManager',
    'get_config_manager',
]
