"""阶段 2.5b 合成信号单测（8.3 模板拟合 + 8.2 平滑隶属度）

不依赖图片：用构造的色相/明度分布验证 Matsuda 模板拟合的选型行为
（含扇区均衡约束与优先序）和 smoothstep 分区隶属度的数学性质。
"""

import numpy as np

from core import color_distribution as e


def _fit(h: np.ndarray, chroma: float = 0.1):
    C = np.full(h.shape[0], chroma)
    return e.analyze_harmony_fit(C, h, chroma)


# ==================== 8.3 模板拟合 ====================

def test_fit_single_narrow_peak():
    """单窄峰 → i 模板 / 单色配色，高置信度"""
    h = np.full(1000, 200.0) + np.linspace(-3.0, 3.0, 1000)
    label_key, fit = _fit(h)
    assert fit['template'] == 'i'
    assert label_key == 'harmony_monochromatic'
    assert fit['confidence'] > 0.8


def test_fit_two_opposite_peaks():
    """两个 180° 对向均衡窄峰 → I 模板 / 互补色"""
    h = np.concatenate([np.full(500, 30.0), np.full(500, 210.0)])
    label_key, fit = _fit(h)
    assert fit['template'] == 'I'
    assert label_key == 'harmony_complementary'


def test_fit_sector_balance_gate():
    """95/5 失衡对向峰：均衡约束禁用 I 的白嫖旋转 → 单色而非互补"""
    h = np.concatenate([np.full(950, 30.0), np.full(50, 210.0)])
    label_key, fit = _fit(h)
    assert label_key == 'harmony_monochromatic'
    assert fit['template'] in ('i', 'V')


def test_fit_wide_contiguous_spread():
    """约 90° 连续平铺 → V 模板（单色大扇区），i 装不下"""
    h = np.linspace(100.0, 190.0, 1000)
    label_key, fit = _fit(h)
    assert fit['template'] == 'V'
    assert label_key == 'harmony_monochromatic'


def test_fit_half_circle_spread():
    """约 240° 大扇区平铺 → T 模板 / 邻近色（单/双扇区模板均装不下）"""
    h = np.arange(0.0, 240.0, 0.5)
    label_key, fit = _fit(h)
    assert fit['template'] == 'T'
    assert label_key == 'harmony_analogous'


def test_fit_double_complementary():
    """四个 90° 等距均衡峰（两对互补对）：X 模板旋转 45° 后两扇区
    各拢相邻两峰，几乎完美拟合 → 双互补"""
    h = np.concatenate([np.full(250, a) for a in (0.0, 90.0, 180.0, 270.0)])
    label_key, fit = _fit(h)
    assert fit['template'] == 'X'
    assert label_key == 'harmony_double_complementary'
    assert fit['confidence'] > 0.8


def test_fit_triadic_free():
    """三个 120° 等距均衡峰（旧"三角配色"）：Matsuda 8 模板无对应形态，
    宽模板达标线折减后 X 也不达标 → 自由配色，置信度低"""
    h = np.concatenate([np.full(300, a) for a in (0.0, 120.0, 240.0)])
    label_key, fit = _fit(h)
    assert label_key == 'harmony_free'
    assert fit['confidence'] < 0.5


def test_fit_achromatic():
    """整图彩度趋 0 → N 模板 / 黑白灰调"""
    h = np.full(100, 123.0)
    C = np.full(100, 0.001)
    label_key, fit = e.analyze_harmony_fit(C, h, 0.001)
    assert fit['template'] == 'N'
    assert label_key == 'harmony_achromatic'


def test_fit_output_fields():
    """拟合输出字段与取值范围"""
    _, fit = _fit(np.full(100, 60.0))
    assert set(fit) == {'template', 'rotation', 'error', 'confidence'}
    assert 0.0 <= fit['rotation'] < 360.0
    assert fit['error'] >= 0.0
    assert 0.0 <= fit['confidence'] <= 1.0


# ==================== 8.2 平滑隶属度 ====================

def test_smoothstep_shape():
    """smoothstep 端点与中点"""
    x = np.array([0.0, 0.27, 0.35, 0.43, 1.0])
    w = e._smoothstep(x, 0.27, 0.43)
    assert w[0] == 0.0 and w[1] == 0.0
    assert abs(w[2] - 0.5) < 1e-12
    assert w[3] == 1.0 and w[4] == 1.0


def test_zone_membership_sums_to_100():
    """任意明度分布下三区软占比之和恒为 100%"""
    rng = np.random.default_rng(0)
    n = 1000
    L = rng.random(n)
    C = np.full(n, 0.05)
    h = rng.random(n) * 360.0
    zones = e.analyze_zones(L, C, h, h)
    total = sum(zones[k]['pixel_pct'] for k in ('dark', 'mid', 'bright'))
    assert abs(total - 100.0) < 1e-9


def test_zone_hard_cut_outside_transition():
    """过渡带外像素的归属与硬切完全一致（各 1/3 占比精确复现）"""
    L = np.concatenate([np.full(100, 0.10), np.full(100, 0.20),   # 暗
                        np.full(100, 0.50), np.full(100, 0.60),   # 中
                        np.full(100, 0.85), np.full(100, 0.95)])  # 亮
    n = L.shape[0]
    C = np.full(n, 0.05)
    h = np.full(n, 30.0)
    zones = e.analyze_zones(L, C, h, h)
    for key in ('dark', 'mid', 'bright'):
        assert abs(zones[key]['pixel_pct'] - 100.0 / 3.0) < 1e-9


def test_zone_boundary_half_membership():
    """全图 L 恰在暗/中过渡带中心 → 暗部与中间调各得 50% 软占比"""
    n = 200
    L = np.full(n, e.ZONE_DARK_MAX)
    C = np.full(n, 0.05)
    h = np.full(n, 200.0)
    zones = e.analyze_zones(L, C, h, h)
    assert abs(zones['dark']['pixel_pct'] - 50.0) < 1e-9
    assert abs(zones['mid']['pixel_pct'] - 50.0) < 1e-9
    assert zones['bright']['pixel_pct'] == 0.0


def test_zone_no_pixels_label():
    """像素全在亮部：暗部/中间调隶属度全 0 → 报"无像素"而非误报中性"""
    n = 100
    L = np.full(n, 0.9)
    C = np.full(n, 0.05)
    h = np.full(n, 30.0)
    zones = e.analyze_zones(L, C, h, h)
    for key in ('dark', 'mid'):
        assert zones[key]['pixel_pct'] == 0.0
        assert zones[key]['label_key'] == 'zone_no_pixels'
        assert zones[key]['label_args'] == {'zone': key}
        assert zones[key]['composition'] == []
    assert zones['bright']['pixel_pct'] == 100.0
