# 标准库导入
import math
from datetime import datetime
from typing import List, Dict, Any

# 第三方库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QSizePolicy, QApplication, QLineEdit, QFileDialog
)
from qfluentwidgets import (
    CardWidget, ScrollArea, ToolButton, FluentIcon, ComboBox,
    InfoBar, InfoBarPosition, isDarkTheme, qconfig,
    PushButton, SubtitleLabel, MessageBox
)

# 项目模块导入
from core import get_color_info, hex_to_rgb, get_config_manager, ServiceFactory
from utils import tr, get_locale_manager, calculate_grid_columns
from core.async_loader import BaseBatchLoader
from core.grouping import generate_groups
from .cards import ColorModeContainer, get_text_color, get_border_color, get_placeholder_color
from utils.theme_colors import get_card_background_color, get_title_color, get_interface_background_color
from utils.platform import is_windows_10
from dialogs import ColorblindPreviewDialog, ContrastCheckDialog, EditPaletteDialog


# =============================================================================
# 异步加载线程
# =============================================================================

class FavoriteGroupLoaderThread(BaseBatchLoader):
    """配色管理分组数据异步加载线程
    
    用于大数据量配色组的分批加载，避免阻塞UI主线程。
    """
    
    data_ready = Signal(int, list)
    
    def __init__(self, favorites: List[Dict[str, Any]], group_indices: List[int], batch_size: int = 10, parent=None):
        """初始化加载线程
        
        Args:
            favorites: 完整的收藏列表
            group_indices: 当前分组的索引列表
            batch_size: 每批加载数量（默认10）
            parent: 父对象
        """
        super().__init__(batch_size, parent)
        self._favorites = favorites
        self._group_indices = group_indices
        self._total_items = len(group_indices)
    
    def get_total_batches(self) -> int:
        """获取总批次数
        
        Returns:
            int: 总批次数
        """
        return math.ceil(self._total_items / self._batch_size)
    
    def load_batch(self, batch_idx: int) -> list:
        """加载指定批次的数据
        
        Args:
            batch_idx: 批次索引（从0开始）
            
        Returns:
            list: 批次数据列表
        """
        start = batch_idx * self._batch_size
        end = min(start + self._batch_size, self._total_items)
        
        batch_data = []
        for i in range(start, end):
            if self._check_cancelled():
                return batch_data
            fav_idx = self._group_indices[i]
            if 0 <= fav_idx < len(self._favorites):
                batch_data.append(self._favorites[fav_idx])
        
        self.data_ready.emit(batch_idx, batch_data)
        
        return batch_data


# =============================================================================
# 配色管理色卡组件
# =============================================================================

