from __future__ import annotations

# 标准库导入


# 项目模块导入
from .color import hex_to_rgb, rgb_to_hsb, rgb_to_lab, hsb_to_rgb, rgb_to_hsl, hsl_to_rgb


def _normalize_hue_for_interpolation(h1: float, h2: float) -> tuple[float, float]:
    """归一化色相值，使插值沿最短路径

    当色相差值超过180°时，调整色相值使插值沿最短路径
    处理色相跨越0°/360°的情况

    Args:
        h1: 起始色相 (0-360)
        h2: 结束色相 (0-360)

    Returns:
        tuple[float, float]: 调整后的起始色相和结束色相
    """
    diff = h2 - h1
    if diff > 180:
        h2 -= 360
    elif diff < -180:
        h2 += 360
    return h1, h2


def _interpolate_rgb(start_rgb: tuple[int, int, int], end_rgb: tuple[int, int, int], steps: int) -> list[tuple[int, int, int]]:
    """在RGB空间进行线性插值

    Args:
        start_rgb: 起始RGB颜色 (r, g, b)
        end_rgb: 结束RGB颜色 (r, g, b)
        steps: 中间色数量

    Returns:
        list[tuple[int, int, int]]: RGB颜色列表，包含起始色、中间色、结束色
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


def _interpolate_hsb(start_rgb: tuple[int, int, int], end_rgb: tuple[int, int, int], steps: int) -> list[tuple[int, int, int]]:
    """在HSB空间进行插值，色相沿最短路径过渡

    Args:
        start_rgb: 起始RGB颜色 (r, g, b)
        end_rgb: 结束RGB颜色 (r, g, b)
        steps: 中间色数量

    Returns:
        list[tuple[int, int, int]]: RGB颜色列表，包含起始色、中间色、结束色
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


def _interpolate_hsl(start_rgb: tuple[int, int, int], end_rgb: tuple[int, int, int], steps: int) -> list[tuple[int, int, int]]:
    """在HSL空间进行插值，色相沿最短路径过渡

    Args:
        start_rgb: 起始RGB颜色 (r, g, b)
        end_rgb: 结束RGB颜色 (r, g, b)
        steps: 中间色数量

    Returns:
        list[tuple[int, int, int]]: RGB颜色列表，包含起始色、中间色、结束色
    """
    h1, s1, l1 = rgb_to_hsl(*start_rgb)
    h2, s2, l2 = rgb_to_hsl(*end_rgb)

    h1, h2 = _normalize_hue_for_interpolation(h1, h2)

    colors = [start_rgb]
    total_segments = steps + 1

    for i in range(1, steps + 1):
        t = i / total_segments
        h = h1 + (h2 - h1) * t
        s = s1 + (s2 - s1) * t
        l = l1 + (l2 - l1) * t
        h = h % 360
        colors.append(hsl_to_rgb(h, s, l))

    colors.append(end_rgb)
    return colors


def _interpolate_lab(start_rgb: tuple[int, int, int], end_rgb: tuple[int, int, int], steps: int) -> list[tuple[int, int, int]]:
    """在LAB空间进行线性插值

    LAB颜色空间是感知均匀的，插值结果在人眼看来更平滑

    Args:
        start_rgb: 起始RGB颜色 (r, g, b)
        end_rgb: 结束RGB颜色 (r, g, b)
        steps: 中间色数量

    Returns:
        list[tuple[int, int, int]]: RGB颜色列表，包含起始色、中间色、结束色
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


def _lab_to_rgb(L: float, A: float, B: float) -> tuple[int, int, int]:
    """将LAB颜色空间转换为RGB

    这是rgb_to_lab的逆运算

    Args:
        L: 亮度分量 (0-100)
        A: 红绿对立分量 (-128-127)
        B: 黄蓝对立分量 (-128-127)

    Returns:
        tuple[int, int, int]: RGB颜色值 (R, G, B)，每个值范围0-255
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
) -> list[tuple[int, int, int]]:
    """生成渐变色序列

    支持RGB、HSB、HSL、LAB四种颜色空间的插值

    Args:
        start_hex: 起始颜色HEX值，如"#FF0000"
        end_hex: 结束颜色HEX值，如"#0000FF"
        steps: 中间色数量 (1-10)
        color_space: 颜色空间 ('rgb', 'hsb', 'hsl', 'lab')，默认'lab'

    Returns:
        list[tuple[int, int, int]]: RGB颜色列表，包含起始色、所有中间色、结束色

    Raises:
        ValueError: 当输入的HEX值格式无效时
    """
    start_rgb = hex_to_rgb(start_hex)
    end_rgb = hex_to_rgb(end_hex)

    steps = max(1, min(10, steps))

    if color_space == 'rgb':
        return _interpolate_rgb(start_rgb, end_rgb, steps)
    elif color_space == 'hsb':
        return _interpolate_hsb(start_rgb, end_rgb, steps)
    elif color_space == 'hsl':
        return _interpolate_hsl(start_rgb, end_rgb, steps)
    elif color_space == 'lab':
        return _interpolate_lab(start_rgb, end_rgb, steps)
    else:
        return _interpolate_lab(start_rgb, end_rgb, steps)


