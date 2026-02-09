# 标准库导入
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QSizePolicy, QApplication, QFrame
)
from PySide6.QtGui import QColor
from qfluentwidgets import (
    CardWidget, ToolButton, FluentIcon, ComboBox, PrimaryPushButton, PushButton,
    InfoBar, InfoBarPosition, isDarkTheme, qconfig, ScrollArea
)

# 项目模块导入
from core import get_color_info, hex_to_rgb
from core.color_data import (
    get_color_series_names, get_color_series,
    get_light_shades, get_dark_shades, get_color_series_name_mapping,
    get_nice_palette_count, get_nice_palette, get_random_nice_palette,
    get_nice_palettes_batch,
    get_tailwind_color_series_names, get_tailwind_color_series,
    get_material_color_series_names, get_material_color_series,
    get_colorbrewer_series_names, get_colorbrewer_color_series,
    get_colorbrewer_series_type,
    get_radix_color_series_names, get_radix_color_series,
    get_nord_color_series_names, get_nord_color_series,
    get_nord_light_shades, get_nord_dark_shades,
    get_dracula_color_series_names, get_dracula_color_series,
    get_dracula_light_shades, get_dracula_dark_shades,
    get_rose_pine_color_series_names, get_rose_pine_color_series,
    get_solarized_color_series_names, get_solarized_color_series,
    get_catppuccin_color_series_names, get_catppuccin_color_series,
    get_gruvbox_color_series_names, get_gruvbox_color_series
)
from .cards import ColorModeContainer, get_text_color, get_border_color, get_placeholder_color
from .theme_colors import get_card_background_color
from utils.platform import is_windows_10


class PaletteLoaderThread(QThread):
    """配色方案数据异步加载线程"""

    data_ready = Signal(int, list)  # 信号：索引, 颜色列表
    loading_finished = Signal()

    def __init__(self, palettes_data, parent=None):
        """初始化加载线程

        Args:
            palettes_data: 配色方案数据列表 [(index, colors), ...]
            parent: 父对象
        """
        super().__init__(parent)
        self._palettes_data = palettes_data
        self._is_cancelled = False

    def cancel(self):
        """请求取消加载（线程安全）"""
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._is_cancelled

    def run(self):
        """在子线程中发送配色方案数据"""
        for palette_index, colors in self._palettes_data:
            if self._check_cancelled():
                return

            # 发射信号通知主线程创建卡片
            self.data_ready.emit(palette_index, colors)

        self.loading_finished.emit()


class PresetColorCard(QWidget):
    """预设色彩面板中的单个色卡组件"""

    color_changed = Signal(dict)  # 信号：颜色信息字典

    def __init__(self, parent=None):
        self._hex_value = "--"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
        super().__init__(parent)
        self.setup_ui()
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_styles)

    def _update_styles(self):
        """更新样式以适配主题"""
        self._update_hex_button_style()
        self._update_color_block_style()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(160)
        self.setMinimumWidth(100)

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
        self.hex_container.setMinimumHeight(28)
        self.hex_container.setMaximumHeight(35)
        hex_layout = QHBoxLayout(self.hex_container)
        hex_layout.setContentsMargins(0, 0, 0, 0)
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

    def _update_hex_button_style(self):
        """更新16进制按钮样式"""
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


