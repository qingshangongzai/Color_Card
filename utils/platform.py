# 标准库导入
import ctypes
import ctypes.wintypes
import os
import sys


# 项目模块导入
from .icon import get_icon_path


# AllowSetForegroundWindow 常量
ASFW_ANY = -1  # 允许任何进程设置前台窗口

# SetWindowPos 常量
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

# SetWindowLongPtrW 常量
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

# macOS 原生窗口常量：ctypes 直接调用 libobjc，不引入 pyobjc 依赖
_LIBOBJC_PATH = '/usr/lib/libobjc.A.dylib'
# NSWindow.level：普通层级 0，NSFloatingWindowLevel 3
_NS_NORMAL_WINDOW_LEVEL = 0
_NS_FLOATING_WINDOW_LEVEL = 3
# NSWindowStyleMaskNonactivatingPanel：面板点击不触发应用的 Active 状态迁移
_NS_WINDOW_STYLE_MASK_NONACTIVATING_PANEL = 1 << 7

# LoadImageW 返回 HICON（64 位句柄），提前声明返回类型避免被 ctypes 默认的
# c_int 截断；仅在 Windows 下设置，保证跨平台 import 不失败
if os.name == 'nt':
    ctypes.windll.user32.LoadImageW.restype = ctypes.wintypes.HANDLE
    ctypes.windll.user32.SetWindowPos.restype = ctypes.wintypes.BOOL
    ctypes.windll.user32.SetWindowPos.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.wintypes.UINT,
    ]
    ctypes.windll.user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    ctypes.windll.user32.GetWindowLongPtrW.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.c_int,
    ]
    ctypes.windll.user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    ctypes.windll.user32.SetWindowLongPtrW.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.c_int,
        ctypes.c_ssize_t,
    ]


_libobjc: ctypes.CDLL | None = None
_libobjc_unavailable = False


def _get_libobjc() -> ctypes.CDLL | None:
    """懒加载 libobjc，并声明 sel_registerName 的签名

    Returns:
        ctypes.CDLL: 可用的 libobjc；加载失败时返回 None 并缓存失败标记
    """
    global _libobjc, _libobjc_unavailable
    if _libobjc is None and not _libobjc_unavailable:
        try:
            lib = ctypes.CDLL(_LIBOBJC_PATH)
        except OSError:
            _libobjc_unavailable = True
            return None
        lib.sel_registerName.restype = ctypes.c_void_p
        lib.sel_registerName.argtypes = [ctypes.c_char_p]
        _libobjc = lib
    return _libobjc


def _objc_send(restype, *argtypes):
    """按返回类型取 objc_msgSend 函数指针

    objc_msgSend 的调用约定随返回类型变化（void / 整型），必须按返回类型分别
    取函数指针，不能复用一个无类型指针。

    Args:
        restype: 返回类型
        *argtypes: 参数类型

    Returns:
        ctypes 函数指针；libobjc 不可用时返回 None
    """
    lib = _get_libobjc()
    if lib is None:
        return None
    return ctypes.CFUNCTYPE(restype, *argtypes)(('objc_msgSend', lib))


def _objc_sel(name: str) -> ctypes.c_void_p | None:
    """按方法名取 SEL

    Args:
        name: Objective-C 方法名，如 'setLevel:'

    Returns:
        SEL 指针；libobjc 不可用时返回 None
    """
    lib = _get_libobjc()
    if lib is None:
        return None
    return ctypes.c_void_p(lib.sel_registerName(name.encode()))


