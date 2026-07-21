from __future__ import annotations



class VersionManager:
    """应用程序版本管理器，负责管理应用程序的版本信息和应用元数据"""

    def __init__(self) -> None:
        """初始化版本管理器"""
        # 版本号组件
        self.major: int = 1
        self.minor: int = 11
        self.patch: int = 0
        self.prerelease: str = ""

        # 核心版本信息
        self.version: str = f"{self.major}.{self.minor}.{self.patch}{self.prerelease}"

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

    def get_app_info(self) -> dict[str, str]:
        """获取应用程序信息

        Returns:
            dict: 包含应用程序名称、公司、版权等元数据的字典
        """
        return self.app_info.copy()


# 创建全局版本管理器实例
version_manager: VersionManager = VersionManager()
