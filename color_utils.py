import colorsys
import math


def rgb_to_hsb(r, g, b):
    """将RGB转换为HSB (Hue, Saturation, Brightness)"""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def rgb_to_lab(r, g, b):
    """将RGB转换为LAB颜色空间"""
    # 首先转换为XYZ
    r, g, b = r / 255.0, g / 255.0, b / 255.0

    # 应用gamma校正
    r = r ** 2.2 if r > 0.04045 else r / 12.92
    g = g ** 2.2 if g > 0.04045 else g / 12.92
    b = b ** 2.2 if b > 0.04045 else b / 12.92

    # 转换为XYZ
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    # 参考白点D65
    x_ref, y_ref, z_ref = 0.95047, 1.00000, 1.08883

    x, y, z = x / x_ref, y / y_ref, z / z_ref

    # 转换为LAB
    def f(t):
        return t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116

    l = 116 * f(y) - 16
    a = 500 * (f(x) - f(y))
    b_val = 200 * (f(y) - f(z))

    return l, a, b_val


def get_color_info(r, g, b):
    """获取颜色的完整信息"""
    h, s, b_val = rgb_to_hsb(r, g, b)
    l, a, b_lab = rgb_to_lab(r, g, b)

    return {
        'rgb': (r, g, b),
        'hsb': (round(h), round(s), round(b_val)),
        'lab': (round(l), round(a), round(b_lab))
    }


def get_luminance(r, g, b):
    """计算像素的明度值 (0-255)
    
    使用 Rec. 709 标准计算亮度值
    """
    return int(0.2126 * r + 0.7152 * g + 0.0722 * b)


def get_zone(luminance):
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
        区域编号字符串，如 "3-4"
    """
    zone_index = min(luminance // 32, 7)
    return f"{zone_index}-{zone_index + 1}"


def get_zone_bounds(zone_str):
    """获取区域对应的明度范围
    
    Args:
        zone_str: 区域编号，如 "3-4"
    
    Returns:
        (min_luminance, max_luminance) 元组
    """
    start = int(zone_str.split('-')[0])
    return (start * 32, (start + 1) * 32 - 1)


def calculate_histogram(image):
    """计算图片的明度直方图
    
    Args:
        image: QImage 对象
    
    Returns:
        长度为256的列表，表示每个明度值的像素数量
    """
    histogram = [0] * 256
    
    if image is None or image.isNull():
        return histogram
    
    width = image.width()
    height = image.height()
    
    for y in range(height):
        for x in range(width):
            color = image.pixelColor(x, y)
            luminance = get_luminance(color.red(), color.green(), color.blue())
            histogram[luminance] += 1
    
    return histogram
