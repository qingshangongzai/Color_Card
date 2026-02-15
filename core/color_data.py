# 标准库导入
import json
import os
import random


class ColorSource:
    """配色源类（直接读取新格式JSON）"""
    
    def __init__(self, json_data: dict):
        self._data = json_data
        self._id = json_data.get("id", "")
        self._name = json_data.get("name_zh", json_data.get("name", ""))
        self._description = json_data.get("description", "")
        self._author = json_data.get("author", "")
        self._category = json_data.get("category", "")
        self._palettes = json_data.get("palettes", [])
        self._groups = json_data.get("groups", [])
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def author(self) -> str:
        return self._author
    
    @property
    def category(self) -> str:
        return self._category
    
    @property
    def has_groups(self) -> bool:
        return len(self._groups) > 0
    
    @property
    def total_palettes(self) -> int:
        return len(self._palettes)
    
    @property
    def total_groups(self) -> int:
        return len(self._groups)
    
    def get_groups(self) -> list:
        """获取分组列表
        
        Returns:
            list: 分组列表，每个元素为 {"name": 分组名称}
        """
        return [{"name": g["name"]} for g in self._groups]
    
    def get_palettes_for_group(self, group_index: int) -> list:
        """获取指定分组下的配色
        
        Args:
            group_index: 分组索引
        
        Returns:
            list: 配色列表
        """
        if group_index < 0 or group_index >= len(self._groups):
            return self._palettes
        indices = self._groups[group_index].get("indices", [])
        return [self._palettes[i] for i in indices if i < len(self._palettes)]
    
    def get_all_palettes(self) -> list:
        """获取所有配色（无分组时使用）
        
        Returns:
            list: 所有配色列表
        """
        return self._palettes
    
    def get_group_info(self, group_index: int) -> dict:
        """获取分组信息
        
        Args:
            group_index: 分组索引
        
        Returns:
            dict: 分组信息，包含 name, total_items, indices
        """
        if group_index < 0 or group_index >= len(self._groups):
            return {
                "name": "全部",
                "total_items": len(self._palettes),
                "indices": list(range(len(self._palettes)))
            }
        group = self._groups[group_index]
        indices = group.get("indices", [])
        return {
            "name": group["name"],
            "total_items": len(indices),
            "indices": indices,
        }
    
    def get_palettes_for_group_batch(self, group_index: int, start: int, count: int) -> list:
        """分批获取指定分组下的配色
        
        Args:
            group_index: 分组索引
            start: 起始索引（在分组内的相对索引）
            count: 获取数量
        
        Returns:
            list: 配色列表
        """
        if group_index < 0 or group_index >= len(self._groups):
            palettes = self._palettes
        else:
            indices = self._groups[group_index].get("indices", [])
            palettes = [self._palettes[i] for i in indices if i < len(self._palettes)]
        
        end = min(start + count, len(palettes))
        return palettes[start:end]


class ColorSourceRegistry:
    """配色源注册表（单例模式）"""
    
    _instance = None
    _sources = {}
    _loaded = False
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if not ColorSourceRegistry._loaded:
            self._discover_sources()
            ColorSourceRegistry._loaded = True
    
    def _discover_sources(self):
        """自动发现 color_data/ 目录下的 JSON 文件"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        color_data_dir = os.path.join(project_root, 'color_data')
        
        if not os.path.exists(color_data_dir):
            return
        
        for filename in os.listdir(color_data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(color_data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if 'id' in data and 'palettes' in data:
                        source = ColorSource(data)
                        ColorSourceRegistry._sources[source.id] = source
                except (OSError, json.JSONDecodeError) as e:
                    print(f"加载配色源失败 {filename}: {e}")
    
    def get(self, source_id: str) -> ColorSource:
        """获取指定配色源
        
        Args:
            source_id: 配色源ID
        
        Returns:
            ColorSource: 配色源对象，不存在则返回 None
        """
        return ColorSourceRegistry._sources.get(source_id)
    
    def get_all_ids(self) -> list:
        """获取所有配色源ID
        
        Returns:
            list: 配色源ID列表
        """
        return list(ColorSourceRegistry._sources.keys())
    
    def get_all_sources(self) -> list:
        """获取所有配色源
        
        Returns:
            list: ColorSource 对象列表
        """
        return list(ColorSourceRegistry._sources.values())


def get_color_source_registry() -> ColorSourceRegistry:
    """获取配色源注册表单例
    
    Returns:
        ColorSourceRegistry: 注册表实例
    """
    return ColorSourceRegistry.get_instance()


def get_color_source(source_id: str) -> ColorSource:
    """获取指定配色源
    
    Args:
        source_id: 配色源ID
    
    Returns:
        ColorSource: 配色源对象，不存在则返回 None
    """
    return get_color_source_registry().get(source_id)


def get_all_color_sources() -> list:
    """获取所有配色源
    
    Returns:
        list: ColorSource 对象列表
    """
    return get_color_source_registry().get_all_sources()


def get_all_palettes():
    """获取所有配色方案（统一格式）
    
    将所有配色源转换为统一的配色组格式，便于随机选择和展示。
    
    Returns:
        list: 配色组列表，每个元素为字典：
            {
                "id": 唯一标识,
                "name": 显示名称,
                "source": 来源ID,
                "colors": 颜色值列表,
                "color_count": 颜色数量
            }
    """
    all_palettes = []
    for source in get_all_color_sources():
        for i, palette in enumerate(source.get_all_palettes()):
            colors = palette.get("colors", [])
            if colors:
                all_palettes.append({
                    "id": f"{source.id}_{i}",
                    "name": palette.get("name", f"配色 #{i+1}"),
                    "source": source.id,
                    "colors": colors,
                    "color_count": len(colors)
                })
    return all_palettes


def get_random_palettes(count=10):
    """随机获取指定数量的配色方案
    
    Args:
        count: 需要返回的配色组数量（默认10）
    
    Returns:
        list: 随机选择的配色组列表
    """
    all_palettes = get_all_palettes()
    total = len(all_palettes)
    
    if total == 0:
        return []
    
    if count >= total:
        return all_palettes
    
    return random.sample(all_palettes, count)
