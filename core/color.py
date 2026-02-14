# 标准库导入
import colorsys
from typing import Dict, List, Tuple

# 第三方库导入
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


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


def hex_to_rgb(hex_value: str) -> Tuple[int, int, int]:
    """将16进制颜色值转换为RGB

    Args:
        hex_value: 16进制颜色值，如 "#FF0000" 或 "FF0000"

    Returns:
        tuple: (R 0-255, G 0-255, B 0-255)

    Raises:
        ValueError: 当输入格式无效时
    """
    # 移除 # 前缀和空白字符
    hex_value = hex_value.lstrip('#').strip().upper()

    # 验证长度
    if len(hex_value) != 6:
        raise ValueError("无效的16进制颜色值，必须是6位十六进制数")

    # 验证字符有效性
    if not all(c in '0123456789ABCDEF' for c in hex_value):
        raise ValueError("无效的16进制颜色值，包含非法字符")

    # 转换为RGB
    r = int(hex_value[0:2], 16)
    g = int(hex_value[2:4], 16)
    b = int(hex_value[4:6], 16)

    return r, g, b


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
    """计算图片的明度直方图（使用NumPy向量化优化）

    Args:
        image: QImage 对象
        sample_step: 采样步长，每隔N个像素采样一次（默认4，即1/16的像素）

    Returns:
        list: 长度为256的列表，表示每个明度值的像素数量
    """
    if image is None or image.isNull():
        return [0] * 256

    width = image.width()
    height = image.height()

    # 使用NumPy向量化计算（如果可用）
    if NUMPY_AVAILABLE and hasattr(image, 'bits'):
        try:
            return _calculate_histogram_numpy(image, width, height, sample_step)
        except Exception:
            pass  # 失败时回退到纯Python实现

    return _calculate_histogram_python(image, width, height, sample_step)


def _calculate_histogram_numpy(image, width: int, height: int, sample_step: int) -> List[int]:
    """使用NumPy向量化计算明度直方图"""
    # 将QImage转换为NumPy数组
    image = image.convertToFormat(image.Format.Format_RGB888)
    ptr = image.bits()
    ptr.setsize(image.sizeInBytes())
    arr = np.array(ptr).reshape(height, width, 3)

    # 采样像素（包含边缘像素）
    sampled = arr[::sample_step, ::sample_step]

    # 额外采样边缘像素
    edge_pixels = []
    if width > 0:
        edge_pixels.append(arr[::sample_step, -1])
    if height > 0:
        edge_pixels.append(arr[-1, ::sample_step])

    # 合并所有采样像素
    if edge_pixels:
        all_pixels = np.vstack([sampled.reshape(-1, 3)] + [e.reshape(-1, 3) for e in edge_pixels])
    else:
        all_pixels = sampled.reshape(-1, 3)

    # 向量化计算明度值
    luminance = _calculate_luminance_numpy(all_pixels)

    # 使用bincount统计直方图
    histogram = np.bincount(luminance, minlength=256)

    return histogram.tolist()


def _calculate_luminance_numpy(pixels: np.ndarray) -> np.ndarray:
    """使用NumPy向量化计算明度值（Rec. 709标准 + sRGB Gamma校正）

    Args:
        pixels: NumPy数组，形状为 (N, 3)，值范围 0-255

    Returns:
        np.ndarray: 明度值数组，值范围 0-255
    """
    # 归一化到 0-1 范围
    rgb = pixels.astype(np.float32) / 255.0

    # sRGB Gamma 解码（向量化）
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)

    # 应用 Rec. 709 权重
    luminance_linear = 0.2126 * linear[:, 0] + 0.7152 * linear[:, 1] + 0.0722 * linear[:, 2]

    # 编码回 sRGB 空间
    luminance_srgb = np.where(
        luminance_linear <= 0.0031308,
        luminance_linear * 12.92,
        1.055 * (luminance_linear ** (1.0 / 2.4)) - 0.055
    )

    # 转换到 0-255 范围，使用round与Python实现保持一致
    return np.clip(np.round(luminance_srgb * 255), 0, 255).astype(np.uint8)


def _calculate_histogram_python(image, width: int, height: int, sample_step: int) -> List[int]:
    """使用纯Python计算明度直方图（回退实现）"""
    histogram = [0] * 256

    # 采样计算直方图
    for y in range(0, height, sample_step):
        for x in range(0, width, sample_step):
            color = image.pixelColor(x, y)
            luminance = get_luminance(color.red(), color.green(), color.blue())
            histogram[luminance] += 1

    # 额外采样最右侧和最底部的边缘像素
    if width > 0:
        right_x = width - 1
        for y in range(0, height, sample_step):
            color = image.pixelColor(right_x, y)
            luminance = get_luminance(color.red(), color.green(), color.blue())
            histogram[luminance] += 1

    if height > 0:
        bottom_y = height - 1
        for x in range(0, width, sample_step):
            color = image.pixelColor(x, bottom_y)
            luminance = get_luminance(color.red(), color.green(), color.blue())
            histogram[luminance] += 1

    # 采样右下角像素
    if width > 0 and height > 0:
        color = image.pixelColor(width - 1, height - 1)
        luminance = get_luminance(color.red(), color.green(), color.blue())
        histogram[luminance] += 1

    return histogram


def calculate_rgb_histogram(image, sample_step: int = 4) -> Tuple[List[int], List[int], List[int]]:
    """计算图片的RGB直方图（使用NumPy向量化优化）

    Args:
        image: QImage 对象
        sample_step: 采样步长，每隔N个像素采样一次（默认4，即1/16的像素）

    Returns:
        tuple: 三个长度为256的列表的元组 (R_histogram, G_histogram, B_histogram)
    """
    if image is None or image.isNull():
        return [0] * 256, [0] * 256, [0] * 256

    width = image.width()
    height = image.height()

    # 使用NumPy向量化计算（如果可用）
    if NUMPY_AVAILABLE and hasattr(image, 'bits'):
        try:
            return _calculate_rgb_histogram_numpy(image, width, height, sample_step)
        except Exception:
            pass  # 失败时回退到纯Python实现

    return _calculate_rgb_histogram_python(image, width, height, sample_step)


