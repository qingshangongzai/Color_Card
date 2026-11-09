# 标准库导入
import argparse
import ctypes
import os
import sys
from pathlib import Path
# 源码直接运行时将项目根目录加入 sys.path；打包后 sys.path 已由运行时配置，
# 再插入会把解压目录里的 .py 副本顶到导入优先级之上，导致模块半初始化
if '__compiled__' not in globals():
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

# 第三方库导入（必须在 set_app_user_model_id 之后导入）
from PySide6.QtWidgets import QApplication

# 项目模块导入（必须在 set_app_user_model_id 之后导入）
from installer.core.registry_installer import REGISTRY_KEY


def _get_install_path() -> str:
    """从注册表获取旧版本的安装路径

    HKCU 优先（新版安装器），HKLM 回退（旧 Inno Setup）。

    Returns:
        str: 安装路径，未找到返回空字符串
    """
    if sys.platform != 'win32':
        return ''

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        with key:
            path, _ = winreg.QueryValueEx(key, "InstallPath")
            if path:
                return path
    except (OSError, FileNotFoundError):
        pass

    from installer.core.registry_installer import RegistryInstaller
    registry = RegistryInstaller()
    inno_path = registry.find_inno_install_path()
    if inno_path:
        return str(inno_path)

    return ''


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
    from installer.wizard.install_wizard import InstallWizard
    from installer.wizard.pages.welcome_page import WelcomePage
    from installer.wizard.pages.install_path_page import InstallPathPage
    from installer.wizard.pages.update_page import UpdatePage
    from installer.wizard.pages.progress_page import ProgressPage
    from installer.wizard.pages.finish_page import FinishPage
    from installer.core.install_service import InstallService

    wizard = InstallWizard()

    wizard.add_page(WelcomePage())

    # 旧安装目录仍在才算更新：注册表有残留但目录被删时回退到新安装
    if old_install_path and Path(old_install_path).exists():
        wizard.add_page(UpdatePage(old_install_path))
    else:
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


def main():
    """主入口"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--install-path', type=str, help='用户选择的安装路径')
    parser.add_argument('--skip-to-progress', action='store_true', help='直接跳转到安装进度页面')
    parser.add_argument('--desktop-shortcut', action='store_true', help='创建桌面快捷方式')
    parser.add_argument('--start-menu-shortcut', action='store_true', help='创建开始菜单快捷方式')
    args = parser.parse_args()

    os.environ['QT_IMAGEIO_MAXALLOC'] = '1024'

    app = QApplication(sys.argv)

    # 迷你样式层：深浅色启动时判定一次并烘焙进 QSS（替代原组件库主题入口）
    from installer.wizard.mini_style import apply_mini_style
    apply_mini_style(app)

    from utils import load_icon_universal
    app_icon = load_icon_universal()
    app.setWindowIcon(app_icon)

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


if __name__ == "__main__":
    main()
