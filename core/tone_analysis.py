"""影调分析服务"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

import numpy as np


class ToneKey(str, Enum):
    """影调基调"""
    HIGH = "high"
    MID = "mid"
    LOW = "low"
    FULL = "full"


class ToneRange(str, Enum):
    """影调跨度"""
    LONG = "long"
    MEDIUM = "medium"
    SHORT = "short"


@dataclass
class ToneAnalysisResult:
    """影调分析结果"""
    mean: float
    median: float
    std: float
    min_val: int
    max_val: int
    shadows: float
    midtones: float
    highlights: float
    tone_key: ToneKey
    tone_range: ToneRange
    histogram: np.ndarray
    peak_position: float
    tone_key_confidence: float
    tone_range_confidence: float


class ToneAnalysisService:
    """影调分析服务"""

    # 基调判断阈值
    KEY_HIGH_MIN = 160
    KEY_MID_MIN = 80
    KEY_MID_MAX = 176
    KEY_LOW_MAX = 96

    # 跨度判断阈值
    RANGE_LONG = 180
    RANGE_MEDIUM = 100

    # 全长调判断阈值
    MIN_ZONE_PERCENTAGE = 15
    MIN_RANGE_THRESHOLD = 30
    MAX_RANGE_THRESHOLD = 225
    U_SHAPE_RATIO = 0.7

    # 边界缓冲区（用于置信度计算）
    KEY_BUFFER = 15  # 基调边界缓冲带
    RANGE_BUFFER = 20  # 跨度边界缓冲带

    def analyze_from_array(self, img_array: np.ndarray) -> ToneAnalysisResult:
        """从 NumPy 数组分析影调

        Args:
            img_array: RGB 图片数组 (H, W, 3)

        Returns:
            ToneAnalysisResult: 分析结果
        """
        gray = self._rgb_to_gray(img_array)

        mean = float(np.mean(gray))
        median = float(np.median(gray))
        std = float(np.std(gray))
        min_val = int(np.min(gray))
        max_val = int(np.max(gray))

        shadows = float(np.sum(gray < 64) / gray.size * 100)
        midtones = float(np.sum((gray >= 64) & (gray < 192)) / gray.size * 100)
        highlights = float(np.sum(gray >= 192) / gray.size * 100)

        hist, _ = np.histogram(gray, bins=256, range=(0, 256))
        peak_position = self._calc_peak_position(hist)

        tone_key, tone_range, key_confidence, range_confidence = self._classify_tone(
            peak_position, min_val, max_val, shadows, highlights, hist
        )

        return ToneAnalysisResult(
            mean=mean, median=median, std=std,
            min_val=min_val, max_val=max_val,
            shadows=shadows, midtones=midtones,
            highlights=highlights,
            tone_key=tone_key,
            tone_range=tone_range,
            histogram=hist,
            peak_position=peak_position,
            tone_key_confidence=key_confidence,
            tone_range_confidence=range_confidence
        )

    def _calc_peak_position(self, hist: np.ndarray) -> float:
        """计算波峰位置（直方图最大值位置）

        Args:
            hist: 直方图数据

        Returns:
            float: 波峰位置
        """
        return float(np.argmax(hist))

    def _classify_tone(self, peak: float, min_val: int, max_val: int,
                       shadows: float, highlights: float,
                       hist: np.ndarray) -> Tuple[ToneKey, ToneRange, float, float]:
        """判断影调类型

        Args:
            peak: 波峰位置
            min_val: 最小亮度值
            max_val: 最大亮度值
            shadows: 暗部占比
            highlights: 亮部占比
            hist: 直方图数据

        Returns:
            Tuple[ToneKey, ToneRange, float, float]: 基调、跨度、基调置信度、跨度置信度
        """
        spread = max_val - min_val

        # 全长调判断
        if self._is_full_tone(hist, shadows, highlights, min_val, max_val):
            return ToneKey.FULL, ToneRange.LONG, 1.0, 1.0

        # 基调判断（带置信度）
        tone_key, key_confidence = self._get_tone_key(peak)

        # 跨度判断（带置信度）
        tone_range, range_confidence = self._get_tone_range(spread)

        return tone_key, tone_range, key_confidence, range_confidence

    def _is_full_tone(self, hist: np.ndarray, shadows: float,
                      highlights: float, min_val: int, max_val: int) -> bool:
        """判断是否为全长调

        特征：两端都有明显像素，中间相对较少
        """
        has_shadows = shadows > self.MIN_ZONE_PERCENTAGE
        has_highlights = highlights > self.MIN_ZONE_PERCENTAGE
        full_range = (min_val < self.MIN_RANGE_THRESHOLD) and (max_val > self.MAX_RANGE_THRESHOLD)

        # U型分布判断
        mid_avg = np.mean(hist[64:192])
        edge_avg = np.mean(np.concatenate([hist[:32], hist[224:]]))

        return has_shadows and has_highlights and full_range and (mid_avg < edge_avg * self.U_SHAPE_RATIO)

    def _get_tone_key(self, peak: float) -> Tuple[ToneKey, float]:
        """根据波峰位置确定基调及置信度

        Args:
            peak: 波峰位置

        Returns:
            Tuple[ToneKey, float]: 基调类型、置信度(0.5-1.0)
        """
        # 高调区域
        if peak >= self.KEY_HIGH_MIN:
            distance = peak - self.KEY_HIGH_MIN
            confidence = 0.5 + 0.5 * min(distance / self.KEY_BUFFER, 1.0)
            return ToneKey.HIGH, confidence

        # 低调区域
        if peak <= self.KEY_LOW_MAX:
            distance = self.KEY_LOW_MAX - peak
            confidence = 0.5 + 0.5 * min(distance / self.KEY_BUFFER, 1.0)
            return ToneKey.LOW, confidence

        # 中调区域
        dist_to_low = peak - self.KEY_LOW_MAX
        dist_to_high = self.KEY_HIGH_MIN - peak

        if dist_to_low < self.KEY_BUFFER and dist_to_low < dist_to_high:
            # 靠近低调边界
            confidence = 0.5 + 0.5 * (dist_to_low / self.KEY_BUFFER)
        elif dist_to_high < self.KEY_BUFFER:
            # 靠近高调边界
            confidence = 0.5 + 0.5 * (dist_to_high / self.KEY_BUFFER)
        else:
            # 中调核心区
            confidence = 1.0

        return ToneKey.MID, confidence

    def _get_tone_range(self, spread: int) -> Tuple[ToneRange, float]:
        """根据分布宽度确定跨度及置信度

        Args:
            spread: 分布宽度(最大-最小)

        Returns:
            Tuple[ToneRange, float]: 跨度类型、置信度(0.5-1.0)
        """
        # 长调区域
        if spread >= self.RANGE_LONG:
            distance = spread - self.RANGE_LONG
            confidence = 0.5 + 0.5 * min(distance / self.RANGE_BUFFER, 1.0)
            return ToneRange.LONG, confidence

        # 短调区域
        if spread < self.RANGE_MEDIUM:
            distance = self.RANGE_MEDIUM - spread
            confidence = 0.5 + 0.5 * min(distance / self.RANGE_BUFFER, 1.0)
            return ToneRange.SHORT, confidence

        # 中调区域
        dist_to_short = spread - self.RANGE_MEDIUM
        dist_to_long = self.RANGE_LONG - spread

        if dist_to_short < self.RANGE_BUFFER and dist_to_short < dist_to_long:
            # 靠近短调边界
            confidence = 0.5 + 0.5 * (dist_to_short / self.RANGE_BUFFER)
        elif dist_to_long < self.RANGE_BUFFER:
            # 靠近长调边界
            confidence = 0.5 + 0.5 * (dist_to_long / self.RANGE_BUFFER)
        else:
            # 中调核心区
            confidence = 1.0

        return ToneRange.MEDIUM, confidence



    def _rgb_to_gray(self, img_array: np.ndarray) -> np.ndarray:
        """RGB 转灰度 (Rec. 709 标准)"""
        return (0.299 * img_array[:, :, 0] +
                0.587 * img_array[:, :, 1] +
                0.114 * img_array[:, :, 2]).astype(np.uint8)

    def get_gray_image(self, img_array: np.ndarray) -> np.ndarray:
        """获取灰度图像"""
        return self._rgb_to_gray(img_array)


# 标准库导入
from typing import Optional

# 项目模块导入
from .cache_base import BaseCache


class ToneAnalysisCache(BaseCache):
    """影调分析缓存管理器

    使用LRU策略管理影调分析结果缓存，避免重复计算同一张图片的明度分析。

    缓存键格式: (image_fingerprint,)
    """

    def __init__(self, max_size: int = 20):
        """初始化影调分析缓存

        Args:
            max_size: 最大缓存条目数，默认20
        """
        super().__init__(max_size)

    def get(self, image_key: str) -> Optional[ToneAnalysisResult]:
        """获取缓存的分析结果

        Args:
            image_key: 图片指纹键

        Returns:
            Optional[ToneAnalysisResult]: 缓存的分析结果，未命中返回None
        """
        key = self._get_key(image_key)
        return self._get_from_cache(key)

    def set(self, image_key: str, result: ToneAnalysisResult) -> None:
        """存储分析结果到缓存

        Args:
            image_key: 图片指纹键
            result: 分析结果
        """
        key = self._get_key(image_key)
        self._set_to_cache(key, result)

    def _get_key(self, image_key: str) -> tuple:
        """生成缓存键

        Args:
            image_key: 图片指纹键

        Returns:
            tuple: 缓存键元组
        """
        return (image_key,)


# 全局缓存实例
_tone_analysis_cache: Optional[ToneAnalysisCache] = None


def get_tone_analysis_cache() -> ToneAnalysisCache:
    """获取全局影调分析缓存实例

    Returns:
        ToneAnalysisCache: 全局缓存实例
    """
    global _tone_analysis_cache
    if _tone_analysis_cache is None:
        _tone_analysis_cache = ToneAnalysisCache()
    return _tone_analysis_cache


def clear_tone_analysis_cache() -> None:
    """清空全局影调分析缓存"""
    global _tone_analysis_cache
    if _tone_analysis_cache is not None:
        _tone_analysis_cache.clear()
