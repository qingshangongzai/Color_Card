"""阶段 2.5c 合成信号单测（8.1 色偏双证据 / 8.4 主色卡去随机 / 8.5 彩色度）

不依赖图片：直接构造 OKLab 数组验证判定逻辑与数值性质，
参照 test_harmony_fit.py 的合成信号模式。
"""

from __future__ import annotations

import math

import numpy as np

from core import color_distribution as e


def _noise(n: int, scale: float, seed: int = 7) -> np.ndarray:
    """测试用确定性噪声（引擎本身无随机，随机源仅在测试侧）"""
    return np.random.default_rng(seed).normal(0.0, scale, n)


def _cast(a, b, L) -> dict:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    L = np.asarray(L, dtype=np.float64)
    return e.analyze_cast(a, b, np.hypot(a, b), L)


# ==================== 8.1 色偏双证据 ====================

def test_cast_wb_shift_rescued_by_bright_band():
    """组4 场景合成：白纸 L>0.9 被证据一排除 + 暖移，亮带报出方向"""
    n_paper, n_screen = 6000, 4000
    # 白纸（亮，证据一候选被 L 过滤）整体 b+0.04；蓝屏为高彩内容
    a = np.concatenate([_noise(n_paper, 0.002, 1),
                        _noise(n_screen, 0.005, 2) - 0.02])
    b = np.concatenate([_noise(n_paper, 0.002, 3) + 0.04,
                        _noise(n_screen, 0.005, 4) - 0.12])
    L = np.concatenate([np.full(n_paper, 0.95) + _noise(n_paper, 0.005, 5),
                        np.full(n_screen, 0.5) + _noise(n_screen, 0.01, 6)])
    r = _cast(a, b, L)
    assert r['kind'] == 'wb_error'
    assert 'warm_yellow' in r['label_args']['direction']
    assert r['label_args']['level'] == 'strong'
    assert 0.0 < r['confidence'] < 1.0


def test_cast_pseudo_neutral_overridden():
    """伪中性候选陷阱：低彩偏冷内容误导证据一，集中偏暖的亮带否决之"""
    n_fake, n_bright, n_color = 3000, 3000, 4000
    a = np.concatenate([_noise(n_fake, 0.005, 1),
                        _noise(n_bright, 0.003, 2),
                        _noise(n_color, 0.005, 3) + 0.18])
    b = np.concatenate([_noise(n_fake, 0.008, 4) - 0.018,   # 候选：偏冷
                        _noise(n_bright, 0.003, 5) + 0.035,  # 亮带：偏暖（紧凑）
                        _noise(n_color, 0.005, 6) + 0.05])
    L = np.concatenate([np.full(n_fake, 0.55) + _noise(n_fake, 0.02, 7),
                        np.full(n_bright, 0.86) + _noise(n_bright, 0.01, 8),
                        np.full(n_color, 0.4) + _noise(n_color, 0.02, 9)])
    r = _cast(a, b, L)
    assert 'warm_yellow' in r['label_args']['direction'], r['label_args']
    assert 0.0 < r['confidence'] < 1.0


def test_cast_agreeing_evidence_high_confidence():
    """双证据方向一致：高置信（confidence=1，UI 不加低置信后缀）"""
    n_gray, n_color = 6000, 4000
    a = np.concatenate([_noise(n_gray, 0.006, 1),
                        _noise(n_color, 0.01, 2) + 0.12])
    b = np.concatenate([_noise(n_gray, 0.006, 3) + 0.025,
                        _noise(n_color, 0.01, 4) + 0.1])
    L = np.concatenate([np.linspace(0.3, 0.92, n_gray),
                        np.full(n_color, 0.5)])
    r = _cast(a, b, L)
    assert r['kind'] in ('wb_error', 'styled')
    assert any(d in ('warm_yellow', 'yellow') for d in r['label_args']['direction'])
    assert r['confidence'] == 1.0


def test_cast_neutral():
    """无偏移灰场 + 彩色内容：白平衡中性"""
    n_gray, n_color = 6000, 4000
    a = np.concatenate([_noise(n_gray, 0.004, 1), _noise(n_color, 0.01, 2) + 0.15])
    b = np.concatenate([_noise(n_gray, 0.004, 3), _noise(n_color, 0.01, 4) + 0.08])
    L = np.concatenate([np.linspace(0.3, 0.92, n_gray), np.full(n_color, 0.5)])
    r = _cast(a, b, L)
    assert r['kind'] == 'neutral' and r['label_key'] == 'cast_neutral'
    assert r['confidence'] == 1.0


def test_cast_sky_band_cannot_override_neutral():
    """天空蓝区亮带不得否决中性候选（蓝天与冷偏移统计同构）"""
    n_gray, n_sky = 6000, 4000
    ang = math.radians(245.0)
    a = np.concatenate([_noise(n_gray, 0.004, 1),
                        _noise(n_sky, 0.003, 2) + 0.06 * math.cos(ang)])
    b = np.concatenate([_noise(n_gray, 0.004, 3),
                        _noise(n_sky, 0.003, 4) + 0.06 * math.sin(ang)])
    L = np.concatenate([np.linspace(0.25, 0.7, n_gray),
                        np.full(n_sky, 0.82) + _noise(n_sky, 0.01, 5)])
    r = _cast(a, b, L)
    assert r['kind'] == 'neutral' and r['label_key'] == 'cast_neutral'


