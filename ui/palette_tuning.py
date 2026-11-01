"""动态色彩微调调色板界面

左栏基色控制台 + 右栏配色卡片网格。计算逻辑全部由
core.palette_tuning.PaletteTuningEngine 提供，本模块只负责展示与交互。
"""

# 标准库导入
import math
import re
import uuid
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QSlider, QSplitter, QStyle, QStyleOptionSlider,
    QVBoxLayout, QWidget
)
from qfluentwidgets import (
    FluentIcon, InfoBar, InfoBarPosition, PushButton, ScrollArea,
    ScrollBarHandleDisplayMode, SegmentedWidget, Slider, ToolButton,
    TransparentToolButton, isDarkTheme, qconfig
)

# 项目模块导入
from core import (
    MODES, PaletteTuningEngine, TuningItem, get_color_info, get_config_manager,
    hex_now, hex_to_rgb, parse_hex_input, from_palette_tuning_storage,
    to_palette_tuning_storage
)
from core.palette_tuning import MAX_COUNT, MIN_COUNT
from core.logger import get_logger, log_user_action
from ui.cards import BaseCard
from utils import tr, get_locale_manager
from utils.theme_colors import (
    get_accent_color, get_border_color, get_invalid_input_border_color,
    get_locked_card_background_color, get_locked_tag_color,
    get_picker_fill_color, get_placeholder_color, get_secondary_text_color,
    get_text_color
)

logger = get_logger("palette_tuning_ui")

# H 通道恒彩虹（与原型 8-stop 首尾闭合一致）
RAINBOW_STOPS = (
    '#FF4D4D', '#FFE14D', '#4DFF77', '#4DE1FF', '#4D6BFF', '#C44DFF', '#FF4D9D', '#FF4D4D'
)

# 卡片网格列数：调色板卡片含滑块与数值框，需要足够宽度
MAX_GRID_COLUMNS = 2

# 交互与提示时长
SAVE_DEBOUNCE_MS = 800          # 配置防抖保存间隔
HEX_INVALID_FLASH_MS = 700      # 非法 HEX 红框停留时长
INFOBAR_DURATION_MS = 2000      # InfoBar 显示时长
REPEAT_DELAY_MS = 400           # 步进按钮长按连发延迟
REPEAT_INTERVAL_MS = 90         # 步进按钮连发间隔
BOUNDARY_EPSILON = 1e-9         # 步进边界判定容差

_NUM_RE = re.compile(r'^-?\d+(\.\d+)?$')


# ==================== 通用工具 ====================

def _round_prec(v: float, dec: int) -> float:
    """按显示精度取整（复刻 JS Math.round 远离零舍入）"""
    m = 10 ** dec
    return math.floor(v * m + 0.5) / m


def _fmt_val(v: float, dec: int) -> str:
    """通道值显示文本"""
    r = _round_prec(v, dec)
    return f'{r:.{dec}f}' if dec > 0 else str(int(r))


def _parse_num_loose(text: str | None) -> float | None:
    """宽松解析输入框数值：兼容 "(+5)" / "-10" / " 8.3 "；非法返回 None"""
    if text is None:
        return None
    cleaned = re.sub(r'[()\s]', '', str(text))
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    if not _NUM_RE.match(cleaned):
        return None
    return float(cleaned)


def _input_style_sheet(invalid: bool = False) -> str:
    """输入框样式（非法输入时为红边框）"""
    border = get_invalid_input_border_color() if invalid else get_border_color()
    return f"""
        QLineEdit {{
            font-size: 12px;
            font-weight: bold;
            color: {get_text_color().name()};
            background-color: transparent;
            border: 1px solid {border.name()};
            border-radius: 4px;
            padding: 2px 6px;
        }}
        QLineEdit:focus {{
            border: 2px solid {get_accent_color().name()};
        }}
    """


def _track_colors(spec, ch_vec: dict[str, float], mode) -> list[str]:
    """轨道渐变端点：环形通道恒彩虹，其余按 min / 中点 / max 合成真实颜色"""
    if spec.circular:
        return list(RAINBOW_STOPS)
    stops: list[str] = []
    for value in (spec.min, (spec.min + spec.max) / 2, spec.max):
        ch = dict(ch_vec)
        ch[spec.key] = value
        rgb = mode.to_rgb(*(ch[c.key] for c in mode.channels))
        stops.append(hex_now(rgb))
    return stops


def _linked_track_colors(
    spec,
    item: TuningItem,
    mode,
    base_ch: dict[str, float],
) -> list[str]:
    """联动模式轨道渐变：当前通道偏移从下限到上限时对应的真实颜色"""
    current: dict[str, float] = {}
    for channel in mode.channels:
        value = base_ch[channel.key] + item.offset[channel.key]
        current[channel.key] = value % 360 if channel.circular else max(
            channel.min, min(channel.max, value)
        )

    stops: list[str] = []
    for offset in (-spec.off_max, 0.0, spec.off_max):
        ch = dict(current)
        value = base_ch[spec.key] + offset
        ch[spec.key] = max(spec.min, min(spec.max, value))
        rgb = mode.to_rgb(*(ch[c.key] for c in mode.channels))
        stops.append(hex_now(rgb))
    return stops


