# 标准库导入
from typing import List, Tuple, Optional

# 项目模块导入
from .cache_base import BaseCache


class ColorSchemeCache(BaseCache):
    """配色计算结果缓存管理器

    使用LRU(最近最少使用)策略管理配色计算结果的缓存，
    避免相同参数的配色计算重复执行，提升响应速度。

    缓存键格式: (scheme_type, hue_rounded, count, saturation_rounded)
    色相值四舍五入到小数点后1位，平衡缓存命中率和精度。
    """

    def __init__(self, max_size: int = 100):
        """初始化配色缓存管理器

        Args:
            max_size: 最大缓存条目数，默认100
        """
        super().__init__(max_size)

    def get(
        self,
        scheme_type: str,
        hue: float,
        count: int,
        saturation: float
    ) -> Optional[List[Tuple[float, float, float]]]:
        """获取缓存的配色计算结果

        Args:
            scheme_type: 配色方案类型
            hue: 基础色相 (0-360)
            count: 生成颜色数量
            saturation: 基准饱和度 (0-100)

        Returns:
            Optional[List[Tuple[float, float, float]]]: 缓存的HSB颜色列表，
            如果缓存未命中则返回None
        """
        key = self._get_key(scheme_type, hue, count, saturation)
        return self._get_from_cache(key)

    def set(
        self,
        scheme_type: str,
        hue: float,
        count: int,
        saturation: float,
        colors: List[Tuple[float, float, float]]
    ) -> None:
        """存储配色计算结果到缓存

        Args:
            scheme_type: 配色方案类型
            hue: 基础色相 (0-360)
            count: 生成颜色数量
            saturation: 基准饱和度 (0-100)
            colors: HSB颜色列表
        """
        key = self._get_key(scheme_type, hue, count, saturation)
        self._set_to_cache(key, colors)

    def _get_key(
        self,
        scheme_type: str,
        hue: float,
        count: int,
        saturation: float
    ) -> tuple:
        """生成缓存键

        色相值四舍五入到小数点后1位，饱和度四舍五入到整数，
        在保证配色质量的同时提高缓存命中率。

        Args:
            scheme_type: 配色方案类型
            hue: 基础色相 (0-360)
            count: 生成颜色数量
            saturation: 基准饱和度 (0-100)

        Returns:
            tuple: 缓存键元组
        """
        # 色相精度：0.1度
        hue_rounded = round(hue, 1)
        # 饱和度精度：1%
        saturation_rounded = round(saturation)

        return (scheme_type, hue_rounded, count, saturation_rounded)


# 全局缓存实例
_color_scheme_cache: Optional[ColorSchemeCache] = None


def get_color_scheme_cache() -> ColorSchemeCache:
    """获取全局配色缓存实例

    Returns:
        ColorSchemeCache: 全局配色缓存实例
    """
    global _color_scheme_cache
    if _color_scheme_cache is None:
        _color_scheme_cache = ColorSchemeCache()
    return _color_scheme_cache


def clear_color_scheme_cache() -> None:
    """清空全局配色缓存"""
    global _color_scheme_cache
    if _color_scheme_cache is not None:
        _color_scheme_cache.clear()
