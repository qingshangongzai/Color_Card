"""合成信号单测（阶段三：峰内构成）

不依赖图片：直接构造标量/OKLab 数组验证 max_results 截断参数、
rep_weight 代表值口径与 analyze_hue_peaks 的 composition 字段，
参照 test_25d_upgrades.py 的合成信号模式。
峰级"不截断"的端到端行为由 25a 验证集红裙 golden 固化
（yellow_green 峰 5 条 > COMP_MAX）。

已裁决口径（2026-09-06）：峰内构成的段代表 L/C 用 chroma 权重
（与峰的 chroma 加权归属同源），分区构成默认 'area' 零回归。
"""

import numpy as np

from core import color_distribution as e


# ==================== max_results 截断参数 ====================

def _five_seg_C_h(n_per=1000):
    """构造 5 段各 n_per 像素的合成数组（每段权重 20%，均过门槛）"""
    hues = (0.0, 30.0, 60.0, 120.0, 240.0)   # red/orange_red/yellow/green/blue
    h = np.concatenate([np.full(n_per, hu) for hu in hues])
    C = np.full(len(h), 0.10)
    return C, h


def test_composition_max_results_default_is_comp_max():
    """默认截断 = COMP_MAX（分区调用点零回归），返回按权重降序"""
    C, h = _five_seg_C_h()
    comp = e.analyze_hue_composition(C, h)
    assert len(comp) == e.COMP_MAX
    pcts = [c['weight_pct'] for c in comp]
    assert pcts == sorted(pcts, reverse=True)


def test_composition_max_results_none_expands_all():
    """max_results=None 不截断（峰调用点口径）：5 段全展开"""
    C, h = _five_seg_C_h()
    comp = e.analyze_hue_composition(C, h, max_results=None)
    assert len(comp) == 5
    assert {c['name'] for c in comp} == {'red', 'orange_red', 'yellow', 'green', 'blue'}


def test_composition_max_results_explicit():
    """显式数字按数字截断"""
    C, h = _five_seg_C_h()
    assert len(e.analyze_hue_composition(C, h, max_results=2)) == 2


# ==================== rep_weight 段代表 L/C 口径 ====================

def test_rep_weight_chroma_flips_pname():
    """红裙机理合成复现：red 段内高彩暗红少数 + 近白高光多数

    面积权重下 rep_c 被低彩像素稀释 < 0.03 判灰族（warm_gray）；
    chroma 权重与归属口径同源，且代表值只在可见彩度成员（C >= 0.02）
    上计算——近白高光（色相数值落段但无色彩感知）不参与代表值，
    忠实判深红（红裙实测：82% 成员为 C≈0.006 近白高光）。
    """
    n_hi, n_lo = 300, 2700
    C = np.concatenate([np.full(n_hi, 0.09), np.full(n_lo, 0.01)])
    L = np.concatenate([np.full(n_hi, 0.34), np.full(n_lo, 0.60)])
    h = np.full(n_hi + n_lo, 5.0)            # 全落红段

    comp_area = e.analyze_hue_composition(C, h, None, L)
    comp_chroma = e.analyze_hue_composition(C, h, None, L, rep_weight='chroma')
    assert comp_area[0]['name'] == 'red'
    assert comp_area[0]['pname'] == 'warm_gray'      # 面积口径：稀释 → 灰族
    assert comp_chroma[0]['name'] == 'red'
    assert comp_chroma[0]['pname'] == 'deep_red'     # chroma 口径：仅可见成员 → 深红


def test_rep_weight_uniform_value_consistent():
    """单一 C 值直方图下两口径代表值退化一致（权重仅差常数比例）"""
    n = 3000
    C = np.full(n, 0.082)
    h = np.full(n, 6.9)
    L = np.full(n, 0.34)
    comp_area = e.analyze_hue_composition(C, h, None, L)
    comp_chroma = e.analyze_hue_composition(C, h, None, L, rep_weight='chroma')
    assert comp_area[0]['pname'] == comp_chroma[0]['pname'] == 'deep_red'
    assert comp_area[0]['rgb'] == comp_chroma[0]['rgb']


# ==================== 分区构成的真实代表色 ====================
def test_zone_composition_carries_rgb():
    """分区调用点（默认 'area' 口径）同样输出真实代表色 rgb

    红裙暗部"深红"条锚点：段代表值原样还原为 rgb（修正前该条按分区
    平均彩度渲染为棕灰 (115,96,94)，与条目名不一致）。
    """
    rgb0 = (91, 37, 28)
    L, C, h_ok = e.oklab_to_lch(e.srgb_to_oklab(np.array([rgb0], dtype=np.uint8)))
    n = 3000
    comp = e.analyze_hue_composition(
        np.full(n, float(C[0])), np.full(n, 6.9), None,
        np.full(n, float(L[0])), np.full(n, float(h_ok[0])))
    assert comp[0]['name'] == 'red'
    assert comp[0]['rgb'] is not None, 'rgb 不得为 None（UI 绘制中断回归）'
    assert all(abs(a - b) <= 2 for a, b in zip(rgb0, comp[0]['rgb'])), comp[0]['rgb']


