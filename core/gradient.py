# 标准库导入
from typing import List, Tuple

# 项目模块导入
from .color import hex_to_rgb, rgb_to_hsb, rgb_to_lab, hsb_to_rgb


def _normalize_hue_for_interpolation(h1: float, h2: float) -> Tuple[float, float]:
    """归一化色相值，使插值沿最短路径

    当色相差值超过180°时，调整色相值使插值沿最短路径
    处理色相跨越0°/360°的情况

    Args:
        h1: 起始色相 (0-360)
        h2: 结束色相 (0-360)

    Returns:
        Tuple[float, float]: 调整后的起始色相和结束色相
    """
    diff = h2 - h1
    if diff > 180:
        h2 -= 360
    elif diff < -180:
        h2 += 360
    return h1, h2


def _interpolate_rgb(start_rgb: Tuple[int, int, int], end_rgb: Tuple[int, int, int], steps: int) -> List[Tuple[int, int, int]]:
    """在RGB空间进行线性插值

    Args:
        start_rgb: 起始RGB颜色 (r, g, b)
        end_rgb: 结束RGB颜色 (r, g, b)
        steps: 中间色数量

    Returns:
        List[Tuple[int, int, int]]: RGB颜色列表，包含起始色、中间色、结束色
    """
    colors = [start_rgb]
    r1, g1, b1 = start_rgb
    r2, g2, b2 = end_rgb

    total_segments = steps + 1
    for i in range(1, steps + 1):
        t = i / total_segments
        r = round(r1 + (r2 - r1) * t)
        g = round(g1 + (g2 - g1) * t)
        b = round(b1 + (b2 - b1) * t)
        colors.append((r, g, b))

    colors.append(end_rgb)
    return colors


def _interpolate_hsb(start_rgb: Tuple[int, int, int], end_rgb: Tuple[int, int, int], steps: int) -> List[Tuple[int, int, int]]:
    """在HSB空间进行插值，色相沿最短路径过渡

    Args:
        start_rgb: 起始RGB颜色 (r, g, b)
        end_rgb: 结束RGB颜色 (r, g, b)
        steps: 中间色数量

    Returns:
        List[Tuple[int, int, int]]: RGB颜色列表，包含起始色、中间色、结束色
    """
    # 转换为HSB
    h1, s1, b1 = rgb_to_hsb(*start_rgb)
    h2, s2, b2 = rgb_to_hsb(*end_rgb)

    # 归一化色相，使插值沿最短路径
    h1, h2 = _normalize_hue_for_interpolation(h1, h2)

    colors = [start_rgb]
    total_segments = steps + 1

    for i in range(1, steps + 1):
        t = i / total_segments
        h = h1 + (h2 - h1) * t
        s = s1 + (s2 - s1) * t
        b = b1 + (b2 - b1) * t
        # 确保色相在0-360范围内
        h = h % 360
        colors.append(hsb_to_rgb(h, s, b))

    colors.append(end_rgb)
    return colors


def _interpolate_lab(start_rgb: Tuple[int, int, int], end_rgb: Tuple[int, int, int], steps: int) -> List[Tuple[int, int, int]]:
    """在LAB空间进行线性插值

    LAB颜色空间是感知均匀的，插值结果在人眼看来更平滑

    Args:
        start_rgb: 起始RGB颜色 (r, g, b)
        end_rgb: 结束RGB颜色 (r, g, b)
        steps: 中间色数量

    Returns:
        List[Tuple[int, int, int]]: RGB颜色列表，包含起始色、中间色、结束色
    """
    # 转换为LAB
    L1, A1, B1 = rgb_to_lab(*start_rgb)
    L2, A2, B2 = rgb_to_lab(*end_rgb)

    colors = [start_rgb]
    total_segments = steps + 1

    for i in range(1, steps + 1):
        t = i / total_segments
        L = L1 + (L2 - L1) * t
        A = A1 + (A2 - A1) * t
        B = B1 + (B2 - B1) * t
        # 转换回RGB
        colors.append(_lab_to_rgb(L, A, B))

    colors.append(end_rgb)
    return colors


