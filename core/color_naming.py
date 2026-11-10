"""色名规则（HSB 十二段技术色名与感知色名）

技术色相名只描述色相轴，不替代感知色名；感知色名由最终 sRGB 三元组计算，
保证名称与显示的色块来自同一个数值输入。
"""

from __future__ import annotations

import numpy as np

from .color_space import oklab_to_lch, srgb255_to_oklab, srgb_hsb_hue

# ==================== 色名映射（主项目 HSB 12 色环标准） ====================

# HSB 色相角每 30° 一段，色名 id 居中（0°=red、30°=orange_red ... 330°=purple_red），
# 与 locales 既有 color_wheel.hue_* 词条一一对应
_HUE_NAMES = ('red', 'orange_red', 'yellow', 'yellow_green', 'green', 'cyan_green',
              'cyan', 'cyan_blue', 'blue', 'purple', 'magenta', 'purple_red')

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


def perceptual_color_name_from_rgb(rgb: tuple[int, int, int]) -> str:
    """感知色名 id：只接受 0~255 的 int 三元组，内部显式除以 255

    主色卡、构成项等展示名称必须由与绘制色块相同的最终 RGB 计算，
    避免浮点中心、平均角或另一构成项带来的名称与色块不同源。
    三通道相等时 HSB 色相无定义（退化为 0°），直接判灰，避免中性灰
    因色相默认值被误判为暖灰。
    """
    if rgb[0] == rgb[1] == rgb[2]:
        return 'gray'
    srgb = np.asarray(rgb, dtype=np.float64) / 255.0
    L, C, _ = oklab_to_lch(srgb255_to_oklab(rgb))
    hue_hsb = float(srgb_hsb_hue(srgb))
    return perceptual_color_name(float(L), float(C), hue_hsb)
