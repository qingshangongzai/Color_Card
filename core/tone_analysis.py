"""影调分析服务"""

from dataclasses import dataclass
from typing import Tuple

import numpy as np


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
    tone_type: str
    histogram: np.ndarray


class ToneAnalysisService:
    """影调分析服务"""

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

        tone_type = self._classify_tone(mean, shadows, highlights, std, midtones)

        hist, _ = np.histogram(gray, bins=256, range=(0, 256))

        return ToneAnalysisResult(
            mean=mean, median=median, std=std,
            min_val=min_val, max_val=max_val,
            shadows=shadows, midtones=midtones,
            highlights=highlights, tone_type=tone_type,
            histogram=hist
        )

    def _rgb_to_gray(self, img_array: np.ndarray) -> np.ndarray:
        """RGB 转灰度 (Rec. 709 标准)

        Args:
            img_array: RGB 图片数组 (H, W, 3)

        Returns:
            灰度数组 (H, W)
        """
        return (0.299 * img_array[:, :, 0] +
                0.587 * img_array[:, :, 1] +
                0.114 * img_array[:, :, 2]).astype(np.uint8)

    def _classify_tone(self, mean: float, shadows: float, highlights: float,
                       std: float, midtones: float) -> str:
        """判断影调类型

        Args:
            mean: 平均亮度
            shadows: 暗部占比
            highlights: 亮部占比
            std: 标准差
            midtones: 中间调占比

        Returns:
            影调类型字符串
        """
        if mean > 180 and shadows < 5:
            return "高调 (High-key)"
        elif mean < 80 and highlights < 5:
            return "低调 (Low-key)"
        elif 110 <= mean <= 150 and 40 <= midtones <= 70:
            return "中调 (Mid-tone)"
        elif std < 40:
            return "短调 - 低对比度"
        elif std > 80:
            return "长调 - 高对比度"
        else:
            return "正常调"

    def get_gray_image(self, img_array: np.ndarray) -> np.ndarray:
        """获取灰度图像

        Args:
            img_array: RGB 图片数组 (H, W, 3)

        Returns:
            灰度数组 (H, W)
        """
        return self._rgb_to_gray(img_array)
