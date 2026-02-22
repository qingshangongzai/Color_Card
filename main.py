# 标准库导入
import ctypes
import os
import sys


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


# 立即调用（在导入 PySide6 之前）
set_app_user_model_id()

# 只导入启动画面必需的模块
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen


def _get_base_path() -> str:
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
    # 开发环境 - 返回当前文件所在目录
    return os.path.dirname(os.path.abspath(__file__))


def _create_splash_screen():
    """创建并显示启动画面

    Returns:
        QSplashScreen: 启动画面对象，如果创建失败返回 None
    """
    try:
        # 获取基础路径
        base_path = _get_base_path()

        # 构建 logo 路径
        logo_path = os.path.join(base_path, 'logo', 'Color Card_logo.ico')

        # 加载启动画面图片
        splash_pixmap = QPixmap(logo_path)
        if splash_pixmap.isNull():
            return None

        # 缩放到 250x250
        splash_pixmap = splash_pixmap.scaled(
            250, 250,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # 创建启动画面
        splash = QSplashScreen(splash_pixmap)
        splash.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )

        # 居中显示
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - splash_pixmap.width()) // 2
            y = (screen_geometry.height() - splash_pixmap.height()) // 2
            splash.move(x, y)

        # 显示启动画面
        splash.show()

        # 添加"启动中……"文字
        splash.showMessage(
            "启动中……",
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            color=QColor(128, 128, 128)
        )

        return splash
    except Exception:
        return None


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 增加 Qt 图像分配限制，支持超大图片（1GB）
    os.environ['QT_IMAGEIO_MAXALLOC'] = '1024'

    app = QApplication(sys.argv)

    # 立即显示启动画面（在其他模块导入前）
    splash = _create_splash_screen()

    # 临时重定向 stdout 以屏蔽 QFluentWidgets 的推广提示
    from io import StringIO
    _old_stdout = sys.stdout
    sys.stdout = StringIO()

    # 导入其他模块（在启动画面显示后）
    from PySide6.QtCore import qInstallMessageHandler
    from qfluentwidgets import setTheme, setThemeColor, Theme

    # 恢复 stdout
    sys.stdout = _old_stdout

    # 安装自定义 Qt 消息处理器以过滤 QFont 警告
    def qt_message_handler(mode, context, message):
        """自定义 Qt 消息处理器，过滤掉 QFont::setPointSize 警告"""
        if "QFont::setPointSize: Point size <= 0" in message:
            return
        # 调用默认处理器输出其他消息
        sys.__stdout__.write(message + '\n')

    qInstallMessageHandler(qt_message_handler)

    # 导入项目模块
    from core import get_config_manager
    from utils import fix_windows_taskbar_icon_for_window, load_icon_universal, tr, get_locale_manager
    from ui import MainWindow

    # 设置应用程序图标（重要！）
    app_icon = load_icon_universal()
    app.setWindowIcon(app_icon)

    # 加载主题配置并设置初始主题
    config_manager = get_config_manager()
    config_manager.load()
    
    # 初始化语言管理器并加载用户语言配置
    locale_manager = get_locale_manager()
    language_setting = config_manager.get('settings.language', 'ZW_JT')
    locale_manager.load_language(language_setting)
    
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

    # 关闭启动画面并修复任务栏图标（在窗口显示后调用）
    def _on_window_shown():
        if splash:
            splash.finish(window)
        fix_windows_taskbar_icon_for_window(window)

    QTimer.singleShot(100, _on_window_shown)

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        # 用户中断程序（Ctrl+C），正常退出
        print("\n程序被用户中断")
        sys.exit(0)


if __name__ == '__main__':
    main()
