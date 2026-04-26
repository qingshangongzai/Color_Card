# 第三方库导入
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPalette
from qframelesswindow import FramelessDialog
from qfluentwidgets import qconfig

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
            # 使用 QIcon 加载 ICO 以支持多分辨率
            icon = QIcon(icon_path)
            # 获取设备像素比
            pixel_ratio = self.devicePixelRatio()
            # 请求较大尺寸以获得更好质量
            icon_size = int(64 * pixel_ratio)
            pixmap = icon.pixmap(icon.actualSize(QSize(icon_size, icon_size)))
            if not pixmap.isNull():
                # 缩放到目标显示尺寸
                target_size = int(20 * pixel_ratio)
                scaled_pixmap = pixmap.scaled(
                    target_size, target_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                scaled_pixmap.setDevicePixelRatio(pixel_ratio)
                logo_label.setPixmap(scaled_pixmap)

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

    def _update_window_buttons_color(self, text_color):
        """更新窗口按钮颜色以适配主题

        Args:
            text_color: 文本颜色 (QColor)
        """
        title_bar = self.titleBar

        # 更新最小化按钮
        if title_bar.minBtn:
            title_bar.minBtn.setNormalColor(text_color)
            title_bar.minBtn.setHoverColor(text_color)
            title_bar.minBtn.setHoverBackgroundColor(get_close_button_hover_bg_color())
            title_bar.minBtn.setPressedColor(text_color)

        # 更新最大化按钮
        if title_bar.maxBtn:
            title_bar.maxBtn.setNormalColor(text_color)
            title_bar.maxBtn.setHoverColor(text_color)
            title_bar.maxBtn.setHoverBackgroundColor(get_close_button_hover_bg_color())
            title_bar.maxBtn.setPressedColor(text_color)

        # 更新关闭按钮
        if title_bar.closeBtn:
            title_bar.closeBtn.setNormalColor(text_color)
            title_bar.closeBtn.setHoverColor(get_close_button_hover_color())
            title_bar.closeBtn.setHoverBackgroundColor(get_close_button_hover_bg_color())
            title_bar.closeBtn.setPressedColor(get_close_button_pressed_color())

    def _update_styles(self):
        """更新样式以适配主题"""
        text_color = get_text_color()
        text_color_str = text_color.name()
        bg_color = get_dialog_bg_color()

        # 使用 QPalette 设置窗口背景色
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, bg_color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        bg_color_str = bg_color.name()

        # 设置样式表 - 窗口背景和 QLabel 文字颜色
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color_str};
            }}
            QLabel {{
                color: {text_color_str};
                background-color: transparent;
            }}
        """)

        # 更新标题标签颜色（如果存在）
        if hasattr(self, '_title_label') and self._title_label:
            self._title_label.setStyleSheet(
                f"color: {text_color_str}; font-size: 13px; font-weight: 500;"
            )

        # 更新窗口按钮颜色
        self._update_window_buttons_color(text_color)

    def closeEvent(self, event):
        """关闭事件：断开主题变化信号连接

        子类可以重写此方法，但应调用 super().closeEvent(event)
        以确保信号正确断开。
        """
        if hasattr(self, '_theme_connection'):
            try:
                qconfig.themeChangedFinished.disconnect(self._theme_connection)
            except (TypeError, RuntimeError):
                pass
            delattr(self, '_theme_connection')
        super().closeEvent(event)
