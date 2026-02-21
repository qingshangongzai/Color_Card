"""色盲模拟预览对话框

提供配色方案的色盲模拟预览功能，支持多种色盲类型切换。
"""

# 标准库导入
from typing import List, Dict, Tuple

# 第三方库导入
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
    QFrame
)
from PySide6.QtGui import QColor
from qfluentwidgets import (
    ComboBox, isDarkTheme, qconfig, ScrollArea
)

# 项目模块导入
from utils import tr, fix_windows_taskbar_icon_for_window, load_icon_universal, set_window_title_bar_theme
from core.colorblind import (
    simulate_colorblind, get_colorblind_info, get_all_colorblind_types
)
from utils.theme_colors import (
    get_dialog_bg_color, get_text_color, get_border_color,
    get_secondary_text_color, get_title_color
)


class ColorBlock(QWidget):
    """颜色块组件"""
    
    def __init__(self, width: int = 60, height: int = 40, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._color = QColor(200, 200, 200)
        self._border_color = get_border_color()
    
    def set_color(self, rgb: Tuple[int, int, int]):
        """设置颜色"""
        self._color = QColor(rgb[0], rgb[1], rgb[2])
        self.update()
    
    def paintEvent(self, event):
        """绘制颜色块"""
        from PySide6.QtGui import QPainter, QBrush, QPen
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._color))
        painter.drawRoundedRect(1, 1, self.width()-2, self.height()-2, 6, 6)
        
        # 绘制边框
        painter.setPen(QPen(self._border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, self.width()-1, self.height()-1, 6, 6)


class ColorComparisonRow(QWidget):
    """颜色对比行组件 - 显示原颜色和模拟颜色"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._update_styles()
        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_styles)
    
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        # 左侧固定宽度区域（颜色块 + 箭头）
        color_area = QWidget()
        color_area_layout = QHBoxLayout(color_area)
        color_area_layout.setContentsMargins(0, 0, 0, 0)
        color_area_layout.setSpacing(5)
        color_area.setFixedWidth(155)
        
        # 原颜色块
        self.original_block = ColorBlock(50, 32)
        color_area_layout.addWidget(self.original_block)
        
        # 箭头标签
        self.arrow_label = QLabel("→")
        self.arrow_label.setStyleSheet("font-size: 16px;")
        self.arrow_label.setFixedWidth(16)
        self.arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color_area_layout.addWidget(self.arrow_label)
        
        # 模拟颜色块
        self.simulated_block = ColorBlock(50, 32)
        color_area_layout.addWidget(self.simulated_block)
        
        layout.addWidget(color_area)
        
        # 颜色值信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.original_hex = QLabel(tr('dialogs.colorblind.original') + ": #------")
        self.original_hex.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(self.original_hex)
        
        self.simulated_hex = QLabel(tr('dialogs.colorblind.simulated') + ": #------")
        self.simulated_hex.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(self.simulated_hex)
        
        layout.addLayout(info_layout)
        layout.addStretch()
    
    def _update_styles(self):
        """更新样式以适配主题"""
        secondary_color = get_secondary_text_color()
        self.arrow_label.setStyleSheet(f"font-size: 18px; color: {secondary_color.name()};")
        self.original_hex.setStyleSheet(f"font-size: 12px; color: {secondary_color.name()};")
        self.simulated_hex.setStyleSheet(f"font-size: 12px; color: {secondary_color.name()};")
    
    def set_colors(self, original_rgb: Tuple[int, int, int], simulated_rgb: Tuple[int, int, int]):
        """设置颜色对比
        
        Args:
            original_rgb: 原始 RGB 颜色
            simulated_rgb: 模拟后的 RGB 颜色
        """
        self.original_block.set_color(original_rgb)
        self.simulated_block.set_color(simulated_rgb)
        
        # 更新 HEX 显示
        original_hex = f"#{original_rgb[0]:02X}{original_rgb[1]:02X}{original_rgb[2]:02X}"
        simulated_hex = f"#{simulated_rgb[0]:02X}{simulated_rgb[1]:02X}{simulated_rgb[2]:02X}"
        
        self.original_hex.setText(f"{tr('dialogs.colorblind.original')}: {original_hex}")
        self.simulated_hex.setText(f"{tr('dialogs.colorblind.simulated')}: {simulated_hex}")


class ColorblindPreviewDialog(QDialog):
    """色盲模拟预览对话框
    
    显示配色方案在不同色盲类型下的视觉效果。
    """
    
    def __init__(self, scheme_name: str, colors: List[Dict], parent=None):
        """初始化色盲预览对话框
        
        Args:
            scheme_name: 配色方案名称
            colors: 颜色列表，每个颜色是一个字典，包含 'rgb' 键
            parent: 父窗口
        """
        super().__init__(parent)
        self._scheme_name = scheme_name
        self._colors = colors
        self._current_type = 'normal'
        
        self.setWindowTitle(tr('dialogs.colorblind.window_title', name=scheme_name))
        self.setFixedSize(320, 420)
        
        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())
        
        # 设置窗口标志
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.CustomizeWindowHint
        )
        
        # 设置窗口背景色
        bg_color = get_dialog_bg_color()
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color.name()}; }}")
        
        self.setup_ui()
        self.update_preview()
        
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
        title_label = QLabel(tr('dialogs.colorblind.title'))
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {title_color.name()};")
        main_layout.addWidget(title_label)
        
        name_label = QLabel(tr('dialogs.colorblind.scheme_name', name=self._scheme_name))
        name_label.setStyleSheet(f"font-size: 13px; color: {secondary_color.name()};")
        main_layout.addWidget(name_label)
        
        # 色盲类型选择
        type_layout = QHBoxLayout()
        type_layout.setSpacing(10)
        
        type_label = QLabel(tr('dialogs.colorblind.colorblind_type'))
        type_label.setStyleSheet(f"font-size: 13px; color: {text_color.name()};")
        type_layout.addWidget(type_label)
        
        self.type_combo = ComboBox()
        self.type_combo.setMinimumWidth(150)
        
        # 添加色盲类型选项
        self._type_keys = []
        colorblind_types = get_all_colorblind_types()
        for key, info in colorblind_types.items():
            self.type_combo.addItem(info['name'])
            self._type_keys.append(key)
        
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        
        main_layout.addLayout(type_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {border_color.name()};")
        main_layout.addWidget(line)
        
        # 列标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # 左侧固定宽度区域标题
        color_area_title = QWidget()
        color_area_title_layout = QHBoxLayout(color_area_title)
        color_area_title_layout.setContentsMargins(5, 0, 0, 0)
        color_area_title_layout.setSpacing(5)
        color_area_title.setFixedWidth(155)
        
        original_title = QLabel(tr('dialogs.colorblind.original_color'))
        original_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color.name()};")
        original_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        original_title.setFixedWidth(60)
        color_area_title_layout.addWidget(original_title)
        
        arrow_spacer = QLabel("")
        arrow_spacer.setFixedWidth(15)
        color_area_title_layout.addWidget(arrow_spacer)
        
        simulated_title = QLabel(tr('dialogs.colorblind.simulated_color'))
        simulated_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {text_color.name()};")
        simulated_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        simulated_title.setFixedWidth(70)
        color_area_title_layout.addWidget(simulated_title)
        
        header_layout.addWidget(color_area_title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # 颜色对比列表（带滚动条）
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            ScrollArea {
                background-color: transparent;
                border: none;
            }
            ScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.comparison_container = QWidget()
        self.comparison_container.setStyleSheet("background: transparent;")
        self.comparison_layout = QVBoxLayout(self.comparison_container)
        self.comparison_layout.setContentsMargins(0, 0, 0, 0)
        self.comparison_layout.setSpacing(5)
        self.comparison_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 创建颜色对比行
        self.comparison_rows = []
        for color_data in self._colors:
            row = ColorComparisonRow()
            self.comparison_rows.append(row)
            self.comparison_layout.addWidget(row)
        
        self.comparison_layout.addStretch()
        scroll_area.setWidget(self.comparison_container)
        main_layout.addWidget(scroll_area, stretch=1)
        
        # 说明文字
        self.description_label = QLabel("")
        self.description_label.setStyleSheet(f"font-size: 12px; color: {secondary_color.name()}; padding: 5px;")
        self.description_label.setWordWrap(True)
        main_layout.addWidget(self.description_label)
    
    def _on_type_changed(self, index: int):
        """色盲类型改变"""
        if 0 <= index < len(self._type_keys):
            self._current_type = self._type_keys[index]
            self.update_preview()
    
    def update_preview(self):
        """更新预览显示"""
        # 更新每个颜色行的显示
        for i, row in enumerate(self.comparison_rows):
            if i < len(self._colors):
                color_data = self._colors[i]
                original_rgb = tuple(color_data.get('rgb', [128, 128, 128]))
                
                # 计算模拟颜色
                simulated_rgb = simulate_colorblind(original_rgb, self._current_type)
                
                row.set_colors(original_rgb, simulated_rgb)
        
        # 更新说明文字
        info = get_colorblind_info(self._current_type)
        self.description_label.setText(tr('dialogs.colorblind.description', text=info['description']))
    
    def _update_title_bar_theme(self):
        """更新标题栏主题以适配当前主题"""
        set_window_title_bar_theme(self, isDarkTheme())
    
    def showEvent(self, event):
        """窗口显示事件"""
        self._update_title_bar_theme()
        super().showEvent(event)
