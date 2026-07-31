"""色彩分布分析对话框（阶段 3b）

与明度分析对话框（tone_analysis_dialog）同构的一对：一个管明度、一个管色彩。
core 引擎输出 label_key + label_args，本对话框负责翻译成文案并渲染，
图表控件只接收已翻译的视图模型，业务判定全部留在 core。
"""

from __future__ import annotations

import sys

import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
)
from qfluentwidgets import BodyLabel, qconfig

from core import analyze_color_distribution, get_color_distribution_cache
from core.color_distribution import hue_name
from utils import tr

from .base_frameless_dialog import BaseFramelessDialog
from .tone_analysis_dialog import StatCard
from ui.color_distribution_charts import (
    DominantColorsBarWidget, HueWheelWidget, ZoneToningBarWidget
)

# 感知色名 id：属 color_distribution.pname_* 词条，其余色名 id 回落 color_wheel.hue_*
_PNAME_IDS = ('gray', 'warm_gray', 'blue_gray', 'brown', 'pink')


class AnalysisWorker(QThread):
    """色彩分布分析工作线程"""
    analysis_complete = Signal(object, object)  # result, img_array

    def __init__(self, img_array: np.ndarray):
        super().__init__()
        self._img_array = img_array
        self._is_running = True

    def stop(self) -> None:
        """标记停止，阻止分析完成后向已关闭的对话框发信号"""
        self._is_running = False

    def run(self) -> None:
        """执行分析"""
        result = analyze_color_distribution(self._img_array)
        if self._is_running:
            self.analysis_complete.emit(result, self._img_array)


