# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, InfoBar, InfoBarPosition, PushButton, ToolButton, qconfig

# 项目模块导入
from utils.theme_colors import (
    get_border_color, get_placeholder_color, get_secondary_text_color,
    get_text_color, get_zone_background_color, get_zone_text_color
)


class BaseCard(QWidget):
    """卡片基类，提供统一的卡片接口
    
    子类需要实现：
        - setup_ui(): 设置界面
        - clear(): 清空显示
    """
    
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面（子类必须实现）"""
        raise NotImplementedError("子类必须实现 setup_ui 方法")
    
    def clear(self):
        """清空显示（子类必须实现）"""
        raise NotImplementedError("子类必须实现 clear 方法")


class BaseCardPanel(QWidget):
    """卡片面板基类，提供统一的卡片管理功能
    
    功能：
        - 卡片列表管理
        - 卡片数量控制（2-6个）
        - 批量清空卡片
    """
    
    def __init__(self, parent=None, card_count: int = 5):
        super().__init__(parent)
        self._card_count = card_count
        self.cards = []
        self.setup_ui()
        self._create_initial_cards()
    
    def _create_initial_cards(self):
        """创建初始卡片"""
        for i in range(self._card_count):
            card = self._create_card(i)
            self.cards.append(card)
            self.layout().addWidget(card)
    
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # 设置sizePolicy，允许水平压缩但保持最小宽度
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    
    def set_card_count(self, count: int):
        """设置卡片数量
        
        Args:
            count: 卡片数量 (2-6)
        """
        if count < 2 or count > 6:
            return
        
        if count == self._card_count:
            return
        
        old_count = self._card_count
        self._card_count = count
        
        layout = self.layout()
        
        if count > old_count:
            self._add_cards(old_count, count)
        else:
            self._remove_cards(old_count, count)
    
    def _add_cards(self, old_count: int, new_count: int):
        """增加卡片（子类重写）"""
        for i in range(old_count, new_count):
            card = self._create_card(i)
            self.cards.append(card)
            self.layout().addWidget(card)
    
    def _remove_cards(self, old_count: int, new_count: int):
        """减少卡片"""
        for i in range(old_count - 1, new_count - 1, -1):
            card = self.cards.pop()
            self.layout().removeWidget(card)
            card.deleteLater()
    
    def _create_card(self, index: int):
        """创建单个卡片（子类必须实现）
        
        Args:
            index: 卡片索引
            
        Returns:
            BaseCard: 卡片实例
        """
        raise NotImplementedError("子类必须实现 _create_card 方法")
    
    def clear_all(self):
        """清空所有卡片"""
        for card in self.cards:
            card.clear()


# 色彩模式配置：模式名称 -> (显示名称, 标签列表, 单位列表, 格式化函数)
COLOR_MODE_CONFIG = {
    'HSB': (
        'HSB',
        ['H:', 'S:', 'B:'],
        ['°', '%', '%'],
        lambda values: [f"{values[0]}°", f"{values[1]}%", f"{values[2]}%"]
    ),
    'LAB': (
        'LAB',
        ['L:', 'A:', 'B:'],
        ['', '', ''],
        lambda values: [str(values[0]), str(values[1]), str(values[2])]
    ),
    'HSL': (
        'HSL',
        ['H:', 'S:', 'L:'],
        ['°', '%', '%'],
        lambda values: [f"{values[0]}°", f"{values[1]}%", f"{values[2]}%"]
    ),
    'CMYK': (
        'CMYK',
        ['C:', 'M:', 'Y:', 'K:'],
        ['%', '%', '%', '%'],
        lambda values: [f"{values[0]}%", f"{values[1]}%", f"{values[2]}%", f"{values[3]}%"]
    ),
    'RGB': (
        'RGB',
        ['R:', 'G:', 'B:'],
        ['', '', ''],
        lambda values: [str(values[0]), str(values[1]), str(values[2])]
    )
}





class ColorValueLabel(QWidget):
    """显示单个颜色值的标签"""
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 1, 3, 1)
        layout.setSpacing(3)

        self.label = QLabel(label_text)
        self.value = QLabel("--")

        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addStretch()

    def set_value(self, value):
        self.value.setText(str(value))


class ColorModeContainer(QWidget):
    """显示单个色彩模式的容器"""
    def __init__(self, mode='HSB', parent=None):
        super().__init__(parent)
        self._mode = mode
        self._labels = []
        self.setup_ui()
        self._update_styles()
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 根据模式创建标签
        config = COLOR_MODE_CONFIG.get(self._mode, COLOR_MODE_CONFIG['HSB'])
        labels_text = config[1]
        self._labels = []
        for text in labels_text:
            label = ColorValueLabel(text)
            self._labels.append(label)
            layout.addWidget(label)

    def _update_styles(self):
        """更新样式以适配主题"""
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            label_color = "#bbbbbb"
            value_color = "#ffffff"
        else:
            label_color = "#666666"
            value_color = "#333333"
        
        for label in self._labels:
            label.label.setStyleSheet(f"color: {label_color}; font-size: 11px;")
            label.value.setStyleSheet(f"color: {value_color}; font-size: 12px; font-weight: bold;")

    def set_mode(self, mode):
        """设置色彩模式"""
        if self._mode == mode:
            return
        self._mode = mode

        # 清除现有标签
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重新创建标签
        config = COLOR_MODE_CONFIG.get(mode, COLOR_MODE_CONFIG['HSB'])
        labels_text = config[1]
        self._labels = []
        for text in labels_text:
            label = ColorValueLabel(text)
            self._labels.append(label)
            layout.addWidget(label)
        
        # 应用当前主题样式
        self._update_styles()

    def update_values(self, color_info):
        """更新颜色值显示"""
        mode_key = self._mode.lower()
        if mode_key not in color_info:
            return

        values = color_info[mode_key]
        config = COLOR_MODE_CONFIG.get(self._mode, COLOR_MODE_CONFIG['HSB'])
        format_func = config[3]
        formatted_values = format_func(values)

        for i, label in enumerate(self._labels):
            if i < len(formatted_values):
                label.set_value(formatted_values[i])
            else:
                label.set_value("--")

    def clear_values(self):
        """清空所有值"""
        for label in self._labels:
            label.set_value("--")


class ColorCard(BaseCard):
    """单个色卡组件"""
    def __init__(self, index, parent=None):
        self._hex_value = "--"
        self._color_modes = ['HSB', 'LAB']
        self._current_color_info = None
        super().__init__(index, parent)
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_color_block_style)

    def setup_ui(self):
        from PySide6.QtWidgets import QSizePolicy

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        # 设置sizePolicy，允许垂直压缩
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 设置色卡最小高度，确保文字区域有足够空间
        self.setMinimumHeight(120)

        # 颜色块
        self.color_block = QWidget()
        self.color_block.setMinimumHeight(30)
        self.color_block.setMaximumHeight(80)
        self._update_placeholder_style()
        layout.addWidget(self.color_block)

        # 数值区域（两列布局）
        values_container = QWidget()
        values_container.setMinimumHeight(45)
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
        self.hex_container.setMinimumHeight(26)
        self.hex_container.setMaximumHeight(36)
        hex_layout = QHBoxLayout(self.hex_container)
        hex_layout.setContentsMargins(0, 2, 0, 0)
        hex_layout.setSpacing(3)

        # 16进制值显示按钮
        self.hex_button = PushButton("--")
        self.hex_button.setFixedHeight(24)
        self.hex_button.setEnabled(False)
        self._update_hex_button_style()

        # 复制按钮
        self.copy_button = ToolButton(FluentIcon.COPY)
        self.copy_button.setFixedSize(24, 24)
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

        # 如果有当前颜色信息，更新显示
        if self._current_color_info:
            self.update_color_display()

    def set_color(self, color_info):
        """设置颜色信息"""
        self._current_color_info = color_info

        # 更新颜色块
        r, g, b = color_info['rgb']
        color_str = f"rgb({r}, {g}, {b})"
        border_color = get_border_color()
        self.color_block.setStyleSheet(
            f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
        )

        # 更新色彩模式值
        self.update_color_display()

        # 更新16进制值
        self._hex_value = color_info['hex']
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
        self.hex_container.setVisible(visible)


class ColorCardPanel(BaseCardPanel):
    """色卡面板（包含多个色卡）"""
    def __init__(self, parent=None, card_count=5):
        self._hex_visible = True
        self._color_modes = ['HSB', 'LAB']
        super().__init__(parent, card_count)

    def _create_card(self, index):
        """创建色卡实例"""
        card = ColorCard(index)
        card.set_color_modes(self._color_modes)
        card.set_hex_visible(self._hex_visible)
        return card

    def set_color_modes(self, modes):
        """设置显示的色彩模式"""
        if len(modes) < 2:
            return

        self._color_modes = [modes[0], modes[1]]
        for card in self.cards:
            card.set_color_modes(self._color_modes)

    def update_color(self, index, color_info):
        """更新指定索引的颜色"""
        if 0 <= index < len(self.cards):
            self.cards[index].set_color(color_info)

    def set_hex_visible(self, visible):
        """设置是否显示16进制颜色值"""
        self._hex_visible = visible
        for card in self.cards:
            card.set_hex_visible(visible)

    def is_hex_visible(self):
        """获取16进制颜色值显示状态"""
        return self._hex_visible





class ZoneValueLabel(QWidget):
    """显示Zone值的标签 - 主题适配背景框 + 主题适配文字"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 30)
        self._zone = -1
        self._luminance = 0

    def set_zone(self, zone: int, luminance: int = 0):
        """设置Zone值"""
        self._zone = zone
        self._luminance = luminance
        self.update()

    def clear(self):
        """清空显示"""
        self._zone = -1
        self._luminance = 0
        self.update()

    def get_zone_label(self) -> str:
        """获取Zone显示标签"""
        if self._zone < 0:
            return "--"
        return str(self._zone)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 主题适配背景框
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(get_zone_background_color())
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)

        # 主题适配文字
        painter.setPen(get_zone_text_color())
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)

        label = self.get_zone_label()
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, label)


class LuminanceCard(BaseCard):
    """单个明度信息卡 - 简化版，只显示Zone"""
    def __init__(self, index, parent=None):
        super().__init__(index, parent)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Zone显示框
        self.zone_label = ZoneValueLabel()
        layout.addWidget(self.zone_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 索引标签
        index_label = QLabel(f"#{self.index + 1}")
        secondary_color = get_secondary_text_color()
        index_label.setStyleSheet(f"color: {secondary_color.name()}; font-size: 11px;")
        index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(index_label)

        layout.addStretch()

    def set_zone(self, zone: int, luminance: int = 0):
        """设置Zone信息"""
        self.zone_label.set_zone(zone, luminance)

    def clear(self):
        """清空显示"""
        self.zone_label.clear()


class LuminanceCardPanel(BaseCardPanel):
    """明度信息卡面板（包含多个Zone卡）"""
    def __init__(self, parent=None, card_count=5):
        super().__init__(parent, card_count)

    def _create_card(self, index):
        """创建明度卡实例"""
        return LuminanceCard(index)

    def update_zone(self, index: int, zone: int, luminance: int = 0):
        """更新指定索引的Zone"""
        if 0 <= index < len(self.cards):
            self.cards[index].set_zone(zone, luminance)
