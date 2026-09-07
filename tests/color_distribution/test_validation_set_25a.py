"""扩充验证集 golden 用例（断言已 key 化）

覆盖 测试图片/1~4 四组素材（46 张），场景标注见 测试图片/素材盘点.md：
- 组1 直出（13 张）：白平衡中性基线、近无彩边界、极端高调 WB 梯度对照（AZZ04162 三连）
- 组2 调色（9 张）：风格化 vs 白平衡判别正样本、整体染色、互补/邻近结构
- 组3 网络风格化（17 张）：雪景/绿植/逆光/特殊色调/感知色名等场景缺口补齐
- 组4 RAW+LR 白平衡偏移梯度（7 张）：cast 方向 ground truth 断言，
  8.1 双证据落地后全部转正（原 5 条 xfail 已摘除）

断言容差与阶段一一致：色相角 ±10°，label_key / 枚举精确匹配。
直出图 cast 期望按方案 8.0 允许"中性或轻微偏色"两档（cast_not_strong）。
8.1 三态输出：cast_neutral / cast_wb_error / cast_styled（label_args 携带
level + direction id 元组），低置信为 confidence=0.5（UI 追加后缀）；
双证据均不可用时仍报 cast_unknown（kind='unknown'）。
"""

import functools
import os

import pytest

from core import color_distribution as e
from tests.color_distribution.conftest import ROOT, load_image_rgb, materials_missing

# 素材目录不随仓库分发，其他机器整模块跳过（本机必跑）
pytestmark = pytest.mark.skipif(
    materials_missing('测试图片'),
    reason='验证集素材目录缺失，跳过图片 golden')

