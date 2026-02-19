# 标准库导入
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
                "theme": "auto",
                "color_wheel_labels_visible": True,
                "language": "zh_CN"
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
            "favorites": [],
            "scene_templates": {}
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

    def get_favorite(self, favorite_id: str) -> Optional[Dict[str, Any]]:
        """获取单个收藏项

        Args:
            favorite_id: 收藏ID或名称（当没有id时）

        Returns:
            Optional[Dict[str, Any]]: 收藏数据字典，未找到返回None
        """
        favorites = self._config.get("favorites", [])

        # 先尝试根据id查找
        for favorite in favorites:
            if favorite.get("id") == favorite_id:
                return favorite

        # 如果没有找到，尝试根据name查找（兼容旧数据）
        for favorite in favorites:
            if favorite.get("name") == favorite_id:
                return favorite

        return None

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
            favorite_id: 收藏ID或名称（当没有id时）

        Returns:
            bool: 是否删除成功
        """
        if "favorites" not in self._config:
            return False

        favorites = self._config["favorites"]
        original_count = len(favorites)

        # 先尝试根据id删除
        self._config["favorites"] = [f for f in favorites if f.get("id") != favorite_id]

        # 如果没有删除任何项，尝试根据name删除（兼容旧数据）
        if len(self._config["favorites"]) == original_count:
            self._config["favorites"] = [f for f in favorites if f.get("name") != favorite_id]

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

    def set_favorites(self, favorites: list) -> None:
        """设置收藏列表（用于批量替换）

        Args:
            favorites: 收藏列表
        """
        self._config["favorites"] = favorites

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

    def update_favorite(self, favorite_id: str, palette_data: dict) -> bool:
        """更新整个收藏配色

        Args:
            favorite_id: 收藏ID
            palette_data: 新的配色数据

        Returns:
            bool: 是否更新成功
        """
        if "favorites" not in self._config:
            return False

        favorites = self._config["favorites"]
        for fav in favorites:
            if fav.get("id") == favorite_id:
                fav['name'] = palette_data.get('name', fav.get('name', ''))
                fav['colors'] = palette_data.get('colors', fav.get('colors', []))
                return True

        return False

    def get_scene_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取用户场景模板索引

        Returns:
            Dict[str, List[Dict[str, Any]]]: 场景模板索引字典
        """
        return self._config.get("scene_templates", {})

    def add_scene_template(self, scene_type: str, template_data: Dict[str, Any]) -> bool:
        """添加场景模板

        Args:
            scene_type: 场景类型ID
            template_data: 模板数据（包含 path, name, added_at）

        Returns:
            bool: 是否添加成功
        """
        if "scene_templates" not in self._config:
            self._config["scene_templates"] = {}

        if scene_type not in self._config["scene_templates"]:
            self._config["scene_templates"][scene_type] = []

        templates = self._config["scene_templates"][scene_type]
        template_path = template_data.get("path", "")

        if any(t.get("path") == template_path for t in templates):
            return False

        templates.append(template_data)
        return True

    def remove_scene_template(self, scene_type: str, template_path: str) -> bool:
        """移除场景模板

        Args:
            scene_type: 场景类型ID
            template_path: 模板路径

        Returns:
            bool: 是否移除成功
        """
        if "scene_templates" not in self._config:
            return False

        if scene_type not in self._config["scene_templates"]:
            return False

        templates = self._config["scene_templates"][scene_type]
        original_count = len(templates)
        self._config["scene_templates"][scene_type] = [
            t for t in templates if t.get("path") != template_path
        ]

        return len(self._config["scene_templates"][scene_type]) < original_count

    def get_scene_templates_by_type(self, scene_type: str) -> List[Dict[str, Any]]:
        """获取指定场景类型的模板列表

        Args:
            scene_type: 场景类型ID

        Returns:
            List[Dict[str, Any]]: 模板列表
        """
        templates = self._config.get("scene_templates", {})
        return templates.get(scene_type, [])


