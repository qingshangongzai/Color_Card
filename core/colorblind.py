"""色盲模拟模块

提供各种色盲类型的颜色转换功能。
使用 LMS 色彩空间转换矩阵实现准确的色盲模拟。
"""

from typing import Tuple, Dict


# 色盲类型定义
COLORBLIND_TYPES = {
    'normal': {
        'name': '正常视觉',
        'description': '正常色彩视觉，可以看到完整的色彩谱。'
    },
    'protanopia': {
        'name': '红色盲',
        'description': '红色视锥细胞缺失，难以区分红色和绿色，红色看起来较暗。'
    },
    'deuteranopia': {
        'name': '绿色盲',
        'description': '绿色视锥细胞缺失，难以区分红色和绿色，是最常见的色盲类型。'
    },
    'tritanopia': {
        'name': '蓝色盲',
        'description': '蓝色视锥细胞缺失，难以区分蓝色和黄色，非常罕见。'
    },
    'achromatopsia': {
        'name': '全色盲',
        'description': '完全无法感知颜色，只能看到灰度，极为罕见。'
    }
}


def rgb_to_lms(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """将 RGB 转换为 LMS 色彩空间
    
    LMS 代表长波(L)、中波(M)、短波(S)视锥细胞的响应值。
    使用 Bradford 变换矩阵。
    
    Args:
        r: 红色分量 (0-255)
        g: 绿色分量 (0-255)
        b: 蓝色分量 (0-255)
        
    Returns:
        (L, M, S) 元组
    """
    # 归一化到 0-1
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    
    # sRGB 到线性 RGB 的伽马校正
    def gamma_correction(c):
        if c <= 0.04045:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4
    
    r_linear = gamma_correction(r_norm)
    g_linear = gamma_correction(g_norm)
    b_linear = gamma_correction(b_norm)
    
    # RGB 到 LMS 转换矩阵 (Bradford)
    l = 0.8951 * r_linear + 0.2664 * g_linear - 0.1614 * b_linear
    m = -0.7502 * r_linear + 1.7135 * g_linear + 0.0367 * b_linear
    s = 0.0389 * r_linear - 0.0685 * g_linear + 1.0296 * b_linear
    
    return (l, m, s)


def lms_to_rgb(l: float, m: float, s: float) -> Tuple[int, int, int]:
    """将 LMS 转换回 RGB 色彩空间
    
    Args:
        l: 长波视锥响应
        m: 中波视锥响应
        s: 短波视锥响应
        
    Returns:
        (r, g, b) 元组，范围 0-255
    """
    # LMS 到 RGB 转换矩阵 (Bradford 逆矩阵)
    r_linear = 0.986993 * l - 0.147054 * m + 0.159963 * s
    g_linear = 0.432305 * l + 0.51836 * m + 0.049291 * s
    b_linear = -0.008529 * l + 0.040043 * m + 0.968487 * s
    
    # 线性 RGB 到 sRGB 的伽马校正
    def gamma_correction_inv(c):
        if c <= 0.0031308:
            return c * 12.92
        else:
            return 1.055 * (c ** (1.0 / 2.4)) - 0.055
    
    r_norm = gamma_correction_inv(r_linear)
    g_norm = gamma_correction_inv(g_linear)
    b_norm = gamma_correction_inv(b_linear)
    
    # 裁剪到 0-1 范围并转换为 0-255
    r = int(max(0, min(1, r_norm)) * 255)
    g = int(max(0, min(1, g_norm)) * 255)
    b = int(max(0, min(1, b_norm)) * 255)
    
    return (r, g, b)


def simulate_protanopia(l: float, m: float, s: float) -> Tuple[float, float, float]:
    """模拟红色盲 (Protanopia)
    
    红色视锥细胞缺失，L 通道信息丢失。
    使用红色盲模拟矩阵。
    """
    # 红色盲转换：L 通道由 M 和 S 估算
    l_blind = 0.0 * l + 2.02344 * m - 2.52581 * s
    m_blind = m
    s_blind = s
    return (l_blind, m_blind, s_blind)


def simulate_deuteranopia(l: float, m: float, s: float) -> Tuple[float, float, float]:
    """模拟绿色盲 (Deuteranopia)
    
    绿色视锥细胞缺失，M 通道信息丢失。
    使用绿色盲模拟矩阵。
    """
    # 绿色盲转换：M 通道由 L 和 S 估算
    l_blind = l
    m_blind = 0.49421 * l + 0.0 * m + 1.24827 * s
    s_blind = s
    return (l_blind, m_blind, s_blind)


def simulate_tritanopia(l: float, m: float, s: float) -> Tuple[float, float, float]:
    """模拟蓝色盲 (Tritanopia)
    
    蓝色视锥细胞缺失，S 通道信息丢失。
    使用蓝色盲模拟矩阵。
    """
    # 蓝色盲转换：S 通道由 L 和 M 估算
    l_blind = l
    m_blind = m
    s_blind = -0.395913 * l + 0.801109 * m + 0.0 * s
    return (l_blind, m_blind, s_blind)


def simulate_achromatopsia(l: float, m: float, s: float) -> Tuple[float, float, float]:
    """模拟全色盲 (Achromatopsia)
    
    完全无法感知颜色，转换为灰度。
    使用 LMS 到灰度的转换。
    """
    # 转换为灰度值 (使用亮度权重)
    gray = 0.299 * l + 0.587 * m + 0.114 * s
    return (gray, gray, gray)


def simulate_colorblind(
    rgb: Tuple[int, int, int],
    colorblind_type: str = 'normal'
) -> Tuple[int, int, int]:
    """模拟指定类型的色盲效果
    
    Args:
        rgb: 原始 RGB 颜色元组 (r, g, b)，范围 0-255
        colorblind_type: 色盲类型，可选值：
            - 'normal': 正常视觉
            - 'protanopia': 红色盲
            - 'deuteranopia': 绿色盲
            - 'tritanopia': 蓝色盲
            - 'achromatopsia': 全色盲
            
    Returns:
        模拟后的 RGB 颜色元组 (r, g, b)，范围 0-255
    """
    if colorblind_type == 'normal':
        return rgb
    
    r, g, b = rgb
    
    # 转换为 LMS 空间
    l, m, s = rgb_to_lms(r, g, b)
    
    # 应用色盲模拟
    if colorblind_type == 'protanopia':
        l, m, s = simulate_protanopia(l, m, s)
    elif colorblind_type == 'deuteranopia':
        l, m, s = simulate_deuteranopia(l, m, s)
    elif colorblind_type == 'tritanopia':
        l, m, s = simulate_tritanopia(l, m, s)
    elif colorblind_type == 'achromatopsia':
        l, m, s = simulate_achromatopsia(l, m, s)
    else:
        return rgb
    
    # 转换回 RGB
    return lms_to_rgb(l, m, s)


def get_colorblind_info(colorblind_type: str) -> Dict[str, str]:
    """获取色盲类型的信息
    
    Args:
        colorblind_type: 色盲类型
        
    Returns:
        包含名称和描述的字典
    """
    return COLORBLIND_TYPES.get(colorblind_type, {
        'name': '未知',
        'description': '未知的色盲类型。'
    })


def get_all_colorblind_types() -> Dict[str, Dict[str, str]]:
    """获取所有支持的色盲类型
    
    Returns:
        色盲类型字典，键为类型标识，值为信息字典
    """
    return COLORBLIND_TYPES.copy()
