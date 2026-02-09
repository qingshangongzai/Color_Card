# 标准库导入
import uuid
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QSizePolicy, QApplication, QLineEdit
)
from PySide6.QtGui import QColor
from qfluentwidgets import (
    CardWidget, ScrollArea, ToolButton, FluentIcon,
    InfoBar, InfoBarPosition, isDarkTheme, qconfig
)

# 项目模块导入
from core import get_color_info, hex_to_rgb
from .cards import COLOR_MODE_CONFIG, ColorModeContainer, get_text_color, get_border_color, get_placeholder_color
from .theme_colors import get_card_background_color
from utils.platform import is_windows_10


class ColorManagementColorCard(QWidget):
    """色彩管理中的单个色卡组件（与其他面板样式一致）"""

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
            # 输入无效，恢复原值
            self.hex_input.setText(self._hex_value)
            InfoBar.warning(
                title="输入无效",
                content=f"请输入有效的16进制颜色值（如 #FF0000）",
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


class ColorManagementSchemeCard(CardWidget):
    """色彩管理配色方案卡片（水平排列色卡样式，动态数量）"""

    delete_requested = Signal(str)
    rename_requested = Signal(str, str)  # favorite_id, new_name
    preview_requested = Signal(dict)  # favorite_data
    contrast_requested = Signal(dict)  # favorite_data
    color_changed = Signal(str, int, dict)  # favorite_id, color_index, new_color_info

    def __init__(self, favorite_data: dict, parent=None):
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

        # 色卡面板（水平排列）
        self.cards_panel = QWidget()
        cards_layout = QHBoxLayout(self.cards_panel)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(15)

        layout.addWidget(self.cards_panel)

        # 操作按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 对比度检查按钮
        self.contrast_button = ToolButton(FluentIcon.ZOOM_IN)
        self.contrast_button.setFixedSize(28, 28)
        self.contrast_button.clicked.connect(self._on_contrast_clicked)
        button_layout.addWidget(self.contrast_button)

        # 预览按钮（色盲模拟）
        self.preview_button = ToolButton(FluentIcon.VIEW)
        self.preview_button.setFixedSize(28, 28)
        self.preview_button.clicked.connect(self._on_preview_clicked)
        button_layout.addWidget(self.preview_button)

        # 重命名按钮
        self.rename_button = ToolButton(FluentIcon.EDIT)
        self.rename_button.setFixedSize(28, 28)
        self.rename_button.clicked.connect(self._on_rename_clicked)
        button_layout.addWidget(self.rename_button)

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
                ColorManagementSchemeCard,
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
            card = ColorManagementColorCard()
            card.set_color_modes(self._color_modes)
            card.hex_container.setVisible(self._hex_visible)
            card.color_changed.connect(lambda color_info, idx=i: self._on_color_changed(idx, color_info))
            self._color_cards.append(card)
            layout.addWidget(card)

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

    def _on_rename_clicked(self):
        """重命名按钮点击"""
        favorite_id = self._favorite_data.get('id', '')
        current_name = self._favorite_data.get('name', '')
        if favorite_id:
            self.rename_requested.emit(favorite_id, current_name)

    def _on_preview_clicked(self):
        """预览按钮点击（色盲模拟）"""
        self.preview_requested.emit(self._favorite_data)

    def _on_contrast_clicked(self):
        """对比度检查按钮点击"""
        self.contrast_requested.emit(self._favorite_data)

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


class ColorManagementSchemeList(QWidget):
    """色彩管理配色方案列表容器"""

    favorite_deleted = Signal(str)
    favorite_renamed = Signal(str, str)  # favorite_id, current_name
    favorite_preview = Signal(dict)  # favorite_data
    favorite_contrast = Signal(dict)  # favorite_data
    favorite_color_changed = Signal(str, int, dict)  # favorite_id, color_index, new_color_info

    def __init__(self, parent=None):
        self._favorites = []
        self._favorite_cards = {}
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
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

        self._text_label = QLabel("还没有收藏的配色方案")
        self._text_label.setStyleSheet(f"font-size: 14px; color: {get_text_color(secondary=True).name()};")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._text_label)

        self._hint_label = QLabel("在色彩提取或配色方案面板点击收藏按钮")
        self._hint_label.setStyleSheet(f"font-size: 12px; color: {get_text_color(secondary=True).name()};")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._hint_label)

        self.content_layout.addWidget(self._empty_widget, alignment=Qt.AlignmentFlag.AlignCenter)

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
            card = ColorManagementSchemeCard(favorite)
            card.set_hex_visible(self._hex_visible)
            card.set_color_modes(self._color_modes)
            card.delete_requested.connect(self.favorite_deleted)
            card.rename_requested.connect(self._on_rename_requested)
            card.preview_requested.connect(self._on_preview_requested)
            card.contrast_requested.connect(self._on_contrast_requested)
            card.color_changed.connect(self._on_color_changed)
            self.content_layout.addWidget(card)
            self._favorite_cards[favorite.get('id', '')] = card

        self.content_layout.addStretch()

    def _on_rename_requested(self, favorite_id, current_name):
        """重命名请求处理

        Args:
            favorite_id: 收藏项ID
            current_name: 当前名称
        """
        self.favorite_renamed.emit(favorite_id, current_name)

    def _on_preview_requested(self, favorite_data):
        """预览请求处理（色盲模拟）

        Args:
            favorite_data: 收藏项数据
        """
        self.favorite_preview.emit(favorite_data)

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
