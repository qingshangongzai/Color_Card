"""安装器无边框对话框基座

收编自 dialogs/base_frameless_dialog.py 并裁剪：去掉组件库主题信号与
theme_colors 依赖，改由 mini_style 提供静态色值。原文件保持不动。
修改标题栏 / 淡入逻辑时须同步 dialogs/base_frameless_dialog.py。
"""

# 第三方库导入
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QLabel
from qframelesswindow import FramelessDialog

# 项目模块导入
from installer.wizard.mini_style import build_qss, detect_scheme, resolve_tokens
from utils.icon import get_icon_path


class BaseFramelessDialog(FramelessDialog):
    """无边框对话框基座

    提供 Fluent 风格标题栏与迷你层静态样式。子类依次调用
    _setup_title_bar()、_update_styles() 即可，不再监听主题变化。
    """

    def __init__(self, parent=None):
        """初始化对话框，初始透明避免样式就绪前闪烁"""
        super().__init__(parent)
        self.setWindowOpacity(0.0)
        self._fade_animation = None

    def _enable_show(self):
        """样式就绪后延迟一帧启动淡入"""
        QTimer.singleShot(0, self._start_fade_in)

    def _start_fade_in(self):
        """启动 120ms 淡入动画"""
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(120)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_animation.start()

    def _setup_title_bar(self):
        """在 FramelessDialog 内置标题栏中插入 Logo 与标题"""
        title_bar = self.titleBar
        h_layout = title_bar.layout()
        if not h_layout:
            return

        text_color_str = resolve_tokens()['window_fg']

        left_spacer = QLabel(title_bar)
        left_spacer.setFixedWidth(10)

        icon_path = get_icon_path()
        logo_label = None
        if icon_path:
            logo_label = QLabel(title_bar)
            icon = QIcon(icon_path)
            pixel_ratio = self.devicePixelRatio()
            icon_size = int(64 * pixel_ratio)
            pixmap = icon.pixmap(icon.actualSize(QSize(icon_size, icon_size)))
            if not pixmap.isNull():
                target_size = int(20 * pixel_ratio)
                scaled_pixmap = pixmap.scaled(
                    target_size, target_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                scaled_pixmap.setDevicePixelRatio(pixel_ratio)
                logo_label.setPixmap(scaled_pixmap)

        spacer_label = QLabel(title_bar)
        spacer_label.setFixedWidth(8)

        title_label = QLabel(self.windowTitle(), title_bar)
        title_label.setStyleSheet(
            f"color: {text_color_str}; font-size: 13px; font-weight: 500;"
        )

        for widget in [title_label, spacer_label, logo_label, left_spacer]:
            if widget:
                h_layout.insertWidget(0, widget)
                h_layout.setAlignment(widget, Qt.AlignmentFlag.AlignVCenter)

        self._title_label = title_label

    def _update_window_buttons_color(self, text_color: QColor):
        """按主题色更新标题栏窗口按钮三色

        Args:
            text_color: 文本颜色
        """
        tokens = resolve_tokens()
        title_bar = self.titleBar

        for button in (title_bar.minBtn, title_bar.maxBtn):
            if button:
                button.setNormalColor(text_color)
                button.setHoverColor(text_color)
                button.setHoverBackgroundColor(QColor(tokens['close_hover_bg']))
                button.setPressedColor(text_color)

        if title_bar.closeBtn:
            title_bar.closeBtn.setNormalColor(text_color)
            title_bar.closeBtn.setHoverColor(QColor(tokens['close_hover_fg']))
            title_bar.closeBtn.setHoverBackgroundColor(
                QColor(tokens['close_hover_bg'])
            )
            title_bar.closeBtn.setPressedColor(QColor(tokens['close_hover_fg']))

    def _update_styles(self):
        """应用迷你层完整 QSS，并同步调色板与标题栏按钮颜色"""
        scheme = detect_scheme()
        tokens = resolve_tokens(scheme)

        # palette + autoFill 作为兜底：QDialog 规则的背景由 QSS 提供，二者同色
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(tokens['window_bg']))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.setStyleSheet(build_qss(scheme))

        if hasattr(self, '_title_label') and self._title_label:
            self._title_label.setStyleSheet(
                f"color: {tokens['window_fg']}; font-size: 13px; font-weight: 500;"
            )

        self._update_window_buttons_color(QColor(tokens['window_fg']))
