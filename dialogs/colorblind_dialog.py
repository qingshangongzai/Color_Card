"""色盲模拟预览对话框

提供配色方案的色盲模拟预览功能，支持多种色盲类型切换和严重程度调节。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QVBoxLayout, QWidget
)
from PySide6.QtGui import QColor, QPainter
from qfluentwidgets import (
    ComboBox, Slider, qconfig
)

from utils import tr, load_icon_universal
from dialogs import BaseFramelessDialog
from core.colorblind import (
    simulate_colorblind, get_colorblind_info, get_all_colorblind_types
)
from utils.theme_colors import (
    get_text_color, get_secondary_text_color,
    get_title_color
)


class PalettePreviewStrip(QWidget):
    """配色色块条，横排显示一组色块"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors: list[tuple[int, int, int]] = []
        self.setFixedHeight(40)

    def set_colors(self, colors: list[tuple[int, int, int]]):
        self._colors = colors
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._colors:
            return
        n = len(self._colors)
        w = self.width() // n
        for i, rgb in enumerate(self._colors):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(rgb[0], rgb[1], rgb[2]))
            painter.drawRoundedRect(i * w + 2, 2, w - 4, self.height() - 4, 4, 4)


class ColorblindPreviewDialog(BaseFramelessDialog):
    """色盲模拟预览对话框

    显示配色方案在不同色盲类型下的视觉效果。
    """

    def __init__(self, scheme_name: str, colors: list[dict], parent=None):
        super().__init__(parent)
        self._scheme_name = scheme_name
        self._colors = colors
        self._current_type = 'normal'
        self._severity = 0.5

        self.setWindowTitle(tr('dialogs.colorblind.window_title', name=scheme_name))
        self.setFixedSize(600, 380)

        self.setWindowIcon(load_icon_universal())

        self.setup_ui()
        self._setup_title_bar()
        self._update_styles()

        self.update_preview()

        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        self._enable_show()

    def setup_ui(self):
        """设置界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 40, 20, 20)
        main_layout.setSpacing(12)

        text_color = get_text_color()
        secondary_color = get_secondary_text_color()
        title_color = get_title_color()

        title_label = QLabel(tr('dialogs.colorblind.title'))
        title_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {title_color.name()};"
        )
        main_layout.addWidget(title_label)

        name_label = QLabel(tr('dialogs.colorblind.scheme_name', name=self._scheme_name))
        name_label.setStyleSheet(f"font-size: 13px; color: {secondary_color.name()};")
        main_layout.addWidget(name_label)

        strip_label = QLabel(tr('dialogs.colorblind.original'))
        strip_label.setStyleSheet(f"font-size: 12px; color: {secondary_color.name()};")
        main_layout.addWidget(strip_label)

        self.original_strip = PalettePreviewStrip()
        main_layout.addWidget(self.original_strip)

        simulated_label = QLabel(tr('dialogs.colorblind.simulated'))
        simulated_label.setStyleSheet(f"font-size: 12px; color: {secondary_color.name()};")
        main_layout.addWidget(simulated_label)

        self.simulated_strip = PalettePreviewStrip()
        main_layout.addWidget(self.simulated_strip)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)

        type_label = QLabel(tr('dialogs.colorblind.colorblind_type'))
        type_label.setStyleSheet(f"font-size: 13px; color: {text_color.name()};")
        control_layout.addWidget(type_label)

        self.type_combo = ComboBox()
        self.type_combo.setMinimumWidth(130)
        self._type_keys = []
        colorblind_types = get_all_colorblind_types()
        for key, info in colorblind_types.items():
            self.type_combo.addItem(info['name'])
            self._type_keys.append(key)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        control_layout.addWidget(self.type_combo)

        self.severity_container = QWidget()
        severity_layout = QHBoxLayout(self.severity_container)
        severity_layout.setContentsMargins(0, 0, 0, 0)
        severity_layout.setSpacing(6)

        self.severity_label = QLabel(tr('dialogs.colorblind.severity', value=50))
        self.severity_label.setStyleSheet(f"font-size: 13px; color: {text_color.name()};")
        severity_layout.addWidget(self.severity_label)

        self.severity_slider = Slider(Qt.Orientation.Horizontal)
        self.severity_slider.setRange(0, 100)
        self.severity_slider.setValue(50)
        self.severity_slider.setMinimumWidth(120)
        self.severity_slider.valueChanged.connect(self._on_severity_changed)
        severity_layout.addWidget(self.severity_slider, stretch=1)

        control_layout.addWidget(self.severity_container)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        self.description_label = QLabel("")
        self.description_label.setStyleSheet(
            f"font-size: 12px; color: {secondary_color.name()}; padding: 5px;"
        )
        self.description_label.setWordWrap(True)
        main_layout.addWidget(self.description_label)

        self._update_severity_visibility()

    def _on_type_changed(self, index: int):
        """色盲类型改变"""
        if 0 <= index < len(self._type_keys):
            self._current_type = self._type_keys[index]
            self._update_severity_visibility()
            self.update_preview()

    def _on_severity_changed(self, value: int):
        """严重程度滑块回调"""
        self._severity = value / 100.0
        self.severity_label.setText(tr('dialogs.colorblind.severity', value=value))
        self.update_preview()

    def _update_severity_visibility(self):
        """根据当前色盲类型控制滑块可见性"""
        is_anomal = self._current_type in ('protanomaly', 'deuteranomaly', 'tritanomaly')
        self.severity_container.setVisible(is_anomal)

    def update_preview(self):
        """更新所有预览组件的显示"""
        original_rgbs = [
            tuple(color_data.get('rgb', [128, 128, 128]))
            for color_data in self._colors
        ]

        severity = self._severity
        simulated_rgbs = [
            simulate_colorblind(rgb, self._current_type, severity)
            for rgb in original_rgbs
        ]

        self.original_strip.set_colors(original_rgbs)
        self.simulated_strip.set_colors(simulated_rgbs)

        info = get_colorblind_info(self._current_type)
        self.description_label.setText(
            tr('dialogs.colorblind.description', desc=info['description'])
        )
