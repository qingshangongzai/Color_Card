# 标准库导入
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QSizePolicy, QApplication, QLineEdit, QScrollArea, QFrame
)
from PySide6.QtGui import QColor
from qfluentwidgets import (
    CardWidget, ToolButton, FluentIcon,
    InfoBar, InfoBarPosition, isDarkTheme, qconfig
)

# 项目模块导入
from core import get_color_info, hex_to_rgb
from core.open_color_data import (
    OPEN_COLOR_DATA, get_color_series_names,
    get_light_shades, get_dark_shades, get_color_series_name_mapping
)
from .cards import ColorModeContainer, get_text_color, get_border_color, get_placeholder_color
from .theme_colors import get_card_background_color


class PresetColorCard(QWidget):
    """预设色彩面板中的单个色卡组件"""

    color_changed = Signal(dict)  # 信号：颜色信息字典

    def __init__(self, parent=None):
        self._hex_value = "#------"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
        super().__init__(parent)
        self.setup_ui()
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_styles)

    def _update_styles(self):
        """更新样式以适配主题"""
        self._update_hex_input_style()
        self._update_color_block_style()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(160)
        self.setMinimumWidth(120)
        self.setMaximumWidth(150)

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
        values_layout.setSpacing(5)

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

        # 16进制值输入框（可编辑）
        self.hex_input = QLineEdit()
        self.hex_input.setFixedHeight(28)
        self.hex_input.setEnabled(False)
        self.hex_input.setMaxLength(7)  # #RRGGBB 格式
        self.hex_input.setPlaceholderText("#RRGGBB")
        self.hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_hex_input_style()

        # 复制按钮
        self.copy_button = ToolButton(FluentIcon.COPY)
        self.copy_button.setFixedSize(28, 28)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_hex_to_clipboard)

        hex_layout.addWidget(self.hex_input, stretch=1)
        hex_layout.addWidget(self.copy_button)

        layout.addWidget(self.hex_container)

    def _update_placeholder_style(self):
        """更新占位符样式"""
        placeholder_color = get_placeholder_color()
        self.color_block.setStyleSheet(
            f"background-color: {placeholder_color.name()}; border-radius: 4px;"
        )

    def _update_color_block_style(self):
        """更新颜色块样式（主题切换时调用）"""
        if self._current_color_info:
            rgb = self._current_color_info.get('rgb', [0, 0, 0])
            color_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
            border_color = get_border_color()
            self.color_block.setStyleSheet(
                f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
            )
        else:
            self._update_placeholder_style()

    def _update_hex_input_style(self):
        """更新16进制输入框样式"""
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
        hex_value = color_info.get('hex', '--')
        if hex_value != '--' and not hex_value.startswith('#'):
            hex_value = '#' + hex_value
        self._hex_value = hex_value
        self.hex_input.setText(self._hex_value)
        self.hex_input.setEnabled(True)
        self.copy_button.setEnabled(True)

        # 更新色彩模式值
        self.mode_container_1.update_values(color_info)
        self.mode_container_2.update_values(color_info)

    def clear(self):
        """清空显示"""
        self._current_color_info = None
        self._hex_value = "#------"
        self._update_placeholder_style()
        self.hex_input.setText("#------")
        self.hex_input.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.mode_container_1.clear_values()
        self.mode_container_2.clear_values()