def _copy_hex(hex_value: str, source: QWidget):
    """复制 HEX 到剪贴板并提示"""
    QApplication.clipboard().setText(hex_value)
    InfoBar.success(
        title=tr('palette_tuning.copied_title'),
        content=tr('palette_tuning.copied', hex=hex_value),
        orient=Qt.Orientation.Horizontal,
        isClosable=True,
        position=InfoBarPosition.TOP,
        duration=INFOBAR_DURATION_MS,
        parent=source.window()
    )


def _clear_layout(layout):
    """移除并销毁布局中的全部子控件"""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()


# ==================== 基础控件 ====================

class ColorSwatch(QWidget):
    """颜色色块；clickable 为 True 时点击触发 clicked 信号"""

    clicked = Signal()

    def __init__(
        self,
        min_height: int = 40,
        fixed_width: int | None = None,
        parent=None,
        clickable: bool = True,
    ):
        super().__init__(parent)
        self._color = get_placeholder_color().name()
        self._clickable = clickable
        self.setMinimumHeight(min_height)
        if fixed_width is not None:
            self.setFixedWidth(fixed_width)
            self.setFixedHeight(min_height)
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_color(self, hex_color: str):
        """设置色块颜色"""
        self._color = hex_color
        self.update()

    def paintEvent(self, event):
        """绘制圆角色块"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(get_border_color(), 1))
        painter.setBrush(QColor(self._color))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)

    def mousePressEvent(self, event):
        """左键点击触发 clicked（仅可交互色块）"""
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class NumericLineEdit(QLineEdit):
    """数值输入框：聚焦全选、Enter 提交（通过失焦触发 editingFinished）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(58)
        self.setFixedHeight(24)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.update_style()

    def update_style(self):
        """更新主题样式"""
        self.setStyleSheet(_input_style_sheet())

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()
            return
        super().keyPressEvent(event)


class HexLineEdit(QLineEdit):
    """基色 HEX 输入框：聚焦快照、Esc 取消"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.focus_handler = None
        self.escape_handler = None
        self.setPlaceholderText('#RRGGBB')
        self.setMaxLength(7)
        self.setFixedHeight(30)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()
        if self.focus_handler is not None:
            self.focus_handler()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.escape_handler is not None:
                self.escape_handler()
            self.clearFocus()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()
            return
        super().keyPressEvent(event)


class ChannelSlider(QSlider):
    """通道滑块，自绘轨道渐变与手柄"""

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._stops: list[str] = []
        self.setFixedHeight(22)
        self.setMinimumWidth(24)

    def set_track_colors(self, colors: list[str]):
        """设置轨道渐变色"""
        self._stops = list(colors)
        self.update()

    def paintEvent(self, event):
        """绘制渐变轨道 + 圆形手柄"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self
        )
        if groove.width() <= 0:
            return

        cy = self.height() / 2
        track_h = 6.0
        track = QRectF(groove.left(), cy - track_h / 2, groove.width(), track_h)

        gradient = QLinearGradient(track.left(), 0, track.right(), 0)
        if self._stops:
            last = len(self._stops) - 1
            for index, color in enumerate(self._stops):
                gradient.setColorAt(index / last if last else 0.0, QColor(color))
        else:
            gradient.setColorAt(0.0, get_border_color())

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(track, track_h / 2, track_h / 2)

        span = self.maximum() - self.minimum()
        ratio = (self.value() - self.minimum()) / span if span else 0.0
        inset = 7.0
        x = groove.left() + inset + ratio * (groove.width() - 2 * inset)
        painter.setPen(QPen(get_border_color(), 1))
        painter.setBrush(get_picker_fill_color())
        painter.drawEllipse(QPointF(x, cy), 7, 7)


class RepeatToolButton(TransparentToolButton):
    """长按连发的步进按钮（400ms 后每 90ms 触发一次 clicked）"""

    def __init__(self, icon, parent=None):
        super().__init__(parent)
        self.setIcon(icon)
        self.setFixedSize(20, 20)
        self.setIconSize(QSize(8, 8))

        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.setInterval(REPEAT_DELAY_MS)
        self._delay_timer.timeout.connect(self._start_repeat)

        self._repeat_timer = QTimer(self)
        self._repeat_timer.setInterval(REPEAT_INTERVAL_MS)
        self._repeat_timer.timeout.connect(self._emit_step)

        self.pressed.connect(self._delay_timer.start)
        self.released.connect(self._stop_repeat)

    def _start_repeat(self):
        self._repeat_timer.start()

    def _stop_repeat(self):
        self._delay_timer.stop()
        self._repeat_timer.stop()

    def _emit_step(self):
        if not self.isEnabled():
            self._stop_repeat()
            return
        self.clicked.emit()

    def leaveEvent(self, event):
        self._stop_repeat()
        super().leaveEvent(event)


# ==================== 卡片通道行 ====================

