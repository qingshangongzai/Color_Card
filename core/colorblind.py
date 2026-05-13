"""色盲模拟模块

提供各种色盲类型的颜色转换功能。
使用 Machado 2009 LMS 色彩空间矩阵实现准确的色盲模拟。
"""

from __future__ import annotations

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
    },
    'protanomaly': {
        'name': '红色弱',
        'description': '红色视锥细胞功能减弱，对红色敏感度降低。'
    },
    'deuteranomaly': {
        'name': '绿色弱',
        'description': '绿色视锥细胞功能减弱，对绿色敏感度降低，最常见的色觉异常。'
    },
    'tritanomaly': {
        'name': '蓝色弱',
        'description': '蓝色视锥细胞功能减弱，对蓝色敏感度降低，极罕见。'
    },
}

# ========== Machado 2009 矩阵常量 ==========
# 来源: "A Physiologically-based Model for Simulation of Color Vision Deficiency"
# doi: 10.1109/TVCG.2009.113

# RGB → LMS 转换矩阵（Machado 2009, Table I）
MACHADO_LMS_FROM_RGB = [
    [0.3904725,  0.6882901,  -0.0786870],
    [-0.2296649,  1.1833588,  0.0463308],
    [0.0000000,   0.0000000,  1.0000000],
]

# LMS → RGB 转换矩阵（Machado 2009 逆矩阵）
MACHADO_RGB_FROM_LMS = [
    [2.4399508,  -1.4196877,  0.2194128],
    [0.4734952,   0.8066012,  0.0734703],
    [0.0000000,   0.0000000,  1.0000000],
]

# 完全缺失型色盲矩阵（severity=1.0, Machado 2009 Table I）
MACHADO_MATRICES = {
    'protan': [
        [0.152286,   1.052583,  -0.204868],
        [0.114503,   0.786281,   0.099216],
        [-0.003882, -0.048116,   1.051998],
    ],
    'deutan': [
        [0.367322,   0.860646,  -0.227968],
        [0.280085,   0.672501,   0.047413],
        [-0.011820,  0.042940,   0.968881],
    ],
    'tritan': [
        [1.255528,  -0.076749,  -0.178779],
        [-0.078411,  0.930809,   0.147602],
        [0.004733,   0.691367,   0.303900],
    ],
}


def _apply_matrix(v: tuple[float, float, float], m: list[list[float]]) -> tuple[float, float, float]:
    """3x3 矩阵乘以 3 维向量 v"""
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def _gamma_linearize(c: float) -> float:
    """sRGB 非线性通道 → 线性通道"""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _gamma_delinearize(c: float) -> float:
    """线性通道 → sRGB 非线性通道"""
    if c <= 0.0031308:
        return c * 12.92
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _interpolate_matrix(full_matrix: list[list[float]], severity: float) -> list[list[float]]:
    """在单位矩阵和完全缺失矩阵之间做线性插值

    Args:
        full_matrix: severity=1.0 时的完全缺失矩阵
        severity: 严重程度 (0.0-1.0)

    Returns:
        插值后的 3x3 矩阵
    """
    result = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            identity = 1.0 if i == j else 0.0
            result[i][j] = identity * (1.0 - severity) + full_matrix[i][j] * severity
    return result


def _get_blind_matrix(cvd_type: str, severity: float) -> list[list[float]] | None:
    """根据色盲类型和严重程度获取最终变换矩阵

    Args:
        cvd_type: 色盲类型标识
        severity: 严重程度 (0.0-1.0)，仅对 anomal 类型生效

    Returns:
        3x3 变换矩阵，normal/achromatopsia 返回 None
    """
    if cvd_type in ('protanopia', 'protanomaly'):
        matrix_key = 'protan'
    elif cvd_type in ('deuteranopia', 'deuteranomaly'):
        matrix_key = 'deutan'
    elif cvd_type in ('tritanopia', 'tritanomaly'):
        matrix_key = 'tritan'
    else:
        return None

    actual_severity = 1.0 if cvd_type.endswith('opia') else severity
    return _interpolate_matrix(MACHADO_MATRICES[matrix_key], actual_severity)


def simulate_colorblind(
    rgb: tuple[int, int, int],
    cvd_type: str = 'normal',
    severity: float = 0.5
) -> tuple[int, int, int]:
    """模拟指定类型的色盲效果

    Args:
        rgb: 原始 RGB 颜色元组 (r, g, b)，范围 0-255
        cvd_type: 色盲类型，可选值：
            - 'normal': 正常视觉
            - 'protanopia': 红色盲
            - 'deuteranopia': 绿色盲
            - 'tritanopia': 蓝色盲
            - 'achromatopsia': 全色盲
            - 'protanomaly': 红色弱（severity 生效）
            - 'deuteranomaly': 绿色弱（severity 生效）
            - 'tritanomaly': 蓝色弱（severity 生效）
        severity: 严重程度 0.0-1.0，仅对 anomal 类型生效，
                  0.0=正常视觉，1.0=完全缺失

    Returns:
        模拟后的 RGB 颜色元组 (r, g, b)，范围 0-255
    """
    if cvd_type == 'normal':
        return rgb

    R, G, B = rgb

    if cvd_type == 'achromatopsia':
        gray = int(0.299 * R + 0.587 * G + 0.114 * B)
        return (gray, gray, gray)

    # severity 接近 0 时直接返回原值，避免矩阵往返精度损失
    if severity < 0.001:
        return rgb

    matrix = _get_blind_matrix(cvd_type, severity)
    if matrix is None:
        return rgb

    r_norm = R / 255.0
    g_norm = G / 255.0
    b_norm = B / 255.0

    r_lin = _gamma_linearize(r_norm)
    g_lin = _gamma_linearize(g_norm)
    b_lin = _gamma_linearize(b_norm)

    lms = _apply_matrix((r_lin, g_lin, b_lin), MACHADO_LMS_FROM_RGB)

    lms_blind = _apply_matrix(lms, matrix)

    rgb_lin = _apply_matrix(lms_blind, MACHADO_RGB_FROM_LMS)

    r_out = _gamma_delinearize(rgb_lin[0])
    g_out = _gamma_delinearize(rgb_lin[1])
    b_out = _gamma_delinearize(rgb_lin[2])

    return (
        int(max(0, min(255, r_out * 255))),
        int(max(0, min(255, g_out * 255))),
        int(max(0, min(255, b_out * 255))),
    )


def get_colorblind_info(colorblind_type: str) -> dict[str, str]:
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


def get_all_colorblind_types() -> dict[str, dict[str, str]]:
    """获取所有支持的色盲类型

    Returns:
        色盲类型字典，键为类型标识，值为信息字典
    """
    return COLORBLIND_TYPES.copy()