class ImagePreviewWidget(QWidget):
    """原图预览（单图等比缩放）"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: transparent;")
        self._label.setMinimumSize(100, 100)
        layout.addWidget(self._label)

        self._img_rgb: np.ndarray | None = None

    def set_image(self, img_rgb: np.ndarray) -> None:
        """设置图片（RGB uint8 数组）"""
        self._img_rgb = img_rgb
        self._update_display()

    def _update_display(self) -> None:
        if self._img_rgb is None:
            return
        h, w = self._img_rgb.shape[:2]
        display_w = max(self.width() - 10, 100)
        display_h = max(self.height() - 10, 100)

        q_image = QImage(self._img_rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image).scaled(
            display_w, display_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._label.setPixmap(pixmap)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_display()


class ColorDistributionDialog(BaseFramelessDialog):
    """色彩分布分析对话框"""

    def __init__(self, img_array: np.ndarray | None, image_key: str | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._img_array = img_array
        self._image_key = image_key
        self._worker: AnalysisWorker | None = None
        self._stat_cards: list[StatCard] = []

        self.setWindowTitle(tr('color_distribution.dialog_title'))
        self.setMinimumSize(900, 600)
        self.resize(1100, 750)

        # 显示标题栏的最大化和最小化按钮（FramelessDialog 默认隐藏）
        self.titleBar.minBtn.show()
        self.titleBar.maxBtn.show()
        self.titleBar.setDoubleClickEnabled(True)

        # 恢复最大化按钮样式（FramelessDialog 初始化时禁用了）
        if sys.platform == 'win32':
            import win32con
            import win32gui
            hWnd = int(self.winId())
            style = win32gui.GetWindowLong(hWnd, win32con.GWL_STYLE)
            win32gui.SetWindowLong(hWnd, win32con.GWL_STYLE, style | win32con.WS_MAXIMIZEBOX)

        self._setup_ui()
        self._update_styles()

        self._theme_connection = qconfig.themeChangedFinished.connect(self._on_theme_changed)

        if self._img_array is not None:
            self.start_analysis()

        self._enable_show()

    def _setup_ui(self) -> None:
        """设置界面（三段式：顶部图表行 + 中部图表行 + 卡片网格）"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 40, 20, 10)
        main_layout.setSpacing(8)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # 加载中标签
        self._loading_label = BodyLabel(tr('color_distribution.loading'), self)
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self._loading_label)

        # 图表区（初始隐藏）
        self._charts_widget = QWidget(self)
        self._charts_widget.hide()
        charts_layout = QVBoxLayout(self._charts_widget)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(10)

        # 顶部行：原图预览 + 色轮密度图
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)
        self._preview = ImagePreviewWidget()
        self._wheel_chart = HueWheelWidget()
        top_layout.addWidget(self._preview, stretch=1)
        top_layout.addWidget(self._wheel_chart, stretch=1)
        charts_layout.addWidget(top_widget, stretch=4)

        # 中部行：分区调色条 + 主色卡条
        mid_widget = QWidget()
        mid_layout = QHBoxLayout(mid_widget)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(10)
        self._zone_chart = ZoneToningBarWidget()
        self._palette_chart = DominantColorsBarWidget()
        mid_layout.addWidget(self._zone_chart, stretch=1)
        mid_layout.addWidget(self._palette_chart, stretch=1)
        charts_layout.addWidget(mid_widget, stretch=5)

        content_layout.addWidget(self._charts_widget, stretch=1)

        # 统计卡片区域（初始隐藏）
        self._stats_widget = QWidget(self)
        self._stats_widget.hide()
        stats_layout: QGridLayout = QGridLayout(self._stats_widget)
        stats_layout.setSpacing(12)
        content_layout.addWidget(self._stats_widget)

        main_layout.addWidget(content_widget)

    def start_analysis(self) -> None:
        """开始分析（先查缓存，未命中起线程）"""
        if self._img_array is None:
            return

        if self._image_key:
            cache = get_color_distribution_cache()
            cached_result = cache.get(self._image_key)
            if cached_result is not None:
                self._display_result(cached_result, self._img_array)
                return

        self._worker = AnalysisWorker(self._img_array)
        self._worker.analysis_complete.connect(self._on_analysis_complete)
        self._worker.start()

    def _on_analysis_complete(self, result: dict, img_array: np.ndarray) -> None:
        """分析完成回调"""
        if self._image_key:
            get_color_distribution_cache().set(self._image_key, result)

        self._display_result(result, img_array)

        if self._worker:
            self._worker.deleteLater()
            self._worker = None

    def _display_result(self, result: dict, img_array: np.ndarray) -> None:
        """显示分析结果"""
        self._loading_label.hide()

        self._preview.set_image(img_array)
        self._wheel_chart.update_data(result['wheel'], self._wheel_axis_labels())
        self._zone_chart.update_data(self._zones_view(result['zones']))
        self._palette_chart.update_data(self._palette_view(result['palette']))
        self._charts_widget.show()

        self._create_stat_cards(result)
        self._stats_widget.show()

    # ==================== label_key → 已翻译文案 ====================

    @staticmethod
    def _pname_text(pid: str) -> str:
        """感知色名 id 译文（5 个专属 pname，其余回落 12 色相名）"""
        if pid in _PNAME_IDS:
            return tr(f'color_distribution.pname_{pid}')
        return tr(f'color_wheel.hue_{pid}')

    def _cast_text(self, cast: dict) -> str:
        """色偏结论文案（含方向/级别参数与低置信后缀）"""
        args = cast['label_args']
        if args:
            direction = '、'.join(
                tr(f'color_distribution.dir_{d}') for d in args['direction'])
            text = tr(f'color_distribution.{cast["label_key"]}',
                      level=tr(f'color_distribution.level_{args["level"]}'),
                      direction=direction)
        else:
            text = tr(f'color_distribution.{cast["label_key"]}')
        if 0.0 < cast['confidence'] < 1.0:
            text += tr('color_distribution.low_confidence_suffix')
        return text

    @staticmethod
    def _harmony_text(result: dict) -> str:
        """配色结构文案（附置信度百分比，仿影调类型卡）"""
        base = tr(f'color_distribution.{result["harmony"]}')
        confidence = result['harmony_fit']['confidence']
        return f'{base} ({int(confidence * 100)}%)'

    @staticmethod
    def _style_text(style: dict | None) -> str:
        """调色风格文案（无风格时显示占位词条）"""
        if style is None:
            return tr('color_distribution.style_none')
        args = style['label_args']
        kwargs = {}
        for key in ('dark', 'bright', 'hue'):
            if key in args:
                kwargs[key] = tr(f'color_wheel.hue_{args[key]}')
        return tr(f'color_distribution.{style["label_key"]}', **kwargs)

    @staticmethod
    def _warmth_text(warmth: dict) -> str:
        """冷暖倾向文案（档名 + 连续值）"""
        label = tr(f'color_distribution.{warmth["label_key"]}')
        return f'{label} ({warmth["value"]:+.2f})'

    def _zone_text(self, zone: dict) -> str:
        """分区状态文案（卡片用，卡片标题已含分区名）"""
        args = zone['label_args']
        kwargs = {}
        if 'hue' in args:
            kwargs['hue'] = tr(f'color_wheel.hue_{args["hue"]}')
        text = tr(f'color_distribution.{zone["label_key"]}', **kwargs)
        if zone.get('mix'):
            text += tr('color_distribution.zone_mix_suffix')
        return text

    @staticmethod
    def _chroma_text(chroma_dist: dict) -> str:
        """饱和度文案（彩度分档 · 彩色度分档，分隔符拼两个已译词条）"""
        chroma = tr(f'color_distribution.{chroma_dist["label_key"]}')
        colorfulness = tr(f'color_distribution.{chroma_dist["colorfulness_key"]}')
        return f'{chroma} · {colorfulness}'

    # ==================== 图表视图模型 ====================

    @staticmethod
    def _wheel_axis_labels() -> list[str]:
        """色轮四方位（0°/90°/180°/270°）翻译后的色名"""
        return [tr(f'color_wheel.hue_{hue_name(deg)}') for deg in (0, 90, 180, 270)]

    def _zones_view(self, zones: dict) -> dict:
        """分区调色条视图模型（文案已翻译）"""
        zone_views = []
        for key in ('dark', 'mid', 'bright'):
            zone = zones[key]
            composition = []
            for c in zone['composition']:
                lo, hi = c['range']
                line1 = f'{self._pname_text(c["pname"])} {lo:.0f}°~{hi % 360:.0f}°'
                if c['weight_pct'] < 1.0:
                    line2 = tr('color_distribution.area', pct=int(round(c['area_pct'])))
                else:
                    line2 = f'{c["weight_pct"]:.0f}%'
                composition.append({
                    'hue': c['hue'], 'range': c['range'],
                    'weight_pct': c['weight_pct'], 'line1': line1, 'line2': line2,
                })
            zone_views.append({
                'key': key,
                'name_text': tr(f'color_distribution.zone_{key}'),
                'chroma': zone['chroma'],
                'is_empty': zone['pixel_pct'] < 0.05,
                'status_text': self._zone_status_text(zone),
                'composition': composition,
            })
        return {'style_text': self._style_text(zones['style']), 'zones': zone_views}

    @staticmethod
    def _zone_status_text(zone: dict) -> str:
        """无构成分区的状态词（不含分区名，块下已单独标注分区名）"""
        return tr(f'color_distribution.{zone["label_key"]}')

    def _palette_view(self, palette: list) -> list[dict]:
        """主色卡视图模型"""
        views = []
        for i, (rgb, pct, pname) in enumerate(palette, 1):
            views.append({
                'rgb': rgb, 'pct': pct,
                'display_name': self._pname_text(pname),
                'index_label': tr('color_distribution.dominant', index=i),
            })
        return views

    # ==================== 卡片 ====================

    def _create_stat_cards(self, result: dict) -> None:
        """创建 2×4 统计卡片"""
        for card in self._stat_cards:
            card.deleteLater()
        self._stat_cards.clear()

        stats_layout = self._stats_widget.layout()
        assert stats_layout is not None

        zones = result['zones']
        stats = [
            (tr('color_distribution.card_cast'), self._cast_text(result['cast']),
             tr('color_distribution.cast_hint')),
            (tr('color_distribution.card_harmony'), self._harmony_text(result), ''),
            (tr('color_distribution.card_style'), self._style_text(zones['style']), ''),
            (tr('color_distribution.card_warmth'), self._warmth_text(result['warmth']), ''),
            (tr('color_distribution.card_dark'), self._zone_text(zones['dark']), ''),
            (tr('color_distribution.card_mid'), self._zone_text(zones['mid']), ''),
            (tr('color_distribution.card_bright'), self._zone_text(zones['bright']), ''),
            (tr('color_distribution.card_chroma'), self._chroma_text(result['chroma_dist']), ''),
        ]

        columns = 4
        for i, (title, value, hint) in enumerate(stats):
            card = StatCard(title, value, self._stats_widget, hint)
            stats_layout.addWidget(card, i // columns, i % columns)
            self._stat_cards.append(card)

    def _on_theme_changed(self) -> None:
        """主题变化回调"""
        self._update_styles()
        self._wheel_chart.update_theme()
        self._zone_chart.update_theme()
        self._palette_chart.update_theme()
        for card in self._stat_cards:
            card._update_styles()

    def _update_styles(self) -> None:
        """更新样式"""
        super()._update_styles()

    def closeEvent(self, event) -> None:
        """关闭事件"""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.quit()
            self._worker.wait(1000)
        super().closeEvent(event)
