# 标准库导入
from collections import OrderedDict
from typing import Optional, Any


class BaseCache:
    """缓存基类，提供LRU机制和通用功能

    使用LRU(最近最少使用)策略管理缓存数据，
    子类只需实现特定的缓存键生成逻辑。

    Attributes:
        _cache: 有序字典，存储缓存数据
        _max_size: 最大缓存条目数
        _hits: 缓存命中次数
        _misses: 缓存未命中次数
    """

    def __init__(self, max_size: int = 100):
        """初始化缓存基类

        Args:
            max_size: 最大缓存条目数
        """
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _get_key(self, *args) -> tuple:
        """生成缓存键，子类必须重写

        Args:
            *args: 缓存参数

        Returns:
            tuple: 缓存键元组

        Raises:
            NotImplementedError: 子类未实现此方法
        """
        raise NotImplementedError("子类必须实现 _get_key 方法")

    def _get_from_cache(self, key: tuple) -> Optional[Any]:
        """从缓存获取数据，内部方法

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存数据，未命中返回None
        """
        if key in self._cache:
            # 移动到末尾（最近使用）
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

        self._misses += 1
        return None

    def _set_to_cache(self, key: tuple, value: Any) -> None:
        """存储数据到缓存，内部方法

        Args:
            key: 缓存键
            value: 要存储的数据
        """
        # 如果已存在，先删除旧值
        if key in self._cache:
            del self._cache[key]

        # 检查是否需要淘汰
        while len(self._cache) >= self._max_size:
            # 淘汰最久未使用的（第一个）
            self._cache.popitem(last=False)

        # 添加新值到末尾（最近使用）
        self._cache[key] = value

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            dict: 包含命中率、命中次数、未命中次数、缓存大小的字典
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            'hit_rate': hit_rate,
            'hits': self._hits,
            'misses': self._misses,
            'size': len(self._cache),
            'max_size': self._max_size
        }
