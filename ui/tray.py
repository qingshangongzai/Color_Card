"""Windows / macOS 托盘图标与右键菜单"""

# 标准库导入
import os
import sys

# 第三方库导入
from PySide6.QtCore import QObject
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon
from qfluentwidgets import Action, FluentIcon, SystemTrayMenu

# 项目模块导入
from core import get_logger
from dialogs import AboutDialog
from utils import get_base_path, load_icon_universal, tr
from utils.platform import show_and_activate_window

logger = get_logger("tray")


class TrayIcon(QObject):
    """托盘图标：持有 QSystemTrayIcon 与右键菜单"""

    def __init__(self, window):
        super().__init__()
        self._window = window

        self._tray = QSystemTrayIcon(_load_tray_icon(), self)
        self._menu = SystemTrayMenu()

        self._show_action = Action(FluentIcon.HOME, "", self)
        self._show_action.triggered.connect(self._show_main_window)
        self._menu.addAction(self._show_action)

        self._settings_action = Action(FluentIcon.SETTING, "", self)
        self._settings_action.triggered.connect(self._open_settings)
        self._menu.addAction(self._settings_action)

        self._menu.addSeparator()

        self._about_action = Action(FluentIcon.INFO, "", self)
        self._about_action.triggered.connect(self._show_about)
        self._menu.addAction(self._about_action)

        self._exit_action = Action(FluentIcon.CLOSE, "", self)
        self._exit_action.triggered.connect(self._quit_app)
        self._menu.addAction(self._exit_action)

        # 缺任一环节托盘都不可用：不挂菜单右键无响应，不写 tooltip 无提示，不 show 图标不出现
        self._tray.setContextMenu(self._menu)
        self.update_texts()
        self._tray.show()

        # mac 单击即弹菜单（系统行为），恢复入口只用菜单项与 Dock 图标，
        # 接 activated 会与菜单弹出冲突，故仅 Windows 连接
        if sys.platform == 'win32':
            self._tray.activated.connect(self._on_activated)

    def update_texts(self) -> None:
        """刷新菜单文案与托盘提示（语言切换后调用）"""
        self._tray.setToolTip(tr('tray.tooltip'))
        self._show_action.setText(tr('tray.show_window'))
        self._settings_action.setText(tr('tray.settings'))
        self._about_action.setText(tr('tray.about'))
        self._exit_action.setText(tr('tray.exit'))

    def hide(self) -> None:
        """隐藏托盘图标（退出前调用）"""
        self._tray.hide()

    def _on_activated(self, reason):
        """托盘图标激活：单击恢复主窗口"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_main_window()

    def _show_main_window(self):
        """显示并前置主窗口"""
        show_and_activate_window(self._window)

    def _open_settings(self):
        """打开设置页"""
        self._window.show_settings_page()

    def _show_about(self):
        """显示关于对话框"""
        self._show_main_window()
        dialog = AboutDialog(self._window)
        dialog.exec()
        dialog.deleteLater()

    def _quit_app(self):
        """请求退出：走 closeEvent 的退出链路，确保保存配置并清理线程"""
        self._window.request_quit()


def _load_tray_icon() -> QIcon:
    """加载托盘图标：mac 用模板图，Windows 复用应用 ICO

    Returns:
        QIcon: 托盘图标；mac 模板图缺失或无法解码时回退通用图标
    """
    if sys.platform == 'darwin':
        icon_path = os.path.join(get_base_path(), 'logo', 'tray_mac.png')
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            # 模板图只取 alpha 通道，由系统按菜单栏明暗着色；不设置会按彩色图渲染
            if not icon.isNull():
                icon.setIsMask(True)
                return icon
        # 回退彩色 ICO 在菜单栏会显示为彩色或发虚，记日志便于定位产物漏带/损坏
        logger.warning(f"mac 托盘模板图缺失或无法解码，回退通用图标: {icon_path}")
    return load_icon_universal()


def create_tray(window) -> TrayIcon | None:
    """创建托盘图标

    Args:
        window: 主窗口实例

    Returns:
        TrayIcon | None: Windows / macOS 且系统托盘可用时返回托盘对象，否则返回 None
    """
    if sys.platform not in ('win32', 'darwin'):
        return None
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    return TrayIcon(window)
