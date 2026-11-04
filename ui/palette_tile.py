"""悬浮配色磁贴：托盘唤出的只读收藏配色窗口"""

# 标准库导入
import sys

# 第三方库导入
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon,
    IconWidget,
    ScrollBarHandleDisplayMode,
    SearchLineEdit,
    SegmentedWidget,
    SimpleCardWidget,
    SmoothScrollArea,
    StrongBodyLabel,
    TransparentToggleToolButton,
    TransparentToolButton,
    qconfig,
    themeColor,
)

# 项目模块导入
from core import get_config_manager
from utils import load_icon_universal, set_window_topmost, show_and_activate_window, tr
from utils.theme_colors import (
    get_dialog_bg_color,
    get_floating_tile_shadow_color,
    get_secondary_text_color,
)

from .empty_state import EmptyStateWidget

# 卡片尺寸固定，不随收藏数量变化；窗口四周留出阴影与圆角空间
CARD_WIDTH = 380
CARD_HEIGHT = 460
WINDOW_MARGIN = 14

# 距屏幕可用区域边缘的间距
SCREEN_MARGIN = 24

# 内容区：每行色块数、色块高度、网格与组间距
COLUMNS = 4
SWATCH_MIN_HEIGHT = 46
GRID_HORIZONTAL_SPACING = 10
GRID_VERTICAL_SPACING = 12
GROUP_SPACING = 14
GROUP_HEADER_HEIGHT = 34

# 空状态在滚动区内的最小占位高度，避免贴顶
EMPTY_STATE_MIN_HEIGHT = 200

# 复制后 HEX 文本显示「已复制」的时长
COPY_LABEL_RESTORE_MS = 1000

ROUTE_ALL = 'all'
ROUTE_COMMON = 'common'


def _color_from_dict(hex_value: str, rgb: object) -> QColor:
    """按 rgb 优先、hex 兜底构造颜色，rgb 允许 tuple 或 JSON 反序列化后的 list"""
    if (
        isinstance(rgb, (tuple, list))
        and len(rgb) == 3
        and all(isinstance(channel, int) and 0 <= channel <= 255 for channel in rgb)
    ):
        return QColor(rgb[0], rgb[1], rgb[2])
    return QColor(hex_value)


def extract_swatch_data(favorite: dict) -> list[tuple[str, QColor]]:
    """提取一组收藏的可渲染色块：显示用 HEX 与绘制用颜色

    只读 colors 每项的 hex 与 rgb；缺 hex 或颜色非法时跳过该项。
    """
    swatches: list[tuple[str, QColor]] = []
    colors = favorite.get('colors') or []
    for color in colors:
        if not isinstance(color, dict):
            continue
        hex_value = color.get('hex')
        if not isinstance(hex_value, str) or not hex_value:
            continue
        display_hex = hex_value.upper()
        qcolor = _color_from_dict(display_hex, color.get('rgb'))
        if not qcolor.isValid():
            continue
        swatches.append((display_hex, qcolor))
    return swatches


def matches_query(search_keys: tuple[str, tuple[str, ...]], query: str) -> bool:
    """名称或任一 HEX 包含查询词即匹配；查询词为空时恒匹配"""
    if not query:
        return True
    name, hex_values = search_keys
    return query in name or any(query in hex_value for hex_value in hex_values)


def _start_window_move(widget: QWidget) -> None:
    """交给系统原生拖动窗口，避免跨平台手算坐标"""
    handle = widget.window().windowHandle()
    if handle is not None:
        handle.startSystemMove()


class TileCard(SimpleCardWidget):
    """磁贴卡片：不透明底色，避免色块颜色与主题背景混合"""

    def _normalBackgroundColor(self) -> QColor:
        return get_dialog_bg_color()

    def mousePressEvent(self, event) -> None:
        """卡片内边距等空白处也可拖动窗口；子控件区域的点击不受影响"""
        if event.button() == Qt.MouseButton.LeftButton \
                and self.childAt(event.position().toPoint()) is None:
            _start_window_move(self)
            event.accept()
            return
        super().mousePressEvent(event)


