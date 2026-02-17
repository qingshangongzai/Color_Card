"""UI模块，统一导出所有UI相关的类和函数"""

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
from .color_extract import ColorExtractInterface
from .luminance_extract import LuminanceExtractInterface
from .color_generation import ColorGenerationInterface, GenerationColorInfoCard, GenerationColorPanel
from .palette_management import (
    PaletteManagementInterface,
    PaletteManagementCard, PaletteManagementList,
    PaletteManagementColorCard
)
from .preset_color import PresetColorInterface
from .settings import SettingsInterface
from .color_preview import (
    ColorPreviewInterface,
    DraggableColorDot, ColorDotBar,
    PreviewToolbar, MixedPreviewPanel,
    BaseLayout, SingleLayout, ScrollVLayout,
    ScrollHLayout, GridLayout, MixedLayout, LayoutFactory
)

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
    'ColorExtractInterface',
    'LuminanceExtractInterface',
    'SettingsInterface',
    'ColorGenerationInterface',
    'PaletteManagementInterface',
    'PresetColorInterface',
    'ColorPreviewInterface',
    'GenerationColorInfoCard',
    'GenerationColorPanel',
    'PaletteManagementCard',
    'PaletteManagementList',
    'PaletteManagementColorCard',
    'DraggableColorDot',
    'ColorDotBar',
    'PreviewToolbar',
    'MixedPreviewPanel',
    'BaseLayout',
    'SingleLayout',
    'ScrollVLayout',
    'ScrollHLayout',
    'GridLayout',
    'MixedLayout',
    'LayoutFactory',
]
