"""对比度检查对话框

提供配色方案中任意两种颜色的对比度检查功能，
支持 WCAG 2.1 标准，实时预览文字可读性效果。
"""

# 标准库导入
from typing import List, Dict, Tuple

# 第三方库导入
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
    QFrame, QGridLayout, QScrollArea
)
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from qfluentwidgets import (
    ComboBox, PushButton, ToolButton, FluentIcon,
    isDarkTheme, qconfig, CardWidget
)

# 项目模块导入
from core.contrast import (
    calculate_contrast_ratio, get_contrast_info,
    rgb_to_hex, get_contrast_status_color
)
from ui.theme_colors import (
    get_dialog_bg_color, get_text_color, get_border_color,
    get_secondary_text_color, get_title_color, get_card_background_color
)
from utils import fix_windows_taskbar_icon_for_window, load_icon_universal, set_window_title_bar_theme


class ColorSelector(QWidget):
    """颜色选择器组件"""
    
    color_selected = Signal(int)  # 信号：选中颜色的索引
    
    def __init__(self, title: str, colors: List[Dict], parent=None):
        """初始化颜色选择器
        
        Args:
            title: 选择器标题（如"背景色"、"文本色"）
            colors: 颜色列表，每个颜色是一个字典，包含 'rgb' 键
            parent: 父窗口
        """
        self._title = title
        self._colors = colors
        self._selected_index = 0
        super().__init__(parent)
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题
        self.title_label = QLabel(self._title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # 颜色块按钮
        self.color_block = PushButton()
        self.color_block.setFixedSize(80, 60)
        self.color_block.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_block.clicked.connect(self._on_color_block_clicked)
        layout.addWidget(self.color_block, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 颜色下拉选择
        self.color_combo = ComboBox()
        self.color_combo.setFixedWidth(100)
        for i, color_data in enumerate(self._colors):
            rgb = color_data.get('rgb', [128, 128, 128])
            hex_val = rgb_to_hex(tuple(rgb))
            self.color_combo.addItem(f"颜色 {i+1}")
            self.color_combo.setItemData(i, i)
        self.color_combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self.color_combo, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 初始化显示
        self._update_color_display()
    
    def _update_styles(self):
        """更新样式以适配主题"""
        title_color = get_title_color()
        
        self.title_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {title_color.name()};"
        )
    
    def _update_color_display(self):
        """更新颜色显示"""
        if 0 <= self._selected_index < len(self._colors):
            rgb = self._colors[self._selected_index].get('rgb', [128, 128, 128])
            hex_val = rgb_to_hex(tuple(rgb))
            
            # 更新颜色块
            self.color_block.setStyleSheet(f"""
                PushButton {{
                    background-color: {hex_val};
                    border: 2px solid {get_border_color().name()};
                    border-radius: 6px;
                }}
                PushButton:hover {{
                    border: 2px solid {get_text_color().name()};
                }}
            """)
            
            # 更新下拉框
            self.color_combo.blockSignals(True)
            self.color_combo.setCurrentIndex(self._selected_index)
            self.color_combo.blockSignals(False)
    
    def _on_color_block_clicked(self):
        """颜色块点击 - 循环切换到下一个颜色"""
        self._selected_index = (self._selected_index + 1) % len(self._colors)
        self._update_color_display()
        self.color_selected.emit(self._selected_index)
    
    def _on_combo_changed(self, index: int):
        """下拉框选择改变"""
        if 0 <= index < len(self._colors):
            self._selected_index = index
            self._update_color_display()
            self.color_selected.emit(self._selected_index)
    
    def get_current_rgb(self) -> Tuple[int, int, int]:
        """获取当前选中的 RGB 颜色
        
        Returns:
            RGB 颜色元组 (r, g, b)
        """
        if 0 <= self._selected_index < len(self._colors):
            return tuple(self._colors[self._selected_index].get('rgb', [128, 128, 128]))
        return (128, 128, 128)
    
    def set_selected_index(self, index: int):
        """设置选中的颜色索引
        
        Args:
            index: 颜色索引
        """
        if 0 <= index < len(self._colors):
            self._selected_index = index
            self._update_color_display()


class PreviewCard(QWidget):
    """预览卡片组件"""
    
    def __init__(self, title: str, font_size: int, is_bold: bool = False, parent=None):
        """初始化预览卡片
        
        Args:
            title: 卡片标题
            font_size: 字体大小
            is_bold: 是否粗体
            parent: 父窗口
        """
        self._title = title
        self._font_size = font_size
        self._is_bold = is_bold
        self._bg_rgb = (255, 255, 255)
        self._text_rgb = (0, 0, 0)
        super().__init__(parent)
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)
    
    def setup_ui(self):
        """设置界面"""
        self.setFixedSize(140, 100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # 标题
        self.title_label = QLabel(self._title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.title_label)
        
        # 示例文字
        self.sample_label = QLabel("高颜色对比\n可使任何内\n容都更易于\n阅读")
        self.sample_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.sample_label.setWordWrap(True)
        layout.addWidget(self.sample_label)
        
        layout.addStretch()
    
    def _update_styles(self):
        """更新样式以适配主题"""
        secondary_color = get_secondary_text_color()
        self.title_label.setStyleSheet(
            f"font-size: 10px; color: {secondary_color.name()};"
        )
        self._update_preview()
    
    def _update_preview(self):
        """更新预览显示"""
        text_hex = rgb_to_hex(self._text_rgb)
        
        font_weight = "bold" if self._is_bold else "normal"
        
        self.sample_label.setStyleSheet(f"""
            font-size: {self._font_size}px;
            font-weight: {font_weight};
            color: {text_hex};
        """)
        
        self.update()
    
    def set_colors(self, bg_rgb: Tuple[int, int, int], text_rgb: Tuple[int, int, int]):
        """设置预览颜色
        
        Args:
            bg_rgb: 背景色 RGB 元组
            text_rgb: 文字色 RGB 元组
        """
        self._bg_rgb = bg_rgb
        self._text_rgb = text_rgb
        self._update_preview()
    
    def paintEvent(self, event):
        """绘制背景和边框"""
        from PySide6.QtGui import QPainter, QBrush, QPen
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        bg_color = QColor(self._bg_rgb[0], self._bg_rgb[1], self._bg_rgb[2])
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        
        # 绘制边框
        border_color = get_border_color()
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 8, 8)


