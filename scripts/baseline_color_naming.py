"""基线感知命名规则快照（冻结自 666a081）

仅供离线构建与报告重建复现基线，运行时不得导入。规则原样保留当时的
12 段技术色名与感知色名补丁，因此中性灰会因 HSB 色相默认 0° 落到
warm_gray——这是基线行为，不在本快照中修正。
"""

from __future__ import annotations

_HUE_NAMES = ('red', 'orange_red', 'yellow', 'yellow_green', 'green', 'cyan_green',
              'cyan', 'cyan_blue', 'blue', 'purple', 'magenta', 'purple_red')

PERCEPT_GRAY_CHROMA = 0.03
PERCEPT_BROWN_L_MAX = 0.55
PERCEPT_DEEP_RED_CHROMA_MIN = 0.08
PERCEPT_PINK_L_MIN = 0.70
PERCEPT_PINK_CHROMA_MAX = 0.10
PERCEPT_WARM_NAMES = ('red', 'orange_red', 'yellow', 'magenta', 'purple_red')
PERCEPT_COOL_NAMES = ('cyan', 'cyan_blue', 'blue', 'purple')
PERCEPT_BROWN_NAMES = ('orange_red', 'yellow')
PERCEPT_PINK_NAMES = ('red', 'magenta', 'purple_red')


def hue_name(hue: float) -> str:
    """HSB 色相角（度）转 12 段技术色名 id"""
    return _HUE_NAMES[int(((hue + 15.0) % 360.0) // 30.0)]


def perceptual_color_name(lightness: float, chroma: float, hue_hsb: float) -> str:
    """基线感知色名 id：由 L/C/h 共同决定的展示名"""
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
