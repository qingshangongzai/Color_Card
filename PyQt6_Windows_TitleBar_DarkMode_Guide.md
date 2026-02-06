# PyQt6 Windows 标题栏深色模式切换指南

本文档介绍如何在 PyQt6 项目中实现 Windows 10/11 原生标题栏的深色/浅色模式切换。

## 目录

- [实现原理](#实现原理)
- [核心代码](#核心代码)
- [使用方法](#使用方法)
- [完整示例](#完整示例)
- [注意事项](#注意事项)

## 实现原理

通过 Windows DWM (Desktop Window Manager) API 设置窗口标题栏的沉浸式深色模式：

- 使用 `DwmSetWindowAttribute` 函数
- 属性常量 `DWMWA_USE_IMMERSIVE_DARK_MODE = 20`
- 值 `1` 表示深色模式，`0` 表示浅色模式

## 核心代码

### 1. 设置单个窗口标题栏主题

```python
import sys
import ctypes
from PyQt6.QtWidgets import QMainWindow, QDialog

# Windows DWM API 常量
DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def set_window_title_bar_theme(window, is_dark=False):
    """为窗口设置标题栏主题（Windows 10+ 深色/浅色模式）

    Args:
        window: PyQt6 窗口对象（QMainWindow 或 QDialog）
        is_dark: 是否使用深色模式，True 为深色，False 为浅色

    Returns:
        bool: 设置成功返回 True，失败返回 False
    """
    try:
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
            print("[DEBUG] 尝试设置已删除窗口的标题栏主题，跳过")
            return False
        else:
            print(f"[DEBUG] 设置窗口标题栏主题失败: {e}")
            return False
    except Exception as e:
        print(f"[DEBUG] 设置窗口标题栏主题失败: {e}")
        return False
```

### 2. 获取系统主题模式

```python
import sys


def get_system_theme_mode():
    """获取系统主题模式

    Returns:
        str: 系统主题模式，"light" 或 "dark"
    """
    try:
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if value == 1 else "dark"
            except Exception:
                return "light"
        # 其他平台默认浅色主题
        return "light"
    except Exception:
        return "light"
```

### 3. Mixin 类（推荐用法）

```python
import weakref
from PyQt6.QtCore import QTimer


class TitleBarThemeMixin:
    """标题栏主题 Mixin 类

    为窗口提供自动标题栏主题切换功能。
    使用方式：继承此类，并在 __init__ 中调用 register_for_theme_updates()
    """

    def register_for_theme_updates(self):
        """注册窗口以接收主题更新"""
        style_helper = UnifiedStyleHelper.get_instance()
        style_helper.register_title_bar_theme_callback(self)

        # 立即应用当前主题
        self._apply_title_bar_theme()

    def _apply_title_bar_theme(self):
        """应用当前主题到标题栏"""
        style_helper = UnifiedStyleHelper.get_instance()

        is_dark = style_helper.theme_mode == "dark"
        if style_helper.theme_mode == "system":
            is_dark = get_system_theme_mode() == "dark"

        set_window_title_bar_theme(self, is_dark)


class UnifiedStyleHelper:
    """统一样式助手（简化版）"""

    _instance = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = UnifiedStyleHelper()
        return cls._instance

    def __init__(self):
        self.theme_mode = "light"  # "light", "dark", "system"
        self._title_bar_theme_windows = []

    def register_title_bar_theme_callback(self, window):
        """注册标题栏主题更新回调"""
        window_ref = weakref.ref(window)
        if window_ref not in self._title_bar_theme_windows:
            self._title_bar_theme_windows.append(window_ref)

    def unregister_title_bar_theme_callback(self, window):
        """注销标题栏主题更新回调"""
        for window_ref in self._title_bar_theme_windows:
            if window_ref() is window:
                self._title_bar_theme_windows.remove(window_ref)
                break

    def set_theme(self, theme_mode):
        """设置主题并通知所有窗口"""
        self.theme_mode = theme_mode
        self._notify_title_bar_theme_changed()

    def _notify_title_bar_theme_changed(self):
        """通知所有注册的窗口更新标题栏主题"""
        def batch_update():
            is_dark = self.theme_mode == "dark"
            if self.theme_mode == "system":
                is_dark = get_system_theme_mode() == "dark"

            # 清理已销毁的窗口引用
            valid_windows = []
            for window_ref in self._title_bar_theme_windows:
                window = window_ref()
                if window is not None:
                    valid_windows.append(window_ref)

            self._title_bar_theme_windows = valid_windows

            # 更新所有窗口
            for window_ref in self._title_bar_theme_windows:
                window = window_ref()
                if window is not None:
                    try:
                        set_window_title_bar_theme(window, is_dark)
                    except (OSError, ValueError) as e:
                        print(f"[DEBUG] 更新窗口标题栏失败: {e}")

        QTimer.singleShot(0, batch_update)
```

## 使用方法

### 方式一：使用 Mixin 类（推荐）

```python
from PyQt6.QtWidgets import QMainWindow, QApplication


class MainWindow(QMainWindow, TitleBarThemeMixin):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("深色模式示例")
        self.resize(800, 600)

        # 注册主题更新
        self.register_for_theme_updates()


# 切换主题时所有注册窗口自动更新
def switch_theme(theme_mode):
    style_helper = UnifiedStyleHelper.get_instance()
    style_helper.set_theme(theme_mode)  # "light", "dark", "system"
```

### 方式二：手动设置

```python
from PyQt6.QtWidgets import QMainWindow, QApplication


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("手动设置示例")
        self.resize(800, 600)

        # 手动设置深色标题栏
        set_window_title_bar_theme(self, is_dark=True)


# 运行时切换
def toggle_title_bar(window, is_dark):
    set_window_title_bar_theme(window, is_dark)
```

## 完整示例

```python
import sys
import ctypes
import weakref
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, QTimer


# =============================================================================
# 核心功能
# =============================================================================

DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def set_window_title_bar_theme(window, is_dark=False):
    """设置窗口标题栏主题"""
    try:
        if sys.platform != "win32":
            return False

        if not window or not hasattr(window, 'windowHandle'):
            return False

        window_handle = window.windowHandle()
        if not window_handle:
            return False

        hwnd = int(window_handle.winId())
        value = ctypes.c_int(1 if is_dark else 0)

        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
        return result == 0
    except Exception as e:
        print(f"设置标题栏主题失败: {e}")
        return False


def get_system_theme_mode():
    """获取系统主题模式"""
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        return "light"
    except Exception:
        return "light"


# =============================================================================
# 主题管理器
# =============================================================================

class ThemeManager:
    """主题管理器（单例）"""

    _instance = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = ThemeManager()
        return cls._instance

    def __init__(self):
        self.theme_mode = "system"
        self._windows = []

    def register_window(self, window):
        """注册窗口"""
        window_ref = weakref.ref(window)
        if window_ref not in self._windows:
            self._windows.append(window_ref)
            # 立即应用当前主题
            self._apply_to_window(window)

    def set_theme(self, mode):
        """设置主题"""
        self.theme_mode = mode
        self._notify_all()

    def _apply_to_window(self, window):
        """应用主题到单个窗口"""
        is_dark = self.theme_mode == "dark"
        if self.theme_mode == "system":
            is_dark = get_system_theme_mode() == "dark"
        set_window_title_bar_theme(window, is_dark)

    def _notify_all(self):
        """通知所有窗口"""
        def update_all():
            is_dark = self.theme_mode == "dark"
            if self.theme_mode == "system":
                is_dark = get_system_theme_mode() == "dark"

            # 清理无效引用并更新
            valid_windows = []
            for window_ref in self._windows:
                window = window_ref()
                if window is not None:
                    valid_windows.append(window_ref)
                    set_window_title_bar_theme(window, is_dark)

            self._windows = valid_windows

        QTimer.singleShot(0, update_all)


# =============================================================================
# 主窗口
# =============================================================================

class DemoWindow(QMainWindow):
    """演示窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Windows 标题栏深色模式示例")
        self.resize(600, 400)

        # 注册到主题管理器
        ThemeManager.get_instance().register_window(self)

        # 创建界面
        self._setup_ui()

    def _setup_ui(self):
        """设置界面"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        title = QLabel("Windows 标题栏深色模式切换")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 说明
        desc = QLabel("点击下方按钮切换标题栏颜色")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(30)

        # 按钮区域
        btn_layout = QHBoxLayout()

        btn_light = QPushButton("浅色模式")
        btn_light.clicked.connect(lambda: self._switch_theme("light"))
        btn_layout.addWidget(btn_light)

        btn_dark = QPushButton("深色模式")
        btn_dark.clicked.connect(lambda: self._switch_theme("dark"))
        btn_layout.addWidget(btn_dark)

        btn_system = QPushButton("跟随系统")
        btn_system.clicked.connect(lambda: self._switch_theme("system"))
        btn_layout.addWidget(btn_system)

        layout.addLayout(btn_layout)

        # 当前状态
        self.status_label = QLabel("当前: 系统主题")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def _switch_theme(self, mode):
        """切换主题"""
        ThemeManager.get_instance().set_theme(mode)
        mode_text = {"light": "浅色", "dark": "深色", "system": "系统"}
        self.status_label.setText(f"当前: {mode_text.get(mode, mode)}主题")


# =============================================================================
# 运行
# =============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = DemoWindow()
    window.show()

    sys.exit(app.exec())
```

## 注意事项

### 1. 系统要求

- **仅支持 Windows 10 版本 2004 (Build 19041) 及以上**
- Windows 11 完全支持
- 非 Windows 系统会静默跳过，不影响程序运行

### 2. 窗口要求

- 窗口必须已经创建（有有效的 `windowHandle`）
- 建议在 `show()` 之后或 `__init__` 末尾调用
- 对于对话框，确保在显示后设置

### 3. 常见问题

| 问题 | 解决方案 |
|------|----------|
| 标题栏颜色未改变 | 检查 Windows 版本是否支持（需 19041+） |
| 切换后部分窗口未更新 | 确保窗口已注册到主题管理器 |
| 程序崩溃 | 检查窗口是否已被销毁，使用 `weakref` 避免悬空引用 |
| 非 Windows 平台报错 | 添加 `sys.platform == "win32"` 检查 |

### 4. 最佳实践

1. **使用单例模式管理主题状态**，避免多个管理器冲突
2. **使用 `weakref`** 引用窗口，防止内存泄漏
3. **使用 `QTimer.singleShot`** 批量更新，避免界面卡顿
4. **添加异常处理**，特别是针对窗口已销毁的情况
5. **提供跟随系统选项**，让应用自动适应系统主题

---

**参考来源**: BetterGI StellTrack 项目实现
