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
from .interfaces import ColorExtractInterface, LuminanceExtractInterface, SettingsInterface, ColorGenerationInterface, PaletteManagementInterface, PresetColorInterface, ColorPreviewInterface
from .generation_widgets import GenerationColorInfoCard, GenerationColorPanel
from .palette_management_widgets import PaletteManagementCard, PaletteManagementList
from .preview_widgets import (
    DraggableColorDot, ColorDotBar,
    PreviewToolbar, MixedPreviewPanel,
    BaseLayout, SingleLayout, ScrollVLayout,
    ScrollHLayout, GridLayout, MixedLayout, LayoutFactory
)

__all__ = [
    # 主窗口
    'MainWindow',
    # 画布
    'BaseCanvas',
    'ImageCanvas',
    'LuminanceCanvas',
    # 卡片
    'BaseCard',
    'BaseCardPanel',
    'ColorCard',
    'ColorCardPanel',
    'LuminanceCard',
    'LuminanceCardPanel',
    # 控件
    'ColorPicker',
    'HSBColorWheel',
    'InteractiveColorWheel',
    'ZoomViewer',
    # 直方图
    'BaseHistogram',
    'LuminanceHistogramWidget',
    'RGBHistogramWidget',
    # 界面
    'ColorExtractInterface',
    'LuminanceExtractInterface',
    'SettingsInterface',
    'ColorGenerationInterface',
    'PaletteManagementInterface',
    'PresetColorInterface',
    'ColorPreviewInterface',
    # 配色生成组件
    'GenerationColorInfoCard',
    'GenerationColorPanel',
    # 配色管理组件
    'PaletteManagementCard',
    'PaletteManagementList',
    # 配色预览组件
    'DraggableColorDot',
    'ColorDotBar',
    'PreviewToolbar',
    'MixedPreviewPanel',
    # 布局系统
    'BaseLayout',
    'SingleLayout',
    'ScrollVLayout',
    'ScrollHLayout',
    'GridLayout',
    'MixedLayout',
    'LayoutFactory',
]
