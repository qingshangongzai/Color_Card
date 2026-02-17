# 标准库导入
import re
from datetime import datetime

# 第三方库导入
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)
from PySide6.QtGui import QColor
from qfluentwidgets import (
    LineEdit, PrimaryPushButton, PushButton, ToolButton, FluentIcon,
    ScrollArea, isDarkTheme, qconfig
)

# 项目模块导入
from core import get_color_info, hex_to_rgb
from ui.theme_colors import get_dialog_bg_color, get_text_color, get_border_color
from utils import fix_windows_taskbar_icon_for_window, load_icon_universal, set_window_title_bar_theme


class ColorInputRow(QWidget):
    """颜色输入行组件"""

    def __init__(self, index: int, parent=None):
        self._index = index
        self._color_info = None
        super().__init__(parent)
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 序号标签
        self.index_label = QLabel(f"颜色 {self._index + 1}")
        self.index_label.setFixedWidth(50)
        layout.addWidget(self.index_label)

        # HEX输入框
        self.hex_input = LineEdit()
        self.hex_input.setPlaceholderText("#RRGGBB")
        self.hex_input.setMaxLength(7)
        self.hex_input.setFixedWidth(100)
        self.hex_input.textChanged.connect(self._on_hex_changed)
        layout.addWidget(self.hex_input)

        # 颜色预览块
        self.preview_block = QLabel()
        self.preview_block.setFixedSize(28, 28)
        self._update_preview_style(None)
        layout.addWidget(self.preview_block)

        # 删除按钮
        self.delete_button = ToolButton(FluentIcon.REMOVE)
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_button)

        layout.addStretch()

    def _update_styles(self):
        """更新样式以适配主题"""
        text_color = get_text_color()
        self.index_label.setStyleSheet(f"color: {text_color.name()}; font-size: 13px;")
        self._update_preview_style(self._color_info)

    def _update_preview_style(self, color_info):
        """更新预览块样式"""
        border_color = get_border_color()
        if color_info:
            rgb = color_info.get('rgb', [0, 0, 0])
            color_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
            self.preview_block.setStyleSheet(
                f"background-color: {color_str}; border-radius: 4px; border: 1px solid {border_color.name()};"
            )
        else:
            self.preview_block.setStyleSheet(
                f"background-color: transparent; border-radius: 4px; border: 1px solid {border_color.name()};"
            )

    def _on_hex_changed(self, text: str):
        """HEX值变化处理"""
        text = text.strip().upper()

        # 自动添加#前缀
        if text and not text.startswith('#'):
            text = '#' + text
            self.hex_input.setText(text)
            return

        # 验证HEX格式
        if self._is_valid_hex(text):
            try:
                r, g, b = hex_to_rgb(text)
                self._color_info = get_color_info(r, g, b)
                self._color_info['hex'] = text
                self._update_preview_style(self._color_info)
            except ValueError:
                self._color_info = None
                self._update_preview_style(None)
        else:
            self._color_info = None
            self._update_preview_style(None)

    def _is_valid_hex(self, text: str) -> bool:
        """验证HEX格式"""
        if not text:
            return False
        pattern = r'^#[0-9A-F]{6}$'
        return bool(re.match(pattern, text.upper()))

    def _on_delete_clicked(self):
        """删除按钮点击"""
        # 找到 EditPaletteDialog 父组件
        dialog = self.window()
        if isinstance(dialog, EditPaletteDialog):
            dialog.remove_color_row(self)
        self.deleteLater()

    def get_color_info(self):
        """获取颜色信息"""
        return self._color_info

    def has_valid_color(self) -> bool:
        """是否有有效颜色"""
        return self._color_info is not None

    def set_index(self, index: int):
        """设置序号"""
        self._index = index
        self.index_label.setText(f"颜色 {index + 1}")

    def set_color_info(self, color_info: dict):
        """设置颜色信息

        Args:
            color_info: 颜色信息字典
        """
        self._color_info = color_info
        hex_value = color_info.get('hex', '')
        if hex_value:
            self.hex_input.setText(hex_value)
            self._update_preview_style(color_info)