class SceneConfigManager:
    """场景配置管理器，处理预览场景配置的加载、保存和导入导出"""

    SCENES_DIR_NAME: str = "preview_scenes"
    SCENES_FILE_NAME: str = "scenes.json"
    USER_SCENES_DIR_NAME: str = "user_scenes"

    def __init__(self) -> None:
        """初始化场景配置管理器"""
        self._scenes_dir: Path = self._get_scenes_dir()
        self._user_scenes_dir: Path = self._scenes_dir / self.USER_SCENES_DIR_NAME
        self._builtin_scenes: List[Dict[str, Any]] = []
        self._user_scenes: List[Dict[str, Any]] = []
        self._loaded: bool = False  # 延迟加载标志

    def _get_scenes_dir(self) -> Path:
        """获取场景配置目录路径

        Returns:
            Path: 场景配置目录的完整路径
        """
        # 从项目根目录查找
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        return project_root / self.SCENES_DIR_NAME

    def _ensure_user_scenes_dir(self) -> None:
        """确保用户场景目录存在"""
        self._user_scenes_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_loaded(self) -> None:
        """确保场景数据已加载（延迟加载）"""
        if not self._loaded:
            self._load_all_scenes()
            self._loaded = True

    def _load_all_scenes(self) -> None:
        """加载所有场景配置（内置 + 用户自定义）"""
        self._load_builtin_scenes()
        self._load_user_scenes()

    def _load_builtin_scenes(self) -> None:
        """加载内置场景配置"""
        scenes_file = self._scenes_dir / self.SCENES_FILE_NAME
        if not scenes_file.exists():
            print(f"内置场景配置文件不存在: {scenes_file}")
            return

        try:
            with open(scenes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._builtin_scenes = data.get("scenes", [])
            print(f"已加载 {len(self._builtin_scenes)} 个内置场景")
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"加载内置场景配置失败: {e}")
            self._builtin_scenes = []

    def _load_user_scenes(self) -> None:
        """加载用户自定义场景配置"""
        self._user_scenes = []

        if not self._user_scenes_dir.exists():
            return

        for scene_file in self._user_scenes_dir.glob("*.json"):
            try:
                with open(scene_file, 'r', encoding='utf-8') as f:
                    scene_config = json.load(f)

                # 验证场景配置格式
                if self._validate_scene_config(scene_config):
                    # 标记为用户场景
                    scene_config["builtin"] = False
                    scene_config["_source_file"] = scene_file.name
                    self._user_scenes.append(scene_config)
                else:
                    print(f"用户场景配置格式无效: {scene_file.name}")

            except (json.JSONDecodeError, IOError, OSError) as e:
                print(f"加载用户场景失败 {scene_file.name}: {e}")

        print(f"已加载 {len(self._user_scenes)} 个用户场景")

    def _validate_scene_config(self, config: Dict[str, Any]) -> bool:
        """验证场景配置格式

        Args:
            config: 场景配置字典

        Returns:
            bool: 是否有效
        """
        required_fields = ["id", "name", "type"]
        return all(field in config for field in required_fields)

    def get_all_scenes(self) -> List[Dict[str, Any]]:
        """获取所有场景配置（内置 + 用户自定义）

        Returns:
            List[Dict[str, Any]]: 所有场景配置列表
        """
        self._ensure_loaded()
        # 合并内置场景和用户场景
        all_scenes = self._builtin_scenes.copy()

        # 检查用户场景ID是否与内置场景冲突
        builtin_ids = {scene["id"] for scene in all_scenes}
        for user_scene in self._user_scenes:
            if user_scene["id"] not in builtin_ids:
                all_scenes.append(user_scene)
            else:
                print(f"用户场景ID '{user_scene['id']}' 与内置场景冲突，已跳过")

        return all_scenes

    def get_builtin_scenes(self) -> List[Dict[str, Any]]:
        """获取内置场景配置

        Returns:
            List[Dict[str, Any]]: 内置场景配置列表
        """
        self._ensure_loaded()
        return self._builtin_scenes.copy()

    def get_user_scenes(self) -> List[Dict[str, Any]]:
        """获取用户自定义场景配置

        Returns:
            List[Dict[str, Any]]: 用户场景配置列表
        """
        self._ensure_loaded()
        return self._user_scenes.copy()

    def get_scene_by_id(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取场景配置

        Args:
            scene_id: 场景ID

        Returns:
            Optional[Dict[str, Any]]: 场景配置，如果不存在则返回None
        """
        self._ensure_loaded()
        # 先在内置场景中查找
        for scene in self._builtin_scenes:
            if scene["id"] == scene_id:
                return scene.copy()

        # 再在用户场景中查找
        for scene in self._user_scenes:
            if scene["id"] == scene_id:
                return scene.copy()

        return None

    def import_scene(self, file_path: str) -> Tuple[bool, str]:
        """导入场景配置文件

        Args:
            file_path: 配置文件路径

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息或成功消息)
        """
        self._ensure_loaded()
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                return False, f"文件不存在: {file_path}"

            with open(source_path, 'r', encoding='utf-8') as f:
                scene_config = json.load(f)

            # 验证配置格式
            if not self._validate_scene_config(scene_config):
                return False, "场景配置格式无效，必须包含 id, name, type 字段"

            # 检查ID是否冲突
            scene_id = scene_config["id"]
            existing_scene = self.get_scene_by_id(scene_id)
            if existing_scene:
                if existing_scene.get("builtin"):
                    return False, f"场景ID '{scene_id}' 与内置场景冲突"
                else:
                    # 覆盖现有用户场景
                    self.delete_user_scene(scene_id)

            # 确保用户场景目录存在
            self._ensure_user_scenes_dir()

            # 生成文件名
            file_name = f"{scene_id}.json"
            target_path = self._user_scenes_dir / file_name

            # 复制文件
            shutil.copy2(source_path, target_path)

            # 重新加载用户场景
            self._load_user_scenes()

            return True, f"场景 '{scene_config.get('name', scene_id)}' 导入成功"

        except json.JSONDecodeError as e:
            return False, f"JSON 解析错误: {e}"
        except (IOError, OSError) as e:
            return False, f"文件操作错误: {e}"
        except Exception as e:
            return False, f"导入失败: {e}"

    def export_scene(self, scene_id: str, file_path: str) -> Tuple[bool, str]:
        """导出场景配置到文件

        Args:
            scene_id: 场景ID
            file_path: 导出文件路径

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息或成功消息)
        """
        scene_config = self.get_scene_by_id(scene_id)
        if not scene_config:
            return False, f"场景 '{scene_id}' 不存在"

        try:
            target_path = Path(file_path)

            # 确保目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # 添加导出元数据
            export_data = scene_config.copy()
            export_data["_export_info"] = {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0"
            }

            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)

            return True, f"场景 '{scene_config.get('name', scene_id)}' 导出成功"

        except (IOError, OSError) as e:
            return False, f"文件写入错误: {e}"
        except Exception as e:
            return False, f"导出失败: {e}"

    def save_user_scene(self, scene_config: Dict[str, Any]) -> Tuple[bool, str]:
        """保存用户自定义场景

        Args:
            scene_config: 场景配置字典

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息或成功消息)
        """
        self._ensure_loaded()
        # 验证配置格式
        if not self._validate_scene_config(scene_config):
            return False, "场景配置格式无效，必须包含 id, name, type 字段"

        scene_id = scene_config["id"]

        # 检查是否与内置场景冲突
        for builtin_scene in self._builtin_scenes:
            if builtin_scene["id"] == scene_id:
                return False, f"场景ID '{scene_id}' 与内置场景冲突"

        try:
            # 确保用户场景目录存在
            self._ensure_user_scenes_dir()

            # 标记为用户场景
            scene_config["builtin"] = False

            # 生成文件名
            file_name = f"{scene_id}.json"
            file_path = self._user_scenes_dir / file_name

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(scene_config, f, ensure_ascii=False, indent=4)

            # 重新加载用户场景
            self._load_user_scenes()

            return True, f"场景 '{scene_config.get('name', scene_id)}' 保存成功"

        except (IOError, OSError) as e:
            return False, f"文件写入错误: {e}"
        except Exception as e:
            return False, f"保存失败: {e}"

    def delete_user_scene(self, scene_id: str) -> bool:
        """删除用户自定义场景

        Args:
            scene_id: 场景ID

        Returns:
            bool: 是否删除成功
        """
        self._ensure_loaded()
        # 检查是否为内置场景
        for builtin_scene in self._builtin_scenes:
            if builtin_scene["id"] == scene_id:
                print(f"不能删除内置场景: {scene_id}")
                return False

        # 查找并删除用户场景文件
        for scene in self._user_scenes:
            if scene["id"] == scene_id:
                source_file = scene.get("_source_file")
                if source_file:
                    file_path = self._user_scenes_dir / source_file
                    if file_path.exists():
                        file_path.unlink()

                # 重新加载用户场景
                self._load_user_scenes()
                return True

        return False

    def reload_scenes(self) -> None:
        """重新加载所有场景配置"""
        self._loaded = True  # 强制设置为已加载状态
        self._load_all_scenes()
        print(f"场景配置已重新加载，共 {len(self.get_all_scenes())} 个场景")


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None
_scene_config_manager: Optional[SceneConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例

    Returns:
        ConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_scene_config_manager() -> SceneConfigManager:
    """获取全局场景配置管理器实例

    Returns:
        SceneConfigManager: 场景配置管理器实例
    """
    global _scene_config_manager
    if _scene_config_manager is None:
        _scene_config_manager = SceneConfigManager()
    return _scene_config_manager


class SceneTypeManager:
    """场景类型管理器 - 从 scenes_data/ 目录加载场景配置和SVG模板"""

    SCENES_DATA_DIR = "scenes_data"
    SCENE_TYPES_FILE = "scene_types.json"

    def __init__(self) -> None:
        """初始化场景类型管理器"""
        self._scenes_data_dir: Path = self._get_scenes_data_dir()
        self._scene_types: List[Dict[str, Any]] = []
        self._loaded: bool = False

    def _get_scenes_data_dir(self) -> Path:
        """获取 scenes_data 目录路径

        Returns:
            Path: scenes_data 目录的完整路径
        """
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        return project_root / self.SCENES_DATA_DIR

    def _ensure_loaded(self) -> None:
        """确保场景数据已加载（延迟加载）"""
        if not self._loaded:
            self._load_scene_types()
            self._loaded = True

    def _load_scene_types(self) -> None:
        """从 scene_types.json 加载场景类型"""
        scene_types_file = self._scenes_data_dir / self.SCENE_TYPES_FILE

        if not scene_types_file.exists():
            print(f"场景类型配置文件不存在: {scene_types_file}")
            self._scene_types = []
            return

        try:
            with open(scene_types_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._scene_types = data.get("scene_types", [])
            print(f"已加载 {len(self._scene_types)} 个场景类型")
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"加载场景类型配置失败: {e}")
            self._scene_types = []

    def get_all_scene_types(self) -> List[Dict[str, Any]]:
        """获取所有场景类型配置

        Returns:
            List[Dict[str, Any]]: 场景类型配置列表
        """
        self._ensure_loaded()
        return self._scene_types.copy()

    def get_scene_type_by_id(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取场景类型配置

        Args:
            scene_id: 场景类型ID

        Returns:
            Optional[Dict[str, Any]]: 场景类型配置，如果不存在则返回None
        """
        self._ensure_loaded()
        for scene_type in self._scene_types:
            if scene_type.get("id") == scene_id:
                return scene_type.copy()
        return None

    def get_builtin_svg_path(self, scene_type: str) -> Optional[str]:
        """获取内置SVG模板路径

        Args:
            scene_type: 场景类型ID（如 'ui', 'web'）

        Returns:
            str: SVG文件路径，如果不存在则返回None
        """
        svg_path = self._scenes_data_dir / scene_type / "default.svg"
        if svg_path.exists():
            return str(svg_path)
        return None

    def get_layout_config(self, scene_type: str) -> Dict[str, Any]:
        """加载场景的布局配置

        Args:
            scene_type: 场景类型ID

        Returns:
            dict: 布局配置字典
        """
        layout_file = self._scenes_data_dir / scene_type / "layout.json"

        if not layout_file.exists():
            return {}

        try:
            with open(layout_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"加载布局配置失败: {e}")
            return {}

    def get_all_templates(self, scene_type: str) -> List[Dict[str, Any]]:
        """获取场景类型的所有模板（内置 + 用户模板）

        Args:
            scene_type: 场景类型ID

        Returns:
            List[Dict[str, Any]]: 模板列表，每个模板包含 path, is_builtin 字段
        """
        templates = []

        # 内置模板 - 加载场景目录下所有svg文件
        scene_dir = self._scenes_data_dir / scene_type
        if scene_dir.exists():
            # 获取所有svg文件，按文件名排序
            svg_files = sorted(scene_dir.glob("*.svg"))
            for svg_path in svg_files:
                templates.append({
                    "path": str(svg_path),
                    "is_builtin": True
                })

        # 用户模板
        config_manager = get_config_manager()
        user_templates = config_manager.get_scene_templates_by_type(scene_type)
        for template in user_templates:
            template_path = template.get("path", "")
            if template_path and Path(template_path).exists():
                templates.append({
                    "path": template_path,
                    "is_builtin": False
                })

        return templates


_scene_type_manager: Optional[SceneTypeManager] = None


def get_scene_type_manager() -> SceneTypeManager:
    """获取全局场景类型管理器实例

    Returns:
        SceneTypeManager: 场景类型管理器实例
    """
    global _scene_type_manager
    if _scene_type_manager is None:
        _scene_type_manager = SceneTypeManager()
    return _scene_type_manager
