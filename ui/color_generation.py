"""配色生成模块

包含配色生成的界面组件和主界面，支持多种配色算法和交互式色轮。
"""

# ==================== 导入 ====================
# 标准库导入
import uuid
from datetime import datetime

# 第三方库导入
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QApplication,
    QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor
from qfluentwidgets import (
    CardWidget, PushButton, ToolButton, FluentIcon, InfoBar, InfoBarPosition,
    qconfig, isDarkTheme, ComboBox, PrimaryPushButton, Slider
)

# 项目模块导入
from core import get_color_info, get_config_manager, hsb_to_rgb, rgb_to_hsb, adjust_brightness
from utils import tr, get_locale_manager
from dialogs import EditPaletteDialog
from .cards import BaseCard, BaseCardPanel, ColorModeContainer, get_text_color, get_placeholder_color, get_border_color
from .color_wheel import InteractiveColorWheel
from .theme_colors import get_canvas_empty_bg_color


# ==================== 配色生成组件 ====================
class GenerationColorInfoCard(BaseCard):
    """配色生成颜色信息卡片（与ColorCard样式一致）"""

    clicked = Signal(int)

    def __init__(self, index: int, parent=None):
        self._hex_value = "--"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
        self._hex_visible = True
        super().__init__(index, parent)
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_color_block_style)

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 设置sizePolicy，允许垂直压缩
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 设置色卡最小高度，确保基本显示
        self.setMinimumHeight(120)

        # 颜色块
        self.color_block = QWidget()
        self.color_block.setMinimumHeight(40)
        self.color_block.setMaximumHeight(80)
        self._update_placeholder_style()
        layout.addWidget(self.color_block)

        # 数值区域（两列布局）
        values_container = QWidget()
        values_container.setMinimumHeight(50)
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
        layout.addStretch()

        # 设置点击事件
        self.setCursor(Qt.CursorShape.PointingHandCursor)

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
            r, g, b = self._current_color_info['rgb']
            color_str = f"rgb({r}, {g}, {b})"
            border_color = get_border_color()
            self.color_block.setStyleSheet(
                f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
            )
        else:
            # 无颜色时更新占位符样式
            self._update_placeholder_style()

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
            # 显示复制成功提示
            InfoBar.success(
                title=tr('color_generation.copied'),
                content=tr('color_generation.copied_content', hex=self._hex_value),
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

        # 如果有当前颜色信息，更新显示
        if self._current_color_info:
            self.update_color_display()

    def set_color(self, rgb: Tuple[int, int, int]):
        """设置颜色

        Args:
            rgb: RGB颜色元组 (r, g, b)
        """
        self._current_color_info = get_color_info(rgb[0], rgb[1], rgb[2])

        # 更新颜色块
        r, g, b = self._current_color_info['rgb']
        color_str = f"rgb({r}, {g}, {b})"
        border_color = get_border_color()
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
        )

        # 更新色彩模式值
        self.update_color_display()

        # 更新16进制值
        self._hex_value = self._current_color_info['hex']
        self.hex_button.setText(self._hex_value)
        self.hex_button.setEnabled(True)
        self.copy_button.setEnabled(True)

    def update_color_display(self):
        """根据当前模式更新颜色值显示"""
        if not self._current_color_info:
            return

        self.mode_container_1.update_values(self._current_color_info)
        self.mode_container_2.update_values(self._current_color_info)

    def clear(self):
        """清空颜色，恢复默认状态"""
        self._current_color_info = None

        # 重置颜色块
        self._update_placeholder_style()

        # 重置所有值
        self.mode_container_1.clear_values()
        self.mode_container_2.clear_values()

        # 重置16进制值
        self._hex_value = "--"
        self.hex_button.setText("--")
        self.hex_button.setEnabled(False)
        self.copy_button.setEnabled(False)

    def set_hex_visible(self, visible):
        """设置16进制显示区域的可见性"""
        self._hex_visible = visible
        self.hex_container.setVisible(visible)

    def mousePressEvent(self, event):
        """处理鼠标点击"""
        self.clicked.emit(self.index)
        super().mousePressEvent(event)


