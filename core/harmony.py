"""色彩和谐度分析模块

提供配色方案的色彩和谐度计算，支持多种和谐类型判断和评分。
"""

from __future__ import annotations

import math


def calculate_hue_distance(hue1: float, hue2: float) -> float:
    """计算色相环上最短距离

    Args:
        hue1: 第一个色相值 (0-360)
        hue2: 第二个色相值 (0-360)

    Returns:
        float: 色相环上最短距离 (0-180)
    """
    diff = abs(hue1 - hue2) % 360
    return min(diff, 360 - diff)


def _check_monochromatic(hues: list[float]) -> bool:
    """判断是否为单色系配色

    Args:
        hues: 色相列表

    Returns:
        bool: 是否为单色系
    """
    if len(hues) < 2:
        return True
    for i in range(len(hues)):
        for j in range(i + 1, len(hues)):
            if calculate_hue_distance(hues[i], hues[j]) >= 15:
                return False
    return True


def _check_analogous(hues: list[float]) -> bool:
    """判断是否为类似色配色

    Args:
        hues: 色相列表

    Returns:
        bool: 是否为类似色
    """
    if len(hues) < 2:
        return False
    sorted_hues = sorted(hues)
    for i in range(len(sorted_hues) - 1):
        dist = calculate_hue_distance(sorted_hues[i], sorted_hues[i + 1])
        if dist < 15 or dist > 45:
            return False
    if len(sorted_hues) > 2:
        last_dist = calculate_hue_distance(sorted_hues[-1], sorted_hues[0])
        if last_dist < 15 or last_dist > 45:
            return False
    return True


def _check_complementary(hues: list[float]) -> bool:
    """判断是否为互补色配色

    Args:
        hues: 色相列表

    Returns:
        bool: 是否为互补色
    """
    if len(hues) < 2:
        return False
    for i in range(len(hues)):
        for j in range(i + 1, len(hues)):
            dist = calculate_hue_distance(hues[i], hues[j])
            if 165 <= dist <= 195:
                return True
    return False


def _check_split_complementary(hues: list[float]) -> bool:
    """判断是否为分裂互补配色

    Args:
        hues: 色相列表

    Returns:
        bool: 是否为分裂互补
    """
    if len(hues) < 3:
        return False
    for i in range(len(hues)):
        complement_hue = (hues[i] + 180) % 360
        left_found = False
        right_found = False
        for j in range(len(hues)):
            if i == j:
                continue
            dist_left = calculate_hue_distance(hues[j], (complement_hue - 30) % 360)
            dist_right = calculate_hue_distance(hues[j], (complement_hue + 30) % 360)
            if dist_left <= 20:
                left_found = True
            if dist_right <= 20:
                right_found = True
        if left_found and right_found:
            return True
    return False


def _check_triadic(hues: list[float]) -> bool:
    """判断是否为三角配色

    Args:
        hues: 色相列表

    Returns:
        bool: 是否为三角配色
    """
    if len(hues) < 3:
        return False
    for i in range(len(hues)):
        for j in range(i + 1, len(hues)):
            for k in range(j + 1, len(hues)):
                d1 = calculate_hue_distance(hues[i], hues[j])
                d2 = calculate_hue_distance(hues[j], hues[k])
                d3 = calculate_hue_distance(hues[k], hues[i])
                if (100 <= d1 <= 140 and 100 <= d2 <= 140 and 100 <= d3 <= 140):
                    return True
    return False


def _check_tetradic(hues: list[float]) -> bool:
    """判断是否为四角配色

    Args:
        hues: 色相列表

    Returns:
        bool: 是否为四角配色
    """
    if len(hues) < 4:
        return False
    complement_pairs = 0
    for i in range(len(hues)):
        for j in range(i + 1, len(hues)):
            dist = calculate_hue_distance(hues[i], hues[j])
            if 165 <= dist <= 195:
                complement_pairs += 1
    return complement_pairs >= 2


def _determine_harmony_type(hues: list[float]) -> tuple[str, str]:
    """判断和谐类型

    Args:
        hues: 色相列表

    Returns:
        tuple[str, str]: (和谐类型英文名, 翻译键)
    """
    if len(hues) < 2:
        return 'monochromatic', 'dialogs.harmony.type_monochromatic'

    if _check_monochromatic(hues):
        return 'monochromatic', 'dialogs.harmony.type_monochromatic'
    if _check_analogous(hues):
        return 'analogous', 'dialogs.harmony.type_analogous'
    if _check_triadic(hues):
        return 'triadic', 'dialogs.harmony.type_triadic'
    if _check_split_complementary(hues):
        return 'split_complementary', 'dialogs.harmony.type_split_complementary'
    if _check_complementary(hues):
        return 'complementary', 'dialogs.harmony.type_complementary'
    if _check_tetradic(hues):
        return 'tetradic', 'dialogs.harmony.type_tetradic'

    return 'none', 'dialogs.harmony.type_none'


