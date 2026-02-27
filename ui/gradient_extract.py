# 标准库导入
import uuid
from datetime import datetime
from typing import List, Tuple

# 第三方库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QSplitter, QVBoxLayout, QWidget
)
from qfluentwidgets import (
    FluentIcon, InfoBar, InfoBarPosition, PushButton, Slider, ToolButton, qconfig, isDarkTheme
)

# 项目模块导入
from core import generate_gradient, generate_random_gradient, get_color_info, rgb_to_hex
from core import get_config_manager
from ui.cards import ColorCard
from utils import tr, get_locale_manager, calculate_grid_columns
from utils.theme_colors import get_border_color, get_card_background_color, get_text_color


class ColorDot(QWidget):
    """颜色圆点，仅用于显示"""

    def __init__(self, initial_color: str = "#FF0000", parent=None):
        super().__init__(parent)
        self._color = initial_color
        self._radius = 12
        self.setFixedSize(24, 24)
        self._update_style()

    def _update_style(self):
        """更新样式"""
        border_color = get_border_color()
        self.setStyleSheet(f"""
            ColorDot {{
                background-color: {self._color};
                border: 2px solid {border_color.name()};
                border-radius: {self._radius}px;
            }}
        """)

    def paintEvent(self, event):
        """绘制事件，确保背景色显示"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景圆
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(self.rect().center(), self._radius, self._radius)

        # 绘制边框
        border_color = get_border_color()
        painter.setPen(QColor(border_color))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.rect().center(), self._radius - 1, self._radius - 1)

    def set_color(self, hex_color: str):
        """设置颜色

        Args:
            hex_color: HEX颜色值，如"#FF0000"
        """
        self._color = hex_color
        self._update_style()
        self.update()

    def get_color(self) -> str:
        """获取当前颜色"""
        return self._color


class GradientPreviewWidget(QWidget):
    """渐变预览控件，显示渐变色竖条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors: List[Tuple[int, int, int]] = []
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_colors(self, colors: List[Tuple[int, int, int]]):
        """设置渐变色

        Args:
            colors: RGB颜色列表 [(r, g, b), ...]
        """
        self._colors = colors
        self.update()

    def paintEvent(self, event):
        """绘制渐变预览"""
        if not self._colors:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        color_count = len(self._colors)

        if color_count == 0:
            return

        # 计算每个颜色条的宽度
        bar_width = width / color_count

        # 绘制每个颜色条
        for i, (r, g, b) in enumerate(self._colors):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(r, g, b))
            x = i * bar_width
            # 最后一个条可能稍微宽一点以填满空间
            w = bar_width if i < color_count - 1 else width - x
            painter.drawRect(int(x), 0, int(w) + 1, height)


