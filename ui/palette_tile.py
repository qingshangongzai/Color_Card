"""悬浮配色磁贴：托盘唤出的只读收藏配色窗口"""

# 标准库导入
import sys
from dataclasses import dataclass

# 第三方库导入
from PySide6.QtCore import QEvent, QRect, QSize, Qt, QTimer, Signal
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
from utils import (
    load_icon_universal,
    set_window_tool_style,
    set_window_topmost,
    show_and_activate_window,
    tr,
)
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
GROUP_HEADER_SPACING = 8

# 「全部」行视图最多预览的色点数与色点尺寸
ROW_PREVIEW_COUNT = 5
ROW_DOT_SIZE = 12
ROW_DOT_SPACING = 6

# 已建组体回收上限；按提交内存增量与滚动渲染耗时实测确定
MAX_LIVE_GROUPS = 40

# 组内容形态
FORM_GRID = 'grid'
FORM_COLLAPSED = 'collapsed'
FORM_ROW = 'row'

# 空状态在滚动区内的最小占位高度，避免贴顶
EMPTY_STATE_MIN_HEIGHT = 200

# 复制后 HEX 文本显示「已复制」的时长
COPY_LABEL_RESTORE_MS = 1000

# 收藏变更的合并窗口；同一窗口内的多次变更只触发一次刷新
REFRESH_DEBOUNCE_MS = 50

# 已建变更组数达到该值时改走一次保状态全量重建
FULL_REBUILD_THRESHOLD = 10

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


# 颜色指纹：(hex, rgb)；收藏指纹：(name, colors, pinned)
ColorFingerprint = tuple[str, tuple[int, ...] | None]
FavoriteFingerprint = tuple[str, tuple[ColorFingerprint, ...], bool]


def favorite_fingerprint(favorite: dict) -> FavoriteFingerprint:
    """只复制影响显示的字段，避免持有配置内部 dict 的引用"""
    color_items: list[ColorFingerprint] = []
    colors = favorite.get('colors') or []
    for color in colors:
        if not isinstance(color, dict):
            continue
        hex_value = color.get('hex')
        rgb = color.get('rgb')
        rgb_tuple = tuple(rgb) if isinstance(rgb, (tuple, list)) else None
        color_items.append((str(hex_value or ''), rgb_tuple))
    return (
        str(favorite.get('name', '')),
        tuple(color_items),
        bool(favorite.get('pinned', False)),
    )


def build_favorites_snapshot(favorites: list[dict]) -> dict[str, FavoriteFingerprint]:
    """按收藏顺序生成 id → 指纹 的快照"""
    return {
        str(favorite.get('id', '')): favorite_fingerprint(favorite)
        for favorite in favorites
    }


