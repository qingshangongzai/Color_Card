# 标准库导入
import ctypes
import os
import sys
from io import StringIO


def set_app_user_model_id():
    """设置 Windows AppUserModelID
    
    这必须在创建 QApplication 之前调用！
    格式：CompanyName.AppName.Version
    """
    if os.name != 'nt':
        return False
    
    try:
        app_id = 'HXiaoStudio.ColorCard.1.0.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except Exception:
        return False


def qt_message_handler(mode, context, message):
    """自定义 Qt 消息处理器，过滤掉 QFont::setPointSize 警告"""
    if "QFont::setPointSize: Point size <= 0" in message:
        return
    # 调用默认处理器输出其他消息
    sys.__stdout__.write(message + '\n')


# 立即调用（在导入 PySide6 之前）
set_app_user_model_id()

# 临时重定向 stdout 以屏蔽 QFluentWidgets 的推广提示
_old_stdout = sys.stdout
sys.stdout = StringIO()

# 第三方库导入
from PySide6.QtCore import Qt, QTimer, qInstallMessageHandler
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, setThemeColor, Theme

# 恢复 stdout
sys.stdout = _old_stdout

# 安装自定义 Qt 消息处理器以过滤 QFont 警告
qInstallMessageHandler(qt_message_handler)

# 项目模块导入
from core import get_config_manager
from utils import fix_windows_taskbar_icon_for_window, load_icon_universal
from ui import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # 设置应用程序图标（重要！）
    app_icon = load_icon_universal()
    app.setWindowIcon(app_icon)

    # 加载主题配置并设置初始主题
    config_manager = get_config_manager()
    config_manager.load()
    theme_setting = config_manager.get('settings.theme', 'auto')

    if theme_setting == 'light':
        setTheme(Theme.LIGHT)
    elif theme_setting == 'dark':
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.AUTO)

    setThemeColor('#0078d4')

    window = MainWindow()
    window.show()

    # 修复任务栏图标（在窗口显示后调用）
    QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(window))

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        # 用户中断程序（Ctrl+C），正常退出
        print("\n程序被用户中断")
        sys.exit(0)


if __name__ == '__main__':
    main()
