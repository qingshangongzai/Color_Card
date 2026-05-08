# 标准库导入
import argparse
import ctypes
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 将项目根目录添加到 sys.path（确保 installer 模块可导入）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def set_app_user_model_id():
    """设置 Windows AppUserModelID

    这必须在创建 QApplication 之前调用！
    """
    if os.name != 'nt':
        return False

    try:
        app_id = 'HXiaoStudio.ColorCard.1.0.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except (OSError, AttributeError):
        return False


# 立即调用（在导入 PySide6 之前）
set_app_user_model_id()


def setup_global_exception_handler(logger):
    """设置全局异常处理器

    Args:
        logger: 日志记录器
    """
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "未捕获的异常",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception


def _create_splash_screen(project_root: str):
    """创建并显示启动画面

    Args:
        project_root: 项目根目录路径

    Returns:
        QSplashScreen | None: 启动画面对象，失败时返回 None
    """
    from PySide6.QtCore import Qt, QSize
    from PySide6.QtGui import QColor, QIcon
    from PySide6.QtWidgets import QSplashScreen

    logo_path = os.path.join(project_root, 'logo', 'Color Card_logo.ico')
    icon = QIcon(logo_path)
    if icon.isNull():
        return None

    pixmap = icon.pixmap(QSize(192, 192))
    if pixmap.isNull():
        return None

    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.SplashScreen
        | Qt.WindowType.WindowDoesNotAcceptFocus
    )

    screen = QApplication.primaryScreen()
    if screen:
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - pixmap.width()) // 2
        y = (screen_geometry.height() - pixmap.height()) // 2
        splash.move(x, y)

    splash.show()
    QApplication.processEvents()
    splash.showMessage(
        "启动中……",
        alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        color=QColor(128, 128, 128)
    )

    return splash


# Windows 注册表支持
if sys.platform == 'win32':
    import winreg

# 第三方库导入
from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme

# 项目模块导入
from installer.core.registry_installer import REGISTRY_KEY
from installer.core.install_service import InstallService
from installer.core.permission_checker import is_frozen, get_exe_path
from installer.wizard.install_wizard import InstallWizard
from installer.wizard.pages.welcome_page import WelcomePage
from installer.wizard.pages.install_path_page import InstallPathPage
from installer.wizard.pages.progress_page import ProgressPage
from installer.wizard.pages.finish_page import FinishPage


def _get_install_path() -> str:
    """从注册表获取旧版本的安装路径

    Returns:
        str: 安装路径，未找到返回空字符串
    """
    if sys.platform != 'win32':
        return ''

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        with key:
            path, _ = winreg.QueryValueEx(key, "InstallPath")
            return path if path else ''
    except (OSError, FileNotFoundError):
        return ''


def _is_running_installer() -> bool:
    """检测当前是否以安装程序身份运行（而非已安装的程序）

    判断依据：exe 所在位置
    - 打包后在临时目录 → 安装程序（NSIS/Inno 释放的安装包）
    - 打包后在安装目录内 → 已安装的程序
    - 打包后在下载目录等 → 安装程序（用户刚下载的新安装包）

    Returns:
        bool: 是否为安装程序
    """
    if not is_frozen():
        return True

    exe_path = get_exe_path()

    temp_dir = os.environ.get('TEMP', '')
    if temp_dir and str(exe_path).lower().startswith(temp_dir.lower()):
        return True

    old_install_path = _get_install_path()
    if old_install_path:
        try:
            exe_path.relative_to(Path(old_install_path))
            return False
        except ValueError:
            return True

    return True


def run_installer(
    old_install_path: str = '',
    skip_to_progress: bool = False,
    preset_config: dict | None = None
) -> dict:
    """运行安装向导

    Args:
        old_install_path: 旧版本安装路径（用于升级时预填）
        skip_to_progress: 是否直接跳转到进度页面
        preset_config: 预设配置（提权重启后恢复）

    Returns:
        dict: 安装配置
    """
    wizard = InstallWizard()

    wizard.add_page(WelcomePage())

    path_page = InstallPathPage()
    if old_install_path:
        path_page.set_default_path(old_install_path)
    wizard.add_page(path_page)

    progress_page = ProgressPage()
    install_service = InstallService()
    progress_page.set_install_service(install_service)
    wizard.add_page(progress_page)

    wizard.add_page(FinishPage())

    if skip_to_progress and preset_config:
        wizard.set_preset_config(preset_config)
        wizard.skip_to_progress_page()

    wizard.exec()
    return wizard.get_config()


def _get_project_root() -> str:
    """获取项目根目录

    PyInstaller：sys._MEIPASS（临时解压目录）
    Nuitka：__file__ 所在目录（与 logo 在同一临时解压目录）
    开发环境：installer/main.py 的父目录

    Returns:
        str: 项目根目录
    """
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    import __main__
    if getattr(__main__, '__compiled__', False):
        return str(Path(__file__).resolve().parent)
    return str(Path(__file__).resolve().parent.parent)