class PaletteManagementColorCard(QWidget):
    """配色管理中的单个色卡组件（与其他面板样式一致）"""

    color_changed = Signal(dict)  # 信号：颜色信息字典

    def __init__(self, parent=None):
        self._hex_value = "#------"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
        self._color_history = []  # 颜色修改历史
        self._history_index = -1  # 当前历史索引
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

        # 16进制值输入框（可编辑）
        self.hex_input = QLineEdit()
        self.hex_input.setFixedHeight(28)
        self.hex_input.setEnabled(False)
        self.hex_input.setMaxLength(7)  # #RRGGBB 格式
        self.hex_input.setPlaceholderText("#RRGGBB")
        self.hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 文本居中
        self.hex_input.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)  # 禁用右键菜单
        self._update_hex_input_style()
        self.hex_input.textChanged.connect(self._on_hex_text_changed)
        self.hex_input.editingFinished.connect(self._on_hex_editing_finished)
        # 安装事件过滤器以捕获键盘事件（支持Ctrl+Z撤回）
        self.hex_input.installEventFilter(self)

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
            # 有颜色时更新边框
            rgb = self._current_color_info.get('rgb', [0, 0, 0])
            color_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
            border_color = get_border_color()
            self.color_block.setStyleSheet(
                f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
            )
        else:
            # 无颜色时更新占位符样式
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
            QLineEdit:focus {{
                border: 2px solid #0078d4;
            }}
            """
        )

    def _on_hex_text_changed(self, text: str):
        """16进制文本变化处理（自动格式化为大写并确保#前缀）"""
        if not text:
            return

        # 自动转大写
        upper_text = text.upper()

        # 只允许有效的十六进制字符和#
        valid_chars = '#0123456789ABCDEF'
        filtered_text = ''.join(c for c in upper_text if c in valid_chars)

        # 确保以#开头
        if not filtered_text.startswith('#'):
            filtered_text = '#' + filtered_text

        # 限制长度（# + 6位十六进制）
        if len(filtered_text) > 7:
            filtered_text = filtered_text[:7]

        # 更新文本（如果发生变化）
        if text != filtered_text:
            cursor_pos = self.hex_input.cursorPosition()
            self.hex_input.setText(filtered_text)
            # 保持光标位置
            new_pos = min(len(filtered_text), cursor_pos + (1 if not text.startswith('#') else 0))
            self.hex_input.setCursorPosition(new_pos)

    def _on_hex_editing_finished(self):
        """16进制编辑完成处理（验证并更新颜色）"""
        text = self.hex_input.text().strip().upper()

        if not text:
            return

        # 添加 # 前缀
        if not text.startswith('#'):
            text = '#' + text

        # 如果颜色没有变化，不进行处理
        if text == self._hex_value:
            return

        # 验证并转换
        try:
            r, g, b = hex_to_rgb(text)

            # 创建新的颜色信息
            new_color_info = get_color_info(r, g, b)
            new_color_info['hex'] = text

            # 更新当前颜色信息
            self._current_color_info = new_color_info
            self._hex_value = text

            # 更新颜色块
            color_str = f"rgb({r}, {g}, {b})"
            border_color = get_border_color()
            self.color_block.setStyleSheet(
                f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
            )

            # 更新色彩模式值
            self.mode_container_1.update_values(new_color_info)
            self.mode_container_2.update_values(new_color_info)

            # 发射颜色变化信号
            self.color_changed.emit(new_color_info)

            # 保存新颜色到历史记录（在更新后保存）
            self._add_to_history(new_color_info)

        except ValueError:
            self.hex_input.setText(self._hex_value)
            InfoBar.warning(
                title=tr('messages.invalid_input.title'),
                content=tr('messages.invalid_input.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )

    def _add_to_history(self, color_info):
        """添加颜色到历史记录

        Args:
            color_info: 颜色信息字典
        """
        # 删除当前位置之后的历史记录
        self._color_history = self._color_history[:self._history_index + 1]
        # 添加新记录
        self._color_history.append(color_info.copy())
        self._history_index += 1
        # 限制历史记录长度（最多10条）
        if len(self._color_history) > 10:
            self._color_history.pop(0)
            self._history_index -= 1

    def eventFilter(self, obj, event):
        """事件过滤器（捕获输入框的Ctrl+Z快捷键）

        Args:
            obj: 事件源对象
            event: 事件对象

        Returns:
            bool: 是否已处理事件
        """
        if obj == self.hex_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._undo_color_change()
                return True
        return super().eventFilter(obj, event)

    def _undo_color_change(self):
        """撤回上一步颜色修改"""
        # 需要至少2条历史记录才能撤回（当前颜色 + 上一个颜色）
        if self._history_index >= 1:
            # 索引减1，获取上一个颜色
            self._history_index -= 1
            prev_color_info = self._color_history[self._history_index]
            # 应用历史颜色（不添加到历史）
            self._apply_color_info(prev_color_info)

    def _apply_color_info(self, color_info):
        """应用颜色信息（不触发历史记录）

        Args:
            color_info: 颜色信息字典
        """
        self._current_color_info = color_info
        self._hex_value = color_info.get('hex', '#------')

        # 更新颜色块
        rgb = color_info.get('rgb', [0, 0, 0])
        color_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
        border_color = get_border_color()
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
        )

        # 更新输入框
        self.hex_input.setText(self._hex_value)

        # 更新色彩模式值
        self.mode_container_1.update_values(color_info)
        self.mode_container_2.update_values(color_info)

        # 发射颜色变化信号
        self.color_changed.emit(color_info)

    def _copy_hex_to_clipboard(self):
        """复制16进制颜色值到剪贴板"""
        if self._hex_value and self._hex_value != "--":
            clipboard = QApplication.clipboard()
            clipboard.setText(self._hex_value)
            InfoBar.success(
                title=tr('messages.copy_success.title'),
                content=tr('messages.copy_success.content', default=f"颜色值 {self._hex_value} 已复制到剪贴板").format(value=self._hex_value),
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

        # 更新16进制值（确保带#前缀）
        hex_value = color_info.get('hex', '--')
        if hex_value != '--' and not hex_value.startswith('#'):
            hex_value = '#' + hex_value
        self._hex_value = hex_value
        self.hex_input.setText(self._hex_value)
        self.hex_input.setEnabled(True)
        self.copy_button.setEnabled(True)

        # 初始化历史记录（如果是空的历史记录）
        if not self._color_history:
            self._color_history = [color_info.copy()]
            self._history_index = 0

        # 更新色彩模式值
        self.mode_container_1.update_values(color_info)
        self.mode_container_2.update_values(color_info)

    def clear(self):
        """清空显示"""
        self._current_color_info = None
        self._hex_value = "#------"
        self._color_history = []  # 清空历史记录
        self._history_index = -1
        self._update_placeholder_style()
        self.hex_input.setText("#------")
        self.hex_input.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.mode_container_1.clear_values()
        self.mode_container_2.clear_values()


# =============================================================================
# 配色管理卡片
# =============================================================================

class PaletteManagementCard(CardWidget):
    """配色管理卡片（网格排列色卡样式，动态数量）"""

    delete_requested = Signal(str)
    preview_requested = Signal(dict)
    contrast_requested = Signal(dict)
    color_changed = Signal(str, int, dict)
    preview_in_panel_requested = Signal(dict)
    edit_requested = Signal(dict)
    MAX_COLORS_PER_ROW = 6

    def __init__(self, favorite_data: Dict[str, Any], parent=None):
        self._favorite_data = favorite_data
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._color_cards = []
        super().__init__(parent)
        self.setup_ui()
        self._load_favorite_data()
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

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        self.time_label = QLabel()
        self.time_label.setStyleSheet("font-size: 11px;")
        header_layout.addWidget(self.time_label)

        layout.addLayout(header_layout)

        # 色卡面板（垂直布局容器，每行使用水平布局）
        self.cards_panel = QWidget()
        cards_layout = QVBoxLayout(self.cards_panel)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(15)

        layout.addWidget(self.cards_panel)

        # 操作按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 在配色预览面板中预览按钮
        self.preview_panel_button = ToolButton(FluentIcon.VIEW)
        self.preview_panel_button.setFixedSize(28, 28)
        self.preview_panel_button.clicked.connect(self._on_preview_in_panel_clicked)
        button_layout.addWidget(self.preview_panel_button)

        # 对比度检查按钮
        self.contrast_button = ToolButton(FluentIcon.BRIGHTNESS)
        self.contrast_button.setFixedSize(28, 28)
        self.contrast_button.clicked.connect(self._on_contrast_clicked)
        button_layout.addWidget(self.contrast_button)

        # 预览按钮（色盲模拟）
        self.preview_button = ToolButton(FluentIcon.ZOOM_IN)
        self.preview_button.setFixedSize(28, 28)
        self.preview_button.clicked.connect(self._on_preview_clicked)
        button_layout.addWidget(self.preview_button)

        # 管理按钮（编辑配色）
        self.edit_button = ToolButton(FluentIcon.EDIT)
        self.edit_button.setFixedSize(28, 28)
        self.edit_button.clicked.connect(self._on_edit_clicked)
        button_layout.addWidget(self.edit_button)

        # 删除按钮
        self.delete_button = ToolButton(FluentIcon.DELETE)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

    def _update_styles(self):
        """更新样式以适配主题"""
        name_color = get_text_color(secondary=False)
        time_color = get_text_color(secondary=True)
        card_bg = get_card_background_color()
        border_color = get_border_color()

        self.name_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {name_color.name()};")
        self.time_label.setStyleSheet(f"font-size: 11px; color: {time_color.name()};")
        
        # 只在 Win10 上应用强制样式（Win11 上 qfluentwidgets 能正常工作）
        if is_windows_10():
            self.setStyleSheet(f"""
                PaletteManagementCard,
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
            """)

    def _clear_color_cards(self):
        """清空所有色卡"""
        # 清空色卡列表
        for card in self._color_cards:
            card.deleteLater()
        self._color_cards.clear()

        # 清空所有行布局
        layout = self.cards_panel.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.layout():
                # 删除行布局中的所有色卡
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    @staticmethod
    def _calculate_columns(color_count: int) -> int:
        """计算每行显示的列数

        Args:
            color_count: 颜色数量

        Returns:
            int: 每行列数
        """
        return calculate_grid_columns(color_count)

    def _create_color_cards(self, count):
        """创建指定数量的色卡

        Args:
            count: 色卡数量
        """
        layout = self.cards_panel.layout()
        # 计算每行显示的列数
        columns = self._calculate_columns(count)

        # 按行创建色卡
        current_row_layout = None
        for i in range(count):
            # 每行开始时创建新的水平布局
            if i % columns == 0:
                current_row_layout = QHBoxLayout()
                current_row_layout.setContentsMargins(0, 0, 0, 0)
                current_row_layout.setSpacing(15)
                layout.addLayout(current_row_layout)

            card = PaletteManagementColorCard()
            card.set_color_modes(self._color_modes)
            card.hex_container.setVisible(self._hex_visible)
            card.color_changed.connect(lambda color_info, idx=i: self._on_color_changed(idx, color_info))
            self._color_cards.append(card)

            # 添加到当前行的水平布局，设置stretch=1使色卡均匀分布
            current_row_layout.addWidget(card, stretch=1)

    def _on_color_changed(self, color_index: int, color_info: dict):
        """颜色变化处理

        Args:
            color_index: 颜色索引
            color_info: 新的颜色信息
        """
        favorite_id = self._favorite_data.get('id', '')
        if favorite_id:
            self.color_changed.emit(favorite_id, color_index, color_info)

    def _load_favorite_data(self):
        """加载收藏数据"""
        self.name_label.setText(self._favorite_data.get('name', tr('palette_management.unnamed')))

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
        # 如果没有id，使用name作为备选标识
        if not favorite_id:
            favorite_id = self._favorite_data.get('name', '')
        if favorite_id:
            self.delete_requested.emit(favorite_id)

    def _on_preview_clicked(self):
        """预览按钮点击（色盲模拟）"""
        self.preview_requested.emit(self._favorite_data)

    def _on_preview_in_panel_clicked(self):
        """在配色预览面板中预览按钮点击"""
        self.preview_in_panel_requested.emit(self._favorite_data)

    def _on_contrast_clicked(self):
        """对比度检查按钮点击"""
        self.contrast_requested.emit(self._favorite_data)

    def _on_edit_clicked(self):
        """管理按钮点击（编辑配色）"""
        self.edit_requested.emit(self._favorite_data)

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


# =============================================================================
# 配色管理列表容器
# =============================================================================

class PaletteManagementList(QWidget):
    """配色管理列表容器"""

    favorite_deleted = Signal(str)
    favorite_preview = Signal(dict)
    favorite_contrast = Signal(dict)
    favorite_color_changed = Signal(str, int, dict)
    favorite_preview_in_panel = Signal(dict)
    favorite_edit = Signal(dict)
    group_changed = Signal(int)
    groups_updated = Signal(list)

    BATCH_THRESHOLD = 50
    BATCH_SIZE = 10

    def __init__(self, parent=None):
        self._favorites = []
        self._favorite_cards = {}
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self._groups = []
        self._current_group_index = 0
        self._loader = None
        super().__init__(parent)
        self.setup_ui()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.scroll_area = ScrollArea()
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

        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(15)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_label = QLabel()
        self._icon_label.setStyleSheet(f"font-size: 48px; color: {get_text_color(secondary=True).name()};")
        self._icon_label.setText("⭐")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._icon_label)

        self._text_label = QLabel(tr('palette_management.empty_title'))
        self._text_label.setStyleSheet(f"font-size: 14px; color: {get_text_color(secondary=True).name()};")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._text_label)

        self._hint_label = QLabel(tr('palette_management.empty_hint'))
        self._hint_label.setStyleSheet(f"font-size: 12px; color: {get_text_color(secondary=True).name()};")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._hint_label)

        self.content_layout.addWidget(self._empty_widget, alignment=Qt.AlignmentFlag.AlignCenter)

    def _clear_cards(self):
        """清空所有卡片"""
        self._cancel_loader()
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._favorite_cards = {}

    def _cancel_loader(self):
        """取消加载线程"""
        if self._loader is not None:
            self._loader.cancel()
            self._loader = None

    def set_favorites(self, favorites):
        """设置收藏列表"""
        self._favorites = favorites
        self._groups = generate_groups(len(favorites))
        self._current_group_index = 0
        self.groups_updated.emit(self._groups)
        
        if not favorites:
            self._show_empty_state()
            return
        
        self._load_current_group()

    def _load_current_group(self):
        """加载当前分组的数据"""
        self._cancel_loader()
        self._clear_cards()
        
        if not self._groups or self._current_group_index >= len(self._groups):
            return
        
        current_group = self._groups[self._current_group_index]
        group_indices = current_group.get("indices", [])
        
        if len(group_indices) > self.BATCH_THRESHOLD:
            self._start_batch_loading(group_indices)
        else:
            self._load_group_directly(group_indices)

    def _load_group_directly(self, group_indices: list):
        """直接加载分组数据（小数据量）
        
        Args:
            group_indices: 分组索引列表
        """
        for idx in group_indices:
            if 0 <= idx < len(self._favorites):
                favorite = self._favorites[idx]
                card = PaletteManagementCard(favorite)
                card.set_hex_visible(self._hex_visible)
                card.set_color_modes(self._color_modes)
                card.delete_requested.connect(self.favorite_deleted)
                card.preview_requested.connect(self._on_preview_requested)
                card.contrast_requested.connect(self._on_contrast_requested)
                card.color_changed.connect(self._on_color_changed)
                card.preview_in_panel_requested.connect(self._on_preview_in_panel_requested)
                card.edit_requested.connect(self._on_edit_requested)
                self.content_layout.addWidget(card)
                self._favorite_cards[favorite.get('id', '')] = card
        
        self.content_layout.addStretch()

    def _start_batch_loading(self, group_indices: List[int]):
        """启动分批加载
        
        Args:
            group_indices: 分组索引列表
        """
        self._loader = FavoriteGroupLoaderThread(
            self._favorites, group_indices, self.BATCH_SIZE, parent=self
        )
        self._loader.data_ready.connect(self._on_batch_data_ready)
        self._loader.loading_finished.connect(self._on_loading_finished)
        self._loader.start()

    def _on_batch_data_ready(self, batch_idx: int, batch_data: List[Dict[str, Any]]):
        """批次数据就绪回调
        
        Args:
            batch_idx: 批次索引
            batch_data: 批次数据列表
        """
        for favorite in batch_data:
            card = PaletteManagementCard(favorite)
            card.set_hex_visible(self._hex_visible)
            card.set_color_modes(self._color_modes)
            card.delete_requested.connect(self.favorite_deleted)
            card.preview_requested.connect(self._on_preview_requested)
            card.contrast_requested.connect(self._on_contrast_requested)
            card.color_changed.connect(self._on_color_changed)
            card.preview_in_panel_requested.connect(self._on_preview_in_panel_requested)
            card.edit_requested.connect(self._on_edit_requested)
            self.content_layout.addWidget(card)
            self._favorite_cards[favorite.get('id', '')] = card
        
        QApplication.processEvents()

    def _on_loading_finished(self):
        """加载完成回调"""
        self.content_layout.addStretch()
        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None

    def set_current_group(self, group_index: int):
        """设置当前分组
        
        Args:
            group_index: 分组索引
        """
        if group_index < 0 or group_index >= len(self._groups):
            return
        
        if group_index != self._current_group_index:
            self._current_group_index = group_index
            self.group_changed.emit(group_index)
            self._load_current_group()

    def get_groups(self) -> list:
        """获取分组列表
        
        Returns:
            list: 分组配置列表
        """
        return self._groups

    def get_current_group_index(self) -> int:
        """获取当前分组索引
        
        Returns:
            int: 当前分组索引
        """
        return self._current_group_index

    def _on_preview_requested(self, favorite_data):
        """预览请求处理（色盲模拟）

        Args:
            favorite_data: 收藏项数据
        """
        self.favorite_preview.emit(favorite_data)

    def _on_preview_in_panel_requested(self, favorite_data):
        """在配色预览面板中预览请求处理

        Args:
            favorite_data: 收藏项数据
        """
        self.favorite_preview_in_panel.emit(favorite_data)

    def _on_contrast_requested(self, favorite_data):
        """对比度检查请求处理

        Args:
            favorite_data: 收藏项数据
        """
        self.favorite_contrast.emit(favorite_data)

    def _on_color_changed(self, favorite_id: str, color_index: int, color_info: dict):
        """颜色变化请求处理

        Args:
            favorite_id: 收藏项ID
            color_index: 颜色索引
            color_info: 新的颜色信息
        """
        self.favorite_color_changed.emit(favorite_id, color_index, color_info)

    def _on_edit_requested(self, favorite_data):
        """编辑请求处理

        Args:
            favorite_data: 收藏项数据
        """
        self.favorite_edit.emit(favorite_data)

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

    def _update_styles(self):
        """更新样式以适配主题"""
        if hasattr(self, '_icon_label') and self._icon_label is not None:
            try:
                self._icon_label.setStyleSheet(f"font-size: 48px; color: {get_text_color(secondary=True).name()};")
            except RuntimeError:
                pass
        if hasattr(self, '_text_label') and self._text_label is not None:
            try:
                self._text_label.setStyleSheet(f"font-size: 14px; color: {get_text_color(secondary=True).name()};")
            except RuntimeError:
                pass
        if hasattr(self, '_hint_label') and self._hint_label is not None:
            try:
                self._hint_label.setStyleSheet(f"font-size: 12px; color: {get_text_color(secondary=True).name()};")
            except RuntimeError:
                pass
    
    def update_texts(self):
        """更新界面文本"""
        if hasattr(self, '_text_label') and self._text_label is not None:
            try:
                self._text_label.setText(tr('palette_management.empty_title'))
            except RuntimeError:
                pass
        if hasattr(self, '_hint_label') and self._hint_label is not None:
            try:
                self._hint_label.setText(tr('palette_management.empty_hint'))
            except RuntimeError:
                pass


