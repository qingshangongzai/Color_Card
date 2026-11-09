"""安装器迷你组件层

以 Qt 原生控件为基，样式基调交给 mini_style 生成的 QSS；输入框的聚焦下沿带、
进度条的轨道与块、复选框指示器三处是原型自绘的部分，按原版绘制路径静态复刻，
构造签名与现有调用点保持一致。
"""

# 第三方库导入
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStyle,
    QStyleOptionButton,
)

# 项目模块导入
from installer.wizard.mini_style import (
    checkbox_colors,
    checked_fill_colors,
    progress_track_rgba,
    resolve_tokens,
)

# 复选框指示器几何：20px 总边长（18px 内容 + 1px 透明描边）；圆角 4.5 与边框 1px
# 取自原型绘制代码（check_box.py: drawRoundedRect(rect, 4.5, 4.5) + 默认笔宽）
_INDICATOR_RADIUS = 4.5
_CHECK_PEN_WIDTH = 1.0
_BORDER_PEN_WIDTH = 1.0
_CHECK_POINTS = ((0.228, 0.497), (0.390, 0.651), (0.776, 0.303))

# 输入框焦点带几何：下沿 10px 高的圆角矩形减去上方 8px，剩 2px 可见带；两端由 5px 圆角内缩
_FOCUS_BAND_HEIGHT = 10
_FOCUS_BAND_CUT = 8
_FOCUS_BAND_RADIUS = 5

# 交互态 → 色表键后缀 / 绘制不透明度（原型仅对勾符号在禁用态压到 0.8）
_STATE_SUFFIX = {'normal': '', 'hover': '_hover', 'pressed': '_pressed', 'disabled': '_disabled'}
_STATE_OPACITY = {'normal': 1.0, 'hover': 1.0, 'pressed': 1.0, 'disabled': 0.8}


class PrimaryPushButton(QPushButton):
    """主按钮：由 QSS 的 PrimaryPushButton 选择器着色"""


class PushButton(QPushButton):
    """中性按钮：由 QSS 的 QPushButton 选择器着色"""


class LineEdit(QLineEdit):
    """单行输入框：QSS 驱动，聚焦时补一条原型的下沿高亮带"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(33)
        self._accent = QColor(resolve_tokens()['accent'])

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.hasFocus():
            return

        # 原型先画内容再叠带子：文字因此在聚焦前后位置不动。带子为下沿 10px 高的圆角矩形
        # 减去上方 8px，只剩 2px 高、两端各内缩约 5px
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        m = self.contentsMargins()
        w = self.width() - m.left() - m.right()
        h = self.height()
        band = QPainterPath()
        band.addRoundedRect(
            QRectF(m.left(), h - _FOCUS_BAND_HEIGHT, w, _FOCUS_BAND_HEIGHT),
            _FOCUS_BAND_RADIUS, _FOCUS_BAND_RADIUS,
        )
        cut = QPainterPath()
        cut.addRect(m.left(), h - _FOCUS_BAND_HEIGHT, w, _FOCUS_BAND_CUT)
        painter.fillPath(band.subtracted(cut), self._accent)


class ProgressBar(QProgressBar):
    """进度条：自绘 1px 居中轨道线与圆角块，隐藏内建百分比文字（页面另有独立标签）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self._track = QColor(*progress_track_rgba())
        self._bar = QColor(resolve_tokens()['accent'])

    def paintEvent(self, event):
        # 不调 super()：原型的轨道是 1px 横线、其余区域透明，QSS 的整高填充画不出来。
        # 1px 画笔在抗锯齿下会落在相邻两行各约 50%（h=6 时第 2、3 行），这是原版实测形态，
        # 不要为「看起来是 1px」改笔宽或挪半像素
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(self._track)
        y = self.height() // 2
        painter.drawLine(0, y, self.width(), y)

        if self.minimum() >= self.maximum():
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bar)
        w = int(self.value() / (self.maximum() - self.minimum()) * self.width())
        radius = self.height() / 2
        painter.drawRoundedRect(0, 0, w, self.height(), radius, radius)


class CheckBox(QCheckBox):
    """复选框：文字与焦点框由基类绘制，20×20 圆角指示器静态自绘"""

    def __init__(self, text: str = '', parent=None):
        super().__init__(text, parent)
        self._tokens = resolve_tokens()
        self._checked_fill = checked_fill_colors()
        self._indicator = checkbox_colors()
        self._hovered = False
        self._pressed = False

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, option, self
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_indicator(painter, QRectF(rect))

    def _state(self) -> str:
        """当前交互态名，用作色表键后缀"""
        if not self.isEnabled():
            return 'disabled'
        if self._pressed:
            return 'pressed'
        if self._hovered:
            return 'hover'
        return 'normal'

    def _draw_indicator(self, painter: QPainter, rect: QRectF):
        """在 indicator 矩形内绘制静态圆角指示器

        Args:
            painter: 当前绘制器
            rect: 基类样式给出的 indicator 区域
        """
        tokens = self._tokens
        side = min(rect.width(), rect.height())
        box = QRectF(rect.x(), rect.y() + (rect.height() - side) / 2, side, side)
        state = self._state()
        suffix = _STATE_SUFFIX[state]

        if self.isChecked():
            if state == 'disabled':
                fill = QColor(*self._indicator['checked_disabled'])
                painter.setPen(Qt.PenStyle.NoPen)
            else:
                fill = QColor(self._checked_fill[state])
                painter.setPen(QPen(fill, _BORDER_PEN_WIDTH))
            painter.setBrush(fill)
            painter.drawRoundedRect(box, _INDICATOR_RADIUS, _INDICATOR_RADIUS)

            pen = QPen(QColor(tokens['on_accent']))
            pen.setWidthF(_CHECK_PEN_WIDTH)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setOpacity(_STATE_OPACITY[state])
            check = QPainterPath()
            start, *rest = _CHECK_POINTS
            check.moveTo(box.left() + side * start[0], box.top() + side * start[1])
            for ratio_x, ratio_y in rest:
                check.lineTo(box.left() + side * ratio_x, box.top() + side * ratio_y)
            painter.drawPath(check)
            return

        # 未勾选：描边与浅底色按原型的 normal / hover / pressed / disabled 取值。原型用默认
        # 1px 画笔直接画在 indicator 矩形上（描边跨路径两侧各 0.5px），这里同法绘制；
        # 若把矩形外扩 0.5px，整圈描边会外移半个像素，圆角处与原型明显不同
        pen = QPen(QColor(*self._indicator['border' + suffix]), _BORDER_PEN_WIDTH)
        painter.setPen(pen)
        painter.setBrush(QColor(*self._indicator['bg' + suffix]))
        painter.drawRoundedRect(box, _INDICATOR_RADIUS, _INDICATOR_RADIUS)