class PresetColorSchemeCard(CardWidget):
    """预设色彩方案卡片（展示一个颜色系列的色阶）"""

    def __init__(self, series_key: str, series_data: dict, parent=None):
        self._series_key = series_key
        self._series_data = series_data
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._shade_mode = 'light'  # 'light' 或 'dark'，对于非顺序色表示前半/后半
        self._color_cards = []
        # 获取配色类型（仅ColorBrewer有，其他默认为sequential）
        self._series_type = self._get_series_type()
        super().__init__(parent)
        self.setup_ui()
        self._load_color_data()
        self._update_styles()
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_styles)

    def _get_series_type(self) -> str:
        """获取颜色系列的类型"""
        # ColorBrewer 系列根据数据中的 type 字段确定
        if self._series_key.startswith('brewer_'):
            return get_colorbrewer_series_type(self._series_key) or 'sequential'
        # Nord 和 Dracula 颜色数量较少，使用单组模式直接显示
        if self._series_key.startswith(('nord', 'dracula')):
            return 'single'
        # Catppuccin 和 Gruvbox 颜色数量较多，使用四段式显示（第一段/第二段/第三段/第四段）
        if self._series_key.startswith(('catppuccin', 'gruvbox')):
            return 'quad'
        # Rose Pine 和 Solarized 使用三段式显示（前半/中间/后半）
        if self._series_key.startswith(('rose_pine', 'solarized')):
            return 'triple'
        # 其他配色方案默认为顺序色（浅色组/深色组）
        return 'sequential'

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

        # 色阶切换按钮（单组模式不显示）
        self.shade_toggle_btn = ToolButton(FluentIcon.CONNECT)
        self.shade_toggle_btn.setFixedSize(28, 28)
        self.shade_toggle_btn.clicked.connect(self._on_toggle_shade_mode)
        # 单组模式隐藏切换按钮
        if self._series_type == 'single':
            self.shade_toggle_btn.setVisible(False)
        header_layout.addWidget(self.shade_toggle_btn)

        layout.addLayout(header_layout)

        # 色卡面板（水平布局容器）
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        layout.addWidget(self.cards_container, stretch=1)

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
        """切换显示模式"""
        if self._series_type == 'quad':
            # 四段式：light -> medium -> dark -> ultra_dark -> light
            if self._shade_mode == 'light':
                self._shade_mode = 'medium'
            elif self._shade_mode == 'medium':
                self._shade_mode = 'dark'
            elif self._shade_mode == 'dark':
                self._shade_mode = 'ultra_dark'
            else:
                self._shade_mode = 'light'
        elif self._series_type == 'triple':
            # 三段式：light -> medium -> dark -> light
            if self._shade_mode == 'light':
                self._shade_mode = 'medium'
            elif self._shade_mode == 'medium':
                self._shade_mode = 'dark'
            else:
                self._shade_mode = 'light'
        else:
            # 两段式：light -> dark -> light
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
            self.cards_layout.addWidget(card, stretch=1)

    def _load_color_data(self):
        """加载颜色数据"""
        # 清空现有色卡
        self._clear_color_cards()

        # 获取颜色数据
        colors_dict = self._series_data.get('colors', {})
        total_colors = len(colors_dict)

        # 根据配色类型决定显示逻辑
        if self._series_type == 'single':
            # 单组模式：直接显示所有颜色（用于 Nord、Dracula 等）
            series_name = self._series_data.get('name', '未命名')
            self.name_label.setText(series_name)
            # 显示所有颜色
            colors = [colors_dict.get(i, '') for i in range(total_colors)]
        elif self._series_type == 'sequential':
            # 顺序色：浅色组/深色组
            series_name = self._series_data.get('name', '未命名')
            shade_text = "浅色组" if self._shade_mode == 'light' else "深色组"
            self.name_label.setText(f"{series_name} - {shade_text}")

            # 根据总颜色数决定每段显示数量，尽量平均分配
            half_count = total_colors // 2

            if self._shade_mode == 'light':
                # 浅色组: 索引 0 到 half_count-1
                colors = [colors_dict.get(i, '') for i in range(min(half_count, total_colors))]
            else:
                # 深色组: 索引 half_count 到末尾
                colors = [colors_dict.get(i, '') for i in range(half_count, total_colors)]

        elif self._series_type == 'diverging':
            # 发散色：左半部分/右半部分（以中间为界）
            series_name = self._series_data.get('name', '未命名')
            half_index = total_colors // 2

            if self._shade_mode == 'light':
                # 左半部分
                shade_text = "左半"
                colors = [colors_dict.get(i, '') for i in range(half_index)]
            else:
                # 右半部分
                shade_text = "右半"
                colors = [colors_dict.get(i, '') for i in range(half_index, total_colors)]

            self.name_label.setText(f"{series_name} - {shade_text}")

        elif self._series_type == 'quad':
            # 四段式：第一段/第二段/第三段/第四段（每段6个颜色）
            series_name = self._series_data.get('name', '未命名')

            if self._shade_mode == 'light':
                # 第一段：索引 0-5
                shade_text = "第一段"
                colors = [colors_dict.get(i, '') for i in range(0, 6)]
            elif self._shade_mode == 'medium':
                # 第二段：索引 6-11
                shade_text = "第二段"
                colors = [colors_dict.get(i, '') for i in range(6, 12)]
            elif self._shade_mode == 'dark':
                # 第三段：索引 12-17
                shade_text = "第三段"
                colors = [colors_dict.get(i, '') for i in range(12, 18)]
            else:  # ultra_dark
                # 第四段：索引 18-23
                shade_text = "第四段"
                colors = [colors_dict.get(i, '') for i in range(18, 24)]

            self.name_label.setText(f"{series_name} - {shade_text}")

        elif self._series_type == 'triple':
            # 三段式：前半/中间/后半（每行最多显示5个颜色）
            series_name = self._series_data.get('name', '未命名')

            # 计算三段的分割点，尽量平均分配
            segment_size = total_colors // 3
            first_end = segment_size
            second_end = segment_size * 2

            if self._shade_mode == 'light':
                # 前半部分
                shade_text = "前半"
                colors = [colors_dict.get(i, '') for i in range(first_end)]
            elif self._shade_mode == 'medium':
                # 中间部分
                shade_text = "中间"
                colors = [colors_dict.get(i, '') for i in range(first_end, second_end)]
            else:  # dark
                # 后半部分
                shade_text = "后半"
                colors = [colors_dict.get(i, '') for i in range(second_end, total_colors)]

            self.name_label.setText(f"{series_name} - {shade_text}")

        else:  # qualitative
            # 定性色：前半部分/后半部分（按索引平分）
            series_name = self._series_data.get('name', '未命名')
            half_index = total_colors // 2

            if self._shade_mode == 'light':
                # 前半部分
                shade_text = "前半"
                colors = [colors_dict.get(i, '') for i in range(half_index)]
            else:
                # 后半部分
                shade_text = "后半"
                colors = [colors_dict.get(i, '') for i in range(half_index, total_colors)]

            self.name_label.setText(f"{series_name} - {shade_text}")

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


