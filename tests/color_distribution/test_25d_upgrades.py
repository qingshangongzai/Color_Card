"""合成信号单测（感知色名层 / 近中性冷暖混合 / 冷暖阈值冻结）

不依赖图片：直接构造标量/OKLab 数组验证判定逻辑与数值性质，
参照 test_25c_upgrades.py 的合成信号模式。
"""

import json
import os

import numpy as np

from core import color_distribution as e
from core import color_naming as naming
from core.color_data import get_base_path
from tests.color_distribution.conftest import ok_hue

# ==================== 结构化感知色名 classify_color_name ====================

FAMILIES = {'black', 'white', 'gray', 'red', 'orange', 'yellow', 'green',
            'cyan', 'blue', 'purple', 'magenta', 'pink', 'brown'}
TONES = {'none', 'vivid', 'deep', 'light', 'dark', 'pale', 'muted'}
HUE_MODIFIERS = {'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple'}


def test_classify_color_name_contract():
    """结构化色名字段固定，ID 均属词表，置信度在 0~1"""
    name = naming.classify_color_name((180, 146, 170))
    assert set(name) == {'family_id', 'secondary_family_id', 'tone_id',
                         'hue_modifier_id', 'confidence', 'technical_hue_id'}
    assert name['family_id'] in FAMILIES
    assert name['secondary_family_id'] is None or name['secondary_family_id'] in FAMILIES
    assert name['tone_id'] in TONES
    assert name['hue_modifier_id'] is None or name['hue_modifier_id'] in HUE_MODIFIERS
    assert 0.0 < name['confidence'] <= 1.0
    assert name['technical_hue_id'] == 'purple_red'


def _load_model_artifact() -> dict:
    model_path = os.path.join(get_base_path(), 'color_data', 'naming',
                              'color_name_model.json')
    with open(model_path, encoding='utf-8') as handle:
        return json.load(handle)


def test_classify_color_name_projects_to_allowed_combinations():
    """全色域抽样：tone 与细色相修饰始终落在模型的允许集合内"""
    model = _load_model_artifact()
    allowed_tones = model['allowed_tones']
    allowed_modifiers = model['allowed_hue_modifiers']
    for r in range(0, 256, 51):
        for g in range(0, 256, 51):
            for b in range(0, 256, 51):
                name = naming.classify_color_name((r, g, b))
                family = name['family_id']
                assert family in FAMILIES
                assert name['tone_id'] in TONES
                assert name['tone_id'] in allowed_tones[family]
                assert name['hue_modifier_id'] != family
                assert (name['hue_modifier_id'] is None
                        or name['hue_modifier_id'] in allowed_modifiers[family])
                if family in ('black', 'white'):
                    assert name['tone_id'] == 'none'
                    assert name['hue_modifier_id'] is None


def test_classify_color_name_known_anchors():
    """最终 RGB 锚点：纯色落到对应色系，近黑按暗色处理而非满通道蓝"""
    assert naming.classify_color_name((255, 0, 0))['family_id'] == 'red'
    assert naming.classify_color_name((0, 255, 0))['family_id'] == 'green'
    assert naming.classify_color_name((0, 0, 255))['family_id'] == 'blue'
    assert naming.classify_color_name((128, 128, 128))['family_id'] == 'gray'
    assert naming.classify_color_name((255, 255, 255))['family_id'] == 'white'
    assert naming.classify_color_name((0, 0, 0))['family_id'] == 'black'
    near_black = naming.classify_color_name((0, 0, 1))
    assert near_black['tone_id'] != 'vivid'
    assert near_black['confidence'] < 1.0


def test_classify_color_name_stable():
    """同一 RGB 多次命名结果一致（模型只读）"""
    rgb = (180, 146, 170)
    assert len({str(naming.classify_color_name(rgb)) for _ in range(5)}) == 1


def test_naming_model_version_matches_artifact():
    """运行时模型版本等于模型 JSON 的 version 字段"""
    assert naming.get_naming_model_version() == _load_model_artifact()['version']


def test_cache_key_includes_naming_model_version(monkeypatch):
    """缓存键含模型版本：更换模型版本后旧分析结果不再命中"""
    cache = e.ColorDistributionCache(max_size=2)
    monkeypatch.setattr(e, 'get_naming_model_version', lambda: 'v1')
    cache.set('img', {'palette': []})
    assert cache.get('img') == {'palette': []}
    monkeypatch.setattr(e, 'get_naming_model_version', lambda: 'v2')
    assert cache.get('img') is None


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
    assert {c['name'] for c in dark['composition']} == {'orange_red', 'blue'}
    for c in dark['composition']:
        assert c['color_name'] == naming.classify_color_name(c['rgb'])


