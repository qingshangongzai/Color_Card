from __future__ import annotations
# 标准库导入
from typing import Any

# 第三方库导入
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PrimaryPushButton, PushButton, ScrollArea, ScrollBarHandleDisplayMode, qconfig

# 项目模块导入
from utils import tr, load_icon_universal
from utils.theme_colors import get_text_color, get_secondary_text_color
from dialogs import BaseFramelessDialog


class UpdateAvailableDialog(BaseFramelessDialog):
    """新版本可用提示对话框

    当检测到有新版本时弹出，提供直接下载或跳转到发行页面的功能。
    """

    def __init__(self, parent=None, current_version="", latest_version="", download_url="", changelog=None):
        """初始化新版本提示对话框

        Args:
            parent: 父窗口对象
            current_version: 当前版本号
            latest_version: 最新版本号
            download_url: 下载链接
            changelog: 版本信息列表
        """
        super().__init__(parent)
        self.setWindowTitle(tr('dialogs.update.title'))
        self.setFixedSize(450, 500)
        self.current_version = current_version
        self.latest_version = latest_version
        self.download_url = download_url
        self.changelog = changelog

        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())

        # 设置界面
        self.setup_ui()

        # 设置标题栏和样式（基类提供）
        self._setup_title_bar()
        self._update_styles()

        # 监听主题变化
        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        # 样式准备好后允许显示
        self._enable_show()

    def _changelog_to_html(self, versions: list[dict[str, Any]]) -> str:
        """将版本信息列表转换为 HTML

        Args:
            versions: 版本信息列表，每个版本包含 version、date、changes

        Returns:
            str: HTML 格式的文本
        """
        if not versions:
            return ""

        text_color = get_text_color().name()
        secondary_color = get_secondary_text_color().name()
        html_lines = []

        for i, version_info in enumerate(versions):
            version = version_info.get("version", "")
            date = version_info.get("date", "")
            notes = version_info.get("notes", [])
            changes = version_info.get("changes", [])

            if i > 0:
                html_lines.append(f'<hr style="border: none; border-top: 1px solid rgba(128, 128, 128, 0.3); margin: 10px 0;">')

            html_lines.append(
                f'<h2 style="margin: 15px 0 10px 0; font-size: 18px; font-weight: bold; color: {text_color};">'
                f'{version}<small style="font-size: 10px; color: {secondary_color};"> ({date})</small></h2>'
            )

            if notes:
                html_lines.append(f'<div style="margin: 10px 0 5px 0; color: {text_color};"><b>通知</b></div>')
                for note in notes:
                    html_lines.append(
                        f'<div style="margin: 5px 0 5px 20px; color: {text_color};">• {note}</div>'
                    )

            for change in changes:
                category = change.get("category", "")
                items = change.get("items", [])

                html_lines.append(f'<div style="margin: 10px 0 5px 0; color: {text_color};"><b>{category}</b></div>')

                for item in items:
                    if isinstance(item, str):
                        html_lines.append(f'<div style="margin: 5px 0 5px 20px; color: {text_color};">• {item}</div>')
                    elif isinstance(item, dict):
                        title = item.get("title", "")
                        desc = item.get("desc", "")
                        html_lines.append(f'<div style="margin: 5px 0 0 10px; color: {text_color};">• <b>{title}</b></div>')
                        desc_lines = desc.split("<br>")
                        for line in desc_lines:
                            html_lines.append(f'<div style="margin: 2px 0 0 30px; color: {text_color};">{line}</div>')

        return ''.join(html_lines)

    def _update_styles(self):
        """更新样式以适配主题"""
        super()._update_styles()

        if hasattr(self, 'changelog_label') and self.changelog_label:
            text_color = get_text_color().name()
            self.changelog_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {text_color};
                    padding: 5px;
                }}
            """)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)

        # 提示文本
        info_label = QLabel(tr('dialogs.update.new_version'))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        # 版本信息
        version_label = QLabel(tr('dialogs.update.version_info', current=self.current_version, latest=self.latest_version))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        # 更新日志区域
        if self.changelog:
            scroll_area = ScrollArea()
            scroll_area.scrollDelagate.vScrollBar.setHandleDisplayMode(ScrollBarHandleDisplayMode.ON_HOVER)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMinimumHeight(300)
            scroll_area.setStyleSheet("""
                ScrollArea {
                    background-color: transparent;
                    border: none;
                }
                ScrollArea > QWidget > QWidget {
                    background-color: transparent;
                }
            """)

            corner_widget = QWidget()
            corner_widget.setStyleSheet("background: transparent;")
            scroll_area.setCornerWidget(corner_widget)

            html_content = self._changelog_to_html(self.changelog)

            self.changelog_label = QLabel()
            self.changelog_label.setTextFormat(Qt.TextFormat.RichText)
            self.changelog_label.setText(html_content)
            self.changelog_label.setWordWrap(True)
            self.changelog_label.setOpenExternalLinks(True)
            self.changelog_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            text_color = get_text_color().name()
            self.changelog_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {text_color};
                    padding: 5px;
                }}
            """)

            scroll_area.setWidget(self.changelog_label)
            layout.addWidget(scroll_area, stretch=1)

        layout.addStretch()

        # 按钮区域
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        buttons_layout.addStretch()

        release_button = PushButton(tr('dialogs.update.release_page'))
        release_button.setMinimumWidth(90)
        release_button.clicked.connect(self.open_release_page)
        buttons_layout.addWidget(release_button)

        download_button = PrimaryPushButton(tr('dialogs.update.download'))
        download_button.setMinimumWidth(90)
        download_button.clicked.connect(self.on_download_clicked)
        buttons_layout.addWidget(download_button)

        buttons_layout.addStretch()

        layout.addWidget(buttons_container)

    def on_download_clicked(self):
        """处理下载按钮点击"""
        if self.download_url:
            QDesktopServices.openUrl(QUrl(self.download_url))
        else:
            self.open_release_page()
        self.accept()

    def open_release_page(self):
        """打开 Gitee 发行版页面"""
        if self.latest_version:
            url = f"https://gitee.com/HxiaoStudio/Color_Card/releases/tag/{self.latest_version}"
        else:
            url = "https://gitee.com/HxiaoStudio/Color_Card/releases"
        QDesktopServices.openUrl(QUrl(url))
        self.accept()

    def closeEvent(self, event):
        """关闭事件"""
        super().closeEvent(event)
