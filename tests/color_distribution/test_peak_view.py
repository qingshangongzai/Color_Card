"""峰标题视图模型测试：单/多构成标题语义与纯色块

不构造完整对话框：_peaks_view 是静态方法，只依赖峰数据与已翻译文案。
0.9%/1.1% 用例走 analyze_hue_composition，锁定第二构成段跨过
COMP_MIN_PCT 时标题在“有主导色名称/无名称”之间跳变的既定口径。
"""

import numpy as np
import pytest

import ui.color_distribution_charts  # noqa: F401  先加载 ui 子模块，绕开 ui/dialogs 包初始化互引
from core import color_distribution as e
from core.color_naming import classify_color_name
from dialogs.color_distribution_dialog import ColorDistributionDialog
from utils import get_locale_manager, tr

LOCALES = ('EN_US', 'FR_FR', 'HY_FT', 'HY_JT', 'JA_JP', 'RU_RU')


@pytest.fixture(autouse=True)
def _load_locale():
    """加载简体中文词条，测试结束后恢复原语言，避免污染其他测试"""
    manager = get_locale_manager()
    previous = manager.get_current_language()
    manager.load_language('HY_JT')
    yield
    manager.load_language(previous)


def _color(family: str, tone: str = 'none', modifier: str | None = None,
           secondary: str | None = None) -> dict:
    return {
        'family_id': family, 'secondary_family_id': secondary, 'tone_id': tone,
        'hue_modifier_id': modifier, 'confidence': 0.8, 'technical_hue_id': 'red',
    }


def _name(family: str, tone: str = 'none', modifier: str | None = None,
          secondary: str | None = None) -> str:
    """视图层期望的色名文案（与对话框同模板，但参数字面量独立给出）"""
    return ColorDistributionDialog._color_name_text(
        _color(family, tone, modifier, secondary))


def _peak(composition: list[dict], name: str = 'magenta',
          weight_pct: float = 50.0, minor: bool = False,
          range_: tuple[float, float] = (0.0, 40.0)) -> dict:
    return {
        'name': name, 'weight_pct': weight_pct,
        'range': range_, 'minor': minor, 'composition': composition,
    }


def _item(color_name: dict, rgb: tuple[int, int, int],
          weight_pct: float = 50.0) -> dict:
    return {
        'color_name': color_name, 'weight_pct': weight_pct, 'area_pct': weight_pct,
        'range': (0.0, 20.0), 'rgb': rgb,
    }


def test_single_composition_title_uses_item_name_and_rgb():
    """单构成峰：标题名称与色块都取唯一构成项，不用峰技术色名"""
    item = _item(_color('pink'), (180, 146, 170))
    peak = _peak([item])
    view = ColorDistributionDialog._peaks_view([peak])['peaks'][0]
    assert view['show_swatch'] is True
    assert view['swatch_rgb'] == item['rgb']
    assert view['title_text'] == tr(
        'color_distribution.peak_title_single', index=1, range='0°~40°',
        weight='50.0%', name=_name('pink'), minor='')
    assert tr(f'color_wheel.hue_{peak["name"]}') not in view['title_text']


def test_single_peak_title_name_recomputed_from_final_rgb():
    """单构成峰标题名称可由最终 RGB 复算（模型 → 视图同源闭环）"""
    rgb = (180, 146, 170)
    color_name = classify_color_name(rgb)
    view = ColorDistributionDialog._peaks_view(
        [_peak([_item(color_name, rgb)])])['peaks'][0]
    assert view['show_swatch'] is True
    assert view['swatch_rgb'] == rgb
    assert view['title_text'] == tr(
        'color_distribution.peak_title_single', index=1, range='0°~40°',
        weight='50.0%',
        name=ColorDistributionDialog._color_name_text(color_name), minor='')


def test_gray_tone_name_from_model_keeps_lightness():
    """真实模型锚点：暗蓝灰/浅蓝灰保留明暗修饰，不退化为单一“冷灰”"""
    dark = classify_color_name((31, 59, 77))
    light = classify_color_name((183, 201, 226))
    assert dark['family_id'] == 'gray' and dark['tone_id'] == 'dark'
    assert light['family_id'] == 'gray' and light['tone_id'] == 'light'
    assert ColorDistributionDialog._color_name_text(dark) == '暗冷灰'
    assert ColorDistributionDialog._color_name_text(light) == '浅冷灰'