# =============================================================================
# 配色管理界面
# =============================================================================

class PaletteManagementInterface(QWidget):
    """配色管理界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('paletteManagementInterface')
        self._config_manager = get_config_manager()
        self._palette_service = None
        self.setup_ui()
        self._load_favorites()
        self._load_settings()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)
        
        locale_manager = get_locale_manager()
        if locale_manager:
            locale_manager.language_changed.connect(self._on_language_changed)

    def _get_palette_service(self):
        """延迟获取配色服务
        
        Returns:
            PaletteService: 配色服务实例
        """
        if self._palette_service is None:
            self._palette_service = ServiceFactory.get_palette_service(self)
            self._setup_service_connections()
        return self._palette_service

    def _setup_service_connections(self):
        """设置配色服务信号连接"""
        self._palette_service.import_finished.connect(self._on_import_finished)
        self._palette_service.import_error.connect(self._on_import_error)
        self._palette_service.export_finished.connect(self._on_export_finished)
        self._palette_service.export_error.connect(self._on_export_error)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = SubtitleLabel(tr('palette_management.title'))
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.add_button = PushButton(FluentIcon.ADD, tr('palette_management.add'), self)
        self.add_button.clicked.connect(self._on_add_clicked)
        header_layout.addWidget(self.add_button)

        self.import_button = PushButton(FluentIcon.DOWN, tr('palette_management.import'), self)
        self.import_button.clicked.connect(self._on_import_clicked)
        header_layout.addWidget(self.import_button)

        self.export_button = PushButton(FluentIcon.UP, tr('palette_management.export'), self)
        self.export_button.clicked.connect(self._on_export_clicked)
        header_layout.addWidget(self.export_button)

        self.clear_all_button = PushButton(FluentIcon.DELETE, tr('palette_management.clear_all'), self)
        self.clear_all_button.setMinimumWidth(100)
        self.clear_all_button.clicked.connect(self._on_clear_all_clicked)
        header_layout.addWidget(self.clear_all_button)

        self.group_combo = ComboBox(self)
        self.group_combo.setFixedWidth(150)
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        header_layout.addWidget(self.group_combo)

        layout.addLayout(header_layout)

        self.palette_management_list = PaletteManagementList(self)
        self.palette_management_list.favorite_deleted.connect(self._on_favorite_deleted)
        self.palette_management_list.favorite_preview.connect(self._on_favorite_preview)
        self.palette_management_list.favorite_contrast.connect(self._on_favorite_contrast)
        self.palette_management_list.favorite_color_changed.connect(self._on_favorite_color_changed)
        self.palette_management_list.favorite_preview_in_panel.connect(self._on_favorite_preview_in_panel)
        self.palette_management_list.favorite_edit.connect(self._on_favorite_edit)
        self.palette_management_list.groups_updated.connect(self._on_groups_updated)
        layout.addWidget(self.palette_management_list, stretch=1)

    def _on_groups_updated(self, groups: list):
        """分组列表更新回调
        
        Args:
            groups: 分组配置列表
        """
        self.group_combo.clear()
        for i, group in enumerate(groups):
            self.group_combo.addItem(group["name"])
            self.group_combo.setItemData(i, i)

    def _on_group_changed(self, index: int):
        """分组切换回调
        
        Args:
            index: 分组索引
        """
        if index >= 0:
            self.palette_management_list.set_current_group(index)

    def _load_favorites(self):
        """加载收藏列表"""
        favorites = self._config_manager.get_favorites()
        self.palette_management_list.set_favorites(favorites)

    def _on_clear_all_clicked(self):
        """清空所有按钮点击"""
        msg_box = MessageBox(
            tr('dialogs.confirm.clear_title'),
            tr('dialogs.confirm.clear_content'),
            self
        )
        msg_box.yesButton.setText(tr('dialogs.confirm.confirm_btn'))
        msg_box.cancelButton.setText(tr('dialogs.confirm.cancel_btn'))
        if msg_box.exec():
            self._config_manager.clear_favorites()
            self._config_manager.save()
            self._load_favorites()

    def _on_favorite_deleted(self, favorite_id):
        """收藏删除回调"""
        favorite = self._config_manager.get_favorite(favorite_id)
        palette_name = favorite.get('name', tr('palette_management.unnamed')) if favorite else tr('palette_management.unnamed')

        msg_box = MessageBox(
            tr('dialogs.confirm.delete_title'),
            tr('dialogs.confirm.delete_content', default=f"确定要删除「{palette_name}」吗？此操作不可撤销。").format(name=palette_name),
            self
        )
        msg_box.yesButton.setText(tr('dialogs.confirm.delete_btn'))
        msg_box.cancelButton.setText(tr('dialogs.confirm.cancel_btn'))

        if msg_box.exec():
            self._config_manager.delete_favorite(favorite_id)
            self._config_manager.save()
            self._load_favorites()

    def _on_import_clicked(self):
        """导入按钮点击"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr('palette_management.import_title'),
            "",
            tr('palette_management.json_filter')
        )

        if not file_path:
            return

        self._pending_import_path = file_path

        msg_box = MessageBox(
            tr('dialogs.confirm.import_mode_title'),
            tr('dialogs.confirm.import_mode_content'),
            self
        )
        msg_box.yesButton.setText(tr('dialogs.confirm.append'))
        msg_box.cancelButton.setText(tr('dialogs.confirm.replace'))

        # 获取结果：1=追加, 0=替换
        result = msg_box.exec()

        # 确定导入模式
        if result == 1:  # 点击了"追加"
            self._pending_import_mode = 'append'
        else:  # 点击了"替换"
            self._pending_import_mode = 'replace'

        # 调用服务开始导入
        self._get_palette_service().import_from_file(file_path)

    def _on_import_finished(self, palettes: list):
        """导入完成回调

        Args:
            palettes: 导入的配色列表
        """
        if self._pending_import_mode == 'replace':
            self._config_manager.clear_favorites()

        for palette in palettes:
            self._config_manager.add_favorite(palette)

        self._config_manager.save()
        self._load_favorites()

        InfoBar.success(
            title=tr('messages.import_success.title'),
            content=tr('messages.import_success.content', default=f"成功导入 {len(palettes)} 个配色").format(count=len(palettes)),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def _on_import_error(self, error_msg: str):
        """导入错误回调

        Args:
            error_msg: 错误信息
        """
        InfoBar.error(
            title=tr('messages.import_failed.title'),
            content=tr('messages.import_failed.content', default=error_msg).format(error=error_msg),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def _on_export_clicked(self):
        """导出按钮点击"""
        default_name = f"color_card_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr('palette_management.export_title'),
            default_name,
            tr('palette_management.json_filter')
        )

        if not file_path:
            return

        # 确保文件扩展名为 .json
        if not file_path.endswith('.json'):
            file_path += '.json'

        # 获取收藏列表并调用服务导出
        favorites = self._config_manager.get_favorites()
        self._get_palette_service().export_to_file(favorites, file_path)

    def _on_export_finished(self, file_path: str):
        """导出完成回调

        Args:
            file_path: 导出文件路径
        """
        InfoBar.success(
            title=tr('messages.export_success.title'),
            content=tr('messages.export_success.content', default=f"收藏已导出到：{file_path}").format(path=file_path),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def _on_export_error(self, error_msg: str):
        """导出错误回调

        Args:
            error_msg: 错误信息
        """
        InfoBar.error(
            title=tr('messages.export_failed.title'),
            content=tr('messages.export_failed.content', default=error_msg).format(error=error_msg),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def _on_favorite_preview(self, favorite_data):
        """收藏预览回调（色盲模拟）

        Args:
            favorite_data: 收藏项数据
        """
        scheme_name = favorite_data.get('name', tr('palette_management.unnamed'))
        colors = favorite_data.get('colors', [])

        if not colors:
            InfoBar.warning(
                title=tr('messages.preview_failed.title'),
                content=tr('messages.preview_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 显示色盲模拟预览对话框
        dialog = ColorblindPreviewDialog(
            scheme_name=scheme_name,
            colors=colors,
            parent=self.window()
        )
        dialog.exec()

    def _on_favorite_preview_in_panel(self, favorite_data):
        """在配色预览面板中预览回调

        Args:
            favorite_data: 收藏项数据
        """
        colors = favorite_data.get('colors', [])

        if not colors:
            InfoBar.warning(
                title=tr('messages.preview_failed.title'),
                content=tr('messages.preview_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        color_values = []
        for color_info in colors:
            hex_value = color_info.get('hex', '')
            if hex_value:
                if not hex_value.startswith('#'):
                    hex_value = '#' + hex_value
                color_values.append(hex_value)

        if not color_values:
            InfoBar.warning(
                title=tr('messages.preview_invalid.title'),
                content=tr('messages.preview_invalid.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 调用主窗口跳转到配色预览页面
        window = self.window()
        if window and hasattr(window, 'show_color_preview'):
            window.show_color_preview(color_values)

    def _on_add_clicked(self):
        """添加配色按钮点击"""
        favorites = self._config_manager.get_favorites()
        default_name = f"{tr('messages.palette')} {len(favorites) + 1}"

        dialog = EditPaletteDialog(default_name=default_name, parent=self.window())

        if dialog.exec() != EditPaletteDialog.DialogCode.Accepted:
            return

        palette_data = dialog.get_palette_data()
        if not palette_data:
            return

        self._config_manager.add_favorite(palette_data)
        self._config_manager.save()

        self._load_favorites()

        InfoBar.success(
            title=tr('messages.add_success.title'),
            content=tr('messages.add_success.content', default=f"配色「{palette_data['name']}」已添加").format(name=palette_data['name']),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

    def _on_favorite_edit(self, favorite_data):
        """收藏编辑回调

        Args:
            favorite_data: 收藏项数据
        """
        favorite_id = favorite_data.get('id', '')
        default_name = favorite_data.get('name', '')

        dialog = EditPaletteDialog(
            default_name=default_name,
            palette_data=favorite_data,
            parent=self.window()
        )

        if dialog.exec() != EditPaletteDialog.DialogCode.Accepted:
            return

        new_palette_data = dialog.get_palette_data()
        if not new_palette_data:
            return

        if self._config_manager.update_favorite(favorite_id, new_palette_data):
            self._config_manager.save()
            self._load_favorites()

            InfoBar.success(
                title=tr('messages.update_success.title'),
                content=tr('messages.update_success.content', default=f"配色「{new_palette_data['name']}」已更新").format(name=new_palette_data['name']),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
        else:
            InfoBar.error(
                title=tr('messages.update_failed.title'),
                content=tr('messages.update_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )

    def _on_favorite_contrast(self, favorite_data):
        """收藏对比度检查回调

        Args:
            favorite_data: 收藏项数据
        """
        scheme_name = favorite_data.get('name', tr('palette_management.unnamed'))
        colors = favorite_data.get('colors', [])

        if not colors:
            InfoBar.warning(
                title=tr('messages.preview_failed.title'),
                content=tr('messages.preview_failed.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 显示对比度检查对话框
        dialog = ContrastCheckDialog(
            scheme_name=scheme_name,
            colors=colors,
            parent=self.window()
        )
        dialog.exec()

    def _on_favorite_color_changed(self, favorite_id: str, color_index: int, color_info: Dict[str, Any]):
        """收藏颜色变化回调

        Args:
            favorite_id: 收藏项ID
            color_index: 颜色索引
            color_info: 新的颜色信息
        """
        if self._config_manager.update_favorite_color(favorite_id, color_index, color_info):
            self._config_manager.save()

            InfoBar.success(
                title=tr('messages.color_updated.title'),
                content=tr('messages.color_updated.content', default=f"配色中的颜色已更新为 {color_info.get('hex', '#------')}").format(hex=color_info.get('hex', '#------')),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )

    def _load_settings(self):
        """加载显示设置"""
        hex_visible = self._config_manager.get('settings.hex_visible', True)
        color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self.palette_management_list.update_display_settings(hex_visible, color_modes)

    def update_display_settings(self, hex_visible=None, color_modes=None):
        """更新显示设置

        Args:
            hex_visible: 是否显示16进制颜色值
            color_modes: 色彩模式列表
        """
        self.palette_management_list.update_display_settings(hex_visible, color_modes)

    def _update_styles(self):
        """更新样式以适配主题"""
        title_color = get_title_color()
        self.title_label.setStyleSheet(f"color: {title_color.name()};")
        
        if is_windows_10():
            bg_color = get_interface_background_color()
            card_bg = get_card_background_color()
            border_color = get_border_color()
            text_color = get_text_color()
            
            self.setStyleSheet(f"""
                PaletteManagementInterface {{
                    background-color: {bg_color.name()};
                }}
                ScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
                ScrollArea > QWidget > QWidget {{
                    background-color: transparent;
                }}
                PaletteManagementSchemeCard,
                CardWidget {{
                    background-color: {card_bg.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 8px;
                }}
                PushButton {{
                    background-color: {card_bg.name()};
                    color: {text_color.name()};
                    border: 1px solid {border_color.name()};
                    border-radius: 4px;
                }}
                PushButton:hover {{
                    background-color: {card_bg.lighter(110).name() if not isDarkTheme() else card_bg.darker(110).name()};
                }}
                QLabel {{
                    color: {text_color.name()};
                }}
            """)
    
    def _on_language_changed(self):
        """语言切换回调"""
        self.update_texts()
        self.palette_management_list.update_texts()
    
    def update_texts(self):
        """更新界面文本"""
        self.title_label.setText(tr('palette_management.title'))
        self.add_button.setText(tr('palette_management.add'))
        self.import_button.setText(tr('palette_management.import'))
        self.export_button.setText(tr('palette_management.export'))
        self.clear_all_button.setText(tr('palette_management.clear_all'))
