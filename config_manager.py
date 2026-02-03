"""配置管理模块

负责应用程序状态的保存和加载，使用 JSON 格式存储配置。
配置文件位置：用户主目录下的 .color_card/config.json
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器，处理应用程序配置的加载和保存"""

    CONFIG_VERSION = "1.0"
    CONFIG_DIR_NAME = ".color_card"
    CONFIG_FILE_NAME = "config.json"

    def __init__(self):
        """初始化配置管理器"""
        self._config_path = self._get_config_path()
        self._config: Dict[str, Any] = {}
        self._load_default_config()

    def _get_config_path(self) -> Path:
        """获取配置文件路径

        Returns:
            Path: 配置文件的完整路径
        """
        home_dir = Path.home()
        config_dir = home_dir / self.CONFIG_DIR_NAME
        return config_dir / self.CONFIG_FILE_NAME

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        config_dir = self._config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

    def _load_default_config(self):
        """加载默认配置"""
        self._config = {
            "version": self.CONFIG_VERSION,
            "settings": {
                "hex_visible": True
            },
            "window": {
                "width": 940,
                "height": 660
            }
        }

    def load(self) -> Dict[str, Any]:
        """从文件加载配置

        Returns:
            Dict[str, Any]: 加载的配置字典
        """
        if not self._config_path.exists():
            return self._config

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # 合并加载的配置和默认配置（保留默认值作为后备）
            self._merge_config(self._config, loaded_config)

        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"加载配置文件失败: {e}")
            # 使用默认配置

        return self._config

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """递归合并配置字典

        Args:
            base: 基础配置字典（会被修改）
            override: 覆盖配置字典
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def save(self, config: Optional[Dict[str, Any]] = None):
        """保存配置到文件

        Args:
            config: 要保存的配置字典，如果为 None 则保存当前配置
        """
        if config is not None:
            self._config = config

        self._ensure_config_dir()

        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
        except (IOError, OSError) as e:
            print(f"保存配置文件失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项

        Args:
            key: 配置键，支持点号分隔的嵌套路径（如 "settings.hex_visible"）
            default: 默认值

        Returns:
            Any: 配置值，如果不存在则返回默认值
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """设置配置项

        Args:
            key: 配置键，支持点号分隔的嵌套路径（如 "settings.hex_visible"）
            value: 配置值
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_settings(self) -> Dict[str, Any]:
        """获取设置配置

        Returns:
            Dict[str, Any]: 设置配置字典
        """
        return self._config.get("settings", {})

    def set_settings(self, settings: Dict[str, Any]):
        """设置设置配置

        Args:
            settings: 设置配置字典
        """
        self._config["settings"] = settings

    def get_window_config(self) -> Dict[str, Any]:
        """获取窗口配置

        Returns:
            Dict[str, Any]: 窗口配置字典
        """
        return self._config.get("window", {})

    def set_window_config(self, window_config: Dict[str, Any]):
        """设置窗口配置

        Args:
            window_config: 窗口配置字典
        """
        self._config["window"] = window_config


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例

    Returns:
        ConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