def test_multi_composition_title_has_no_name_or_swatch():
    """多构成峰：标题只剩峰序号/区间/权重，不借用子项名称和色块"""
    comp = [_item(_color('pink'), (180, 146, 170), 60.0),
            _item(_color('purple', 'muted'), (172, 140, 169), 40.0)]
    peak = _peak(comp)
    view = ColorDistributionDialog._peaks_view([peak])['peaks'][0]
    assert view['show_swatch'] is False
    assert view['swatch_rgb'] is None
    assert view['title_text'] == tr(
        'color_distribution.peak_title_multi', index=1, range='0°~40°',
        weight='50.0%', minor='')
    assert _name('pink') not in view['title_text']
    assert tr(f'color_wheel.hue_{peak["name"]}') not in view['title_text']


def test_multi_composition_title_keeps_minor_marker():
    """次峰标记仍在峰级标题内，由词条模板给出位置"""
    comp = [_item(_color('pink'), (180, 146, 170)),
            _item(_color('purple', 'muted'), (172, 140, 169))]
    view = ColorDistributionDialog._peaks_view(
        [_peak(comp, minor=True)])['peaks'][0]
    assert tr('color_distribution.peak_minor') in view['title_text']


def test_empty_composition_has_no_swatch_or_fallback():
    """空构成峰不绘制任何回退色块"""
    view = ColorDistributionDialog._peaks_view([_peak([])])['peaks'][0]
    assert view['show_swatch'] is False
    assert view['swatch_rgb'] is None
    assert view['items'] == []


def test_color_name_text_covers_tone_modifier_and_gray():
    """单名称模板：明暗/细色相修饰与灰族冷暖路径均按词条拼装"""
    assert _name('red', 'deep', 'orange') == '深橙红'
    assert _name('blue', 'vivid') == '鲜蓝'
    assert _name('green', 'muted') == '浊绿'
    assert _name('gray', modifier='blue') == '冷灰'
    assert _name('gray', 'dark', 'blue') == '暗冷灰'
    assert _name('gray', 'light', 'blue') == '浅冷灰'
    assert _name('gray', modifier='red') == '暖灰'
    assert _name('gray', 'dark', 'red') == '暗暖灰'
    assert _name('gray', 'light', 'red') == '浅暖灰'
    assert _name('gray', modifier='green') == '绿灰'
    assert _name('gray', 'dark', 'green') == '暗绿灰'
    assert _name('pink', secondary='magenta') == '粉／品红过渡'


@pytest.mark.parametrize('lang', LOCALES)
def test_color_name_templates_render_in_all_locales(lang):
    """六语言离屏渲染：所有模板均无裸 key、无未替换占位符"""
    manager = get_locale_manager()
    previous = manager.get_current_language()
    manager.load_language(lang)
    try:
        names = [_color('red', 'deep', 'orange'), _color('gray', modifier='blue'),
                 _color('gray', 'dark', 'blue'), _color('gray', 'light', 'red'),
                 _color('pink', secondary='magenta'), _color('white')]
        for color_name in names:
            text = ColorDistributionDialog._color_name_text(color_name)
            assert text and '{' not in text and 'color_name.' not in text
    finally:
        manager.load_language(previous)


def _two_segment_composition(n_second: int) -> list[dict]:
    """两段可见彩度像素，第二段占 n_second/1000（0.9% 或 1.1%）"""
    n_first = 1000 - n_second
    C = np.full(1000, 0.1)
    h = np.concatenate([np.full(n_first, 5.0), np.full(n_second, 35.0)])
    L = np.full(1000, 0.6)
    h_ok = np.full(1000, 29.0)
    return e.analyze_hue_composition(C, h, None, L, h_ok, max_results=None)


def test_peak_title_switches_at_composition_threshold():
    """第二构成段 0.9% 被过滤→单构成标题；1.1% 保留→多构成无名称"""
    low = _two_segment_composition(9)
    high = _two_segment_composition(11)
    assert len(low) == 1
    assert len(high) == 2

    low_view = ColorDistributionDialog._peaks_view([_peak(low)])['peaks'][0]
    high_view = ColorDistributionDialog._peaks_view([_peak(high)])['peaks'][0]
    assert low_view['show_swatch'] is True
    assert low_view['swatch_rgb'] == low[0]['rgb']
    assert high_view['show_swatch'] is False
    assert high_view['swatch_rgb'] is None