def test_zones_neutral_single_side_plain():
    """近中性暗区仅冷色 → 维持纯"接近中性"，构成为空"""
    L, C, h_ok, hsb = _zone_arrays(4000, 0.30, 0.012, (250.0,))
    zones = e.analyze_zones(L, C, h_ok, hsb)
    dark = zones['dark']
    assert dark['label_key'] == 'zone_neutral' and dark['mix'] is False
    assert dark['composition'] == []


# ==================== 主色卡 / 构成携带结构化色名 ====================

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


def test_palette_carries_color_name():
    """主色卡条目为 {rgb, weight_pct, color_name}，名称由最终 RGB 计算"""
    lab = _lab_clusters(((0.40, 0.05, 0.06), 5000, 1),
                        ((0.55, 0.0, -0.14), 3000, 2))
    result = e.analyze_palette(lab)
    assert result
    for item in result:
        assert set(item) == {'rgb', 'weight_pct', 'color_name'}
        assert len(item['rgb']) == 3 and isinstance(item['weight_pct'], float)
        assert item['color_name'] == naming.classify_color_name(item['rgb'])


def test_composition_carries_color_name():
    """构成条目含 color_name；暗暖足彩段命中棕"""
    n = 3000
    C = np.full(n, 0.10)
    h = np.full(n, 30.0)             # 橙红
    L = np.full(n, 0.40)            # 暗 → 棕
    h_ok = np.full(n, ok_hue((200, 120, 40)))
    comp = e.analyze_hue_composition(C, h, None, L, h_ok)
    assert comp and comp[0]['name'] == 'orange_red'
    assert comp[0]['color_name'] == naming.classify_color_name(comp[0]['rgb'])
    assert comp[0]['color_name']['family_id'] == 'brown'


def test_composition_red_segment_color_name():
    """暗红段构成名称与代表色同源（红裙锚点：hue 6.9、L 0.34、C 0.082）"""
    n = 3000
    C = np.full(n, 0.082)
    h = np.full(n, 6.9)              # 红
    L = np.full(n, 0.34)            # 暗
    h_ok = np.full(n, ok_hue((91, 37, 28)))
    comp = e.analyze_hue_composition(C, h, None, L, h_ok)
    assert comp and comp[0]['name'] == 'red'
    assert comp[0]['color_name'] == naming.classify_color_name(comp[0]['rgb'])
    assert comp[0]['color_name']['family_id'] in ('red', 'brown')


# ==================== 名称与最终 RGB 同源 ====================

def test_palette_color_name_same_source():
    """主色卡名称可由条目最终 RGB 复算"""
    lab = _lab_clusters(((0.40, 0.05, 0.06), 5000, 1),
                        ((0.55, 0.0, -0.14), 3000, 2))
    for item in e.analyze_palette(lab):
        assert item['color_name'] == naming.classify_color_name(item['rgb'])


def test_composition_color_name_none_without_rgb():
    """未传 h_ok 没有代表 RGB 时 color_name 为 None，不回退另一套命名输入"""
    n = 3000
    comp = e.analyze_hue_composition(
        np.full(n, 0.10), np.full(n, 30.0), None, np.full(n, 0.40))
    assert comp and comp[0]['rgb'] is None
    assert comp[0]['color_name'] is None


def test_peak_composition_color_name_same_source():
    """峰内构成名称与绘制 RGB 同源"""
    n = 3000
    peaks = e.analyze_hue_peaks(
        np.full(n, 0.09), np.full(n, 29.0), np.full(n, 0.0), np.full(n, 0.34))
    assert peaks
    for item in peaks[0]['composition']:
        assert item['color_name'] == naming.classify_color_name(item['rgb'])


# ==================== 8.7 冷暖五档阈值（校准后冻结） ====================

def test_warmth_constants_frozen():
    """2.5d 全量验证集复核后冻结（0 张不符），阈值不变"""
    assert e.WARMTH_WEAK == 0.15
    assert e.WARMTH_STRONG == 0.5


def _warmth_key(value, n=10000):
    """构造 h=55(cos=1) 与 h=145(cos=0) 两组，令 warmth 值 ≈ value（可负）"""
    warm_pole = 55.0 if value >= 0 else 235.0    # 235° 相对 55° cos=-1
    n1 = round(abs(value) * n)
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
