from __future__ import annotations
# 标准库导入
from typing import Any

# 第三方库导入
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from qfluentwidgets import setThemeColor

# 项目模块导入
from dialogs.base_frameless_dialog import BaseFramelessDialog
from installer.wizard.base_page import BasePage
from installer.core.permission_checker import run_as_admin
from utils.icon import load_icon_universal
from utils.platform import fix_windows_taskbar_icon_for_window


class InstallWizard(BaseFramelessDialog):
    """安装向导主窗口"""

    PROGRESS_PAGE_INDEX = 2  # 进度页面索引

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("取色卡安装向导")
        self.setFixedSize(520, 380)

        setThemeColor('#0078d4')

        app_icon = load_icon_universal()
        self.setWindowIcon(app_icon)

        self._pages: list[BasePage] = []
        self._current_page_index = 0

        self._config: dict[str, Any] = {
            'install_path': '',
            'create_desktop_shortcut': True,
            'create_start_menu': True,
            'run_after_install': False,
        }

        self._setup_title_bar()
        self.setup_ui()
        self._update_styles()
        self._enable_show()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 40, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

    def add_page(self, page: BasePage):
        page.set_wizard(self)
        page.set_config(self._config)
        page.setup_ui()
        self._pages.append(page)
        self._stack.addWidget(page)

        page.next_requested.connect(self.next_page)
        page.back_requested.connect(self.prev_page)
        page.close_requested.connect(self.close)

        # 连接提权请求信号
        if hasattr(page, 'elevation_requested'):
            page.elevation_requested.connect(self._on_elevation_requested)

    def _on_elevation_requested(self, install_path: str, create_desktop: bool, create_start_menu: bool):
        """处理提权请求

        Args:
            install_path: 用户选择的安装路径
            create_desktop: 是否创建桌面快捷方式
            create_start_menu: 是否创建开始菜单快捷方式
        """
        run_as_admin(install_path, create_desktop, create_start_menu)

    def set_preset_config(self, config: dict[str, Any]):
        """设置预设配置

        Args:
            config: 预设配置
        """
        self._config.update(config)

    def skip_to_progress_page(self):
        """直接跳转到进度页面"""
        if self.PROGRESS_PAGE_INDEX < len(self._pages):
            self._current_page_index = self.PROGRESS_PAGE_INDEX
            progress_page = self._pages[self.PROGRESS_PAGE_INDEX]
            self._stack.setCurrentWidget(progress_page)
            progress_page.on_enter()

    def next_page(self):
        if self._current_page_index < len(self._pages) - 1:
            current_page = self._pages[self._current_page_index]
            if not current_page.can_next():
                return

            self._current_page_index += 1
            next_page = self._pages[self._current_page_index]
            self._stack.setCurrentWidget(next_page)
            next_page.on_enter()

    def prev_page(self):
        if self._current_page_index > 0:
            current_page = self._pages[self._current_page_index]
            if not current_page.can_back():
                return

            self._current_page_index -= 1
            prev_page = self._pages[self._current_page_index]
            self._stack.setCurrentWidget(prev_page)
            prev_page.on_enter()

    def get_config(self) -> dict[str, Any]:
        return self._config.copy()

    def _update_styles(self):
        super()._update_styles()
        for page in self._pages:
            page._update_styles()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(self))