class ColorBlock(QWidget):
    """纯色色块：只填充直角纯色，保证第三方吸管取到标称色值"""

    clicked = Signal()

    def __init__(self, color: QColor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self.setMinimumHeight(SWATCH_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:
        """高度按色块最小高度上报，避免组数多时网格把色块压扁"""
        return QSize(64, SWATCH_MIN_HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return QSize(32, SWATCH_MIN_HEIGHT)

    def paintEvent(self, _event) -> None:
        """直角填充，不叠加描边、圆角或半透明像素"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._color)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class SwatchCard(QWidget):
    """单个色块 + HEX 文本，点击色块复制 HEX"""

    clicked = Signal(object)  # 信号：被点击的色块卡片自身

    def __init__(
        self,
        hex_value: str,
        color: QColor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._hex = hex_value
        self._hovered = False
        self._copied = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self._block = ColorBlock(color, self)
        self._block.clicked.connect(self._on_block_clicked)
        layout.addWidget(self._block)

        self._hex_label = CaptionLabel(hex_value, self)
        self._hex_label.pixelFontSize = 11
        self._hex_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hex_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._hex_label)

        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(self._reset_label)
        self.refresh_theme()

    @property
    def hex_value(self) -> str:
        """该色块对应的 HEX 值"""
        return self._hex

    def _on_block_clicked(self) -> None:
        self.clicked.emit(self)

    def show_copied(self) -> None:
        """复制后在原位显示「已复制」，避免浮层遮挡其它色值"""
        self._copied = True
        self._hex_label.setText(tr('palette_tile.copied'))
        self.refresh_theme()
        self._restore_timer.start(COPY_LABEL_RESTORE_MS)

    def _reset_label(self) -> None:
        self._copied = False
        self._hex_label.setText(self._hex)
        self.refresh_theme()

    def refresh_theme(self) -> None:
        """按悬停 / 已复制状态刷新 HEX 文本；色块本身不参与主题"""
        highlighted = self._copied or self._hovered
        color = themeColor() if highlighted else get_secondary_text_color()
        self._hex_label.setTextColor(color, color)
        font = self._hex_label.font()
        font.setBold(self._copied)
        self._hex_label.setFont(font)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.refresh_theme()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.refresh_theme()
        super().leaveEvent(event)


class GroupHeader(QWidget):
    """分组标题行：名称 + 折叠箭头"""

    clicked = Signal()

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(GROUP_HEADER_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 0)
        layout.setSpacing(8)

        self._name_label = StrongBodyLabel(name, self)
        self._name_label.pixelFontSize = 13
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._name_label)
        layout.addStretch()

        self._arrow = IconWidget(FluentIcon.CHEVRON_DOWN_MED, self)
        self._arrow.setFixedSize(16, 16)
        self._arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._arrow, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_expanded(self, expanded: bool) -> None:
        """箭头随折叠状态切换方向"""
        icon = FluentIcon.CHEVRON_DOWN_MED if expanded else FluentIcon.CHEVRON_RIGHT_MED
        self._arrow.setIcon(icon)

    def set_name(self, name: str) -> None:
        """更新标题文本；语言切换后由 PaletteGroup 重算"""
        self._name_label.setText(name)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton \
                and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PaletteGroup(QWidget):
    """一组收藏：标题行 + 可折叠的完整色块网格"""

    swatch_clicked = Signal(object)  # 信号：被点击的 SwatchCard
    toggled = Signal(str, bool)  # 信号：收藏 id, 是否展开

    def __init__(
        self,
        favorite: dict,
        expanded: bool,
        card_index: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.favorite_id = str(favorite.get('id', ''))
        self.pinned = bool(favorite.get('pinned', False))
        # 标题在语言切换后需重算，保留原始数据以重取 name 与序号
        self._favorite = favorite
        self._card_index = card_index
        swatches = extract_swatch_data(favorite)
        self._search_keys = (
            str(favorite.get('name', '')).lower(),
            tuple(hex_value.lower() for hex_value, _ in swatches),
        )
        self._expanded = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 序号与配色管理卡片一致，按收藏列表位置编号；无名称时用同一个兜底文案
        self._header = GroupHeader(self._title_text(), self)
        self._header.clicked.connect(self._toggle)
        layout.addWidget(self._header)

        self._body = QWidget(self)
        grid = QGridLayout(self._body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(GRID_HORIZONTAL_SPACING)
        grid.setVerticalSpacing(GRID_VERTICAL_SPACING)
        for column in range(COLUMNS):
            grid.setColumnStretch(column, 1)
        layout.addWidget(self._body)

        self._swatches: list[SwatchCard] = []
        for index, (hex_value, color) in enumerate(swatches):
            row, column = divmod(index, COLUMNS)
            card = SwatchCard(hex_value, color, self._body)
            card.clicked.connect(self.swatch_clicked)
            grid.addWidget(card, row, column)
            self._swatches.append(card)

        self.set_expanded(expanded)

    @property
    def swatches(self) -> list[SwatchCard]:
        """组内全部色块，供测试与主题刷新使用"""
        return self._swatches

    @property
    def expanded(self) -> bool:
        """当前是否展开"""
        return self._expanded

    def matches(self, query: str) -> bool:
        """名称或色值是否匹配搜索词"""
        return matches_query(self._search_keys, query)

    def _title_text(self) -> str:
        """组标题：全局序号 + 名称，无名称时用配色管理的兜底文案"""
        name = self._favorite.get('name', tr('palette_management.unnamed'))
        return f"{self._card_index + 1}.{name}"

    def retranslate(self) -> None:
        """语言切换后重算标题文本（用户名称本身不翻译）"""
        self._header.set_name(self._title_text())

    def set_expanded(self, expanded: bool) -> None:
        """设置折叠状态并同步箭头与组体可见性"""
        self._expanded = expanded
        self._header.set_expanded(expanded)
        self._body.setVisible(expanded)

    def refresh_theme(self) -> None:
        """主题切换后刷新组内色块文本颜色"""
        for card in self._swatches:
            card.refresh_theme()

    def _toggle(self) -> None:
        self.set_expanded(not self._expanded)
        self.toggled.emit(self.favorite_id, self._expanded)


class DragBar(QWidget):
    """标题栏空白区域：按住拖动窗口"""

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            _start_window_move(self)
            event.accept()
            return
        super().mousePressEvent(event)


class FloatingPaletteTile(QWidget):
    """悬浮配色磁贴：只读展示收藏配色，关闭时仅隐藏"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('floatingPaletteTile')

        self._favorites: list[dict] = []
        self._group_widgets: list[PaletteGroup] = []
        self._collapsed_ids: set[str] = set()
        self._query = ''
        self._route = ROUTE_COMMON

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
        # 右侧留出更宽的边距，避免滚动条紧贴卡片边缘
        card_layout.setContentsMargins(16, 12, 24, 14)
        card_layout.setSpacing(10)
        card_layout.addWidget(self._build_header(self._card))

        self._scroll = SmoothScrollArea(self._card)
        self._scroll.delegate.vScrollBar.setHandleDisplayMode(
            ScrollBarHandleDisplayMode.ON_HOVER
        )
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.enableTransparentBackground()
        self._scroll.viewport().setAutoFillBackground(False)
        card_layout.addWidget(self._scroll, 1)
        self._scroll.setWidget(self._build_content())

    def _build_content(self) -> QWidget:
        """构建滚动内容区：分组容器 + 空状态 + 尾部留白"""
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content)
        # 右侧留出滚动条展开时的宽度，色块不被滑块覆盖
        self._content_layout.setContentsMargins(0, 0, 14, 0)
        self._content_layout.setSpacing(GROUP_SPACING)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._groups_host = QWidget(self._content)
        self._groups_host.setStyleSheet("background: transparent;")
        self._groups_layout = QVBoxLayout(self._groups_host)
        self._groups_layout.setContentsMargins(0, 0, 0, 0)
        self._groups_layout.setSpacing(GROUP_SPACING)
        self._groups_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._content_layout.addWidget(self._groups_host)

        self._empty_widget = EmptyStateWidget(
            '⭐',
            'palette_tile.empty_title',
            'palette_tile.empty_hint',
            self._content,
        )
        self._empty_widget.setMinimumHeight(EMPTY_STATE_MIN_HEIGHT)
        self._empty_widget.hide()
        self._content_layout.addWidget(self._empty_widget)
        self._content_layout.addStretch(1)
        return self._content

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
        self._search.textChanged.connect(self._on_search_changed)
        top.addWidget(self._search, 1, Qt.AlignmentFlag.AlignVCenter)

        self._pin_button = TransparentToggleToolButton(FluentIcon.UNPIN, bar)
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
        self._segmented.currentItemChanged.connect(self._on_route_changed)
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
        for group in self._group_widgets:
            group.retranslate()
        self._empty_widget.retranslate()

    def _update_styles(self) -> None:
        """主题切换后刷新卡片阴影与色块文本颜色"""
        self._shadow.setColor(get_floating_tile_shadow_color())
        for group in self._group_widgets:
            group.refresh_theme()

    def mousePressEvent(self, event) -> None:
        """窗口透明外边距区域也可拖动窗口"""
        if event.button() == Qt.MouseButton.LeftButton \
                and not self._card.geometry().contains(event.position().toPoint()):
            _start_window_move(self)
            event.accept()
            return
        super().mousePressEvent(event)

    def show_and_activate(self) -> None:
        """显示并前置磁贴（重复唤出只前置，不新建窗口）"""
        show_and_activate_window(self)

    def showEvent(self, event) -> None:
        """每次显示都摆回屏幕右下角，并重读收藏"""
        super().showEvent(event)
        self._place_bottom_right()
        self._reload_favorites()

    def _place_bottom_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.move(
            available.right() - self.width() - SCREEN_MARGIN,
            available.bottom() - self.height() - SCREEN_MARGIN,
        )

    def _reload_favorites(self) -> None:
        """读取当前收藏并重建内容"""
        self._apply_favorites(get_config_manager().get_favorites())

    def _apply_favorites(self, favorites: list[dict]) -> None:
        """按收藏列表重建组控件；折叠状态按组 id 恢复"""
        self._favorites = favorites

        # 旧组先隐藏使其立即退出布局排布，延后销毁；析构时自动从布局移除
        for group in self._group_widgets:
            group.hide()
            group.deleteLater()
        self._group_widgets = []

        for index, favorite in enumerate(favorites):
            favorite_id = str(favorite.get('id', ''))
            group = PaletteGroup(
                favorite,
                expanded=favorite_id not in self._collapsed_ids,
                card_index=index,
                parent=self._groups_host,
            )
            group.toggled.connect(self._on_group_toggled)
            group.swatch_clicked.connect(self._copy_hex)
            self._groups_layout.addWidget(group)
            self._group_widgets.append(group)

        self._refresh_visibility(reset_scroll=True)

    def _on_group_toggled(self, favorite_id: str, expanded: bool) -> None:
        """记录用户显式收起 / 展开的组，重建后沿用"""
        if expanded:
            self._collapsed_ids.discard(favorite_id)
        else:
            self._collapsed_ids.add(favorite_id)

    def _on_route_changed(self, route_key: str) -> None:
        """切换全部 / 常用，滚动位置归零"""
        self._route = route_key
        self._refresh_visibility(reset_scroll=True)

    def _on_search_changed(self, text: str) -> None:
        """搜索词空 ↔ 非空时归零滚动位置，其余输入保持当前位置"""
        query = text.strip().lower()
        reset_scroll = bool(self._query) != bool(query)
        self._query = query
        self._refresh_visibility(reset_scroll=reset_scroll)

    def _refresh_visibility(self, reset_scroll: bool = False) -> None:
        """按 tab 与搜索词过滤组，并在无可见组时显示对应空状态"""
        visible_count = 0
        for group in self._group_widgets:
            visible = (self._route == ROUTE_ALL or group.pinned) and group.matches(self._query)
            group.setVisible(visible)
            if visible:
                visible_count += 1

        self._update_empty_state(visible_count)
        if reset_scroll:
            self._scroll.verticalScrollBar().setValue(0)

    def _update_empty_state(self, visible_count: int) -> None:
        """有可见组时隐藏空状态，否则按无匹配 / 无收藏 / 无常用区分"""
        if visible_count > 0:
            self._empty_widget.hide()
            return
        if self._query:
            self._empty_widget.set_state('🔍', 'palette_tile.no_match')
        elif self._route == ROUTE_COMMON and self._favorites:
            self._empty_widget.set_state(
                '📌',
                'palette_tile.pinned_empty_title',
                'palette_tile.pinned_empty_hint',
            )
        else:
            self._empty_widget.set_state(
                '⭐', 'palette_tile.empty_title', 'palette_tile.empty_hint'
            )
        self._empty_widget.show()

    def _copy_hex(self, card: SwatchCard) -> None:
        """复制色块 HEX 到剪贴板，并在色块原位提示"""
        QApplication.clipboard().setText(card.hex_value)
        card.show_copied()

    def _on_pin_toggled(self, checked: bool) -> None:
        """切换置顶状态并同步图钉图标；切换失败时回滚按钮，避免高亮与实际不符"""
        if set_window_topmost(self, checked):
            self._pin_button.setIcon(FluentIcon.PIN if checked else FluentIcon.UNPIN)
            return
        self._pin_button.blockSignals(True)
        self._pin_button.setChecked(not checked)
        self._pin_button.blockSignals(False)
