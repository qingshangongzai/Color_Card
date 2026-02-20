# 标准库导入
import hashlib
from typing import List, Optional

# 第三方库导入
from PySide6.QtGui import QImage

# 项目模块导入
from .cache_base import BaseCache


class HistogramCache(BaseCache):
    """直方图数据缓存管理器

    使用LRU(最近最少使用)策略管理直方图计算结果的缓存，
    在切换标签页后能够快速恢复直方图显示，无需重新计算。

    缓存键格式: (image_key, histogram_type)
    图片指纹基于图片尺寸和像素采样生成。
    """

    def __init__(self, max_size: int = 50):
        """初始化直方图缓存管理器

        Args:
            max_size: 最大缓存条目数，默认50
        """
        super().__init__(max_size)

    def get(self, image_key: str, histogram_type: str) -> Optional[List[int]]:
        """获取缓存的直方图数据

        Args:
            image_key: 图片指纹键
            histogram_type: 直方图类型 ('luminance', 'rgb', 'hue')

        Returns:
            Optional[List[int]]: 缓存的直方图数据，如果缓存未命中则返回None
        """
        key = self._get_key(image_key, histogram_type)
        return self._get_from_cache(key)

    def set(
        self,
        image_key: str,
        histogram_type: str,
        histogram_data: List[int]
    ) -> None:
        """存储直方图数据到缓存

        Args:
            image_key: 图片指纹键
            histogram_type: 直方图类型 ('luminance', 'rgb', 'hue')
            histogram_data: 直方图数据列表
        """
        key = self._get_key(image_key, histogram_type)
        self._set_to_cache(key, histogram_data)

    def clear_by_image(self, image_key: str) -> None:
        """清除指定图片的所有直方图缓存

        Args:
            image_key: 图片指纹键
        """
        keys_to_remove = [
            key for key in self._cache.keys()
            if key[0] == image_key
        ]
        for key in keys_to_remove:
            del self._cache[key]

    def _get_key(self, image_key: str, histogram_type: str) -> tuple:
        """生成缓存键

        Args:
            image_key: 图片指纹键
            histogram_type: 直方图类型

        Returns:
            tuple: 缓存键元组
        """
        return (image_key, histogram_type)


class ImageFingerprintGenerator:
    """图片指纹生成器

    基于图片尺寸和像素采样生成唯一指纹，用于直方图缓存键。
    指纹生成速度快，能够区分不同的图片。
    """

    @staticmethod
    def generate(image: QImage) -> str:
        """生成图片指纹

        使用图片尺寸和采样像素的哈希值生成指纹。
        采样点均匀分布在图片上，确保指纹的唯一性。

        Args:
            image: 输入图片

        Returns:
            str: 图片指纹字符串
        """
        if image.isNull():
            return ""

        width = image.width()
        height = image.height()

        # 采样点数量（固定9个点：四角+四边中点+中心）
        sample_points = [
            (0, 0),  # 左上角
            (width // 2, 0),  # 上边中点
            (width - 1, 0),  # 右上角
            (0, height // 2),  # 左边中点
            (width // 2, height // 2),  # 中心
            (width - 1, height // 2),  # 右边中点
            (0, height - 1),  # 左下角
            (width // 2, height - 1),  # 下边中点
            (width - 1, height - 1),  # 右下角
        ]

        # 收集采样像素值
        samples = []
        for x, y in sample_points:
            if 0 <= x < width and 0 <= y < height:
                pixel = image.pixel(x, y)
                samples.append(pixel)

        # 生成哈希
        data = f"{width}x{height}:" + ",".join(str(s) for s in samples)
        return hashlib.md5(data.encode()).hexdigest()


# 全局缓存实例
_histogram_cache: Optional[HistogramCache] = None


def get_histogram_cache() -> HistogramCache:
    """获取全局直方图缓存实例

    Returns:
        HistogramCache: 全局直方图缓存实例
    """
    global _histogram_cache
    if _histogram_cache is None:
        _histogram_cache = HistogramCache()
    return _histogram_cache


def clear_histogram_cache() -> None:
    """清空全局直方图缓存"""
    global _histogram_cache
    if _histogram_cache is not None:
        _histogram_cache.clear()


def generate_image_fingerprint(image: QImage) -> str:
    """生成图片指纹

    便捷函数，直接调用 ImageFingerprintGenerator.generate

    Args:
        image: 输入图片

    Returns:
        str: 图片指纹字符串
    """
    return ImageFingerprintGenerator.generate(image)