class TuneChannelRow(QWidget):
    """配色卡片的单个通道行：滑块 + 步进按钮 + 数值框"""

    def __init__(self, spec, card, parent=None):
        super().__init__(parent)
        self._spec = spec
        self._card = card
        self._updating = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._label = QLabel(tr(spec.label_key))
        self._label.setFixedWidth(14)

        self._dec_btn = RepeatToolButton(FluentIcon.REMOVE, self)
        self._inc_btn = RepeatToolButton(FluentIcon.ADD, self)

        self._slider = ChannelSlider(self)

        self._num = NumericLineEdit(self)

        layout.addWidget(self._label)
        layout.addWidget(self._dec_btn)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._inc_btn)
        layout.addWidget(self._num)

        self._slider.valueChanged.connect(self._on_slider_changed)
        self._num.editingFinished.connect(self._on_num_finished)
        self._dec_btn.clicked.connect(lambda: self._card.step_param(self._spec.key, -1))
        self._inc_btn.clicked.connect(lambda: self._card.step_param(self._spec.key, 1))

    def update_texts(self):
        """更新多语言文本"""
        self._label.setText(tr(self._spec.label_key))

    def update_style(self):
        """更新输入框与标签样式"""
        self._num.update_style()
        self._label.setStyleSheet(
            f"color: {get_secondary_text_color().name()}; font-size: 11px;"
        )

    def refresh(self, item: TuningItem, mode, base_ch: dict[str, float]):
        """按条目当前状态刷新滑块 / 数值框 / 轨道"""
        spec = self._spec
        locked = item.is_locked
        if locked:
            assert item.absolute is not None, "锁定项必须已有绝对值"
            value = item.absolute[spec.key]
        else:
            value = item.offset[spec.key]
        lo, hi = (spec.min, spec.max) if locked else (-spec.off_max, spec.off_max)

        self._updating = True
        self._slider.setRange(int(lo), int(hi))
        self._slider.setValue(int(_round_prec(value, 0)))
        self._updating = False

        if not self._num.hasFocus():
            self._num.setText(_fmt_val(value, spec.dec))

        self._dec_btn.setEnabled(not (value <= lo + BOUNDARY_EPSILON))
        self._inc_btn.setEnabled(not (value >= hi - BOUNDARY_EPSILON))

        if spec.circular:
            colors = list(RAINBOW_STOPS)
        elif locked:
            assert item.absolute is not None, "锁定项必须已有绝对值"
            colors = _track_colors(spec, item.absolute, mode)
        else:
            colors = _linked_track_colors(spec, item, mode, base_ch)
        self._slider.set_track_colors(colors)

    def _on_slider_changed(self, value: int):
        if self._updating:
            return
        self._card.set_param(self._spec.key, float(value))

    def _on_num_finished(self):
        if self._updating:
            return
        parsed = _parse_num_loose(self._num.text())
        if parsed is None:
            self._card.refresh()
            return
        self._card.set_param(self._spec.key, parsed)


# ==================== 配色卡片 ====================

