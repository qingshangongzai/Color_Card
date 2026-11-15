"""主色条视图模型测试：色相角与色块同源、中性色占位、取整回绕

不构造完整对话框：_palette_view 是静态方法，只依赖主色数据与已翻译文案。
色相角期望值由色块 RGB 独立复算得出（HSB 轴），不从代码内部反推。
"""

import pytest

import ui.color_distribution_charts  # noqa: F401  先加载 ui 子模块，绕开 ui/dialogs 包初始化互引
from dialogs.color_distribution_dialog import ColorDistributionDialog
from utils import get_locale_manager, tr


@pytest.fixture(autouse=True)
def _load_locale():
    """加载简体中文词条，测试结束后恢复原语言，避免污染其他测试"""
    manager = get_locale_manager()
    previous = manager.get_current_language()
    manager.load_language('HY_JT')
    yield
    manager.load_language(previous)


def _color() -> dict:
    """主色条目用的结构化色名（只给色名模板实际读取的四个字段）"""
    return {
        'family_id': 'gray', 'secondary_family_id': None, 'tone_id': 'none',
        'hue_modifier_id': None,
    }


def _palette(rgb: tuple[int, int, int]) -> list[dict]:
    """单条主色卡数据（占比 100%，本用例只关心色块与色相角）"""
    return [{'rgb': rgb, 'weight_pct': 100.0, 'color_name': _color()}]


def _hue_text(rgb: tuple[int, int, int]) -> str:
    return ColorDistributionDialog._palette_view(_palette(rgb))[0]['hue_text']


@pytest.mark.parametrize('rgb, expected', [
    ((225, 231, 233), '195°'),
    ((133, 180, 197), '196°'),
    ((80, 146, 175), '198°'),
])
def test_hue_text_matches_swatch_rgb(rgb, expected):
    """色相角取该条色块自身的 RGB，与着色用的整数完全一致"""
    assert _hue_text(rgb) == expected


@pytest.mark.parametrize('rgb', [(0, 0, 0), (128, 128, 128), (255, 255, 255)])
def test_neutral_swatch_has_no_hue(rgb):
    """三通道相等的中性色没有色相，显示占位符而不是 0°"""
    assert _hue_text(rgb) == tr('color_distribution.hue_none')
    assert _hue_text(rgb) != '0°'


def test_hue_text_wraps_360_to_0():
    """色相 359.8° 取整到 360° 时回绕显示 0°，不出现 360°"""
    assert _hue_text((255, 0, 1)) == '0°'
