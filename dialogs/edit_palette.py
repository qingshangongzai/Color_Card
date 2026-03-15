# 标准库导入
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# 第三方库导入
from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QRect
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QGridLayout, QApplication
)
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QBrush, QPen, QMouseEvent
from qfluentwidgets import (
    LineEdit, PrimaryPushButton, PushButton, ToolButton, FluentIcon,
    ScrollArea, isDarkTheme, qconfig
)

# 项目模块导入
from core import (
    hex_to_rgb, rgb_to_hex, rgb_to_hsb, hsb_to_rgb,
    rgb_to_lab, lab_to_rgb, rgb_to_hsl, hsl_to_rgb,
    rgb_to_cmyk, cmyk_to_rgb, get_color_info
)
from core.config import get_config_manager
from utils import tr, fix_windows_taskbar_icon_for_window, load_icon_universal, set_window_title_bar_theme
from utils.theme_colors import get_dialog_bg_color, get_text_color, get_border_color


# ==================== 颜色选择器对话框组件 ====================

# 48个预设颜色（8行×6列）
PRESET_COLORS = [
    # 第1行：黑色系（黑、深灰、中灰、浅灰、白、米白）
    ["#000000", "#333333", "#666666", "#999999", "#CCCCCC", "#FFFFFF"],
    # 第2行：红色系（深红、红、橙红、浅红、粉红、浅粉）
    ["#8B0000", "#FF0000", "#FF4500", "#FF6347", "#FFB6C1", "#FFC0CB"],
    # 第3行：橙色系（深橙、橙、金橙、浅橙、杏色、桃色）
    ["#CC5500", "#FF8C00", "#FFA500", "#FFAE42", "#FFDAB9", "#FFDAB9"],
    # 第4行：黄色系（深黄、黄、柠檬黄、浅黄、奶油、象牙）
    ["#B8860B", "#FFD700", "#FFFF00", "#FFFFE0", "#FFF8DC", "#FFFFF0"],
    # 第5行：绿色系（深绿、绿、草绿、浅绿、薄荷绿、青绿）
    ["#006400", "#008000", "#32CD32", "#90EE90", "#98FB98", "#20B2AA"],
    # 第6行：青色系（深青、青、天青、浅青、水色、薄荷）
    ["#008B8B", "#00CED1", "#00FFFF", "#AFEEEE", "#E0FFFF", "#40E0D0"],
    # 第7行：蓝色系（深蓝、蓝、天蓝、浅蓝、冰蓝、钢蓝）
    ["#00008B", "#0000FF", "#1E90FF", "#87CEEB", "#ADD8E6", "#4682B4"],
    # 第8行：紫色系（深紫、紫、紫罗兰、浅紫、薰衣草、洋红）
    ["#4B0082", "#800080", "#8A2BE2", "#9370DB", "#E6E6FA", "#FF00FF"],
]