# ==================== analyze_hue_peaks 每峰 composition ====================

def test_peak_composition_carries_l():
    """analyze_hue_peaks 加 L 形参：峰内构成携带 pname，L 生效判深红"""
    n1, n2 = 2000, 1000
    C = np.full(n1 + n2, 0.09)
    h = np.full(n1 + n2, 5.0)
    hsb_h = np.full(n1 + n2, 5.0)
    L = np.concatenate([np.full(n1, 0.30), np.full(n2, 0.70)])

    peaks = e.analyze_hue_peaks(C, h, hsb_h, L)
    assert len(peaks) == 1
    comp = peaks[0]['composition']
    assert comp and comp[0]['name'] == 'red'
    assert comp[0]['pname'] == 'deep_red'    # 加权 rep_l≈0.43 < 0.55 且 C≥0.08

    peaks_no_l = e.analyze_hue_peaks(C, h, hsb_h)
    assert peaks_no_l[0]['composition'][0]['pname'] == 'red'   # L 缺省回退 0.6


def test_peak_composition_structure():
    """峰 dict 的 composition 为条目列表，字段与分区构成一致（含 rep_c/rgb）"""
    n = 3000
    C = np.full(n, 0.09)
    h = np.full(n, 5.0)
    hsb_h = np.full(n, 5.0)
    peaks = e.analyze_hue_peaks(C, h, hsb_h)
    comp = peaks[0]['composition']
    assert comp
    for item in comp:
        assert {'name', 'pname', 'hue', 'weight_pct', 'area_pct', 'range',
                'rep_c', 'rgb'} <= set(item)
        assert isinstance(item['rgb'], tuple) and len(item['rgb']) == 3
        assert all(isinstance(v, int) and 0 <= v <= 255 for v in item['rgb'])


def test_peak_composition_rgb_roundtrip():
    """段真实代表色往返：任意 sRGB 经 OKLab→LCH→_rep_rgb 应回到原色（±2）"""
    for rgb0 in ((255, 0, 0), (30, 144, 255), (200, 160, 134), (91, 37, 28)):
        arr = np.array([rgb0], dtype=np.uint8)
        L, C, h = e.oklab_to_lch(e.srgb_to_oklab(arr))
        rgb1 = e._rep_rgb(float(L[0]), float(C[0]), float(h[0]))
        assert all(abs(a - b) <= 2 for a, b in zip(rgb0, rgb1)), f'{rgb0} -> {rgb1}'


def test_peak_composition_low_chroma_gray_fallback():
    """整段成员均不可见（C < 0.02）时 rgb 兜底中性灰且非 None

    回归：低彩图（mean_chroma 高于灰调线但全图无可见彩度成员）曾输出
    rgb=None，UI 端 QColor.fromRgb(*None) 抛 TypeError 绘制中断。
    """
    img = np.full((64, 64, 3), (133, 128, 125), dtype=np.uint8)
    result = e.analyze_color_distribution(img)
    peaks = result['hue_peaks']
    assert peaks, '低彩图仍应有峰（高于 ACHROMATIC_EPS）'
    for peak in peaks:
        assert peak['composition'], '低彩峰仍应有构成条目'
        for item in peak['composition']:
            assert item['rgb'] is not None, 'rgb 不得为 None（UI 崩溃回归）'
            r, g, b = item['rgb']
            assert max(r, g, b) - min(r, g, b) <= 2, '无可见成员段应为中性灰'


def test_peak_composition_uses_hsb_axis():
    """段归属传 HSB 展示轴（双轴偏移修复核心）：纯红图 OKLCH h≈29° 落
    orange_red bin，但峰内构成必须按 hsb_h=0° 归 red 段；
    若误传 OKLCH 的 h 将判 orange_red（红裙机理回归）"""
    img = np.full((8, 8, 3), (255, 0, 0), dtype=np.uint8)
    result = e.analyze_color_distribution(img)
    peaks = result['hue_peaks']
    assert len(peaks) == 1
    assert peaks[0]['name'] == 'red'
    assert peaks[0]['composition'][0]['name'] == 'red'


def test_achromatic_image_no_peaks():
    """全局灰调：peaks 为空，无峰内构成"""
    img = np.full((8, 8, 3), 128, dtype=np.uint8)
    result = e.analyze_color_distribution(img)
    assert result['hue_peaks'] == []