class GenerationColorPanel(BaseCardPanel):
    """配色生成色块面板（支持动态卡片数量）"""

    color_clicked = Signal(int)

    def __init__(self, parent=None, card_count=5):
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        super().__init__(parent, card_count)

    def _create_card(self, index):
        """创建色卡实例"""
        card = GenerationColorInfoCard(index)
        card.set_color_modes(self._color_modes)
        card.set_hex_visible(self._hex_visible)
        card.clicked.connect(self.on_card_clicked)
        return card

    def on_card_clicked(self, index):
        """卡片点击回调"""
        self.color_clicked.emit(index)

    def set_color_modes(self, modes):
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self.cards:
            card.set_color_modes(self._color_modes)

    def set_hex_visible(self, visible):
        """设置是否显示16进制颜色值"""
        self._hex_visible = visible
        for card in self.cards:
            card.set_hex_visible(visible)

    def set_colors(self, colors: list[tuple[int, int, int]]):
        """设置颜色列表

        Args:
            colors: RGB颜色列表
        """
        for i, card in enumerate(self.cards):
            if i < len(colors):
                card.set_color(colors[i])
            else:
                card.clear()

    def update_settings(self, hex_visible, color_modes):
        """统一更新显示设置

        Args:
            hex_visible: 是否显示16进制颜色值
            color_modes: 色彩模式列表
        """
        self.set_hex_visible(hex_visible)
        self.set_color_modes(color_modes)


