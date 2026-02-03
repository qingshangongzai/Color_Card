"""图标工具模块 - 提供Windows任务栏图标显示支持

本模块提供以下功能：
1. 设置 AppUserModelID（必须在创建 QApplication 之前调用）
2. 加载应用程序图标（支持开发环境和打包后的环境）
3. 修复 Windows 任务栏图标显示
4. 窗口图标修复混入类

参考文档：状态栏图标显示参考文档.md
"""

import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtCore import Qt, QTimer, QObject, Signal


def set_app_user_model_id():
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
    except Exception:
        return False


def get_base_path():
    """获取应用程序基础路径
    
    支持开发环境和 PyInstaller 打包后的环境
    
    Returns:
        str: 应用程序基础路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    # 开发环境
    return os.path.dirname(os.path.abspath(__file__))


def get_icon_path():
    """获取图标文件路径
    
    Returns:
        str: 图标文件的完整路径，如果找不到则返回 None
    """
    base_path = get_base_path()
    
    # 可能的图标路径列表
    possible_paths = [
        os.path.join(base_path, 'logo', 'Color Card_logo.ico'),
        os.path.join(base_path, 'Color Card_logo.ico'),
        os.path.join(base_path, 'logo.ico'),
        os.path.join(base_path, 'logo', 'logo.ico'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def load_icon_universal():
    """统一的图标加载函数，适用于所有环境
    
    Returns:
        QIcon: 应用程序图标对象
    """
    icon_path = get_icon_path()
    
    if icon_path:
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon
    
    # 如果找不到图标，创建后备图标
    return create_fallback_icon()


def create_fallback_icon():
    """创建后备图标（当找不到图标文件时使用）
    
    Returns:
        QIcon: 后备图标对象
    """
    try:
        # 创建一个简单的蓝色图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#0078d4"))
        
        painter = QPainter(pixmap)
        painter.setPen(QColor('white'))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "CC")
        painter.end()
        
        return QIcon(pixmap)
    except Exception:
        return QIcon()


# 全局变量：跟踪每个窗口的图标修复状态
_TASKBAR_ICON_FIXED_WINDOWS = {}


def fix_windows_taskbar_icon_for_window(window):
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
        
    except Exception:
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._icon_fixed = False
        self._fix_timer = None
    
    def setup_icon_fixing(self, delay_ms=100):
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
    
    def _fix_icon_safe(self):
        """安全修复任务栏图标"""
        try:
            if self._icon_fixed:
                return True
            
            success = fix_windows_taskbar_icon_for_window(self)
            self._icon_fixed = True
            self.icon_fixed.emit(success)
            return success
        except Exception:
            self.icon_fixed.emit(False)
            return False
    
    def fix_taskbar_icon(self):
        """修复任务栏图标 - 兼容旧接口"""
        return self._fix_icon_safe()
