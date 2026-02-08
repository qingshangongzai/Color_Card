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
from .interfaces import ColorExtractInterface, LuminanceExtractInterface, SettingsInterface, ColorSchemeInterface, FavoritesInterface
from .scheme_widgets import SchemeColorInfoCard, SchemeColorPanel
from .favorite_widgets import FavoriteSchemeCard, FavoriteSchemeList

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
    'ColorSchemeInterface',
    'FavoritesInterface',
    # 配色方案组件
    'SchemeColorInfoCard',
    'SchemeColorPanel',
    # 收藏组件
    'FavoriteSchemeCard',
    'FavoriteSchemeList',
]
