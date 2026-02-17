# 标准库导入
import math
import uuid
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QSizePolicy, QApplication
)
from qfluentwidgets import (
    CardWidget, ToolButton, FluentIcon, PushButton,
    InfoBar, InfoBarPosition, qconfig, ScrollArea
)

# 项目模块导入
from core import get_color_info, hex_to_rgb
from core.async_loader import BaseBatchLoader
from core.color_data import (
    get_color_source, get_random_palettes, ColorSource
)
from .cards import ColorModeContainer, get_text_color, get_border_color, get_placeholder_color
from .theme_colors import get_card_background_color
from utils.platform import is_windows_10


class GroupLoaderThread(BaseBatchLoader):
    """分组数据异步加载线程
    
    用于大数据量配色组的分批加载，避免阻塞UI主线程。
    """
    
    data_ready = Signal(int, list)
    
    def __init__(self, source: ColorSource, group_index: int, batch_size: int = 10, parent=None):
        """初始化加载线程
        
        Args:
            source: 配色源对象
            group_index: 分组索引
            batch_size: 每批加载数量（默认10）
            parent: 父对象
        """
        super().__init__(batch_size, parent)
        self._source = source
        self._group_index = group_index
        
        group_info = source.get_group_info(group_index)
        self._total_items = group_info.get("total_items", 0)
    
    def get_total_batches(self) -> int:
        """获取总批次数"""
        return math.ceil(self._total_items / self._batch_size)
    
    def load_batch(self, batch_idx: int) -> list:
        """加载指定批次的数据
        
        Args:
            batch_idx: 批次索引（从0开始）
            
        Returns:
            list: 批次数据列表
        """
        start = batch_idx * self._batch_size
        data = self._source.get_palettes_for_group_batch(
            self._group_index, start, self._batch_size
        )
        self.data_ready.emit(batch_idx, data)
        return data


class PresetColorCard(QWidget):
    """预设色彩面板中的单个色卡组件"""

    color_changed = Signal(dict)

    def __init__(self, parent=None):
        self._hex_value = "--"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
        super().__init__(parent)
        self.setup_ui()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def _update_styles(self):
        self._update_hex_button_style()
        self._update_color_block_style()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(160)
        self.setMinimumWidth(100)

        self.color_block = QWidget()
        self.color_block.setMinimumHeight(40)
        self.color_block.setMaximumHeight(80)
        self._update_placeholder_style()
        layout.addWidget(self.color_block)

        values_container = QWidget()
        values_container.setMinimumHeight(60)
        values_layout = QHBoxLayout(values_container)
        values_layout.setContentsMargins(0, 0, 0, 0)
        values_layout.setSpacing(5)

        self.mode_container_1 = ColorModeContainer(self._color_modes[0])
        values_layout.addWidget(self.mode_container_1)

        self.mode_container_2 = ColorModeContainer(self._color_modes[1])
        values_layout.addWidget(self.mode_container_2)

        layout.addWidget(values_container)

        self.hex_container = QWidget()
        self.hex_container.setMinimumHeight(28)
        self.hex_container.setMaximumHeight(35)
        hex_layout = QHBoxLayout(self.hex_container)
        hex_layout.setContentsMargins(0, 0, 0, 0)
        hex_layout.setSpacing(5)

        self.hex_button = PushButton("--")
        self.hex_button.setFixedHeight(28)
        self.hex_button.setEnabled(False)
        self._update_hex_button_style()

        self.copy_button = ToolButton(FluentIcon.COPY)
        self.copy_button.setFixedSize(28, 28)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_hex_to_clipboard)

        hex_layout.addWidget(self.hex_button, stretch=1)
        hex_layout.addWidget(self.copy_button)

        layout.addWidget(self.hex_container)

    def _update_placeholder_style(self):
        placeholder_color = get_placeholder_color()
        self.color_block.setStyleSheet(
            f"background-color: {placeholder_color.name()}; border-radius: 4px;"
        )

    def _update_color_block_style(self):
        if self._current_color_info:
            rgb = self._current_color_info.get('rgb', [0, 0, 0])
            color_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
            border_color = get_border_color()
            self.color_block.setStyleSheet(
                f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
            )
        else:
            self._update_placeholder_style()

    def _update_hex_button_style(self):
        primary_color = get_text_color(secondary=False)
        border_color = get_border_color()
        self.hex_button.setStyleSheet(
            f"""
            PushButton {{
                font-size: 12px;
                font-weight: bold;
                color: {primary_color.name()};
                background-color: transparent;
                border: 1px solid {border_color.name()};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            PushButton:disabled {{
                color: {get_text_color(secondary=True).name()};
                background-color: transparent;
            }}
            """
        )

    def _copy_hex_to_clipboard(self):
        if self._hex_value and self._hex_value != "--":
            clipboard = QApplication.clipboard()
            clipboard.setText(self._hex_value)
            InfoBar.success(
                title="已复制",
                content=f"颜色值 {self._hex_value} 已复制到剪贴板",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )

    def set_color_modes(self, modes):
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        self.mode_container_1.set_mode(modes[0])
        self.mode_container_2.set_mode(modes[1])

        if self._current_color_info:
            self.update_color(self._current_color_info)

    def update_color(self, color_info):
        self._current_color_info = color_info

        rgb = color_info.get('rgb', [0, 0, 0])
        color_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
        border_color = get_border_color()
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
        )

        hex_value = color_info.get('hex', '--')
        if hex_value != '--' and not hex_value.startswith('#'):
            hex_value = '#' + hex_value
        self._hex_value = hex_value
        self.hex_button.setText(self._hex_value)
        self.hex_button.setEnabled(True)
        self.copy_button.setEnabled(True)

        self.mode_container_1.update_values(color_info)
        self.mode_container_2.update_values(color_info)

    def clear(self):
        self._current_color_info = None
        self._hex_value = "--"
        self._update_placeholder_style()
        self.hex_button.setText("--")
        self.hex_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.mode_container_1.clear_values()
        self.mode_container_2.clear_values()