class PresetGrid(QWidget):
    """预设颜色网格组件"""

    color_selected = Signal(int, int, int)  # 信号：RGB颜色被选中

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_color = None
        self._color_buttons = []
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 设置行列拉伸因子，使颜色块均匀分布
        for row in range(8):
            layout.setRowStretch(row, 1)
        for col in range(6):
            layout.setColumnStretch(col, 1)

        # 创建48个颜色块
        for row in range(8):
            for col in range(6):
                color_hex = PRESET_COLORS[row][col]
                btn = self._create_color_button(color_hex)
                layout.addWidget(btn, row, col)
                self._color_buttons.append((btn, color_hex))

    def _create_color_button(self, color_hex: str) -> QLabel:
        """创建颜色按钮"""
        btn = QLabel(self)
        btn.setMinimumSize(24, 24)
        btn.setStyleSheet(f"""
            QLabel {{
                background-color: {color_hex};
                border: 1px solid {get_border_color().name()};
                border-radius: 2px;
            }}
            QLabel:hover {{
                border: 2px solid {get_text_color().name()};
            }}
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.mousePressEvent = lambda e, c=color_hex: self._on_color_clicked(c)
        return btn

    def _on_color_clicked(self, color_hex: str):
        """颜色被点击"""
        r, g, b = hex_to_rgb(color_hex)
        self._selected_color = (r, g, b)
        self.color_selected.emit(r, g, b)


class ColorPreview(QWidget):
    """颜色预览组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(128, 128, 128)  # 默认灰色
        self.setFixedSize(100, 60)

    def set_color(self, r: int, g: int, b: int):
        """设置颜色"""
        self._color = QColor(r, g, b)
        self.update()

    def paintEvent(self, event):
        """绘制颜色预览"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制颜色块
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.fillRect(rect, self._color)

        # 绘制边框
        painter.setPen(QPen(get_border_color(), 1))
        painter.drawRect(rect)


class GradientSlider(QWidget):
    """带渐变的滑块组件"""

    value_changed = Signal(int)  # 信号：值变化

    def __init__(self, min_val: int, max_val: int, parent=None):
        super().__init__(parent)
        self._min_val = min_val
        self._max_val = max_val
        self._value = min_val
        self._gradient = None
        self._dragging = False

        self.setFixedSize(200, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_gradient(self, gradient: QLinearGradient):
        """设置渐变背景"""
        self._gradient = gradient
        self.update()

    def set_value(self, value: int):
        """设置值"""
        self._value = max(self._min_val, min(self._max_val, value))
        self.update()
        self.value_changed.emit(self._value)

    def get_value(self) -> int:
        """获取当前值"""
        return self._value

    def paintEvent(self, event):
        """绘制滑块"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制轨道背景
        track_rect = QRect(0, 8, self.width(), 4)
        if self._gradient:
            painter.fillRect(track_rect, QBrush(self._gradient))
        else:
            painter.fillRect(track_rect, QBrush(QColor(200, 200, 200)))

        # 计算滑块位置
        ratio = (self._value - self._min_val) / (self._max_val - self._min_val)
        x_pos = int(ratio * (self.width() - 16)) + 8

        # 绘制滑块指示器（圆形）
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QPoint(x_pos, 10), 8, 8)

        # 绘制边框
        painter.setPen(QPen(get_border_color(), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPoint(x_pos, 10), 8, 8)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._update_value_from_pos(event.pos().x())

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        if self._dragging:
            self._update_value_from_pos(event.pos().x())

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def _update_value_from_pos(self, x: int):
        """根据位置更新值"""
        ratio = max(0, min(1, (x - 8) / (self.width() - 16)))
        value = int(self._min_val + ratio * (self._max_val - self._min_val))
        self.set_value(value)


class ColorModeSliders(QWidget):
    """颜色模式滑块组"""

    value_changed = Signal()  # 信号：任意滑块值变化

    # 模式参数定义
    MODE_PARAMS = {
        'HSB': [('H', 0, 360, '°'), ('S', 0, 100, '%'), ('B', 0, 100, '%')],
        'RGB': [('R', 0, 255, ''), ('G', 0, 255, ''), ('B', 0, 255, '')],
        'LAB': [('L', 0, 100, ''), ('A', -128, 127, ''), ('B', -128, 127, '')],
        'HSL': [('H', 0, 360, '°'), ('S', 0, 100, '%'), ('L', 0, 100, '%')],
        'CMYK': [('C', 0, 100, '%'), ('M', 0, 100, '%'), ('Y', 0, 100, '%'), ('K', 0, 100, '%')],
    }

    def __init__(self, mode: str, parent=None):
        super().__init__(parent)
        self._mode = mode
        self._params = self.MODE_PARAMS.get(mode, [])
        self._sliders = []
        self._labels = []
        self._current_rgb = (128, 128, 128)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 模式标题
        title = QLabel(f"{self._mode}:")
        title.setStyleSheet(f"color: {get_text_color().name()}; font-size: 12px;")
        layout.addWidget(title)

        # 创建3个滑块
        for i, (name, min_val, max_val, unit) in enumerate(self._params):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(5)

            # 滑块
            slider = GradientSlider(min_val, max_val)
            slider.value_changed.connect(lambda v, idx=i: self._on_slider_changed(idx, v))
            self._sliders.append(slider)
            row_layout.addWidget(slider)

            # 数值标签
            label = QLabel(f"{min_val}{unit}")
            label.setFixedWidth(45)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            label.setStyleSheet(f"color: {get_text_color().name()}; font-size: 11px;")
            self._labels.append((label, unit))
            row_layout.addWidget(label)

            layout.addLayout(row_layout)

    def _on_slider_changed(self, index: int, value: int):
        """滑块值变化"""
        label, unit = self._labels[index]
        label.setText(f"{value}{unit}")
        self.value_changed.emit()

    def set_values(self, values: Tuple[float, ...]):
        """设置滑块值"""
        for i, value in enumerate(values):
            if i < len(self._sliders):
                self._sliders[i].set_value(int(value))
                label, unit = self._labels[i]
                label.setText(f"{int(value)}{unit}")

    def get_values(self) -> Tuple[float, ...]:
        """获取当前滑块值"""
        return tuple(slider.get_value() for slider in self._sliders)

    def update_gradient(self, current_rgb: Tuple[int, int, int]):
        """根据当前颜色更新滑块渐变背景"""
        self._current_rgb = current_rgb
        r, g, b = current_rgb

        if self._mode == 'HSB':
            h, s, v = rgb_to_hsb(r, g, b)
            # H滑块：色相渐变
            gradient_h = QLinearGradient(0, 0, 200, 0)
            for i in range(7):
                hue = i * 60
                color = QColor.fromHsv(int(hue / 360 * 255), 255, 255)
                gradient_h.setColorAt(i / 6, color)
            self._sliders[0].set_gradient(gradient_h)

            # S滑块：从灰到纯色
            gradient_s = QLinearGradient(0, 0, 200, 0)
            gradient_s.setColorAt(0.0, QColor.fromHsv(int(h / 360 * 255), 0, int(v / 100 * 255)))
            gradient_s.setColorAt(1.0, QColor.fromHsv(int(h / 360 * 255), 255, int(v / 100 * 255)))
            self._sliders[1].set_gradient(gradient_s)

            # B滑块：从黑到纯色
            gradient_b = QLinearGradient(0, 0, 200, 0)
            gradient_b.setColorAt(0.0, QColor.fromHsv(int(h / 360 * 255), int(s / 100 * 255), 0))
            gradient_b.setColorAt(1.0, QColor.fromHsv(int(h / 360 * 255), int(s / 100 * 255), 255))
            self._sliders[2].set_gradient(gradient_b)

        elif self._mode == 'RGB':
            # R滑块：从黑到红
            gradient_r = QLinearGradient(0, 0, 200, 0)
            gradient_r.setColorAt(0.0, QColor(0, g, b))
            gradient_r.setColorAt(1.0, QColor(255, g, b))
            self._sliders[0].set_gradient(gradient_r)

            # G滑块：从黑到绿
            gradient_g = QLinearGradient(0, 0, 200, 0)
            gradient_g.setColorAt(0.0, QColor(r, 0, b))
            gradient_g.setColorAt(1.0, QColor(r, 255, b))
            self._sliders[1].set_gradient(gradient_g)

            # B滑块：从黑到蓝
            gradient_b = QLinearGradient(0, 0, 200, 0)
            gradient_b.setColorAt(0.0, QColor(r, g, 0))
            gradient_b.setColorAt(1.0, QColor(r, g, 255))
            self._sliders[2].set_gradient(gradient_b)

        elif self._mode == 'HSL':
            h, s, l = rgb_to_hsl(r, g, b)
            # H滑块：色相渐变
            gradient_h = QLinearGradient(0, 0, 200, 0)
            for i in range(7):
                hue = i * 60
                color = QColor.fromHsv(int(hue / 360 * 255), 255, 255)
                gradient_h.setColorAt(i / 6, color)
            self._sliders[0].set_gradient(gradient_h)

            # S滑块：从灰到纯色
            gradient_s = QLinearGradient(0, 0, 200, 0)
            gradient_s.setColorAt(0.0, QColor.fromHsl(int(h / 360 * 359), 0, int(l / 100 * 255)))
            gradient_s.setColorAt(1.0, QColor.fromHsl(int(h / 360 * 359), 255, int(l / 100 * 255)))
            self._sliders[1].set_gradient(gradient_s)

            # L滑块：从黑到白
            gradient_l = QLinearGradient(0, 0, 200, 0)
            gradient_l.setColorAt(0.0, QColor.fromHsl(int(h / 360 * 359), int(s / 100 * 255), 0))
            gradient_l.setColorAt(0.5, QColor.fromHsl(int(h / 360 * 359), int(s / 100 * 255), 128))
            gradient_l.setColorAt(1.0, QColor.fromHsl(int(h / 360 * 359), int(s / 100 * 255), 255))
            self._sliders[2].set_gradient(gradient_l)

        elif self._mode == 'CMYK':
            c, m, y, k = rgb_to_cmyk(r, g, b)
            # C滑块：从当前颜色到青色
            gradient_c = QLinearGradient(0, 0, 200, 0)
            r1, g1, b1 = cmyk_to_rgb(0, m, y, k)
            r2, g2, b2 = cmyk_to_rgb(100, m, y, k)
            gradient_c.setColorAt(0.0, QColor(r1, g1, b1))
            gradient_c.setColorAt(1.0, QColor(r2, g2, b2))
            self._sliders[0].set_gradient(gradient_c)

            # M滑块：从当前颜色到品红
            gradient_m = QLinearGradient(0, 0, 200, 0)
            r1, g1, b1 = cmyk_to_rgb(c, 0, y, k)
            r2, g2, b2 = cmyk_to_rgb(c, 100, y, k)
            gradient_m.setColorAt(0.0, QColor(r1, g1, b1))
            gradient_m.setColorAt(1.0, QColor(r2, g2, b2))
            self._sliders[1].set_gradient(gradient_m)

            # Y滑块：从当前颜色到黄色
            gradient_y = QLinearGradient(0, 0, 200, 0)
            r1, g1, b1 = cmyk_to_rgb(c, m, 0, k)
            r2, g2, b2 = cmyk_to_rgb(c, m, 100, k)
            gradient_y.setColorAt(0.0, QColor(r1, g1, b1))
            gradient_y.setColorAt(1.0, QColor(r2, g2, b2))
            self._sliders[2].set_gradient(gradient_y)

            # K滑块：从当前颜色到黑色
            gradient_k = QLinearGradient(0, 0, 200, 0)
            r1, g1, b1 = cmyk_to_rgb(c, m, y, 0)
            r2, g2, b2 = cmyk_to_rgb(c, m, y, 100)
            gradient_k.setColorAt(0.0, QColor(r1, g1, b1))
            gradient_k.setColorAt(1.0, QColor(r2, g2, b2))
            self._sliders[3].set_gradient(gradient_k)


class ColorPickerDialog(QDialog):
    """颜色选择器对话框"""

    def __init__(self, initial_color: Optional[Tuple[int, int, int]] = None, parent=None):
        super().__init__(parent)
        self._initial_color = initial_color or (128, 128, 128)
        self._current_rgb = list(self._initial_color)
        self._color_info = None
        self._updating = False  # 防止循环更新

        self.setWindowTitle(tr('dialogs.color_picker.title'))
        self.setFixedSize(520, 420)

        # 设置窗口标志
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.CustomizeWindowHint
        )

        # 设置背景色
        bg_color = get_dialog_bg_color()
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color.name()}; }}")

        self.setup_ui()
        self._update_from_rgb()

        # 修复任务栏图标
        QTimer.singleShot(100, lambda: self._fix_taskbar_icon())

        # 监听主题变化
        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_title_bar_theme
        )

    def closeEvent(self, event):
        """关闭事件"""
        try:
            qconfig.themeChangedFinished.disconnect(self._theme_connection)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)

    def setup_ui(self):
        """设置界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 内容区域（左右分割）
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # 左侧：预设颜色网格
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.preset_grid = PresetGrid()
        self.preset_grid.color_selected.connect(self._on_preset_selected)
        left_layout.addWidget(self.preset_grid, stretch=1)

        content_layout.addLayout(left_layout, stretch=1)

        # 右侧：预览和滑块
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)

        # 颜色预览
        preview_layout = QHBoxLayout()
        preview_layout.addStretch()
        self.color_preview = ColorPreview()
        preview_layout.addWidget(self.color_preview)
        preview_layout.addStretch()
        right_layout.addLayout(preview_layout)

        # 获取设置中的颜色模式
        config_manager = get_config_manager()
        color_modes = config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        hex_visible = config_manager.get('settings.hex_visible', True)

        # 模式1滑块组
        mode1 = color_modes[0] if len(color_modes) > 0 else 'HSB'
        self.mode1_sliders = ColorModeSliders(mode1)
        self.mode1_sliders.value_changed.connect(self._on_mode1_changed)
        right_layout.addWidget(self.mode1_sliders)

        # 模式2滑块组
        mode2 = color_modes[1] if len(color_modes) > 1 else 'LAB'
        self.mode2_sliders = ColorModeSliders(mode2)
        self.mode2_sliders.value_changed.connect(self._on_mode2_changed)
        right_layout.addWidget(self.mode2_sliders)

        # HEX输入
        if hex_visible:
            hex_layout = QHBoxLayout()

            self.hex_input = LineEdit()
            self.hex_input.setFixedWidth(140)
            self.hex_input.setMaxLength(7)
            self.hex_input.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self.hex_input.textChanged.connect(self._on_hex_changed)
            self._update_hex_input_style()
            hex_layout.addWidget(self.hex_input)

            # 复制按钮
            self.copy_button = ToolButton(FluentIcon.COPY)
            self.copy_button.setFixedSize(28, 28)
            self.copy_button.clicked.connect(self._copy_hex_to_clipboard)
            hex_layout.addWidget(self.copy_button)

            hex_layout.addStretch()
            right_layout.addLayout(hex_layout)
        else:
            self.hex_input = None
            self.copy_button = None

        right_layout.addStretch()
        content_layout.addLayout(right_layout)

        main_layout.addLayout(content_layout)

        # 底部按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_button = PushButton(tr('dialogs.color_picker.cancel'))
        cancel_button.setMinimumWidth(80)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        confirm_button = PrimaryPushButton(tr('dialogs.color_picker.confirm'))
        confirm_button.setMinimumWidth(80)
        confirm_button.clicked.connect(self._on_confirm)
        buttons_layout.addWidget(confirm_button)

        main_layout.addLayout(buttons_layout)

    def _on_preset_selected(self, r: int, g: int, b: int):
        """预设颜色被选中"""
        self._current_rgb = [r, g, b]
        self._update_from_rgb()

    def _on_mode1_changed(self):
        """模式1滑块值变化"""
        if self._updating:
            return
        self._updating = True

        values = self.mode1_sliders.get_values()
        mode = self.mode1_sliders._mode

        # 根据模式计算RGB
        r, g, b = self._convert_mode_to_rgb(mode, values)
        self._current_rgb = [r, g, b]

        # 更新其他组件
        self._update_sliders(mode)
        self._update_preview()
        self._update_hex()

        self._updating = False

    def _on_mode2_changed(self):
        """模式2滑块值变化"""
        if self._updating:
            return
        self._updating = True

        values = self.mode2_sliders.get_values()
        mode = self.mode2_sliders._mode

        # 根据模式计算RGB
        r, g, b = self._convert_mode_to_rgb(mode, values)
        self._current_rgb = [r, g, b]

        # 更新其他组件
        self._update_sliders(mode)
        self._update_preview()
        self._update_hex()

        self._updating = False

    def _on_hex_changed(self, text: str):
        """HEX输入变化"""
        if self._updating:
            return

        text = text.strip().upper()
        if not text.startswith('#'):
            return

        if len(text) == 7:
            try:
                r, g, b = hex_to_rgb(text)
                self._current_rgb = [r, g, b]
                self._updating = True
                self._update_sliders()
                self._update_preview()
                self._updating = False
            except ValueError:
                pass

    def _convert_mode_to_rgb(self, mode: str, values: Tuple[float, ...]) -> Tuple[int, int, int]:
        """将模式值转换为RGB"""
        if mode == 'HSB':
            return hsb_to_rgb(values[0], values[1], values[2])
        elif mode == 'RGB':
            return (int(values[0]), int(values[1]), int(values[2]))
        elif mode == 'LAB':
            return lab_to_rgb(values[0], values[1], values[2])
        elif mode == 'HSL':
            return hsl_to_rgb(values[0], values[1], values[2])
        elif mode == 'CMYK':
            return cmyk_to_rgb(values[0], values[1], values[2], values[3])  # CMYK有4个参数
        return (128, 128, 128)

    def _update_from_rgb(self):
        """从RGB更新所有组件"""
        if self._updating:
            return
        self._updating = True

        self._update_sliders()
        self._update_preview()
        self._update_hex()

        self._updating = False

    def _update_sliders(self, exclude_mode: str = None):
        """更新滑块值和渐变"""
        r, g, b = self._current_rgb

        # 更新模式1
        if self.mode1_sliders._mode != exclude_mode:
            values = self._convert_rgb_to_mode(self.mode1_sliders._mode, r, g, b)
            self.mode1_sliders.set_values(values)
        self.mode1_sliders.update_gradient((r, g, b))

        # 更新模式2
        if self.mode2_sliders._mode != exclude_mode:
            values = self._convert_rgb_to_mode(self.mode2_sliders._mode, r, g, b)
            self.mode2_sliders.set_values(values)
        self.mode2_sliders.update_gradient((r, g, b))

    def _convert_rgb_to_mode(self, mode: str, r: int, g: int, b: int) -> Tuple[float, ...]:
        """将RGB转换为模式值"""
        if mode == 'HSB':
            return rgb_to_hsb(r, g, b)
        elif mode == 'RGB':
            return (float(r), float(g), float(b))
        elif mode == 'LAB':
            return rgb_to_lab(r, g, b)
        elif mode == 'HSL':
            return rgb_to_hsl(r, g, b)
        elif mode == 'CMYK':
            c, m, y, k = rgb_to_cmyk(r, g, b)
            return (c, m, y, k)  # 返回4个值
        return (0.0, 0.0, 0.0)

    def _update_preview(self):
        """更新颜色预览"""
        self.color_preview.set_color(*self._current_rgb)

    def _update_hex(self):
        """更新HEX输入"""
        if self.hex_input:
            hex_value = rgb_to_hex(*self._current_rgb)
            if self.hex_input.text().upper() != hex_value:
                self.hex_input.setText(hex_value)

    def _update_hex_input_style(self):
        """更新HEX输入框样式"""
        if not self.hex_input:
            return

        primary_color = get_text_color(secondary=False)
        secondary_color = get_text_color(secondary=True)
        border_color = get_border_color()

        self.hex_input.setStyleSheet(
            f"""
            QLineEdit {{
                font-size: 12px;
                font-weight: bold;
                color: {primary_color.name()};
                background-color: transparent;
                border: 1px solid {border_color.name()};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:disabled {{
                color: {secondary_color.name()};
                background-color: transparent;
                border: 1px solid {border_color.name()};
            }}
            QLineEdit:focus {{
                border: 2px solid #0078d4;
            }}
            """
        )

    def _copy_hex_to_clipboard(self):
        """复制HEX值到剪贴板"""
        if self.hex_input:
            hex_text = self.hex_input.text()
            if hex_text:
                clipboard = QApplication.clipboard()
                clipboard.setText(hex_text)
                self._show_tooltip(tr('messages.copy_success.content', value=hex_text))

    def _show_tooltip(self, message: str):
        """显示提示条（使用自定义 QLabel）"""
        # 创建提示标签
        tooltip_label = QLabel(self)
        tooltip_label.setText(f"✓ {message}")
        tooltip_label.setStyleSheet("""
            QLabel {
                background-color: #D4EDDA;
                color: #155724;
                border: 1px solid #C3E6CB;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }
        """)
        tooltip_label.adjustSize()

        # 定位在对话框顶部中央
        x = (self.width() - tooltip_label.width()) // 2
        tooltip_label.move(x, 5)
        tooltip_label.show()

        # 2秒后自动消失
        QTimer.singleShot(2000, tooltip_label.deleteLater)

    def _on_confirm(self):
        """确认按钮点击"""
        r, g, b = self._current_rgb
        self._color_info = get_color_info(r, g, b)
        self.accept()

    def get_color_info(self) -> Dict[str, Any]:
        """获取选择的颜色信息"""
        return self._color_info

    def _update_title_bar_theme(self):
        """更新标题栏主题"""
        set_window_title_bar_theme(self, isDarkTheme())

    def _fix_taskbar_icon(self):
        """修复任务栏图标"""
        try:
            if self and self.isVisible():
                fix_windows_taskbar_icon_for_window(self)
        except RuntimeError:
            pass

    def showEvent(self, event):
        """窗口显示事件"""
        self._update_title_bar_theme()
        super().showEvent(event)


class ColorInputRow(QWidget):
    """颜色输入行组件"""

    # 防抖延迟时间（毫秒）
    DEBOUNCE_DELAY = 200

    def __init__(self, index: int, parent=None):
        self._index = index
        self._color_info = None
        self._pending_text = ""
        super().__init__(parent)
        self.setup_ui()
        self._update_styles()
        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        # 添加防抖定时器
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._process_hex_input)

    def closeEvent(self, event):
        """关闭事件 - 断开信号连接"""
        try:
            if hasattr(self, '_theme_connection'):
                qconfig.themeChangedFinished.disconnect(self._theme_connection)
                delattr(self, '_theme_connection')
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)

    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 序号标签
        self.index_label = QLabel(f"{tr('dialogs.edit_palette.color_label')} {self._index + 1}")
        self.index_label.setFixedWidth(50)
        layout.addWidget(self.index_label)

        # HEX输入框
        self.hex_input = LineEdit()
        self.hex_input.setPlaceholderText("#RRGGBB")
        self.hex_input.setMaxLength(7)
        self.hex_input.setFixedWidth(100)
        self.hex_input.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.hex_input.textChanged.connect(self._on_hex_changed)
        layout.addWidget(self.hex_input)

        # 颜色预览块
        self.preview_block = QLabel()
        self.preview_block.setFixedSize(28, 28)
        self._update_preview_style(None)
        # 安装事件过滤器以捕获右键点击
        self.preview_block.installEventFilter(self)
        self.preview_block.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.preview_block)

        # 删除按钮
        self.delete_button = ToolButton(FluentIcon.REMOVE)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_button)

        layout.addStretch()

    def eventFilter(self, obj, event):
        """事件过滤器处理左键点击"""
        if obj == self.preview_block and event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._open_color_picker()
                return True
        return super().eventFilter(obj, event)

    def _open_color_picker(self):
        """打开颜色选择器对话框"""
        # 获取当前颜色作为初始值
        if self._color_info and 'rgb' in self._color_info:
            initial = self._color_info['rgb']
        else:
            initial = (128, 128, 128)  # 默认灰色

        dialog = ColorPickerDialog(initial, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            color_info = dialog.get_color_info()
            if color_info:
                self.set_color_info(color_info)

    def _update_styles(self):
        """更新样式以适配主题"""
        text_color = get_text_color()
        self.index_label.setStyleSheet(f"color: {text_color.name()}; font-size: 13px;")
        self._update_preview_style(self._color_info)

    def _update_preview_style(self, color_info):
        """更新预览块样式"""
        border_color = get_border_color()
        if color_info:
            rgb = color_info.get('rgb', [0, 0, 0])
            color_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
            self.preview_block.setStyleSheet(
                f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
            )
        else:
            self.preview_block.setStyleSheet(
                f"background-color: transparent; border-radius: 4px; border: 1px solid {border_color.name()};"
            )

    def _on_hex_changed(self, text: str):
        """HEX值变化处理 - 防抖版本"""
        text = text.strip().upper()

        # 自动添加#前缀（立即处理）
        if text and not text.startswith('#'):
            text = '#' + text
            self.hex_input.setText(text)
            return

        self._pending_text = text
        # 启动防抖定时器
        self._debounce_timer.start(self.DEBOUNCE_DELAY)

    def _process_hex_input(self):
        """处理HEX输入（防抖后）"""
        text = self._pending_text

        # 验证HEX格式
        if self._is_valid_hex(text):
            try:
                r, g, b = hex_to_rgb(text)
                # 只保存基本信息，不调用get_color_info进行完整转换
                self._color_info = {'rgb': (r, g, b), 'hex': text}
                self._update_preview_style(self._color_info)
            except ValueError:
                self._color_info = None
                self._update_preview_style(None)
        else:
            self._color_info = None
            self._update_preview_style(None)

    def _is_valid_hex(self, text: str) -> bool:
        """验证HEX格式"""
        if not text:
            return False
        pattern = r'^#[0-9A-F]{6}$'
        return bool(re.match(pattern, text.upper()))

    def _on_delete_clicked(self):
        """删除按钮点击"""
        # 找到 EditPaletteDialog 父组件
        dialog = self.window()
        if isinstance(dialog, EditPaletteDialog):
            dialog.remove_color_row(self)
        self.deleteLater()

    def get_color_info(self):
        """获取颜色信息（延迟计算完整信息）"""
        if self._color_info is None:
            return None

        # 如果只有基本信息，计算完整信息
        if 'hsb' not in self._color_info:
            from core import get_color_info as get_full_color_info
            r, g, b = self._color_info['rgb']
            hex_value = self._color_info.get('hex', '')
            self._color_info = get_full_color_info(r, g, b)
            self._color_info['hex'] = hex_value

        return self._color_info

    def has_valid_color(self) -> bool:
        """是否有有效颜色"""
        return self._color_info is not None

    def set_index(self, index: int):
        """设置序号"""
        self._index = index
        self.index_label.setText(f"颜色 {index + 1}")

    def set_color_info(self, color_info: Dict[str, Any]):
        """设置颜色信息

        Args:
            color_info: 颜色信息字典
        """
        self._color_info = color_info
        hex_value = color_info.get('hex', '')
        if hex_value:
            self.hex_input.setText(hex_value)
            self._update_preview_style(color_info)


class EditPaletteDialog(QDialog):
    """编辑配色对话框"""

    def __init__(self, default_name="", palette_data=None, parent=None, show_name_input=True):
        """初始化添加/编辑配色对话框

        Args:
            default_name: 默认配色名称
            palette_data: 已有配色数据（编辑模式），None表示添加模式
            parent: 父窗口
            show_name_input: 是否显示名称输入区域（默认True）
        """
        super().__init__(parent)
        self._palette_data = palette_data
        self._is_edit_mode = palette_data is not None
        self._show_name_input = show_name_input
        self.setWindowTitle("编辑配色" if self._is_edit_mode else "添加配色")
        self.setFixedSize(300, 400)
        self._default_name = default_name
        self._color_rows = []

        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())

        # 设置窗口标志
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.CustomizeWindowHint
        )

        # 设置窗口背景色
        bg_color = get_dialog_bg_color()
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color.name()}; }}")

        self.setup_ui()

        # 如果是编辑模式，加载已有数据
        if self._is_edit_mode:
            self._load_palette_data()

        # 修复任务栏图标
        QTimer.singleShot(100, lambda: self._fix_taskbar_icon())

        # 监听主题变化
        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_title_bar_theme
        )

    def closeEvent(self, event):
        """关闭事件 - 断开信号连接"""
        try:
            qconfig.themeChangedFinished.disconnect(self._theme_connection)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 名称输入区域（根据参数决定是否显示）
        if self._show_name_input:
            name_layout = QHBoxLayout()
            name_label = QLabel("配色名称：")
            name_label.setStyleSheet(f"color: {get_text_color().name()}; font-size: 13px;")
            name_layout.addWidget(name_label)

            self.name_input = LineEdit()
            self.name_input.setText(self._default_name)
            self.name_input.setPlaceholderText("输入配色名称...")
            self.name_input.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self.name_input.setClearButtonEnabled(True)
            name_layout.addWidget(self.name_input)
            layout.addLayout(name_layout)

            # 分隔线
            separator = QLabel()
            separator.setFixedHeight(1)
            separator.setStyleSheet(f"background-color: {get_border_color().name()};")
            layout.addWidget(separator)

        # 颜色列表标题
        colors_title = QLabel(tr('dialogs.edit_palette.colors_title'))
        colors_title.setStyleSheet(f"color: {get_text_color().name()}; font-size: 13px;")
        layout.addWidget(colors_title)

        # 颜色输入区域（可滚动）
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("ScrollArea { border: none; background: transparent; }")
        self.scroll_area.setMaximumHeight(200)

        # 设置滚动条角落为透明（防止出现灰色方块）
        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        self.scroll_area.setCornerWidget(corner_widget)

        self.colors_container = QWidget()
        self.colors_container.setStyleSheet("background: transparent;")
        self.colors_layout = QVBoxLayout(self.colors_container)
        self.colors_layout.setContentsMargins(0, 0, 0, 0)
        self.colors_layout.setSpacing(10)
        self.colors_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.colors_container)
        layout.addWidget(self.scroll_area)

        # 添加颜色按钮
        self.add_color_button = PushButton(FluentIcon.ADD, tr('dialogs.edit_palette.add_color'))
        self.add_color_button.setFixedHeight(32)
        self.add_color_button.clicked.connect(lambda: self._on_add_color())
        layout.addWidget(self.add_color_button)

        # 按钮区域
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # 取消按钮
        self.cancel_button = PushButton("取消")
        self.cancel_button.setMinimumWidth(80)
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        # 确认按钮
        self.confirm_button = PrimaryPushButton(tr('dialogs.edit_palette.confirm'))
        self.confirm_button.setMinimumWidth(80)
        self.confirm_button.clicked.connect(self._on_confirm)
        buttons_layout.addWidget(self.confirm_button)

        layout.addLayout(buttons_layout)

        # 设置焦点到名称输入框（如果存在）
        if self._show_name_input:
            self.name_input.setFocus()
            self.name_input.selectAll()

        # 添加第一个颜色输入行（不滚动）
        self._on_add_color(scroll_to_bottom=False)

    def _on_add_color(self, scroll_to_bottom: bool = True):
        """添加颜色输入行
        
        Args:
            scroll_to_bottom: 是否滚动到底部（默认True，初始化时传False）
        """
        row = ColorInputRow(len(self._color_rows), self.colors_container)
        self._color_rows.append(row)
        self.colors_layout.addWidget(row)
        if scroll_to_bottom:
            self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """滚动到颜色列表底部"""
        def do_scroll():
            scroll_bar = self.scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

        QTimer.singleShot(50, do_scroll)

    def remove_color_row(self, row):
        """移除颜色输入行

        Args:
            row: 要移除的 ColorInputRow 实例
        """
        if row in self._color_rows:
            self._color_rows.remove(row)
        # 更新剩余行的序号
        for i, r in enumerate(self._color_rows):
            r.set_index(i)

    def _load_palette_data(self):
        """加载已有配色数据（编辑模式）"""
        if not self._palette_data:
            return

        # 设置名称
        name = self._palette_data.get('name', '')
        if name and self._show_name_input:
            self.name_input.setText(name)

        # 获取已有颜色
        colors = self._palette_data.get('colors', [])

        # 保留原始ID（用于编辑模式）
        self._original_id = self._palette_data.get('id', '')

        # 清空默认添加的空行（从布局中移除、隐藏并删除）
        while self._color_rows:
            row = self._color_rows.pop()
            self.colors_layout.removeWidget(row)
            row.close()  # 触发 closeEvent 断开信号
            row.hide()
            row.deleteLater()

        # 立即处理事件，确保widget被正确删除
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()

        # 添加已有颜色
        for i, color_info in enumerate(colors):
            row = ColorInputRow(i, self.colors_container)
            row.set_color_info(color_info)
            self._color_rows.append(row)
            self.colors_layout.addWidget(row)

    def _on_confirm(self):
        """确认按钮点击"""
        # 获取有效颜色
        valid_colors = []
        for row in self._color_rows:
            if row.has_valid_color():
                valid_colors.append(row.get_color_info())

        # 验证至少有一个有效颜色
        if not valid_colors:
            self._show_error_tooltip("请至少输入一个有效的颜色值")
            return

        # 获取名称
        name = self.name_input.text().strip() if self._show_name_input else ""
        if not name:
            name = self._default_name

        self._palette_data = {
            'name': name,
            'colors': valid_colors,
            'created_at': datetime.now().isoformat()
        }

        # 如果是编辑模式，保留原始ID；如果是添加模式，生成新ID
        if self._is_edit_mode and hasattr(self, '_original_id') and self._original_id:
            self._palette_data['id'] = self._original_id
        else:
            # 添加模式：生成新ID
            import uuid
            self._palette_data['id'] = str(uuid.uuid4())

        self.accept()

    def _show_error_tooltip(self, message: str):
        """显示错误提示（使用自定义 QLabel 替代 InfoBar）"""
        # 创建错误提示标签
        error_label = QLabel(self)
        error_label.setText(f"⚠ {message}")
        error_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3CD;
                color: #856404;
                border: 1px solid #FFEAA7;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }
        """)
        error_label.adjustSize()
        
        # 定位在对话框顶部中央
        x = (self.width() - error_label.width()) // 2
        error_label.move(x, 5)
        error_label.show()
        
        # 3秒后自动消失
        QTimer.singleShot(3000, error_label.deleteLater)

    def get_palette_data(self):
        """获取配色数据

        Returns:
            dict: 包含名称、颜色列表和创建时间的字典
        """
        return getattr(self, '_palette_data', None)

    def _update_title_bar_theme(self):
        """更新标题栏主题以适配当前主题"""
        set_window_title_bar_theme(self, isDarkTheme())

    def _fix_taskbar_icon(self):
        """修复任务栏图标"""
        try:
            if self and self.isVisible():
                fix_windows_taskbar_icon_for_window(self)
        except RuntimeError:
            # 对象已被销毁
            pass

    def showEvent(self, event):
        """窗口显示事件 - 在显示前设置标题栏主题避免闪烁"""
        self._update_title_bar_theme()
        super().showEvent(event)
