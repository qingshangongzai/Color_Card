"""单色明度梯度测试

验证 generate_lightness_shades 的基准色锚定语义：
基准色恰好出现一次、总数恒等于 count、明度单调非递增、
端点包含（HSB/HSL）、固化输出基线（test_doc_baseline）。
"""

# 标准库导入
import random
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 第三方库导入
import pytest

# 项目模块导入
from core.gradient import generate_lightness_shades  # noqa: E402
from core.color import (  # noqa: E402
    hex_to_rgb,
    rgb_to_hex,
    rgb_to_hsb,
    rgb_to_hsl,
    rgb_to_lab,
)

SPACES = ['lab', 'hsb', 'hsl']

# 代表色：覆盖常规色、边界色与高饱和色
REPRESENTATIVE_COLORS = ['#FF5733', '#000000', '#FFFFFF', '#808080', '#0000FF', '#00FF00']

# 固定种子随机色，保证测试可复现
_rng = random.Random(20261031)
RANDOM_COLORS = [
    '#%02X%02X%02X' % (_rng.randint(0, 255), _rng.randint(0, 255), _rng.randint(0, 255))
    for _ in range(4)
]


def _lightness(rgb, space):
    """按空间取明度分量：LAB 取 L，HSB 取 B，HSL 取 L（与算法一致）"""
    if space == 'lab':
        return rgb_to_lab(*rgb)[0]
    if space == 'hsl':
        return rgb_to_hsl(*rgb)[2]
    return rgb_to_hsb(*rgb)[2]


@pytest.mark.parametrize('space', SPACES)
@pytest.mark.parametrize('count', range(3, 13))
@pytest.mark.parametrize('base_hex', REPRESENTATIVE_COLORS + RANDOM_COLORS)
def test_base_color_included(base_hex, count, space):
    """基准色恰好在结果中出现一次，总数恒等于 count"""
    colors = generate_lightness_shades(base_hex, count, space)

    assert len(colors) == count
    assert colors.count(hex_to_rgb(base_hex)) == 1


@pytest.mark.parametrize('space', SPACES)
@pytest.mark.parametrize(
    'base_hex',
    ['#000000', '#FFFFFF', '#FF0000', '#808080', '#010101', '#FEFEFE', '#FF5733'],
)
def test_boundary_colors(base_hex, space):
    """边界色（纯黑/纯白/近似黑/近似白/中灰/高饱和）包含性与数量"""
    for count in (3, 9, 12):
        colors = generate_lightness_shades(base_hex, count, space)

        assert len(colors) == count, f"count={count}"
        assert colors.count(hex_to_rgb(base_hex)) == 1, f"count={count}"


@pytest.mark.parametrize('space', SPACES)
@pytest.mark.parametrize('count', [3, 7, 12])
@pytest.mark.parametrize('base_hex', REPRESENTATIVE_COLORS + RANDOM_COLORS)
def test_monotonic_lightness(base_hex, count, space):
    """明度序列非递增（相邻容差 0.01，兼容浮点与裁剪平台）"""
    colors = generate_lightness_shades(base_hex, count, space)
    lightness_values = [_lightness(c, space) for c in colors]

    for prev, curr in zip(lightness_values, lightness_values[1:]):
        assert curr <= prev + 0.01, f"{base_hex}/{space}: {[round(v, 2) for v in lightness_values]}"


@pytest.mark.parametrize('space', SPACES)
@pytest.mark.parametrize('base_hex', REPRESENTATIVE_COLORS + RANDOM_COLORS)
def test_no_adjacent_duplicates(base_hex, space):
    """count=12 下相邻色阶不相等"""
    colors = generate_lightness_shades(base_hex, 12, space)

    for prev, curr in zip(colors, colors[1:]):
        assert prev != curr, f"{base_hex}/{space}: {[rgb_to_hex(*c) for c in colors]}"


@pytest.mark.parametrize('count', [3, 7, 12])
@pytest.mark.parametrize('base_hex', ['#FF5733', '#808080', '#FFFFFF', '#010101'])
@pytest.mark.parametrize('space', ['hsb', 'hsl'])
def test_endpoint_reached(base_hex, count, space):
    """HSB/HSL 端点包含：亮侧有阶时首阶 ≈ 95，暗侧有阶时末阶 ≈ 10（±1.0）

    LAB 模式端点受色域裁剪影响，不做此断言（预期行为）。
    侧阶数分配公式与算法一致（按剩余空间比例取整）。
    """
    base_rgb = hex_to_rgb(base_hex)
    base_l = _lightness(base_rgb, space)

    up_ratio = max(0.0, min(1.0, (95 - base_l) / 85))
    lighter_n = round(up_ratio * (count - 1))
    darker_n = count - 1 - lighter_n

    colors = generate_lightness_shades(base_hex, count, space)

    if lighter_n > 0:
        assert abs(_lightness(colors[0], space) - 95) <= 1.0, f"{base_hex}/{space}: 亮侧首阶应达上限"
    if darker_n > 0:
        assert abs(_lightness(colors[-1], space) - 10) <= 1.0, f"{base_hex}/{space}: 暗侧末阶应达下限"


# 固化回归基线：generate_lightness_shades('#FF5733', 7, space) 的期望输出
DOC_BASELINE = {
    'lab': ['#FFBB8B', '#FF895E', '#FF5733', '#D63114', '#AE0000', '#870000', '#630000'],
    'hsb': ['#FF5733', '#D94A2B', '#B23D24', '#8C301C', '#662314', '#40160D', '#1A0905'],
    'hsl': ['#FFEAE5', '#FFA18C', '#FF5733', '#F22B00', '#B22000', '#731400', '#330900'],
}


@pytest.mark.parametrize('space', SPACES)
def test_doc_baseline(space):
    """固化三空间输出基线（hex 大写比较）"""
    colors = generate_lightness_shades('#FF5733', 7, space)
    actual = [rgb_to_hex(*c).upper() for c in colors]

    assert actual == DOC_BASELINE[space]