HUE_TOL = 10.0


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
    # ---------- 组1 直出（相机原片，无风格化） ----------
    ('测试图片/1/AZZ04073.jpg', '直出·樱花蓝天(蓝天误导cast的8.1边界样本)', {
        'cast_not_strong': True,        # 直出允许中性或轻微，不得报"明显"
        'harmony': 'harmony_monochromatic',
        'top_peak': ('cyan_blue', 215),
        'warmth_key': 'warmth_strong_cool',
        'bright_dominant': True,
    }),
    ('测试图片/1/AZZ04134.jpg', '直出·白纸巾+蓝屏(白纸L>0.9被证据一排除的边界例)', {
        # 8.1：证据二亮带兼容白纸，报中性（单证据低置信），原"不可判"退役
        'cast_key': 'cast_neutral',
        'cast_confidence': 0.5,
        'harmony': 'harmony_monochromatic',
        'top_peak': ('cyan_blue', 211),
        'chroma_key': 'chroma_low',
    }),
    ('测试图片/1/AZZ04162.jpg', '直出·高调棚拍手办(暖WB版)', {
        'cast_key': 'cast_unknown',     # 亮部99%全被候选排除
        'top_peak': ('orange_red', 33),
        'warmth_key': 'warmth_strong_warm',
        'bright_dominant': True,
        'chroma_key': 'chroma_low',
    }),
    ('测试图片/1/AZZ04162-2.jpg', '直出·高调棚拍手办(近中性WB版)', {
        'cast_key': 'cast_unknown',
        'top_peak': ('orange_red', 22),
        'warmth_key': 'warmth_strong_warm',
        'bright_dominant': True,
    }),
    ('测试图片/1/AZZ04162-3.jpg', '直出·高调棚拍手办(冷WB版)', {
        # 8.1：亮部全剪切回退暗带，暗带高度集中(D/σ=35)报出冷方向，
        # 救援路径+低残差彩度判白平衡偏差（与此图冷 WB 版真值一致）
        'cast_key': 'cast_wb_error',
        'cast_level': 'strong',
        'cast_direction': ('cool_blue', 'magenta'),
        'cast_confidence': 0.5,
        'top_peak': ('blue', 226),
        'warmth_key': 'warmth_strong_cool',
        'bright_dominant': True,
    }),
    ('测试图片/1/AZZ04821.jpg', '直出·蓝天仙人掌(中性底图候选)', {
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'harmony': 'harmony_monochromatic',
        'top_peak': ('cyan_blue', 209),
        'warmth_key': 'warmth_strong_cool',
    }),
    ('测试图片/1/DSC00429.jpg', '直出·室内双人人像(展会混合光)', {
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        # 2.5b：暖色家族宽(橙~黄)+对向窄蓝，Y 模板(宽+窄对向)拟合最优，
        # 双窄扇区 I 装不下宽暖调，旧"互补"系两峰夹角规则的粗粒度结论
        'harmony': 'harmony_split_complementary',
        'top_peak': ('orange_red', 26),
        'chroma_key': 'chroma_low',
    }),
    ('测试图片/1/DSC00802.jpg', '直出·蓝调时刻城市夜景', {
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'top_peak': ('cyan_blue', 216),
        'dark_dominant': True,          # 夜景暗部主导
    }),
    ('测试图片/1/DSC01639.jpg', '直出·白鸭灰地(最佳合成底图)', {
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'chroma_key': 'chroma_low',
        'top_peak': ('orange_red', 28),
    }),
    ('测试图片/1/DSC01961.jpg', '直出·晨雾日出城市(黄金时刻)', {
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'warmth_key': 'warmth_strong_warm',
        'top_peak': ('orange_red', 28),
    }),
    ('测试图片/1/DSC09895.jpg', '直出·逆光剪影人物街道', {
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'harmony': 'harmony_monochromatic',
        'top_peak': ('orange_red', 30),
        'warmth_key': 'warmth_strong_warm',
        'dark_dominant': True,          # 剪影暗部主导
    }),
    ('测试图片/1/QSG03394.jpg', '直出·手机硬光棚拍(近无彩边界)', {
        # 8.1：证据二亮带近零，单证据报中性低置信（原"不可判"）
        'cast_key': 'cast_neutral',
        'cast_confidence': 0.5,
        'chroma_key': 'chroma_low',
        'harmony': 'harmony_monochromatic',
    }),
    ('测试图片/1/QSG03395.jpg', '直出·手机棚拍另一角度(近无彩)', {
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'chroma_key': 'chroma_low',
    }),

    # ---------- 组2 调色（HSL 等风格化处理） ----------
    ('测试图片/2/1178021690.jpg', '日系小清新(低饱和偏冷)', {
        'top_peak': ('cyan', 190),
        'chroma_key': 'chroma_low',
        'warmth_key': 'warmth_strong_cool',
        'bright_dominant': True,
    }),
    ('测试图片/2/1200110207.jpg', '海湾大桥日落(粉橙天+深蓝海)', {
        'top_peak': ('red', 12),
        # 2.5b：粉橙与深蓝两家族对向，I 模板拟合达标——旧"自由"系多峰
        # 夹角落在规则外的误报，互补才是此图的正确描述
        'harmony': 'harmony_complementary',
    }),
    ('测试图片/2/48704.jpg', 'teal夜景光轨(近中性参照实测)', {
        # 8.1 实测：候选与亮带参照均真中性(s<0.01)、全局倾向弱，
        # 维持中性——盘点时"应转风格化倾向"的设想在统计上不成立
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'top_peak': ('cyan_blue', 196),
        'warmth_key': 'warmth_strong_cool',
    }),
    ('测试图片/2/50052.jpg', '城市夜景俯瞰(暖橙+青灰)', {
        'harmony': 'harmony_complementary',
        'top_peak': ('orange_red', 16),
    }),
    ('测试图片/2/543678808.jpg', '蓝调时刻猫剪影(深蓝单色)', {
        # 8.1：亮带空回退暗带(D/σ=5.6)，报风格化倾向（原"不可判"）
        'cast_key': 'cast_styled',
        'cast_level': 'weak',
        'cast_direction': ('blue', 'magenta'),
        'cast_confidence': 0.5,
        'harmony': 'harmony_monochromatic',
        'top_peak': ('cyan_blue', 206),
        'warmth_key': 'warmth_strong_cool',
    }),
    ('测试图片/2/692665127.jpg', '水塔晚霞(粉紫渐变,色相跨0°)', {
        'top_peak': ('red', 0),         # 实测 360°，环形容差应按 0° 判等
        'dark_dominant': True,
    }),
    ('测试图片/2/761801996.jpg', '黄金时刻逆光人群(整体染色)', {
        'style': {'label_key': 'style_unified', 'label_args': {'hue': 'orange_red'}},
        'warmth_key': 'warmth_strong_warm',
        'top_peak': ('orange_red', 32),
        'cast_dir_any': ('warm_yellow',),
    }),
    ('测试图片/2/922040775.jpg', '蓝调大桥长曝光(风格化vs白平衡判别正样本)', {
        'style': {'label_key': 'style_unified', 'label_args': {'hue': 'cyan_blue'}},
        'top_peak': ('cyan_blue', 206),
        'cast_dir_any': ('cool_blue',),
        'warmth_key': 'warmth_strong_cool',
    }),
    ('测试图片/2/955724375.jpg', '图书馆走廊(暖阳光+蓝椅)', {
        'harmony': 'harmony_complementary',
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'top_peak': ('orange_red', 22),
    }),

    # ---------- 组3 网络风格化（场景缺口补齐） ----------
    ('测试图片/3/1774980698568.jpg', '绿植风光', {
        # 感知色名阶段一：红裙暗部第 4 条 red 段（C=0.082）不再归棕 → 深红；
        # 暗橙红段仍为棕（双轴偏移属阶段三范畴）
        'top_peak': ('yellow_green', 90),
        'dark_comp': [('cyan_green', 'cyan_green'), ('green', 'green'),
                      ('orange_red', 'brown'), ('red', 'deep_red')],
        # 阶段三验收 1：橙红峰内出现 red 段（峰内 14.95% ≥1%，pname=red）——
        # HSB 段归属 + chroma 权重可见成员代表值，红裙红色身份端到端呈现；
        # yellow_green 峰 5 条固化"不截断"裁决
        'peaks_comp': [
            ('yellow_green', [('yellow_green', 'yellow_green'),
                              ('yellow', 'warm_gray'), ('green', 'green'),
                              ('cyan_green', 'cyan_green'),
                              ('orange_red', 'orange_red')]),
            ('orange_red', [('orange_red', 'orange_red'), ('red', 'red')]),
            ('cyan', [('cyan_blue', 'cyan_blue'), ('cyan', 'cyan'),
                      ('cyan_green', 'cyan_green')]),
        ],
    }),
    ('测试图片/3/DM_20260518185447_001.jpg', '风光(青绿+黄多色构成)', {
        # 2.5b：宽黄绿家族+对向窄蓝紫，Y 模板拟合达标，旧"自由"系规则盲区
        'harmony': 'harmony_split_complementary',
        'top_peak_name': 'yellow_green',
        # 阶段三验收 2：yellow_green 峰内 yellow 段（峰内 16.08% ≥1%）——
        # 黄色身份在绿峰内呈现；暗黄可见成员忠实判棕
        'peaks_comp': [
            ('yellow_green', [('yellow_green', 'yellow_green'),
                              ('yellow', 'brown'), ('green', 'green')]),
            ('cyan_blue', [('cyan_blue', 'cyan_blue'), ('blue', 'blue'),
                           ('cyan', 'cyan')]),
            ('orange_red', [('orange_red', 'orange_red'),
                            ('red', 'deep_red')]),
        ],
    }),
    ('测试图片/3/imgi_20_24a15955fce2433a92d38bcecf8ba8ef.jpg', '绿调风光(整体绿调)', {
        # 2.5b：全部色相落在约 90° 连续扇区内，V 模板即单色大扇区——
        # 单色↔邻近边界图，按模板词汇归单色（style 仍锁定整体染绿）
        'harmony': 'harmony_monochromatic',
        'style': {'label_key': 'style_unified', 'label_args': {'hue': 'green'}},
        'top_peak': ('cyan_green', 158),
        'dark_dominant': True,
    }),
    ('测试图片/3/imgi_23_824170d5a5d24995bcef2df6333696a4.jpg', '紫橙对比风光', {
        'style': {'label_key': 'style_teal_orange', 'label_args': {}},
        'top_peak': ('blue', 233),
    }),
    ('测试图片/3/imgi_25_631fa5ad48f84f79a33ff9dbff1a7d10.jpg', '品红/紫调(色相跨0°邻域)', {
        'top_peak': ('purple_red', 332),
        'style': {'label_key': 'style_unified', 'label_args': {'hue': 'purple_red'}},
    }),
    ('测试图片/3/imgi_28_05d4c5a1d5ce4cdc804c9cdb42cec08f.jpg', '雪山小镇航拍(高调偏蓝)', {
        # 8.1：雪地亮带高度集中地偏蓝(D/σ=8.3)，证据一缺席时低置信报出
        # （雪景蓝调与冷 WB 统计同构，方向本身属实，原"不可判"）
        'cast_key': 'cast_wb_error',
        'cast_level': 'strong',
        'cast_direction': ('cool_blue', 'green'),
        'cast_confidence': 0.5,
        'harmony': 'harmony_monochromatic',
        'top_peak': ('cyan_blue', 209),
        'warmth_key': 'warmth_strong_cool',
    }),
    ('测试图片/3/imgi_32_0195f827801d4139b4ddea808f13f82e.jpg', '雪村夜景(蓝调雪地+暖窗灯)', {
        'style': {'label_key': 'style_teal_orange', 'label_args': {}},
        'top_peak': ('cyan_blue', 215),
        'warmth_key': 'warmth_strong_cool',
    }),
    ('测试图片/3/imgi_169_43d954f9aa0f4659afa210a1182ab35d.jpg', '雪林鹿剪影(粉橘日落,色相跨0°)', {
        'style': {'label_key': 'style_teal_orange', 'label_args': {}},
        'top_peak': ('red', 0),
        'chroma_key': 'chroma_low',
    }),
    ('测试图片/3/imgi_14_ecec0afb606c4dfea051e30d98b70ad2.jpg', '雪山星空银河(夜景低调)', {
        'top_peak': ('cyan_blue', 224),
        'warmth_key': 'warmth_strong_cool',
        'dark_dominant': True,
    }),
    ('测试图片/3/DM_20260518184829_001.jpg', '日光人像(抱羊羔,胶片感)', {
        'cast_key': 'cast_neutral',
        'cast_confidence': 1.0,
        'top_peak': ('cyan_blue', 205),
        'chroma_key': 'chroma_low',
    }),
    ('测试图片/3/imgi_260_1014384041.jpg', '火山黑荒漠+熔岩红(特殊色调)', {
        'top_peak': ('cyan_blue', 219),
        'chroma_key': 'chroma_low',
        'dark_dominant': True,
    }),
    ('测试图片/3/imgi_44_cover-500px96506015f4a2b3a8a504cad8d082faf9b86ef7c.jpg',
     '秋日森林小径(8.6感知色名"棕"样本)', {
        'style': {'label_key': 'style_unified', 'label_args': {'hue': 'orange_red'}},
        'top_peak': ('orange_red', 44),
        'warmth_key': 'warmth_strong_warm',
        # 感知色名阶段一反例锚点：真棕仍为棕（暗黄 brown、中间调双 brown），
        # 暗部 red 段 C=0.015 属灰族不翻转（仍 warm_gray）
        'dark_comp': [('orange_red', 'warm_gray'), ('yellow', 'brown'),
                      ('red', 'warm_gray')],
        'mid_comp': [('orange_red', 'brown'), ('yellow', 'brown')],
    }),
    ('测试图片/3/imgi_4_500px1073341026.jpg', '暖黄风光', {
        'top_peak': ('yellow', 48),
        'warmth_key': 'warmth_strong_warm',
        'harmony': 'harmony_monochromatic',
        # 阶段三辅证锚点：单峰 100% 展开 4 条；red 段可见成员彩度仍低
        # （面积 0.83%），忠实保持灰族 warm_gray——灰族不误翻红的反向边界
        'peaks_comp': [
            ('yellow', [('yellow', 'yellow'), ('orange_red', 'orange_red'),
                        ('yellow_green', 'yellow_green'), ('red', 'warm_gray')]),
        ],
    }),
    ('测试图片/3/imgi_57_d4523d4bfdb4473a9f57daa6c506d76f.jpg', '蓝金风光(风格化判别正样本)', {
        # 2.5b 平滑隶属度：亮部纳入过渡带橙调后均值 40° 归橙红（原 47° 黄边界），
        # 暗部 201° 青蓝，风格命中青橙规则——与蓝金同属冷暖对比，边界图改判合理
        'style': {'label_key': 'style_teal_orange', 'label_args': {}},
        'top_peak': ('orange_red', 28),
        'warmth_key': 'warmth_warm',
    }),
    ('测试图片/3/imgi_59_500px1121759522.jpg', '紫红邻近色(高cast风格化)', {
        # 2.5b：紫~紫红连续扇区 V 模板拟合几乎完美(E<1)，单色↔邻近边界图归单色
        'harmony': 'harmony_monochromatic',
        'top_peak': ('purple_red', 328),
    }),
    ('测试图片/3/imgi_8_1115639033.jpg', '蓝调夜空(单色蓝)', {
        'style': {'label_key': 'style_unified', 'label_args': {'hue': 'cyan_blue'}},
        'top_peak': ('cyan_blue', 215),
        'warmth_key': 'warmth_strong_cool',
    }),
    ('测试图片/3/AZZ04169.jpg', '高调白背景手办(亮部99%边界例)', {
        'cast_key': 'cast_unknown',
        'bright_dominant': True,
        'chroma_key': 'chroma_low',
    }),
]


