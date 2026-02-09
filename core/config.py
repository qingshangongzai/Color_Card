# 标准库导入
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# 项目模块导入
from version import version_manager


class ConfigManager:
    """配置管理器，处理应用程序配置的加载和保存"""

    CONFIG_VERSION: str = "1.0"
    CONFIG_DIR_NAME: str = ".color_card"
    CONFIG_FILE_NAME: str = "config.json"

    def __init__(self) -> None:
        """初始化配置管理器"""
        self._config_path: Path = self._get_config_path()
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

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        config_dir = self._config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

    def _load_default_config(self) -> None:
        """加载默认配置"""
        self._config = {
            "version": self.CONFIG_VERSION,
            "app_version": version_manager.get_version(),
            "settings": {
                "hex_visible": True,
                "color_modes": ["HSB", "LAB"],
                "color_sample_count": 5,
                "luminance_sample_count": 5,
                "histogram_scaling_mode": "adaptive",
                "color_wheel_mode": "RGB",
                "theme": "auto"
            },
            "scheme": {
                "default_scheme": "monochromatic",
                "color_count": 5,
                "brightness_adjustment": 0
            },
            "window": {
                "width": 940,
                "height": 660,
                "is_maximized": False
            },
            "favorites": []
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

            # 数据迁移：将旧版本的 schemes 和 extracts 合并到 favorites
            self._migrate_favorites_data(loaded_config)

            # 合并加载的配置和默认配置（保留默认值作为后备）
            self._merge_config(self._config, loaded_config)

        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"加载配置文件失败: {e}")
            # 使用默认配置

        return self._config

    def _migrate_favorites_data(self, loaded_config: Dict[str, Any]) -> None:
        """迁移旧版本的收藏数据到新格式

        Args:
            loaded_config: 从文件加载的配置字典
        """
        if 'favorites' in loaded_config and loaded_config['favorites']:
            return

        favorites = []

        # 迁移 schemes
        if 'schemes' in loaded_config:
            for scheme in loaded_config['schemes']:
                if isinstance(scheme, dict):
                    favorites.append(scheme)

        # 迁移 extracts
        if 'extracts' in loaded_config:
            for extract in loaded_config['extracts']:
                if isinstance(extract, dict):
                    # 确保 extract 有正确的 source 字段
                    extract['source'] = 'color_extract'
                    favorites.append(extract)

        # 更新 favorites
        if favorites:
            loaded_config['favorites'] = favorites
            # 清理旧数据
            if 'schemes' in loaded_config:
                del loaded_config['schemes']
            if 'extracts' in loaded_config:
                del loaded_config['extracts']
            if 'colors' in loaded_config:
                del loaded_config['colors']
            if 'display_settings' in loaded_config:
                del loaded_config['display_settings']

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
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

    def save(self, config: Optional[Dict[str, Any]] = None) -> None:
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

    def set(self, key: str, value: Any) -> None:
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

    def set_settings(self, settings: Dict[str, Any]) -> None:
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

    def set_window_config(self, window_config: Dict[str, Any]) -> None:
        """设置窗口配置

        Args:
            window_config: 窗口配置字典
        """
        self._config["window"] = window_config

    def get_favorites(self) -> list:
        """获取收藏列表

        Returns:
            list: 收藏配色方案列表
        """
        return self._config.get("favorites", [])

    def add_favorite(self, favorite_data: Dict[str, Any]) -> str:
        """添加收藏

        Args:
            favorite_data: 收藏数据字典

        Returns:
            str: 收藏ID
        """
        if "favorites" not in self._config:
            self._config["favorites"] = []

        favorites = self._config["favorites"]
        favorite_id = favorite_data.get("id", "")

        if favorite_id and any(f.get("id") == favorite_id for f in favorites):
            return favorite_id

        self._config["favorites"].append(favorite_data)
        return favorite_id

    def delete_favorite(self, favorite_id: str) -> bool:
        """删除收藏

        Args:
            favorite_id: 收藏ID

        Returns:
            bool: 是否删除成功
        """
        if "favorites" not in self._config:
            return False

        favorites = self._config["favorites"]
        original_count = len(favorites)
        self._config["favorites"] = [f for f in favorites if f.get("id") != favorite_id]

        return len(self._config["favorites"]) < original_count

    def rename_favorite(self, favorite_id: str, new_name: str) -> bool:
        """重命名收藏

        Args:
            favorite_id: 收藏ID
            new_name: 新名称

        Returns:
            bool: 是否重命名成功
        """
        if "favorites" not in self._config:
            return False

        favorites = self._config["favorites"]
        for fav in favorites:
            if fav.get("id") == favorite_id:
                fav["name"] = new_name
                return True

        return False

    def clear_favorites(self) -> None:
        """清空所有收藏"""
        self._config["favorites"] = []

    def export_favorites(self, file_path: str) -> bool:
        """导出收藏到文件

        Args:
            file_path: 导出文件路径

        Returns:
            bool: 是否导出成功
        """
        try:
            favorites = self.get_favorites()
            export_data = {
                "version": "1.0",
                "export_time": datetime.now().isoformat(),
                "favorites": favorites
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
            return True
        except (IOError, OSError) as e:
            print(f"导出收藏失败: {e}")
            return False

    def import_favorites(self, file_path: str, mode: str = 'append') -> tuple:
        """从文件导入收藏

        Args:
            file_path: 导入文件路径
            mode: 导入模式，'append' 追加到现有收藏，'replace' 替换现有收藏

        Returns:
            tuple: (是否成功, 导入数量, 错误信息)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # 验证文件格式
            if not isinstance(import_data, dict):
                return False, 0, "文件格式错误：根对象必须是字典"

            imported_favorites = import_data.get("favorites", [])
            if not isinstance(imported_favorites, list):
                return False, 0, "文件格式错误：favorites 必须是列表"

            # 验证每个收藏项的格式
            valid_favorites = []
            for fav in imported_favorites:
                if isinstance(fav, dict) and "colors" in fav:
                    # 确保有 id
                    if "id" not in fav:
                        fav["id"] = str(uuid.uuid4())
                    valid_favorites.append(fav)

            if mode == 'replace':
                self._config["favorites"] = valid_favorites
            else:  # append
                existing_ids = {f.get("id") for f in self._config.get("favorites", [])}
                for fav in valid_favorites:
                    if fav.get("id") not in existing_ids:
                        self._config["favorites"].append(fav)
                        existing_ids.add(fav.get("id"))

            return True, len(valid_favorites), ""

        except json.JSONDecodeError as e:
            return False, 0, f"JSON 解析错误: {e}"
        except (IOError, OSError) as e:
            return False, 0, f"文件读取错误: {e}"
        except Exception as e:
            return False, 0, f"导入失败: {e}"

    def update_favorite_color(self, favorite_id: str, color_index: int, color_info: dict) -> bool:
        """更新收藏中的颜色

        Args:
            favorite_id: 收藏ID
            color_index: 颜色索引
            color_info: 新的颜色信息

        Returns:
            bool: 是否更新成功
        """
        if "favorites" not in self._config:
            return False

        favorites = self._config["favorites"]
        for fav in favorites:
            if fav.get("id") == favorite_id:
                colors = fav.get("colors", [])
                if 0 <= color_index < len(colors):
                    colors[color_index] = color_info
                    return True

        return False

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