def _ns_window(window) -> int | None:
    """取 Qt 窗口对应的 NSWindow：winId → NSView → [view window]

    Args:
        window: PySide6 窗口对象

    Returns:
        int: NSWindow 指针；libobjc 不可用或取不到时返回 None
    """
    sel_window = _objc_sel('window')
    send_view_window = _objc_send(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    if sel_window is None or send_view_window is None:
        return None
    return send_view_window(ctypes.c_void_p(int(window.winId())), sel_window)


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


def set_window_topmost(window, topmost: bool) -> bool:
    """切换窗口置顶状态，不重建原生窗口

    Args:
        window: PySide6 窗口对象
        topmost: True 置顶，False 取消置顶

    Returns:
        bool: 切换成功返回 True；不支持的平台或调用失败返回 False
    """
    if sys.platform == 'darwin':
        try:
            ns_window = _ns_window(window)
            sel_set_level = _objc_sel('setLevel:')
            sel_level = _objc_sel('level')
            send_void = _objc_send(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)
            send_level = _objc_send(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)
            if (ns_window is None or sel_set_level is None or sel_level is None
                    or send_void is None or send_level is None):
                return False
            level = _NS_FLOATING_WINDOW_LEVEL if topmost else _NS_NORMAL_WINDOW_LEVEL
            send_void(ns_window, sel_set_level, level)
            # setLevel 无返回值，读回层级确认生效
            return send_level(ns_window, sel_level) == level
        except (AttributeError, OSError, RuntimeError):
            return False

    if os.name != 'nt':
        return False

    try:
        user32 = ctypes.windll.user32
        return bool(user32.SetWindowPos(
            ctypes.wintypes.HWND(int(window.winId())),
            ctypes.wintypes.HWND(HWND_TOPMOST if topmost else HWND_NOTOPMOST),
            0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE,
        ))
    except (AttributeError, OSError, RuntimeError):
        return False


def set_window_nonactivating(window) -> bool:
    """把窗口设为非激活面板，点击窗口不触发应用的 Active 状态迁移

    只改 NSWindow.styleMask、不重建原生窗口。已置位的直接返回，可重复调用；
    样式位可能重置 level，调用方须在其后重新应用层级。

    Args:
        window: PySide6 窗口对象

    Returns:
        bool: 样式位已生效返回 True；非 macOS 或调用失败返回 False
    """
    if sys.platform != 'darwin':
        return False

    try:
        ns_window = _ns_window(window)
        sel_style_mask = _objc_sel('styleMask')
        sel_set_style_mask = _objc_sel('setStyleMask:')
        send_mask = _objc_send(ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p)
        send_set_mask = _objc_send(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong
        )
        if (ns_window is None or sel_style_mask is None or sel_set_style_mask is None
                or send_mask is None or send_set_mask is None):
            return False
        style_mask = send_mask(ns_window, sel_style_mask)
        if style_mask & _NS_WINDOW_STYLE_MASK_NONACTIVATING_PANEL:
            return True
        send_set_mask(
            ns_window,
            sel_set_style_mask,
            style_mask | _NS_WINDOW_STYLE_MASK_NONACTIVATING_PANEL,
        )
        # setStyleMask 无返回值，读回样式位确认生效
        return bool(
            send_mask(ns_window, sel_style_mask)
            & _NS_WINDOW_STYLE_MASK_NONACTIVATING_PANEL
        )
    except (AttributeError, OSError, RuntimeError):
        return False


def order_front_regardless(window) -> bool:
    """把窗口前置到同层级窗口之上，不激活所属应用

    Args:
        window: PySide6 窗口对象

    Returns:
        bool: 前置成功返回 True；非 macOS 或调用失败返回 False
    """
    if sys.platform != 'darwin':
        return False

    try:
        ns_window = _ns_window(window)
        send_void = _objc_send(None, ctypes.c_void_p, ctypes.c_void_p)
        if ns_window is None or send_void is None:
            return False
        send_void(ns_window, _objc_sel('orderFrontRegardless'))
        return True
    except (AttributeError, OSError, RuntimeError):
        return False


def set_window_tool_style(window) -> bool:
    """给窗口加 WS_EX_TOOLWINDOW 与 WS_EX_NOACTIVATE 扩展样式

    WS_EX_TOOLWINDOW：不进任务栏与 Alt+Tab；WS_EX_NOACTIVATE：点击 / 拖动
    不抢前台，全屏应用不会被中断。只改扩展样式、不重建原生窗口，需在窗口
    获得原生句柄后调用；需要键盘输入的子控件由调用方在点击时显式激活窗口。

    Args:
        window: PySide6 窗口对象

    Returns:
        bool: 两个标志均已生效返回 True；非 Windows 或调用失败返回 False
    """
    if os.name != 'nt':
        return False

    try:
        user32 = ctypes.windll.user32
        hwnd = ctypes.wintypes.HWND(int(window.winId()))
        required = WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        if style & required == required:
            return True
        user32.SetWindowLongPtrW(
            hwnd, GWL_EXSTYLE, ctypes.c_ssize_t(style | required)
        )
        # SetWindowLongPtrW 返回旧样式，无法区分失败；改读回样式确认生效
        return bool(user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & required == required)
    except (AttributeError, OSError, RuntimeError):
        return False


def show_and_activate_window(window) -> bool:
    """还原或显示窗口，并将其前置激活

    Args:
        window: PySide6 窗口对象

    Returns:
        bool: Windows 强制前置是否成功；其他平台恒为 False
    """
    if window.isMinimized():
        window.showNormal()
    elif not window.isVisible():
        window.show()
    window.raise_()
    window.activateWindow()
    return force_window_to_front(window)