@pytest.mark.parametrize('rel, note, expect', VALIDATION,
                         ids=[v[0].split('/')[-1][:24] for v in VALIDATION])
def test_validation_image_25a(rel, note, expect):
    r = _analyze(rel)

    if 'harmony' in expect:
        assert r['harmony'] == expect['harmony'], f'{note} harmony'
    if 'chroma_key' in expect:
        assert r['chroma_dist']['label_key'] == expect['chroma_key'], f'{note} chroma'
    if 'warmth_key' in expect:
        assert r['warmth']['label_key'] == expect['warmth_key'], f'{note} warmth'
    if 'cast_key' in expect:
        assert r['cast']['label_key'] == expect['cast_key'], f'{note} cast'
    if 'cast_level' in expect:
        assert r['cast']['label_args']['level'] == expect['cast_level'], f'{note} cast 级别'
    if 'cast_direction' in expect:
        assert r['cast']['label_args']['direction'] == expect['cast_direction'], f'{note} cast 方向'
    if 'cast_confidence' in expect:
        assert r['cast']['confidence'] == expect['cast_confidence'], f'{note} cast 置信度'
    if 'cast_dir_any' in expect:
        direction = r['cast']['label_args'].get('direction', ())
        assert any(d in direction for d in expect['cast_dir_any']), f'{note} cast 方向'
    if expect.get('cast_not_strong'):
        assert r['cast']['label_args'].get('level') != 'strong', f'{note} 直出图不得报明显偏色'
    if 'style' in expect:
        assert r['zones']['style'] == expect['style'], f'{note} style'
    if 'top_peak_name' in expect:
        tp = _top_peak(r)
        assert tp is not None and tp['name'] == expect['top_peak_name'], f'{note} 主峰色名'
    if 'top_peak' in expect:
        name, hue = expect['top_peak']
        tp = _top_peak(r)
        assert tp is not None, f'{note} 应有主色相峰'
        assert tp['name'] == name, f'{note} 主峰色名 got {tp["name"]}'
        assert _hue_close(tp['hue'], hue), f'{note} 主峰色相 {tp["hue"]:.0f} vs {hue}'
    if 'dark_comp' in expect:
        got = [(c['name'], c['pname']) for c in r['zones']['dark']['composition']]
        assert got == expect['dark_comp'], f'{note} 暗部构成 {got}'
    if 'mid_comp' in expect:
        got = [(c['name'], c['pname']) for c in r['zones']['mid']['composition']]
        assert got == expect['mid_comp'], f'{note} 中间调构成 {got}'
    if 'peaks_comp' in expect:
        # 阶段三峰内构成：(峰名, [(段名, 感知名), ...]) 有序精确断言；
        # 列表按峰权重降序、段按峰内权重降序，不截断（yellow_green 峰
        # 5 条 > COMP_MAX=4 同时固化"不截断"裁决）
        got = [(p['name'], [(c['name'], c['pname']) for c in p['composition']])
               for p in r['hue_peaks']]
        assert got == expect['peaks_comp'], f'{note} 峰内构成 {got}'
    if expect.get('bright_dominant'):
        assert r['zones']['bright']['pixel_pct'] > 40.0, f'{note} 应亮部主导'
    if expect.get('dark_dominant'):
        assert r['zones']['dark']['pixel_pct'] > 40.0, f'{note} 应暗部主导'


