"""峰标题视图模型测试：单/多构成标题语义与纯色块

不构造完整对话框：_peaks_view 是静态方法，只依赖峰数据与已翻译文案。
0.9%/1.1% 用例走 analyze_hue_composition，锁定第二构成段跨过
COMP_MIN_PCT 时标题在“有主导色名称/无名称”之间跳变的既定口径。
"""

import numpy as np
import pytest

import ui.color_distribution_charts  # noqa: F401  先加载 ui 子模块，绕开 ui/dialogs 包初始化互引
from core import color_distribution as e
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


def _peak(composition: list[dict], name: str = 'magenta',
          weight_pct: float = 50.0, minor: bool = False,
          range_: tuple[float, float] = (0.0, 40.0)) -> dict:
    return {
        'name': name, 'weight_pct': weight_pct,
        'range': range_, 'minor': minor, 'composition': composition,
    }


def _item(pname: str, rgb: tuple[int, int, int],
          weight_pct: float = 50.0) -> dict:
    return {
        'pname': pname, 'weight_pct': weight_pct, 'area_pct': weight_pct,
        'range': (0.0, 20.0), 'rgb': rgb,
    }


def test_single_composition_title_uses_item_name_and_rgb():
    """单构成峰：标题名称与色块都取唯一构成项，不用峰技术色名"""
    item = _item('pink', (180, 146, 170))
    peak = _peak([item])
    view = ColorDistributionDialog._peaks_view([peak])['peaks'][0]
    assert view['show_swatch'] is True
    assert view['swatch_rgb'] == item['rgb']
    assert view['title_text'] == tr(
        'color_distribution.peak_title_single', index=1, range='0°~40°',
        weight='50.0%', name=tr('color_distribution.pname_pink'), minor='')
    assert tr(f'color_wheel.hue_{peak["name"]}') not in view['title_text']


def test_multi_composition_title_has_no_name_or_swatch():
    """多构成峰：标题只剩峰序号/区间/权重，不借用子项名称和色块"""
    comp = [_item('pink', (180, 146, 170), 60.0),
            _item('magenta', (172, 140, 169), 40.0)]
    peak = _peak(comp)
    view = ColorDistributionDialog._peaks_view([peak])['peaks'][0]
    assert view['show_swatch'] is False
    assert view['swatch_rgb'] is None
    assert view['title_text'] == tr(
        'color_distribution.peak_title_multi', index=1, range='0°~40°',
        weight='50.0%', minor='')
    assert tr('color_distribution.pname_pink') not in view['title_text']
    assert tr(f'color_wheel.hue_{peak["name"]}') not in view['title_text']


def test_multi_composition_title_keeps_minor_marker():
    """次峰标记仍在峰级标题内，由词条模板给出位置"""
    comp = [_item('pink', (180, 146, 170)), _item('magenta', (172, 140, 169))]
    view = ColorDistributionDialog._peaks_view(
        [_peak(comp, minor=True)])['peaks'][0]
    assert tr('color_distribution.peak_minor') in view['title_text']


def test_empty_composition_has_no_swatch_or_fallback():
    """空构成峰不绘制任何回退色块"""
    view = ColorDistributionDialog._peaks_view([_peak([])])['peaks'][0]
    assert view['show_swatch'] is False
    assert view['swatch_rgb'] is None
    assert view['items'] == []


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
