"""图片内存管理模块

管理QPixmap和QImage的内存使用，实现LRU缓存策略，
限制最大内存占用，自动清理旧图片。
"""

# 标准库导入
import gc
import time
from collections import OrderedDict
from typing import Dict, Optional, Tuple

# 第三方库导入
from PySide6.QtGui import QImage, QPixmap


class ImageMemoryManager:
    """图片内存管理器

    管理QPixmap和QImage的内存使用，实现LRU缓存策略，
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
        self._images: OrderedDict[str, Tuple[QPixmap, QImage, int, float]] = (
            OrderedDict()
        )

        # 统计信息
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._evictions: int = 0

    def add_image(
        self, source_id: str, pixmap: QPixmap, image: QImage
    ) -> None:
        """添加图片到内存管理器

        如果内存超过限制，自动清理最久未使用的图片。

        Args:
            source_id: 图片唯一标识（如文件路径）
            pixmap: QPixmap对象
            image: QImage对象
        """
        if pixmap.isNull() or image.isNull():
            return

        # 计算图片内存占用
        size = self._calculate_size(pixmap, image)

        # 如果已存在，先移除旧数据
        if source_id in self._images:
            self._remove_image(source_id)

        # 超过限制时清理旧图片
        while (
            self._current_memory + size > self._max_memory
            and self._images
        ):
            self._evict_oldest()

        # 添加新图片
        timestamp = time.time()
        self._images[source_id] = (pixmap, image, size, timestamp)
        self._current_memory += size

    def get_image(
        self, source_id: str
    ) -> Optional[Tuple[QPixmap, QImage]]:
        """获取图片

        更新访问时间，实现LRU策略。

        Args:
            source_id: 图片唯一标识

        Returns:
            (QPixmap, QImage) 元组，如果不存在则返回None
        """
        if source_id not in self._images:
            self._cache_misses += 1
            return None

        # 更新访问时间
        pixmap, image, size, _ = self._images[source_id]
        self._images[source_id] = (pixmap, image, size, time.time())

        # 移动到末尾（最新使用）
        self._images.move_to_end(source_id)

        self._cache_hits += 1
        return pixmap, image

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

        pixmap, image, size, _ = self._images.pop(source_id)
        self._current_memory -= size

        # 直接赋值为 None，让 Python 垃圾回收处理
        # 注意：QPixmap 和 QImage 没有 detach() 方法
        del pixmap
        del image

    def _evict_oldest(self) -> None:
        """清理最久未使用的图片"""
        if not self._images:
            return

        # 获取最久未使用的图片（OrderedDict的第一个元素）
        oldest_id = next(iter(self._images))
        self._remove_image(oldest_id)
        self._evictions += 1

    def clear_all(self) -> None:
        """清空所有图片"""
        # 显式释放所有Qt对象
        for source_id in list(self._images.keys()):
            self._remove_image(source_id)

        self._images.clear()
        self._current_memory = 0

        # 触发垃圾回收
        gc.collect()

    def _calculate_size(
        self, pixmap: QPixmap, image: QImage
    ) -> int:
        """计算图片内存占用

        Args:
            pixmap: QPixmap对象
            image: QImage对象

        Returns:
            内存占用（字节）
        """
        # QPixmap 没有 sizeInBytes() 方法，使用 QImage 计算
        # QPixmap 和 QImage 共享相同的像素数据时内存占用相近
        image_size = image.sizeInBytes()
        # QPixmap 通常有一些额外开销，估算为 image 的 1.1 倍
        return int(image_size * 1.1)

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