class TuneCard(BaseCard):
    """单个配色卡片"""

    def __init__(
        self,
        item: TuningItem,
        engine: PaletteTuningEngine,
        on_state_changed,
        parent=None,
    ):
        self._item = item
        self._engine = engine
        self._on_state_changed = on_state_changed
        self._rows: list[TuneChannelRow] = []
        self._style_key = None
        super().__init__(item.id - 1, parent)

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setMinimumWidth(220)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_rows_container())
        layout.addLayout(self._build_footer())
        self.rebuild_rows()

    def _build_header(self) -> QHBoxLayout:
        """顶部：色块 + 名称/模式标签 + 重置 + 锁定"""
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)

        self._swatch = ColorSwatch(44, 44, self, clickable=False)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(3)
        self._name_label = QLabel()
        self._tag_label = QLabel()
        info.addWidget(self._name_label)
        info.addWidget(self._tag_label)

        self._reset_button = ToolButton(FluentIcon.SYNC, self)
        self._reset_button.setFixedSize(24, 24)
        self._reset_button.clicked.connect(self._reset_item)

        self._lock_button = ToolButton(FluentIcon.UNPIN, self)
        self._lock_button.setFixedSize(24, 24)
        self._lock_button.clicked.connect(self._toggle_lock)

        top.addWidget(self._swatch)
        top.addLayout(info, 1)
        top.addWidget(self._reset_button)
        top.addWidget(self._lock_button)
        return top

    def _build_rows_container(self) -> QWidget:
        """通道行容器（模式切换时重建）"""
        self._rows_container = QWidget(self)
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(6)
        return self._rows_container

    def _build_footer(self) -> QHBoxLayout:
        """底部：最终 HEX + 复制"""
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(4)
        self._hex_label = QLabel()
        self._hex_label.setFixedHeight(24)
        self._copy_button = ToolButton(FluentIcon.COPY, self)
        self._copy_button.setFixedSize(24, 24)
        self._copy_button.clicked.connect(self._copy_current_hex)
        bottom.addWidget(self._hex_label, 1)
        bottom.addWidget(self._copy_button)
        return bottom

    def clear(self):
        """清空颜色显示（BaseCard 契约；本页卡片始终绑定配色条目）"""
        self._swatch.set_color(get_placeholder_color().name())
        self._hex_label.clear()

    def rebuild_rows(self):
        """按当前色彩模式重建通道行"""
        _clear_layout(self._rows_layout)
        self._rows = []
        mode = MODES[self._engine.mode]
        for spec in mode.channels:
            row = TuneChannelRow(spec, self, self._rows_container)
            self._rows.append(row)
            self._rows_layout.addWidget(row)

    def update_texts(self):
        """更新多语言文本"""
        for row in self._rows:
            row.update_texts()
        self.refresh()

    def update_styles(self):
        """更新主题样式"""
        text_color = get_text_color()
        self._name_label.setStyleSheet(
            f"color: {text_color.name()}; font-size: 13px; font-weight: bold;"
        )
        self._hex_label.setStyleSheet(
            f"""
            QLabel {{
                font-size: 12px;
                font-weight: bold;
                color: {text_color.name()};
                background-color: transparent;
                border: 1px solid {get_border_color().name()};
                border-radius: 4px;
                padding: 2px 8px;
            }}
            """
        )
        for row in self._rows:
            row.update_style()
        self._style_key = None

    def refresh(self):
        """全量刷新卡片显示"""
        mode = MODES[self._engine.mode]
        hex_value = hex_now(self._item.final_rgb)

        self._swatch.set_color(hex_value)
        self._hex_label.setText(hex_value)
        self._name_label.setText(tr('palette_tuning.item_name', index=self._item.id))

        locked = self._item.is_locked
        tag_key = 'palette_tuning.locked_tag' if locked else 'palette_tuning.unlocked_tag'
        self._tag_label.setText(tr(tag_key))
        self._lock_button.setIcon(FluentIcon.PIN if locked else FluentIcon.UNPIN)

        self._apply_card_style()

        base_ch = self._engine.base_channels()
        for row in self._rows:
            row.refresh(self._item, mode, base_ch)

    def set_param(self, key: str, value: float):
        """写入联动偏移 / 独立绝对值"""
        self._engine.set_param(self._item.id, key, value)
        self.refresh()
        self._on_state_changed()

    def step_param(self, key: str, direction: int):
        """步进 ±1"""
        self._engine.step_param(self._item.id, key, direction)
        self.refresh()
        self._on_state_changed()

    def _toggle_lock(self):
        """锁定 / 解锁切换"""
        if self._item.is_locked:
            self._engine.unlock_item(self._item.id)
            log_user_action('palette_tuning_unlock_item', {'item': self._item.name})
        else:
            self._engine.lock_item(self._item.id)
            log_user_action('palette_tuning_lock_item', {'item': self._item.name})
        self.refresh()
        self._on_state_changed()

    def _reset_item(self):
        """重置：回到基色"""
        self._engine.reset_item(self._item.id)
        log_user_action('palette_tuning_reset_item', {'item': self._item.name})
        self.refresh()
        self._on_state_changed()

    def _copy_current_hex(self):
        _copy_hex(hex_now(self._item.final_rgb), self)

    def _apply_card_style(self):
        """锁定态三重表达中的背景色与标签色（状态未变时跳过）"""
        locked = self._item.is_locked
        style_key = (locked, isDarkTheme())
        if self._style_key == style_key:
            return
        self._style_key = style_key

        if locked:
            background = get_locked_card_background_color()
            self.setStyleSheet(
                "TuneCard {"
                f" background-color: rgba({background.red()}, {background.green()},"
                f" {background.blue()}, {background.alpha()});"
                " border-radius: 8px;"
                "}"
            )
            self._tag_label.setStyleSheet(
                f"color: {get_locked_tag_color().name()}; font-size: 11px;"
            )
        else:
            self.setStyleSheet("TuneCard { background-color: transparent; }")
            self._tag_label.setStyleSheet(
                f"color: {get_secondary_text_color().name()}; font-size: 11px;"
            )


# ==================== 基色通道行 ====================