class PresetColorSchemeCard(CardWidget):
    """预设色彩方案卡片（展示一个颜色系列的色阶）"""

    def __init__(self, series_key: str, series_data: dict, parent=None):
        self._series_key = series_key
        self._series_data = series_data
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._shade_mode = 'light'  # 'light' 或 'dark'
        self._color_cards = []
        super().__init__(parent)
        self.setup_ui()
        self._load_color_data()
        self._update_styles()
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 头部信息
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # 颜色系列名称
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        # 色阶切换按钮
        self.shade_toggle_btn = ToolButton(FluentIcon.CONNECT)
        self.shade_toggle_btn.setFixedSize(28, 28)
        self.shade_toggle_btn.clicked.connect(self._on_toggle_shade_mode)
        header_layout.addWidget(self.shade_toggle_btn)

        layout.addLayout(header_layout)

        # 色卡面板（横向滚动区域）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_area.setFixedHeight(200)

        # 内容容器
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area)

    def _update_styles(self):
        """更新样式以适配主题"""
        name_color = get_text_color(secondary=False)
        card_bg = get_card_background_color()
        border_color = get_border_color()

        self.name_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {name_color.name()};")

        # 只在 Win10 上应用强制样式
        from utils.platform import is_windows_10
        if is_windows_10():
            self.setStyleSheet(f"""
                PresetColorSchemeCard,
                CardWidget {{
                    background-color: {card_bg.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 8px;
                }}
                ToolButton {{
                    background-color: transparent;
                    border: none;
                }}
                ToolButton:hover {{
                    background-color: rgba(128, 128, 128, 30);
                    border-radius: 4px;
                }}
                QToolTip {{
                    background-color: {card_bg.name()};
                    color: {name_color.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
            """)

    def _on_toggle_shade_mode(self):
        """切换浅色/深色组"""
        self._shade_mode = 'dark' if self._shade_mode == 'light' else 'light'
        self._load_color_data()

    def _clear_color_cards(self):
        """清空所有色卡"""
        for card in self._color_cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self._color_cards.clear()

    def _create_color_cards(self, colors: list):
        """创建色卡

        Args:
            colors: 颜色值列表 (HEX格式)
        """
        for hex_color in colors:
            card = PresetColorCard()
            card.set_color_modes(self._color_modes)
            card.hex_container.setVisible(self._hex_visible)

            # 转换 HEX 到颜色信息
            try:
                r, g, b = hex_to_rgb(hex_color)
                color_info = get_color_info(r, g, b)
                color_info['hex'] = hex_color
                card.update_color(color_info)
            except ValueError:
                card.clear()

            self._color_cards.append(card)
            self.cards_layout.addWidget(card)

        # 添加弹性空间
        self.cards_layout.addStretch()

    def _load_color_data(self):
        """加载颜色数据"""
        # 设置标题
        series_name = self._series_data.get('name', '未命名')
        shade_text = "浅色组" if self._shade_mode == 'light' else "深色组"
        self.name_label.setText(f"{series_name} - {shade_text}")

        # 清空现有色卡
        self._clear_color_cards()

        # 获取颜色数据
        if self._shade_mode == 'light':
            colors = get_light_shades(self._series_key)
        else:
            from core.open_color_data import get_dark_shades
            colors = get_dark_shades(self._series_key)

        # 创建色卡
        self._create_color_cards(colors)

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


class PresetColorList(QWidget):
    """预设色彩列表容器"""

    def __init__(self, parent=None):
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._scheme_cards = {}
        super().__init__(parent)
        self.setup_ui()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # 设置滚动条角落为透明
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

        # 加载所有颜色系列
        self._load_all_series()

    def _load_all_series(self):
        """加载所有颜色系列"""
        # 清空现有内容
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._scheme_cards.clear()

        # 获取所有颜色系列
        series_names = get_color_series_names()

        for series_key in series_names:
            series_data = OPEN_COLOR_DATA.get(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        # 添加弹性空间
        self.content_layout.addStretch()

    def set_hex_visible(self, visible):
        """设置是否显示16进制颜色值"""
        self._hex_visible = visible
        for card in self._scheme_cards.values():
            card.set_hex_visible(visible)

    def set_color_modes(self, modes):
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self._scheme_cards.values():
            card.set_color_modes(modes)

    def update_display_settings(self, hex_visible=None, color_modes=None):
        """更新显示设置"""
        if hex_visible is not None:
            self.set_hex_visible(hex_visible)
        if color_modes is not None:
            self.set_color_modes(color_modes)

    def _update_styles(self):
        """更新样式以适配主题"""
        pass  # 样式由子组件自己处理
