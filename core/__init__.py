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
)

from .config import ConfigManager, get_config_manager, SceneConfigManager, get_scene_config_manager, SceneTypeManager, get_scene_type_manager

from .svg_color_mapper import (
    ElementType,
    SVGElementInfo,
    ColorMappingConfig,
    SVGElementClassifier,
    SVGColorMapper,
    create_mapping_from_palette,
    suggest_mapping_strategy,
)

from .color_data import (
    ColorSource,
    ColorSourceRegistry,
    get_color_source_registry,
    get_color_source,
    get_all_color_sources,
    get_all_palettes,
    get_random_palettes,
)

from .async_loader import BaseBatchLoader

from .grouping import GROUPING_THRESHOLDS, generate_groups, should_use_batch_loading

from .image_mediator import ImageMediator

from .color_service import ColorService, DominantColorExtractor

from .palette_service import PaletteService, PaletteImporter, PaletteExporter

from .image_service import ImageService, ProgressiveImageLoader, ColorSpaceInfo, ColorSpaceDetector

from .luminance_service import LuminanceService, LuminanceCalculator

from .preview_service import PreviewService

from .histogram_service import HistogramService, HistogramCalculator

from .cache_base import BaseCache

from .color_scheme_cache import (
    ColorSchemeCache,
    get_color_scheme_cache,
    clear_color_scheme_cache,
)

from .histogram_cache import (
    HistogramCache,
    get_histogram_cache,
    clear_histogram_cache,
    generate_image_fingerprint,
)

__all__ = [
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
    'ConfigManager',
    'get_config_manager',
    'SceneConfigManager',
    'get_scene_config_manager',
    'SceneTypeManager',
    'get_scene_type_manager',
    'ElementType',
    'SVGElementInfo',
    'ColorMappingConfig',
    'SVGElementClassifier',
    'SVGColorMapper',
    'create_mapping_from_palette',
    'suggest_mapping_strategy',
    'ColorSource',
    'ColorSourceRegistry',
    'get_color_source_registry',
    'get_color_source',
    'get_all_color_sources',
    'get_all_palettes',
    'get_random_palettes',
    'BaseBatchLoader',
    'GROUPING_THRESHOLDS',
    'generate_groups',
    'should_use_batch_loading',
    'ImageMediator',
    'ColorService',
    'DominantColorExtractor',
    'PaletteService',
    'PaletteImporter',
    'PaletteExporter',
    'ImageService',
    'ProgressiveImageLoader',
    'ColorSpaceInfo',
    'ColorSpaceDetector',
    'LuminanceService',
    'LuminanceCalculator',
    'PreviewService',
    'HistogramService',
    'HistogramCalculator',
    'BaseCache',
    'ColorSchemeCache',
    'get_color_scheme_cache',
    'clear_color_scheme_cache',
    'HistogramCache',
    'get_histogram_cache',
    'clear_histogram_cache',
    'generate_image_fingerprint',
]