def _lab_to_rgb(L: float, A: float, B: float) -> Tuple[int, int, int]:
    """将LAB颜色空间转换为RGB

    这是rgb_to_lab的逆运算

    Args:
        L: 亮度分量 (0-100)
        A: 红绿对立分量 (-128-127)
        B: 黄蓝对立分量 (-128-127)

    Returns:
        Tuple[int, int, int]: RGB颜色值 (R, G, B)，每个值范围0-255
    """
    # 步骤1: 从LAB转换到XYZ
    def f_inv(t: float) -> float:
        """f函数的逆函数"""
        if t > 0.20689655172413793:  # (6/29)^3 的立方根
            return t ** 3
        else:
            return 3 * 0.12841854934601665 * 0.12841854934601665 * (t - 16 / 116)

    # 参考白点 (D65)
    x_ref, y_ref, z_ref = 0.95047, 1.00000, 1.08883

    # 计算f(Y), f(X), f(Z)
    fy = (L + 16) / 116
    fx = fy + A / 500
    fz = fy - B / 200

    # 计算XYZ
    x = x_ref * f_inv(fx)
    y = y_ref * f_inv(fy)
    z = z_ref * f_inv(fz)

    # 步骤2: 从XYZ转换到线性RGB
    r_linear = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
    g_linear = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
    b_linear = x * 0.0556434 + y * -0.2040259 + z * 1.0572252

    # 步骤3: 应用gamma校正（从线性空间转换到sRGB）
    def linear_to_srgb(c: float) -> float:
        if c <= 0.0031308:
            return c * 12.92
        else:
            return 1.055 * (c ** (1 / 2.4)) - 0.055

    r = max(0, min(255, round(linear_to_srgb(r_linear) * 255)))
    g = max(0, min(255, round(linear_to_srgb(g_linear) * 255)))
    b_out = max(0, min(255, round(linear_to_srgb(b_linear) * 255)))

    return r, g, b_out


def generate_gradient(
    start_hex: str,
    end_hex: str,
    steps: int,
    color_space: str = 'lab'
) -> List[Tuple[int, int, int]]:
    """生成渐变色序列

    支持RGB、HSB、LAB三种颜色空间的插值

    Args:
        start_hex: 起始颜色HEX值，如"#FF0000"
        end_hex: 结束颜色HEX值，如"#0000FF"
        steps: 中间色数量 (1-10)
        color_space: 颜色空间 ('rgb', 'hsb', 'lab')，默认'lab'

    Returns:
        List[Tuple[int, int, int]]: RGB颜色列表，包含起始色、所有中间色、结束色

    Raises:
        ValueError: 当输入的HEX值格式无效时
    """
    # 解析HEX值
    start_rgb = hex_to_rgb(start_hex)
    end_rgb = hex_to_rgb(end_hex)

    # 确保steps在有效范围内
    steps = max(1, min(10, steps))

    # 根据颜色空间选择插值方法
    if color_space == 'rgb':
        return _interpolate_rgb(start_rgb, end_rgb, steps)
    elif color_space == 'hsb':
        return _interpolate_hsb(start_rgb, end_rgb, steps)
    elif color_space == 'lab':
        return _interpolate_lab(start_rgb, end_rgb, steps)
    else:
        # 默认使用LAB空间
        return _interpolate_lab(start_rgb, end_rgb, steps)


def generate_random_gradient(steps: int = 2, color_space: str = 'lab') -> Tuple[str, str, List[Tuple[int, int, int]]]:
    """生成随机渐变色

    Args:
        steps: 中间色数量 (1-10)，默认2
        color_space: 颜色空间 ('rgb', 'hsb', 'lab')，默认'lab'

    Returns:
        Tuple[str, str, List[Tuple[int, int, int]]]: (起始色HEX, 结束色HEX, RGB颜色列表)
    """
    import random

    # 生成随机起始色和结束色
    start_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    end_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    # 转换为HEX
    from .color import rgb_to_hex
    start_hex = rgb_to_hex(*start_rgb)
    end_hex = rgb_to_hex(*end_rgb)

    # 生成渐变
    colors = generate_gradient(start_hex, end_hex, steps, color_space)

    return start_hex, end_hex, colors


def generate_lightness_shades(base_hex: str, count: int = 9) -> List[Tuple[int, int, int]]:
    """生成单色明度梯度

    固定色相和饱和度，明度从高到低均匀分布

    Args:
        base_hex: 基准颜色HEX值，如"#FF5733"
        count: 色阶数量 (3-13)，默认9

    Returns:
        List[Tuple[int, int, int]]: RGB颜色列表

    Raises:
        ValueError: 当输入的HEX值格式无效时
    """
    count = max(3, min(13, count))

    base_rgb = hex_to_rgb(base_hex)
    H, S, _ = rgb_to_hsb(*base_rgb)

    min_brightness = 10
    max_brightness = 95
    step = (max_brightness - min_brightness) / (count - 1)

    colors = []
    for i in range(count):
        B = max_brightness - i * step
        colors.append(hsb_to_rgb(H, S, B))

    return colors


def generate_random_lightness_shade(count: int = 9) -> Tuple[str, List[Tuple[int, int, int]]]:
    """生成随机单色明度梯度

    Args:
        count: 色阶数量 (3-13)，默认9

    Returns:
        Tuple[str, List[Tuple[int, int, int]]]: (基准色HEX, RGB颜色列表)
    """
    import random
    from .color import rgb_to_hex

    base_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    base_hex = rgb_to_hex(*base_rgb)

    colors = generate_lightness_shades(base_hex, count)

    return base_hex, colors