# ---------- 组4：RAW+LR 白平衡偏移梯度（cast 方向 ground truth） ----------
#
# 底图 AZZ04134（白纸巾+蓝屏），ground truth 为相对基准版的全图 OKLab Δa/Δb 实测。
# 8.1 双证据落地：证据二亮部参照带兼容白纸（原 L>0.9 被排除）并可否决
# 蓝屏伪中性候选，六张偏移版方向/级别全部报对（原 5 条 xfail 已转正摘标）。
#
# 每条：(文件, 真值说明, 方向必含其一, 方向禁含, 强度级别要求或 None)

WB_GRADIENT = [
    pytest.param('AZZ04134-2.jpg', 'Δb=-0.020 色温调低(轻微偏冷)',
                 ('cool_blue', 'blue'), ('warm_yellow', 'yellow'), None),
    pytest.param('AZZ04134-3.jpg', 'Δb=-0.082 色温调低(明显偏冷)',
                 ('cool_blue', 'blue'), ('warm_yellow', 'yellow'), 'strong'),
    pytest.param('AZZ04134-4.jpg', 'Δb=+0.056 色温调高(偏暖)',
                 ('warm_yellow', 'yellow'), ('cool_blue', 'blue', 'green'), None),
    pytest.param('AZZ04134-5.jpg', 'Δb=+0.093 色温调高(明显偏暖,本组最强)',
                 ('warm_yellow', 'yellow'), ('cool_blue', 'blue'), 'strong'),
    pytest.param('AZZ04134-6.jpg', 'Δa=+0.022 Tint偏品红',
                 ('magenta',), ('green',), None),
    pytest.param('AZZ04134-7.jpg', 'Δa=-0.042 Tint偏绿(明显)',
                 ('green',), ('magenta',), 'strong'),
]


