"""卸载入口

由主程序 `--uninstall` 分流调用，调用前必须已创建 QApplication
（UninstallDialog 是 QWidget，无 QApplication 无法创建）。
"""

# 标准库导入
import os
import subprocess

# 项目模块导入
from core.logger import get_logger
from installer.core.registry_installer import RegistryInstaller
from uninstaller.uninstall_dialog import UninstallDialog

logger = get_logger("installer")


def run_uninstall(skip_to_progress: bool = False, delete_config: bool = False) -> None:
    """运行卸载程序

    Args:
        skip_to_progress: 是否直接开始卸载
        delete_config: 是否删除用户配置
    """
    # 对话框启动前读取安装路径：卸载过程中注册表条目会被删除
    install_path = RegistryInstaller().get_install_path()

    dialog = UninstallDialog()
    if skip_to_progress:
        dialog.start_uninstall(delete_config)

    if dialog.exec() != 1 or not install_path:
        return

    batch_path = install_path / "uninstall_cleanup.bat"
    if not batch_path.exists():
        return

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
