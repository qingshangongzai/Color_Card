"""合成信号单测（感知色名层 / 近中性冷暖混合 / 冷暖阈值冻结）

不依赖图片：直接构造标量/OKLab 数组验证判定逻辑与数值性质，
参照 test_25c_upgrades.py 的合成信号模式。
"""

import numpy as np

from core import color_distribution as e


# ==================== 8.6 感知色名 perceptual_color_name ====================

def test_pname_gray_family_by_warmth():
    """低彩 → 灰族：暖侧暖灰 / 冷侧蓝灰 / 中间灰"""
    assert e.perceptual_color_name(0.5, 0.02, 30.0) == 'warm_gray'    # 橙红
    assert e.perceptual_color_name(0.5, 0.02, 240.0) == 'blue_gray'   # 蓝
    assert e.perceptual_color_name(0.5, 0.02, 120.0) == 'gray'        # 绿（非冷非暖）


def test_pname_brown():
    """暗橙红/暗黄 + 足彩 → 棕（红段已退出棕，另见 test_pname_deep_red_and_maroon）"""
    assert e.perceptual_color_name(0.40, 0.08, 30.0) == 'brown'       # 暗橙红
    assert e.perceptual_color_name(0.54, 0.08, 60.0) == 'brown'       # 暗黄，L 边界内
    # 亮橙红不归棕（L >= 阈值）
    assert e.perceptual_color_name(0.55, 0.08, 30.0) == 'orange_red'


def test_pname_deep_red_and_maroon():
    """暗红不再归棕：高彩"深红"、低彩"栗红"（红裙暗部 red 段实测 C=0.082）"""
    assert e.perceptual_color_name(0.339, 0.082, 6.9) == 'deep_red'   # 红裙暗部锚点
    assert e.perceptual_color_name(0.40, 0.05, 350.0) == 'maroon'     # 浊暗红
    # 彩度分界：C >= 0.08 深红，以下（足彩）栗红
    assert e.perceptual_color_name(0.40, 0.08, 0.0) == 'deep_red'
    assert e.perceptual_color_name(0.40, 0.079, 0.0) == 'maroon'
    # 明度边界：L >= 0.55 恢复基名"红"
    assert e.perceptual_color_name(0.55, 0.10, 0.0) == 'red'
    # 低彩暗红仍归灰族（暖侧）
    assert e.perceptual_color_name(0.40, 0.02, 0.0) == 'warm_gray'


def test_pname_pink():
    """亮低饱和红/品红/紫红 → 粉"""
    assert e.perceptual_color_name(0.75, 0.06, 300.0) == 'pink'       # 亮低饱和品红
    # 浓品红不归粉（彩度过高）
    assert e.perceptual_color_name(0.75, 0.14, 300.0) == 'magenta'
    # 暗品红不归粉（明度不足）
    assert e.perceptual_color_name(0.60, 0.06, 300.0) == 'magenta'


def test_pname_fallthrough_keeps_base():
    """足彩非棕非粉 → 保持 12 段基名，与 hue_name 一致"""
    for hue in (0.0, 60.0, 120.0, 200.0, 240.0, 330.0):
        assert e.perceptual_color_name(0.6, 0.18, hue) == e.hue_name(hue)


# ==================== 8.6 近中性分区冷暖混合 ====================

def test_neutral_zone_mix_bidirectional():
    """暖侧与冷侧权重占比均超阈值 → 判混合"""
    comp = [{'name': 'cyan_blue', 'weight_pct': 33.0},
            {'name': 'orange_red', 'weight_pct': 31.0},
            {'name': 'red', 'weight_pct': 25.0}]
    assert e._neutral_zone_mix(comp) is True


def test_neutral_zone_mix_single_side():
    """仅一侧有色（另一侧为 0）→ 不判混合"""
    comp = [{'name': 'cyan_blue', 'weight_pct': 34.0},
            {'name': 'cyan_green', 'weight_pct': 20.0},
            {'name': 'yellow_green', 'weight_pct': 16.0}]
    assert e._neutral_zone_mix(comp) is False


