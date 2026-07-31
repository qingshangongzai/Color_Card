"""验证集 golden 用例（断言已 key 化）

从 测试图片/、51055510/、121231221/ 挑选 10 张典型图，人工目检标注预期关键结论，
覆盖：高调、低调/黑白、蓝金(互补/分区染色)、高饱和、单色蓝调、暖调、
绿调画作、以及 Display P3 与 sRGB 同图一致性。

断言只锁定各图"定义性"的稳定输出，容差按方案：色相角 ±10°、连续值 ±0.02，
label_key / 枚举字段精确匹配，避免浮点差异导致脆断。
色相角与色名 id 按主项目 HSB 12 色环标准（引擎内部统计仍为 OKLCH 轴）。
"""

import functools
import os

import pytest

from core import color_distribution as e
from tests.color_distribution.conftest import ROOT, load_image_rgb, materials_missing

# 素材目录不随仓库分发，其他机器整模块跳过（本机必跑）
pytestmark = pytest.mark.skipif(
    materials_missing('测试图片', '51055510', '121231221'),
    reason='验证集素材目录缺失，跳过图片 golden')

HUE_TOL = 10.0        # 色相角容差（度）
VALUE_TOL = 0.02      # 连续值容差


@functools.lru_cache(maxsize=None)
def _analyze(rel: str) -> dict:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        pytest.skip(f'验证集图片缺失: {rel}')
    return e.analyze_color_distribution(load_image_rgb(path))


def _top_peak(result: dict) -> dict | None:
    peaks = result['hue_peaks']
    return peaks[0] if peaks else None


def _hue_close(a: float, b: float, tol: float = HUE_TOL) -> bool:
    return e.circular_diff(a, b) <= tol


# 验证集：(相对路径, 人工标注说明, 期望断言 dict)
VALIDATION = [
    ('51055510/1774857334632.jpeg', '高调人像·樱花白裙(冷蓝天)', {
        'chroma_key': 'chroma_low',
        'warmth_key': 'warmth_strong_cool',
        # 2.5b 模板拟合：黄绿中间调(权重~15%)+青蓝天空实为双色家族，
        # L 模板(窄黄绿+宽青蓝)拟合优于单扇区，旧"单色"系峰高规则漏报
        'harmony': 'harmony_complementary',
        'top_peak': ('cyan_blue', 204),
        'bright_dominant': True,        # 高调：亮部占比 > 60%
    }),
    ('51055510/imgi_93_3d74a0422ce44c6db83d5933788b85e1.jpg', '黑白低调沙漠', {
        'harmony': 'harmony_achromatic',
        'chroma_key': 'chroma_low',
        'warmth_key': 'warmth_neutral',
        'peaks_empty': True,            # 黑白：所有色相输出为空
        'bright_minimal': True,         # 低调：亮部内容极少
    }),
    ('51055510/imgi_26_4d9cb11be7e44f26b981147a25778884.jpg', '蓝金·风电场(蓝天+金色荒漠)', {
        'harmony': 'harmony_complementary',
        'style': {'label_key': 'style_blue_gold', 'label_args': {}},
        'warmth_key': 'warmth_warm',
        'top_peak_name': 'orange_red',
    }),
    ('测试图片/PixPin_2026-02-27_00-18-13.png', '高饱和·红底黄马插画', {
        'chroma_key': 'chroma_high',
        'warmth_key': 'warmth_strong_warm',
        'harmony': 'harmony_monochromatic',
        'top_peak': ('red', 3),
    }),
    ('51055510/1774980787589.jpg', '单色蓝调·夜空月亮', {
        'harmony': 'harmony_monochromatic',
        'warmth_key': 'warmth_strong_cool',
        'top_peak': ('cyan_blue', 206),
        'cast_dir_any': ('cool_blue',),
        'style': {'label_key': 'style_unified', 'label_args': {'hue': 'cyan_blue'}},
    }),
    ('51055510/imgi_24_500px1122030971.jpg', '暖调·晨雾日出', {
        'warmth_key': 'warmth_strong_warm',
        'harmony': 'harmony_monochromatic',
        'cast_dir_any': ('warm_yellow',),
        'top_peak': ('orange_red', 28),
        'style': {'label_key': 'style_unified', 'label_args': {'hue': 'orange_red'}},
    }),
    ('51055510/DM_20260518185501_001.jpg', '暖调·沙漠日落', {
        'warmth_key': 'warmth_strong_warm',
        'harmony': 'harmony_monochromatic',
        'chroma_key': 'chroma_low',
        'top_peak': ('orange_red', 27),
    }),
    ('测试图片/2023_NYR_22055_0035B_000(claude_monet_le_bassin_aux_nympheas_d6453115104217).jpg',
     'Monet睡莲·绿调画作', {
        'harmony': 'harmony_monochromatic',
        'chroma_key': 'chroma_medium',
        'warmth_key': 'warmth_warm',
        'top_peak': ('yellow', 63),
    }),
    ('121231221/测试 - Display P3.jpg', 'Display P3 原图(绿调、白平衡中性)', {
        'cast_key': 'cast_neutral',
        'chroma_key': 'chroma_low',
        'warmth_key': 'warmth_neutral',
        'top_peak': ('yellow_green', 78),
    }),
    ('121231221/测试-photo RGB.jpg', 'sRGB 同图(与 P3 应一致)', {
        'cast_key': 'cast_neutral',
        'chroma_key': 'chroma_low',
        'warmth_key': 'warmth_neutral',
        'top_peak': ('yellow_green', 77),
    }),
]


