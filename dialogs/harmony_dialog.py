"""色彩和谐度分析对话框

分析配色方案的和谐类型、评分，并提供色相环可视化和优化建议。
"""

from __future__ import annotations

import math

# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QVBoxLayout, QWidget
)
from qfluentwidgets import qconfig, ScrollArea

# 项目模块导入
from utils import tr, load_icon_universal
from dialogs import BaseFramelessDialog
from core.harmony import analyze_harmony
from utils.theme_colors import (
    get_border_color,
    get_harmony_wheel_line_color,
    get_harmony_wheel_dot_border_color,
    get_harmony_score_excellent_color,
    get_harmony_score_good_color,
    get_harmony_score_average_color,
    get_harmony_score_poor_color,
)


class HarmonyWheel(QWidget):
    """色相环可视化组件，透明背景"""

    def __init__(self, colors: list[dict], parent=None):
        self._colors = colors
        self._hue_values = []
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._extract_hues()

    def _extract_hues(self):
        """提取颜色色相值"""
        self._hue_values = []
        for color in self._colors:
            hsb = color.get('hsb', (0, 0, 0))
            self._hue_values.append(float(hsb[0]))

    def paintEvent(self, event):
        """绘制色相环和颜色标记"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2
        outer_radius = min(center_x, center_y) - 10
        inner_radius = outer_radius - 20

        for angle_deg in range(360):
            hue_color = QColor.fromHsv(angle_deg, 255, 255)
            painter.setPen(QPen(hue_color, 1))
            start_angle = int((angle_deg - 0.5) * 16)
            span_angle = 16 * 2
            painter.drawArc(
                int(center_x - outer_radius),
                int(center_y - outer_radius),
                int(outer_radius * 2),
                int(outer_radius * 2),
                start_angle, span_angle
            )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            int(center_x - inner_radius),
            int(center_y - inner_radius),
            int(inner_radius * 2),
            int(inner_radius * 2)
        )

        if len(self._hue_values) >= 2:
            line_color = get_harmony_wheel_line_color()
            pen = QPen(line_color, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(len(self._hue_values)):
                for j in range(i + 1, len(self._hue_values)):
                    x1 = center_x + inner_radius * math.cos(math.radians(self._hue_values[i] - 90))
                    y1 = center_y + inner_radius * math.sin(math.radians(self._hue_values[i] - 90))
                    x2 = center_x + inner_radius * math.cos(math.radians(self._hue_values[j] - 90))
                    y2 = center_y + inner_radius * math.sin(math.radians(self._hue_values[j] - 90))
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        dot_border_color = get_harmony_wheel_dot_border_color()
        for i, hue in enumerate(self._hue_values):
            x = center_x + inner_radius * math.cos(math.radians(hue - 90))
            y = center_y + inner_radius * math.sin(math.radians(hue - 90))

            rgb = self._colors[i].get('rgb', [128, 128, 128]) if i < len(self._colors) else [128, 128, 128]
            dot_color = QColor(rgb[0], rgb[1], rgb[2])

            painter.setPen(QPen(dot_border_color, 2))
            painter.setBrush(dot_color)
            painter.drawEllipse(int(x - 7), int(y - 7), 14, 14)


class HarmonyAnalysisDialog(BaseFramelessDialog):
    """色彩和谐度分析对话框"""

    def __init__(self, scheme_name: str, colors: list[dict], parent=None):
        super().__init__(parent)
        self._scheme_name = scheme_name
        self._colors = colors
        self._analysis_result = analyze_harmony(colors)

        self.setWindowTitle(tr('dialogs.harmony.window_title', name=scheme_name))
        self.setWindowIcon(load_icon_universal())
        self.setFixedWidth(520)

        self._setup_title_bar()
        self.setup_ui()
        self._update_styles()

        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        self._enable_show()

    def setup_ui(self):
        """设置界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 40, 20, 20)
        main_layout.setSpacing(15)

        title_label = QLabel(tr('dialogs.harmony.title'))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        name_label = QLabel(tr('dialogs.harmony.scheme_name', name=self._scheme_name))
        name_label.setStyleSheet("font-size: 13px;")
        main_layout.addWidget(name_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        self.harmony_wheel = HarmonyWheel(self._colors)
        content_layout.addWidget(self.harmony_wheel, alignment=Qt.AlignmentFlag.AlignCenter)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)

        type_title = QLabel(tr('dialogs.harmony.harmony_type'))
        type_title.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(type_title)

        self.type_label = QLabel(tr(self._analysis_result['harmony_type_key']))
        self.type_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        info_layout.addWidget(self.type_label)

        score_title = QLabel(tr('dialogs.harmony.score'))
        score_title.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(score_title)

        score = self._analysis_result['score']
        score_level_key = self._analysis_result['score_level']
        self.score_label = QLabel(f"{score}")
        self.score_label.setStyleSheet("font-size: 36px; font-weight: bold;")
        info_layout.addWidget(self.score_label)

        self.score_level_label = QLabel(tr(score_level_key))
        self.score_level_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        info_layout.addWidget(self.score_level_label)

        info_layout.addStretch()
        content_layout.addWidget(info_widget, stretch=1)

        main_layout.addLayout(content_layout)

        suggestions = self._analysis_result.get('suggestions', [])
        if suggestions:
            suggest_title = QLabel(tr('dialogs.harmony.suggestions'))
            suggest_title.setStyleSheet("font-size: 13px; font-weight: bold;")
            main_layout.addWidget(suggest_title)

            for sug_key in suggestions:
                sug_label = QLabel(f"• {tr(sug_key)}")
                sug_label.setWordWrap(True)
                sug_label.setStyleSheet("font-size: 12px;")
                main_layout.addWidget(sug_label)

        analysis_title = QLabel(tr('dialogs.harmony.hue_analysis'))
        analysis_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        main_layout.addWidget(analysis_title)

        self._build_color_table(main_layout)

        main_layout.addStretch()

    def _build_color_table(self, layout: QVBoxLayout):
        """构建色差分析表格

        Args:
            layout: 父布局
        """
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            ScrollArea {
                background-color: transparent;
                border: none;
            }
            ScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        scroll_area.setMinimumHeight(80)
        scroll_area.setMaximumHeight(200)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        headers = [
            tr('dialogs.harmony.color_column'),
            tr('dialogs.harmony.hue_column'),
            tr('dialogs.harmony.saturation_column'),
            tr('dialogs.harmony.brightness_column'),
            tr('dialogs.harmony.distance_column'),
        ]
        widths = [40, 50, 50, 50, 50]
        for header_text, width in zip(headers, widths):
            h_label = QLabel(header_text)
            h_label.setFixedWidth(width)
            h_label.setStyleSheet("font-size: 11px; font-weight: bold;")
            header_layout.addWidget(h_label)

        container_layout.addWidget(header_widget)

        hue_distances = self._analysis_result.get('hue_distances', [])

        for i, color in enumerate(self._colors):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(8)

            color_block = QLabel()
            rgb = color.get('rgb', [128, 128, 128])
            hex_val = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
            color_block.setFixedSize(24, 24)
            color_block.setStyleSheet(
                f"background-color: {hex_val}; border-radius: 4px; border: 1px solid {get_border_color().name()};"
            )
            color_block.setFixedWidth(40)
            row_layout.addWidget(color_block)

            hsb = color.get('hsb', (0, 0, 0))
            h_val, s_val, b_val = f"{hsb[0]:.0f}°", f"{hsb[1]:.0f}%", f"{hsb[2]:.0f}%"

            for val_text, width in zip([h_val, s_val, b_val], [50, 50, 50]):
                val_label = QLabel(val_text)
                val_label.setFixedWidth(width)
                val_label.setStyleSheet("font-size: 11px;")
                row_layout.addWidget(val_label)

            if 0 < i <= len(hue_distances):
                dist_text = f"{hue_distances[i - 1]}°"
            else:
                dist_text = "--"
            dist_label = QLabel(dist_text)
            dist_label.setFixedWidth(50)
            dist_label.setStyleSheet("font-size: 11px;")
            row_layout.addWidget(dist_label)

            container_layout.addWidget(row_widget)

        container_layout.addStretch()
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)

    def _update_styles(self):
        """更新样式以适配主题"""
        super()._update_styles()

        score = self._analysis_result['score']
        if score >= 80:
            score_color = get_harmony_score_excellent_color()
        elif score >= 60:
            score_color = get_harmony_score_good_color()
        elif score >= 40:
            score_color = get_harmony_score_average_color()
        else:
            score_color = get_harmony_score_poor_color()

        self.score_label.setStyleSheet(
            f"font-size: 36px; font-weight: bold; color: {score_color.name()};"
        )
        self.score_level_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {score_color.name()};"
        )

        self.harmony_wheel.update()

    def closeEvent(self, event):
        """关闭事件"""
        super().closeEvent(event)