# ==================== 配色生成界面 ====================
class ColorGenerationInterface(QWidget):
    """配色生成界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('colorGenerationInterface')
        self._current_scheme = 'monochromatic'
        self._base_hue = 0.0
        self._base_saturation = 100.0
        self._base_brightness = 100.0
        self._brightness_value = 100  # 全局明度值 (10-100)，直接对应HSB的B值
        self._scheme_colors = []  # 配色颜色列表 [(h, s, b), ...]
        self._color_wheel_mode = 'RGB'  # 色轮模式：RGB 或 RYB
        self._colors_generated = False  # 颜色是否已生成（延迟生成优化）

        self._config_manager = get_config_manager()

        self.setup_ui()
        self.setup_connections()
        self._load_settings()
        # 根据初始配色设置卡片数量
        self._update_card_count()
        # 延迟生成配色颜色，避免阻塞启动
        # 颜色将在首次显示时生成
        self._update_styles()
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_styles)

    def showEvent(self, event):
        """界面显示事件，延迟生成配色颜色"""
        super().showEvent(event)
        # 首次显示时生成配色颜色
        if not self._colors_generated:
            self._colors_generated = True
            QTimer.singleShot(0, self._generate_scheme_colors)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部控制栏（居中显示）
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setSpacing(15)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 配色选择下拉框
        self.scheme_label = QLabel(tr('color_generation.title'))
        top_layout.addWidget(self.scheme_label)

        self.scheme_combo = ComboBox(self)
        self.scheme_combo.addItem(tr('color_generation.schemes.monochromatic'))
        self.scheme_combo.addItem(tr('color_generation.schemes.analogous'))
        self.scheme_combo.addItem(tr('color_generation.schemes.complementary'))
        self.scheme_combo.addItem(tr('color_generation.schemes.split_complementary'))
        self.scheme_combo.addItem(tr('color_generation.schemes.double_complementary'))
        self.scheme_combo.setItemData(0, "monochromatic")
        self.scheme_combo.setItemData(1, "analogous")
        self.scheme_combo.setItemData(2, "complementary")
        self.scheme_combo.setItemData(3, "split_complementary")
        self.scheme_combo.setItemData(4, "double_complementary")
        self.scheme_combo.setFixedWidth(150)
        top_layout.addWidget(self.scheme_combo)

        # 随机按钮
        self.random_btn = PrimaryPushButton(FluentIcon.SYNC, tr('color_generation.random'), self)
        self.random_btn.setFixedWidth(100)
        top_layout.addWidget(self.random_btn)

        # 收藏按钮
        self.favorite_button = PrimaryPushButton(FluentIcon.HEART, tr('color_generation.favorite'), self)
        self.favorite_button.setFixedWidth(80)
        self.favorite_button.clicked.connect(self._on_favorite_clicked)
        top_layout.addWidget(self.favorite_button)

        layout.addWidget(top_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # 使用分割器分隔上下区域（避免重叠）
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setMinimumHeight(300)
        splitter.setHandleWidth(0)  # 隐藏分隔条
        layout.addWidget(splitter, stretch=1)

        # 上半部分：色轮和明度调整
        upper_widget = QWidget()
        upper_layout = QVBoxLayout(upper_widget)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(15)

        # 色轮容器（与图片显示组件样式一致）
        self.wheel_container = QWidget(self)
        self.wheel_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.wheel_container.setMinimumSize(300, 200)
        bg_color = get_canvas_empty_bg_color()
        self.wheel_container.setStyleSheet(f"background-color: {bg_color.name()}; border-radius: 8px;")

        wheel_container_layout = QVBoxLayout(self.wheel_container)
        wheel_container_layout.setContentsMargins(10, 10, 10, 10)

        # 可交互色环（在容器内自适应，占满整个容器）
        self.color_wheel = InteractiveColorWheel(self.wheel_container)
        wheel_container_layout.addWidget(self.color_wheel, stretch=1)

        upper_layout.addWidget(self.wheel_container, stretch=1)

        # 明度调整滑块（色轮下方，整体居中但控件紧凑排列）
        brightness_container = QWidget()
        brightness_layout = QHBoxLayout(brightness_container)
        brightness_layout.setSpacing(5)
        brightness_layout.setContentsMargins(0, 0, 0, 0)

        self.brightness_label = QLabel(tr('color_generation.brightness'))
        brightness_layout.addWidget(self.brightness_label)

        self.brightness_slider = Slider(Qt.Orientation.Horizontal, brightness_container)
        self.brightness_slider.setRange(10, 100)
        self.brightness_slider.setValue(100)
        self.brightness_slider.setFixedWidth(200)
        brightness_layout.addWidget(self.brightness_slider)

        self.brightness_value_label = QLabel("100")
        self.brightness_value_label.setFixedWidth(30)
        brightness_layout.addWidget(self.brightness_value_label)

        upper_layout.addWidget(brightness_container, alignment=Qt.AlignmentFlag.AlignCenter)

        splitter.addWidget(upper_widget)

        # 下方：色块面板
        self.color_panel = GenerationColorPanel(self)
        self.color_panel.setMinimumHeight(150)
        splitter.addWidget(self.color_panel)

        splitter.setSizes([400, 200])

    def setup_connections(self):
        """设置信号连接"""
        self.scheme_combo.currentIndexChanged.connect(self.on_scheme_changed)
        self.random_btn.clicked.connect(self.on_random_clicked)
        self.color_wheel.base_color_changed.connect(self.on_base_color_changed)
        self.color_wheel.scheme_color_changed.connect(self.on_scheme_color_changed)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        
        locale_manager = get_locale_manager()
        if locale_manager:
            locale_manager.language_changed.connect(self._on_language_changed)

    def _update_styles(self):
        """更新样式以适配主题"""
        if isDarkTheme():
            label_color = "#ffffff"
            value_color = "#ffffff"
        else:
            label_color = "#333333"
            value_color = "#333333"

        self.scheme_label.setStyleSheet(f"color: {label_color};")
        self.brightness_label.setStyleSheet(f"color: {label_color};")
        self.brightness_value_label.setStyleSheet(f"color: {value_color};")

    def update_texts(self):
        """更新所有界面文本"""
        self.scheme_label.setText(tr('color_generation.title'))
        self.random_btn.setText(tr('color_generation.random'))
        self.favorite_button.setText(tr('color_generation.favorite'))
        self.brightness_label.setText(tr('color_generation.brightness'))
        
        current_index = self.scheme_combo.currentIndex()
        self.scheme_combo.setItemText(0, tr('color_generation.schemes.monochromatic'))
        self.scheme_combo.setItemText(1, tr('color_generation.schemes.analogous'))
        self.scheme_combo.setItemText(2, tr('color_generation.schemes.complementary'))
        self.scheme_combo.setItemText(3, tr('color_generation.schemes.split_complementary'))
        self.scheme_combo.setItemText(4, tr('color_generation.schemes.double_complementary'))

    def _on_language_changed(self):
        """语言切换回调"""
        self.update_texts()

    def _load_settings(self):
        """加载显示设置"""
        # 从配置管理器读取设置
        hex_visible = self._config_manager.get('settings.hex_visible', True)
        color_modes = self._config_manager.get('settings.color_modes', ['HSB', 'LAB'])
        self._color_wheel_mode = self._config_manager.get('settings.color_wheel_mode', 'RGB')

        # 应用设置到色块面板
        self.color_panel.update_settings(hex_visible, color_modes)

    def _update_card_count(self):
        """根据当前配色更新卡片数量"""
        scheme_counts = {
            'monochromatic': 4,      # 同色系：4个
            'analogous': 4,          # 邻近色：4个
            'complementary': 5,      # 互补色：5个
            'split_complementary': 3, # 分离补色：3个
            'double_complementary': 4  # 双补色：4个
        }
        count = scheme_counts.get(self._current_scheme, 5)
        self.color_panel.set_card_count(count)

    def update_display_settings(self, hex_visible=None, color_modes=None):
        """更新显示设置（由设置界面调用）

        Args:
            hex_visible: 是否显示16进制颜色值
            color_modes: 色彩模式列表
        """
        if hex_visible is not None:
            self.color_panel.set_hex_visible(hex_visible)

        if color_modes is not None and len(color_modes) >= 2:
            self.color_panel.set_color_modes(color_modes)

    def on_scheme_changed(self, index):
        """配色生成改变回调"""
        self._current_scheme = self.scheme_combo.currentData()

        # 根据配色类型调整卡片数量
        self._update_card_count()

        self._generate_scheme_colors()

    def on_random_clicked(self):
        """随机按钮点击回调"""
        import random
        self._base_hue = random.uniform(0, 360)
        self._base_saturation = random.uniform(60, 100)
        self.color_wheel.set_base_color(self._base_hue, self._base_saturation, self._base_brightness)
        self._generate_scheme_colors()

    def on_base_color_changed(self, h, s, b):
        """基准颜色改变回调

        色相变化时，所有采样点跟随旋转；
        饱和度变化时，仅基准点变化，其他采样点保持原位。
        """
        # 计算色相变化量
        delta_h = h - self._base_hue
        # 计算饱和度变化量
        delta_s = s - self._base_saturation

        # 更新基准点
        self._base_hue = h
        self._base_saturation = s

        # RYB模式下，重新生成配色以保持RYB色轮上的相对角度关系
        if self._color_wheel_mode == 'RYB' and delta_h != 0:
            self._generate_scheme_colors()
            return

        # 色相变化：所有采样点跟着旋转（仅RGB模式）
        if delta_h != 0 and self._scheme_colors:
            for i in range(len(self._scheme_colors)):
                old_h, old_s, old_b = self._scheme_colors[i]
                new_h = (old_h + delta_h) % 360
                self._scheme_colors[i] = (new_h, old_s, old_b)

        # 饱和度变化：更新 _scheme_colors[0]（基准点）
        if delta_s != 0 and self._scheme_colors:
            old_h, old_s, old_b = self._scheme_colors[0]
            self._scheme_colors[0] = (old_h, s, old_b)

        # 更新色轮显示
        self.color_wheel.set_base_color(self._base_hue, self._base_saturation, self._base_brightness)
        self.color_wheel.set_scheme_colors(self._scheme_colors)

        # 更新色块面板
        colors = [hsb_to_rgb(h_val, s_val, b_val) for h_val, s_val, b_val in self._scheme_colors]
        self.color_panel.set_colors(colors)

    def on_scheme_color_changed(self, index, h, s, b):
        """配色采样点颜色改变回调

        Args:
            index: 采样点索引
            h: 色相
            s: 饱和度
            b: 亮度
        """
        # 更新配色数据
        if 0 <= index < len(self._scheme_colors):
            self._scheme_colors[index] = (h, s, b)

            # 转换为RGB并更新色块面板
            rgb = hsb_to_rgb(h, s, b)
            self.color_panel.set_colors([hsb_to_rgb(*c) for c in self._scheme_colors])

    def on_brightness_changed(self, value):
        """明度调整回调"""
        self._brightness_value = value
        self.brightness_value_label.setText(str(value))
        # 更新色轮的全局明度
        self.color_wheel.set_global_brightness(value)
        self._generate_scheme_colors()

    def set_color_wheel_mode(self, mode: str):
        """设置色轮模式

        Args:
            mode: 'RGB' 或 'RYB'
        """
        if self._color_wheel_mode != mode:
            self._color_wheel_mode = mode
            self._generate_scheme_colors()

    def _generate_scheme_colors(self):
        """生成配色颜色"""
        from core import (
            get_scheme_preview_colors, get_scheme_preview_colors_ryb,
        )

        # 根据配色类型确定颜色数量
        scheme_counts = {
            'monochromatic': 4,      # 同色系：4个
            'analogous': 4,          # 邻近色：4个
            'complementary': 5,      # 互补色：5个
            'split_complementary': 3, # 分离补色：3个
            'double_complementary': 4  # 双补色：4个
        }
        count = scheme_counts.get(self._current_scheme, 5)

        # 根据色轮模式选择对应的配色生成函数，传入基准饱和度
        if self._color_wheel_mode == 'RYB':
            colors = get_scheme_preview_colors_ryb(self._current_scheme, self._base_hue, count, self._base_saturation)
        else:
            colors = get_scheme_preview_colors(self._current_scheme, self._base_hue, count, self._base_saturation)

        # 转换为HSB并应用全局明度值
        self._scheme_colors = []
        for i, rgb in enumerate(colors):
            h, s, b = rgb_to_hsb(*rgb)
            # 使用全局明度值，忽略原始配色中的B值
            self._scheme_colors.append((h, s, self._brightness_value))

        # 转换为RGB颜色用于显示
        colors = [hsb_to_rgb(h, s, b) for h, s, b in self._scheme_colors]

        # 更新色块面板
        self.color_panel.set_colors(colors)

        # 更新色环上的配色点
        self.color_wheel.set_scheme_colors(self._scheme_colors)

    def _on_favorite_clicked(self):
        """收藏按钮点击回调"""
        colors = []
        for card in self.color_panel.cards:
            if card._current_color_info:
                colors.append(card._current_color_info)

        if not colors:
            InfoBar.warning(
                title=tr('color_generation.favorite_failed'),
                content=tr('color_generation.no_colors_to_favorite'),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
            return

        # 弹出编辑配色对话框
        default_name = f"配色 {len(self._config_manager.get_favorites()) + 1}"

        # 构造配色数据
        palette_data = {
            "name": default_name,
            "colors": colors
        }

        dialog = EditPaletteDialog(
            default_name=default_name,
            palette_data=palette_data,
            parent=self.window()
        )

        if dialog.exec() != EditPaletteDialog.DialogCode.Accepted:
            return

        new_palette_data = dialog.get_palette_data()
        if not new_palette_data:
            return

        favorite_data = {
            "id": str(uuid.uuid4()),
            "name": new_palette_data['name'],
            "colors": new_palette_data['colors'],
            "created_at": datetime.now().isoformat(),
            "source": "color_scheme"
        }

        self._config_manager.add_favorite(favorite_data)
        self._config_manager.save()

        # 刷新配色管理面板
        window = self.window()
        if window and hasattr(window, 'refresh_palette_management'):
            window.refresh_palette_management()

        InfoBar.success(
            title=tr('color_generation.favorite_success'),
            content=tr('color_generation.favorite_success_content', name=favorite_data['name']),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )
