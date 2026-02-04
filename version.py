"""版本管理模块

负责管理应用程序的版本信息和应用元数据。
"""


class VersionManager:
    """应用程序版本管理器，负责管理应用程序的版本信息和应用元数据"""

    def __init__(self):
        """初始化版本管理器"""
        # 版本号组件
        self.major = 1
        self.minor = 0
        self.patch = 0
        self.build = 0

        # 核心版本信息
        self.version = f"{self.major}.{self.minor}.{self.patch}"

        # 详细版本信息结构
        self.version_info = {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "build": self.build,
            "full": f"{self.major}.{self.minor}.{self.patch}",
            "short": f"{self.major}.{self.minor}.{self.patch}"
        }

        # 应用程序元数据
        self.app_info = {
            "name": "取色卡",
            "name_en": "Color Card",
            "company": "浮晓 HXiao Studio",
            "copyright": "© 2026 浮晓 HXiao Studio",
            "description": "取色卡 - Color Card",
            "internal_name": "Color_Card",
            "original_filename": "Color_Card.exe",
            "developer": "青山公仔",
            "email": "hxiao_studio@163.com"
        }

    def get_version(self):
        """获取当前版本号

        Returns:
            str: 应用程序版本号，格式为"X.Y.Z"
        """
        return self.version

    def get_version_info(self):
        """获取版本详细信息

        Returns:
            dict: 包含主要版本号、次要版本号、补丁版本号、构建号和完整版本号的字典
        """
        return self.version_info.copy()

    def get_app_info(self):
        """获取应用程序信息

        Returns:
            dict: 包含应用程序名称、公司、版权等元数据的字典
        """
        return self.app_info.copy()

    def get_full_app_name(self):
        """获取完整应用程序名称（包含版本号）

        Returns:
            str: 完整的应用程序名称，格式为"应用名称 v版本号"
        """
        return f"{self.app_info['name']} v{self.version}"

    def get_file_version_info(self):
        """获取文件版本信息（用于Windows EXE元数据）

        Returns:
            dict: 包含文件版本和产品版本的高16位和低16位值的字典
        """
        return {
            "file_version_ms": (self.version_info["major"] << 16) | self.version_info["minor"],
            "file_version_ls": (self.version_info["patch"] << 16) | self.version_info["build"],
            "product_version_ms": (self.version_info["major"] << 16) | self.version_info["minor"],
            "product_version_ls": (self.version_info["patch"] << 16) | self.version_info["build"]
        }


# 创建全局版本管理器实例
version_manager = VersionManager()