def run_uninstaller(skip_to_progress: bool = False, delete_config: bool = False):
    """运行卸载程序

    Args:
        skip_to_progress: 是否直接开始卸载
        delete_config: 是否删除用户配置
    """
    import subprocess
    from installer.uninstaller.uninstall_dialog import UninstallDialog
    from installer.core.registry_installer import RegistryInstaller
    from core import get_logger

    logger = get_logger("installer")

    # 对话框启动前读取安装路径（注册表在卸载过程中会被删除）
    registry_installer = RegistryInstaller()
    install_path = registry_installer.get_install_path()

    dialog = UninstallDialog()

    if skip_to_progress:
        dialog.start_uninstall(delete_config)

    result = dialog.exec()

    if result == 1 and install_path:
        batch_path = install_path / "uninstall_cleanup.bat"
        if batch_path.exists():
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                subprocess.Popen(
                    ['cmd.exe', '/c', str(batch_path)],
                    cwd=os.environ['TEMP'],
                    startupinfo=startupinfo
                )
                logger.info("自删除脚本已启动")
            except (OSError, subprocess.SubprocessError) as e:
                logger.error(f"自删除脚本启动失败: {e}")


def run_main_app():
    """运行主程序

    执行完整的初始化流程，包括日志、配置、语言包、主题等。
    """
    startup_start_time = time.perf_counter()

    project_root = _get_project_root()
    os.chdir(project_root)

    splash = _create_splash_screen(project_root)

    from core import get_logger_manager, get_logger
    logger_manager = get_logger_manager()
    logger_manager.initialize()
    logger = get_logger("installer")
    setup_global_exception_handler(logger)

    try:
        from io import StringIO
        _old_stdout = sys.stdout
        sys.stdout = StringIO()

        from core import get_config_manager
        config_manager = get_config_manager()
        config_manager.load()

        from utils import get_locale_manager
        locale_manager = get_locale_manager()
        language_setting = config_manager.get('settings.language', 'auto')
        locale_manager.load_language(language_setting)

        from PySide6.QtCore import qInstallMessageHandler, QTimer
        from qfluentwidgets import setTheme, setThemeColor, Theme

        sys.stdout = _old_stdout

        def _qt_message_handler(mode, _context, message):
            if "QFont::setPointSize: Point size <= 0" in message:
                return
            sys.__stdout__.write(message + '\n')

        qInstallMessageHandler(_qt_message_handler)

        theme_setting = config_manager.get('settings.theme', 'auto')
        if theme_setting == 'light':
            setTheme(Theme.LIGHT)
        elif theme_setting == 'dark':
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.AUTO)
        setThemeColor('#0078d4')

        from ui.main_window import MainWindow
        from utils import fix_windows_taskbar_icon_for_window, force_window_to_front
        window = MainWindow()
        window.show()

        if hasattr(window, 'titleBar') and hasattr(window.titleBar, 'init_theme'):
            window.titleBar.init_theme(theme_setting)

        if splash:
            splash.finish(window)
        fix_windows_taskbar_icon_for_window(window)
        force_window_to_front(window)

        startup_time = (time.perf_counter() - startup_start_time) * 1000
        logger.info(f"启动完成，总耗时: {startup_time:.2f}ms")

        def _auto_check_update(window, config_manager):
            if not config_manager.get('settings.auto_check_update', True):
                return
            last_check = config_manager.get('settings.last_check_time')
            if last_check:
                try:
                    last_time = datetime.fromisoformat(last_check)
                    if datetime.now() - last_time < timedelta(days=7):
                        return
                except (ValueError, TypeError):
                    pass
            from version import version_manager
            from dialogs import UpdateAvailableDialog
            UpdateAvailableDialog.check_update(window, version_manager.get_version())
            config_manager.set('settings.last_check_time', datetime.now().isoformat())
            config_manager.save()

        QTimer.singleShot(3000, lambda: _auto_check_update(window, config_manager))

        return window

    except (OSError, ImportError, ValueError) as e:
        logger.critical(f"程序启动失败: {str(e)}", exc_info=True)
        raise


def main():
    """主入口"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--uninstall', action='store_true', help='运行卸载程序')
    parser.add_argument('--install-path', type=str, help='用户选择的安装路径')
    parser.add_argument('--skip-to-progress', action='store_true', help='直接跳转到安装进度页面')
    parser.add_argument('--desktop-shortcut', action='store_true', help='创建桌面快捷方式')
    parser.add_argument('--start-menu-shortcut', action='store_true', help='创建开始菜单快捷方式')
    parser.add_argument('--skip-to-uninstall-progress', action='store_true', help='直接开始卸载')
    parser.add_argument('--delete-config', action='store_true', help='删除用户配置')
    args = parser.parse_args()

    os.environ['QT_IMAGEIO_MAXALLOC'] = '1024'

    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)

    from utils import load_icon_universal
    app_icon = load_icon_universal()
    app.setWindowIcon(app_icon)

    if args.uninstall:
        run_uninstaller(
            skip_to_progress=args.skip_to_uninstall_progress,
            delete_config=args.delete_config
        )
        sys.exit(0)

    if _is_running_installer():
        old_path = _get_install_path()
        preset_path = args.install_path or old_path

        preset_config = None
        if args.skip_to_progress and args.install_path:
            preset_config = {
                'install_path': args.install_path,
                'create_desktop_shortcut': args.desktop_shortcut,
                'create_start_menu': args.start_menu_shortcut,
            }

        config = run_installer(
            old_install_path=preset_path,
            skip_to_progress=args.skip_to_progress,
            preset_config=preset_config
        )

        if config.get('run_after_install', False):
            install_path = config.get('install_path', '')
            if install_path:
                exe_path = Path(install_path) / "Color Card.exe"
                if exe_path.exists():
                    import subprocess
                    subprocess.Popen(
                        [str(exe_path)],
                        shell=True,
                        creationflags=subprocess.DETACHED_PROCESS
                    )
            sys.exit(0)
        else:
            sys.exit(0)
    else:
        window = run_main_app()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
