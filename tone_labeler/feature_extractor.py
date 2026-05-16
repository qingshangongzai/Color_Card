"""影调特征提取模块

复用主程序的核心模块，提取图片的影调特征用于标注和分析。
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PySide6.QtGui import QImage

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.color import calculate_luminance_from_array, calculate_histogram
from core.tone_analysis import ToneAnalysisService, ToneKey, ToneRange


@dataclass
class ToneFeatures:
    """影调特征数据"""
    mean: float
    median: float
    std: float
    min_val: int
    max_val: int
    P10: int
    P90: int
    peak: int
    span: int
    low_ratio: float
    mid_ratio: float
    high_ratio: float
    histogram: np.ndarray
    tone_key: ToneKey
    tone_range: ToneRange
    tone_name: str
    key_confidence: float
    range_confidence: float


class FeatureExtractor:
    """影调特征提取器"""

    TONE_NAMES = {
        (ToneKey.HIGH, ToneRange.LONG): "高长调",
        (ToneKey.HIGH, ToneRange.MEDIUM): "高中调",
        (ToneKey.HIGH, ToneRange.SHORT): "高短调",
        (ToneKey.MID, ToneRange.LONG): "中长调",
        (ToneKey.MID, ToneRange.MEDIUM): "中中调",
        (ToneKey.MID, ToneRange.SHORT): "中短调",
        (ToneKey.LOW, ToneRange.LONG): "低长调",
        (ToneKey.LOW, ToneRange.MEDIUM): "低中调",
        (ToneKey.LOW, ToneRange.SHORT): "低短调",
        (ToneKey.FULL, ToneRange.LONG): "全长调",
    }

    def __init__(self):
        self._tone_service = ToneAnalysisService()

    def extract_from_image(self, image: QImage) -> Optional[ToneFeatures]:
        """从 QImage 提取影调特征

        Args:
            image: QImage 对象

        Returns:
            ToneFeatures: 影调特征数据，失败返回 None
        """
        if image is None or image.isNull():
            return None

        arr = self._qimage_to_numpy(image)
        if arr is None:
            return None

        return self.extract_from_array(arr)

    def extract_from_array(self, rgb_array: np.ndarray) -> Optional[ToneFeatures]:
        """从 NumPy 数组提取影调特征

        Args:
            rgb_array: RGB 数组 (H, W, 3)

        Returns:
            ToneFeatures: 影调特征数据
        """
        gray = calculate_luminance_from_array(rgb_array)

        mean = float(np.mean(gray))
        median = float(np.median(gray))
        std = float(np.std(gray))
        min_val = int(np.min(gray))
        max_val = int(np.max(gray))

        hist, _ = np.histogram(gray, bins=256, range=(0, 256))
        hist_normalized = hist / hist.sum()

        low_ratio = float(hist_normalized[:86].sum())
        mid_ratio = float(hist_normalized[86:171].sum())
        high_ratio = float(hist_normalized[171:].sum())

        cdf = np.cumsum(hist_normalized)
        P10 = int(np.searchsorted(cdf, 0.10))
        P90 = int(np.searchsorted(cdf, 0.90))

        h_smooth = self._gaussian_smooth(hist_normalized)
        peak = int(np.argmax(h_smooth))

        span = P90 - P10

        result = self._tone_service.analyze_from_array(rgb_array)

        tone_name = self.TONE_NAMES.get(
            (result.tone_key, result.tone_range),
            f"{result.tone_key.value}{result.tone_range.value}"
        )

        return ToneFeatures(
            mean=mean,
            median=median,
            std=std,
            min_val=min_val,
            max_val=max_val,
            P10=P10,
            P90=P90,
            peak=peak,
            span=span,
            low_ratio=low_ratio,
            mid_ratio=mid_ratio,
            high_ratio=high_ratio,
            histogram=hist,
            tone_key=result.tone_key,
            tone_range=result.tone_range,
            tone_name=tone_name,
            key_confidence=result.tone_key_confidence,
            range_confidence=result.tone_range_confidence
        )

    def _qimage_to_numpy(self, image: QImage) -> Optional[np.ndarray]:
        """QImage 转 NumPy 数组"""
        width = image.width()
        height = image.height()

        if image.format() != QImage.Format.Format_RGB888:
            image = image.convertToFormat(QImage.Format.Format_RGB888)

        ptr = image.bits()
        bytes_per_line = image.bytesPerLine()

        if bytes_per_line == width * 3:
            arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 3))
        else:
            arr = np.zeros((height, width, 3), dtype=np.uint8)
            for y in range(height):
                offset = y * bytes_per_line
                row = np.array(ptr[offset:offset + width * 3], dtype=np.uint8)
                arr[y] = row.reshape((width, 3))

        return arr.copy()

    def _gaussian_smooth(self, hist: np.ndarray, sigma: float = 1.2) -> np.ndarray:
        """高斯平滑直方图"""
        try:
            from scipy.ndimage import gaussian_filter1d
            return gaussian_filter1d(hist, sigma=sigma)
        except ImportError:
            kernel_size = 5
            kernel = np.exp(-0.5 * (np.arange(kernel_size) - kernel_size // 2) ** 2 / sigma ** 2)
            kernel = kernel / kernel.sum()
            return np.convolve(hist, kernel, mode='same')

    def features_to_dict(self, features: ToneFeatures) -> Dict[str, Any]:
        """将特征转换为字典格式

        Args:
            features: 影调特征

        Returns:
            Dict: 特征字典
        """
        return {
            "mean": features.mean,
            "median": features.median,
            "std": features.std,
            "min_val": features.min_val,
            "max_val": features.max_val,
            "P10": features.P10,
            "P90": features.P90,
            "peak": features.peak,
            "span": features.span,
            "low_ratio": features.low_ratio,
            "mid_ratio": features.mid_ratio,
            "high_ratio": features.high_ratio,
        }

    def algorithm_result_to_dict(self, features: ToneFeatures) -> Dict[str, Any]:
        """将算法结果转换为字典格式

        Args:
            features: 影调特征

        Returns:
            Dict: 算法结果字典
        """
        return {
            "tone_key": features.tone_key.value,
            "tone_range": features.tone_range.value,
            "tone_name": features.tone_name,
            "key_confidence": features.key_confidence,
            "range_confidence": features.range_confidence,
        }