def _calculate_rgb_histogram_numpy(image, width: int, height: int, sample_step: int) -> Tuple[List[int], List[int], List[int]]:
    """使用NumPy向量化计算RGB直方图"""
    # 将QImage转换为NumPy数组
    image = image.convertToFormat(image.Format.Format_RGB888)
    ptr = image.bits()
    ptr.setsize(image.sizeInBytes())
    arr = np.array(ptr).reshape(height, width, 3)

    # 采样像素（包含边缘像素）
    sampled = arr[::sample_step, ::sample_step]

    # 额外采样边缘像素
    edge_pixels = []
    if width > 0:
        edge_pixels.append(arr[::sample_step, -1])
    if height > 0:
        edge_pixels.append(arr[-1, ::sample_step])

    # 合并所有采样像素
    if edge_pixels:
        all_pixels = np.vstack([sampled.reshape(-1, 3)] + [e.reshape(-1, 3) for e in edge_pixels])
    else:
        all_pixels = sampled.reshape(-1, 3)

    # 分离RGB通道
    r_channel = all_pixels[:, 0].astype(np.uint8)
    g_channel = all_pixels[:, 1].astype(np.uint8)
    b_channel = all_pixels[:, 2].astype(np.uint8)

    # 使用bincount统计各通道直方图
    histogram_r = np.bincount(r_channel, minlength=256)
    histogram_g = np.bincount(g_channel, minlength=256)
    histogram_b = np.bincount(b_channel, minlength=256)

    return histogram_r.tolist(), histogram_g.tolist(), histogram_b.tolist()


def _calculate_rgb_histogram_python(image, width: int, height: int, sample_step: int) -> Tuple[List[int], List[int], List[int]]:
    """使用纯Python计算RGB直方图（回退实现）"""
    histogram_r = [0] * 256
    histogram_g = [0] * 256
    histogram_b = [0] * 256

    # 采样计算直方图
    for y in range(0, height, sample_step):
        for x in range(0, width, sample_step):
            color = image.pixelColor(x, y)
            histogram_r[color.red()] += 1
            histogram_g[color.green()] += 1
            histogram_b[color.blue()] += 1

    # 额外采样最右侧和最底部的边缘像素
    if width > 0:
        right_x = width - 1
        for y in range(0, height, sample_step):
            color = image.pixelColor(right_x, y)
            histogram_r[color.red()] += 1
            histogram_g[color.green()] += 1
            histogram_b[color.blue()] += 1

    if height > 0:
        bottom_y = height - 1
        for x in range(0, width, sample_step):
            color = image.pixelColor(x, bottom_y)
            histogram_r[color.red()] += 1
            histogram_g[color.green()] += 1
            histogram_b[color.blue()] += 1

    # 采样右下角像素
    if width > 0 and height > 0:
        color = image.pixelColor(width - 1, height - 1)
        histogram_r[color.red()] += 1
        histogram_g[color.green()] += 1
        histogram_b[color.blue()] += 1

    return histogram_r, histogram_g, histogram_b


def hsb_to_rgb(h: float, s: float, b: float) -> Tuple[int, int, int]:
    """将HSB转换为RGB

    Args:
        h: 色相 (0-360)
        s: 饱和度 (0-100)
        b: 亮度 (0-100)

    Returns:
        tuple: (R 0-255, G 0-255, B 0-255)
    """
    h_norm = h / 360.0
    s_norm = s / 100.0
    v_norm = b / 100.0

    r, g, b_out = colorsys.hsv_to_rgb(h_norm, s_norm, v_norm)
    return round(r * 255), round(g * 255), round(b_out * 255)


