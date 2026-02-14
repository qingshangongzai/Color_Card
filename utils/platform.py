# 标准库导入
import ctypes
import os
import sys
from typing import Dict, Optional

# 第三方库导入
from PySide6.QtCore import QObject, Qt, QTimer, Signal

# 项目模块导入
from .icon import get_icon_path


# Windows DWM API 常量
DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def is_windows_10() -> bool:
    """检测是否为 Windows 10 系统

    Returns:
        bool: 是 Windows 10 返回 True，否则返回 False（包括 Win11 或非 Windows 系统）
    """
    if sys.platform != "win32":
        return False

    try:
        # 使用 Windows 版本检测
        # Windows 10: major=10, minor=0, build < 22000
        # Windows 11: major=10, minor=0, build >= 22000
        version = sys.getwindowsversion()
        if version.major == 10 and version.minor == 0:
            # build 22000 是 Windows 11 的第一个版本
            return version.build < 22000
        return False
    except Exception:
        return False


def set_window_title_bar_theme(window, is_dark=False):
    """为窗口设置标题栏主题（Windows 10+ 深色/浅色模式）

    通过 Windows DWM (Desktop Window Manager) API 设置窗口标题栏的沉浸式深色模式。
    仅支持 Windows 10 版本 2004 (Build 19041) 及以上，Windows 11 完全支持。

    Args:
        window: PySide6 窗口对象（QMainWindow 或 QDialog）
        is_dark: 是否使用深色模式，True 为深色，False 为浅色

    Returns:
        bool: 设置成功返回 True，失败返回 False
    """
    try:
        # 仅 Windows 平台支持
        if sys.platform != "win32":
            return False

        # 窗口有效性检查
        if not window:
            return False

        if hasattr(window, 'isValid') and callable(window.isValid):
            if not window.isValid():
                return False

        if not hasattr(window, 'windowHandle'):
            return False

        window_handle = window.windowHandle()
        if not window_handle:
            return False

        if hasattr(window_handle, 'isValid') and callable(window_handle.isValid):
            if not window_handle.isValid():
                return False

        # 获取窗口句柄
        hwnd = int(window_handle.winId())
        value = ctypes.c_int(1 if is_dark else 0)

        # 调用 DWM API 设置窗口标题栏主题
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )

        return result == 0

    except RuntimeError as e:
        if "wrapped C/C++ object" in str(e) and "has been deleted" in str(e):
            # 尝试设置已删除窗口的标题栏主题，静默跳过
            return False
        else:
            return False
    except Exception:
        return False


def set_app_user_model_id() -> bool:
    """设置 AppUserModelID - 必须在创建 QApplication 之前调用

    Windows 使用 AppUserModelID 来识别和分组任务栏上的应用程序。
    如果不设置，Windows 会将 Python 解释器作为默认分组，导致图标显示异常。

    Returns:
        bool: 设置成功返回 True，失败返回 False
    """
    if os.name != 'nt':  # 仅 Windows 需要
        return False

    try:
        # 格式：CompanyName.AppName.Version
        app_id = 'HXiaoStudio.ColorCard.1.0.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except (AttributeError, OSError):
        return False


# 全局变量：跟踪每个窗口的图标修复状态
_TASKBAR_ICON_FIXED_WINDOWS: Dict[int, bool] = {}


def fix_windows_taskbar_icon_for_window(window) -> bool:
    """为特定窗口修复 Windows 任务栏图标

    Args:
        window: PySide6 窗口对象 (QMainWindow 或 QDialog)

    Returns:
        bool: 修复成功返回 True，失败返回 False
    """
    if os.name != 'nt':
        return False

    # 使用窗口对象的 id 作为键，为每个窗口单独跟踪修复状态
    window_id = id(window)
    global _TASKBAR_ICON_FIXED_WINDOWS

    # 检查此窗口是否已经修复过
    if window_id in _TASKBAR_ICON_FIXED_WINDOWS and _TASKBAR_ICON_FIXED_WINDOWS[window_id]:
        return False

    try:
        # 确保窗口已经显示
        if not window.isVisible():
            window.show()
        window.raise_()
        window.activateWindow()

        # 使用 Qt 方法获取窗口句柄
        hwnd = int(window.winId())

        # 获取图标路径
        icon_path = get_icon_path()

        if not icon_path:
            return False

        # 使用 ctypes 设置图标
        user32 = ctypes.windll.user32

        # 加载图标
        if icon_path.lower().endswith('.ico'):
            h_icon = user32.LoadImageW(
                None, icon_path,
                1,  # IMAGE_ICON
                0, 0,  # 使用实际大小
                0x00000010  # LR_LOADFROMFILE
            )
        else:
            # 对于 PNG 等格式，需要先加载为位图
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                h_icon = pixmap.toImage().bits()
            else:
                return False

        if h_icon:
            # 设置图标（大图标和小图标）
            user32.SendMessageW(hwnd, 0x0080, 1, h_icon)  # WM_SETICON, ICON_BIG
            user32.SendMessageW(hwnd, 0x0080, 0, h_icon)  # WM_SETICON, ICON_SMALL

            # 强制刷新任务栏
            user32.UpdateWindow(hwnd)

            # 标记此窗口已修复
            _TASKBAR_ICON_FIXED_WINDOWS[window_id] = True
            return True

        return False

    except (AttributeError, OSError, RuntimeError):
        return False


class WindowIconMixin(QObject):
    """窗口图标修复混入类，提供统一的任务栏图标修复功能

    使用示例：
        class MyWindow(QMainWindow, WindowIconMixin):
            def __init__(self):
                super().__init__()
                # ... 其他初始化代码 ...

            def showEvent(self, event):
                super().showEvent(event)
                self.setup_icon_fixing()
    """

    icon_fixed = Signal(bool)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._icon_fixed: bool = False
        self._fix_timer: Optional[QTimer] = None

    def setup_icon_fixing(self, delay_ms: int = 100) -> None:
        """设置图标修复，在窗口显示后调用

        Args:
            delay_ms: 延迟时间（毫秒），默认 100ms
        """
        if self._icon_fixed:
            return

        if os.name == 'nt':
            self._fix_timer = QTimer()
            self._fix_timer.setSingleShot(True)
            self._fix_timer.timeout.connect(self._fix_icon_safe)
            self._fix_timer.start(delay_ms)

    def _fix_icon_safe(self) -> bool:
        """安全修复任务栏图标

        Returns:
            bool: 修复成功返回 True，失败返回 False
        """
        try:
            if self._icon_fixed:
                return True

            success = fix_windows_taskbar_icon_for_window(self)
            self._icon_fixed = True
            self.icon_fixed.emit(success)
            return success
        except (AttributeError, OSError, RuntimeError):
            self.icon_fixed.emit(False)
            return False

    def fix_taskbar_icon(self) -> bool:
        """修复任务栏图标 - 兼容旧接口

        Returns:
            bool: 修复成功返回 True，失败返回 False
        """
        return self._fix_icon_safe()