class EditPaletteDialog(QDialog):
    """编辑配色对话框"""

    def __init__(self, default_name="", palette_data=None, parent=None):
        """初始化添加/编辑配色对话框

        Args:
            default_name: 默认配色名称
            palette_data: 已有配色数据（编辑模式），None表示添加模式
            parent: 父窗口
        """
        super().__init__(parent)
        self._palette_data = palette_data
        self._is_edit_mode = palette_data is not None
        self.setWindowTitle("编辑配色" if self._is_edit_mode else "添加配色")
        self.setFixedSize(300, 400)
        self._default_name = default_name
        self._color_rows = []

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

        # 如果是编辑模式，加载已有数据
        if self._is_edit_mode:
            self._load_palette_data()

        # 修复任务栏图标
        QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(self))

        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_title_bar_theme)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 名称输入区域
        name_layout = QHBoxLayout()
        name_label = QLabel("配色名称：")
        name_label.setStyleSheet(f"color: {get_text_color().name()}; font-size: 13px;")
        name_layout.addWidget(name_label)

        self.name_input = LineEdit()
        self.name_input.setText(self._default_name)
        self.name_input.setPlaceholderText("输入配色名称...")
        self.name_input.setClearButtonEnabled(True)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # 分隔线
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {get_border_color().name()};")
        layout.addWidget(separator)

        # 颜色列表标题
        colors_title = QLabel("颜色列表（至少输入一个）")
        colors_title.setStyleSheet(f"color: {get_text_color().name()}; font-size: 13px;")
        layout.addWidget(colors_title)

        # 颜色输入区域（可滚动）
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("ScrollArea { border: none; background: transparent; }")
        scroll_area.setMaximumHeight(200)

        # 设置滚动条角落为透明（防止出现灰色方块）
        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        scroll_area.setCornerWidget(corner_widget)

        self.colors_container = QWidget()
        self.colors_container.setStyleSheet("background: transparent;")
        self.colors_layout = QVBoxLayout(self.colors_container)
        self.colors_layout.setContentsMargins(0, 0, 0, 0)
        self.colors_layout.setSpacing(10)
        self.colors_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(self.colors_container)
        layout.addWidget(scroll_area)

        # 添加颜色按钮
        self.add_color_button = PushButton(FluentIcon.ADD, "添加颜色")
        self.add_color_button.setFixedHeight(32)
        self.add_color_button.clicked.connect(self._on_add_color)
        layout.addWidget(self.add_color_button)

        # 按钮区域
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # 取消按钮
        self.cancel_button = PushButton("取消")
        self.cancel_button.setMinimumWidth(80)
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        # 确认按钮
        self.confirm_button = PrimaryPushButton("确认")
        self.confirm_button.setMinimumWidth(80)
        self.confirm_button.clicked.connect(self._on_confirm)
        buttons_layout.addWidget(self.confirm_button)

        layout.addLayout(buttons_layout)

        # 设置焦点到名称输入框
        self.name_input.setFocus()
        self.name_input.selectAll()

        # 添加第一个颜色输入行
        self._on_add_color()

    def _on_add_color(self):
        """添加颜色输入行"""
        row = ColorInputRow(len(self._color_rows), self.colors_container)
        self._color_rows.append(row)
        self.colors_layout.addWidget(row)

    def remove_color_row(self, row):
        """移除颜色输入行

        Args:
            row: 要移除的 ColorInputRow 实例
        """
        if row in self._color_rows:
            self._color_rows.remove(row)
        # 更新剩余行的序号
        for i, r in enumerate(self._color_rows):
            r.set_index(i)

    def _load_palette_data(self):
        """加载已有配色数据（编辑模式）"""
        if not self._palette_data:
            return

        # 设置名称
        name = self._palette_data.get('name', '')
        if name:
            self.name_input.setText(name)

        # 获取已有颜色
        colors = self._palette_data.get('colors', [])

        # 清空默认添加的空行（从布局中移除、隐藏并删除）
        while self._color_rows:
            row = self._color_rows.pop()
            self.colors_layout.removeWidget(row)
            row.hide()
            row.deleteLater()

        # 立即处理事件，确保widget被正确删除
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()

        # 添加已有颜色
        for i, color_info in enumerate(colors):
            row = ColorInputRow(i, self.colors_container)
            row.set_color_info(color_info)
            self._color_rows.append(row)
            self.colors_layout.addWidget(row)

    def _on_confirm(self):
        """确认按钮点击"""
        # 获取有效颜色
        valid_colors = []
        for row in self._color_rows:
            if row.has_valid_color():
                valid_colors.append(row.get_color_info())

        # 验证至少有一个有效颜色
        if not valid_colors:
            self._show_error_tooltip("请至少输入一个有效的颜色值")
            return

        # 获取名称
        name = self.name_input.text().strip()
        if not name:
            name = self._default_name

        self._palette_data = {
            'name': name,
            'colors': valid_colors,
            'created_at': datetime.now().isoformat()
        }

        self.accept()

    def _show_error_tooltip(self, message: str):
        """显示错误提示（使用自定义 QLabel 替代 InfoBar）"""
        # 创建错误提示标签
        error_label = QLabel(self)
        error_label.setText(f"⚠ {message}")
        error_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3CD;
                color: #856404;
                border: 1px solid #FFEAA7;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }
        """)
        error_label.adjustSize()
        
        # 定位在对话框顶部中央
        x = (self.width() - error_label.width()) // 2
        error_label.move(x, 5)
        error_label.show()
        
        # 3秒后自动消失
        QTimer.singleShot(3000, error_label.deleteLater)

    def get_palette_data(self):
        """获取配色数据

        Returns:
            dict: 包含名称、颜色列表和创建时间的字典
        """
        return getattr(self, '_palette_data', None)

    def _update_title_bar_theme(self):
        """更新标题栏主题以适配当前主题"""
        set_window_title_bar_theme(self, isDarkTheme())

    def showEvent(self, event):
        """窗口显示事件 - 在显示前设置标题栏主题避免闪烁"""
        self._update_title_bar_theme()
        super().showEvent(event)