def generate_monochromatic(hue: float, count: int = 4, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成同色系配色方案

    基于同一色相，通过调整饱和度和亮度生成和谐的颜色组合

    Args:
        hue: 基准色相 (0-360)
        count: 生成颜色数量 (默认4)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度序列

    Returns:
        list: HSB颜色列表 [(h, s, b), ...]
    """
    colors = []
    # 基于基准饱和度生成递减的饱和度序列
    if count == 4:
        # 在基准饱和度基础上递减，保持合理的间隔
        saturations = [
            base_saturation,
            max(20, base_saturation * 0.75),
            max(20, base_saturation * 0.5),
            max(20, base_saturation * 0.25)
        ]
        brightnesses = [100, 90, 80, 70]
    else:
        # 根据数量均匀分布饱和度
        step = (base_saturation - 20) / max(count - 1, 1)
        saturations = [max(20, base_saturation - i * step) for i in range(count)]
        brightnesses = [100 - i * (30 / max(count - 1, 1)) for i in range(count)]

    for i in range(count):
        s = max(20, min(100, saturations[i] if i < len(saturations) else 50))
        b = max(40, min(100, brightnesses[i] if i < len(brightnesses) else 70))
        colors.append((hue % 360, s, b))

    return colors


def generate_analogous(hue: float, angle: float = 30, count: int = 4, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成邻近色配色方案

    在色相环上选择与基准色相邻的颜色，创造和谐统一的视觉效果

    Args:
        hue: 基准色相 (0-360)
        angle: 邻近角度范围 (默认30度)
        count: 生成颜色数量 (默认4)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: HSB颜色列表 [(h, s, b), ...]
    """
    colors = []
    if count == 4:
        # 4个颜色：基准色两侧各1个，加上基准色和另一个过渡色
        hues = [
            (hue - angle) % 360,
            (hue - angle / 2) % 360,
            hue % 360,
            (hue + angle / 2) % 360
        ]
    else:
        step = (2 * angle) / max(count - 1, 1)
        hues = [(hue - angle + i * step) % 360 for i in range(count)]

    # 基于基准饱和度生成变化的饱和度
    for i, h in enumerate(hues):
        # 距离基准色越远，饱和度略有变化
        distance_from_center = abs(i - len(hues) / 2) / (len(hues) / 2)
        saturation_variation = 1 - distance_from_center * 0.3  # 变化范围30%
        s = max(60, min(100, base_saturation * saturation_variation))
        colors.append((h, s, 90))

    return colors


def generate_complementary(hue: float, count: int = 5, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成互补色配色方案

    选择色相环上相对位置的颜色（相差180度），创造强烈对比
    所有采样点集中在两个区域：基准色区域和互补色区域

    Args:
        hue: 基准色相 (0-360)
        count: 生成颜色数量 (默认5)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: HSB颜色列表 [(h, s, b), ...]
    """
    colors = []
    comp_hue = (hue + 180) % 360

    if count == 5:
        # 基准色一侧3个：通过调整饱和度和明度来区分，保持色相一致
        colors = [
            (hue, base_saturation, 100),                    # 基准色：最鲜艳
            (hue, max(30, base_saturation * 0.75), 90),     # 基准色：降低饱和度
            (hue, max(30, base_saturation * 0.5), 80),      # 基准色：进一步降低饱和度
            # 互补色一侧2个
            (comp_hue, base_saturation, 100),               # 互补色：最鲜艳
            (comp_hue, max(30, base_saturation * 0.75), 90), # 互补色：降低饱和度
        ]
    else:
        # 平均分配：基准色一侧 ceil(count/2)，互补色一侧 floor(count/2)
        base_count = (count + 1) // 2
        comp_count = count - base_count

        # 基准色一侧：同一色相，基于基准饱和度生成变化
        for i in range(base_count):
            saturation_factor = 1 - i * (0.5 / max(base_count, 1))  # 从100%递减到50%
            s = max(30, base_saturation * saturation_factor)
            b = 100 - i * (20 / max(base_count, 1))  # 明度稍微降低
            colors.append((hue, s, max(80, b)))

        # 互补色一侧：同一色相，基于基准饱和度生成变化
        for i in range(comp_count):
            saturation_factor = 1 - i * (0.5 / max(comp_count, 1))
            s = max(30, base_saturation * saturation_factor)
            b = 100 - i * (20 / max(comp_count, 1))
            colors.append((comp_hue, s, max(80, b)))

    return colors


def generate_split_complementary(hue: float, angle: float = 30, count: int = 3, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成分离补色配色方案

    选择基准色和互补色两侧的颜色，既有对比又更柔和

    Args:
        hue: 基准色相 (0-360)
        angle: 分离角度 (默认30度)
        count: 生成颜色数量 (默认3)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: HSB颜色列表 [(h, s, b), ...]
    """
    colors = []
    comp_hue = (hue + 180) % 360
    left_comp = (comp_hue - angle) % 360
    right_comp = (comp_hue + angle) % 360

    if count == 3:
        # 3个颜色：基准色 + 两个分离补色
        colors = [
            (hue, base_saturation, 100),
            (left_comp, max(50, base_saturation * 0.9), 100),
            (right_comp, max(50, base_saturation * 0.9), 100)
        ]
    else:
        colors.append((hue, base_saturation, 100))
        colors.append((left_comp, max(50, base_saturation * 0.9), 100))
        colors.append((right_comp, max(50, base_saturation * 0.9), 100))
        remaining = count - 3
        for i in range(remaining):
            blend_hue = (hue + (i + 1) * 60) % 360
            s = max(50, base_saturation * (0.7 - i * 0.1))
            colors.append((blend_hue, s, 85))

    return colors


def generate_double_complementary(hue: float, angle: float = 30, count: int = 4, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成双补色配色方案

    选择两组互补色，创造丰富而平衡的配色方案

    Args:
        hue: 基准色相 (0-360)
        angle: 分离角度 (默认30度)
        count: 生成颜色数量 (默认4)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: HSB颜色列表 [(h, s, b), ...]
    """
    colors = []
    comp_hue = (hue + 180) % 360
    second_hue = (hue + angle) % 360
    second_comp = (second_hue + 180) % 360

    if count == 4:
        # 4个颜色：两组互补色，使用基准饱和度
        colors = [
            (hue, base_saturation, 100),
            (comp_hue, max(50, base_saturation * 0.9), 100),
            (second_hue, max(50, base_saturation * 0.9), 100),
            (second_comp, max(50, base_saturation * 0.8), 100)
        ]
    else:
        hues = [hue, comp_hue, second_hue, second_comp]
        saturations = [
            base_saturation,
            max(50, base_saturation * 0.9),
            max(50, base_saturation * 0.9),
            max(50, base_saturation * 0.8)
        ]
        for i in range(min(count, 4)):
            colors.append((hues[i], saturations[i], 95))
        for i in range(4, count):
            blend_hue = (hue + i * 45) % 360
            s = max(50, base_saturation * (0.7 - (i - 4) * 0.1))
            colors.append((blend_hue, s, 85))

    return colors


def adjust_brightness(hsb_colors: List[Tuple[float, float, float]], brightness_delta: float) -> List[Tuple[float, float, float]]:
    """调整配色方案的明度

    Args:
        hsb_colors: HSB颜色列表 [(h, s, b), ...]
        brightness_delta: 明度调整值 (-100 到 +100)

    Returns:
        list: 调整后的HSB颜色列表
    """
    adjusted = []
    for h, s, b in hsb_colors:
        new_b = max(10, min(100, b + brightness_delta))
        adjusted.append((h, s, new_b))
    return adjusted


def get_scheme_preview_colors(scheme_type: str, base_hue: float, count: int = 5, base_saturation: float = 100) -> List[Tuple[int, int, int]]:
    """获取配色方案的预览颜色（RGB格式）

    Args:
        scheme_type: 配色方案类型 ('monochromatic', 'analogous', 'complementary',
                     'split_complementary', 'double_complementary')
        base_hue: 基准色相 (0-360)
        count: 生成颜色数量
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: RGB颜色列表 [(r, g, b), ...]
    """
    # 根据方案类型调用对应的生成器，传递 base_saturation 参数
    if scheme_type == 'monochromatic':
        hsb_colors = generate_monochromatic(base_hue, count, base_saturation)
    elif scheme_type == 'analogous':
        hsb_colors = generate_analogous(base_hue, 30, count, base_saturation)
    elif scheme_type == 'complementary':
        hsb_colors = generate_complementary(base_hue, count, base_saturation)
    elif scheme_type == 'split_complementary':
        hsb_colors = generate_split_complementary(base_hue, 30, count, base_saturation)
    elif scheme_type == 'double_complementary':
        hsb_colors = generate_double_complementary(base_hue, 30, count, base_saturation)
    else:
        hsb_colors = generate_monochromatic(base_hue, count, base_saturation)

    return [hsb_to_rgb(h, s, b) for h, s, b in hsb_colors]


# ==================== MMCQ 主色调提取算法 ====================

class _ColorCube:
    """MMCQ 颜色立方体，用于表示颜色空间中的一个区域"""

    def __init__(self, pixels: List[Tuple[int, int, int]], use_numpy: bool = False):
        """
        Args:
            pixels: RGB 像素列表 [(r, g, b), ...]
            use_numpy: 是否使用 numpy 优化
        """
        self.pixels = pixels
        self._use_numpy = use_numpy and NUMPY_AVAILABLE
        self._cache_volume = None
        self._cache_avg_color = None
        self._cache_ranges = None
        self._np_pixels = None

        # 如果使用 numpy，预先转换为 numpy 数组
        if self._use_numpy and pixels:
            self._np_pixels = np.array(pixels, dtype=np.int32)

    def _get_ranges(self) -> Tuple[int, int, int, int, int, int]:
        """获取各颜色通道的范围（使用缓存）"""
        if self._cache_ranges is not None:
            return self._cache_ranges

        if not self.pixels:
            self._cache_ranges = (0, 0, 0, 0, 0, 0)
            return self._cache_ranges

        if self._use_numpy and self._np_pixels is not None:
            # 使用 numpy 快速计算
            r_min, r_max = int(self._np_pixels[:, 0].min()), int(self._np_pixels[:, 0].max())
            g_min, g_max = int(self._np_pixels[:, 1].min()), int(self._np_pixels[:, 1].max())
            b_min, b_max = int(self._np_pixels[:, 2].min()), int(self._np_pixels[:, 2].max())
        else:
            # 普通方法
            r_min = min(p[0] for p in self.pixels)
            r_max = max(p[0] for p in self.pixels)
            g_min = min(p[1] for p in self.pixels)
            g_max = max(p[1] for p in self.pixels)
            b_min = min(p[2] for p in self.pixels)
            b_max = max(p[2] for p in self.pixels)

        self._cache_ranges = (r_min, r_max, g_min, g_max, b_min, b_max)
        return self._cache_ranges

    def get_volume(self) -> int:
        """计算立方体体积（各颜色通道的范围乘积）"""
        if self._cache_volume is not None:
            return self._cache_volume

        if not self.pixels:
            self._cache_volume = 0
            return 0

        r_min, r_max, g_min, g_max, b_min, b_max = self._get_ranges()
        self._cache_volume = (r_max - r_min) * (g_max - g_min) * (b_max - b_min)
        return self._cache_volume

    def get_count(self) -> int:
        """获取像素数量"""
        return len(self.pixels)

    def get_average_color(self) -> Tuple[int, int, int]:
        """计算立方体内像素的平均颜色"""
        if self._cache_avg_color is not None:
            return self._cache_avg_color

        if not self.pixels:
            self._cache_avg_color = (0, 0, 0)
            return self._cache_avg_color

        if self._use_numpy and self._np_pixels is not None:
            # 使用 numpy 快速计算
            avg = self._np_pixels.mean(axis=0)
            self._cache_avg_color = (int(round(avg[0])), int(round(avg[1])), int(round(avg[2])))
        else:
            # 普通方法
            r_sum = sum(p[0] for p in self.pixels)
            g_sum = sum(p[1] for p in self.pixels)
            b_sum = sum(p[2] for p in self.pixels)
            count = len(self.pixels)

            self._cache_avg_color = (
                round(r_sum / count),
                round(g_sum / count),
                round(b_sum / count)
            )

        return self._cache_avg_color

    def get_longest_axis(self) -> str:
        """获取最长的颜色轴 ('r', 'g', 或 'b')"""
        if not self.pixels:
            return 'r'

        r_min, r_max, g_min, g_max, b_min, b_max = self._get_ranges()

        r_range = r_max - r_min
        g_range = g_max - g_min
        b_range = b_max - b_min

        max_range = max(r_range, g_range, b_range)
        if max_range == r_range:
            return 'r'
        elif max_range == g_range:
            return 'g'
        else:
            return 'b'

    def split(self) -> Tuple['_ColorCube', '_ColorCube']:
        """沿最长轴的中位数切分立方体"""
        if not self.pixels:
            return _ColorCube([], self._use_numpy), _ColorCube([], self._use_numpy)

        axis = self.get_longest_axis()
        axis_index = {'r': 0, 'g': 1, 'b': 2}[axis]

        if self._use_numpy and self._np_pixels is not None:
            # 使用 numpy 快速排序
            sorted_indices = np.argsort(self._np_pixels[:, axis_index])
            mid = len(sorted_indices) // 2

            pixels1 = [self.pixels[i] for i in sorted_indices[:mid]]
            pixels2 = [self.pixels[i] for i in sorted_indices[mid:]]
        else:
            # 普通方法
            sorted_pixels = sorted(self.pixels, key=lambda p: p[axis_index])
            mid = len(sorted_pixels) // 2
            pixels1 = sorted_pixels[:mid]
            pixels2 = sorted_pixels[mid:]

        # 切分为两个立方体
        cube1 = _ColorCube(pixels1, self._use_numpy)
        cube2 = _ColorCube(pixels2, self._use_numpy)

        return cube1, cube2


def _mmcq_quantize(pixels: List[Tuple[int, int, int]], count: int) -> List[_ColorCube]:
    """MMCQ 算法核心实现

    Args:
        pixels: RGB 像素列表
        count: 目标颜色数量

    Returns:
        list: 颜色立方体列表
    """
    if not pixels or count <= 0:
        return []

    # 判断是否使用 numpy 优化（像素数量较多时）
    use_numpy = NUMPY_AVAILABLE and len(pixels) > 1000

    # 初始立方体包含所有像素
    cubes = [_ColorCube(pixels, use_numpy)]

    # 递归切分直到达到目标数量
    while len(cubes) < count:
        # 找到体积最大的立方体进行切分
        max_volume = -1
        cube_to_split = None
        cube_index = -1

        for i, cube in enumerate(cubes):
            # 优先切分像素数量多且体积大的立方体
            volume = cube.get_volume()
            pixel_count = cube.get_count()
            if pixel_count > 1 and volume > max_volume:
                max_volume = volume
                cube_to_split = cube
                cube_index = i

        if cube_to_split is None or cube_to_split.get_count() <= 1:
            break

        # 移除原立方体，添加切分后的两个立方体
        cubes.pop(cube_index)
        cube1, cube2 = cube_to_split.split()
        cubes.append(cube1)
        cubes.append(cube2)

    return cubes


def _extract_pixels_fast(image, sample_step: int = 4) -> List[Tuple[int, int, int]]:
    """快速提取图片像素数据

    使用 numpy 优化像素提取性能。

    Args:
        image: QImage 或 PIL Image 对象
        sample_step: 采样步长

    Returns:
        list: RGB 像素列表
    """
    pixels = []

    # 处理 QImage
    if hasattr(image, 'width') and hasattr(image, 'height'):
        width = image.width()
        height = image.height()

        if NUMPY_AVAILABLE and hasattr(image, 'bits'):
            # 使用 numpy 批量读取像素（QImage 格式）
            try:
                # 将 QImage 转换为 numpy 数组
                image = image.convertToFormat(image.Format.Format_RGB888)
                ptr = image.bits()
                ptr.setsize(image.sizeInBytes())
                arr = np.array(ptr).reshape(height, width, 3)

                # 采样像素
                arr_sampled = arr[::sample_step, ::sample_step]
                pixels = [(int(r), int(g), int(b)) for r, g, b in arr_sampled.reshape(-1, 3)]

                # 额外采样边缘像素
                if width > 0 and height > 0:
                    right_edge = arr[::sample_step, -1]
                    bottom_edge = arr[-1, ::sample_step]
                    pixels.extend([(int(r), int(g), int(b)) for r, g, b in right_edge])
                    pixels.extend([(int(r), int(g), int(b)) for r, g, b in bottom_edge])

                return pixels
            except Exception:
                pass  # 失败时回退到普通方法

        # 普通方法（逐个读取）
        for y in range(0, height, sample_step):
            for x in range(0, width, sample_step):
                color = image.pixelColor(x, y)
                pixels.append((color.red(), color.green(), color.blue()))

        # 额外采样边缘像素
        if width > 0 and height > 0:
            for y in range(0, height, sample_step):
                color = image.pixelColor(width - 1, y)
                pixels.append((color.red(), color.green(), color.blue()))
            for x in range(0, width, sample_step):
                color = image.pixelColor(x, height - 1)
                pixels.append((color.red(), color.green(), color.blue()))

    # 处理 PIL Image
    elif hasattr(image, 'size') and hasattr(image, 'getpixel'):
        width, height = image.size

        if NUMPY_AVAILABLE and hasattr(image, 'convert'):
            # 使用 numpy 批量读取像素（PIL Image 格式）
            try:
                import numpy as np
                arr = np.array(image.convert('RGB'))

                # 采样像素
                arr_sampled = arr[::sample_step, ::sample_step]
                pixels = [(int(r), int(g), int(b)) for r, g, b in arr_sampled.reshape(-1, 3)]

                # 额外采样边缘像素
                if width > 0 and height > 0:
                    right_edge = arr[::sample_step, -1]
                    bottom_edge = arr[-1, ::sample_step]
                    pixels.extend([(int(r), int(g), int(b)) for r, g, b in right_edge])
                    pixels.extend([(int(r), int(g), int(b)) for r, g, b in bottom_edge])

                return pixels
            except Exception:
                pass  # 失败时回退到普通方法

        # 普通方法
        for y in range(0, height, sample_step):
            for x in range(0, width, sample_step):
                pixel = image.getpixel((x, y))
                if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
                    pixels.append((pixel[0], pixel[1], pixel[2]))

    return pixels


def extract_dominant_colors(
    image,
    count: int = 5,
    sample_step: int = 4
) -> List[Tuple[int, int, int]]:
    """使用 MMCQ 算法提取图片主色调

    基于中位切分量化算法，递归分割颜色空间来提取主要颜色。
    使用采样策略和 numpy 优化性能。

    Args:
        image: QImage 或 PIL Image 对象
        count: 提取颜色数量 (3-8，默认5)
        sample_step: 采样步长，每隔N个像素采样一次（默认4）

    Returns:
        list: RGB 主色调列表 [(r, g, b), ...]，按重要性排序
    """
    # 限制颜色数量范围
    count = max(3, min(8, count))

    # 提取像素数据（使用优化后的方法）
    pixels = _extract_pixels_fast(image, sample_step)

    if not pixels:
        return []

    # 执行 MMCQ 算法
    cubes = _mmcq_quantize(pixels, count)

    # 按像素数量排序（数量越多越重要）
    cubes.sort(key=lambda c: c.get_count(), reverse=True)

    # 提取平均颜色
    dominant_colors = [cube.get_average_color() for cube in cubes]

    return dominant_colors


def _extract_pixels_with_positions_fast(
    image,
    sample_step: int = 4
) -> Tuple[int, int, List[Tuple[int, int, int, int, int]]]:
    """快速提取图片像素数据及其位置

    Args:
        image: QImage 或 PIL Image 对象
        sample_step: 采样步长

    Returns:
        tuple: (width, height, pixel_data) 其中 pixel_data 是 [(x, y, r, g, b), ...]
    """
    pixel_data = []
    width, height = 0, 0

    # 处理 QImage
    if hasattr(image, 'width') and hasattr(image, 'height'):
        width = image.width()
        height = image.height()

        if NUMPY_AVAILABLE and hasattr(image, 'bits'):
            # 使用 numpy 批量读取像素
            try:
                image = image.convertToFormat(image.Format.Format_RGB888)
                ptr = image.bits()
                ptr.setsize(image.sizeInBytes())
                arr = np.array(ptr).reshape(height, width, 3)

                # 采样像素位置
                y_coords, x_coords = np.meshgrid(
                    np.arange(0, height, sample_step),
                    np.arange(0, width, sample_step),
                    indexing='ij'
                )

                for y, x in zip(y_coords.flat, x_coords.flat):
                    r, g, b = arr[y, x]
                    pixel_data.append((int(x), int(y), int(r), int(g), int(b)))

                return width, height, pixel_data
            except Exception:
                pass  # 失败时回退到普通方法

        # 普通方法
        for y in range(0, height, sample_step):
            for x in range(0, width, sample_step):
                color = image.pixelColor(x, y)
                pixel_data.append((x, y, color.red(), color.green(), color.blue()))

    # 处理 PIL Image
    elif hasattr(image, 'size') and hasattr(image, 'getpixel'):
        width, height = image.size

        if NUMPY_AVAILABLE and hasattr(image, 'convert'):
            # 使用 numpy 批量读取像素
            try:
                arr = np.array(image.convert('RGB'))

                # 采样像素位置
                y_coords, x_coords = np.meshgrid(
                    np.arange(0, height, sample_step),
                    np.arange(0, width, sample_step),
                    indexing='ij'
                )

                for y, x in zip(y_coords.flat, x_coords.flat):
                    r, g, b = arr[y, x]
                    pixel_data.append((int(x), int(y), int(r), int(g), int(b)))

                return width, height, pixel_data
            except Exception:
                pass  # 失败时回退到普通方法

        # 普通方法
        for y in range(0, height, sample_step):
            for x in range(0, width, sample_step):
                pixel = image.getpixel((x, y))
                if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
                    pixel_data.append((x, y, pixel[0], pixel[1], pixel[2]))

    return width, height, pixel_data


def find_dominant_color_positions(
    image,
    dominant_colors: List[Tuple[int, int, int]],
    sample_step: int = 4
) -> List[Tuple[float, float]]:
    """找到每种主色调在图片中的代表性位置

    使用聚类思想，找到每种主色调在图片中的重心位置。
    使用 numpy 优化性能。

    Args:
        image: QImage 或 PIL Image 对象
        dominant_colors: 主色调列表 [(r, g, b), ...]
        sample_step: 采样步长（默认4）

    Returns:
        list: 相对坐标列表 [(rel_x, rel_y), ...]，与 dominant_colors 一一对应
    """
    if not dominant_colors:
        return []

    # 提取像素数据及其位置（使用优化后的方法）
    width, height, pixel_data = _extract_pixels_with_positions_fast(image, sample_step)

    if not pixel_data or width == 0 or height == 0:
        # 返回默认中心位置
        return [(0.5, 0.5)] * len(dominant_colors)

    # 使用 numpy 加速聚类计算
    if NUMPY_AVAILABLE and len(pixel_data) > 100:
        try:
            # 转换为 numpy 数组
            pixel_array = np.array(pixel_data, dtype=np.float32)  # [x, y, r, g, b]
            dominant_array = np.array(dominant_colors, dtype=np.float32)  # [r, g, b]

            # 提取颜色部分
            pixel_colors = pixel_array[:, 2:5]  # [r, g, b]

            # 计算每个像素到每个主色调的距离
            # 使用广播: (n_pixels, 1, 3) - (1, n_colors, 3) -> (n_pixels, n_colors)
            diff = pixel_colors[:, np.newaxis, :] - dominant_array[np.newaxis, :, :]
            distances = np.sum(diff ** 2, axis=2)  # 平方距离

            # 找到每个像素最接近的主色调
            closest_indices = np.argmin(distances, axis=1)

            # 计算每种颜色的重心位置
            positions = []
            for i in range(len(dominant_colors)):
                mask = closest_indices == i
                cluster = pixel_array[mask]

                if len(cluster) > 0:
                    avg_x = cluster[:, 0].mean()
                    avg_y = cluster[:, 1].mean()
                    positions.append((avg_x / width, avg_y / height))
                else:
                    positions.append((0.5, 0.5))

            return positions
        except Exception:
            pass  # 失败时回退到普通方法

    # 普通方法（当 numpy 不可用或数据量较小时）
    color_clusters = [[] for _ in dominant_colors]

    # 将每个像素归类到最接近的主色调
    for x, y, r, g, b in pixel_data:
        min_distance = float('inf')
        closest_color_index = 0

        for i, (dr, dg, db) in enumerate(dominant_colors):
            distance = ((r - dr) ** 2 + (g - dg) ** 2 + (b - db) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_color_index = i

        color_clusters[closest_color_index].append((x, y))

    # 计算每种颜色的重心位置
    positions = []
    for cluster in color_clusters:
        if cluster:
            avg_x = sum(p[0] for p in cluster) / len(cluster)
            avg_y = sum(p[1] for p in cluster) / len(cluster)
            positions.append((avg_x / width, avg_y / height))
        else:
            positions.append((0.5, 0.5))

    return positions


# ==================== RYB 色彩空间支持 ====================

# RYB 色相映射表：RGB色相角度 -> RYB色相角度
# 基于传统美术色轮的红-黄-蓝三原色系统
RYB_HUE_MAP_RGB_TO_RYB = {
    0: 0,       # 红
    30: 30,     # 橙红
    60: 60,     # 橙
    90: 90,     # 橙黄
    120: 120,   # 黄
    150: 150,   # 黄绿
    180: 180,   # 绿（RYB中绿在180度）
    210: 210,   # 青绿
    240: 240,   # 青
    270: 270,   # 蓝
    300: 300,   # 紫
    330: 330,   # 品红
    360: 360,   # 红
}

# RYB 色相映射表：RYB色相角度 -> RGB色相角度
RYB_HUE_MAP_RYB_TO_RGB = {
    0: 0,       # 红
    30: 30,     # 橙红
    60: 60,     # 橙
    90: 90,     # 橙黄
    120: 120,   # 黄
    150: 150,   # 黄绿
    180: 180,   # 绿（RYB中绿在180度，RGB中绿在120度）
    210: 210,   # 青绿
    240: 240,   # 青
    270: 270,   # 蓝
    300: 300,   # 紫
    330: 330,   # 品红
    360: 360,   # 红
}


def rgb_hue_to_ryb_hue(rgb_hue: float) -> float:
    """将 RGB 色相转换为 RYB 色相

    RYB色轮是传统美术色轮，三原色为红、黄、蓝
    与RGB色轮的主要差异：
    - RYB中绿色在180度（黄和蓝之间）
    - RGB中绿色在120度

    Args:
        rgb_hue: RGB色相 (0-360)

    Returns:
        float: RYB色相 (0-360)
    """
    # 规范化色相到 0-360
    hue = rgb_hue % 360

    # 分段线性映射
    # RGB: 红(0) -> 黄(60) -> 绿(120) -> 青(180) -> 蓝(240) -> 紫(300) -> 红(360)
    # RYB: 红(0) -> 橙(60) -> 黄(120) -> 绿(180) -> 蓝(240) -> 紫(300) -> 红(360)

    if hue <= 60:
        # 红到黄区域：RGB 0-60 -> RYB 0-120
        return hue * 2
    elif hue <= 120:
        # 黄到绿区域：RGB 60-120 -> RYB 120-180
        return 120 + (hue - 60)
    elif hue <= 180:
        # 绿到青区域：RGB 120-180 -> RYB 180-210
        return 180 + (hue - 120) * 0.5
    elif hue <= 240:
        # 青到蓝区域：RGB 180-240 -> RYB 210-240
        return 210 + (hue - 180) * 0.5
    else:
        # 蓝到红区域：RGB 240-360 -> RYB 240-360
        return hue


def ryb_hue_to_rgb_hue(ryb_hue: float) -> float:
    """将 RYB 色相转换为 RGB 色相

    Args:
        ryb_hue: RYB色相 (0-360)

    Returns:
        float: RGB色相 (0-360)
    """
    # 规范化色相到 0-360
    hue = ryb_hue % 360

    # 反向映射
    if hue <= 120:
        # 红到黄区域：RYB 0-120 -> RGB 0-60
        return hue * 0.5
    elif hue <= 180:
        # 黄到绿区域：RYB 120-180 -> RGB 60-120
        return 60 + (hue - 120)
    elif hue <= 210:
        # 绿到青区域：RYB 180-210 -> RGB 120-180
        return 120 + (hue - 180) * 2
    elif hue <= 240:
        # 青到蓝区域：RYB 210-240 -> RGB 180-240
        return 180 + (hue - 210) * 2
    else:
        # 蓝到红区域：RYB 240-360 -> RGB 240-360
        return hue


def generate_ryb_monochromatic(ryb_hue: float, count: int = 4, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成 RYB 同色系配色方案

    Args:
        ryb_hue: RYB基准色相 (0-360)
        count: 生成颜色数量 (默认4)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度序列

    Returns:
        list: HSB颜色列表 [(h, s, b), ...] (RGB色相)
    """
    colors = []
    # 基于基准饱和度生成递减的饱和度序列
    if count == 4:
        saturations = [
            base_saturation,
            max(20, base_saturation * 0.75),
            max(20, base_saturation * 0.5),
            max(20, base_saturation * 0.25)
        ]
        brightnesses = [100, 90, 80, 70]
    else:
        step = (base_saturation - 20) / max(count - 1, 1)
        saturations = [max(20, base_saturation - i * step) for i in range(count)]
        brightnesses = [100 - i * (30 / max(count - 1, 1)) for i in range(count)]

    # 转换 RYB 色相到 RGB 色相
    rgb_hue = ryb_hue_to_rgb_hue(ryb_hue)

    for i in range(count):
        s = max(20, min(100, saturations[i] if i < len(saturations) else 50))
        b = max(40, min(100, brightnesses[i] if i < len(brightnesses) else 70))
        colors.append((rgb_hue % 360, s, b))

    return colors


def generate_ryb_analogous(ryb_hue: float, angle: float = 30, count: int = 4, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成 RYB 邻近色配色方案

    Args:
        ryb_hue: RYB基准色相 (0-360)
        angle: 邻近角度范围 (默认30度)
        count: 生成颜色数量 (默认4)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: HSB颜色列表 [(h, s, b), ...] (RGB色相)
    """
    colors = []
    if count == 4:
        # 4个颜色：基准色两侧各1个，加上基准色和另一个过渡色
        ryb_hues = [
            (ryb_hue - angle) % 360,
            (ryb_hue - angle / 2) % 360,
            ryb_hue % 360,
            (ryb_hue + angle / 2) % 360
        ]
    else:
        step = (2 * angle) / max(count - 1, 1)
        ryb_hues = [(ryb_hue - angle + i * step) % 360 for i in range(count)]

    # 基于基准饱和度生成变化的饱和度
    for i, h in enumerate(ryb_hues):
        # 距离基准色越远，饱和度略有变化
        distance_from_center = abs(i - len(ryb_hues) / 2) / (len(ryb_hues) / 2)
        saturation_variation = 1 - distance_from_center * 0.3  # 变化范围30%
        s = max(60, min(100, base_saturation * saturation_variation))
        # 转换 RYB 色相到 RGB 色相
        rgb_hue = ryb_hue_to_rgb_hue(h)
        colors.append((rgb_hue, s, 90))

    return colors


def generate_ryb_complementary(ryb_hue: float, count: int = 5, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成 RYB 互补色配色方案

    在RYB色轮中，互补色相差180度

    Args:
        ryb_hue: RYB基准色相 (0-360)
        count: 生成颜色数量 (默认5)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: HSB颜色列表 [(h, s, b), ...] (RGB色相)
    """
    colors = []
    ryb_comp_hue = (ryb_hue + 180) % 360

    # 转换到 RGB 色相
    rgb_hue = ryb_hue_to_rgb_hue(ryb_hue)
    rgb_comp_hue = ryb_hue_to_rgb_hue(ryb_comp_hue)

    if count == 5:
        # 基准色一侧3个：通过调整饱和度和明度来区分
        colors = [
            (rgb_hue, base_saturation, 100),
            (rgb_hue, max(30, base_saturation * 0.75), 90),
            (rgb_hue, max(30, base_saturation * 0.5), 80),
            # 互补色一侧2个
            (rgb_comp_hue, base_saturation, 100),
            (rgb_comp_hue, max(30, base_saturation * 0.75), 90),
        ]
    else:
        # 平均分配
        base_count = (count + 1) // 2
        comp_count = count - base_count

        for i in range(base_count):
            saturation_factor = 1 - i * (0.5 / max(base_count, 1))  # 从100%递减到50%
            s = max(30, base_saturation * saturation_factor)
            b = 100 - i * (20 / max(base_count, 1))
            colors.append((rgb_hue, s, max(80, b)))

        for i in range(comp_count):
            saturation_factor = 1 - i * (0.5 / max(comp_count, 1))
            s = max(30, base_saturation * saturation_factor)
            b = 100 - i * (20 / max(comp_count, 1))
            colors.append((rgb_comp_hue, s, max(80, b)))

    return colors


def generate_ryb_split_complementary(ryb_hue: float, angle: float = 30, count: int = 3, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成 RYB 分离补色配色方案

    Args:
        ryb_hue: RYB基准色相 (0-360)
        angle: 分离角度 (默认30度)
        count: 生成颜色数量 (默认3)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: HSB颜色列表 [(h, s, b), ...] (RGB色相)
    """
    colors = []
    ryb_comp_hue = (ryb_hue + 180) % 360
    ryb_left_comp = (ryb_comp_hue - angle) % 360
    ryb_right_comp = (ryb_comp_hue + angle) % 360

    # 转换到 RGB 色相
    rgb_hue = ryb_hue_to_rgb_hue(ryb_hue)
    rgb_left = ryb_hue_to_rgb_hue(ryb_left_comp)
    rgb_right = ryb_hue_to_rgb_hue(ryb_right_comp)

    if count == 3:
        colors = [
            (rgb_hue, base_saturation, 100),
            (rgb_left, max(50, base_saturation * 0.9), 100),
            (rgb_right, max(50, base_saturation * 0.9), 100)
        ]
    else:
        colors.append((rgb_hue, base_saturation, 100))
        colors.append((rgb_left, max(50, base_saturation * 0.9), 100))
        colors.append((rgb_right, max(50, base_saturation * 0.9), 100))
        remaining = count - 3
        for i in range(remaining):
            blend_hue = (ryb_hue + (i + 1) * 60) % 360
            rgb_blend = ryb_hue_to_rgb_hue(blend_hue)
            s = max(50, base_saturation * (0.7 - i * 0.1))
            colors.append((rgb_blend, s, 85))

    return colors


def generate_ryb_double_complementary(ryb_hue: float, angle: float = 30, count: int = 4, base_saturation: float = 100) -> List[Tuple[float, float, float]]:
    """生成 RYB 双补色配色方案

    Args:
        ryb_hue: RYB基准色相 (0-360)
        angle: 分离角度 (默认30度)
        count: 生成颜色数量 (默认4)
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: HSB颜色列表 [(h, s, b), ...] (RGB色相)
    """
    colors = []
    ryb_comp_hue = (ryb_hue + 180) % 360
    ryb_second_hue = (ryb_hue + angle) % 360
    ryb_second_comp = (ryb_second_hue + 180) % 360

    # 转换到 RGB 色相
    rgb_hue = ryb_hue_to_rgb_hue(ryb_hue)
    rgb_comp = ryb_hue_to_rgb_hue(ryb_comp_hue)
    rgb_second = ryb_hue_to_rgb_hue(ryb_second_hue)
    rgb_second_comp = ryb_hue_to_rgb_hue(ryb_second_comp)

    if count == 4:
        colors = [
            (rgb_hue, base_saturation, 100),
            (rgb_comp, max(50, base_saturation * 0.9), 100),
            (rgb_second, max(50, base_saturation * 0.9), 100),
            (rgb_second_comp, max(50, base_saturation * 0.8), 100)
        ]
    else:
        hues = [rgb_hue, rgb_comp, rgb_second, rgb_second_comp]
        saturations = [
            base_saturation,
            max(50, base_saturation * 0.9),
            max(50, base_saturation * 0.9),
            max(50, base_saturation * 0.8)
        ]
        for i in range(min(count, 4)):
            colors.append((hues[i], saturations[i], 95))
        for i in range(4, count):
            blend_ryb = (ryb_hue + i * 45) % 360
            rgb_blend = ryb_hue_to_rgb_hue(blend_ryb)
            s = max(50, base_saturation * (0.7 - (i - 4) * 0.1))
            colors.append((rgb_blend, s, 85))

    return colors


def get_scheme_preview_colors_ryb(scheme_type: str, base_hue: float, count: int = 5, base_saturation: float = 100) -> List[Tuple[int, int, int]]:
    """获取 RYB 配色方案的预览颜色（RGB格式）

    Args:
        scheme_type: 配色方案类型 ('monochromatic', 'analogous', 'complementary',
                     'split_complementary', 'double_complementary')
        base_hue: 基准色相 (0-360，RGB色相)
        count: 生成颜色数量
        base_saturation: 基准饱和度 (0-100)，用于生成变化的饱和度

    Returns:
        list: RGB颜色列表 [(r, g, b), ...]
    """
    # 先将 RGB 色相转换为 RYB 色相
    ryb_hue = rgb_hue_to_ryb_hue(base_hue)

    # 根据方案类型调用对应的 RYB 生成器，传递 base_saturation 参数
    if scheme_type == 'monochromatic':
        hsb_colors = generate_ryb_monochromatic(ryb_hue, count, base_saturation)
    elif scheme_type == 'analogous':
        hsb_colors = generate_ryb_analogous(ryb_hue, 30, count, base_saturation)
    elif scheme_type == 'complementary':
        hsb_colors = generate_ryb_complementary(ryb_hue, count, base_saturation)
    elif scheme_type == 'split_complementary':
        hsb_colors = generate_ryb_split_complementary(ryb_hue, 30, count, base_saturation)
    elif scheme_type == 'double_complementary':
        hsb_colors = generate_ryb_double_complementary(ryb_hue, 30, count, base_saturation)
    else:
        hsb_colors = generate_ryb_monochromatic(ryb_hue, count, base_saturation)

    return [hsb_to_rgb(h, s, b) for h, s, b in hsb_colors]
