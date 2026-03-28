"""核心功能模块"""

# 启动必需的模块立即导入
from .config import ConfigManager, get_config_manager, SceneConfigManager, get_scene_config_manager, SceneTypeManager, get_scene_type_manager, ConfigLoadError

from .app_mode import (
    AppMode,
    Platform,
    detect_mode,
    get_app_mode,
    get_config_dir,
    detect_platform,
    get_platform,
    is_portable_mode,
    is_installed_mode,
    is_development_mode,
)

from .logger import (
    LoggerManager,
    get_logger_manager,
    get_logger,
    log_user_action,
    log_performance,
)

# 颜色工具函数（轻量级，立即导入）
from .color import (
    rgb_to_hsb,
    rgb_to_lab,
    rgb_to_hex,
    hex_to_rgb,
    rgb_to_hsl,
    rgb_to_cmyk,
    hsb_to_rgb,
    lab_to_rgb,
    hsl_to_rgb,
    cmyk_to_rgb,
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
    rgb_hue_to_ryb_hue,
    ryb_hue_to_rgb_hue,
    generate_ryb_monochromatic,
    generate_ryb_analogous,
    generate_ryb_complementary,
    generate_ryb_split_complementary,
    generate_ryb_double_complementary,
    get_scheme_preview_colors_ryb,
    extract_dominant_colors,
    find_dominant_color_positions,
    ZONE_WIDTH,
)

# 配色数据（已优化为延迟加载）
from .color_data import (
    ColorSource,
    ColorSourceRegistry,
    get_color_source_registry,
    get_color_source,
    get_all_color_sources,
    get_all_palettes,
    get_random_palettes,
)

# 其他工具类（轻量级，立即导入）
from .gradient import (
    generate_gradient,
    generate_random_gradient,
)

from .async_loader import BaseBatchLoader
from .grouping import GROUPING_THRESHOLDS, generate_groups, should_use_batch_loading
from .image_mediator import ImageMediator
from .cache_base import BaseCache

# UI直接使用的服务类（轻量级，立即导入）
from .histogram_service import HistogramService, HistogramCalculator
from .preview_service import PreviewService
from .luminance_service import LuminanceService, LuminanceCalculator


# 重量级服务类延迟导入（启动时不需要立即加载）
def get_color_service():
    """获取颜色服务（延迟导入）"""
    from .color_service import ColorService
    return ColorService()


def get_palette_service():
    """获取配色服务（延迟导入）"""
    from .palette_service import PaletteService
    return PaletteService()


def get_image_service():
    """获取图片服务（延迟导入）"""
    from .image_service import ImageService
    return ImageService()


def get_service_factory():
    """获取服务工厂（延迟导入）"""
    from .service_factory import ServiceFactory
    return ServiceFactory()


def get_svg_color_mapper():
    """获取SVG颜色映射器（延迟导入）"""
    from .svg_color_mapper import SVGColorMapper
    return SVGColorMapper()


__all__ = [
    # 颜色工具函数
    'generate_gradient',
    'generate_random_gradient',
    'rgb_to_hsb',
    'rgb_to_lab',
    'rgb_to_hex',
    'hex_to_rgb',
    'rgb_to_hsl',
    'rgb_to_cmyk',
    'hsb_to_rgb',
    'lab_to_rgb',
    'hsl_to_rgb',
    'cmyk_to_rgb',
    'get_color_info',
    'get_luminance',
    'get_zone',
    'get_zone_bounds',
    'calculate_histogram',
    'calculate_rgb_histogram',
    'generate_monochromatic',
    'generate_analogous',
    'generate_complementary',
    'generate_split_complementary',
    'generate_double_complementary',
    'adjust_brightness',
    'get_scheme_preview_colors',
    'rgb_hue_to_ryb_hue',
    'ryb_hue_to_rgb_hue',
    'generate_ryb_monochromatic',
    'generate_ryb_analogous',
    'generate_ryb_complementary',
    'generate_ryb_split_complementary',
    'generate_ryb_double_complementary',
    'get_scheme_preview_colors_ryb',
    'extract_dominant_colors',
    'find_dominant_color_positions',
    'ZONE_WIDTH',
    # 配置管理
    'ConfigManager',
    'get_config_manager',
    'SceneConfigManager',
    'get_scene_config_manager',
    'SceneTypeManager',
    'get_scene_type_manager',
    'ConfigLoadError',
    # 应用模式
    'AppMode',
    'Platform',
    'detect_mode',
    'get_app_mode',
    'get_config_dir',
    'detect_platform',
    'get_platform',
    'is_portable_mode',
    'is_installed_mode',
    'is_development_mode',
    # 配色数据
    'ColorSource',
    'ColorSourceRegistry',
    'get_color_source_registry',
    'get_color_source',
    'get_all_color_sources',
    'get_all_palettes',
    'get_random_palettes',
    # 工具类
    'BaseBatchLoader',
    'GROUPING_THRESHOLDS',
    'generate_groups',
    'should_use_batch_loading',
    'ImageMediator',
    'BaseCache',
    # 日志
    'LoggerManager',
    'get_logger_manager',
    'get_logger',
    'log_user_action',
    'log_performance',
    # UI直接使用的服务类
    'HistogramService',
    'HistogramCalculator',
    'PreviewService',
    'LuminanceService',
    'LuminanceCalculator',
    # 延迟加载的服务类（通过函数访问）
    'get_color_service',
    'get_palette_service',
    'get_image_service',
    'get_service_factory',
    'get_svg_color_mapper',
]