class NicePaletteCard(CardWidget):
    """Nice Color Palettes 配色方案卡片"""

    def __init__(self, palette_index: int, colors: list, parent=None):
        self._palette_index = palette_index
        self._colors = colors
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._color_cards = []
        super().__init__(parent)
        self.setup_ui()
        self._load_color_data()
        self._update_styles()
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

        # 配色方案编号
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 色卡面板（水平布局容器）
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        layout.addWidget(self.cards_container, stretch=1)

    def _update_styles(self):
        """更新样式以适配主题"""
        name_color = get_text_color(secondary=False)
        card_bg = get_card_background_color()
        border_color = get_border_color()

        self.name_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {name_color.name()};")

        if is_windows_10():
            self.setStyleSheet(f"""
                NicePaletteCard,
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
            if not hex_color:
                continue
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
            self.cards_layout.addWidget(card, stretch=1)

    def _load_color_data(self):
        """加载颜色数据"""
        self.name_label.setText(f"配色方案 #{self._palette_index + 1}")
        self._clear_color_cards()
        self._create_color_cards(self._colors)

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
        self._current_source = 'open_color'
        self._current_palette_index = 0
        self._loader = None  # 异步加载线程
        super().__init__(parent)
        self.setup_ui()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def __del__(self):
        """析构时确保线程已停止"""
        self._cleanup_loader()

    def _cleanup_loader(self):
        """清理加载线程"""
        if self._loader is not None:
            self._loader.cancel()
            self._loader.wait(1000)  # 等待最多1秒
            self._loader = None

    def setup_ui(self):
        """设置界面"""
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

        self._load_all_series()

    def _clear_content(self):
        """清空所有内容"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._scheme_cards.clear()

    def _load_all_series(self):
        """加载所有颜色系列 (Open Color)"""
        self._clear_content()
        self._current_source = 'open_color'

        series_names = get_color_series_names()

        for series_key in series_names:
            series_data = get_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def load_nice_palettes_batch(self, start_index=0, count=50):
        """加载指定范围的 Nice Color Palettes 配色方案（异步加载）

        Args:
            start_index: 起始索引
            count: 加载数量
        """
        # 清理旧线程
        self._cleanup_loader()

        self._clear_content()
        self._current_source = 'nice_palette'
        self._current_start_index = start_index

        # 获取配色方案数据
        palettes = get_nice_palettes_batch(start_index, count)

        # 创建并启动异步加载线程
        self._loader = PaletteLoaderThread(palettes, parent=self)
        self._loader.data_ready.connect(self._on_palette_data_ready)
        self._loader.loading_finished.connect(self._on_loading_finished)
        self._loader.start()

    def _on_palette_data_ready(self, palette_index, colors):
        """处理接收到的配色方案数据，在主线程创建卡片

        Args:
            palette_index: 配色方案索引
            colors: 颜色列表
        """
        # 在主线程中创建卡片
        card = NicePaletteCard(palette_index, colors)
        card.set_hex_visible(self._hex_visible)
        card.set_color_modes(self._color_modes)
        self.content_layout.addWidget(card)
        self._scheme_cards[f'nice_{palette_index}'] = card

    def _on_loading_finished(self):
        """加载完成回调"""
        # 清理线程引用
        self._loader = None

    def set_data_source(self, source: str, data=None):
        """设置数据源

        Args:
            source: 'open_color'、'nice_palette'、'tailwind'、'material'、'colorbrewer' 或 'radix'
            data: Open Color/Tailwind/Material/ColorBrewer/Radix时为系列名称列表，Nice Palettes时为起始索引
        """
        if source == 'open_color':
            if data is None:
                self._load_all_series()
            else:
                self._load_open_color_groups(data)
        elif source == 'nice_palette':
            start_index = data if data is not None else 0
            self.load_nice_palettes_batch(start_index, 50)
        elif source == 'tailwind':
            if data is None:
                # 默认加载所有 Tailwind 颜色系列
                all_series = get_tailwind_color_series_names()
                self._load_tailwind_series(all_series)
            else:
                self._load_tailwind_series(data)
        elif source == 'material':
            if data is None:
                # 默认加载所有 Material Design 颜色系列
                all_series = get_material_color_series_names()
                self._load_material_series(all_series)
            else:
                self._load_material_series(data)
        elif source == 'colorbrewer':
            if data is None:
                # 默认加载所有 ColorBrewer 颜色系列
                all_series = get_colorbrewer_series_names()
                self._load_colorbrewer_series(all_series)
            else:
                self._load_colorbrewer_series(data)
        elif source == 'radix':
            if data is None:
                # 默认加载所有 Radix Colors 颜色系列
                all_series = get_radix_color_series_names()
                self._load_radix_series(all_series)
            else:
                self._load_radix_series(data)
        elif source == 'nord':
            if data is None:
                # 默认加载所有 Nord 颜色系列
                all_series = get_nord_color_series_names()
                self._load_nord_series(all_series)
            else:
                self._load_nord_series(data)
        elif source == 'dracula':
            if data is None:
                # 默认加载所有 Dracula 颜色系列
                all_series = get_dracula_color_series_names()
                self._load_dracula_series(all_series)
            else:
                self._load_dracula_series(data)
        elif source == 'rose_pine':
            if data is None:
                # 默认加载所有 Rose Pine 颜色系列
                all_series = get_rose_pine_color_series_names()
                self._load_rose_pine_series(all_series)
            else:
                self._load_rose_pine_series(data)
        elif source == 'solarized':
            if data is None:
                # 默认加载所有 Solarized 颜色系列
                all_series = get_solarized_color_series_names()
                self._load_solarized_series(all_series)
            else:
                self._load_solarized_series(data)
        elif source == 'catppuccin':
            if data is None:
                # 默认加载所有 Catppuccin 颜色系列
                all_series = get_catppuccin_color_series_names()
                self._load_catppuccin_series(all_series)
            else:
                self._load_catppuccin_series(data)
        elif source == 'gruvbox':
            if data is None:
                # 默认加载所有 Gruvbox 颜色系列
                all_series = get_gruvbox_color_series_names()
                self._load_gruvbox_series(all_series)
            else:
                self._load_gruvbox_series(data)

    def _load_open_color_groups(self, series_keys: list):
        """加载指定分组的 Open Color 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'open_color'

        for series_key in series_keys:
            series_data = get_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_tailwind_series(self, series_keys: list):
        """加载指定分组的 Tailwind Colors 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'tailwind'

        for series_key in series_keys:
            series_data = get_tailwind_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_material_series(self, series_keys: list):
        """加载指定分组的 Material Design Colors 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'material'

        for series_key in series_keys:
            series_data = get_material_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_colorbrewer_series(self, series_keys: list):
        """加载指定分组的 ColorBrewer 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'colorbrewer'

        for series_key in series_keys:
            series_data = get_colorbrewer_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_radix_series(self, series_keys: list):
        """加载指定分组的 Radix Colors 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'radix'

        for series_key in series_keys:
            series_data = get_radix_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_nord_series(self, series_keys: list):
        """加载指定分组的 Nord 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'nord'

        for series_key in series_keys:
            series_data = get_nord_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_dracula_series(self, series_keys: list):
        """加载指定分组的 Dracula 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'dracula'

        for series_key in series_keys:
            series_data = get_dracula_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_rose_pine_series(self, series_keys: list):
        """加载指定分组的 Rose Pine 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'rose_pine'

        for series_key in series_keys:
            series_data = get_rose_pine_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_solarized_series(self, series_keys: list):
        """加载指定分组的 Solarized 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'solarized'

        for series_key in series_keys:
            series_data = get_solarized_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_catppuccin_series(self, series_keys: list):
        """加载指定分组的 Catppuccin 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'catppuccin'

        for series_key in series_keys:
            series_data = get_catppuccin_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

        self.content_layout.addStretch()

    def _load_gruvbox_series(self, series_keys: list):
        """加载指定分组的 Gruvbox 颜色系列

        Args:
            series_keys: 颜色系列名称列表
        """
        self._clear_content()
        self._current_source = 'gruvbox'

        for series_key in series_keys:
            series_data = get_gruvbox_color_series(series_key)
            if series_data:
                card = PresetColorSchemeCard(series_key, series_data)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                self.content_layout.addWidget(card)
                self._scheme_cards[series_key] = card

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
        pass
