# 标准库导入
import ctypes
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """检测是否为打包后的环境（支持 PyInstaller 和 Nuitka）

    Returns:
        bool: 是否为打包后的环境
    """
    if getattr(sys, 'frozen', False):
        return True
    # Nuitka 检测
    import __main__
    return getattr(__main__, '__compiled__', False)


def get_exe_path() -> Path:
    """获取当前可执行文件路径（支持 PyInstaller 和 Nuitka）

    Nuitka 下 sys.executable 指向编译时的 Python 解释器，
    需要用 sys.argv[0] 获取实际的 exe 路径。

    Returns:
        Path: 可执行文件路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller: sys.executable 就是 exe 路径
        return Path(sys.executable)
    # Nuitka: sys.argv[0] 是 exe 路径
    import __main__
    if getattr(__main__, '__compiled__', False):
        return Path(sys.argv[0]).resolve()
    # 开发环境
    return Path(sys.executable)


def close_app_processes(exe_name: str = "Color Card.exe") -> None:
    """关闭指定名称的应用程序进程（排除当前进程）

    用于卸载和覆盖安装场景，关闭旧版本程序。

    Args:
        exe_name: 可执行文件名称，默认为 "Color Card.exe"
    """
    try:
        current_pid = os.getpid()
        # 使用 tasklist 获取所有同名进程
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # 解析输出，关闭其他同名进程
        for line in result.stdout.strip().split('\n'):
            if not line or exe_name not in line:
                continue
            # 格式: "Color Card.exe","PID","Session Name","Session#","Mem Usage"
            parts = line.split(',')
            if len(parts) >= 2:
                pid_str = parts[1].strip('"')
                try:
                    pid = int(pid_str)
                    if pid != current_pid:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(pid)],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                except ValueError:
                    continue
    except (OSError, subprocess.SubprocessError):
        pass


def is_admin() -> bool:
    """检测当前进程是否具有管理员权限

    Returns:
        bool: 是否具有管理员权限
    """
    if os.name != 'nt':
        return True

    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except (OSError, AttributeError):
        return False


def requires_admin(path: str | Path) -> bool:
    """检测写入指定路径是否需要管理员权限

    通过尝试在目标目录创建临时文件来判断。

    Args:
        path: 目标路径

    Returns:
        bool: 是否需要管理员权限
    """
    path = Path(path)

    # 如果目录不存在，检查父目录
    check_path = path
    while not check_path.exists():
        check_path = check_path.parent
        if check_path == check_path.parent:
            break

    # 如果是根目录，检查驱动器
    if not check_path.exists():
        drive = os.path.splitdrive(path)[0]
        if drive:
            check_path = Path(drive + '\\')
        else:
            return True

    # 尝试创建临时文件
    try:
        test_file = check_path / '.write_test_temp_file'
        test_file.touch()
        test_file.unlink()
        return False
    except (OSError, PermissionError):
        return True


def run_as_admin(
    install_path: str | None = None,
    create_desktop_shortcut: bool = True,
    create_start_menu: bool = True,
    is_uninstall: bool = False,
    delete_config: bool = False
) -> None:
    """以管理员权限重新启动程序

    Args:
        install_path: 用户选择的安装路径（用于提权重启后恢复）
        create_desktop_shortcut: 是否创建桌面快捷方式
        create_start_menu: 是否创建开始菜单快捷方式
        is_uninstall: 是否为卸载模式
        delete_config: 是否删除用户配置（卸载模式）
    """
    if is_frozen():
        exe_path = str(get_exe_path())
        args = ""
    else:
        exe_path = sys.executable
        script_path = Path(__file__).resolve().parent.parent / 'main.py'
        args = f'"{script_path}"'

    if is_uninstall:
        args += " --uninstall --skip-to-uninstall-progress"
        if delete_config:
            args += " --delete-config"
    elif install_path:
        args += f' --install-path "{install_path}"'
        if create_desktop_shortcut:
            args += " --desktop-shortcut"
        if create_start_menu:
            args += " --start-menu-shortcut"
        args += " --skip-to-progress"

    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe_path, args, None, 1
        )
    except (OSError, AttributeError):
        pass

    sys.exit(0)
