from __future__ import annotations
# 标准库导入
import ctypes
import ctypes.wintypes
import os


# 项目模块导入
from .icon import get_icon_path


# AllowSetForegroundWindow 常量
ASFW_ANY = -1  # 允许任何进程设置前台窗口

# LoadImageW 返回 HICON（64 位句柄），提前声明返回类型避免被 ctypes 默认的
# c_int 截断；仅在 Windows 下设置，保证跨平台 import 不失败
if os.name == 'nt':
    ctypes.windll.user32.LoadImageW.restype = ctypes.wintypes.HANDLE


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
            # 注意：不能使用 cx=0, cy=0（按实际大小加载）！
            # 对多帧 ICO，LoadImageW 会加载目录中的第一帧（通常是最小的
            # 16x16 帧），任务栏将其放大显示会模糊。
            # 这里显式指定系统大图标尺寸（100% DPI 为 32x32，150% 为 48x48），
            # 让 LoadImageW 选中 ICO 中对应的原生帧。
            cx_icon = user32.GetSystemMetrics(11)  # SM_CXICON
            cy_icon = user32.GetSystemMetrics(12)  # SM_CYICON

            # 大图标：任务栏使用（尺寸随系统 DPI 变化）
            h_icon_big = user32.LoadImageW(
                None, icon_path,
                1,  # IMAGE_ICON
                cx_icon, cy_icon,  # 按系统图标尺寸加载，避免选中最小帧
                0x00000010  # LR_LOADFROMFILE
            )

            # 小图标：窗口标题栏使用（16x16）
            h_icon_small = user32.LoadImageW(
                None, icon_path,
                1,  # IMAGE_ICON
                16, 16,
                0x00000010  # LR_LOADFROMFILE
            )
        else:
            # PNG 兜底分支（实际不可达：get_icon_path() 只返回 .ico）
            # 注意：bits() 返回的是像素缓冲区指针而非 HICON，该分支设置的
            # 图标实际不会生效，保留仅为兼容历史行为。
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                h_icon_big = pixmap.toImage().bits()
                h_icon_small = h_icon_big
            else:
                return False

        if h_icon_big or h_icon_small:
            # 设置图标（大图标和小图标分别使用合适的尺寸）
            if h_icon_big:
                user32.SendMessageW(hwnd, 0x0080, 1, h_icon_big)  # WM_SETICON, ICON_BIG
            if h_icon_small:
                user32.SendMessageW(hwnd, 0x0080, 0, h_icon_small)  # WM_SETICON, ICON_SMALL

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
