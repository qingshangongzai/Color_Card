"""悬浮配色磁贴：托盘唤出的只读收藏配色窗口"""

# 标准库导入
import sys

# 第三方库导入
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    FluentIcon,
    HorizontalSeparator,
    SearchLineEdit,
    SegmentedWidget,
    SimpleCardWidget,
    SmoothScrollArea,
    TransparentToggleToolButton,
    TransparentToolButton,
    qconfig,
)

# 项目模块导入
from utils import load_icon_universal, set_window_topmost, show_and_activate_window, tr
from utils.theme_colors import get_dialog_bg_color, get_floating_tile_shadow_color

# 卡片尺寸固定，不随收藏数量变化；窗口四周留出阴影与圆角空间
CARD_WIDTH = 380
CARD_HEIGHT = 460
WINDOW_MARGIN = 14

# 距屏幕可用区域边缘的间距
SCREEN_MARGIN = 24

ROUTE_ALL = 'all'
ROUTE_COMMON = 'common'


class TileCard(SimpleCardWidget):
    """磁贴卡片：不透明底色，避免色块颜色与主题背景混合"""

    def _normalBackgroundColor(self) -> QColor:
        return get_dialog_bg_color()


class DragBar(QWidget):
    """标题栏空白区域：按住拖动窗口"""

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)


class FloatingPaletteTile(QWidget):
    """悬浮配色磁贴：只读展示收藏配色，关闭时仅隐藏"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('floatingPaletteTile')

        # 顶层窗口：主窗口隐藏到托盘时不连带隐藏；不含置顶标志，置顶由 SetWindowPos 切换
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(CARD_WIDTH + WINDOW_MARGIN * 2, CARD_HEIGHT + WINDOW_MARGIN * 2)

        self._setup_ui()
        self.update_texts()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def _setup_ui(self) -> None:
        """构建卡片、标题栏与滚动区"""
        root = QVBoxLayout(self)
        root.setContentsMargins(WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN)
        root.setSpacing(0)

        self._card = TileCard(self)
        self._card.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self._card.setBorderRadius(12)
        self._shadow = QGraphicsDropShadowEffect(self._card)
        self._shadow.setBlurRadius(28)
        self._shadow.setOffset(0, 6)
        self._card.setGraphicsEffect(self._shadow)
        root.addWidget(self._card)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(16, 12, 16, 14)
        card_layout.setSpacing(10)
        card_layout.addWidget(self._build_header(self._card))
        card_layout.addWidget(HorizontalSeparator(self._card))

        self._scroll = SmoothScrollArea(self._card)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.enableTransparentBackground()
        self._scroll.viewport().setAutoFillBackground(False)
        card_layout.addWidget(self._scroll, 1)

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 6, 0)
        self._content_layout.setSpacing(14)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._content)

    def _build_header(self, parent: QWidget) -> QWidget:
        """构建两行标题栏：logo + 搜索 + 窗口钉/关闭，下方为全部/常用切换"""
        bar = DragBar(parent)
        bar.setFixedHeight(68)
        bar_layout = QVBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(6)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        top.addWidget(self._build_logo(bar), 0, Qt.AlignmentFlag.AlignVCenter)

        self._search = SearchLineEdit(bar)
        self._search.setFixedHeight(32)
        top.addWidget(self._search, 1, Qt.AlignmentFlag.AlignVCenter)

        self._pin_button = TransparentToggleToolButton(FluentIcon.PIN, bar)
        self._pin_button.setFixedSize(28, 28)
        self._pin_button.toggled.connect(self._on_pin_toggled)
        top.addWidget(self._pin_button, 0, Qt.AlignmentFlag.AlignVCenter)
        if sys.platform != 'win32':
            # 置顶仅 Windows 可用，避免 mac 上出现无效开关
            self._pin_button.setEnabled(False)

        self._close_button = TransparentToolButton(FluentIcon.CLOSE, bar)
        self._close_button.setFixedSize(28, 28)
        self._close_button.clicked.connect(self.hide)
        top.addWidget(self._close_button, 0, Qt.AlignmentFlag.AlignVCenter)
        bar_layout.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        self._segmented = SegmentedWidget(bar)
        self._segmented.setFixedHeight(30)
        self._segmented.addItem(ROUTE_ALL, '')
        self._segmented.addItem(ROUTE_COMMON, '')
        self._segmented.setCurrentItem(ROUTE_COMMON)
        bottom.addStretch()
        bottom.addWidget(self._segmented, 0, Qt.AlignmentFlag.AlignVCenter)
        bottom.addStretch()
        bar_layout.addLayout(bottom)

        return bar

    def _build_logo(self, parent: QWidget) -> QLabel:
        """应用 logo，固定 22px"""
        logo = QLabel(parent)
        logo.setFixedSize(22, 22)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(load_icon_universal().pixmap(QSize(22, 22)))
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        return logo

    def update_texts(self) -> None:
        """刷新语言相关文案（语言切换后调用）"""
        self.setWindowTitle(tr('palette_tile.title'))
        self._search.setPlaceholderText(tr('palette_tile.search_placeholder'))
        self._pin_button.setToolTip(tr('palette_tile.pin_tooltip'))
        self._close_button.setToolTip(tr('palette_tile.close_tooltip'))
        self._segmented.setItemText(ROUTE_ALL, tr('palette_tile.tab_all'))
        self._segmented.setItemText(ROUTE_COMMON, tr('palette_tile.tab_common'))

    def _update_styles(self) -> None:
        """主题切换后刷新卡片阴影颜色"""
        self._shadow.setColor(get_floating_tile_shadow_color())

    def show_and_activate(self) -> None:
        """显示并前置磁贴（重复唤出只前置，不新建窗口）"""
        show_and_activate_window(self)

    def showEvent(self, event) -> None:
        """每次显示都摆回屏幕右下角"""
        super().showEvent(event)
        self._place_bottom_right()

    def _place_bottom_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.move(
            available.right() - self.width() - SCREEN_MARGIN,
            available.bottom() - self.height() - SCREEN_MARGIN,
        )

    def _on_pin_toggled(self, checked: bool) -> None:
        """切换置顶状态；失败时回滚按钮，避免显示与实际不一致"""
        if set_window_topmost(self, checked):
            return
        self._pin_button.blockSignals(True)
        self._pin_button.setChecked(not checked)
        self._pin_button.blockSignals(False)
