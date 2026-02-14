"""对比度检查模块

提供 WCAG 2.1 标准的颜色对比度计算和等级判断功能。
"""

from typing import Tuple, Dict


def calculate_relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """计算颜色的相对亮度
    
    使用 WCAG 2.1 标准计算相对亮度，包含 sRGB Gamma 校正。
    
    Args:
        rgb: RGB 颜色元组 (r, g, b)，范围 0-255
        
    Returns:
        相对亮度值，范围 0-1
    """
    r, g, b = rgb
    
    # 归一化到 0-1 范围
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    
    # sRGB Gamma 解码（转换到线性空间）
    def srgb_to_linear(c: float) -> float:
        if c <= 0.03928:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4
    
    r_linear = srgb_to_linear(r_norm)
    g_linear = srgb_to_linear(g_norm)
    b_linear = srgb_to_linear(b_norm)
    
    # 计算相对亮度（Rec. 709 权重）
    luminance = 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear
    
    return luminance


def calculate_contrast_ratio(
    rgb1: Tuple[int, int, int],
    rgb2: Tuple[int, int, int]
) -> float:
    """计算两个颜色的对比度比率
    
    使用 WCAG 2.1 标准公式：ratio = (L1 + 0.05) / (L2 + 0.05)
    其中 L1 是较亮的颜色，L2 是较暗的颜色。
    
    Args:
        rgb1: 第一个 RGB 颜色元组 (r, g, b)，范围 0-255
        rgb2: 第二个 RGB 颜色元组 (r, g, b)，范围 0-255
        
    Returns:
        对比度比率，范围 1-21
    """
    l1 = calculate_relative_luminance(rgb1)
    l2 = calculate_relative_luminance(rgb2)
    
    # 确保 L1 是较亮的颜色
    lighter = max(l1, l2)
    darker = min(l1, l2)
    
    # 计算对比度（避免除以0）
    ratio = (lighter + 0.05) / (darker + 0.05)
    
    return round(ratio, 2)


def get_wcag_level(ratio: float, is_large_text: bool = False) -> str:
    """根据对比度比率获取 WCAG 等级
    
    WCAG 2.1 标准：
    - 普通文字 AA: 4.5:1
    - 普通文字 AAA: 7:1
    - 大号文字 AA: 3:1
    - 大号文字 AAA: 4.5:1
    
    Args:
        ratio: 对比度比率
        is_large_text: 是否为大号文字（18pt+ 或 14pt+粗体）
        
    Returns:
        WCAG 等级：'AAA'、'AA'、'Fail'
    """
    if is_large_text:
        if ratio >= 4.5:
            return 'AAA'
        elif ratio >= 3:
            return 'AA'
        else:
            return 'Fail'
    else:
        if ratio >= 7:
            return 'AAA'
        elif ratio >= 4.5:
            return 'AA'
        else:
            return 'Fail'


def get_contrast_info(
    rgb1: Tuple[int, int, int],
    rgb2: Tuple[int, int, int]
) -> Dict:
    """获取完整的对比度信息
    
    Args:
        rgb1: 第一个 RGB 颜色元组 (r, g, b)，范围 0-255
        rgb2: 第二个 RGB 颜色元组 (r, g, b)，范围 0-255
        
    Returns:
        包含对比度信息的字典：
        {
            'ratio': float,           # 对比度比率
            'normal_text': str,       # 普通文字等级 (AAA/AA/Fail)
            'large_text': str,        # 大号文字等级 (AAA/AA/Fail)
            'passes_aa': bool,        # 是否通过 AA 标准
            'passes_aaa': bool,       # 是否通过 AAA 标准
            'luminance1': float,      # 第一个颜色的相对亮度
            'luminance2': float       # 第二个颜色的相对亮度
        }
    """
    ratio = calculate_contrast_ratio(rgb1, rgb2)
    normal_level = get_wcag_level(ratio, is_large_text=False)
    large_level = get_wcag_level(ratio, is_large_text=True)
    
    return {
        'ratio': ratio,
        'normal_text': normal_level,
        'large_text': large_level,
        'passes_aa': ratio >= 4.5,
        'passes_aaa': ratio >= 7,
        'luminance1': calculate_relative_luminance(rgb1),
        'luminance2': calculate_relative_luminance(rgb2)
    }


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """将 RGB 转换为 HEX 字符串
    
    Args:
        rgb: RGB 颜色元组 (r, g, b)，范围 0-255
        
    Returns:
        HEX 颜色字符串，如 '#FF0000'
    """
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """将 HEX 字符串转换为 RGB
    
    Args:
        hex_color: HEX 颜色字符串，如 '#FF0000' 或 'FF0000'
        
    Returns:
        RGB 颜色元组 (r, g, b)，范围 0-255
        
    Raises:
        ValueError: 如果 HEX 格式无效
    """
    hex_color = hex_color.lstrip('#')
    
    if len(hex_color) != 6:
        raise ValueError(f"无效的 HEX 颜色格式: {hex_color}")
    
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
    except ValueError as e:
        raise ValueError(f"无效的 HEX 颜色格式: {hex_color}") from e


def get_contrast_status_color(ratio: float, is_dark_theme: bool = False) -> Tuple[int, int, int]:
    """获取对比度状态对应的颜色
    
    Args:
        ratio: 对比度比率
        is_dark_theme: 是否为深色主题
        
    Returns:
        RGB 颜色元组 (r, g, b)
    """
    if ratio >= 7:
        # AAA - 绿色
        return (76, 175, 80) if not is_dark_theme else (129, 199, 132)
    elif ratio >= 4.5:
        # AA - 蓝色
        return (33, 150, 243) if not is_dark_theme else (100, 181, 246)
    elif ratio >= 3:
        # 仅大号文字通过 - 橙色
        return (255, 152, 0) if not is_dark_theme else (255, 183, 77)
    else:
        # 不通过 - 红色
        return (244, 67, 54) if not is_dark_theme else (239, 83, 80)