class GradientCardPanel(QWidget):
    """渐变色卡面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: List[ColorCard] = []
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # 创建卡片容器
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent; border: none;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        self.scroll_area.setWidget(self.cards_container)
        self.main_layout.addWidget(self.scroll_area)

    def set_colors(self, colors: List[Tuple[int, int, int]]):
        """设置颜色列表并更新显示

        Args:
            colors: RGB颜色列表 [(r, g, b), ...]
        """
        # 清空现有卡片
        self._clear_cards()

        if not colors:
            return

        # 使用 calculate_grid_columns 计算列数（与内置色彩/配色管理一致）
        color_count = len(colors)
        columns = calculate_grid_columns(color_count)

        # 按行创建卡片
        current_row_layout = None
        for i, rgb in enumerate(colors):
            # 每行开始时创建新的水平布局
            if i % columns == 0:
                current_row_layout = QHBoxLayout()
                current_row_layout.setContentsMargins(0, 0, 0, 0)
                current_row_layout.setSpacing(10)
                self.cards_layout.addLayout(current_row_layout)

            # 创建卡片
            card = ColorCard(i)
            card.set_hex_visible(self._hex_visible)
            card.set_color_modes(self._color_modes)

            # 设置颜色信息
            r, g, b = rgb
            color_info = get_color_info(r, g, b)
            card.set_color(color_info)

            self._cards.append(card)
            current_row_layout.addWidget(card, stretch=1)

        # 添加拉伸因子使卡片均匀分布
        self.cards_layout.addStretch()

    def _clear_cards(self):
        """清空所有卡片"""
        # 删除所有卡片前先触发 closeEvent 断开信号
        for card in self._cards:
            card.close()
            card.deleteLater()
        self._cards.clear()

        # 清空布局中的所有行
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.layout():
                # 删除行布局中的所有控件
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().close()
                        child.widget().deleteLater()

    def set_hex_visible(self, visible: bool):
        """设置16进制显示"""
        self._hex_visible = visible
        for card in self._cards:
            card.set_hex_visible(visible)

    def set_color_modes(self, modes: List[str]):
        """设置色彩模式"""
        if len(modes) < 2:
            return
        self._color_modes = [modes[0], modes[1]]
        for card in self._cards:
            card.set_color_modes(self._color_modes)

    def get_colors(self) -> List[dict]:
        """获取所有颜色的信息字典列表"""
        colors = []
        for card in self._cards:
            if hasattr(card, '_current_color_info') and card._current_color_info:
                colors.append(card._current_color_info)
        return colors


class GradientExtractInterface(QWidget):
    """渐变提取界面"""

    favorite_requested = Signal(dict)  # 收藏请求信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('gradientExtract')
        self._config_manager = get_config_manager()
        self._color_space = self._config_manager.get('settings.gradient_color_space', 'lab')
        self._start_color = "#FF5733"
        self._end_color = "#33FF57"
        self._steps = 2  # 默认2个中间色，共4个颜色

        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)
        get_locale_manager().language_changed.connect(self._on_language_changed)

        # 初始生成渐变
        self._generate_gradient()

    def setup_ui(self):
        """设置界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(0)

        # ========== 上半部分：控制区 + 渐变预览区 ==========
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)

        # ---- 左侧：控制区 ----
        control_widget = QWidget()
        control_widget.setFixedWidth(240)
        control_layout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(15)

        # 起始颜色选择
        start_color_layout = QHBoxLayout()
        start_color_layout.setSpacing(8)
        self.start_color_dot = ColorDot(self._start_color)
        self.start_color_label = QLabel(tr('gradient_extract.start_color'))
        self.start_color_label.setFixedWidth(56)
        self.start_color_input = QLineEdit(self._start_color)
        self.start_color_input.setFixedWidth(105)
        self.start_color_input.setFixedHeight(28)
        self.start_color_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_color_input.textChanged.connect(self._on_start_color_input_changed)
        start_color_layout.addStretch()
        start_color_layout.addWidget(self.start_color_dot)
        start_color_layout.addWidget(self.start_color_label)
        start_color_layout.addWidget(self.start_color_input)
        start_color_layout.addStretch()
        control_layout.addLayout(start_color_layout)

        # 结束颜色选择
        end_color_layout = QHBoxLayout()
        end_color_layout.setSpacing(8)
        self.end_color_dot = ColorDot(self._end_color)
        self.end_color_label = QLabel(tr('gradient_extract.end_color'))
        self.end_color_label.setFixedWidth(56)
        self.end_color_input = QLineEdit(self._end_color)
        self.end_color_input.setFixedWidth(105)
        self.end_color_input.setFixedHeight(28)
        self.end_color_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.end_color_input.textChanged.connect(self._on_end_color_input_changed)
        end_color_layout.addStretch()
        end_color_layout.addWidget(self.end_color_dot)
        end_color_layout.addWidget(self.end_color_label)
        end_color_layout.addWidget(self.end_color_input)
        end_color_layout.addStretch()
        control_layout.addLayout(end_color_layout)

        # 中间色数量控制
        steps_layout = QVBoxLayout()
        steps_header_layout = QHBoxLayout()
        steps_header_layout.setSpacing(8)
        self.steps_label = QLabel(tr('gradient_extract.steps'))
        self.steps_label.setFixedWidth(80)
        self.steps_value_label = QLabel(str(self._steps))
        self.steps_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        steps_header_layout.addStretch()
        steps_header_layout.addWidget(self.steps_label)
        steps_header_layout.addWidget(self.steps_value_label)
        steps_header_layout.addStretch()
        steps_layout.addLayout(steps_header_layout)

        self.steps_slider = Slider(Qt.Orientation.Horizontal)
        self.steps_slider.setMinimum(1)
        self.steps_slider.setMaximum(10)
        self.steps_slider.setValue(self._steps)
        self.steps_slider.valueChanged.connect(self._on_steps_changed)
        steps_layout.addWidget(self.steps_slider)
        control_layout.addLayout(steps_layout)

        top_layout.addWidget(control_widget, alignment=Qt.AlignmentFlag.AlignBottom)

        # ---- 右侧：渐变预览区 ----
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        self.gradient_preview = GradientPreviewWidget()
        preview_layout.addWidget(self.gradient_preview)

        top_layout.addWidget(preview_widget, stretch=1, alignment=Qt.AlignmentFlag.AlignBottom)

        splitter.addWidget(top_widget)

        # ========== 中间：操作按钮区 ==========
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 10, 0, 10)
        button_layout.setSpacing(15)
        button_layout.addStretch()

        self.random_button = PushButton(FluentIcon.SYNC, tr('gradient_extract.random'))
        self.random_button.clicked.connect(self._on_random_clicked)
        button_layout.addWidget(self.random_button)

        self.favorite_button = PushButton(FluentIcon.HEART, tr('gradient_extract.favorite'))
        self.favorite_button.clicked.connect(self._on_favorite_clicked)
        button_layout.addWidget(self.favorite_button)

        button_layout.addStretch()
        splitter.addWidget(button_widget)

        # ========== 下半部分：色卡排列区 ==========
        self.card_panel = GradientCardPanel()
        splitter.addWidget(self.card_panel)

        # 设置分割器比例
        splitter.setStretchFactor(0, 0)  # 上半部分（控制区+预览区）
        splitter.setStretchFactor(1, 0)  # 中间按钮
        splitter.setStretchFactor(2, 1)  # 下半部分色卡（获得更多空间）

        main_layout.addWidget(splitter)

    def _update_styles(self):
        """更新样式以适配主题"""
        text_color = get_text_color()
        secondary_text = get_text_color(secondary=True)

        self.start_color_label.setStyleSheet(f"color: {text_color.name()}; font-size: 13px;")
        self.end_color_label.setStyleSheet(f"color: {text_color.name()}; font-size: 13px;")
        self.steps_label.setStyleSheet(f"color: {text_color.name()}; font-size: 13px;")
        self.steps_value_label.setStyleSheet(f"color: {secondary_text.name()}; font-size: 13px;")

        # 更新输入框样式（与配色管理一致）
        self._update_hex_input_style()

    def _update_hex_input_style(self):
        """更新16进制输入框样式（与配色管理一致）"""
        primary_color = get_text_color(secondary=False)
        secondary_color = get_text_color(secondary=True)
        border_color = get_border_color()

        input_style = f"""
            QLineEdit {{
                font-size: 12px;
                font-weight: bold;
                color: {primary_color.name()};
                background-color: transparent;
                border: 1px solid {border_color.name()};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 2px solid #0078d4;
            }}
        """
        self.start_color_input.setStyleSheet(input_style)
        self.end_color_input.setStyleSheet(input_style)

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        self.start_color_label.setText(tr('gradient_extract.start_color'))
        self.end_color_label.setText(tr('gradient_extract.end_color'))
        self.steps_label.setText(tr('gradient_extract.steps'))
        self.random_button.setText(tr('gradient_extract.random'))
        self.favorite_button.setText(tr('gradient_extract.favorite'))

    def _on_start_color_input_changed(self, text: str):
        """起始颜色输入框改变"""
        if self._is_valid_hex(text):
            self._start_color = text.upper()
            self.start_color_dot.set_color(self._start_color)
            self._generate_gradient()

    def _on_end_color_input_changed(self, text: str):
        """结束颜色输入框改变"""
        if self._is_valid_hex(text):
            self._end_color = text.upper()
            self.end_color_dot.set_color(self._end_color)
            self._generate_gradient()

    def _is_valid_hex(self, text: str) -> bool:
        """检查是否为有效的HEX颜色值"""
        if not text:
            return False
        text = text.strip()
        if text.startswith('#'):
            text = text[1:]
        return len(text) == 6 and all(c in '0123456789ABCDEFabcdef' for c in text)

    def _on_steps_changed(self, value: int):
        """中间色数量改变"""
        self._steps = value
        self.steps_value_label.setText(str(value))
        self._generate_gradient()

    def _generate_gradient(self):
        """生成渐变色"""
        try:
            colors = generate_gradient(
                self._start_color,
                self._end_color,
                self._steps,
                self._color_space
            )
            self._current_colors = colors
            self.gradient_preview.set_colors(colors)
            self.card_panel.set_colors(colors)
        except Exception as e:
            print(f"生成渐变失败: {e}")

    def _on_random_clicked(self):
        """随机按钮点击"""
        start_hex, end_hex, colors = generate_random_gradient(self._steps, self._color_space)
        self._start_color = start_hex
        self._end_color = end_hex
        self.start_color_dot.set_color(start_hex)
        self.end_color_dot.set_color(end_hex)
        self.start_color_input.setText(start_hex)
        self.end_color_input.setText(end_hex)
        self._current_colors = colors
        self.gradient_preview.set_colors(colors)
        self.card_panel.set_colors(colors)

    def _on_favorite_clicked(self):
        """收藏按钮点击"""
        colors = self.card_panel.get_colors()
        if not colors:
            InfoBar.warning(
                title=tr('messages.no_colors.title'),
                content=tr('messages.no_colors.content'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 复制颜色数据，避免引用问题（与P0修复一致）
        colors = [color.copy() for color in colors]

        # 获取当前收藏数量，生成默认名称（与其他面板一致）
        favorites_count = len(self._config_manager.get_favorites())
        default_name = f"配色 {favorites_count + 1}"

        # 创建收藏数据（参考 preset_color 的格式）
        favorite_data = {
            "id": str(uuid.uuid4()),
            "name": default_name,
            "colors": colors,
            "created_at": datetime.now().isoformat(),
            "source": "gradient_extract"
        }

        # 打开编辑对话框
        from dialogs import EditPaletteDialog
        dialog = EditPaletteDialog(
            default_name=default_name,
            palette_data=favorite_data,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取编辑后的数据
            edited_data = dialog.get_palette_data()
            if edited_data:
                # 发射信号让主窗口处理
                self.favorite_requested.emit(edited_data)

                # 显示成功提示
                InfoBar.success(
                    title=tr('gradient_extract.favorite_success.title'),
                    content=tr('gradient_extract.favorite_success.content'),
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self.window()
                )

    def set_color_space(self, color_space: str):
        """设置颜色空间

        Args:
            color_space: 'rgb', 'hsb', 或 'lab'
        """
        self._color_space = color_space
        self._generate_gradient()

    def set_hex_visible(self, visible: bool):
        """设置16进制显示"""
        self.card_panel.set_hex_visible(visible)

    def set_color_modes(self, modes: List[str]):
        """设置色彩模式"""
        self.card_panel.set_color_modes(modes)
