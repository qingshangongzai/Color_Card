from __future__ import annotations
# 标准库导入
import sys
from pathlib import Path

# Windows 快捷方式支持
if sys.platform == 'win32':
    try:
        import win32com.client
        HAS_WIN32COM = True
    except ImportError:
        HAS_WIN32COM = False
else:
    HAS_WIN32COM = False

# 项目模块导入
from core import get_logger

logger = get_logger("installer.shortcut_installer")


class ShortcutInstaller:
    """快捷方式安装器

    负责创建和删除 Windows 快捷方式。
    """

    def create_desktop_shortcut(self, exe_path: Path, name: str) -> bool:
        """创建桌面快捷方式

        Args:
            exe_path: 可执行文件路径
            name: 快捷方式名称

        Returns:
            bool: 是否成功
        """
        if not HAS_WIN32COM:
            logger.warning("缺少 win32com 模块：跳过快捷方式创建")
            return True

        try:
            desktop = Path.home() / "Desktop"
            shortcut_path = desktop / f"{name}.lnk"
            self._create_shortcut(shortcut_path, str(exe_path), "", f"启动 {name}")
            logger.info(f"桌面快捷方式创建成功: {shortcut_path}")
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"桌面快捷方式创建失败: {str(e)}")
            return False

    def create_start_menu_shortcut(self, exe_path: Path, name: str) -> bool:
        """创建开始菜单快捷方式

        Args:
            exe_path: 可执行文件路径
            name: 快捷方式名称

        Returns:
            bool: 是否成功
        """
        if not HAS_WIN32COM:
            logger.warning("缺少 win32com 模块：跳过快捷方式创建")
            return True

        try:
            start_menu = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            program_group = start_menu / name
            program_group.mkdir(parents=True, exist_ok=True)
            shortcut_path = program_group / f"{name}.lnk"
            self._create_shortcut(shortcut_path, str(exe_path), "", f"启动 {name}")
            logger.info(f"开始菜单快捷方式创建成功: {shortcut_path}")
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"开始菜单快捷方式创建失败: {str(e)}")
            return False

    def create_uninstall_shortcut(self, exe_path: Path, name: str) -> bool:
        """创建卸载快捷方式

        Args:
            exe_path: 可执行文件路径
            name: 快捷方式名称

        Returns:
            bool: 是否成功
        """
        if not HAS_WIN32COM:
            logger.warning("缺少 win32com 模块：跳过快捷方式创建")
            return True

        try:
            start_menu = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            program_group = start_menu / name
            shortcut_path = program_group / "卸载.lnk"
            self._create_shortcut(shortcut_path, str(exe_path), "--uninstall", f"卸载 {name}")
            logger.info(f"卸载快捷方式创建成功: {shortcut_path}")
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"卸载快捷方式创建失败: {str(e)}")
            return False

    def remove_desktop_shortcut(self, name: str) -> bool:
        """删除桌面快捷方式

        Args:
            name: 快捷方式名称

        Returns:
            bool: 是否成功
        """
        try:
            desktop = Path.home() / "Desktop"
            shortcut_path = desktop / f"{name}.lnk"
            if shortcut_path.exists():
                shortcut_path.unlink()
                logger.info(f"桌面快捷方式删除成功: {shortcut_path}")
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"桌面快捷方式删除失败: {str(e)}")
            return False

    def remove_start_menu_shortcuts(self, name: str) -> bool:
        """删除开始菜单快捷方式

        Args:
            name: 快捷方式名称

        Returns:
            bool: 是否成功
        """
        try:
            start_menu = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            program_group = start_menu / name
            if program_group.exists():
                for item in program_group.iterdir():
                    if item.is_file():
                        item.unlink()
                program_group.rmdir()
                logger.info(f"开始菜单快捷方式删除成功: {program_group}")
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"开始菜单快捷方式删除失败: {str(e)}")
            return False

    def _create_shortcut(self, shortcut_path: Path, target: str, arguments: str, description: str):
        """创建快捷方式

        Args:
            shortcut_path: 快捷方式路径
            target: 目标路径
            arguments: 参数
            description: 描述
        """
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = target
        shortcut.Arguments = arguments
        shortcut.Description = description
        shortcut.WorkingDirectory = str(Path(target).parent)
        shortcut.save()
