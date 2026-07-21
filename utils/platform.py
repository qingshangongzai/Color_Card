from __future__ import annotations
# 标准库导入
import ctypes
import os


# 项目模块导入
from .icon import get_icon_path


# AllowSetForegroundWindow 常量
ASFW_ANY = -1  # 允许任何进程设置前台窗口


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
_TASKBAR_ICON_FIXED_WINDOWS: dict[int, bool] = {}


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
        # 注意：全屏窗口的 isVisible 可能返回 False，需要特殊处理
        if not window.isVisible() and not window.isFullScreen():
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


def force_window_to_front(window) -> bool:
    """强制将窗口带到最前并激活"""
    if os.name != 'nt':
        return False

    try:
        hwnd = int(window.winId())
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.AllowSetForegroundWindow(ASFW_ANY)
        user32.SwitchToThisWindow(hwnd, True)

        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
        cur_thread = kernel32.GetCurrentThreadId()

        if fg_thread != cur_thread:
            user32.AttachThreadInput(fg_thread, cur_thread, True)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(fg_thread, cur_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)

        window.raise_()
        window.activateWindow()
        return True

    except (AttributeError, OSError, RuntimeError):
        return False