@pytest.mark.parametrize('rel, note, expect', VALIDATION,
                         ids=[v[0].split('/')[-1][:20] for v in VALIDATION])
def test_validation_image(rel, note, expect):
    r = _analyze(rel)

    if 'harmony' in expect:
        assert r['harmony'] == expect['harmony'], f'{note} harmony'
    if 'chroma_key' in expect:
        assert r['chroma_dist']['label_key'] == expect['chroma_key'], f'{note} chroma'
    if 'warmth_key' in expect:
        assert r['warmth']['label_key'] == expect['warmth_key'], f'{note} warmth'
    if 'cast_key' in expect:
        assert r['cast']['label_key'] == expect['cast_key'], f'{note} cast'
    if 'cast_dir_any' in expect:
        direction = r['cast']['label_args'].get('direction', ())
        assert any(d in direction for d in expect['cast_dir_any']), f'{note} cast 方向'
    if 'style' in expect:
        assert r['zones']['style'] == expect['style'], f'{note} style'
    if expect.get('peaks_empty'):
        assert r['hue_peaks'] == [], f'{note} 应无色相峰'
    if 'top_peak_name' in expect:
        tp = _top_peak(r)
        assert tp is not None and tp['name'] == expect['top_peak_name'], f'{note} 主峰色名'
    if 'top_peak' in expect:
        name, hue = expect['top_peak']
        tp = _top_peak(r)
        assert tp is not None, f'{note} 应有主色相峰'
        assert tp['name'] == name, f'{note} 主峰色名 got {tp["name"]}'
        assert _hue_close(tp['hue'], hue), f'{note} 主峰色相 {tp["hue"]:.0f} vs {hue}'
    if expect.get('bright_dominant'):
        assert r['zones']['bright']['pixel_pct'] > 60.0, f'{note} 高调应亮部主导'
    if expect.get('bright_minimal'):
        assert r['zones']['bright']['pixel_pct'] < 2.0, f'{note} 低调应亮部极少'


def test_p3_srgb_consistency():
    """同一张图的 Display P3 与 sRGB 版本，ICC 归一后统计结果应一致"""
    p3 = _analyze('121231221/测试 - Display P3.jpg')
    srgb = _analyze('121231221/测试-photo RGB.jpg')

    assert p3['cast']['label_key'] == srgb['cast']['label_key']
    assert p3['chroma_dist']['label_key'] == srgb['chroma_dist']['label_key']
    assert p3['warmth']['label_key'] == srgb['warmth']['label_key']
    assert abs(p3['warmth']['value'] - srgb['warmth']['value']) < VALUE_TOL
    assert abs(p3['chroma_dist']['p50'] - srgb['chroma_dist']['p50']) < VALUE_TOL

    tp3, tsrgb = _top_peak(p3), _top_peak(srgb)
    assert tp3 is not None and tsrgb is not None
    assert tp3['name'] == tsrgb['name']
    assert _hue_close(tp3['hue'], tsrgb['hue'])


def test_output_structure():
    """输出字典字段完整（harmony_fit + 可视化字段）"""
    r = _analyze('121231221/测试-photo RGB.jpg')
    assert set(r) == {'cast', 'zones', 'hue_peaks', 'harmony', 'harmony_fit',
                      'palette', 'warmth', 'chroma_dist', 'wheel', 'image_size'}
    assert set(r['zones']) == {'dark', 'mid', 'bright', 'style'}
    assert set(r['cast']) >= {'vector', 'strength', 'label_key', 'label_args'}
    assert set(r['harmony_fit']) == {'template', 'rotation', 'error', 'confidence'}
    assert r['harmony_fit']['template'] in ('i', 'V', 'L', 'I', 'T', 'Y', 'X', 'N')
    assert 0.0 <= r['harmony_fit']['confidence'] <= 1.0
    assert r['wheel'].shape == (e.WHEEL_HUE_BINS, e.WHEEL_CHROMA_BINS)
    assert len(r['image_size']) == 2
    assert 1 <= len(r['palette']) <= e.PALETTE_K
    for (rgb, pct, pname) in r['palette']:
        assert len(rgb) == 3 and all(0 <= c <= 255 for c in rgb)
        assert isinstance(pct, float)
        assert isinstance(pname, str) and pname
