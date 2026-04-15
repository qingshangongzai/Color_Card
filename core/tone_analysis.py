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

        tone_key, tone_range = self._classify_tone(
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
            peak_position=peak_position
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
                       hist: np.ndarray) -> Tuple[ToneKey, ToneRange]:
        """判断影调类型

        Args:
            peak: 波峰位置
            min_val: 最小亮度值
            max_val: 最大亮度值
            shadows: 暗部占比
            highlights: 亮部占比
            hist: 直方图数据

        Returns:
            Tuple[ToneKey, ToneRange]: 基调、跨度
        """
        spread = max_val - min_val

        # 全长调判断
        if self._is_full_tone(hist, shadows, highlights, min_val, max_val):
            return ToneKey.FULL, ToneRange.LONG

        # 基调判断
        tone_key = self._get_tone_key(peak)

        # 跨度判断
        tone_range = self._get_tone_range(spread)

        return tone_key, tone_range

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

    def _get_tone_key(self, peak: float) -> ToneKey:
        """根据波峰位置确定基调"""
        if peak >= self.KEY_HIGH_MIN:
            return ToneKey.HIGH
        elif peak <= self.KEY_LOW_MAX:
            return ToneKey.LOW
        else:
            return ToneKey.MID

    def _get_tone_range(self, spread: int) -> ToneRange:
        """根据分布宽度确定跨度"""
        if spread >= self.RANGE_LONG:
            return ToneRange.LONG
        elif spread >= self.RANGE_MEDIUM:
            return ToneRange.MEDIUM
        return ToneRange.SHORT



    def _rgb_to_gray(self, img_array: np.ndarray) -> np.ndarray:
        """RGB 转灰度 (Rec. 709 标准)"""
        return (0.299 * img_array[:, :, 0] +
                0.587 * img_array[:, :, 1] +
                0.114 * img_array[:, :, 2]).astype(np.uint8)

    def get_gray_image(self, img_array: np.ndarray) -> np.ndarray:
        """获取灰度图像"""
        return self._rgb_to_gray(img_array)