def _calculate_hue_score(harmony_type: str) -> float:
    """根据和谐类型计算色相分布得分

    Args:
        harmony_type: 和谐类型英文名

    Returns:
        float: 色相分布得分 (0-100)
    """
    score_map = {
        'monochromatic': 90,
        'analogous': 85,
        'complementary': 80,
        'split_complementary': 78,
        'triadic': 82,
        'tetradic': 75,
        'none': 30,
    }
    return score_map.get(harmony_type, 30)


def _calculate_saturation_consistency(saturations: list[float]) -> float:
    """计算饱和度一致性得分

    Args:
        saturations: 饱和度列表 (0-100)

    Returns:
        float: 饱和度一致性得分 (0-100)
    """
    if len(saturations) < 2:
        return 100.0
    mean_sat = sum(saturations) / len(saturations)
    variance = sum((s - mean_sat) ** 2 for s in saturations) / len(saturations)
    std_dev = math.sqrt(variance)
    score = max(0, 100 - std_dev * 2)
    return round(score, 1)


def _calculate_brightness_distribution(brightnesses: list[float]) -> float:
    """计算明度层次感得分

    Args:
        brightnesses: 明度列表 (0-100)

    Returns:
        float: 明度层次感得分 (0-100)
    """
    if len(brightnesses) < 2:
        return 100.0
    sorted_b = sorted(brightnesses)
    total_range = sorted_b[-1] - sorted_b[0]
    range_score = min(100, total_range * 2)
    n = len(sorted_b)
    if n >= 3:
        ideal_gap = total_range / (n - 1) if total_range > 0 else 0
        gap_deviations = []
        for i in range(1, n):
            actual_gap = sorted_b[i] - sorted_b[i - 1]
            gap_deviations.append(abs(actual_gap - ideal_gap))
        avg_deviation = sum(gap_deviations) / len(gap_deviations)
        uniformity_score = max(0, 100 - avg_deviation * 3)
    else:
        uniformity_score = 80
    score = range_score * 0.4 + uniformity_score * 0.6
    return round(score, 1)


def _get_score_level(score: float) -> str:
    """根据评分获取等级翻译键

    Args:
        score: 和谐度评分 (0-100)

    Returns:
        str: 评分等级翻译键
    """
    if score >= 80:
        return 'dialogs.harmony.score_excellent'
    elif score >= 60:
        return 'dialogs.harmony.score_good'
    elif score >= 40:
        return 'dialogs.harmony.score_average'
    else:
        return 'dialogs.harmony.score_poor'


def _generate_suggestions(
    harmony_type: str,
    sat_score: float,
    bright_score: float
) -> list[str]:
    """生成优化建议

    Args:
        harmony_type: 和谐类型
        sat_score: 饱和度一致性得分
        bright_score: 明度层次感得分

    Returns:
        list[str]: 建议翻译键列表
    """
    suggestions = []
    if harmony_type == 'none':
        suggestions.append('dialogs.harmony.suggestion_consider_harmony_type')
    if sat_score < 50:
        suggestions.append('dialogs.harmony.suggestion_balance_saturation')
    if bright_score < 50:
        suggestions.append('dialogs.harmony.suggestion_balance_brightness')
    return suggestions


def analyze_harmony(colors: list[dict]) -> dict:
    """分析配色方案的和谐度

    Args:
        colors: 颜色信息列表，每个颜色包含 hsb 键

    Returns:
        dict: 和谐度分析结果
    """
    hues = []
    saturations = []
    brightnesses = []
    for color in colors:
        hsb = color.get('hsb', (0, 0, 0))
        if isinstance(hsb, (list, tuple)) and len(hsb) >= 3:
            hues.append(float(hsb[0]))
            saturations.append(float(hsb[1]))
            brightnesses.append(float(hsb[2]))

    if not hues:
        return {
            'harmony_type': 'none',
            'harmony_type_key': 'dialogs.harmony.type_none',
            'score': 0,
            'score_level': 'dialogs.harmony.score_poor',
            'hue_distances': [],
            'suggestions': ['dialogs.harmony.suggestion_consider_harmony_type'],
        }

    harmony_type, harmony_type_key = _determine_harmony_type(hues)

    hue_score = _calculate_hue_score(harmony_type)
    sat_score = _calculate_saturation_consistency(saturations)
    bright_score = _calculate_brightness_distribution(brightnesses)

    total_score = round(hue_score * 0.5 + sat_score * 0.25 + bright_score * 0.25, 1)

    score_level = _get_score_level(total_score)

    sorted_hues = sorted(hues)
    hue_distances = []
    for i in range(len(sorted_hues) - 1):
        hue_distances.append(round(calculate_hue_distance(sorted_hues[i], sorted_hues[i + 1]), 1))

    suggestions = _generate_suggestions(harmony_type, sat_score, bright_score)

    return {
        'harmony_type': harmony_type,
        'harmony_type_key': harmony_type_key,
        'score': total_score,
        'score_level': score_level,
        'hue_distances': hue_distances,
        'suggestions': suggestions,
    }
