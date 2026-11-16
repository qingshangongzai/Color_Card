"""分离色调卡片视图模型测试：两端状态词与全称色名的拼接

不构造完整对话框：_split_text 是静态方法，只依赖分区字典与已翻译文案。
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


def _zone(label_key: str, hue_name: str | None = None) -> dict:
    """最小分区字典（分离色调卡只读取 label_key 与 hue_name）"""
    return {'label_key': label_key, 'hue_name': hue_name}


def _text(dark: dict, bright: dict) -> str:
    return ColorDistributionDialog._split_text({'dark': dark, 'bright': bright})


def test_two_tinted_zones_show_long_names():
    """两端都染色：出暗部 → 亮部的全称名对"""
    assert _text(_zone('zone_tinted', 'cyan_blue'),
                 _zone('zone_tinted', 'orange_red')) == '青蓝 → 橙红'


def test_same_hue_both_ends_keeps_pair():
    """两端同段同色：保留名对，不另造「统一」档词"""
    assert _text(_zone('zone_tinted', 'cyan_blue'),
                 _zone('zone_tinted', 'cyan_blue')) == '青蓝 → 青蓝'


def test_tinted_dark_with_neutral_bright():
    """暗部染色 + 亮部接近中性：状态词只替换降级的一端"""
    assert _text(_zone('zone_tinted', 'cyan_blue'),
                 _zone('zone_neutral')) == '青蓝 → 接近中性'


def test_neutral_dark_with_tinted_bright():
    assert _text(_zone('zone_neutral'),
                 _zone('zone_tinted', 'orange_red')) == '接近中性 → 橙红'


def test_both_neutral_shows_single_word():
    """两端同状态（非染色）：只显示一个状态词"""
    assert _text(_zone('zone_neutral'), _zone('zone_neutral')) == '接近中性'


def test_both_scattered_shows_single_word():
    assert _text(_zone('zone_scattered'), _zone('zone_scattered')) == '色相分散'


def test_both_scarce_shows_single_word():
    assert _text(_zone('zone_scarce'), _zone('zone_scarce')) == '内容极少'


def test_both_empty_uses_split_empty():
    """两端都无像素：用独立的整图空分区表述，不显示单个「无像素」"""
    assert _text(_zone('zone_no_pixels'),
                 _zone('zone_no_pixels')) == tr('color_distribution.split_empty')


def test_tinted_dark_with_scattered_bright():
    assert _text(_zone('zone_tinted', 'cyan_blue'),
                 _zone('zone_scattered')) == '青蓝 → 色相分散'
