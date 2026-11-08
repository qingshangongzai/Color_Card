import subprocess
from pathlib import Path



class VersionManager:
    """应用程序版本管理器，负责管理应用程序的版本信息和应用元数据"""

    def __init__(self) -> None:
        """初始化版本管理器"""
        # 版本号组件
        self.major: int = 1
        self.minor: int = 12
        self.patch: int = 1
        self.prerelease: str = ""

        # 核心版本信息
        self.version: str = f"{self.major}.{self.minor}.{self.patch}{self.prerelease}"

        # 构建信息（git 提交序号与 SHA，仅在启动时解析一次）
        self.build_number, self.commit_sha = self._resolve_build_info()

        # 应用程序元数据
        self.app_info: dict[str, str] = {
            "name": "取色卡",
            "name_en": "Color Card",
            "company": "浮晓 HXiao Studio",
            "copyright": "© 2026 浮晓 HXiao Studio",
            "description": "取色卡(Color Card) - 一站式色彩工具",
            "internal_name": "Color_Card",
            "original_filename": "Color_Card.exe",
            "developer": "青山公仔",
            "email": "hxiao_studio@163.com"
        }

    def get_version(self) -> str:
        """获取当前版本号

        Returns:
            str: 应用程序版本号，格式为"X.Y.Z"
        """
        return self.version

    def get_display_version(self) -> str:
        """获取展示用的完整版本号（含构建号，用于日志等展示场景）

        版本比较（更新检查等）请使用 get_version()，构建信息只用于展示。

        Returns:
            str: 展示版本号，格式为"X.Y.Z[预发布].构建号"
        """
        return f"{self.version}.{self.build_number}"

    def _resolve_build_info(self) -> tuple[str, str]:
        """解析构建信息：优先读打包时固化的 build_info.py，其次查询 git

        Returns:
            tuple[str, str]: (构建号, 提交 SHA)，git 不可用时返回 ("dev", "")
        """
        try:
            # build_info.py 由 CI 打包前生成（源码仓库中不存在，故为可选导入）
            from build_info import BUILD_NUMBER, COMMIT_SHA
        except ImportError:
            return self._query_git_build_info()
        return BUILD_NUMBER, COMMIT_SHA

    def _query_git_build_info(self) -> tuple[str, str]:
        """查询 git 提交序号与 SHA 作为构建信息（源码运行模式）

        Returns:
            tuple[str, str]: (构建号, 提交 SHA)，git 不可用时返回 ("dev", "")
        """
        try:
            # 打包后没有 .git 目录，此路径只在源码模式可达，cwd 用文件所在目录即仓库根
            common_args = {
                "capture_output": True,
                "text": True,
                "timeout": 5,
                "cwd": Path(__file__).resolve().parent,
                "check": True,
            }
            number = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"], **common_args
            ).stdout.strip()
            sha = subprocess.run(
                ["git", "rev-parse", "--short=8", "HEAD"], **common_args
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "dev", ""
        return number, sha

    def get_app_info(self) -> dict[str, str]:
        """获取应用程序信息

        Returns:
            dict: 包含应用程序名称、公司、版权等元数据的字典
        """
        return self.app_info.copy()


# 创建全局版本管理器实例
version_manager: VersionManager = VersionManager()