class GraphicWidget(QWidget):
    """图形绘制组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._graphic_rgb = (0, 0, 0)
        self.setFixedSize(120, 60)
    
    def set_graphic_color(self, rgb: Tuple[int, int, int]):
        """设置图形颜色"""
        self._graphic_rgb = rgb
        self.update()
    
    def paintEvent(self, event):
        """绘制图形元件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        graphic_color = QColor(self._graphic_rgb[0], self._graphic_rgb[1], self._graphic_rgb[2])
        painter.setBrush(QBrush(graphic_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # 绘制方形
        painter.drawRect(20, 20, 20, 20)
        
        # 绘制圆形
        painter.drawEllipse(50, 20, 20, 20)
        
        # 绘制三角形
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        triangle = QPolygonF([
            QPointF(90, 20),
            QPointF(80, 40),
            QPointF(100, 40)
        ])
        painter.drawPolygon(triangle)


class GraphicPreviewCard(QWidget):
    """图形元件预览卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_rgb = (255, 255, 255)
        self._graphic_rgb = (0, 0, 0)
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)
    
    def setup_ui(self):
        """设置界面"""
        self.setFixedSize(140, 100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # 标题
        self.title_label = QLabel("图形元件")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.title_label)
        
        # 图形绘制区域
        self.graphic_widget = GraphicWidget()
        layout.addWidget(self.graphic_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
    
    def _update_styles(self):
        """更新样式以适配主题"""
        secondary_color = get_secondary_text_color()
        self.title_label.setStyleSheet(
            f"font-size: 10px; color: {secondary_color.name()};"
        )
        self.update()
    
    def set_colors(self, bg_rgb: Tuple[int, int, int], graphic_rgb: Tuple[int, int, int]):
        """设置预览颜色
        
        Args:
            bg_rgb: 背景色 RGB 元组
            graphic_rgb: 图形颜色 RGB 元组
        """
        self._bg_rgb = bg_rgb
        self._graphic_rgb = graphic_rgb
        self.update()
        self.graphic_widget.set_graphic_color(graphic_rgb)
    
    def paintEvent(self, event):
        """绘制背景和边框"""
        from PySide6.QtGui import QPainter, QBrush, QPen
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        bg_color = QColor(self._bg_rgb[0], self._bg_rgb[1], self._bg_rgb[2])
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        
        # 绘制边框
        border_color = get_border_color()
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 8, 8)


class ContrastCheckDialog(QDialog):
    """对比度检查对话框
    
    允许用户选择配色方案中的两种颜色进行对比度检查，
    并实时预览文字可读性效果。
    """
    
    def __init__(self, scheme_name: str, colors: List[Dict], parent=None):
        """初始化对比度检查对话框
        
        Args:
            scheme_name: 配色方案名称
            colors: 颜色列表，每个颜色是一个字典，包含 'rgb' 键
            parent: 父窗口
        """
        super().__init__(parent)
        self._scheme_name = scheme_name
        self._colors = colors
        
        self.setWindowTitle(f"对比度检查 - {scheme_name}")
        
        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())
        
        # 设置窗口标志 - 使用 MSWindowsFixedSizeDialogHint 防止 Windows 自动调整大小
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        
        # 设置固定大小（使用最小/最大尺寸确保不被压缩）
        self.setMinimumSize(480, 420)
        self.setMaximumSize(480, 420)
        self.resize(480, 420)
        
        # 设置窗口背景色
        bg_color = get_dialog_bg_color()
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color.name()}; }}")
        
        self.setup_ui()
        self._update_contrast()
        
        # 修复任务栏图标
        QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(self))
        
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_title_bar_theme)
    
    def setup_ui(self):
        """设置界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 获取主题颜色
        title_color = get_title_color()
        text_color = get_text_color()
        secondary_color = get_secondary_text_color()
        border_color = get_border_color()
        
        # 标题
        title_label = QLabel("对比度检查")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {title_color.name()};")
        main_layout.addWidget(title_label)
        
        # 配色方案名称
        name_label = QLabel(f"配色方案: {self._scheme_name}")
        name_label.setStyleSheet(f"font-size: 13px; color: {secondary_color.name()};")
        main_layout.addWidget(name_label)
        
        # 颜色选择区域
        selector_layout = QHBoxLayout()
        selector_layout.setSpacing(10)
        
        # 背景色选择器
        self.bg_selector = ColorSelector("背景色", self._colors)
        self.bg_selector.color_selected.connect(self._update_contrast)
        selector_layout.addWidget(self.bg_selector)
        
        # 交换按钮
        swap_layout = QVBoxLayout()
        swap_layout.addStretch()
        self.swap_button = ToolButton(FluentIcon.SYNC)
        self.swap_button.setFixedSize(32, 32)
        self.swap_button.setToolTip("交换颜色")
        self.swap_button.clicked.connect(self._swap_colors)
        swap_layout.addWidget(self.swap_button)
        swap_layout.addStretch()
        selector_layout.addLayout(swap_layout)
        
        # 文本色选择器
        self.text_selector = ColorSelector("文本色", self._colors)
        self.text_selector.color_selected.connect(self._update_contrast)
        # 默认选择最后一个颜色
        if len(self._colors) > 1:
            self.text_selector.set_selected_index(len(self._colors) - 1)
        selector_layout.addWidget(self.text_selector)
        
        main_layout.addLayout(selector_layout)
        
        # WCAG 等级选择
        level_layout = QHBoxLayout()
        level_layout.setSpacing(10)
        
        level_label = QLabel("WCAG 2.1 等级")
        level_label.setStyleSheet(f"font-size: 13px; color: {text_color.name()};")
        level_layout.addWidget(level_label)
        
        self.level_combo = ComboBox()
        self.level_combo.setFixedWidth(80)
        self.level_combo.addItem("AA")
        self.level_combo.addItem("AAA")
        self.level_combo.setCurrentIndex(0)
        self.level_combo.currentIndexChanged.connect(self._on_level_changed)
        level_layout.addWidget(self.level_combo)
        
        level_layout.addStretch()
        main_layout.addLayout(level_layout)
        
        # 对比度结果显示区域
        result_card = CardWidget()
        result_card.setFixedHeight(70)
        result_layout = QHBoxLayout(result_card)
        result_layout.setContentsMargins(15, 10, 15, 10)
        
        # 对比率标签
        self.ratio_label = QLabel("-- : 1")
        self.ratio_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {text_color.name()};")
        result_layout.addWidget(self.ratio_label)
        
        result_layout.addSpacing(15)
        
        # 等级标签
        self.level_label = QLabel("--")
        self.level_label.setStyleSheet(f"font-size: 16px; font-weight: bold;")
        result_layout.addWidget(self.level_label)
        
        result_layout.addStretch()
        
        main_layout.addWidget(result_card)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {border_color.name()};")
        main_layout.addWidget(line)
        
        # 预览区域标题
        preview_title = QLabel("预览效果")
        preview_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color.name()};")
        main_layout.addWidget(preview_title)
        
        # 预览卡片区域
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(10)
        
        # 一般文字预览
        self.normal_preview = PreviewCard("一般文字", 12)
        preview_layout.addWidget(self.normal_preview)
        
        # 大号文字预览
        self.large_preview = PreviewCard("大号文字", 16, is_bold=True)
        preview_layout.addWidget(self.large_preview)
        
        # 图形元件预览
        self.graphic_preview = GraphicPreviewCard()
        preview_layout.addWidget(self.graphic_preview)
        
        preview_layout.addStretch()
        main_layout.addLayout(preview_layout)
        
        # 说明文字
        self.description_label = QLabel(
            "WCAG 2.1 标准：普通文字 AA 需要 4.5:1，AAA 需要 7:1；"
            "大号文字 AA 需要 3:1，AAA 需要 4.5:1"
        )
        self.description_label.setStyleSheet(f"font-size: 11px; color: {secondary_color.name()};")
        self.description_label.setWordWrap(True)
        main_layout.addWidget(self.description_label)
        
        main_layout.addStretch()
    
    def _swap_colors(self):
        """交换背景色和文本色"""
        bg_index = self.bg_selector._selected_index
        text_index = self.text_selector._selected_index
        
        self.bg_selector.set_selected_index(text_index)
        self.text_selector.set_selected_index(bg_index)
        
        self._update_contrast()
    
    def _on_level_changed(self, index: int):
        """WCAG 等级切换"""
        self._update_contrast()
    
    def _update_contrast(self):
        """更新对比度计算和显示"""
        bg_rgb = self.bg_selector.get_current_rgb()
        text_rgb = self.text_selector.get_current_rgb()
        
        # 计算对比度
        info = get_contrast_info(bg_rgb, text_rgb)
        ratio = info['ratio']
        
        # 获取当前选择的等级
        selected_level = self.level_combo.currentText()  # "AA" 或 "AAA"
        
        # 更新对比率显示
        self.ratio_label.setText(f"{ratio} : 1")
        
        # 获取状态颜色
        is_dark = isDarkTheme()
        status_rgb = get_contrast_status_color(ratio, is_dark)
        status_color = QColor(status_rgb[0], status_rgb[1], status_rgb[2])
        
        # 根据选择的等级判断通过状态
        if selected_level == "AAA":
            # AAA 标准：普通文字 7:1，大号文字 4.5:1
            if ratio >= 7:
                level_text = "✓ 通过 AAA"
            elif ratio >= 4.5:
                level_text = "△ 仅大号通过"
            else:
                level_text = "✗ 不通过"
        else:
            # AA 标准：普通文字 4.5:1，大号文字 3:1
            if ratio >= 4.5:
                level_text = "✓ 通过 AA"
            elif ratio >= 3:
                level_text = "△ 仅大号通过"
            else:
                level_text = "✗ 不通过"
        
        self.level_label.setText(level_text)
        self.level_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {status_color.name()};"
        )
        
        # 更新预览卡片
        self.normal_preview.set_colors(bg_rgb, text_rgb)
        self.large_preview.set_colors(bg_rgb, text_rgb)
        self.graphic_preview.set_colors(bg_rgb, text_rgb)
    
    def _update_title_bar_theme(self):
        """更新标题栏主题以适配当前主题"""
        set_window_title_bar_theme(self, isDarkTheme())
    
    def showEvent(self, event):
        """窗口显示事件"""
        self._update_title_bar_theme()
        super().showEvent(event)
