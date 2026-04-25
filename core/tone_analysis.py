"""影调分析服务"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

import numpy as np

# 项目模块导入
from .color import calculate_luminance_from_array


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

    # 基调判断阈值（与分区一致：暗部0-85，中间调86-170，亮部171-255）
    KEY_HIGH_MIN = 171  # 亮部起始
    KEY_MID_MIN = 86    # 中间调起始
    KEY_MID_MAX = 170   # 中间调结束
    KEY_LOW_MAX = 85    # 暗部结束

    # 全长调判断阈值
    MIN_ZONE_PERCENTAGE = 15
    MIN_RANGE_THRESHOLD = 30
    MAX_RANGE_THRESHOLD = 225
    U_SHAPE_RATIO = 0.7

    # 边界缓冲区（用于置信度计算）
    KEY_BUFFER = 15  # 基调边界缓冲带

    def analyze_from_array(self, img_array: np.ndarray, sample_step: int = 1) -> ToneAnalysisResult:
        """从 NumPy 数组分析影调

        Args:
            img_array: RGB 图片数组 (H, W, 3)
            sample_step: 采样步长，每隔N个像素采样一次（默认1，不采样）

        Returns:
            ToneAnalysisResult: 分析结果
        """
        # 采样处理
        sampled = img_array[::sample_step, ::sample_step]

        gray = self._rgb_to_gray(sampled)

        mean = float(np.mean(gray))
        median = float(np.median(gray))
        std = float(np.std(gray))
        min_val = int(np.min(gray))
        max_val = int(np.max(gray))

        shadows = float(np.sum(gray <= 85) / gray.size * 100)
        midtones = float(np.sum((gray >= 86) & (gray <= 170)) / gray.size * 100)
        highlights = float(np.sum(gray >= 171) / gray.size * 100)

        hist, _ = np.histogram(gray, bins=256, range=(0, 256))
        peak_position = self._calc_peak_position(hist)

        tone_key, tone_range, key_confidence, range_confidence = self._classify_tone(
            peak_position, min_val, max_val, shadows, midtones, highlights, hist
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

    def analyze_from_histogram(
        self,
        histogram: np.ndarray,
        mean: float,
        median: float,
        std: float,
        min_val: int,
        max_val: int
    ) -> ToneAnalysisResult:
        """从直方图数据快速分析影调

        利用已计算的直方图和统计信息快速构建分析结果，
        避免重复的 NumPy 计算。适用于从 HistogramCache 复用数据的场景。

        Args:
            histogram: 直方图数据（256个整数）
            mean: 平均亮度值
            median: 中位数亮度值
            std: 标准差
            min_val: 最小亮度值
            max_val: 最大亮度值

        Returns:
            ToneAnalysisResult: 分析结果
        """
        # 计算波峰位置
        peak_position = self._calc_peak_position(histogram)

        # 从直方图计算区域占比
        total_pixels = np.sum(histogram)
        if total_pixels > 0:
            shadows = float(np.sum(histogram[:86]) / total_pixels * 100)
            midtones = float(np.sum(histogram[86:171]) / total_pixels * 100)
            highlights = float(np.sum(histogram[171:]) / total_pixels * 100)
        else:
            shadows = midtones = highlights = 0.0

        # 影调分类
        tone_key, tone_range, key_confidence, range_confidence = self._classify_tone(
            peak_position, min_val, max_val, shadows, midtones, highlights, histogram
        )

        return ToneAnalysisResult(
            mean=mean,
            median=median,
            std=std,
            min_val=min_val,
            max_val=max_val,
            shadows=shadows,
            midtones=midtones,
            highlights=highlights,
            tone_key=tone_key,
            tone_range=tone_range,
            histogram=histogram,
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

    def _calc_peak_sharpness(self, hist: np.ndarray, peak: int, window: int = 10) -> float:
        """计算波峰尖锐度

        尖锐度反映波峰的集中程度，越尖锐的波峰说明像素堆积越集中，
        基调判定越确定。计算方式为峰值与周围平均值的比值。

        Args:
            hist: 直方图数据
            peak: 波峰位置
            window: 计算窗口大小，默认10

        Returns:
            float: 尖锐度系数 (1.0-5.0)，值越大越尖锐
        """
        peak_val = hist[int(peak)]

        # 获取窗口范围内的数据（排除峰值本身）
        start = max(0, int(peak) - window)
        end = min(len(hist), int(peak) + window + 1)
        surrounding = np.concatenate([hist[start:int(peak)], hist[int(peak)+1:end]])

        surrounding_avg = np.mean(surrounding)
        if surrounding_avg == 0:
            return 5.0

        # 归一化到 1.0-5.0 范围
        ratio = peak_val / surrounding_avg
        return min(5.0, max(1.0, ratio))

    def _calc_distribution_continuity(self, hist: np.ndarray, start: int, end: int) -> float:
        """计算指定区间的分布连续性

        连续性反映像素分布的连贯程度，连续性越高说明分布越自然。
        通过计算非零bin的占比来评估。

        Args:
            hist: 直方图数据
            start: 起始位置
            end: 结束位置

        Returns:
            float: 连续性系数 (0.0-1.0)，值越大连续性越好
        """
        region = hist[start:end]
        if np.sum(region) == 0:
            return 0.0

        # 非零bin占比
        return np.count_nonzero(region) / len(region)

    def _classify_tone(self, peak: float, min_val: int, max_val: int,
                       shadows: float, midtones: float, highlights: float,
                       hist: np.ndarray) -> Tuple[ToneKey, ToneRange, float, float]:
        """判断影调类型

        Args:
            peak: 波峰位置
            min_val: 最小亮度值
            max_val: 最大亮度值
            shadows: 暗部占比
            midtones: 中间调占比
            highlights: 亮部占比
            hist: 直方图数据

        Returns:
            Tuple[ToneKey, ToneRange, float, float]: 基调、跨度、基调置信度、跨度置信度
        """
        # 全长调判断（带置信度）
        is_full, full_confidence = self._is_full_tone(hist, shadows, highlights, min_val, max_val)
        if is_full:
            return ToneKey.FULL, ToneRange.LONG, full_confidence, full_confidence

        # 基调判断（带置信度）
        tone_key, key_confidence = self._get_tone_key(peak, hist)

        # 跨度判断（带置信度），基于区域分布占比
        tone_range, range_confidence = self._get_tone_range_by_distribution(
            shadows, midtones, highlights, hist
        )

        return tone_key, tone_range, key_confidence, range_confidence

    def _is_full_tone(self, hist: np.ndarray, shadows: float,
                      highlights: float, min_val: int, max_val: int) -> Tuple[bool, float]:
        """判断是否为全长调并返回置信度

        特征：两端都有明显像素，中间相对较少

        Args:
            hist: 直方图数据
            shadows: 暗部占比 (%)
            highlights: 亮部占比 (%)
            min_val: 最小亮度值
            max_val: 最大亮度值

        Returns:
            Tuple[bool, float]: (是否全长调, 置信度0.5-1.0)
        """
        # 基础条件检查
        has_shadows = shadows > self.MIN_ZONE_PERCENTAGE
        has_highlights = highlights > self.MIN_ZONE_PERCENTAGE
        full_range = (min_val < self.MIN_RANGE_THRESHOLD) and (max_val > self.MAX_RANGE_THRESHOLD)

        if not (has_shadows and has_highlights and full_range):
            return False, 0.0

        # U型分布判断（基于新分区：暗部0-85，中间调86-170，亮部171-255）
        mid_avg = np.mean(hist[86:171])
        edge_avg = np.mean(np.concatenate([hist[:43], hist[213:]]))

        if mid_avg >= edge_avg * self.U_SHAPE_RATIO:
            return False, 0.0

        # 计算置信度
        # 1. 两端占比因子：两端占比越高，置信度越高
        edge_factor = min(edge_ratio := (shadows + highlights) / 100.0, 0.5) / 0.5

        # 2. U型明显程度因子：中间相对两端越少，置信度越高
        u_factor = max(0.0, 1.0 - mid_avg / (edge_avg * self.U_SHAPE_RATIO))

        # 3. 范围完整度因子
        range_factor = min((max_val - min_val) / 240.0, 1.0)

        # 综合置信度
        confidence = 0.5 + 0.5 * (edge_factor * 0.4 + u_factor * 0.4 + range_factor * 0.2)

        return True, confidence

    def _get_tone_key(self, peak: float, hist: np.ndarray) -> Tuple[ToneKey, float]:
        """根据波峰位置确定基调及置信度

        结合波峰位置和波峰尖锐度评估基调置信度，
        波峰越尖锐，基调判定越确定。

        Args:
            peak: 波峰位置
            hist: 直方图数据

        Returns:
            Tuple[ToneKey, float]: 基调类型、置信度(0.5-1.0)
        """
        # 计算波峰尖锐度因子
        sharpness = self._calc_peak_sharpness(hist, int(peak))
        # 尖锐度 1.0-5.0 映射到 0.7-1.0 的置信度因子
        sharpness_factor = 0.7 + 0.3 * min(1.0, (sharpness - 1.0) / 4.0)

        # 高调区域
        if peak >= self.KEY_HIGH_MIN:
            distance = peak - self.KEY_HIGH_MIN
            position_confidence = 0.5 + 0.5 * min(distance / self.KEY_BUFFER, 1.0)
            confidence = position_confidence * sharpness_factor
            return ToneKey.HIGH, confidence

        # 低调区域
        if peak <= self.KEY_LOW_MAX:
            distance = self.KEY_LOW_MAX - peak
            position_confidence = 0.5 + 0.5 * min(distance / self.KEY_BUFFER, 1.0)
            confidence = position_confidence * sharpness_factor
            return ToneKey.LOW, confidence

        # 中调区域
        dist_to_low = peak - self.KEY_LOW_MAX
        dist_to_high = self.KEY_HIGH_MIN - peak

        if dist_to_low < self.KEY_BUFFER and dist_to_low < dist_to_high:
            # 靠近低调边界
            position_confidence = 0.5 + 0.5 * (dist_to_low / self.KEY_BUFFER)
        elif dist_to_high < self.KEY_BUFFER:
            # 靠近高调边界
            position_confidence = 0.5 + 0.5 * (dist_to_high / self.KEY_BUFFER)
        else:
            # 中调核心区
            position_confidence = 1.0

        confidence = position_confidence * sharpness_factor
        return ToneKey.MID, confidence

    def _get_tone_range_by_distribution(
        self, shadows: float, midtones: float, highlights: float, hist: np.ndarray
    ) -> Tuple[ToneRange, float]:
        """根据区域分布占比确定跨度及置信度

        基于影调分类的核心原则：
        - 长调：暗部、中间调、亮部都有明显分布（从黑到白都有）
        - 中调：缺失一端（只有两段有明显分布）
        - 短调：集中在窄范围内（只有一段占绝对主导）

        结合分布连续性评估，连续性越高，跨度判定越确定。

        Args:
            shadows: 暗部占比 (%)
            midtones: 中间调占比 (%)
            highlights: 亮部占比 (%)
            hist: 直方图数据

        Returns:
            Tuple[ToneRange, float]: 跨度类型、置信度(0.5-1.0)
        """
        # 定义"明显分布"的阈值
        SIGNIFICANT_THRESHOLD = 0.5  # 占比超过0.5%认为有明显分布（仅过滤极端噪声）

        # 计算有多少个区域有明显分布
        significant_zones = 0
        if shadows >= SIGNIFICANT_THRESHOLD:
            significant_zones += 1
        if midtones >= SIGNIFICANT_THRESHOLD:
            significant_zones += 1
        if highlights >= SIGNIFICANT_THRESHOLD:
            significant_zones += 1

        # 计算各区域的分布连续性
        shadow_continuity = self._calc_distribution_continuity(hist, 0, 86)
        midtone_continuity = self._calc_distribution_continuity(hist, 86, 171)
        highlight_continuity = self._calc_distribution_continuity(hist, 171, 256)

        # 长调：三个区域都有明显分布
        if significant_zones >= 3:
            # 基础置信度基于最小区域的占比
            min_ratio = min(shadows, midtones, highlights)
            base_confidence = 0.5 + min(min_ratio / 10.0, 0.5)
            # 连续性因子：三个区域连续性的平均值
            continuity_factor = (shadow_continuity + midtone_continuity + highlight_continuity) / 3.0
            # 连续性好的区域置信度更高（0.8-1.0范围调整）
            confidence = base_confidence * (0.8 + 0.2 * continuity_factor)
            return ToneRange.LONG, confidence

        # 短调：只有一个区域有明显分布（集中度极高）
        if significant_zones == 1:
            max_ratio = max(shadows, midtones, highlights)
            base_confidence = 0.5 + min((max_ratio - 80.0) / 30.0, 0.5)
            # 短调主要依赖主导区域的连续性
            if shadows >= SIGNIFICANT_THRESHOLD:
                continuity_factor = shadow_continuity
            elif midtones >= SIGNIFICANT_THRESHOLD:
                continuity_factor = midtone_continuity
            else:
                continuity_factor = highlight_continuity
            confidence = base_confidence * (0.8 + 0.2 * continuity_factor)
            return ToneRange.SHORT, confidence

        # 中调：两个区域有明显分布
        ratios = [r for r in [shadows, midtones, highlights] if r >= SIGNIFICANT_THRESHOLD]
        continuities = []
        if shadows >= SIGNIFICANT_THRESHOLD:
            continuities.append(shadow_continuity)
        if midtones >= SIGNIFICANT_THRESHOLD:
            continuities.append(midtone_continuity)
        if highlights >= SIGNIFICANT_THRESHOLD:
            continuities.append(highlight_continuity)

        if len(ratios) == 2:
            # 基础置信度基于两个区域的均衡程度
            base_confidence = 0.5 + min(min(ratios) / max(ratios), 0.5)
            # 连续性因子
            continuity_factor = sum(continuities) / len(continuities) if continuities else 1.0
            confidence = base_confidence * (0.8 + 0.2 * continuity_factor)
        else:
            confidence = 0.7

        return ToneRange.MEDIUM, confidence

    def _rgb_to_gray(self, img_array: np.ndarray) -> np.ndarray:
        """RGB 转灰度 (Rec. 709 标准 + sRGB Gamma 校正)"""
        return calculate_luminance_from_array(img_array)

    def get_gray_image(self, img_array: np.ndarray) -> np.ndarray:
        """获取灰度图像（用于显示，使用简单快速转换）"""
        return self._rgb_to_gray_fast(img_array)

    def _rgb_to_gray_fast(self, img_array: np.ndarray) -> np.ndarray:
        """RGB 转灰度（快速版本，用于显示）"""
        return (0.299 * img_array[:, :, 0] +
                0.587 * img_array[:, :, 1] +
                0.114 * img_array[:, :, 2]).astype(np.uint8)


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
