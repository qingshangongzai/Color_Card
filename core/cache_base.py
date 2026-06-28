from __future__ import annotations

# 标准库导入
from collections import OrderedDict
from typing import Any


class BaseCache:
    """缓存基类，提供LRU机制和通用功能

    使用LRU(最近最少使用)策略管理缓存数据，
    子类只需实现特定的缓存键生成逻辑。

    Attributes:
        _cache: 有序字典，存储缓存数据
        _max_size: 最大缓存条目数
    """

    def __init__(self, max_size: int = 100):
        """初始化缓存基类

        Args:
            max_size: 最大缓存条目数
        """
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size

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

    def _get_from_cache(self, key: tuple) -> Any | None:
        """从缓存获取数据，内部方法

        Args:
            key: 缓存键

        Returns:
            Any | None: 缓存数据，未命中返回None
        """
        if key in self._cache:
            # 移动到末尾（最近使用）
            self._cache.move_to_end(key)
            return self._cache[key]

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