class BaseChannelRow(QWidget):
    """基色控制台通道行：滑块 + 步进按钮 + 数值框"""

    def __init__(self, spec, interface, parent=None):
        super().__init__(parent)
        self._spec = spec
        self._interface = interface
        self._updating = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._label = QLabel(tr(spec.label_key))
        self._label.setFixedWidth(16)

        self._dec_btn = RepeatToolButton(FluentIcon.REMOVE, self)
        self._inc_btn = RepeatToolButton(FluentIcon.ADD, self)

        self._slider = ChannelSlider(self)
        self._slider.setRange(int(spec.min), int(spec.max))

        self._num = NumericLineEdit(self)

        layout.addWidget(self._label)
        layout.addWidget(self._dec_btn)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._inc_btn)
        layout.addWidget(self._num)

        self._slider.valueChanged.connect(self._on_slider_changed)
        self._num.editingFinished.connect(self._on_num_finished)
        self._dec_btn.clicked.connect(lambda: self._interface._step_base_channel(spec.key, -1))
        self._inc_btn.clicked.connect(lambda: self._interface._step_base_channel(spec.key, 1))

    def update_texts(self):
        """更新多语言文本"""
        self._label.setText(tr(self._spec.label_key))

    def update_style(self):
        """更新输入框与标签样式"""
        self._num.update_style()
        self._label.setStyleSheet(
            f"color: {get_secondary_text_color().name()}; font-size: 11px;"
        )

    def refresh(self, channels: dict[str, float], track_colors: list[str]):
        """刷新显示值"""
        value = channels[self._spec.key]
        self._dec_btn.setEnabled(not (value <= self._spec.min + BOUNDARY_EPSILON))
        self._inc_btn.setEnabled(not (value >= self._spec.max - BOUNDARY_EPSILON))
        self._updating = True
        self._slider.setValue(int(_round_prec(value, 0)))
        self._updating = False
        if not self._num.hasFocus():
            self._num.setText(_fmt_val(value, self._spec.dec))
        self._slider.set_track_colors(track_colors)

    def _on_slider_changed(self, value: int):
        if self._updating:
            return
        self._interface._on_base_channel(self._spec.key, float(value))

    def _on_num_finished(self):
        if self._updating:
            return
        parsed = _parse_num_loose(self._num.text())
        if parsed is None:
            self._interface._refresh_base()
            return
        self._interface._on_base_channel(self._spec.key, parsed)


# ==================== 界面 ====================