def _zone_arrays(n, L_val, C_val, hsb_pairs):
    """构造单区合成数组：全部落在明度 L_val，色相按 hsb_pairs 均分"""
    L = np.full(n, L_val)
    C = np.full(n, C_val)
    parts = [np.full(n // len(hsb_pairs), h) for h in hsb_pairs]
    hsb = np.concatenate(parts)
    hsb = np.resize(hsb, n)
    return L, C, hsb.copy(), hsb.copy()


def test_zones_neutral_mix_label():
    """近中性暗区内暖(橙红)冷(蓝)各半 → mix 标记为 True（UI 追加混合后缀）"""
    L, C, h_ok, hsb = _zone_arrays(4000, 0.30, 0.012, (30.0, 250.0))
    zones = e.analyze_zones(L, C, h_ok, hsb)
    dark = zones['dark']
    assert dark['label_key'] == 'zone_neutral' and dark['mix'] is True
    pnames = {c['pname'] for c in dark['composition']}
    assert 'warm_gray' in pnames and 'blue_gray' in pnames


def test_zones_neutral_single_side_plain():
    """近中性暗区仅冷色 → 维持纯"接近中性"，构成为空"""
    L, C, h_ok, hsb = _zone_arrays(4000, 0.30, 0.012, (250.0,))
    zones = e.analyze_zones(L, C, h_ok, hsb)
    dark = zones['dark']
    assert dark['label_key'] == 'zone_neutral' and dark['mix'] is False
    assert dark['composition'] == []


# ==================== 8.6 主色卡 / 构成携带 pname ====================

def _lab_clusters(*clusters):
    parts = []
    for (l0, a0, b0), n, seed in clusters:
        rng = np.random.default_rng(seed)
        parts.append(np.column_stack([
            np.clip(rng.normal(l0, 0.01, n), 0.0, 1.0),
            rng.normal(a0, 0.005, n),
            rng.normal(b0, 0.005, n),
        ]))
    return np.concatenate(parts)


def test_palette_carries_pname():
    """主色卡为三元组 ((r,g,b), pct, pname)，pname 为非空感知色名 id"""
    lab = _lab_clusters(((0.40, 0.05, 0.06), 5000, 1),
                        ((0.55, 0.0, -0.14), 3000, 2))
    result = e.analyze_palette(lab)
    assert result and all(len(entry) == 3 for entry in result)
    for rgb, pct, pname in result:
        assert len(rgb) == 3 and isinstance(pct, float)
        assert isinstance(pname, str) and pname


def test_composition_carries_pname():
    """构成条目含 pname；暗暖足彩段命中"棕\""""
    n = 3000
    C = np.full(n, 0.10)
    h = np.full(n, 30.0)             # 橙红
    L = np.full(n, 0.40)            # 暗 → 棕
    comp = e.analyze_hue_composition(C, h, None, L)
    assert comp and comp[0]['name'] == 'orange_red'
    assert comp[0]['pname'] == 'brown'


def test_composition_red_segment_deep_red():
    """暗红段构成 pname 不再是 brown（红裙锚点：hue 6.9、L 0.34、C 0.082）"""
    n = 3000
    C = np.full(n, 0.082)
    h = np.full(n, 6.9)              # 红
    L = np.full(n, 0.34)            # 暗 → 深红
    comp = e.analyze_hue_composition(C, h, None, L)
    assert comp and comp[0]['name'] == 'red'
    assert comp[0]['pname'] == 'deep_red'


# ==================== 8.7 冷暖五档阈值（校准后冻结） ====================

def test_warmth_constants_frozen():
    """2.5d 全量验证集复核后冻结（0 张不符），阈值不变"""
    assert e.WARMTH_WEAK == 0.15
    assert e.WARMTH_STRONG == 0.5


def _warmth_key(value, n=10000):
    """构造 h=55(cos=1) 与 h=145(cos=0) 两组，令 warmth 值 ≈ value（可负）"""
    warm_pole = 55.0 if value >= 0 else 235.0    # 235° 相对 55° cos=-1
    n1 = int(round(abs(value) * n))
    C = np.full(n, 0.2)
    h = np.concatenate([np.full(n1, warm_pole), np.full(n - n1, 145.0)])
    return e.analyze_warmth(C, h)['label_key']


def test_warmth_five_bands():
    """五档边界映射与冻结阈值一致"""
    assert _warmth_key(0.51) == 'warmth_strong_warm'
    assert _warmth_key(0.49) == 'warmth_warm'
    assert _warmth_key(0.16) == 'warmth_warm'
    assert _warmth_key(0.14) == 'warmth_neutral'
    assert _warmth_key(-0.14) == 'warmth_neutral'
    assert _warmth_key(-0.16) == 'warmth_cool'
    assert _warmth_key(-0.51) == 'warmth_strong_cool'