@dataclass
class GroupModel:
    """一组收藏的只读数据模型：不建控件也能完成搜索与高度计算"""

    favorite_id: str
    favorite: dict
    card_index: int
    pinned: bool
    swatches: list[tuple[str, QColor]]
    search_keys: tuple[str, tuple[str, ...]]
    card_height: int
    row_height: int

    def matches(self, query: str) -> bool:
        """名称或色值是否匹配搜索词"""
        return matches_query(self.search_keys, query)

    def title_text(self) -> str:
        """组标题：全局序号 + 名称，无名称时用配色管理的兜底文案"""
        name = self.favorite.get('name', tr('palette_management.unnamed'))
        return f"{self.card_index + 1}.{name}"

    def height_for(self, form: str) -> int:
        """按形态返回组的固定高度，供占位与内容控件保持一致"""
        if form == FORM_ROW:
            return self.row_height
        if form == FORM_COLLAPSED:
            return GROUP_HEADER_HEIGHT
        rows = -(-len(self.swatches) // COLUMNS)
        grid_height = rows * self.card_height + max(rows - 1, 0) * GRID_VERTICAL_SPACING
        return GROUP_HEADER_HEIGHT + GROUP_HEADER_SPACING + grid_height


def build_group_model(
    favorite: dict,
    card_index: int,
    card_height: int,
    row_height: int,
) -> GroupModel:
    """从收藏 dict 构造模型；色块只解析一次，搜索键从同一份色块派生"""
    swatches = extract_swatch_data(favorite)
    search_keys = (
        str(favorite.get('name', '')).lower(),
        tuple(hex_value.lower() for hex_value, _ in swatches),
    )
    return GroupModel(
        favorite_id=str(favorite.get('id', '')),
        favorite=favorite,
        card_index=card_index,
        pinned=bool(favorite.get('pinned', False)),
        swatches=swatches,
        search_keys=search_keys,
        card_height=card_height,
        row_height=row_height,
    )


def _start_window_move(widget: QWidget) -> None:
    """交给系统原生拖动窗口，避免跨平台手算坐标"""
    window = widget.window()
    # NOACTIVATE 窗口点击不抢前台也不改变 z 序，拖动前先提升，避免拖到下层
    window.raise_()
    handle = window.windowHandle()
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
    """分组标题行：名称 + 最多 5 个色点 + 折叠箭头"""

    clicked = Signal()

    def __init__(self, model: GroupModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_name = model.title_text()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(GROUP_HEADER_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 0)
        layout.setSpacing(8)

        self._name_label = StrongBodyLabel(self._full_name, self)
        self._name_label.pixelFontSize = 13
        self._name_label.setMinimumWidth(0)
        self._name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._name_label, 1)

        # 与「全部」行视图一致：色点仅预览，不承担复制与取色
        self._preview = RowColorDots(model.swatches, self)
        layout.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignVCenter)

        self._arrow = IconWidget(FluentIcon.CHEVRON_DOWN_MED, self)
        self._arrow.setFixedSize(16, 16)
        self._arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._arrow, 0, Qt.AlignmentFlag.AlignVCenter)

    def resizeEvent(self, event) -> None:
        """宽度变化后按可用宽度省略过长标题"""
        super().resizeEvent(event)
        self._apply_elided_name()

    def _apply_elided_name(self) -> None:
        width = self._name_label.width()
        if width <= 0:
            self._name_label.setText(self._full_name)
            return
        self._name_label.setText(
            self._name_label.fontMetrics().elidedText(
                self._full_name,
                Qt.TextElideMode.ElideRight,
                width,
            )
        )

    def set_expanded(self, expanded: bool) -> None:
        """箭头随折叠状态切换方向"""
        icon = FluentIcon.CHEVRON_DOWN_MED if expanded else FluentIcon.CHEVRON_RIGHT_MED
        self._arrow.setIcon(icon)

    def set_name(self, name: str) -> None:
        """更新标题文本；语言切换后由 PaletteGroup 重算"""
        self._full_name = name
        self._apply_elided_name()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton \
                and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class RowColorDots(QWidget):
    """行视图的色点预览：单控件绘制，不承担复制与取色"""

    def __init__(
        self,
        swatches: list[tuple[str, QColor]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._colors = [color for _, color in swatches[:ROW_PREVIEW_COUNT]]
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        count = len(self._colors)
        width = count * ROW_DOT_SIZE + max(count - 1, 0) * ROW_DOT_SPACING
        self.setFixedSize(width, ROW_DOT_SIZE)

    def paintEvent(self, _event) -> None:
        """按序绘制圆点；允许抗锯齿，色点仅预览"""
        if not self._colors:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        for index, color in enumerate(self._colors):
            painter.setBrush(color)
            x = index * (ROW_DOT_SIZE + ROW_DOT_SPACING)
            painter.drawEllipse(QRect(x, 0, ROW_DOT_SIZE, ROW_DOT_SIZE))


class GroupRow(QWidget):
    """「全部」行视图：名称 + 最多 5 个色点 + 展开箭头"""

    opened = Signal(str)  # 信号：收藏 id

    def __init__(self, model: GroupModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._full_title = model.title_text()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 0)
        layout.setSpacing(8)

        self._name_label = StrongBodyLabel(self._full_title, self)
        self._name_label.pixelFontSize = 13
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._name_label, 1)

        self._preview = RowColorDots(model.swatches, self)
        layout.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignVCenter)

        # 与「常用」的收起标题一致：右向箭头表示可展开
        self._arrow = IconWidget(FluentIcon.CHEVRON_RIGHT_MED, self)
        self._arrow.setFixedSize(16, 16)
        self._arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._arrow, 0, Qt.AlignmentFlag.AlignVCenter)

    def sizeHint(self) -> QSize:
        """行高与组标题一致，供占位标定"""
        return QSize(200, GROUP_HEADER_HEIGHT)

    def resizeEvent(self, event) -> None:
        """按可用宽度省略过长名称，避免把预览色块挤出可视区"""
        self._apply_elided_title()
        super().resizeEvent(event)

    def _apply_elided_title(self) -> None:
        elided = self._name_label.fontMetrics().elidedText(
            self._full_title,
            Qt.TextElideMode.ElideRight,
            self._name_label.width(),
        )
        self._name_label.setText(elided)

    def retranslate(self) -> None:
        """语言切换后重算标题（用户名称本身不翻译）"""
        self._full_title = self._model.title_text()
        self._apply_elided_title()

    def refresh_theme(self) -> None:
        """主题切换后按新字体重新省略标题"""
        self._apply_elided_title()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton \
                and self.rect().contains(event.position().toPoint()):
            self.opened.emit(self._model.favorite_id)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PaletteGroup(QWidget):
    """一组收藏：标题行 + 可折叠的完整色块网格"""

    swatch_clicked = Signal(object)  # 信号：被点击的 SwatchCard
    toggled = Signal(str, bool)  # 信号：收藏 id, 是否展开

    def __init__(
        self,
        model: GroupModel,
        expanded: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self.favorite_id = model.favorite_id
        self._expanded = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GROUP_HEADER_SPACING)

        self._header = GroupHeader(model, self)
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
        for index, (hex_value, color) in enumerate(model.swatches):
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

    def retranslate(self) -> None:
        """语言切换后重算标题文本（用户名称本身不翻译）"""
        self._header.set_name(self._model.title_text())

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


