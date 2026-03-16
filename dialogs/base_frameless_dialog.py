# 第三方库导入
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPalette, QColor
from qframelesswindow import FramelessDialog

# 项目模块导入
from utils.icon import get_icon_path
from utils.theme_colors import (
    get_text_color, get_dialog_bg_color,
    get_close_button_hover_bg_color,
    get_close_button_hover_color,
    get_close_button_pressed_color
)


class BaseFramelessDialog(FramelessDialog):
    """无边框对话框基类

    提供统一的 Fluent Design 风格标题栏和主题适配功能。
    子类只需调用 _setup_title_bar() 和 _update_styles() 即可。

    使用示例:
        class MyDialog(BaseFramelessDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("我的对话框")
                self.setFixedSize(400, 300)

                # 设置自定义标题栏
                self._setup_title_bar()

                # 初始化样式
                self._update_styles()

                # 设置界面
                self.setup_ui()

                # 监听主题变化
                self._theme_connection = qconfig.themeChangedFinished.connect(
                    self._update_styles
                )

            def closeEvent(self, event):
                # 断开信号连接
                try:
                    qconfig.themeChangedFinished.disconnect(self._theme_connection)
                except (TypeError, RuntimeError):
                    pass
                super().closeEvent(event)
    """

    def _setup_title_bar(self):
        """设置自定义 Fluent Design 风格标题栏"""
        # 获取 FramelessDialog 内置的标题栏
        title_bar = self.titleBar
        h_layout = title_bar.layout()
        if not h_layout:
            return

        # 获取主题颜色
        text_color = get_text_color()
        text_color_str = text_color.name()

        # 创建标题栏控件：左边距、Logo、间距、标题
        # 1. 左边距
        left_spacer = QLabel(title_bar)
        left_spacer.setFixedWidth(10)

        # 2. Logo
        icon_path = get_icon_path()
        logo_label = None
        if icon_path:
            logo_label = QLabel(title_bar)
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                logo_label.setPixmap(pixmap.scaled(
                    20, 20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))

        # 3. Logo和标题之间的间距
        spacer_label = QLabel(title_bar)
        spacer_label.setFixedWidth(8)

        # 4. 标题
        title_label = QLabel(self.windowTitle(), title_bar)
        title_label.setStyleSheet(f"color: {text_color_str}; font-size: 13px; font-weight: 500;")

        # 按顺序插入到布局开头（倒序插入）
        for widget in [title_label, spacer_label, logo_label, left_spacer]:
            if widget:
                h_layout.insertWidget(0, widget)
                h_layout.setAlignment(widget, Qt.AlignmentFlag.AlignVCenter)

        # 保存标题标签引用，以便主题切换时更新
        self._title_label = title_label

    def _update_close_button_color(self, text_color):
        """更新关闭按钮颜色以适配主题

        Args:
            text_color: 文本颜色 (QColor)
        """
        title_bar = self.titleBar
        if hasattr(title_bar, 'closeBtn') and title_bar.closeBtn:
            close_btn = title_bar.closeBtn
            # 设置正常状态颜色
            close_btn.setNormalColor(text_color)
            # 设置悬停状态颜色
            close_btn.setHoverColor(get_close_button_hover_color())
            close_btn.setHoverBackgroundColor(get_close_button_hover_bg_color())
            # 设置按下状态颜色
            close_btn.setPressedColor(get_close_button_pressed_color())

    def _update_styles(self):
        """更新样式以适配主题"""
        text_color = get_text_color()
        text_color_str = text_color.name()
        bg_color = get_dialog_bg_color()

        # 设置 QLabel 文字颜色样式表
        self.setStyleSheet(f"""
            QLabel {{
                color: {text_color_str};
            }}
        """)

        # 使用 QPalette 设置窗口背景色
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(bg_color.name()))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # 更新标题标签颜色（如果存在）
        if hasattr(self, '_title_label') and self._title_label:
            self._title_label.setStyleSheet(f"color: {text_color_str}; font-size: 13px; font-weight: 500;")

        # 更新关闭按钮颜色
        self._update_close_button_color(text_color)
