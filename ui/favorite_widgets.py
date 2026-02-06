# 标准库导入
import uuid
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QScrollArea, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QSizePolicy, QApplication
)
from PySide6.QtGui import QColor
from qfluentwidgets import (
    CardWidget, PushButton, ToolButton, FluentIcon,
    InfoBar, InfoBarPosition, isDarkTheme
)

# 项目模块导入
from core import get_color_info
from .cards import COLOR_MODE_CONFIG, ColorModeContainer, get_text_color, get_border_color, get_placeholder_color


class FavoriteColorCard(QWidget):
    """收藏中的单个色卡组件（与其他面板样式一致）"""

    def __init__(self, parent=None):
        self._hex_value = "--"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(160)

        # 颜色块
        self.color_block = QWidget()
        self.color_block.setMinimumHeight(40)
        self.color_block.setMaximumHeight(80)
        self._update_placeholder_style()
        layout.addWidget(self.color_block)

        # 数值区域（两列布局）
        values_container = QWidget()
        values_container.setMinimumHeight(60)
        values_layout = QHBoxLayout(values_container)
        values_layout.setContentsMargins(0, 0, 0, 0)
        values_layout.setSpacing(10)

        # 第一列色彩模式
        self.mode_container_1 = ColorModeContainer(self._color_modes[0])
        values_layout.addWidget(self.mode_container_1)

        # 第二列色彩模式
        self.mode_container_2 = ColorModeContainer(self._color_modes[1])
        values_layout.addWidget(self.mode_container_2)

        layout.addWidget(values_container)

        # 16进制颜色值显示区域
        self.hex_container = QWidget()
        self.hex_container.setMinimumHeight(30)
        self.hex_container.setMaximumHeight(40)
        hex_layout = QHBoxLayout(self.hex_container)
        hex_layout.setContentsMargins(0, 5, 0, 0)
        hex_layout.setSpacing(5)

        # 16进制值显示按钮
        self.hex_button = PushButton("--")
        self.hex_button.setFixedHeight(28)
        self.hex_button.setEnabled(False)
        self._update_hex_button_style()

        # 复制按钮
        self.copy_button = ToolButton(FluentIcon.COPY)
        self.copy_button.setFixedSize(28, 28)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_hex_to_clipboard)

        hex_layout.addWidget(self.hex_button, stretch=1)
        hex_layout.addWidget(self.copy_button)

        layout.addWidget(self.hex_container)
        layout.addStretch()

    def _update_placeholder_style(self):
        """更新占位符样式"""
        placeholder_color = get_placeholder_color()
        self.color_block.setStyleSheet(
            f"background-color: {placeholder_color.name()}; border-radius: 4px;"
        )

    def _update_hex_button_style(self):
        """更新16进制按钮样式"""
        primary_color = get_text_color(secondary=False)
        self.hex_button.setStyleSheet(
            f"""
            PushButton {{
                font-size: 12px;
                font-weight: bold;
                color: {primary_color.name()};
                background-color: transparent;
                border: 1px solid {get_border_color().name()};
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
        """复制16进制颜色值到剪贴板"""
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
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        self.mode_container_1.set_mode(modes[0])
        self.mode_container_2.set_mode(modes[1])

        if self._current_color_info:
            self.update_color(self._current_color_info)

    def update_color(self, color_info):
        """更新颜色显示"""
        self._current_color_info = color_info

        # 更新颜色块
        rgb = color_info.get('rgb', [0, 0, 0])
        color_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
        border_color = get_border_color()
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
        )

        # 更新16进制值
        self._hex_value = color_info.get('hex', '--')
        self.hex_button.setText(self._hex_value)
        self.hex_button.setEnabled(True)
        self.copy_button.setEnabled(True)

        # 更新色彩模式值
        self.mode_container_1.update_values(color_info)
        self.mode_container_2.update_values(color_info)

    def clear(self):
        """清空显示"""
        self._current_color_info = None
        self._hex_value = "--"
        self._update_placeholder_style()
        self.hex_button.setText("--")
        self.hex_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.mode_container_1.clear_values()
        self.mode_container_2.clear_values()


class FavoriteSchemeCard(CardWidget):
    """收藏配色方案卡片（水平排列色卡样式，动态数量）"""

    delete_requested = Signal(str)

    def __init__(self, favorite_data: dict, parent=None):
        self._favorite_data = favorite_data
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._color_cards = []
        super().__init__(parent)
        self.setup_ui()
        self._load_favorite_data()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 头部信息
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.name_label = QLabel()
        self.name_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {get_text_color().name()};")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"font-size: 11px; color: {get_text_color(secondary=True).name()};")
        header_layout.addWidget(self.time_label)

        layout.addLayout(header_layout)

        # 色卡面板（水平排列）
        self.cards_panel = QWidget()
        cards_layout = QHBoxLayout(self.cards_panel)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(15)

        layout.addWidget(self.cards_panel)

        # 删除按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.delete_button = ToolButton(FluentIcon.DELETE)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

    def _clear_color_cards(self):
        """清空所有色卡"""
        layout = self.cards_panel.layout()
        for card in self._color_cards:
            layout.removeWidget(card)
            card.deleteLater()
        self._color_cards.clear()

    def _create_color_cards(self, count):
        """创建指定数量的色卡

        Args:
            count: 色卡数量
        """
        layout = self.cards_panel.layout()
        for i in range(count):
            card = FavoriteColorCard()
            card.set_color_modes(self._color_modes)
            card.hex_container.setVisible(self._hex_visible)
            self._color_cards.append(card)
            layout.addWidget(card)

    def _load_favorite_data(self):
        """加载收藏数据"""
        self.name_label.setText(self._favorite_data.get('name', '未命名'))

        created_at = self._favorite_data.get('created_at', '')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                self.time_label.setText(dt.strftime('%Y-%m-%d %H:%M'))
            except:
                self.time_label.setText(created_at)
        else:
            self.time_label.setText('')

        colors = self._favorite_data.get('colors', [])

        # 清空现有色卡并根据颜色数量重新创建
        self._clear_color_cards()
        self._create_color_cards(len(colors))

        # 加载颜色数据
        for i, card in enumerate(self._color_cards):
            if i < len(colors):
                card.update_color(colors[i])

    def _on_delete_clicked(self):
        """删除按钮点击"""
        favorite_id = self._favorite_data.get('id', '')
        if favorite_id:
            self.delete_requested.emit(favorite_id)

    def set_hex_visible(self, visible):
        """设置16进制显示区域的可见性"""
        self._hex_visible = visible
        for card in self._color_cards:
            card.hex_container.setVisible(visible)

    def set_color_modes(self, modes):
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self._color_cards:
            card.set_color_modes(modes)

    def update_display(self, hex_visible=None, color_modes=None):
        """更新显示设置"""
        if hex_visible is not None:
            self.set_hex_visible(hex_visible)
        if color_modes is not None:
            self.set_color_modes(color_modes)


class FavoriteSchemeList(QWidget):
    """收藏配色方案列表容器"""

    favorite_deleted = Signal(str)

    def __init__(self, parent=None):
        self._favorites = []
        self._favorite_cards = {}
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # 设置滚动条角落为透明（防止出现灰色方块）
        from PySide6.QtWidgets import QWidget
        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        self.scroll_area.setCornerWidget(corner_widget)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(10)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        self._show_empty_state()

    def _show_empty_state(self):
        """显示空状态"""
        self._clear_cards()

        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(15)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon_label.setStyleSheet("font-size: 48px; color: #999;")
        icon_label.setText("⭐")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon_label)

        text_label = QLabel("还没有收藏的配色方案")
        text_label.setStyleSheet(f"font-size: 14px; color: {get_text_color(secondary=True).name()};")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(text_label)

        hint_label = QLabel("在色彩提取或配色方案面板点击收藏按钮")
        hint_label.setStyleSheet(f"font-size: 12px; color: {get_text_color(secondary=True).name()};")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(hint_label)

        self.content_layout.addWidget(empty_widget, alignment=Qt.AlignmentFlag.AlignCenter)

    def _clear_cards(self):
        """清空所有卡片"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._favorite_cards = {}

    def set_favorites(self, favorites):
        """设置收藏列表"""
        self._favorites = favorites
        self._clear_cards()

        if not favorites:
            self._show_empty_state()
            return

        for favorite in favorites:
            card = FavoriteSchemeCard(favorite)
            card.set_hex_visible(self._hex_visible)
            card.set_color_modes(self._color_modes)
            card.delete_requested.connect(self.favorite_deleted)
            self.content_layout.addWidget(card)
            self._favorite_cards[favorite.get('id', '')] = card

        self.content_layout.addStretch()

    def set_hex_visible(self, visible):
        """设置是否显示16进制颜色值"""
        self._hex_visible = visible
        for card in self._favorite_cards.values():
            card.set_hex_visible(visible)

    def set_color_modes(self, modes):
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self._favorite_cards.values():
            card.set_color_modes(modes)

    def update_display_settings(self, hex_visible=None, color_modes=None):
        """更新显示设置"""
        if hex_visible is not None:
            self.set_hex_visible(hex_visible)
        if color_modes is not None:
            self.set_color_modes(color_modes)