class GroupSlot(QWidget):
    """一组收藏的固定高度占位；已建时持有真实控件，回收后只保留高度"""

    def __init__(
        self,
        model: GroupModel,
        form: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.form = form
        self.content: PaletteGroup | GroupRow | None = None
        self.last_seen = 0
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setFixedHeight(model.height_for(form))

    def attach(self, content: PaletteGroup | GroupRow) -> None:
        """放入真实控件；slot 高度不变，内容由布局填满"""
        self.content = content
        self._layout.addWidget(content)

    def recycle(self) -> None:
        """丢弃真实控件，保留占位高度"""
        if self.content is None:
            return
        self._layout.removeWidget(self.content)
        self.content.hide()
        self.content.deleteLater()
        self.content = None

    def set_model(self, model: GroupModel) -> None:
        """替换模型并按当前形态重算高度"""
        self.model = model
        self.setFixedHeight(model.height_for(self.form))

    def set_form(self, form: str) -> None:
        """切换形态；已有内容随形态作废"""
        if self.form == form:
            return
        self.recycle()
        self.form = form
        self.setFixedHeight(self.model.height_for(form))

    def retranslate(self) -> None:
        if self.content is not None:
            self.content.retranslate()

    def refresh_theme(self) -> None:
        if self.content is not None:
            self.content.refresh_theme()


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

        self._config_manager = get_config_manager()
        self._favorites: list[dict] = []
        self._snapshot: dict[str, FavoriteFingerprint] = {}
        self._dirty = False
        self._loaded = False
        self._tool_style_applied = False
        self._slots: list[GroupSlot] = []
        self._slot_by_id: dict[str, GroupSlot] = {}
        self._collapsed_ids: set[str] = set()
        self._row_open_ids: set[str] = set()
        self._query = ''
        self._route = ROUTE_COMMON
        self._max_live_groups = MAX_LIVE_GROUPS
        self._tick = 0
        self._layout_dirty = False

        # 单次定时器负责合并同一轮收藏变更；每次变更 start() 重启
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._flush_refresh)
        self._config_manager.favorites_changed.connect(self._on_favorites_changed)

        # 顶层窗口：主窗口隐藏到托盘时不连带隐藏；不含置顶标志，置顶由 SetWindowPos 切换
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(CARD_WIDTH + WINDOW_MARGIN * 2, CARD_HEIGHT + WINDOW_MARGIN * 2)

        self._setup_ui()
        self._card_height, self._row_height = self._calibrate_heights()
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
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
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
        # 过滤只在回车 / 搜索按钮时生效，输入过程不重建列表；
        # 文本被删空时立即恢复全部，避免界面停留在无提示的过滤态
        self._search.returnPressed.connect(self._search.search)
        self._search.searchSignal.connect(self._apply_search_query)
        self._search.clearSignal.connect(self._on_search_cleared)
        self._search.textChanged.connect(self._on_search_text_changed)
        # NOACTIVATE 窗口点击不激活，点搜索框时需显式激活才能接收键盘输入
        self._search.installEventFilter(self)
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

    def _calibrate_heights(self) -> tuple[int, int]:
        """量一次真实色块卡片高度；行视图高度固定为组标题高度"""
        swatch = SwatchCard('#000000', QColor('#000000'))
        swatch.ensurePolished()
        card_height = swatch.sizeHint().height()
        swatch.deleteLater()
        return card_height, GROUP_HEADER_HEIGHT

    def update_texts(self) -> None:
        """刷新语言相关文案（语言切换后调用）"""
        self.setWindowTitle(tr('palette_tile.title'))
        self._search.setPlaceholderText(tr('palette_tile.search_placeholder'))
        self._pin_button.setToolTip(tr('palette_tile.pin_tooltip'))
        self._close_button.setToolTip(tr('palette_tile.close_tooltip'))
        self._segmented.setItemText(ROUTE_ALL, tr('palette_tile.tab_all'))
        self._segmented.setItemText(ROUTE_COMMON, tr('palette_tile.tab_common'))
        for slot in self._slots:
            slot.retranslate()
        self._empty_widget.retranslate()

    def _update_styles(self) -> None:
        """主题切换后刷新卡片阴影与色块文本颜色"""
        self._shadow.setColor(get_floating_tile_shadow_color())
        for slot in self._slots:
            slot.refresh_theme()

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
        """每次显示摆回屏幕右下角；首次读取收藏，之后按指纹比对"""
        super().showEvent(event)
        if not self._tool_style_applied:
            # 首次显示后一次性设置工具窗口样式（不进任务栏 / Alt+Tab，
            # 点击与拖动不抢前台）；失败时下次显示重试
            self._tool_style_applied = set_window_tool_style(self)
        self._place_bottom_right()
        if not self._loaded:
            self._reload_favorites()
            return
        if self._dirty:
            # 隐藏期间的变更只标脏，显示时统一走一次比对；无变化零重建
            self._refresh_timer.stop()
            self._flush_refresh()

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
        """首次显示时读取当前收藏并重建内容"""
        self._apply_favorites(self._config_manager.get_favorites())
        self._loaded = True

    def _apply_favorites(self, favorites: list[dict], reset_scroll: bool = True) -> None:
        """重建组占位；真实控件按视口懒创建

        Args:
            favorites: 收藏列表
            reset_scroll: 是否把滚动位置归零；刷新场景传 False 以保留交互状态
        """
        self._favorites = favorites

        for slot in self._slots:
            slot.recycle()
            slot.hide()
            slot.deleteLater()
        self._slots = []
        self._slot_by_id = {}

        for index, favorite in enumerate(favorites):
            model = build_group_model(favorite, index, self._card_height, self._row_height)
            slot = GroupSlot(model, self._form_for(model), self._groups_host)
            self._groups_layout.addWidget(slot)
            self._slots.append(slot)
            self._slot_by_id[model.favorite_id] = slot

        self._refresh_visibility(reset_scroll=reset_scroll)
        self._snapshot = build_favorites_snapshot(self._favorites)
        self._dirty = False
        # 首屏布局可能尚未完成，延后一拍按真实视口高度补建
        QTimer.singleShot(0, self._sync_viewport)

    def _on_favorites_changed(self) -> None:
        """收藏变更：隐藏时只标脏，显示时重启 50ms 合并窗口"""
        self._dirty = True
        if self.isVisible():
            self._refresh_timer.start(REFRESH_DEBOUNCE_MS)

    def _flush_refresh(self) -> None:
        """按 id 指纹 diff 增量刷新；超阈值改走一次保状态全量重建"""
        if not self.isVisible():
            self._dirty = True
            return

        favorites = self._config_manager.get_favorites()
        snapshot = build_favorites_snapshot(favorites)
        if snapshot == self._snapshot and list(snapshot) == list(self._snapshot):
            self._dirty = False
            return

        old_ids = list(self._snapshot)
        new_ids = list(snapshot)
        common_old = [favorite_id for favorite_id in old_ids if favorite_id in snapshot]
        common_new = [favorite_id for favorite_id in new_ids if favorite_id in self._snapshot]
        added = [favorite_id for favorite_id in new_ids if favorite_id not in self._snapshot]
        removed = [favorite_id for favorite_id in old_ids if favorite_id not in snapshot]
        changed = [
            favorite_id for favorite_id in new_ids
            if favorite_id in self._snapshot and self._snapshot[favorite_id] != snapshot[favorite_id]
        ]
        built_changed = [
            favorite_id for favorite_id in changed
            if self._slot_by_id[favorite_id].content is not None
        ]

        if common_old != common_new \
                or len(built_changed) >= FULL_REBUILD_THRESHOLD \
                or len(added) + len(removed) >= FULL_REBUILD_THRESHOLD:
            self._apply_favorites(favorites, reset_scroll=False)
            return

        self._remove_slots(removed)
        self._favorites = favorites
        self._insert_slots(favorites)
        self._renumber_slots()

        favorites_by_id = {
            str(favorite.get('id', '')): favorite for favorite in favorites
        }
        for favorite_id in changed:
            self._rebuild_group(favorites_by_id[favorite_id])

        self._refresh_visibility(reset_scroll=False)
        self._snapshot = snapshot
        self._dirty = False

    def _remove_slots(self, removed: list[str]) -> None:
        """删除已消失的组，并清掉只在旧组上有意义的折叠状态"""
        for favorite_id in removed:
            slot = self._slot_by_id.pop(favorite_id)
            self._slots.remove(slot)
            self._groups_layout.removeWidget(slot)
            slot.recycle()
            slot.hide()
            slot.deleteLater()
            self._collapsed_ids.discard(favorite_id)
            self._row_open_ids.discard(favorite_id)

    def _insert_slots(self, favorites: list[dict]) -> None:
        """按新收藏顺序插入新增组，已有组保持原位"""
        for position, favorite in enumerate(favorites):
            favorite_id = str(favorite.get('id', ''))
            if favorite_id in self._snapshot:
                continue
            model = build_group_model(favorite, position, self._card_height, self._row_height)
            slot = GroupSlot(model, self._form_for(model), self._groups_host)
            self._groups_layout.insertWidget(position, slot)
            self._slots.insert(position, slot)
            self._slot_by_id[favorite_id] = slot

    def _renumber_slots(self) -> None:
        """重排标题序号；已建内容按当前语言重算标题"""
        for position, slot in enumerate(self._slots):
            if slot.model.card_index == position:
                continue
            slot.model.card_index = position
            slot.retranslate()

    @property
    def _group_widgets(self) -> list[QWidget]:
        """已建内容控件（网格或行），由 slot 派生，不单独维护"""
        return [slot.content for slot in self._slots if slot.content is not None]

    def _form_for(self, model: GroupModel) -> str:
        """按 tab、收起与已点开状态决定组的形态"""
        if model.favorite_id in self._collapsed_ids:
            return FORM_COLLAPSED if self._route == ROUTE_COMMON else FORM_ROW
        if self._route == ROUTE_ALL and model.favorite_id not in self._row_open_ids:
            return FORM_ROW
        return FORM_GRID

    def _on_group_toggled(self, favorite_id: str, expanded: bool) -> None:
        """记录用户显式收起 / 展开的组，并切换「全部」下的行视图"""
        if expanded:
            self._collapsed_ids.discard(favorite_id)
        else:
            self._collapsed_ids.add(favorite_id)
        slot = self._slot_by_id.get(favorite_id)
        if slot is not None:
            self._refresh_slot_form(slot)
        self._sync_viewport()

    def _on_row_clicked(self, favorite_id: str) -> None:
        """点开「全部」的行：展开网格，并记入 row_open_ids"""
        self._row_open_ids.add(favorite_id)
        self._collapsed_ids.discard(favorite_id)
        slot = self._slot_by_id.get(favorite_id)
        if slot is not None:
            self._refresh_slot_form(slot)
        self._sync_viewport()

    def _refresh_slot_form(self, slot: GroupSlot) -> None:
        """按当前状态原地切换单组形态；内容由视口同步决定是否重建"""
        form = self._form_for(slot.model)
        if form == slot.form:
            return
        slot.set_form(form)
        self._layout_dirty = True

    def _on_route_changed(self, route_key: str) -> None:
        """切换全部 / 常用，滚动位置归零"""
        self._route = route_key
        self._refresh_visibility(reset_scroll=True)

    def eventFilter(self, obj, event) -> bool:
        """点搜索框时显式激活窗口（NOACTIVATE 窗口点击不抢前台）"""
        if obj is self._search and event.type() == QEvent.Type.MouseButtonPress:
            self.activateWindow()
            self._search.setFocus()
        return super().eventFilter(obj, event)

    def _apply_search_query(self, text: str) -> None:
        """应用搜索词（回车 / 搜索按钮触发）；空 ↔ 非空时归零滚动位置"""
        query = text.strip().lower()
        if query == self._query:
            return
        reset_scroll = bool(self._query) != bool(query)
        self._query = query
        self._refresh_visibility(reset_scroll=reset_scroll)

    def _on_search_cleared(self) -> None:
        """清空搜索词并立即恢复全部（清空按钮 / 删光文本 / 空词回车）"""
        self._apply_search_query('')

    def _on_search_text_changed(self, text: str) -> None:
        """输入过程不触发过滤；仅文本被删空时立即恢复"""
        if not text.strip():
            self._on_search_cleared()

    def _on_scroll_changed(self, _value: int) -> None:
        """滚动时按新的视口窗口补建 / 回收"""
        self._sync_viewport()

    def _refresh_visibility(self, reset_scroll: bool = False) -> None:
        """按 tab 与搜索词过滤组，并在无可见组时显示对应空状态"""
        visible_count = 0
        for slot in self._slots:
            self._refresh_slot_form(slot)
            visible = (self._route == ROUTE_ALL or slot.model.pinned) \
                and slot.model.matches(self._query)
            slot.setVisible(visible)
            if visible:
                visible_count += 1

        self._update_empty_state(visible_count)
        if reset_scroll:
            self._scroll.verticalScrollBar().setValue(0)
        self._layout_dirty = True
        self._sync_viewport()

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

    def _slot_spans(self) -> list[tuple[int, int, GroupSlot]]:
        """按布局顺序累加未隐藏组的高度，返回 (top, bottom, slot)"""
        spans: list[tuple[int, int, GroupSlot]] = []
        offset = 0
        for slot in self._slots:
            if slot.isHidden():
                continue
            height = slot.height()
            spans.append((offset, offset + height, slot))
            offset += height + GROUP_SPACING
        return spans

    def _visible_window(self, spans: list[tuple[int, int, GroupSlot]]) -> list[GroupSlot]:
        """视口内组 + 前后各 1 个缓冲"""
        viewport_height = self._scroll.viewport().height()
        if viewport_height <= 0 or not spans:
            return []
        top = self._scroll.verticalScrollBar().value()
        bottom = top + viewport_height

        first = len(spans) - 1
        for index, (_, span_bottom, _) in enumerate(spans):
            if span_bottom > top:
                first = index
                break
        last = first
        for index, (span_top, _, _) in enumerate(spans):
            if span_top < bottom:
                last = index
        start = max(first - 1, 0)
        end = min(last + 1, len(spans) - 1)
        return [slot for _, _, slot in spans[start:end + 1]]

    def _sync_viewport(self) -> None:
        """按当前视口建必要内容，并回收超出上限的最久未用组"""
        self._tick += 1
        spans = self._slot_spans()
        window = self._visible_window(spans)
        if window:
            for slot in window:
                self._ensure_built(slot)
            self._recycle_overflow(set(window))
        if self._layout_dirty:
            self._flush_layout()
            self._layout_dirty = False

    def _flush_layout(self) -> None:
        """高度变化后同步激活各层布局，避免滚动区与新建内容在下一帧才完成排布"""
        self._groups_layout.activate()
        for slot in self._slots:
            if slot.content is None:
                continue
            slot_layout = slot.layout()
            if slot_layout is not None:
                slot_layout.activate()
            content_layout = slot.content.layout()
            if content_layout is not None:
                content_layout.activate()
        self._content_layout.activate()
        self._content.adjustSize()

    def _ensure_built(self, slot: GroupSlot) -> None:
        """建设一个组的真实控件（行或网格）"""
        slot.last_seen = self._tick
        if slot.content is not None:
            return
        content: PaletteGroup | GroupRow
        if slot.form == FORM_ROW:
            row = GroupRow(slot.model, slot)
            row.opened.connect(self._on_row_clicked)
            content = row
        else:
            group = PaletteGroup(slot.model, expanded=slot.form == FORM_GRID, parent=slot)
            group.swatch_clicked.connect(self._copy_hex)
            group.toggled.connect(self._on_group_toggled)
            content = group
        slot.attach(content)
        content.show()
        # 只激活本组两层布局，让新内容在当前事件内拿到正确尺寸；整表高度未变，无需全量刷新
        slot_layout = slot.layout()
        if slot_layout is not None:
            slot_layout.activate()
        content_layout = content.layout()
        if content_layout is not None:
            content_layout.activate()

    def _recycle_overflow(self, window: set[GroupSlot]) -> None:
        """回收窗口外最久未见的已建内容，直到不超过上限"""
        live_count = len(self._group_widgets)
        if live_count <= self._max_live_groups:
            return
        candidates = [
            slot for slot in self._slots
            if slot.content is not None and slot not in window
        ]
        candidates.sort(key=lambda slot: slot.last_seen)
        for slot in candidates:
            slot.recycle()
            live_count -= 1
            if live_count <= self._max_live_groups:
                break

    def _rebuild_group(self, favorite: dict) -> bool:
        """原位替换单组（模型 + 已建内容），不重置搜索、滚动与折叠状态

        批量刷新时只做重建与标脏，由调用方在全部变更处理完后执行一次
        `_sync_viewport()`，避免逐组重复的全表布局同步。

        Args:
            favorite: 最新收藏 dict，按 id 定位目标组

        Returns:
            bool: 是否找到对应组
        """
        favorite_id = str(favorite.get('id', ''))
        slot = self._slot_by_id.get(favorite_id)
        if slot is None:
            return False

        index = slot.model.card_index
        self._favorites[index] = favorite
        slot.set_model(
            build_group_model(favorite, index, self._card_height, self._row_height)
        )
        self._layout_dirty = True

        if slot.content is not None:
            slot.recycle()
            self._ensure_built(slot)
        return True

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