def test_cast_unknown_when_no_reference():
    """全高彩、无任何低彩参照：报不可判"""
    n = 8000
    a = _noise(n, 0.01, 1) + 0.2
    b = _noise(n, 0.01, 2) + 0.1
    L = np.full(n, 0.5) + _noise(n, 0.05, 3)
    r = _cast(a, b, L)
    assert r['kind'] == 'unknown'
    assert r['label_key'] == 'cast_unknown'


def test_cast_output_fields():
    """8.1 输出结构：kind / confidence / vector2 字段齐全"""
    n = 2000
    a, b = _noise(n, 0.005, 1), _noise(n, 0.005, 2)
    L = np.linspace(0.2, 0.9, n)
    r = _cast(a, b, L)
    assert set(r) >= {'vector', 'vector2', 'strength', 'kind',
                      'confidence', 'label_key', 'label_args', 'candidate_pct'}
    assert r['kind'] in ('neutral', 'wb_error', 'styled', 'unknown')
    assert 0.0 <= r['confidence'] <= 1.0


# ==================== 8.4 主色卡去随机 ====================

def _lab_clusters(*clusters: tuple[tuple[float, float, float], int, int]) -> np.ndarray:
    """按 (中心LAB, 数量, 种子) 构造带小噪声的 OKLab 像素簇"""
    parts = []
    for (l0, a0, b0), n, seed in clusters:
        rng = np.random.default_rng(seed)
        parts.append(np.column_stack([
            np.clip(rng.normal(l0, 0.01, n), 0.0, 1.0),
            rng.normal(a0, 0.005, n),
            rng.normal(b0, 0.005, n),
        ]))
    return np.concatenate(parts)


def test_palette_deterministic():
    """同输入两次运行结果完全一致（去随机验证）"""
    lab = _lab_clusters(((0.7, 0.1, 0.05), 5000, 1),
                        ((0.4, -0.08, 0.1), 3000, 2),
                        ((0.55, 0.0, -0.12), 2000, 3))
    assert e.analyze_palette(lab) == e.analyze_palette(lab)


def test_palette_separates_clusters_with_weights():
    """三个远距簇：输出 3 个主色，占比接近构造比例"""
    lab = _lab_clusters(((0.7, 0.15, 0.0), 5000, 1),
                        ((0.35, -0.1, 0.12), 3000, 2),
                        ((0.55, 0.0, -0.15), 2000, 3))
    result = e.analyze_palette(lab)
    assert len(result) == 3
    pcts = [pct for _, pct, _ in result]
    assert abs(pcts[0] - 50.0) < 3.0
    assert abs(pcts[1] - 30.0) < 3.0
    assert abs(pcts[2] - 20.0) < 3.0


def test_palette_merges_near_centers():
    """ΔE_OK 过近的两簇合并为一个主色"""
    lab = _lab_clusters(((0.6, 0.1, 0.0), 4000, 1),
                        ((0.6, 0.12, 0.0), 4000, 2),     # 与上簇 ΔE=0.02 < 0.04
                        ((0.3, -0.1, -0.1), 2000, 3))
    result = e.analyze_palette(lab)
    assert len(result) == 2
    assert abs(result[0][1] - 80.0) < 3.0


# ==================== 8.5 彩色度 ====================

def test_colorfulness_gray_is_zero():
    """纯灰图：rg/yb 恒为 0，M = 0，无彩感"""
    gray = np.full((5000, 3), 128.0)
    r = e.analyze_colorfulness(gray)
    assert r['colorfulness'] == 0.0
    assert r['colorfulness_key'] == 'colorfulness_none'


def test_colorfulness_known_value():
    """红蓝各半：M 与手算值一致（σ_rgyb≈229.9 + 0.3·μ_rgyb≈42.8）"""
    rgb = np.array([[255.0, 0.0, 0.0]] * 500 + [[0.0, 0.0, 255.0]] * 500)
    r = e.analyze_colorfulness(rgb)
    assert abs(r['colorfulness'] - 272.6) < 1.0
    assert r['colorfulness_key'] == 'colorfulness_extreme'


def test_colorfulness_band_mapping():
    """七档边界：searchsorted 映射与论文阈值一致"""
    bounds = e.COLORFULNESS_BOUNDS
    keys = e.COLORFULNESS_KEYS
    assert len(bounds) == 6 and len(keys) == 7
    # 直接构造边界附近的常数场：σ=0，M = 0.3·μ_rgyb；取 rg=μ，
    # b=(r+g)/2 使 yb=0
    for m_target, expect in ((0.0, 'colorfulness_none'), (16.0, 'colorfulness_slight'),
                             (108.9, 'colorfulness_high'), (109.0, 'colorfulness_extreme')):
        mu = m_target / 0.3
        rgb = np.column_stack([np.full(100, 100.0 + mu),
                               np.full(100, 100.0),
                               np.full(100, 100.0 + mu / 2)])
        r = e.analyze_colorfulness(rgb)
        assert abs(r['colorfulness'] - m_target) < 1e-6
        assert r['colorfulness_key'] == expect


def test_colorfulness_in_chroma_dist():
    """analyze_lab 输出：chroma_dist 携带 colorfulness 两键"""
    lab = _lab_clusters(((0.6, 0.05, 0.05), 3000, 1))
    r = e.analyze_lab(lab)
    cd = r['chroma_dist']
    assert 'colorfulness' in cd and 'colorfulness_key' in cd
    assert cd['colorfulness'] >= 0.0
    assert cd['colorfulness_key'] in e.COLORFULNESS_KEYS
