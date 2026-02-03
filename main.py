import sys
from io import StringIO

# ========== 第 1 步：在导入 PySide6 之前设置 AppUserModelID ==========
# 这必须在创建 QApplication 之前调用！
import os
import ctypes

def set_app_user_model_id():
    """设置 AppUserModelID"""
    if os.name != 'nt':
        return False
    
    try:
        # 格式：CompanyName.AppName.Version
        app_id = 'HXiaoStudio.ColorCard.1.0.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except Exception:
        return False

# 立即调用（在导入 PySide6 之前）
set_app_user_model_id()

# 临时重定向 stdout 以屏蔽 QFluentWidgets 的推广提示
_old_stdout = sys.stdout
sys.stdout = StringIO()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from qfluentwidgets import FluentWindow, setTheme, Theme, setThemeColor

# 恢复 stdout
sys.stdout = _old_stdout

from widgets import MainWindow
from icon_utils import load_icon_universal, fix_windows_taskbar_icon_for_window


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # 设置应用程序图标（重要！）
    app_icon = load_icon_universal()
    app.setWindowIcon(app_icon)

    setTheme(Theme.AUTO)
    setThemeColor('#0078d4')

    window = MainWindow()
    window.show()
    
    # 修复任务栏图标（在窗口显示后调用）
    from PySide6.QtCore import QTimer
    QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(window))

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
