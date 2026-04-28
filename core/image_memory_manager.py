"""图片内存管理模块

管理ImageData的内存使用，实现LRU缓存策略，
限制最大内存占用，自动清理旧图片。
"""

# 标准库导入
import gc
import time
from collections import OrderedDict
from typing import Dict, Optional, Tuple

# 第三方库导入

# 项目模块导入
from .image_service import ImageData


class ImageMemoryManager:
    """图片内存管理器

    管理ImageData的内存使用，实现LRU缓存策略，
    限制最大内存占用，自动清理旧图片。

    Attributes:
        max_memory: 最大内存限制（字节）
        current_memory: 当前内存占用（字节）
        cache_hits: 缓存命中次数
        cache_misses: 缓存未命中次数
        evictions: 清理次数
    """

    def __init__(self, max_memory_mb: int = 500):
        """初始化内存管理器

        Args:
            max_memory_mb: 最大内存限制（MB），默认500MB
        """
        self._max_memory: int = max_memory_mb * 1024 * 1024
        self._current_memory: int = 0
        self._images: OrderedDict[str, Tuple[ImageData, int, float]] = (
            OrderedDict()
        )

        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._evictions: int = 0

    def add_image(
        self, source_id: str, image_data: ImageData
    ) -> None:
        """添加图片到内存管理器

        如果内存超过限制，自动清理最久未使用的图片。

        Args:
            source_id: 图片唯一标识（如文件路径）
            image_data: ImageData 对象
        """
        if image_data.display_pixmap.isNull() or image_data.display_image.isNull():
            return

        size = self._calculate_size(image_data)

        if source_id in self._images:
            self._remove_image(source_id)

        while (
            self._current_memory + size > self._max_memory
            and self._images
        ):
            self._evict_oldest()

        timestamp = time.time()
        self._images[source_id] = (image_data, size, timestamp)
        self._current_memory += size

    def get_image(
        self, source_id: str
    ) -> Optional[ImageData]:
        """获取图片

        更新访问时间，实现LRU策略。

        Args:
            source_id: 图片唯一标识

        Returns:
            ImageData 对象，如果不存在则返回 None
        """
        if source_id not in self._images:
            self._cache_misses += 1
            return None

        image_data, size, _ = self._images[source_id]
        self._images[source_id] = (image_data, size, time.time())
        self._images.move_to_end(source_id)

        self._cache_hits += 1
        return image_data

    def remove_image(self, source_id: str) -> bool:
        """移除指定图片

        Args:
            source_id: 图片唯一标识

        Returns:
            True如果成功移除，False如果不存在
        """
        if source_id not in self._images:
            return False

        self._remove_image(source_id)
        return True

    def _remove_image(self, source_id: str) -> None:
        """内部方法：移除图片并释放内存

        Args:
            source_id: 图片唯一标识
        """
        if source_id not in self._images:
            return

        image_data, size, _ = self._images.pop(source_id)
        self._current_memory -= size

        del image_data

    def _evict_oldest(self) -> None:
        """清理最久未使用的图片"""
        if not self._images:
            return

        oldest_id = next(iter(self._images))
        self._remove_image(oldest_id)
        self._evictions += 1

    def clear_all(self) -> None:
        """清空所有图片"""
        for source_id in list(self._images.keys()):
            self._remove_image(source_id)

        self._images.clear()
        self._current_memory = 0

        gc.collect()

    def _calculate_size(
        self, image_data: ImageData
    ) -> int:
        """计算图片内存占用

        Args:
            image_data: ImageData 对象

        Returns:
            内存占用（字节）
        """
        image_size = image_data.display_image.sizeInBytes()
        pixmap_overhead = int(image_size * 1.1)
        pixels_size = 0
        if image_data.original_pixels is not None:
            pixels_size = image_data.original_pixels.nbytes
        return image_size + pixmap_overhead + pixels_size

    def get_memory_stats(self) -> Dict[str, int]:
        """获取内存统计信息

        Returns:
            包含以下字段的字典：
            - current_memory_mb: 当前内存占用（MB）
            - max_memory_mb: 最大内存限制（MB）
            - image_count: 缓存图片数量
            - cache_hits: 缓存命中次数
            - cache_misses: 缓存未命中次数
            - evictions: 清理次数
        """
        return {
            "current_memory_mb": self._current_memory // (1024 * 1024),
            "max_memory_mb": self._max_memory // (1024 * 1024),
            "image_count": len(self._images),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "evictions": self._evictions,
        }

    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率

        Returns:
            缓存命中率（0.0-1.0）
        """
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total


# 全局内存管理器实例
_memory_manager: Optional[ImageMemoryManager] = None


def get_memory_manager() -> ImageMemoryManager:
    """获取全局内存管理器实例

    Returns:
        ImageMemoryManager: 全局内存管理器实例
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ImageMemoryManager()
    return _memory_manager


def set_memory_limit(max_memory_mb: int) -> None:
    """设置内存限制

    Args:
        max_memory_mb: 最大内存限制（MB）
    """
    manager = get_memory_manager()
    manager._max_memory = max_memory_mb * 1024 * 1024


__all__ = [
    "ImageMemoryManager",
    "get_memory_manager",
    "set_memory_limit",
]
