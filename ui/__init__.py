"""UI模块，统一导出所有UI相关的类和函数"""

# 基础组件立即导出
from .main_window import MainWindow
from .canvases import BaseCanvas, ImageCanvas, LuminanceCanvas
from .cards import (
    BaseCard, BaseCardPanel,
    ColorCard, ColorCardPanel,
    LuminanceCard, LuminanceCardPanel
)
from .histograms import (
    BaseHistogram,
    LuminanceHistogramWidget,
    RGBHistogramWidget
)
from .color_picker import ColorPicker
from .color_wheel import HSBColorWheel, InteractiveColorWheel
from .zoom_viewer import ZoomViewer


# 界面类延迟导入函数
def get_color_extract_interface():
    """获取色彩提取界面类（延迟导入）"""
    from .color_extract import ColorExtractInterface
    return ColorExtractInterface


def get_luminance_extract_interface():
    """获取明度提取界面类（延迟导入）"""
    from .luminance_extract import LuminanceExtractInterface
    return LuminanceExtractInterface


def get_gradient_extract_interface():
    """获取渐变提取界面类（延迟导入）"""
    from .gradient_extract import GradientExtractInterface
    return GradientExtractInterface


def get_color_generation_interface():
    """获取配色生成界面类（延迟导入）"""
    from .color_generation import ColorGenerationInterface
    return ColorGenerationInterface


def get_palette_management_interface():
    """获取配色管理界面类（延迟导入）"""
    from .palette_management import PaletteManagementInterface
    return PaletteManagementInterface


def get_preset_color_interface():
    """获取内置色彩界面类（延迟导入）"""
    from .preset_color import PresetColorInterface
    return PresetColorInterface


def get_settings_interface():
    """获取设置界面类（延迟导入）"""
    from .settings import SettingsInterface
    return SettingsInterface


def get_color_preview_interface():
    """获取配色预览界面类（延迟导入）"""
    from .color_preview import ColorPreviewInterface
    return ColorPreviewInterface


__all__ = [
    'MainWindow',
    'BaseCanvas',
    'ImageCanvas',
    'LuminanceCanvas',
    'BaseCard',
    'BaseCardPanel',
    'ColorCard',
    'ColorCardPanel',
    'LuminanceCard',
    'LuminanceCardPanel',
    'ColorPicker',
    'HSBColorWheel',
    'InteractiveColorWheel',
    'ZoomViewer',
    'BaseHistogram',
    'LuminanceHistogramWidget',
    'RGBHistogramWidget',
    # 延迟导入函数
    'get_color_extract_interface',
    'get_luminance_extract_interface',
    'get_gradient_extract_interface',
    'get_color_generation_interface',
    'get_palette_management_interface',
    'get_preset_color_interface',
    'get_settings_interface',
    'get_color_preview_interface',
]
