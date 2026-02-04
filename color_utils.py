"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: color_utils
功能描述: 颜色空间转换工具，支持 RGB、HSB、LAB、HSL、CMYK 等颜色空间

作者: 青山公仔
创建日期: 2026-02-04
"""

# 标准库导入
import colorsys
from typing import Dict, List, Tuple


def rgb_to_hsb(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """将RGB转换为HSB (Hue, Saturation, Brightness)

    Args:
        r: 红色通道值 (0-255)
        g: 绿色通道值 (0-255)
        b: 蓝色通道值 (0-255)

    Returns:
        tuple: (色相 0-360, 饱和度 0-100, 亮度 0-100)
    """
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
    return h * 360, s * 100, v * 100


def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """将RGB转换为LAB颜色空间

    LAB颜色空间是一种设备无关的颜色空间，L代表亮度(0-100)，
    A和B代表颜色对立通道(-128到127)，适合用于颜色差异计算。

    转换步骤：
    1. RGB归一化到0-1范围
    2. 应用sRGB Gamma校正（转换到线性空间）
    3. 转换为XYZ颜色空间（使用sRGB转换矩阵）
    4. 使用D65参考白点归一化XYZ值
    5. 转换为LAB颜色空间

    Args:
        r: 红色通道值 (0-255)
        g: 绿色通道值 (0-255)
        b: 蓝色通道值 (0-255)

    Returns:
        tuple: (L 0-100, A -128-127, B -128-127)
    """
    # 步骤1: 归一化到 0-1 范围
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0

    # 步骤2: 应用gamma校正（转换到线性空间）
    # sRGB的gamma曲线近似于gamma 2.2，但使用更精确的分段公式
    # 小于等于0.04045的值使用线性转换，大于0.04045的值使用幂函数
    r_norm = r_norm ** 2.2 if r_norm > 0.04045 else r_norm / 12.92
    g_norm = g_norm ** 2.2 if g_norm > 0.04045 else g_norm / 12.92
    b_norm = b_norm ** 2.2 if b_norm > 0.04045 else b_norm / 12.92

    # 步骤3: 转换为XYZ颜色空间
    # 使用sRGB到XYZ的转换矩阵（基于CIE 1931标准）
    # X = 0.4124564*R + 0.3575761*G + 0.1804375*B
    # Y = 0.2126729*R + 0.7151522*G + 0.0721750*B
    # Z = 0.0193339*R + 0.1191920*G + 0.9503041*B
    x = r_norm * 0.4124564 + g_norm * 0.3575761 + b_norm * 0.1804375
    y = r_norm * 0.2126729 + g_norm * 0.7151522 + b_norm * 0.0721750
    z = r_norm * 0.0193339 + g_norm * 0.1191920 + b_norm * 0.9503041

    # 步骤4: 使用D65参考白点归一化XYZ值
    # D65是标准日光白点，色温约6500K，是sRGB和大多数显示器的标准白点
    x_ref, y_ref, z_ref = 0.95047, 1.00000, 1.08883
    x, y, z = x / x_ref, y / y_ref, z / z_ref

    # 步骤5: 转换为LAB颜色空间
    # 使用分段函数f(t)处理非线性转换
    def f(t: float) -> float:
        # 大于0.008856的值使用立方根，小于等于的值使用线性转换
        return t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116

    # L = 116*f(Y) - 16 (亮度分量)
    # A = 500*(f(X) - f(Y)) (红绿对立分量)
    # B = 200*(f(Y) - f(Z)) (黄蓝对立分量)
    l = 116 * f(y) - 16
    a_val = 500 * (f(x) - f(y))
    b_val = 200 * (f(y) - f(z))

    return l, a_val, b_val


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """将RGB转换为16进制颜色值

    Args:
        r: 红色通道值 (0-255)
        g: 绿色通道值 (0-255)
        b: 蓝色通道值 (0-255)

    Returns:
        str: 16进制颜色值，如 "#FF0000"
    """
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """将RGB转换为HSL (Hue, Saturation, Lightness)

    Args:
        r: 红色通道值 (0-255)
        g: 绿色通道值 (0-255)
        b: 蓝色通道值 (0-255)

    Returns:
        tuple: (色相 0-360, 饱和度 0-100, 亮度 0-100)
    """
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
    return h * 360, s * 100, l * 100


def rgb_to_cmyk(r: int, g: int, b: int) -> Tuple[float, float, float, float]:
    """将RGB转换为CMYK (Cyan, Magenta, Yellow, Key/Black)

    Args:
        r: 红色通道值 (0-255)
        g: 绿色通道值 (0-255)
        b: 蓝色通道值 (0-255)

    Returns:
        tuple: (C 0-100, M 0-100, Y 0-100, K 0-100)
    """
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0

    k = 1 - max(r_norm, g_norm, b_norm)
    if k == 1:
        return 0, 0, 0, 100

    c = (1 - r_norm - k) / (1 - k)
    m = (1 - g_norm - k) / (1 - k)
    y = (1 - b_norm - k) / (1 - k)

    return c * 100, m * 100, y * 100, k * 100


def get_color_info(r: int, g: int, b: int) -> Dict[str, any]:
    """获取颜色的完整信息

    Args:
        r: 红色通道值 (0-255)
        g: 绿色通道值 (0-255)
        b: 蓝色通道值 (0-255)

    Returns:
        dict: 包含RGB、HSB、LAB、HEX、HSL、CMYK颜色信息的字典
    """
    h, s, b_val = rgb_to_hsb(r, g, b)
    l, a, b_lab = rgb_to_lab(r, g, b)
    h_hsl, s_hsl, l_hsl = rgb_to_hsl(r, g, b)
    c, m, y, k = rgb_to_cmyk(r, g, b)

    return {
        'rgb': (r, g, b),
        'hsb': (round(h), round(s), round(b_val)),
        'lab': (round(l), round(a), round(b_lab)),
        'hsl': (round(h_hsl), round(s_hsl), round(l_hsl)),
        'cmyk': (round(c), round(m), round(y), round(k)),
        'rgb_display': (r, g, b),
        'hex': rgb_to_hex(r, g, b)
    }


def get_luminance(r: int, g: int, b: int) -> int:
    """计算像素的明度值 (0-255)

    使用 Rec. 709 标准计算亮度值，包含 sRGB Gamma 校正
    这是 Lightroom、Photoshop 等专业软件使用的标准方法

    Args:
        r: 红色通道值 (0-255)
        g: 绿色通道值 (0-255)
        b: 蓝色通道值 (0-255)

    Returns:
        int: 明度值 (0-255)
    """
    # 步骤1: 归一化到 0-1 范围
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # 步骤2: sRGB Gamma 解码（转换到线性空间）
    # sRGB 的 gamma 曲线近似于 gamma 2.2，但使用更精确的公式
    def srgb_to_linear(c: float) -> float:
        if c <= 0.04045:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4

    r_linear = srgb_to_linear(r_norm)
    g_linear = srgb_to_linear(g_norm)
    b_linear = srgb_to_linear(b_norm)

    # 步骤3: 在线性空间应用 Rec. 709 权重
    luminance_linear = 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear

    # 步骤4: 将结果编码回 sRGB Gamma 空间（为了显示一致性）
    def linear_to_srgb(c: float) -> float:
        if c <= 0.0031308:
            return c * 12.92
        else:
            return 1.055 * (c ** (1.0 / 2.4)) - 0.055

    luminance_srgb = linear_to_srgb(luminance_linear)

    # 步骤5: 转换回 0-255 范围
    return min(255, round(luminance_srgb * 255))


def get_zone(luminance: int) -> str:
    """根据明度值返回区域编号

    将 0-255 的明度值分为8个区域：
    Zone 0-1: 0-31    (最暗)
    Zone 1-2: 32-63
    Zone 2-3: 64-95
    Zone 3-4: 96-127
    Zone 4-5: 128-159
    Zone 5-6: 160-191
    Zone 6-7: 192-223
    Zone 7-8: 224-255 (最亮)

    Args:
        luminance: 明度值 (0-255)

    Returns:
        str: 区域编号字符串，如 "3-4"
    """
    zone_index = min(luminance // 32, 7)
    return f"{zone_index}-{zone_index + 1}"


def get_zone_bounds(zone_str: str) -> Tuple[int, int]:
    """获取区域对应的明度范围

    Args:
        zone_str: 区域编号，如 "3-4"

    Returns:
        tuple: (min_luminance, max_luminance) 元组
    """
    start = int(zone_str.split('-')[0])
    return (start * 32, (start + 1) * 32 - 1)


def calculate_histogram(image, sample_step: int = 4) -> List[int]:
    """计算图片的明度直方图（使用采样优化）

    Args:
        image: QImage 对象
        sample_step: 采样步长，每隔N个像素采样一次（默认4，即1/16的像素）

    Returns:
        list: 长度为256的列表，表示每个明度值的像素数量
    """
    histogram = [0] * 256

    if image is None or image.isNull():
        return histogram

    width = image.width()
    height = image.height()

    # 采样计算直方图，大幅提高性能
    # 确保包含边缘像素，使用 min 函数防止越界
    for y in range(0, height, sample_step):
        for x in range(0, width, sample_step):
            color = image.pixelColor(x, y)
            luminance = get_luminance(color.red(), color.green(), color.blue())
            histogram[luminance] += 1

    # 额外采样最右侧和最底部的边缘像素，确保高亮区域不被遗漏
    # 采样最右列
    if width > 0:
        right_x = width - 1
        for y in range(0, height, sample_step):
            color = image.pixelColor(right_x, y)
            luminance = get_luminance(color.red(), color.green(), color.blue())
            histogram[luminance] += 1

    # 采样最底行
    if height > 0:
        bottom_y = height - 1
        for x in range(0, width, sample_step):
            color = image.pixelColor(x, bottom_y)
            luminance = get_luminance(color.red(), color.green(), color.blue())
            histogram[luminance] += 1

    # 采样右下角像素（如果尚未被采样）
    if width > 0 and height > 0:
        color = image.pixelColor(width - 1, height - 1)
        luminance = get_luminance(color.red(), color.green(), color.blue())
        histogram[luminance] += 1

    return histogram


def calculate_rgb_histogram(image, sample_step: int = 4) -> Tuple[List[int], List[int], List[int]]:
    """计算图片的RGB直方图（使用采样优化）

    Args:
        image: QImage 对象
        sample_step: 采样步长，每隔N个像素采样一次（默认4，即1/16的像素）

    Returns:
        tuple: 三个长度为256的列表的元组 (R_histogram, G_histogram, B_histogram)
    """
    histogram_r = [0] * 256
    histogram_g = [0] * 256
    histogram_b = [0] * 256

    if image is None or image.isNull():
        return histogram_r, histogram_g, histogram_b

    width = image.width()
    height = image.height()

    # 采样计算直方图，大幅提高性能
    for y in range(0, height, sample_step):
        for x in range(0, width, sample_step):
            color = image.pixelColor(x, y)
            r = color.red()
            g = color.green()
            b = color.blue()
            histogram_r[r] += 1
            histogram_g[g] += 1
            histogram_b[b] += 1

    # 额外采样最右侧和最底部的边缘像素，确保高亮区域不被遗漏
    # 采样最右列
    if width > 0:
        right_x = width - 1
        for y in range(0, height, sample_step):
            color = image.pixelColor(right_x, y)
            histogram_r[color.red()] += 1
            histogram_g[color.green()] += 1
            histogram_b[color.blue()] += 1

    # 采样最底行
    if height > 0:
        bottom_y = height - 1
        for x in range(0, width, sample_step):
            color = image.pixelColor(x, bottom_y)
            histogram_r[color.red()] += 1
            histogram_g[color.green()] += 1
            histogram_b[color.blue()] += 1

    # 采样右下角像素（如果尚未被采样）
    if width > 0 and height > 0:
        color = image.pixelColor(width - 1, height - 1)
        histogram_r[color.red()] += 1
        histogram_g[color.green()] += 1
        histogram_b[color.blue()] += 1

    return histogram_r, histogram_g, histogram_b
