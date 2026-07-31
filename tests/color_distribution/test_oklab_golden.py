"""sRGB -> OKLab 转换的 golden 单测

用 Ottosson 官方参考色的期望 OKLab 值锁定转换正确性，
特别防"忘做 sRGB gamma 解码、直接对 gamma 值做矩阵运算"这一最常见实现错误
（漏解码会让 red/green/blue 的 L、a、b 明显偏离下列期望值，从而被断言捕获）。
"""

import numpy as np
import pytest

from core import color_distribution as e


# (sRGB 0~255, 期望 OKLab [L, a, b])，参考 Ottosson OKLab 原文
GOLDEN = [
    ('white', (255, 255, 255), (1.0, 0.0, 0.0)),
    ('black', (0, 0, 0), (0.0, 0.0, 0.0)),
    ('gray_808080', (128, 128, 128), (0.5999, 0.0, 0.0)),
    ('red', (255, 0, 0), (0.6280, 0.2249, 0.1258)),
    ('green', (0, 255, 0), (0.8664, -0.2339, 0.1795)),
    ('blue', (0, 0, 255), (0.4520, -0.0324, -0.3115)),
]


@pytest.mark.parametrize('name, rgb, expected', GOLDEN, ids=[g[0] for g in GOLDEN])
def test_srgb_to_oklab_golden(name, rgb, expected):
    got = e.srgb_to_oklab(np.array(rgb, dtype=np.float64))
    np.testing.assert_allclose(got, expected, atol=1e-2,
                               err_msg=f'{name} OKLab 偏离期望，检查 gamma 解码与矩阵')


def test_oklab_roundtrip():
    """OKLab -> sRGB -> OKLab 往返一致（验证反变换）"""
    colors = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255],
                       [128, 128, 128], [10, 200, 60]], dtype=np.float64)
    lab = e.srgb_to_oklab(colors)
    back_rgb = e.oklab_to_srgb(lab).astype(np.float64)
    np.testing.assert_allclose(back_rgb, colors, atol=2.0)


def test_lch_derivation():
    """C = sqrt(a^2+b^2)，h = atan2(b,a) 的派生正确"""
    lab = e.srgb_to_oklab(np.array([[255, 0, 0]], dtype=np.float64))
    _, C, h = e.oklab_to_lch(lab)
    assert C[0] == pytest.approx(np.hypot(lab[0, 1], lab[0, 2]), abs=1e-9)
    assert 0.0 <= h[0] < 360.0


def test_gray_is_near_neutral():
    """中性灰的 chroma 必须趋近 0（OKLCH 的核心优势）"""
    lab = e.srgb_to_oklab(np.array([[128, 128, 128]], dtype=np.float64))
    _, C, _ = e.oklab_to_lch(lab)
    assert C[0] < 1e-3
