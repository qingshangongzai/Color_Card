import os
import sys
from typing import Dict


def _get_base_path() -> str:
    """获取应用程序基础路径

    支持开发环境和 Nuitka/PyInstaller 打包后的环境

    Returns:
        str: 应用程序基础路径
    """
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _read_version_file() -> Dict[str, str]:
    """读取 version.txt 文件

    Returns:
        dict: 包含版本号和元数据的字典
    """
    base_path = _get_base_path()
    version_path = os.path.join(base_path, 'version.txt')

    try:
        with open(version_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]
    except (OSError, IOError) as e:
        print(f"读取 version.txt 失败: {e}")
        return {}

    fields = ["version", "file_version", "product_version",
              "company", "copyright", "description"]
    result = {}
    for i, field in enumerate(fields):
        if i < len(lines) and lines[i]:
            result[field] = lines[i]
    return result


class VersionManager:
    """应用程序版本管理器"""

    def __init__(self) -> None:
        data = _read_version_file()

        self.version: str = data.get("version", "0.0.0")
        self._copyright: str = data.get("copyright", "")

    def get_version(self) -> str:
        """获取当前版本号

        Returns:
            str: 应用程序版本号，格式为"X.Y.Z"
        """
        return self.version

    def get_copyright(self) -> str:
        """获取版权信息

        Returns:
            str: 版权信息字符串
        """
        return self._copyright


version_manager: VersionManager = VersionManager()