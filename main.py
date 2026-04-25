# 标准库导入
import ctypes
import os
import sys
import time

# 记录启动开始时间
_startup_start_time = time.perf_counter()

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
        # 日志系统尚未初始化，静默处理
        return False


def setup_global_exception_handler(logger):
    """设置全局异常处理器

    Args:
        logger: 日志记录器
    """
    def handle_exception(exc_type, exc_value, exc_traceback):
        """处理未捕获的异常"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "未捕获的异常",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception


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
    """创建并显示启动画面"""
    base_path = _get_base_path()
    logo_path = os.path.join(base_path, 'logo', 'Color Card_logo.ico')

    splash_pixmap = QPixmap(logo_path)
    if splash_pixmap.isNull():
        return None

    splash_pixmap = splash_pixmap.scaled(
        250, 250,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    splash = QSplashScreen(splash_pixmap)
    splash.setWindowFlags(
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.SplashScreen |
        Qt.WindowType.WindowDoesNotAcceptFocus
    )

    screen = QApplication.primaryScreen()
    if screen:
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - splash_pixmap.width()) // 2
        y = (screen_geometry.height() - splash_pixmap.height()) // 2
        splash.move(x, y)

    splash.show()
    splash.showMessage(
        "启动中……",
        alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        color=QColor(128, 128, 128)
    )

    return splash


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 增加 Qt 图像分配限制，支持超大图片（1GB）
    os.environ['QT_IMAGEIO_MAXALLOC'] = '1024'

    app = QApplication(sys.argv)

    # 初始化日志系统
    from core import get_logger_manager, get_logger
    logger_manager = get_logger_manager()
    logger_manager.initialize()

    logger = get_logger("main")
    logger.info("应用程序启动")
    logger.info(f"运行环境: frozen={getattr(sys, 'frozen', False)}, _MEIPASS={getattr(sys, '_MEIPASS', None)}, __compiled__={'__compiled__' in globals()}")

    # 记录关键路径信息
    logger.info(f"sys.argv[0]={sys.argv[0]}")
    logger.info(f"sys.executable={sys.executable}")
    logger.info(f"sys.path[0]={sys.path[0] if sys.path else 'empty'}")

    # 设置全局异常处理器
    setup_global_exception_handler(logger)

    # 立即显示启动画面（在其他模块导入前）
    logger.info("开始创建启动画面...")
    splash = _create_splash_screen()
    logger.info(f"启动画面创建完成: {splash is not None}")

    try:
        logger.info("进入主try块...")
        # 临时重定向 stdout 以屏蔽 QFluentWidgets 的推广提示
        from io import StringIO
        _old_stdout = sys.stdout
        sys.stdout = StringIO()

        # 导入其他模块（在启动画面显示后）
        logger.info("开始导入 PySide6 模块...")
        from PySide6.QtCore import qInstallMessageHandler
        logger.info("PySide6 模块导入完成")

        logger.info("开始导入 qfluentwidgets 模块...")
        from qfluentwidgets import setTheme, setThemeColor, Theme
        logger.info("qfluentwidgets 模块导入完成")

        # 恢复 stdout
        sys.stdout = _old_stdout

        # 安装自定义 Qt 消息处理器以过滤 QFont 警告
        def qt_message_handler(mode, _context, message):
            """自定义 Qt 消息处理器，过滤掉 QFont::setPointSize 警告"""
            if "QFont::setPointSize: Point size <= 0" in message:
                return
            # 调用默认处理器输出其他消息
            sys.__stdout__.write(message + '\n')

        qInstallMessageHandler(qt_message_handler)

        # 导入项目模块
        logger.info("开始导入项目模块...")
        logger.info("导入 core 模块...")
        from core import get_config_manager
        logger.info("core 模块导入完成")

        logger.info("导入 utils 模块...")
        from utils import fix_windows_taskbar_icon_for_window, load_icon_universal, get_locale_manager, force_window_to_front
        logger.info("utils 模块导入完成")

        logger.info("导入 ui 模块...")
        from ui import MainWindow
        logger.info("ui 模块导入完成")

        # 设置应用程序图标（重要！）
        logger.info("设置应用程序图标...")
        app_icon = load_icon_universal()
        app.setWindowIcon(app_icon)
        logger.info("应用程序图标设置完成")

        # 加载配置
        logger.info("加载配置...")
        try:
            config_manager = get_config_manager()
            logger.info("获取配置管理器完成")
            config_manager.load()
            logger.info("配置加载完成")
        except Exception as e:
            logger.error(f"配置加载失败: {e}", exc_info=True)
            raise

        # 初始化语言管理器并加载用户语言配置
        logger.info("初始化语言管理器...")
        try:
            locale_manager = get_locale_manager()
            logger.info("获取语言管理器完成")
            language_setting = config_manager.get('settings.language', 'ZW_JT')
            locale_manager.load_language(language_setting)
            logger.info(f"语言设置: {language_setting}")
        except Exception as e:
            logger.error(f"语言管理器初始化失败: {e}", exc_info=True)
            raise

        # 设置主题
        logger.info("设置主题...")
        theme_setting = config_manager.get('settings.theme', 'auto')
        if theme_setting == 'light':
            setTheme(Theme.LIGHT)
        elif theme_setting == 'dark':
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.AUTO)
        setThemeColor('#0078d4')
        logger.info(f"主题设置完成: {theme_setting}")

        logger.info("创建主窗口...")
        try:
            window = MainWindow()
            logger.info("主窗口创建完成")
        except Exception as e:
            logger.error(f"主窗口创建失败: {e}", exc_info=True)
            raise

        # 初始化标题栏主题按钮状态
        if hasattr(window, 'titleBar') and hasattr(window.titleBar, 'init_theme'):
            window.titleBar.init_theme(theme_setting)

        window.show()
        logger.info("主窗口显示完成")

        # 关闭启动画面并修复任务栏图标（在窗口显示后调用）
        def _on_window_shown():
            if splash:
                splash.finish(window)

            # 修复任务栏图标
            fix_windows_taskbar_icon_for_window(window)

            # 使用 Windows API 强制将窗口带到最前
            # 这是解决启动期间用户操作其他窗口导致主窗口不弹出的关键
            force_window_to_front(window)

        QTimer.singleShot(100, _on_window_shown)
        logger.info("启动画面关闭定时器已设置")

        # 计算并输出启动时间
        startup_time = (time.perf_counter() - _startup_start_time) * 1000
        logger.info(f"启动完成，总耗时: {startup_time:.2f}ms")

        logger.info("进入主事件循环...")
        try:
            exit_code = app.exec()
            logger.info(f"主事件循环结束，退出码: {exit_code}")
            sys.exit(exit_code)
        except KeyboardInterrupt:
            logger.info("程序被用户中断 (Ctrl+C)")
            sys.exit(0)
        except Exception as e:
            logger.critical(f"主事件循环异常: {e}", exc_info=True)
            raise

    except Exception as e:
        logger.critical(f"程序启动失败: {str(e)}", exc_info=True)
        # 尝试记录更多调试信息
        try:
            import traceback
            tb_str = traceback.format_exc()
            logger.critical(f"异常堆栈:\n{tb_str}")
        except:
            pass
        raise


if __name__ == '__main__':
    main()