class PaletteCard(CardWidget):
    """配色卡片（统一展示配色方案）"""

    favorite_requested = Signal(dict)
    preview_in_panel_requested = Signal(dict)

    def __init__(self, palette_index: int, palette_data: dict, parent=None):
        self._palette_index = palette_index
        self._palette_data = palette_data
        self._colors = palette_data.get("colors", [])
        self._name = palette_data.get("name", f"配色 #{palette_index + 1}")
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._color_cards = []
        super().__init__(parent)
        self.setup_ui()
        self._load_color_data()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        self.preview_btn = ToolButton(FluentIcon.VIEW)
        self.preview_btn.setFixedSize(28, 28)
        self.preview_btn.clicked.connect(self._on_preview_in_panel_clicked)
        header_layout.addWidget(self.preview_btn)

        self.favorite_btn = ToolButton(FluentIcon.HEART)
        self.favorite_btn.setFixedSize(28, 28)
        self.favorite_btn.clicked.connect(self._on_favorite_clicked)
        header_layout.addWidget(self.favorite_btn)

        layout.addLayout(header_layout)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        layout.addWidget(self.cards_container, stretch=1)

    def _update_styles(self):
        name_color = get_text_color(secondary=False)
        card_bg = get_card_background_color()
        border_color = get_border_color()

        self.name_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {name_color.name()};")

        if is_windows_10():
            self.setStyleSheet(f"""
                PaletteCard,
                CardWidget {{
                    background-color: {card_bg.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 8px;
                }}
                QToolTip {{
                    background-color: {card_bg.name()};
                    color: {name_color.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
            """)

    def _clear_color_cards(self):
        for card in self._color_cards:
            card.deleteLater()
        self._color_cards.clear()

        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    @staticmethod
    def _calculate_columns(color_count: int) -> int:
        if color_count <= 0:
            return 1

        if color_count % 5 == 0:
            return 5

        if color_count % 6 == 0:
            return 6

        if color_count <= 5:
            return color_count
        elif color_count <= 10:
            return 5
        else:
            return 6

    def _create_color_cards(self, colors: list):
        valid_colors = [c for c in colors if c]
        color_count = len(valid_colors)
        columns = self._calculate_columns(color_count)

        current_row_layout = None
        for i, hex_color in enumerate(valid_colors):
            if i % columns == 0:
                current_row_layout = QHBoxLayout()
                current_row_layout.setContentsMargins(0, 0, 0, 0)
                current_row_layout.setSpacing(10)
                self.cards_layout.addLayout(current_row_layout)

            card = PresetColorCard()
            card.set_color_modes(self._color_modes)
            card.hex_container.setVisible(self._hex_visible)

            try:
                r, g, b = hex_to_rgb(hex_color)
                color_info = get_color_info(r, g, b)
                color_info['hex'] = hex_color
                card.update_color(color_info)
            except ValueError:
                card.clear()

            self._color_cards.append(card)
            current_row_layout.addWidget(card, stretch=1)

    def _on_preview_in_panel_clicked(self):
        colors = []
        for card in self._color_cards:
            if card._current_color_info:
                colors.append(card._current_color_info)

        if not colors:
            return

        preview_data = {
            "name": self.name_label.text(),
            "colors": colors,
            "source": "preset_color"
        }

        self.preview_in_panel_requested.emit(preview_data)

    def _on_favorite_clicked(self):
        colors = []
        for card in self._color_cards:
            if card._current_color_info:
                colors.append(card._current_color_info)

        if not colors:
            return

        favorite_data = {
            "id": str(uuid.uuid4()),
            "name": self.name_label.text(),
            "colors": colors,
            "created_at": datetime.now().isoformat(),
            "source": "preset_color"
        }

        self.favorite_requested.emit(favorite_data)

        InfoBar.success(
            title="已收藏",
            content=f"配色 '{favorite_data['name']}' 已添加到配色管理",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

    def _load_color_data(self):
        self.name_label.setText(self._name)
        self._clear_color_cards()
        self._create_color_cards(self._colors)

    def set_hex_visible(self, visible):
        self._hex_visible = visible
        for card in self._color_cards:
            card.hex_container.setVisible(visible)

    def set_color_modes(self, modes):
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self._color_cards:
            card.set_color_modes(modes)

    def update_display(self, hex_visible=None, color_modes=None):
        if hex_visible is not None:
            self.set_hex_visible(hex_visible)
        if color_modes is not None:
            self.set_color_modes(color_modes)


class PresetColorList(QWidget):
    """预设色彩列表容器"""

    favorite_requested = Signal(dict)
    preview_in_panel_requested = Signal(dict)

    BATCH_THRESHOLD = 20
    BATCH_SIZE = 10

    def __init__(self, parent=None):
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._scheme_cards = {}
        self._current_source = None
        self._current_color_source = None
        self._loader = None
        self._palette_counter = 0
        super().__init__(parent)
        self.setup_ui()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("ScrollArea { border: none; background: transparent; }")

        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        self.scroll_area.setCornerWidget(corner_widget)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(15)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

    def _clear_content(self):
        self._cancel_loader()
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._scheme_cards.clear()
        self._palette_counter = 0

    def _cancel_loader(self):
        if self._loader is not None:
            self._loader.cancel()
            self._loader = None

    def set_data_source(self, source: str, data=None):
        if source == 'random':
            count = data if isinstance(data, int) else 10
            self.load_random_palettes(count)
        else:
            group_index = data if isinstance(data, int) else 0
            self.load_color_source(source, group_index)

    def load_color_source(self, source_id: str, group_index: int = 0):
        color_source = get_color_source(source_id)
        if not color_source:
            return

        self._cancel_loader()
        self._clear_content()
        self._current_source = source_id
        self._current_color_source = color_source

        group_info = color_source.get_group_info(group_index)
        total_items = group_info.get("total_items", 0)

        if total_items > self.BATCH_THRESHOLD:
            self._start_batch_loading(color_source, group_index)
        else:
            if color_source.has_groups:
                palettes = color_source.get_palettes_for_group(group_index)
            else:
                palettes = color_source.get_all_palettes()
            self._load_palettes(palettes)

    def _start_batch_loading(self, source: ColorSource, group_index: int):
        self._loader = GroupLoaderThread(
            source, group_index, self.BATCH_SIZE, parent=self
        )
        self._loader.data_ready.connect(self._on_batch_data_ready)
        self._loader.loading_finished.connect(self._on_loading_finished)
        self._loader.start()

    def _on_batch_data_ready(self, batch_idx: int, data: list):
        for palette in data:
            colors = palette.get("colors", [])
            name = palette.get("name", f"配色 #{self._palette_counter + 1}")
            if colors:
                card = PaletteCard(self._palette_counter, {"name": name, "colors": colors})
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                card.favorite_requested.connect(self.favorite_requested)
                card.preview_in_panel_requested.connect(self.preview_in_panel_requested)
                self.content_layout.addWidget(card)
                self._scheme_cards[f'palette_{self._palette_counter}'] = card
            self._palette_counter += 1

    def _on_loading_finished(self):
        self.content_layout.addStretch()
        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None

    def _load_palettes(self, palettes: list):
        for i, palette in enumerate(palettes):
            colors = palette.get("colors", [])
            name = palette.get("name", f"配色 #{i+1}")
            if colors:
                card = PaletteCard(i, {"name": name, "colors": colors})
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                card.favorite_requested.connect(self.favorite_requested)
                card.preview_in_panel_requested.connect(self.preview_in_panel_requested)
                self.content_layout.addWidget(card)
                self._scheme_cards[f'palette_{i}'] = card

        self.content_layout.addStretch()

    def load_random_palettes(self, count=10):
        self._cancel_loader()
        self._clear_content()
        self._current_source = 'random'
        self._current_color_source = None

        random_palettes = get_random_palettes(count)

        for i, palette_data in enumerate(random_palettes):
            colors = palette_data.get('colors', [])
            name = palette_data.get('name', f"配色 #{i+1}")

            if colors:
                card = PaletteCard(i, {"name": name, "colors": colors})
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                card.favorite_requested.connect(self.favorite_requested)
                card.preview_in_panel_requested.connect(self.preview_in_panel_requested)
                self.content_layout.addWidget(card)
                self._scheme_cards[f'random_{i}'] = card

        self.content_layout.addStretch()

    def set_hex_visible(self, visible):
        self._hex_visible = visible
        for card in self._scheme_cards.values():
            card.set_hex_visible(visible)

    def set_color_modes(self, modes):
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self._scheme_cards.values():
            card.set_color_modes(modes)

    def update_display_settings(self, hex_visible=None, color_modes=None):
        if hex_visible is not None:
            self.set_hex_visible(hex_visible)
        if color_modes is not None:
            self.set_color_modes(color_modes)

    def _update_styles(self):
        pass