def test_wb_gradient_baseline():
    """基准版：白平衡相对正常，允许"中性"（含单证据低置信档）"""
    r = _analyze('测试图片/4/AZZ04134.jpg')
    assert r['cast']['label_key'] == 'cast_neutral'
    assert r['cast']['kind'] == 'neutral'


@pytest.mark.parametrize('fname, truth, require_any, forbid, level', WB_GRADIENT,
                         ids=[p.values[0] for p in WB_GRADIENT])
def test_wb_gradient_direction(fname, truth, require_any, forbid, level):
    r = _analyze(f'测试图片/4/{fname}')
    cast = r['cast']

    assert cast['label_key'] != 'cast_unknown', f'{truth}: 不可判（应报出方向）'
    assert cast['label_key'] != 'cast_neutral', f'{truth}: 漏报为中性'
    direction = cast['label_args']['direction']
    assert any(k in direction for k in require_any), f'{truth}: 方向缺失 got {direction}'
    assert not any(k in direction for k in forbid), f'{truth}: 方向报反 got {direction}'
    if level:
        assert cast['label_args']['level'] == level, f'{truth}: 强度级别应为{level}'


def test_wb_gradient_non_cast_stability():
    """组4 同一底图仅白平衡不同：非 cast 模块的分区占比应保持稳定"""
    base = _analyze('测试图片/4/AZZ04134.jpg')
    shifted = _analyze('测试图片/4/AZZ04134-2.jpg')
    for zone in ('dark', 'mid', 'bright'):
        assert abs(base['zones'][zone]['pixel_pct']
                   - shifted['zones'][zone]['pixel_pct']) < 5.0, f'{zone} 占比漂移'
