"""颜色空间转换（sRGB、OKLab、OKLCH、HSB 色相）的纯 NumPy 实现

只依赖标准库与 NumPy，不导入 PySide6，也不使用相对导入——构建脚本可按
文件路径直接加载，避免执行 core/__init__.py 时拉入 GUI 依赖。
"""

from __future__ import annotations

import numpy as np

# Ottosson OKLab 线性 RGB → LMS 矩阵
_M1 = np.array([
    [0.4122214708, 0.5363325363, 0.0514459929],
    [0.2119034982, 0.6806995451, 0.1073969566],
    [0.0883024619, 0.2817188376, 0.6299787005],
], dtype=np.float64)

# LMS'（立方根后）→ OKLab 矩阵
_M2 = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660],
], dtype=np.float64)

# 逆矩阵预计算（oklab → sRGB 还原用）
_M1_INV = np.linalg.inv(_M1)
_M2_INV = np.linalg.inv(_M2)


def srgb_to_linear_array(srgb: np.ndarray) -> np.ndarray:
    """sRGB 传递函数解码到线性 RGB（分段 gamma）

    这一步不可省略：直接对 gamma 值做矩阵运算是最常见的 OKLab 实现错误。
    """
    a = 0.055
    return np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + a) / (1 + a)) ** 2.4,
    )


def _srgb01_to_oklab(x: np.ndarray) -> np.ndarray:
    """已归一化到 0~1 的 sRGB 转 OKLab（不再猜测量程）"""
    linear = srgb_to_linear_array(x)
    lms = linear @ _M1.T
    lms_cbrt = np.cbrt(lms)
    return lms_cbrt @ _M2.T


def srgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    """sRGB（0~1 或 0~255）转 OKLab

    Args:
        rgb: (..., 3) 数组，float(0~1) 或 uint8(0~255)

    Returns:
        (..., 3) 的 OKLab 数组 [L, a, b]
    """
    x = np.asarray(rgb, dtype=np.float64)
    if x.max() > 1.0 + 1e-6:
        x = x / 255.0
    return _srgb01_to_oklab(x)


def srgb255_to_oklab(rgb: tuple[int, int, int]) -> np.ndarray:
    """sRGB 0~255 三元组转 OKLab，显式除以 255 后再转换

    不走 srgb_to_oklab 的 max() > 1 量程猜测：rgb=(0,0,1) 是近黑，
    不能被当作满通道蓝。
    """
    x = np.asarray(rgb, dtype=np.float64) / 255.0
    return _srgb01_to_oklab(x)


def oklab_to_lch(lab: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """OKLab 转 L / C / h（h 单位为度，范围 0~360）"""
    L = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]
    C = np.sqrt(a * a + b * b)
    h = np.degrees(np.arctan2(b, a)) % 360.0
    return L, C, h


def oklab_to_srgb_float(lab: np.ndarray) -> np.ndarray:
    """OKLab 转 sRGB 浮点（0~1 裁剪）"""
    lms_cbrt = lab @ _M2_INV.T
    lms = lms_cbrt ** 3
    linear = lms @ _M1_INV.T
    a = 0.055
    srgb = np.where(
        linear <= 0.0031308,
        linear * 12.92,
        (1 + a) * np.clip(linear, 0, None) ** (1 / 2.4) - a,
    )
    return np.clip(srgb, 0.0, 1.0)


def oklab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """OKLab 转 sRGB（0~255 uint8），用于主色卡还原"""
    return (oklab_to_srgb_float(lab) * 255.0).astype(np.uint8)


def srgb_hsb_hue(srgb: np.ndarray) -> np.ndarray:
    """sRGB 浮点（0~1）转 HSB 色相角（供已有 sRGB 数组时免重复转换）"""
    r = srgb[..., 0]
    g = srgb[..., 1]
    b = srgb[..., 2]
    mx = np.max(srgb, axis=-1)
    delta = mx - np.min(srgb, axis=-1)

    hue = np.zeros_like(mx)
    nz = delta > 1e-12
    rm = nz & (mx == r)
    gm = nz & (mx == g) & ~rm
    bm = nz & (mx == b) & ~rm & ~gm
    hue[rm] = (60.0 * (g[rm] - b[rm]) / delta[rm]) % 360.0
    hue[gm] = 60.0 * (b[gm] - r[gm]) / delta[gm] + 120.0
    hue[bm] = 60.0 * (r[bm] - g[bm]) / delta[bm] + 240.0
    return hue % 360.0


def oklab_to_hsb_hue(lab: np.ndarray) -> np.ndarray:
    """OKLab 转 HSB 色相角（度，0~360），主项目色相标准的坐标轴

    统计权重仍用 OKLCH chroma，仅色相角度/色名按 HSB 轴展示，
    与主项目色环及拾色器读数一致。
    """
    return srgb_hsb_hue(oklab_to_srgb_float(lab))