def generate_random_gradient(steps: int = 2, color_space: str = 'lab') -> tuple[str, str, list[tuple[int, int, int]]]:
    """生成随机渐变色

    Args:
        steps: 中间色数量 (1-10)，默认2
        color_space: 颜色空间 ('rgb', 'hsb', 'hsl', 'lab')，默认'lab'

    Returns:
        tuple[str, str, list[tuple[int, int, int]]]: (起始色HEX, 结束色HEX, RGB颜色列表)
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


def generate_lightness_shades(
    base_hex: str,
    count: int = 9,
    color_space: str = 'hsb'
) -> list[tuple[int, int, int]]:
    """生成单色明度梯度

    固定色相和饱和度，明度从高到低均匀分布
    支持HSB、HSL、LAB三种颜色空间

    Args:
        base_hex: 基准颜色HEX值，如"#FF5733"
        count: 色阶数量 (3-12)，默认9
        color_space: 颜色空间 ('hsb', 'hsl', 'lab')，默认'hsb'

    Returns:
        list[tuple[int, int, int]]: RGB颜色列表

    Raises:
        ValueError: 当输入的HEX值格式无效时
    """
    count = max(3, min(12, count))

    base_rgb = hex_to_rgb(base_hex)

    min_lightness = 10
    max_lightness = 95
    step = (max_lightness - min_lightness) / (count - 1)

    colors = []

    if color_space == 'lab':
        # LAB空间：固定a/b，L从95到10均匀分布
        L, A, B = rgb_to_lab(*base_rgb)
        for i in range(count):
            lightness = max_lightness - i * step
            colors.append(_lab_to_rgb(lightness, A, B))
    elif color_space == 'hsl':
        # HSL空间：固定H/S，L从95%到10%均匀分布
        H, S, _ = rgb_to_hsl(*base_rgb)
        for i in range(count):
            lightness = max_lightness - i * step
            colors.append(hsl_to_rgb(H, S, lightness))
    else:
        # HSB空间（默认）：固定H/S，B从95到10均匀分布
        H, S, _ = rgb_to_hsb(*base_rgb)
        for i in range(count):
            B = max_lightness - i * step
            colors.append(hsb_to_rgb(H, S, B))

    return colors


def generate_random_lightness_shade(
    count: int = 9,
    color_space: str = 'hsb'
) -> tuple[str, list[tuple[int, int, int]]]:
    """生成随机单色明度梯度

    Args:
        count: 色阶数量 (3-12)，默认9
        color_space: 颜色空间 ('hsb', 'hsl', 'lab')，默认'hsb'

    Returns:
        tuple[str, list[tuple[int, int, int]]]: (基准色HEX, RGB颜色列表)
    """
    import random
    from .color import rgb_to_hex

    base_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    base_hex = rgb_to_hex(*base_rgb)

    colors = generate_lightness_shades(base_hex, count, color_space)

    return base_hex, colors


def _interpolate_segment(
    start_rgb: tuple[int, int, int],
    end_rgb: tuple[int, int, int],
    steps: int,
    color_space: str
) -> list[tuple[int, int, int]]:
    """单段颜色插值

    Args:
        start_rgb: 起始RGB颜色
        end_rgb: 结束RGB颜色
        steps: 中间色数量
        color_space: 颜色空间

    Returns:
        list[tuple[int, int, int]]: RGB颜色列表（包含起始色和结束色）
    """
    if steps == 0:
        return [start_rgb, end_rgb]

    if color_space == 'rgb':
        return _interpolate_rgb(start_rgb, end_rgb, steps)
    elif color_space == 'hsb':
        return _interpolate_hsb(start_rgb, end_rgb, steps)
    elif color_space == 'hsl':
        return _interpolate_hsl(start_rgb, end_rgb, steps)
    else:
        return _interpolate_lab(start_rgb, end_rgb, steps)


def generate_three_color_gradient(
    start_hex: str,
    mid_hex: str,
    end_hex: str,
    mid_position: float,
    steps: int,
    color_space: str = 'lab'
) -> list[tuple[int, int, int]]:
    """生成三色渐变色序列

    中间控制色作为中间色之一，根据位置分配两段插值的中间色数量
    总颜色数 = 1(起始) + steps(中间色，包含中间控制色) + 1(结束)

    中间控制色在色卡序列中的索引 = round(mid_position * (steps + 1))
    例如：steps=3, mid_position=0.4, 总颜色数=5
    中间控制色索引 = round(0.4 * 4) = 2 (第3个位置)

    Args:
        start_hex: 起始颜色HEX值
        mid_hex: 中间控制色HEX值
        end_hex: 结束颜色HEX值
        mid_position: 中间控制色位置 (0.1~0.9)
        steps: 中间色总数量 (1-10)，包含中间控制色
        color_space: 颜色空间 ('rgb', 'hsb', 'hsl', 'lab')，默认'lab'

    Returns:
        list[tuple[int, int, int]]: RGB颜色列表

    Raises:
        ValueError: 当输入的HEX值格式无效时
    """
    start_rgb = hex_to_rgb(start_hex)
    mid_rgb = hex_to_rgb(mid_hex)
    end_rgb = hex_to_rgb(end_hex)

    steps = max(1, min(10, steps))
    mid_position = max(0.1, min(0.9, mid_position))

    # 计算中间控制色在色卡序列中的目标索引
    # 总段数 = steps + 1 (从起始到结束)
    total_segments = steps + 1
    target_index = round(mid_position * total_segments)
    # 限制范围：不能在起始(0)或结束(steps+1)位置
    target_index = max(1, min(steps, target_index))

    # A→B 段的中间色数量（在起始色和中间控制色之间）
    steps_first = target_index - 1
    # B→C 段的中间色数量（在中间控制色和结束色之间）
    steps_second = steps - target_index

    # A→B 段：起始色 + 中间色 + 中间控制色
    if steps_first == 0:
        colors_first = [start_rgb, mid_rgb]
    else:
        colors_first = _interpolate_segment(start_rgb, mid_rgb, steps_first, color_space)

    # B→C 段：中间控制色 + 中间色 + 结束色
    if steps_second == 0:
        colors_second = [mid_rgb, end_rgb]
    else:
        colors_second = _interpolate_segment(mid_rgb, end_rgb, steps_second, color_space)

    # 合并，去掉重复的中间控制色
    result = colors_first[:-1] + colors_second

    return result


def generate_random_three_color_gradient(
    steps: int = 2,
    color_space: str = 'lab'
) -> tuple[str, str, str, float, list[tuple[int, int, int]]]:
    """生成随机三色渐变

    Args:
        steps: 中间色数量 (1-10)，默认2
        color_space: 颜色空间 ('rgb', 'hsb', 'hsl', 'lab')，默认'lab'

    Returns:
        tuple: (起始色HEX, 中间色HEX, 结束色HEX, 中间色位置, RGB颜色列表)
    """
    import random
    from .color import rgb_to_hex

    start_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    mid_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    end_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    start_hex = rgb_to_hex(*start_rgb)
    mid_hex = rgb_to_hex(*mid_rgb)
    end_hex = rgb_to_hex(*end_rgb)

    mid_position = random.uniform(0.2, 0.8)

    colors = generate_three_color_gradient(
        start_hex, mid_hex, end_hex, mid_position, steps, color_space
    )

    return start_hex, mid_hex, end_hex, mid_position, colors
