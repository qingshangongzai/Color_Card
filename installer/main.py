# 标准库导入
import argparse
import ctypes
import os
import sys
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

# Windows 注册表支持
if sys.platform == 'win32':
    import winreg

# 第三方库导入
from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme

# 项目模块导入
from installer.core.registry_installer import REGISTRY_KEY
from installer.core.install_service import InstallService
from installer.wizard.install_wizard import InstallWizard
from installer.wizard.pages.welcome_page import WelcomePage
from installer.wizard.pages.install_path_page import InstallPathPage
from installer.wizard.pages.progress_page import ProgressPage
from installer.wizard.pages.finish_page import FinishPage


def is_frozen() -> bool:
    """检测是否为打包后的环境

    Returns:
        bool: 是否为打包后的exe
    """
    return getattr(sys, 'frozen', False)


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
    - 开发环境 → 始终是安装程序
    - 打包后在临时目录 → 安装程序（NSIS/Inno 释放的安装包）
    - 打包后在安装目录内 → 已安装的程序
    - 打包后在下载目录等 → 安装程序（用户刚下载的新安装包）

    Returns:
        bool: 是否为安装程序
    """
    if not is_frozen():
        return True

    exe_path = Path(sys.executable).resolve()

    # 在临时目录 → 安装程序
    temp_dir = os.environ.get('TEMP', '')
    if temp_dir and str(exe_path).lower().startswith(temp_dir.lower()):
        return True

    # 检查是否在已安装的目录内
    old_install_path = _get_install_path()
    if old_install_path:
        try:
            exe_path.relative_to(Path(old_install_path))
            return False  # 在安装目录内 → 已安装的程序
        except ValueError:
            return True  # 不在安装目录内 → 新下载的安装程序

    return True


def run_installer(
    test_mode: bool = False,
    old_install_path: str = '',
    skip_to_progress: bool = False,
    preset_config: dict | None = None
) -> dict:
    """运行安装向导

    Args:
        test_mode: 测试模式
        old_install_path: 旧版本安装路径（用于升级时预填）
        skip_to_progress: 是否直接跳转到进度页面
        preset_config: 预设配置（提权重启后恢复）

    Returns:
        dict: 安装配置
    """
    wizard = InstallWizard()

    wizard.add_page(WelcomePage())

    # 路径选择页面：升级模式下预填旧路径
    path_page = InstallPathPage()
    if old_install_path:
        path_page.set_default_path(old_install_path)
    wizard.add_page(path_page)

    progress_page = ProgressPage()
    install_service = InstallService(test_mode)
    progress_page.set_install_service(install_service)
    wizard.add_page(progress_page)

    wizard.add_page(FinishPage())

    # 如果需要直接跳转到进度页面
    if skip_to_progress and preset_config:
        wizard.set_preset_config(preset_config)
        wizard.skip_to_progress_page()

    wizard.exec()
    return wizard.get_config()


def _get_project_root() -> str:
    """获取项目根目录

    开发环境：installer/main.py 的父目录
    打包环境：exe 所在目录

    Returns:
        str: 项目根目录
    """
    if is_frozen():
        return os.path.dirname(sys.executable)
    return str(Path(__file__).resolve().parent.parent)


def run_uninstaller(skip_to_progress: bool = False, delete_config: bool = False):
    """运行卸载程序

    Args:
        skip_to_progress: 是否直接开始卸载
        delete_config: 是否删除用户配置
    """
    from installer.uninstaller.uninstall_dialog import UninstallDialog

    dialog = UninstallDialog()

    # 如果需要直接开始卸载
    if skip_to_progress:
        dialog.start_uninstall(delete_config)

    result = dialog.exec()

    # 如果卸载成功，执行自删除批处理脚本
    if result == 1:  # QDialog.Accepted
        from installer.core.registry_installer import RegistryInstaller
        registry_installer = RegistryInstaller()
        install_path = registry_installer.get_install_path()

        if install_path:
            batch_path = install_path / "uninstall_cleanup.bat"
            if batch_path.exists():
                import subprocess
                subprocess.Popen(
                    str(batch_path),
                    shell=True,
                    creationflags=subprocess.DETACHED_PROCESS
                )


def run_main_app():
    """运行主程序

    执行完整的初始化流程，包括日志、配置、语言包、主题等。
    """
    # 切换工作目录到项目根目录，确保相对路径正确
    project_root = _get_project_root()
    os.chdir(project_root)

    # 初始化日志系统
    from core import get_logger_manager, get_logger
    logger_manager = get_logger_manager()
    logger_manager.initialize()
    logger = get_logger("installer")

    # 加载配置
    from core import get_config_manager
    config_manager = get_config_manager()
    config_manager.load()

    # 初始化语言管理器并加载用户语言配置
    from utils import get_locale_manager
    locale_manager = get_locale_manager()
    language_setting = config_manager.get('settings.language', 'ZW_JT')
    locale_manager.load_language(language_setting)

    # 设置主题
    from qfluentwidgets import setTheme, setThemeColor, Theme
    theme_setting = config_manager.get('settings.theme', 'auto')
    if theme_setting == 'light':
        setTheme(Theme.LIGHT)
    elif theme_setting == 'dark':
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.AUTO)
    setThemeColor('#0078d4')

    # 创建主窗口
    from ui.main_window import MainWindow
    from utils import fix_windows_taskbar_icon_for_window
    window = MainWindow()
    
    window.show()
    
    # 修复任务栏图标
    fix_windows_taskbar_icon_for_window(window)

    return window


def main():
    """主入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--uninstall', action='store_true', help='运行卸载程序')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--install-path', type=str, help='用户选择的安装路径')
    parser.add_argument('--skip-to-progress', action='store_true', help='直接跳转到安装进度页面')
    parser.add_argument('--desktop-shortcut', action='store_true', help='创建桌面快捷方式')
    parser.add_argument('--start-menu-shortcut', action='store_true', help='创建开始菜单快捷方式')
    parser.add_argument('--skip-to-uninstall-progress', action='store_true', help='直接开始卸载')
    parser.add_argument('--delete-config', action='store_true', help='删除用户配置')
    args = parser.parse_args()

    # 创建应用
    app = QApplication(sys.argv)

    # 设置主题
    setTheme(Theme.AUTO)

    # 设置应用程序图标（用于任务栏和窗口标题栏）
    from utils import load_icon_universal
    app_icon = load_icon_universal()
    app.setWindowIcon(app_icon)

    # 卸载模式
    if args.uninstall:
        run_uninstaller(
            skip_to_progress=args.skip_to_uninstall_progress,
            delete_config=args.delete_config
        )
        sys.exit(0)

    # 测试模式
    test_mode = args.test

    # 判断当前角色：安装程序 or 已安装的程序
    if _is_running_installer():
        # 检查是否有旧版本（升级场景）
        old_path = _get_install_path()

        # 提权重启后恢复用户选择的路径
        preset_path = args.install_path or old_path

        # 构建预设配置（提权重启后恢复）
        preset_config = None
        if args.skip_to_progress and args.install_path:
            preset_config = {
                'install_path': args.install_path,
                'create_desktop_shortcut': args.desktop_shortcut,
                'create_start_menu': args.start_menu_shortcut,
            }

        config = run_installer(
            test_mode,
            old_install_path=preset_path,
            skip_to_progress=args.skip_to_progress,
            preset_config=preset_config
        )

        if config.get('run_after_install', False):
            # 启动已安装的主程序（新进程）
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
        # 已安装的程序，直接启动主界面
        window = run_main_app()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
