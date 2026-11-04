"""悬浮配色磁贴基础渲染测试

覆盖：
- 颜色 dict 按 hex / rgb 渲染，残缺 dict 按 hex 兜底
- 名称与 HEX 搜索匹配
- 常用 / 全部过滤、三类空状态
- 单击色块复制 HEX
- 折叠状态跨重建保留
- 六个语言包补齐磁贴文案键
"""

import os
import sys
import tomllib
from typing import Any

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from PySide6.QtWidgets import QApplication

from tests.favorites_fixture import build_favorites
from ui.palette_tile import (
    ROUTE_ALL,
    ROUTE_COMMON,
    FloatingPaletteTile,
    extract_swatch_data,
    matches_query,
)
from utils import tr

LOCALES_DIR = os.path.join(project_root, 'locales')
PALETTE_TILE_KEYS = {
    'empty_title',
    'empty_hint',
    'pinned_empty_title',
    'pinned_empty_hint',
    'no_match',
    'copied',
}


def _favorite(
    favorite_id: str,
    name: str,
    colors: list[dict],
    pinned: bool | None = None,
) -> dict:
    """构造一条收藏数据"""
    favorite: dict[str, Any] = {
        'id': favorite_id,
        'name': name,
        'colors': colors,
        'created_at': '2026-01-01T09:00:00',
        'source': 'test',
    }
    if pinned is not None:
        favorite['pinned'] = pinned
    return favorite


@pytest.fixture
def tile(qapp):
    """未显示的磁贴，不读取真实配置"""
    widget = FloatingPaletteTile()
    yield widget
    widget.deleteLater()


def test_extract_swatch_data_prefers_rgb_for_painting():
    favorite = _favorite(
        'a',
        '配色',
        [
            {'hex': '#FF0000', 'rgb': (255, 0, 0)},
            {'hex': '#00FF00', 'rgb': [0, 255, 0]},
        ],
    )

    data = extract_swatch_data(favorite)

    assert [hex_value for hex_value, _ in data] == ['#FF0000', '#00FF00']
    assert data[0][1].name() == '#ff0000'
    assert data[1][1].name() == '#00ff00'


def test_extract_swatch_data_residual_dict_falls_back_to_hex():
    favorite = _favorite(
        'a',
        '配色',
        [
            {'hex': '#123456'},
            {'rgb': (1, 2, 3)},
            {'hex': 'not-a-color'},
        ],
    )

    data = extract_swatch_data(favorite)

    assert len(data) == 1
    assert data[0][0] == '#123456'
    assert data[0][1].name() == '#123456'


def test_matches_query_by_name_and_hex():
    search_keys = ('春日原野', ('#a8bfa3',))

    assert matches_query(search_keys, '')
    assert matches_query(search_keys, '春日')
    assert matches_query(search_keys, 'a8bfa3')
    assert not matches_query(search_keys, 'ff0000')


def test_apply_favorites_builds_groups_and_swatches(tile):
    favorites = build_favorites(3)

    tile._apply_favorites(favorites)

    assert len(tile._group_widgets) == 3
    expected = sum(len(extract_swatch_data(favorite)) for favorite in favorites)
    actual = sum(len(group.swatches) for group in tile._group_widgets)
    assert actual == expected


def test_group_titles_use_palette_management_index(tile):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}]),
        _favorite('b', '配色二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}]),
        {'id': 'c', 'colors': [{'hex': '#0000FF', 'rgb': (0, 0, 255)}]},
    ]

    tile._apply_favorites(favorites)

    unnamed = tr('palette_management.unnamed')
    assert tile._group_widgets[0]._header._name_label.text() == '1.配色一'
    assert tile._group_widgets[1]._header._name_label.text() == '2.配色二'
    assert tile._group_widgets[2]._header._name_label.text() == f'3.{unnamed}'


def test_common_tab_keeps_global_index(tile):
    favorites = [
        _favorite('a', '第一组', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}]),
        _favorite('b', '常用组', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
        _favorite('c', '第三组', [{'hex': '#0000FF', 'rgb': (0, 0, 255)}]),
    ]

    tile._apply_favorites(favorites)

    visible = [group for group in tile._group_widgets if not group.isHidden()]
    assert [group._header._name_label.text() for group in visible] == ['2.常用组']


def test_common_tab_shows_only_pinned_groups(tile):
    favorites = [
        _favorite('a', '常用一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '常用二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
        _favorite('c', '未常用', [{'hex': '#0000FF', 'rgb': (0, 0, 255)}], pinned=False),
    ]

    tile._apply_favorites(favorites)

    visible = [group for group in tile._group_widgets if not group.isHidden()]
    assert [group.favorite_id for group in visible] == ['a', 'b']
    assert tile._route == ROUTE_COMMON

    tile._segmented.setCurrentItem(ROUTE_ALL)
    tile._on_route_changed(ROUTE_ALL)

    assert all(not group.isHidden() for group in tile._group_widgets)


def test_search_without_result_shows_no_match_state(tile):
    favorites = [
        _favorite('a', '春日原野', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True)
    ]

    tile._apply_favorites(favorites)
    tile._on_search_changed('不存在的名称')

    assert all(group.isHidden() for group in tile._group_widgets)
    assert not tile._empty_widget.isHidden()
    assert tile._empty_widget._icon_label.text() == '🔍'


def test_common_tab_without_pinned_shows_pinned_empty_state(tile):
    favorites = [
        _favorite('a', '未常用', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=False)
    ]

    tile._apply_favorites(favorites)

    assert not tile._empty_widget.isHidden()
    assert tile._empty_widget._icon_label.text() == '📌'


def test_without_favorites_shows_empty_state(tile):
    tile._apply_favorites([])

    assert not tile._empty_widget.isHidden()
    assert tile._empty_widget._icon_label.text() == '⭐'


def test_copy_hex_writes_clipboard_and_shows_feedback(tile):
    favorites = [
        _favorite('a', '配色', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True)
    ]
    tile._apply_favorites(favorites)
    swatch = tile._group_widgets[0].swatches[0]

    tile._copy_hex(swatch)

    assert QApplication.clipboard().text() == '#FF0000'
    assert swatch._hex_label.text() == tr('palette_tile.copied')


def test_collapsed_state_survives_rebuild(tile):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True)
    ]

    tile._apply_favorites(favorites)
    tile._group_widgets[0]._toggle()
    assert tile._collapsed_ids == {'a'}
    assert tile._group_widgets[0].expanded is False

    tile._apply_favorites(favorites)

    assert tile._group_widgets[0].expanded is False


def test_locale_palette_tile_keys_complete():
    for filename in sorted(os.listdir(LOCALES_DIR)):
        if not filename.endswith('.toml'):
            continue
        with open(os.path.join(LOCALES_DIR, filename), 'rb') as file:
            translations = tomllib.load(file)
        missing = PALETTE_TILE_KEYS - set(translations['palette_tile'])
        assert not missing, f'{filename} 缺少键: {missing}'
