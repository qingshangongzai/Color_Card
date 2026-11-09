"""安装器迷你组件层

以 Qt 原生控件为基，样式全部交给 mini_style 生成的 QSS；除复选框指示器、
进度条文字隐藏与输入框固定高度外不做额外重写，构造签名与现有调用点保持一致。
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
from installer.wizard.mini_style import checkbox_colors, resolve_tokens

# 复选框指示器几何：20px 总边长（18px 内容 + 1px 透明描边）；圆角 4.5 与边框 1px
# 取自原型绘制代码（check_box.py: drawRoundedRect(rect, 4.5, 4.5) + 默认笔宽）
_INDICATOR_RADIUS = 4.5
_CHECK_PEN_WIDTH = 1.0
_BORDER_PEN_WIDTH = 1.0
_CHECK_POINTS = ((0.228, 0.497), (0.390, 0.651), (0.776, 0.303))

# 交互态 → 色表键后缀 / 绘制不透明度（原型仅对勾符号在禁用态压到 0.8）
_STATE_SUFFIX = {'normal': '', 'hover': '_hover', 'pressed': '_pressed', 'disabled': '_disabled'}
_STATE_OPACITY = {'normal': 1.0, 'hover': 1.0, 'pressed': 1.0, 'disabled': 0.8}


class PrimaryPushButton(QPushButton):
    """主按钮：由 QSS 的 PrimaryPushButton 选择器着色"""


class PushButton(QPushButton):
    """中性按钮：由 QSS 的 QPushButton 选择器着色"""


class LineEdit(QLineEdit):
    """单行输入框：由 QSS 驱动，高度取原型固定值 33px"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(33)


class ProgressBar(QProgressBar):
    """进度条：由 QSS 驱动，隐藏内建百分比文字（页面另有独立百分比标签）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)


class CheckBox(QCheckBox):
    """复选框：文字与焦点框由基类绘制，20×20 圆角指示器静态自绘"""

    def __init__(self, text: str = '', parent=None):
        super().__init__(text, parent)
        self._tokens = resolve_tokens()
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
            else:
                fill = QColor(tokens['accent' + suffix])
            painter.setPen(Qt.PenStyle.NoPen)
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

        # 未勾选：描边与浅底色按原型的 normal / hover / pressed / disabled 取值
        border_box = box.adjusted(-0.5, -0.5, 0.5, 0.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(*self._indicator['bg' + suffix]))
        painter.drawRoundedRect(box, _INDICATOR_RADIUS, _INDICATOR_RADIUS)

        pen = QPen(QColor(*self._indicator['border' + suffix]))
        pen.setWidthF(_BORDER_PEN_WIDTH)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(border_box, _INDICATOR_RADIUS, _INDICATOR_RADIUS)