class PaletteTuningInterface(QWidget):
    """动态色彩微调调色板界面"""

    favorite_requested = Signal(dict)  # 收藏请求信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('paletteTuning')
        self._config_manager = get_config_manager()
        self._engine = self._load_engine()
        self._cards: list[TuneCard] = []
        self._base_rows: dict[str, BaseChannelRow] = {}
        self._hex_snapshot: tuple[str, str, dict[str, float]] | None = None
        self._updating_hex_input = False
        self._updating_count = False
        self._theme_connection = None
        self._language_connection = None

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.timeout.connect(self._save_state)

        self.setup_ui()
        self._sync_count_ui()
        self._update_styles()

        self._theme_connection = qconfig.themeChangedFinished.connect(self._update_styles)
        self._language_connection = get_locale_manager().language_changed.connect(
            self._on_language_changed
        )

        logger.info(f"色彩微调界面初始化完成: mode={self._engine.mode}, count={len(self._engine.items)}")

    # ---- 状态加载 / 保存 ----

    def _load_engine(self) -> PaletteTuningEngine:
        """从配置恢复引擎状态"""
        data = {
            'mode': self._config_manager.get('settings.palette_tuning_mode', 'hsb'),
            'base_rgb': self._config_manager.get(
                'settings.palette_tuning_base_rgb', [63.75, 127.5, 127.5]
            ),
            'count': self._config_manager.get('settings.palette_tuning_count', 6),
            'items': self._config_manager.get('settings.palette_tuning_items', []),
        }
        engine = from_palette_tuning_storage(data)
        logger.info(f"色彩微调状态恢复: mode={engine.mode}, count={len(engine.items)}")
        return engine

    def _mark_dirty(self):
        """标记状态已变更，启动防抖保存"""
        self._save_timer.start()

    def flush_save(self):
        """立即落盘（窗口关闭时调用）"""
        self._save_timer.stop()
        self._save_state()

    def _save_state(self):
        """将引擎状态写入配置"""
        data = to_palette_tuning_storage(self._engine)
        self._config_manager.set('settings.palette_tuning_mode', data['mode'])
        self._config_manager.set('settings.palette_tuning_base_rgb', data['base_rgb'])
        self._config_manager.set('settings.palette_tuning_count', len(self._engine.items))
        self._config_manager.set('settings.palette_tuning_items', data['items'])
        self._config_manager.save()

    # ---- 界面搭建 ----

    def setup_ui(self):
        """设置界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(0)
        splitter.setStyleSheet("QSplitter { border: none; background: transparent; }")
        splitter.addWidget(self._build_base_panel())
        splitter.addWidget(self._build_card_area())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 800])

        main_layout.addWidget(splitter)

    def _build_base_panel(self) -> QWidget:
        """左侧基色控制台"""
        panel = QWidget()
        panel.setMinimumWidth(340)
        panel.setMaximumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 24, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self._build_mode_switch(panel))

        # 大色块预览（点击打开取色器）
        self._base_swatch = ColorSwatch(110, parent=panel)
        self._base_swatch.setFixedHeight(110)
        self._base_swatch.clicked.connect(self._open_base_color_picker)
        layout.addLayout(self._build_hex_row(panel))
        layout.addWidget(self._base_swatch)

        layout.addWidget(self._build_base_rows(panel))
        self._rebuild_base_rows()

        # 数量控制 + 收藏整组（置于左栏，填充底部空白）
        layout.addWidget(self._build_count_controls(panel))
        self._favorite_button = PushButton(
            FluentIcon.HEART, tr('palette_tuning.favorite'), panel
        )
        self._favorite_button.clicked.connect(self._on_favorite_clicked)
        layout.addWidget(self._favorite_button)

        self._restore_button = PushButton(
            FluentIcon.SYNC, tr('palette_tuning.restore_default'), panel
        )
        self._restore_button.clicked.connect(self._on_restore_default)
        layout.addWidget(self._restore_button)
        layout.addStretch()

        return panel

    def _build_mode_switch(self, panel: QWidget) -> SegmentedWidget:
        """色彩模式分段控件"""
        self._mode_switch = SegmentedWidget(panel)
        self._mode_switch.setItemFontSize(11)
        for key, mode in MODES.items():
            self._mode_switch.addItem(key, mode.label)
        self._mode_switch.setCurrentItem(self._engine.mode)
        self._mode_switch.currentItemChanged.connect(self._on_mode_selected)
        return self._mode_switch

    def _build_hex_row(self, panel: QWidget) -> QHBoxLayout:
        """基色 HEX 输入行"""
        hex_row = QHBoxLayout()
        hex_row.setContentsMargins(0, 0, 0, 0)
        hex_row.setSpacing(6)
        self._base_hex_input = HexLineEdit(panel)
        self._base_hex_input.focus_handler = self._on_hex_focus_in
        self._base_hex_input.escape_handler = self._on_hex_escape
        self._base_hex_input.textChanged.connect(self._on_hex_text_changed)
        self._base_hex_input.editingFinished.connect(self._on_hex_editing_finished)
        self._copy_button = ToolButton(FluentIcon.COPY, panel)
        self._copy_button.setFixedSize(28, 28)
        self._copy_button.clicked.connect(self._copy_base_hex)
        hex_row.addWidget(self._base_hex_input, 1)
        hex_row.addWidget(self._copy_button)
        return hex_row

    def _build_base_rows(self, panel: QWidget) -> QWidget:
        """基色通道行容器"""
        self._base_rows_container = QWidget(panel)
        self._base_rows_layout = QVBoxLayout(self._base_rows_container)
        self._base_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._base_rows_layout.setSpacing(8)
        return self._base_rows_container

    def _build_count_controls(self, parent: QWidget) -> QWidget:
        """配色数量控制（标签 + 数值 + 滑块 + 步进）"""
        container = QWidget(parent)
        block_layout = QVBoxLayout(container)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        self._count_label = QLabel(tr('palette_tuning.count_label'), container)
        self._count_value_label = QLabel(str(len(self._engine.items)), container)
        self._count_value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        header.addStretch()
        header.addWidget(self._count_label)
        header.addWidget(self._count_value_label)
        header.addStretch()
        block_layout.addLayout(header)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self._count_dec = TransparentToolButton(FluentIcon.REMOVE, container)
        self._count_dec.setFixedSize(26, 26)
        self._count_dec.clicked.connect(lambda: self._change_count(-1))
        self._count_slider = Slider(Qt.Orientation.Horizontal, container)
        self._count_slider.setRange(MIN_COUNT, MAX_COUNT)
        self._count_slider.valueChanged.connect(self._on_count_slider_changed)
        self._count_inc = TransparentToolButton(FluentIcon.ADD, container)
        self._count_inc.setFixedSize(26, 26)
        self._count_inc.clicked.connect(lambda: self._change_count(1))
        row.addWidget(self._count_dec)
        row.addWidget(self._count_slider, 1)
        row.addWidget(self._count_inc)
        block_layout.addLayout(row)

        return container

    def _build_card_area(self) -> QWidget:
        """右侧配色卡片网格"""
        area = QWidget()
        layout = QVBoxLayout(area)
        # 顶部留白与左侧间距：与左栏内容对齐，并与控制区拉开距离
        layout.setContentsMargins(24, 18, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        self._scroll_area = ScrollArea(area)
        self._scroll_area.scrollDelagate.vScrollBar.setHandleDisplayMode(
            ScrollBarHandleDisplayMode.ON_HOVER
        )
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("ScrollArea { border: none; background: transparent; }")
        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        self._scroll_area.setCornerWidget(corner_widget)

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(0, 0, 14, 0)
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll_area.setWidget(self._grid_container)
        layout.addWidget(self._scroll_area, 1)

        self._rebuild_cards()
        return area

    def _rebuild_base_rows(self):
        """按当前模式重建基色通道行"""
        _clear_layout(self._base_rows_layout)
        self._base_rows = {}
        mode = MODES[self._engine.mode]
        for spec in mode.channels:
            row = BaseChannelRow(spec, self, self._base_rows_container)
            self._base_rows[spec.key] = row
            self._base_rows_layout.addWidget(row)

    def _rebuild_cards(self):
        """重建卡片网格（数量变化 / 恢复默认时调用）

        末行仅一张卡时让它跨满所有列，拉长居中独占整行（与渐变生成末行效果一致）
        """
        for card in self._cards:
            card.hide()
            card.deleteLater()
        self._cards.clear()
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

        for column in range(MAX_GRID_COLUMNS):
            self._grid.setColumnStretch(column, 0)

        columns = MAX_GRID_COLUMNS
        count = len(self._engine.items)
        lone_last_row = count % columns == 1
        for index, item in enumerate(self._engine.items):
            card = TuneCard(item, self._engine, self._mark_dirty, self._grid_container)
            card.update_styles()
            card.update_texts()
            self._cards.append(card)
            row, column = index // columns, index % columns
            if lone_last_row and index == count - 1:
                self._grid.addWidget(card, row, 0, 1, columns)
                for spanned_column in range(columns):
                    self._grid.setColumnStretch(spanned_column, 1)
            else:
                self._grid.addWidget(card, row, column)
                self._grid.setColumnStretch(column, 1)

    # ---- 刷新 ----

    def _refresh_all(self):
        """全量刷新基色与全部卡片"""
        self._refresh_base()
        for card in self._cards:
            card.refresh()

    def _refresh_base(self):
        """刷新基色控制台"""
        mode = MODES[self._engine.mode]
        channels = self._engine.base_channels()
        hex_value = hex_now(self._engine.base_rgb)

        self._base_swatch.set_color(hex_value)
        if not self._base_hex_input.hasFocus():
            self._set_hex_text(hex_value)

        display = {}
        for spec in mode.channels:
            display[spec.key] = _round_prec(channels[spec.key], spec.dec)
        for spec in mode.channels:
            row = self._base_rows.get(spec.key)
            if row is not None:
                row.refresh(display, _track_colors(spec, display, mode))

    # ---- 基色交互 ----

    def _on_base_channel(self, key: str, value: float):
        """基色通道值变更"""
        self._engine.set_base_channel(key, value)
        self._refresh_all()
        self._mark_dirty()

    def _step_base_channel(self, key: str, direction: int):
        """基色通道步进 ±1"""
        self._engine.step_base_channel(key, direction)
        self._refresh_all()
        self._mark_dirty()

    def _on_mode_selected(self, mode_key: str):
        """色彩模式切换"""
        self._commit_pending_inputs()
        if mode_key not in MODES or mode_key == self._engine.mode:
            return
        self._engine.switch_mode(mode_key)
        self._rebuild_base_rows()
        for card in self._cards:
            card.rebuild_rows()
        self._update_styles()
        self._mark_dirty()
        log_user_action('palette_tuning_switch_mode', {'mode': mode_key})

    def _commit_pending_inputs(self):
        """切换模式前提交焦点中的输入"""
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, QLineEdit):
            focus_widget.clearFocus()

    # ---- HEX 输入 ----

    def _on_hex_focus_in(self):
        """聚焦时快照基色状态"""
        self._hex_snapshot = (
            hex_now(self._engine.base_rgb),
            self._engine.mode,
            self._engine.base_channels()
        )

    def _on_hex_text_changed(self, text: str):
        """完整 6 位合法 HEX 即时预览"""
        if self._updating_hex_input:
            return
        raw = text.strip().lstrip('#')
        if len(raw) == 6 and parse_hex_input(raw) is not None:
            self._engine.set_base_hex(raw)
            self._refresh_all()
            self._mark_dirty()

    def _set_hex_text(self, hex_value: str):
        """程序化写入 HEX 文本（不触发即时预览）"""
        self._updating_hex_input = True
        self._base_hex_input.setText(hex_value)
        self._updating_hex_input = False

    def _on_hex_editing_finished(self):
        """回车 / 失焦提交，非法回退"""
        parsed = parse_hex_input(self._base_hex_input.text())
        if parsed is None:
            self._restore_hex_snapshot()
            self._set_hex_text(hex_now(self._engine.base_rgb))
            self._base_hex_input.setStyleSheet(_input_style_sheet(invalid=True))
            QTimer.singleShot(
                HEX_INVALID_FLASH_MS,
                lambda: self._base_hex_input.setStyleSheet(_input_style_sheet())
            )
            InfoBar.warning(
                title=tr('palette_tuning.hex_invalid_title'),
                content=tr('palette_tuning.hex_invalid'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=INFOBAR_DURATION_MS,
                parent=self.window()
            )
            return

        if hex_now(self._engine.base_rgb) != parsed:
            self._engine.set_base_hex(parsed)
            self._refresh_all()
            self._mark_dirty()
            log_user_action('palette_tuning_set_base_hex', {'hex': parsed})
        self._set_hex_text(hex_now(self._engine.base_rgb))

    def _on_hex_escape(self):
        """Esc 取消本次 HEX 编辑"""
        self._restore_hex_snapshot()
        self._set_hex_text(hex_now(self._engine.base_rgb))

    def _restore_hex_snapshot(self):
        """恢复到进入输入框前的基色状态"""
        assert self._hex_snapshot is not None, "HEX 输入框获得焦点时已建立快照"
        hex_value, mode_key, channels = self._hex_snapshot
        self._engine.set_base_hex(hex_value)
        if mode_key == self._engine.mode and mode_key != 'lab':
            for spec in MODES[mode_key].channels:
                self._engine.set_base_channel(spec.key, channels[spec.key])
        self._refresh_all()
        self._mark_dirty()

    def _copy_base_hex(self):
        """复制基色 HEX"""
        _copy_hex(hex_now(self._engine.base_rgb), self)

    def _open_base_color_picker(self):
        """点击色块打开取色器"""
        from dialogs import ColorPickerDialog

        r, g, b = hex_to_rgb(hex_now(self._engine.base_rgb))
        dialog = ColorPickerDialog((r, g, b), self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            color_info = dialog.get_color_info()
            if color_info:
                self._engine.set_base_hex(color_info.get('hex', ''))
                self._refresh_all()
                self._mark_dirty()
                log_user_action(
                    'palette_tuning_pick_base_color', {'hex': color_info.get('hex', '')}
                )

    # ---- 数量控制 ----

    def _sync_count_ui(self):
        """数量控件同步与边界禁用"""
        count = len(self._engine.items)
        self._updating_count = True
        self._count_slider.setValue(count)
        self._updating_count = False
        self._count_value_label.setText(str(count))

        self._count_dec.setEnabled(count > MIN_COUNT)
        self._count_inc.setEnabled(count < MAX_COUNT)

    def _on_count_slider_changed(self, value: int):
        if self._updating_count:
            return
        self._apply_count(value)

    def _change_count(self, delta: int):
        self._apply_count(len(self._engine.items) + delta)

    def _apply_count(self, count: int):
        """设置配色数量并重建卡片"""
        count = max(MIN_COUNT, min(MAX_COUNT, int(count)))
        if count == len(self._engine.items):
            self._sync_count_ui()
            return
        self._engine.set_count(count)
        self._rebuild_cards()
        self._sync_count_ui()
        self._mark_dirty()
        log_user_action('palette_tuning_change_count', {'count': count})

    # ---- 恢复默认 / 收藏 ----

    def _on_restore_default(self):
        """恢复默认调色板"""
        from dialogs import ConfirmDialog

        dialog = ConfirmDialog(
            tr('palette_tuning.restore_title'),
            tr('palette_tuning.restore_confirm'),
            self.window()
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._engine = PaletteTuningEngine()
        self._mode_switch.blockSignals(True)
        self._mode_switch.setCurrentItem(self._engine.mode)
        self._mode_switch.blockSignals(False)
        self._rebuild_base_rows()
        self._rebuild_cards()
        self._sync_count_ui()
        self._update_styles()
        self._mark_dirty()
        log_user_action('palette_tuning_restore_default', {})

    def _on_favorite_clicked(self):
        """收藏整组配色"""
        colors = []
        for item in self._engine.items:
            hex_value = hex_now(item.final_rgb)
            r, g, b = hex_to_rgb(hex_value)
            color_info = get_color_info(r, g, b)
            color_info['hex'] = hex_value
            colors.append(color_info)

        favorites_count = len(self._config_manager.get_favorites())
        default_name = tr('palette_tuning.favorite_name', count=favorites_count + 1)
        favorite_data = {
            'id': str(uuid.uuid4()),
            'name': default_name,
            'colors': colors,
            'created_at': datetime.now().isoformat(),
            'source': 'palette_tuning'
        }

        from dialogs import EditPaletteDialog
        dialog = EditPaletteDialog(
            default_name=default_name,
            palette_data=favorite_data,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_data = dialog.get_palette_data()
            if edited_data:
                self.favorite_requested.emit(edited_data)
                log_user_action('palette_tuning_favorite', {
                    'name': edited_data.get('name'),
                    'color_count': len(colors)
                })
                InfoBar.success(
                    title=tr('palette_tuning.favorite_success_title'),
                    content=tr('palette_tuning.favorite_success'),
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=INFOBAR_DURATION_MS,
                    parent=self.window()
                )

    # ---- 主题 / 语言 ----

    def _update_styles(self):
        """更新主题样式"""
        text_color = get_text_color()
        secondary_color = get_secondary_text_color()

        self._count_label.setStyleSheet(f"color: {text_color.name()}; font-size: 13px;")
        self._count_value_label.setStyleSheet(f"color: {secondary_color.name()}; font-size: 13px;")
        self._base_hex_input.setStyleSheet(_input_style_sheet())
        for row in self._base_rows.values():
            row.update_style()
        for card in self._cards:
            card.update_styles()

        self._refresh_all()

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        self._count_label.setText(tr('palette_tuning.count_label'))
        self._restore_button.setText(tr('palette_tuning.restore_default'))
        self._favorite_button.setText(tr('palette_tuning.favorite'))
        for row in self._base_rows.values():
            row.update_texts()
        for card in self._cards:
            card.update_texts()

    # ---- 生命周期 ----

    def closeEvent(self, event):
        """关闭时落盘并断开信号"""
        self._save_timer.stop()
        self._save_state()

        if self._theme_connection is not None:
            qconfig.themeChangedFinished.disconnect(self._theme_connection)
            self._theme_connection = None
        if self._language_connection is not None:
            get_locale_manager().language_changed.disconnect(self._language_connection)
            self._language_connection = None

        super().closeEvent(event)
