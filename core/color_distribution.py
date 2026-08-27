"""色彩分布分析服务模块（OKLCH 引擎）

回答摄影师的四个问题：色偏、分区调色、配色结构、主色卡，
附冷暖倾向与彩度分布。

设计原则：
- 用 OKLab / OKLCH 取代 HSV，暗部噪点的 chroma 天然趋近 0，无需防御代码
- 用 chroma 加权取代硬阈值过滤，用环形合矢量长度 R 取代人为置信度
- 纯 NumPy 向量化，无逐像素 Python 循环，不依赖任何 Qt
- 结论输出 label_key + label_args（色名/档名均为 id），成品文案由 UI 层
  经 locales 词条翻译，引擎不内嵌任何语言的成品文案

入参约定：主程序图片加载层已完成 ICC→sRGB 归一，本模块不做 ICC 转换。
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

from .cache_base import BaseCache

# ==================== 阈值常量（验证集标定后冻结） ====================

MAX_DIM = 1024                    # 降采样长边上限（约 1M 像素）

# 色偏检测（双证据 + 三态语义）
CAST_CHROMA_CAP = 0.05            # 近中性候选 chroma 上限（与 P30 取小）
CAST_L_LOW = 0.2                  # 候选像素明度下限（排除死黑）
CAST_L_HIGH = 0.9                 # 候选像素明度上限（排除死白）
CAST_CANDIDATE_MIN_PCT = 5.0      # 候选占比低于此值证据一不可用
CAST_WEAK = 0.01                  # 轻微偏色下限（证据一尺度）
CAST_STRONG = 0.03                # 明显偏色下限（证据一尺度）
CAST_REF_BRIGHT_Q = (0.75, 0.98)  # 证据二亮部参照带（L 秩分位，Cheng 2014 简化）
CAST_REF_DARK_Q = (0.005, 0.10)   # 亮带空时的暗部参照带回退（如极端高调图）
CAST_REF_CLIP_L = 0.985           # 参照带排除剪切白（a/b 被剪切压缩到 0）
CAST_REF_BLACK_L = 0.05           # 暗带排除死黑
CAST_REF_CHROMA_CAP = 0.08        # 参照带低彩上限（排除高彩场景内容）
CAST_REF_MIN_PX = 50              # 参照带最少像素数，不足视为空带
CAST_REF_WEAK = 0.01              # 证据二轻微偏色下限（参照带含近剪切高光，
CAST_REF_STRONG = 0.02            # 偏移幅度系统性压缩，等级阈值按组 4 单独标定）
CAST_AGREE_MAX_DEG = 60.0         # 双证据方向夹角上限，超过视为结论相悖
CAST_OVERRIDE_CONC = 5.0          # 参照带 D/σ 达此值才可否决证据一 / 暗带才可用
CAST_SKY_HUE = (225.0, 262.0)     # 天空蓝色相区（OKLab ab 角）：蓝天/雪地与冷
                                  # 偏移统计同构，此区内的参照带不得否决证据一
CAST_WB_RESID_MAX = 0.09          # 参照带救援/否决路径下，去除检出偏移后残差
                                  # 彩度 P50 低于此判白平衡偏差，否则判风格化
                                  # （极高彩场景的参照带多为场景内容而非中性面）

# 分区调色（平滑隶属度）
ZONE_DARK_MAX = 0.35              # 暗部过渡带中心（OKLab L）
ZONE_BRIGHT_MIN = 0.7            # 亮部过渡带中心
ZONE_TRANSITION = 0.08            # smoothstep 过渡带半宽（验证集标定项）
ZONE_MEMBER_MIN = 0.01            # 隶属度低于此的像素不参与该区统计（省算力）
ZONE_NEUTRAL_CHROMA = 0.02        # 低于此加权彩度视为无染色
ZONE_MIN_R = 0.4                  # 环形合矢量长度低于此视为色相分散
ZONE_MIN_PCT = 2.0                # 分区占比低于此标"内容极少"
STYLE_ANALOG_MAX = 40.0           # 暗亮同色相判定上限
STYLE_OPPOSITE_MIN = 120.0        # 暗亮对立色相判定下限

# 色相峰检测
HUE_BINS = 72                     # 色相直方图 bin 数（每 bin 5°）
HUE_SMOOTH_SIGMA = 10.0           # 环形高斯平滑标准差（度）
HUE_PEAK_MIN_RATIO = 0.20         # 主峰高度下限（相对最高峰），参与和谐判定
HUE_PEAK_MINOR_RATIO = 0.05       # 次峰高度下限（相对最高峰），仅列入构成展示
HUE_PEAK_MINOR_MIN_PCT = 3.0      # 次峰权重占比下限（%），低于此值丢弃
HUE_PEAK_MERGE_DIST = 30.0        # 相距小于此的峰合并（度）
HUE_PEAK_MAX = 3                  # 最多输出峰数

# 配色结构（Matsuda 模板拟合，验证集标定项）
HARMONY_FIT_GOOD = 14.5           # 拟合达标基线（度）：各模板达标线按覆盖宽度折减
                                  # line = GOOD * (1 - 扇区总宽/360)，宽模板须拟合得
                                  # 更好才算数；全部不达标判"自由配色 / 复杂"
HARMONY_FIT_MAX = 15.0            # 置信度尺度：confidence = 1 - E / MAX
HARMONY_SECTOR_BALANCE = 0.25     # 双扇区模板弱扇区质量须 >= 强扇区的此比例，
                                  # 防近空扇区白嫖单色分布

# 全局灰调判定（边界分支）
ACHROMATIC_EPS = 0.005            # 平均 chroma 低于此判黑白/灰调

# 色名构成（分区调色条用）
COMP_MIN_PCT = 1.0                # 色名区域 chroma 权重占比下限（%）
COMP_MIN_AREA_PCT = 2.0           # 或：可见彩度面积占比下限（%）
COMP_VISIBLE_CHROMA = 0.02        # 面积口径只计彩度高于此的可见彩色像素
COMP_MAX = 4                      # 最多输出构成条目数

# 冷暖倾向
WARM_HUE = 55.0                   # 暖极色相角（OKLCH 橙）
WARMTH_STRONG = 0.5              # 明显偏冷暖阈值
WARMTH_WEAK = 0.15               # 偏冷暖阈值

# 彩度分布
CHROMA_LOW_MAX = 0.05             # 低饱和上限（P50）
CHROMA_HIGH_MIN = 0.12            # 高饱和下限（P50）

# 主色卡（bin 初始化去随机）
PALETTE_K = 6                     # 聚类数上限（合并后自适应输出 3~6 个）
PALETTE_L_SCALE = 0.3             # 聚类时明度轴降权，避免纯色渐变图只按明度切分
PALETTE_BIN_STEP = 0.02           # OKLab 网格 bin 步长（降权特征空间）
PALETTE_INIT_MIN_DIST = 0.05      # 初始化距离抑制半径（已选中心邻域内不再选）
PALETTE_MERGE_DE = 0.04           # 聚类后中心合并阈值（未降权 ΔE_OK）

# 彩色度（Hasler & Süsstrunk 2003 心理物理七档）
COLORFULNESS_BOUNDS = (15.0, 33.0, 45.0, 59.0, 82.0, 109.0)
COLORFULNESS_KEYS = ('colorfulness_none', 'colorfulness_slight',
                     'colorfulness_moderate', 'colorfulness_medium_high',
                     'colorfulness_strong', 'colorfulness_high',
                     'colorfulness_extreme')

# 感知色名（van de Weijer 2009：棕/粉/灰需 L/C/h 共同决定，仅用于展示名）
PERCEPT_GRAY_CHROMA = 0.03       # OKLab C 低于此归灰族（介于 ZONE_NEUTRAL 0.02 与 CHROMA_LOW 0.05 间）
PERCEPT_BROWN_L_MAX = 0.55       # 暗暖色明度低于此：红段判深红/栗红，橙红/黄判"棕"
PERCEPT_DEEP_RED_CHROMA_MIN = 0.08  # 暗红彩度分界：高于此"深红"，以下（足彩）"栗红"
PERCEPT_PINK_L_MIN = 0.70        # 亮低饱和红/品红/紫红明度高于此判"粉"
PERCEPT_PINK_CHROMA_MAX = 0.10   # "粉"的彩度上限（比浓红/品红淡）
PERCEPT_WARM_NAMES = ('red', 'orange_red', 'yellow', 'magenta', 'purple_red')   # 灰族暖侧 / 冷暖混合暖侧
PERCEPT_COOL_NAMES = ('cyan', 'cyan_blue', 'blue', 'purple')                    # 灰族冷侧 / 冷暖混合冷侧
PERCEPT_BROWN_NAMES = ('orange_red', 'yellow')                           # 暗橙红/暗黄 → 棕（暗红不归棕）
PERCEPT_PINK_NAMES = ('red', 'magenta', 'purple_red')                           # 亮低饱和 → 粉
PERCEPT_ZONE_MIX_MIN_PCT = 20.0  # 近中性分区冷暖双向提示：暖侧与冷侧 chroma 权重占比均超此

# 色轮密度图可视化（随结果缓存）
WHEEL_HUE_BINS = 72        # 色轮角度 bin 数（每 bin 5°，HSB 色相）
WHEEL_CHROMA_BINS = 24     # 色轮半径 bin 数（OKLCH chroma）
WHEEL_CHROMA_MAX = 0.35    # 色轮半径上限（chroma 裁剪）

# ==================== 色名映射（主项目 HSB 12 色环标准） ====================

# HSB 色相角每 30° 一段，色名 id 居中（0°=red、30°=orange_red ... 330°=purple_red），
# 与 locales 既有 color_wheel.hue_* 词条一一对应
_HUE_NAMES = ('red', 'orange_red', 'yellow', 'yellow_green', 'green', 'cyan_green',
              'cyan', 'cyan_blue', 'blue', 'purple', 'magenta', 'purple_red')


def hue_name(hue: float) -> str:
    """HSB 色相角（度）转主项目 12 色名 id"""
    return _HUE_NAMES[int(((hue + 15.0) % 360.0) // 30.0)]


def perceptual_color_name(lightness: float, chroma: float, hue_hsb: float) -> str:
    """感知色名 id：由 L/C/h 共同决定的展示名，修饰 12 段基名

    van de Weijer 2009：棕/粉/灰无法由纯色相得出。仅用于主色卡与
    构成条目展示，hue_name（12 段）本身不变。
    - 低彩 → 灰族（暖侧 warm_gray / 冷侧 blue_gray / 其余 gray）
    - 暗红 → deep_red（高彩）/ maroon（低彩），不归棕（"棕"感知上对应暗橙/暗黄）
    - 暗橙红/暗黄 → brown
    - 亮低饱和红/品红/紫红 → pink
    """
    base = hue_name(hue_hsb)
    if chroma < PERCEPT_GRAY_CHROMA:
        if base in PERCEPT_WARM_NAMES:
            return 'warm_gray'
        if base in PERCEPT_COOL_NAMES:
            return 'blue_gray'
        return 'gray'
    if base == 'red' and lightness < PERCEPT_BROWN_L_MAX:
        return 'deep_red' if chroma >= PERCEPT_DEEP_RED_CHROMA_MIN else 'maroon'
    if base in PERCEPT_BROWN_NAMES and lightness < PERCEPT_BROWN_L_MAX:
        return 'brown'
    if (base in PERCEPT_PINK_NAMES and lightness >= PERCEPT_PINK_L_MIN
            and chroma < PERCEPT_PINK_CHROMA_MAX):
        return 'pink'
    return base


def _neutral_zone_mix(comp: list[dict]) -> bool:
    """近中性分区是否存在可感知的冷暖双向成分

    暖侧与冷侧的 chroma 权重占比均超 PERCEPT_ZONE_MIX_MIN_PCT 时，
    说明"整体近中性"掩盖了内部冷暖抵消结构（如蓝灰地面 + 暖棕阴影）。
    近中性分区可见彩度像素稀少，用权重口径（少数着色像素的色相分布）
    而非面积口径衡量方向对立。
    """
    warm = sum(c['weight_pct'] for c in comp if c['name'] in PERCEPT_WARM_NAMES)
    cool = sum(c['weight_pct'] for c in comp if c['name'] in PERCEPT_COOL_NAMES)
    return warm >= PERCEPT_ZONE_MIX_MIN_PCT and cool >= PERCEPT_ZONE_MIX_MIN_PCT


# ==================== sRGB → OKLab ====================

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


def _srgb_to_linear(srgb: np.ndarray) -> np.ndarray:
    """sRGB 传递函数解码到线性 RGB（分段 gamma）

    这一步不可省略：直接对 gamma 值做矩阵运算是最常见的 OKLab 实现错误。
    """
    a = 0.055
    return np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + a) / (1 + a)) ** 2.4,
    )


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

    linear = _srgb_to_linear(x)
    lms = linear @ _M1.T
    lms_cbrt = np.cbrt(lms)
    lab = lms_cbrt @ _M2.T
    return lab


def oklab_to_lch(lab: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """OKLab 转 L / C / h（h 单位为度，范围 0~360）"""
    L = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]
    C = np.sqrt(a * a + b * b)
    h = np.degrees(np.arctan2(b, a)) % 360.0
    return L, C, h


def oklab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """OKLab 转 sRGB（0~255 uint8），用于主色卡还原"""
    return (_oklab_to_srgb_float(lab) * 255.0).astype(np.uint8)


def _oklab_to_srgb_float(lab: np.ndarray) -> np.ndarray:
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


def oklab_to_hsb_hue(lab: np.ndarray) -> np.ndarray:
    """OKLab 转 HSB 色相角（度，0~360），主项目色相标准的坐标轴

    统计权重仍用 OKLCH chroma，仅色相角度/色名按 HSB 轴展示，
    与主项目色环及拾色器读数一致。
    """
    return _srgb_hsb_hue(_oklab_to_srgb_float(lab))


def _srgb_hsb_hue(srgb: np.ndarray) -> np.ndarray:
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


# ==================== 环形统计工具 ====================

def circular_stats(h_deg: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    """加权环形平均色相与合矢量长度 R

    Returns:
        (平均色相角[度], R)。总权重为 0 时返回 (nan, 0.0)。
    """
    total = float(weights.sum())
    if total <= 0:
        return math.nan, 0.0
    rad = np.radians(h_deg)
    x = float(np.sum(weights * np.cos(rad)))
    y = float(np.sum(weights * np.sin(rad)))
    R = math.hypot(x, y) / total
    mean_hue = math.degrees(math.atan2(y, x)) % 360.0
    return mean_hue, R


def circular_diff(a: float, b: float) -> float:
    """两色相角的环形最小夹角（0~180 度）"""
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


# ==================== 各模块 ====================

def _cast_evidence(a: np.ndarray, b: np.ndarray, C: np.ndarray, L: np.ndarray) -> dict:
    """双证据统计量（供 analyze_cast 判定与标定脚本复用）

    证据一：近中性候选像素 a/b 均值（经典白平衡参照）；
    证据二：亮部参照带（L 秩分位带∩低彩，Cheng JOSA A 2014 亮暗投影
    思想的简化版），高光多为受光中性面，不依赖证据一的候选阈值，
    覆盖白纸 L>0.9 被排除、伪中性候选报反的场景；亮带空（如极端
    高调图全剪切）时回退暗部参照带。
    等效圆统计（Gasparini）：参照集均值距 D 与散布半径 σ 之比高 →
    参照整体平移（干净的偏移签名），低 → 参照本身杂散（不可信）。
    """
    # 证据一：近中性候选
    p30 = float(np.percentile(C, 30))
    chroma_cap = min(p30, CAST_CHROMA_CAP)
    mask = (C < chroma_cap) & (L > CAST_L_LOW) & (L < CAST_L_HIGH)
    candidate_pct = float(mask.mean() * 100.0)
    ev1_ok = candidate_pct >= CAST_CANDIDATE_MIN_PCT

    def _stats(sel: np.ndarray) -> tuple[tuple[float, float], float]:
        va, vb = float(a[sel].mean()), float(b[sel].mean())
        sigma = math.hypot(float(a[sel].std()), float(b[sel].std()))
        d = math.hypot(va, vb)
        return (va, vb), (d / sigma if sigma > 1e-9 else math.inf)

    v1, conc1 = _stats(mask) if ev1_ok else ((0.0, 0.0), 0.0)

    # 证据二：亮部参照带，排除剪切白（a/b 被剪切压缩）与高彩内容
    q_lo, q_hi = np.quantile(L, CAST_REF_BRIGHT_Q)
    band = (L >= q_lo) & (L <= min(q_hi, CAST_REF_CLIP_L)) & (C < CAST_REF_CHROMA_CAP)
    ref_dark = False
    if band.sum() < CAST_REF_MIN_PX:
        d_lo, d_hi = np.quantile(L, CAST_REF_DARK_Q)
        band = (L >= max(d_lo, CAST_REF_BLACK_L)) & (L <= d_hi) & (C < CAST_REF_CHROMA_CAP)
        ref_dark = True
    ev2_ok = int(band.sum()) >= CAST_REF_MIN_PX
    v2, conc2 = _stats(band) if ev2_ok else ((0.0, 0.0), 0.0)

    return {
        'v1': v1, 'ev1_ok': ev1_ok, 'candidate_pct': candidate_pct, 'conc1': conc1,
        'v2': v2, 'ev2_ok': ev2_ok, 'conc2': conc2, 'ref_dark': ref_dark,
    }


def _vec_angle(u: tuple[float, float], v: tuple[float, float]) -> float:
    """两矢量夹角（度）0~180"""
    du = math.degrees(math.atan2(u[1], u[0]))
    dv = math.degrees(math.atan2(v[1], v[0]))
    return circular_diff(du, dv)


def _in_sky_hue(v: tuple[float, float]) -> bool:
    """矢量方向是否落在天空蓝色相区（蓝天/雪地与冷偏移统计同构）"""
    ang = math.degrees(math.atan2(v[1], v[0])) % 360.0
    return CAST_SKY_HUE[0] <= ang <= CAST_SKY_HUE[1]


def analyze_cast(a: np.ndarray, b: np.ndarray, C: np.ndarray, L: np.ndarray) -> dict:
    """色偏检测：双证据 + 三态语义

    三态：中性 / 白平衡偏差 / 风格化倾向。两者按证据结构区分：方向来自
    参照带对证据一的否决/救援（中性参照体系被破坏，白平衡错误的结构性
    签名）判白平衡偏差；双证据一致的整体色彩倾向（调色/固有色与 WB
    错误在统计上不可分，把判断留给摄影师）判风格化倾向。另保留双证据
    均不可用时的"不可判"态（kind='unknown'）。两证据方向一致为高置信，
    矛盾或仅单证据可用时降为低置信（UI 按 confidence<1 追加低置信后缀）。
    """
    ev = _cast_evidence(a, b, C, L)
    v1, v2 = ev['v1'], ev['v2']
    s1, s2 = math.hypot(*v1), math.hypot(*v2)

    # 证据二能否独立定方向：带有效且幅度达下限；暗带回退额外要求高度
    # 集中；天空蓝区方向仅在证据一在场时被封禁（蓝天/雪地不得否决
    # 中性候选的结论；证据一缺席时带是唯一线索，低置信报出）
    sky_block = ev['ev1_ok'] and _in_sky_hue(v2)
    decisive2 = (ev['ev2_ok'] and s2 >= CAST_REF_WEAK and not sky_block
                 and (not ev['ref_dark'] or ev['conc2'] >= CAST_OVERRIDE_CONC))

    verdict = None                     # (矢量, 强度, 明显档阈值, 是否参照带救援)
    if ev['ev1_ok']:
        if s1 >= CAST_WEAK:
            agree = (ev['ev2_ok'] and s2 >= CAST_REF_WEAK
                     and _vec_angle(v1, v2) <= CAST_AGREE_MAX_DEG)
            if agree:
                verdict, confidence = (v1, s1, CAST_STRONG, False), 1.0
            elif (decisive2 and ev['conc2'] >= CAST_OVERRIDE_CONC
                  and ev['conc2'] > ev['conc1']):
                # 证据二否决证据一（伪中性候选陷阱：候选被有色场景带偏）
                verdict, confidence = (v2, s2, CAST_REF_STRONG, True), 0.5
            else:
                verdict, confidence = (v1, s1, CAST_STRONG, False), 0.5
        elif decisive2 and ev['conc2'] >= CAST_OVERRIDE_CONC:
            # 候选报中性但参照带整体高度集中地偏移（候选漏抓真实偏色）
            verdict, confidence = (v2, s2, CAST_REF_STRONG, True), 0.5
        else:
            verdict, confidence = 'neutral', 1.0
    else:
        if decisive2:
            verdict, confidence = (v2, s2, CAST_REF_STRONG, True), 0.5
        elif ev['ev2_ok'] and not ev['ref_dark'] and s2 < CAST_REF_WEAK:
            verdict, confidence = 'neutral', 0.5
        else:
            verdict, confidence = 'unknown', 0.0

    if verdict == 'unknown':
        kind, strength, vector = 'unknown', 0.0, (0.0, 0.0)
        label_key, label_args = 'cast_unknown', {}
    elif verdict == 'neutral':
        kind, strength, vector = 'neutral', s1 if ev['ev1_ok'] else s2, v1 if ev['ev1_ok'] else v2
        label_key, label_args = 'cast_neutral', {}
    else:
        vector, strength, strong_thr, rescued = verdict
        level = 'weak' if strength < strong_thr else 'strong'
        direction = _cast_direction(*vector)
        # 三态区分（证据结构）：参照带救援/否决路径 = 白平衡错误签名；
        # 但去除偏移后仍极高彩的场景（如深蓝单色调）参照带多为场景
        # 内容，回归风格化；双证据一致的整体倾向一律报风格化倾向
        if rescued:
            resid = np.hypot(a - vector[0], b - vector[1])
            rescued = float(np.percentile(resid, 50)) < CAST_WB_RESID_MAX
        kind = 'wb_error' if rescued else 'styled'
        label_key = 'cast_wb_error' if rescued else 'cast_styled'
        label_args = {'level': level, 'direction': direction}

    return {
        'vector': vector,
        'vector2': v2,
        'strength': strength,
        'kind': kind,
        'confidence': confidence,
        'label_key': label_key,
        'label_args': label_args,
        'candidate_pct': ev['candidate_pct'],
    }


def _cast_direction(a: float, b: float) -> tuple[str, ...]:
    """由 a/b 符号组合出方向 id 元组（UI 逐个翻译后拼接）

    b>0 暖黄 / b<0 冷蓝 / a>0 品红 / a<0 绿
    """
    parts: list[str] = []
    if b > 0:
        parts.append('warm_yellow' if b >= abs(a) else 'yellow')
    elif b < 0:
        parts.append('cool_blue' if abs(b) >= abs(a) else 'blue')
    if a > 0:
        parts.append('magenta')
    elif a < 0:
        parts.append('green')
    if not parts:
        return ('neutral',)
    return tuple(parts[:2])


def _smoothstep(x: np.ndarray, edge0: float, edge1: float) -> np.ndarray:
    """标准 smoothstep：edge0 以下为 0，edge1 以上为 1，中间三次平滑过渡"""
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def analyze_zones(L: np.ndarray, C: np.ndarray, h_ok: np.ndarray,
                  hsb_h: np.ndarray) -> dict:
    """分区调色分析（split toning）

    每像素对暗/中/亮的隶属度用 smoothstep 过渡带（中心 L=0.35/0.7，
    半宽 ZONE_TRANSITION，三区隶属度和恒为 1），隶属度×chroma 双重加权；
    环形统计在 OKLCH 色相轴上做（感知均匀），展示角度/色名换算 HSB；
    构成统计直接在 HSB 轴上按 12 色名区域切分。
    """
    total = L.shape[0]
    w_bright = _smoothstep(L, ZONE_BRIGHT_MIN - ZONE_TRANSITION,
                           ZONE_BRIGHT_MIN + ZONE_TRANSITION)
    w_dark = 1.0 - _smoothstep(L, ZONE_DARK_MAX - ZONE_TRANSITION,
                               ZONE_DARK_MAX + ZONE_TRANSITION)
    memberships = {
        'dark': w_dark,
        'mid': 1.0 - w_dark - w_bright,
        'bright': w_bright,
    }

    zones: dict = {}
    for key, w_zone in memberships.items():
        pixel_pct = float(w_zone.sum()) / total * 100.0 if total else 0.0
        sel = w_zone > ZONE_MEMBER_MIN
        if not sel.any():
            zones[key] = _empty_zone(key, pixel_pct)
            continue

        wz = w_zone[sel]
        zc = C[sel]
        weight = wz * zc                       # 隶属度 × chroma 双重加权
        mean_hue_ok, R = circular_stats(h_ok[sel], weight)
        # 展示色相：分区像素的 HSB 加权环形均值（与拾色器读数一致）
        mean_hue_hsb, _ = circular_stats(hsb_h[sel], weight)
        zone_chroma = float(weight.sum() / wz.sum())

        zones[key] = _zone_result(key, mean_hue_ok, mean_hue_hsb, R, zone_chroma, pixel_pct)
        # 分区内部色彩构成（HSB 轴按色名区域统计，含 8.6 感知色名）
        if zone_chroma >= ZONE_NEUTRAL_CHROMA:
            zones[key]['composition'] = analyze_hue_composition(zc, hsb_h[sel], wz, L[sel])
        elif zones[key]['label_key'] == 'zone_neutral':
            # 8.6 补充：近中性分区若内部冷暖双向抵消，标记混合（UI 追加后缀词条）
            comp = analyze_hue_composition(zc, hsb_h[sel], wz, L[sel])
            if _neutral_zone_mix(comp):
                zones[key]['composition'] = comp
                zones[key]['mix'] = True
            else:
                zones[key]['composition'] = []
        else:
            zones[key]['composition'] = []

    zones['style'] = _toning_style(zones)
    return zones


def _empty_zone(key: str, pixel_pct: float) -> dict:
    """隶属度全为 0 的空分区（如无暗部像素的高调图）"""
    return {
        'hue': None, 'hue_ok': None, 'hue_name': None, 'R': 0.0, 'chroma': 0.0,
        'pixel_pct': pixel_pct, 'label_key': 'zone_no_pixels',
        'label_args': {'zone': key}, 'mix': False, 'composition': [],
    }


def _zone_result(key: str, hue_ok: float, hue_hsb: float, R: float,
                 chroma: float, pixel_pct: float) -> dict:
    """单分区结论判定（hue_ok 为 OKLCH 角供风格判定，hue_hsb 为展示角）"""
    hsb = hue_hsb if not math.isnan(hue_hsb) else None
    if pixel_pct < ZONE_MIN_PCT:
        valid = chroma >= ZONE_NEUTRAL_CHROMA and R >= ZONE_MIN_R and hsb is not None
        return {
            'hue': hsb if valid else None, 'hue_ok': hue_ok if valid else None,
            'hue_name': hue_name(hsb) if valid else None,
            'R': R, 'chroma': chroma, 'pixel_pct': pixel_pct,
            'label_key': 'zone_scarce', 'label_args': {'zone': key}, 'mix': False,
        }

    if chroma < ZONE_NEUTRAL_CHROMA:
        return {
            'hue': None, 'hue_ok': None, 'hue_name': None, 'R': R, 'chroma': chroma,
            'pixel_pct': pixel_pct,
            'label_key': 'zone_neutral', 'label_args': {'zone': key}, 'mix': False,
        }
    if R < ZONE_MIN_R:
        return {
            'hue': None, 'hue_ok': None, 'hue_name': None, 'R': R, 'chroma': chroma,
            'pixel_pct': pixel_pct,
            'label_key': 'zone_scattered', 'label_args': {'zone': key}, 'mix': False,
        }
    cn = hue_name(hsb)
    return {
        'hue': hsb, 'hue_ok': hue_ok, 'hue_name': cn, 'R': R, 'chroma': chroma,
        'pixel_pct': pixel_pct,
        'label_key': 'zone_tinted', 'label_args': {'zone': key, 'hue': cn}, 'mix': False,
    }


def _toning_style(zones: dict) -> dict | None:
    """暗部与亮部风格命名，返回 {'label_key', 'label_args'} 或 None"""
    dark = zones['dark']
    bright = zones['bright']
    if dark['hue'] is None or bright['hue'] is None:
        return None

    diff = circular_diff(dark['hue_ok'], bright['hue_ok'])
    dn = dark['hue_name']
    bn = bright['hue_name']

    if diff < STYLE_ANALOG_MAX:
        return {'label_key': 'style_unified', 'label_args': {'hue': dn}}
    if diff >= STYLE_OPPOSITE_MIN:
        # HSB 12 色名下的经典风格：暗部青/蓝系 + 亮部橙/黄系
        if dn in ('cyan', 'cyan_blue', 'blue') and bn in ('orange_red', 'red'):
            return {'label_key': 'style_teal_orange', 'label_args': {}}
        if dn in ('blue', 'cyan_blue') and bn in ('yellow', 'yellow_green'):
            return {'label_key': 'style_blue_gold', 'label_args': {}}
        return {'label_key': 'style_contrast', 'label_args': {'dark': dn, 'bright': bn}}
    return None


def analyze_hue_peaks(C: np.ndarray, h: np.ndarray, hsb_h: np.ndarray) -> list[dict]:
    """色相峰检测：加权直方图 + 环形平滑 + 找峰

    找峰与和谐判定在 OKLCH 轴（感知均匀）；对外展示的角度/色名取
    归属像素的 HSB 加权环形均值（与主项目色环及拾色器一致）。
    高度 >= 最高峰 20% 的为主峰（参与和谐判定）；5%~20% 之间且权重占比
    >= 3% 的为次峰（minor=True，仅展示色彩构成）。
    """
    bin_width = 360.0 / HUE_BINS
    idx = np.clip((h / bin_width).astype(int), 0, HUE_BINS - 1)
    hist = np.bincount(idx, weights=C, minlength=HUE_BINS).astype(np.float64)

    smoothed = _circular_gaussian_smooth(hist, HUE_SMOOTH_SIGMA / bin_width)
    total_weight = float(smoothed.sum())
    if total_weight <= 0:
        return []

    peaks = _find_circular_peaks(smoothed)
    if not peaks:
        return []

    max_height = max(smoothed[i] for i in peaks)
    peaks = [i for i in peaks if smoothed[i] >= max_height * HUE_PEAK_MINOR_RATIO]
    peaks = _merge_close_peaks(peaks, smoothed, bin_width)

    pixel = (C, hsb_h, idx)
    results = _peak_results(smoothed, peaks, bin_width, max_height, total_weight, pixel)
    # 权重占比不足的次峰丢弃后重新归属，保证各峰占比合计 100%
    kept = [r for r in results
            if not r['minor'] or r['weight_pct'] >= HUE_PEAK_MINOR_MIN_PCT]
    if len(kept) < len(results):
        results = _peak_results(smoothed, [r['_bin'] for r in kept],
                                bin_width, max_height, total_weight, pixel)

    for r in results:
        del r['_bin']
    results.sort(key=lambda r: r['weight_pct'], reverse=True)
    return results[:HUE_PEAK_MAX]


def _peak_results(smoothed: np.ndarray, peaks: list[int], bin_width: float,
                  max_height: float, total_weight: float,
                  pixel: tuple[np.ndarray, np.ndarray, np.ndarray]) -> list[dict]:
    """按 bin 归属最近峰计算各峰权重占比，展示角/区间取归属像素的 HSB 统计"""
    C, hsb_h, idx = pixel
    n = len(smoothed)
    peak_hues = np.array([i * bin_width + bin_width / 2 for i in peaks])
    bin_centers = np.arange(n) * bin_width + bin_width / 2
    assign = np.array([
        int(np.argmin([circular_diff(bc, ph) for ph in peak_hues]))
        for bc in bin_centers
    ])

    results: list[dict] = []
    for pi, bin_i in enumerate(peaks):
        weight = float(smoothed[assign == pi].sum())
        hue_ok = float(bin_i * bin_width + bin_width / 2)

        pmask = assign[idx] == pi
        w = C[pmask]
        hh = hsb_h[pmask]
        if w.sum() > 0:
            disp_hue, _ = circular_stats(hh, w)
            # 环形展开到均值±180° 后取加权 P10~P90 作为展示区间
            rel = (hh - disp_hue + 180.0) % 360.0 - 180.0
            q10, q90 = _weighted_quantile(rel, w, (0.10, 0.90))
            rng = ((disp_hue + q10) % 360.0, disp_hue + q90)
        else:
            disp_hue = hue_ok
            rng = (hue_ok, hue_ok)

        results.append({
            'hue': disp_hue,                 # 对外展示：HSB 角
            'hue_ok': hue_ok,                # 内部：OKLCH 角（和谐判定用）
            'name': hue_name(disp_hue),
            'weight_pct': weight / total_weight * 100.0,
            'range': rng,
            'minor': bool(smoothed[bin_i] < max_height * HUE_PEAK_MIN_RATIO),
            '_bin': bin_i,
        })
    return results


def _circular_gaussian_smooth(hist: np.ndarray, sigma_bins: float) -> np.ndarray:
    """首尾相接的环形高斯平滑"""
    radius = max(1, int(math.ceil(sigma_bins * 3)))
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-(offsets ** 2) / (2 * sigma_bins ** 2))
    kernel /= kernel.sum()

    out = np.zeros_like(hist)
    for k, off in zip(kernel, offsets):
        out += k * np.roll(hist, off)
    return out


def _find_circular_peaks(arr: np.ndarray) -> list[int]:
    """环形局部极大值下标"""
    n = len(arr)
    peaks = []
    for i in range(n):
        left = arr[(i - 1) % n]
        right = arr[(i + 1) % n]
        if arr[i] > left and arr[i] >= right and arr[i] > 0:
            peaks.append(i)
    return peaks


def _merge_close_peaks(peaks: list[int], arr: np.ndarray, bin_width: float) -> list[int]:
    """相距小于 HUE_PEAK_MERGE_DIST 的峰合并，保留更高的"""
    if not peaks:
        return []
    peaks = sorted(peaks, key=lambda i: arr[i], reverse=True)
    kept: list[int] = []
    for p in peaks:
        ph = p * bin_width + bin_width / 2
        if all(circular_diff(ph, k * bin_width + bin_width / 2) >= HUE_PEAK_MERGE_DIST
               for k in kept):
            kept.append(p)
    return kept


def analyze_hue_composition(C: np.ndarray, h: np.ndarray,
                            area_w: np.ndarray | None = None,
                            L: np.ndarray | None = None) -> list[dict]:
    """色名构成：按 HSB 12 色名区域统计，不依赖找峰

    双口径：chroma 权重占比回答"什么颜色主导色彩感"，可见彩度面积占比
    回答"什么颜色占多少画面"——低饱和但成片的成分（如蓝天里的灰云）
    按面积口径也能列入。

    Args:
        area_w: 分区隶属度权重，None 时按全像素等权；
            权重口径按 area_w*C 加权，面积口径按 area_w 软计数。
        L: 逐像素 OKLab 明度（感知色名用），None 时段代表明度回退中值。

    Returns:
        [{'name', 'pname', 'hue', 'weight_pct', 'area_pct', 'range'}, ...]，
        权重 >= COMP_MIN_PCT 或可见面积 >= COMP_MIN_AREA_PCT 的条目
        按权重降序，最多 COMP_MAX 个。name 为 12 段色名 id，pname 为感知色名 id。
    """
    if area_w is None:
        area_w = np.ones_like(C)
    weight = C * area_w
    total = float(weight.sum())
    area_total = float(area_w.sum())
    if total <= 0 or area_total <= 0:
        return []

    visible = C >= COMP_VISIBLE_CHROMA
    results: list[dict] = []
    for seg in range(12):
        lo = (seg * 30.0 - 15.0) % 360.0     # 色名居中：red 345°~15°、orange_red 15°~45° ...
        rel = (h - lo) % 360.0               # 环形平移，跨 0° 区域也能线性处理
        mask = rel < 30.0
        w = weight[mask]
        pct = float(w.sum()) / total * 100.0
        area_pct = float(area_w[mask & visible].sum()) / area_total * 100.0
        if pct < COMP_MIN_PCT and area_pct < COMP_MIN_AREA_PCT:
            continue
        hues = lo + rel[mask]                # 可能超 360，报告时取模
        mean_hue = float(np.average(hues, weights=w))
        q10, q90 = _weighted_quantile(hues, w, (0.10, 0.90))
        # 8.6 感知色名：段代表 L/C（面积权重均值）+ 段均色相
        seg_area = area_w[mask]
        seg_area_sum = float(seg_area.sum())
        rep_c = float(np.average(C[mask], weights=seg_area)) if seg_area_sum > 0 else 0.0
        rep_l = (float(np.average(L[mask], weights=seg_area))
                 if L is not None and seg_area_sum > 0 else 0.6)
        results.append({
            'name': _HUE_NAMES[seg],
            'pname': perceptual_color_name(rep_l, rep_c, mean_hue % 360.0),
            'hue': mean_hue % 360.0,
            'weight_pct': pct,
            'area_pct': area_pct,
            'range': (q10 % 360.0 if q10 >= 360.0 else q10, q90),
        })

    results.sort(key=lambda r: r['weight_pct'], reverse=True)
    return results[:COMP_MAX]


def _weighted_quantile(values: np.ndarray, weights: np.ndarray,
                       qs: tuple[float, ...]) -> tuple[float, ...]:
    """加权分位数（调用方已将区域内色相平移为连续值，线性即可）"""
    order = np.argsort(values)
    v = values[order]
    cum = np.cumsum(weights[order])
    cum = cum / cum[-1]
    return tuple(float(np.interp(q, cum, v)) for q in qs)


# ==================== 配色结构：Matsuda 模板拟合 ====================

# 模板定义（Cohen-Or et al. 2006 扇区宽度）：((扇区中心, 扇区宽度), ...)，
# rotation=0 时首扇区中心在 0°，拟合时整体旋转
_HARMONY_TEMPLATES = {
    'i': ((0.0, 18.0),),
    'V': ((0.0, 93.6),),
    'L': ((0.0, 18.0), (90.0, 79.2)),
    'I': ((0.0, 18.0), (180.0, 18.0)),
    'T': ((0.0, 180.0),),
    'Y': ((0.0, 93.6), (180.0, 18.0)),
    'X': ((0.0, 93.6), (180.0, 93.6)),
}

# 模板 → 配色结构 label key（自由配色为 harmony_free）
_HARMONY_LABELS = {
    'i': 'harmony_monochromatic',
    'V': 'harmony_monochromatic',
    'L': 'harmony_complementary',
    'I': 'harmony_complementary',
    'T': 'harmony_analogous',
    'Y': 'harmony_split_complementary',
    'X': 'harmony_double_complementary',
    'N': 'harmony_achromatic',
}

# 模板优先序：先单扇区（连续分布的最简描述，i/V 窄→宽），
# 再多扇区与半环大扇区按总宽窄→宽（I 36°、L 97.2°、Y 111.6°、T 180°、X 187.2°），
# 对抗"宽模板必然误差更小"的选型偏置
_HARMONY_ORDER = ('i', 'V', 'I', 'L', 'Y', 'T', 'X')


def _template_dist_matrix(sectors: tuple[tuple[float, float], ...]) -> np.ndarray:
    """模板的 (旋转, bin) 误差矩阵：bin 中心到最近扇区边缘的环形弧距（度）

    行 k 对应模板旋转 k*bin_width 度；扇区内距离为 0。
    """
    bin_width = 360.0 / HUE_BINS
    centers = np.arange(HUE_BINS) * bin_width + bin_width / 2
    dist0 = np.full(HUE_BINS, 360.0)
    for c, w in sectors:
        d = np.abs((centers - c + 180.0) % 360.0 - 180.0)
        dist0 = np.minimum(dist0, np.maximum(0.0, d - w / 2))
    # 旋转 k 个 bin 后 dist[b] = dist0[(b - k) % n]，一次索引生成全部旋转
    idx = (np.arange(HUE_BINS)[None, :] - np.arange(HUE_BINS)[:, None]) % HUE_BINS
    return dist0[idx]


def _sector_mass_matrices(sectors: tuple[tuple[float, float], ...]) -> list[np.ndarray]:
    """每个扇区的 (旋转, bin) 指示矩阵，与 hist 相乘得各旋转下该扇区质量"""
    bin_width = 360.0 / HUE_BINS
    centers = np.arange(HUE_BINS) * bin_width + bin_width / 2
    idx = (np.arange(HUE_BINS)[None, :] - np.arange(HUE_BINS)[:, None]) % HUE_BINS
    mats = []
    for c, w in sectors:
        d = np.abs((centers - c + 180.0) % 360.0 - 180.0)
        inside = (d <= w / 2).astype(np.float64)
        mats.append(inside[idx])
    return mats


_HARMONY_DIST = {name: _template_dist_matrix(sectors)
                 for name, sectors in _HARMONY_TEMPLATES.items()}
_HARMONY_MASS = {name: _sector_mass_matrices(sectors)
                 for name, sectors in _HARMONY_TEMPLATES.items()
                 if len(sectors) > 1}
# 各模板达标线：按扇区总宽折减，覆盖越宽要求拟合越严
_HARMONY_GOOD_LINE = {
    name: HARMONY_FIT_GOOD * (1.0 - sum(w for _, w in sectors) / 360.0)
    for name, sectors in _HARMONY_TEMPLATES.items()
}


def analyze_harmony_fit(C: np.ndarray, h: np.ndarray,
                        mean_chroma: float) -> tuple[str, dict]:
    """配色结构判定：Matsuda 模板旋转拟合，OKLCH 色相轴

    对 chroma 加权色相直方图逐模板求最优旋转角与归一化误差 E
    （加权平均弧距，单位度）；双扇区模板只在扇区质量满足均衡约束的
    旋转角中取最优（防近空扇区白嫖单色分布）；按 _HARMONY_ORDER 优先序
    取第一个 E 不超自身达标线（按覆盖宽度折减）的模板；无一达标则判
    自由配色 harmony_free（template 报全局最小误差模板，供参考）。

    Returns:
        (label_key, {'template', 'rotation', 'error', 'confidence'})
    """
    if mean_chroma < ACHROMATIC_EPS:
        return _HARMONY_LABELS['N'], {
            'template': 'N', 'rotation': 0.0, 'error': 0.0, 'confidence': 1.0,
        }

    bin_width = 360.0 / HUE_BINS
    idx = np.clip((h / bin_width).astype(int), 0, HUE_BINS - 1)
    hist = np.bincount(idx, weights=C, minlength=HUE_BINS).astype(np.float64)
    hist /= hist.sum()

    fits: dict[str, tuple[float, float]] = {}
    for name in _HARMONY_ORDER:
        errors = _HARMONY_DIST[name] @ hist
        if name in _HARMONY_MASS:
            masses = np.stack([m @ hist for m in _HARMONY_MASS[name]])
            # 均衡约束：各扇区都须持有实质质量（排除空扇区白嫖）
            balanced = ((masses.min(axis=0) >= HARMONY_SECTOR_BALANCE * masses.max(axis=0))
                        & (masses.min(axis=0) > 0))
            if not balanced.any():
                continue
            errors = np.where(balanced, errors, np.inf)
        k = int(np.argmin(errors))
        fits[name] = (float(errors[k]), k * bin_width)

    best = next((n for n in _HARMONY_ORDER
                 if n in fits and fits[n][0] <= _HARMONY_GOOD_LINE[n]), None)
    adequate = best is not None
    if best is None:
        best = min(fits, key=lambda n: fits[n][0])
    error, rotation = fits[best]
    confidence = max(0.0, min(1.0, 1.0 - error / HARMONY_FIT_MAX))
    label_key = _HARMONY_LABELS[best] if adequate else 'harmony_free'
    return label_key, {
        'template': best, 'rotation': rotation,
        'error': error, 'confidence': confidence,
    }


def analyze_warmth(C: np.ndarray, h: np.ndarray) -> dict:
    """冷暖倾向：色相投影到冷暖轴，chroma 加权"""
    total = float(C.sum())
    if total <= 0:
        return {'value': 0.0, 'label_key': 'warmth_neutral'}
    rad = np.radians(h - WARM_HUE)
    value = float(np.sum(C * np.cos(rad)) / total)

    if value >= WARMTH_STRONG:
        label_key = 'warmth_strong_warm'
    elif value >= WARMTH_WEAK:
        label_key = 'warmth_warm'
    elif value <= -WARMTH_STRONG:
        label_key = 'warmth_strong_cool'
    elif value <= -WARMTH_WEAK:
        label_key = 'warmth_cool'
    else:
        label_key = 'warmth_neutral'
    return {'value': value, 'label_key': label_key}


def analyze_chroma_dist(C: np.ndarray) -> dict:
    """彩度分布：P25/P50/P75 + 分档"""
    p25 = float(np.percentile(C, 25))
    p50 = float(np.percentile(C, 50))
    p75 = float(np.percentile(C, 75))

    if p50 < CHROMA_LOW_MAX:
        label_key = 'chroma_low'
    elif p50 >= CHROMA_HIGH_MIN:
        label_key = 'chroma_high'
    else:
        label_key = 'chroma_medium'
    return {'p25': p25, 'p50': p50, 'p75': p75, 'label_key': label_key}


def analyze_colorfulness(srgb255: np.ndarray) -> dict:
    """彩色度（Hasler & Süsstrunk 2003）：M = σ_rgyb + 0.3·μ_rgyb

    rg = R-G、yb = (R+G)/2 - B（0~255 尺度），七档分类沿用论文
    心理物理实验阈值，与 chroma P50 分档并列互验。
    """
    rg = srgb255[..., 0] - srgb255[..., 1]
    yb = 0.5 * (srgb255[..., 0] + srgb255[..., 1]) - srgb255[..., 2]
    sigma = math.hypot(float(rg.std()), float(yb.std()))
    mu = math.hypot(float(rg.mean()), float(yb.mean()))
    m = sigma + 0.3 * mu
    idx = int(np.searchsorted(np.array(COLORFULNESS_BOUNDS), m, side='right'))
    return {'colorfulness': m, 'colorfulness_key': COLORFULNESS_KEYS[idx]}


def analyze_palette(lab: np.ndarray, k: int = PALETTE_K) -> list:
    """主色卡提取：bin 加速加权 k-means，确定性无随机

    Chang et al. 2015 思路：L 降权特征空间按固定网格 bin 统计 →
    最密 bin + 距离抑制取初始中心 → 对 bin 质心加权 k-means →
    合并 ΔE_OK 过近的中心，输出自适应个数的主色。

    Returns:
        [((r, g, b), pct, pname), ...]，按占比降序（pname 为 8.6 感知色名 id）。
    """
    n = lab.shape[0]
    if n == 0 or k <= 0:
        return []

    feat = lab.copy()
    feat[:, 0] *= PALETTE_L_SCALE

    # 网格 bin 统计：坐标量化编码为一维 key，bincount 得质心与权重
    grid = np.floor(feat / PALETTE_BIN_STEP).astype(np.int64)
    grid -= grid.min(axis=0)
    dims = grid.max(axis=0) + 1
    key = (grid[:, 0] * dims[1] + grid[:, 1]) * dims[2] + grid[:, 2]
    _, inv = np.unique(key, return_inverse=True)
    w = np.bincount(inv).astype(np.float64)
    pts = np.stack([np.bincount(inv, weights=feat[:, i]) for i in range(3)],
                   axis=1) / w[:, None]

    centers = _bin_init(pts, w, min(k, len(pts)))
    labels = _weighted_kmeans(pts, w, centers)
    cw = np.bincount(labels, weights=w, minlength=len(centers))

    # 聚类在降权空间，合并与输出前把 L 还原
    restored = centers.copy()
    restored[:, 0] /= PALETTE_L_SCALE
    merged = _merge_centers(restored, cw)

    total = sum(mw for _, mw in merged)
    result = []
    for center, mw in merged:
        r, g, b = (int(v) for v in oklab_to_srgb(center))
        cl, cc, _ = oklab_to_lch(center)
        h_hsb = float(oklab_to_hsb_hue(center.reshape(1, 3))[0])
        pname = perceptual_color_name(float(cl), float(cc), h_hsb)
        result.append(((r, g, b), float(mw / total * 100.0), pname))
    result.sort(key=lambda x: x[1], reverse=True)
    return result


def _bin_init(pts: np.ndarray, w: np.ndarray, k: int) -> np.ndarray:
    """最密 bin + 距离抑制初始化（Chang 2015），确定性

    每轮取当前最重 bin 为新中心，抑制其 PALETTE_INIT_MIN_DIST 邻域；
    可选 bin 耗尽时提前结束（初始中心数自适应减少）。
    """
    centers = []
    avail = w.copy()
    while len(centers) < k:
        i = int(np.argmax(avail))
        if avail[i] <= 0:
            break
        centers.append(pts[i])
        d = np.linalg.norm(pts - pts[i], axis=1)
        avail[d < PALETTE_INIT_MIN_DIST] = 0.0
    return np.array(centers)


def _weighted_kmeans(pts: np.ndarray, w: np.ndarray, centers: np.ndarray,
                     max_iter: int = 30) -> np.ndarray:
    """对 bin 质心的加权 k-means（原地更新 centers），返回归属标签"""
    labels = np.argmin(
        np.linalg.norm(pts[:, None, :] - centers[None, :, :], axis=2), axis=1)
    for _ in range(max_iter):
        for c in range(len(centers)):
            m = labels == c
            if w[m].sum() > 0:
                centers[c] = np.average(pts[m], axis=0, weights=w[m])
        new_labels = np.argmin(
            np.linalg.norm(pts[:, None, :] - centers[None, :, :], axis=2), axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
    return labels


def _merge_centers(centers: np.ndarray, weights: np.ndarray) -> list[tuple[np.ndarray, float]]:
    """合并 ΔE_OK < PALETTE_MERGE_DE 的中心（权重加权），按权重降序处理"""
    order = np.argsort(weights)[::-1]
    merged: list[list] = []          # [center, weight]
    for i in order:
        if weights[i] <= 0:
            continue
        for entry in merged:
            if float(np.linalg.norm(entry[0] - centers[i])) < PALETTE_MERGE_DE:
                total = entry[1] + weights[i]
                entry[0] = (entry[0] * entry[1] + centers[i] * weights[i]) / total
                entry[1] = total
                break
        else:
            merged.append([centers[i].copy(), float(weights[i])])
    return [(c, mw) for c, mw in merged]


# ==================== 主入口 ====================

def analyze_lab(lab: np.ndarray) -> dict:
    """分析 OKLab 像素数组，返回结果字典（另附 wheel 可视化字段）

    统计权重用 OKLCH chroma；对外报告的色相角度/色名 id 用 HSB 轴
    （主项目色相标准）；冷暖投影仍用 OKLCH 色相（感知均匀）。
    """
    L, C, h = oklab_to_lch(lab)
    # sRGB 只还原一次，HSB 色相轴与彩色度 M 共用（往返误差可忽略）
    srgb = _oklab_to_srgb_float(lab)
    hsb_h = _srgb_hsb_hue(srgb)
    a = lab[:, 1]
    b = lab[:, 2]
    mean_chroma = float(C.mean())

    # 全局灰调边界分支：整图彩度趋近 0 时视为黑白/灰调，
    # 色相无意义，色相峰与冷暖统一置空/中性，保证所有色相输出为空
    achromatic = mean_chroma < ACHROMATIC_EPS
    if achromatic:
        peaks: list[dict] = []
        warmth = {'value': 0.0, 'label_key': 'warmth_neutral'}
    else:
        peaks = analyze_hue_peaks(C, h, hsb_h)
        warmth = analyze_warmth(C, h)

    harmony_key, harmony_fit = analyze_harmony_fit(C, h, mean_chroma)

    chroma_dist = analyze_chroma_dist(C)
    chroma_dist.update(analyze_colorfulness(srgb * 255.0))

    # 色轮密度图：角度 = HSB 色相，半径 = OKLCH chroma（复用上方中间量，免重复计算）
    wheel, _, _ = np.histogram2d(
        hsb_h, np.clip(C, 0.0, WHEEL_CHROMA_MAX),
        bins=[WHEEL_HUE_BINS, WHEEL_CHROMA_BINS],
        range=[[0.0, 360.0], [0.0, WHEEL_CHROMA_MAX]],
    )

    return {
        'cast': analyze_cast(a, b, C, L),
        'zones': analyze_zones(L, C, h, hsb_h),
        'hue_peaks': peaks,
        'harmony': harmony_key,
        'harmony_fit': harmony_fit,
        'palette': analyze_palette(lab),
        'warmth': warmth,
        'chroma_dist': chroma_dist,
        'wheel': wheel,
    }


def analyze_color_distribution(img_array: np.ndarray) -> dict:
    """分析一张图片的色彩分布（core 公开 API）

    Args:
        img_array: RGB uint8 数组 (H, W, 3)，已由图片加载层完成 ICC→sRGB 归一

    Returns:
        结果字典，另附可视化字段：
        wheel（72 角度 × 24 半径的 chroma 直方图，色轮密度图用）、
        image_size（原始宽高 (w, h)）。整个 dict 可直接进缓存，命中零计算。
    """
    h0, w0 = img_array.shape[:2]
    if max(h0, w0) > MAX_DIM:
        # 长边降采样到 MAX_DIM（BILINEAR），统计结果几乎无差别
        scale = MAX_DIM / max(h0, w0)
        new_size = (max(1, round(w0 * scale)), max(1, round(h0 * scale)))
        img = Image.fromarray(img_array, mode='RGB').resize(
            new_size, Image.Resampling.BILINEAR)
        img_array = np.asarray(img, dtype=np.uint8)

    result = analyze_lab(srgb_to_oklab(img_array.reshape(-1, 3)))
    result['image_size'] = (w0, h0)
    return result


# ==================== 结果缓存 ====================

class ColorDistributionCache(BaseCache):
    """色彩分布分析缓存管理器

    使用LRU策略管理分析结果缓存，避免重复计算同一张图片的色彩分布。

    缓存键格式: (image_fingerprint,)
    """

    def __init__(self, max_size: int = 20):
        """初始化色彩分布分析缓存

        Args:
            max_size: 最大缓存条目数，默认20
        """
        super().__init__(max_size)

    def get(self, image_key: str) -> dict | None:
        """获取缓存的分析结果

        Args:
            image_key: 图片指纹键

        Returns:
            dict | None: 缓存的分析结果，未命中返回None
        """
        key = self._get_key(image_key)
        return self._get_from_cache(key)

    def set(self, image_key: str, result: dict) -> None:
        """存储分析结果到缓存

        Args:
            image_key: 图片指纹键
            result: 分析结果
        """
        key = self._get_key(image_key)
        self._set_to_cache(key, result)

    def _get_key(self, image_key: str) -> tuple:
        """生成缓存键

        Args:
            image_key: 图片指纹键

        Returns:
            tuple: 缓存键元组
        """
        return (image_key,)


# 全局缓存实例
_color_distribution_cache: ColorDistributionCache | None = None


def get_color_distribution_cache() -> ColorDistributionCache:
    """获取全局色彩分布分析缓存实例

    Returns:
        ColorDistributionCache: 全局缓存实例
    """
    global _color_distribution_cache
    if _color_distribution_cache is None:
        _color_distribution_cache = ColorDistributionCache()
    return _color_distribution_cache


def clear_color_distribution_cache() -> None:
    """清空全局色彩分布分析缓存"""
    global _color_distribution_cache
    if _color_distribution_cache is not None:
        _color_distribution_cache.clear()
