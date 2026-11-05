"""悬浮配色磁贴测试

覆盖：
- 颜色 dict 按 hex / rgb 渲染，残缺 dict 按 hex 兜底
- 名称与 HEX 搜索匹配
- 常用 / 全部过滤、三类空状态、全部 tab 行视图
- 单击色块复制 HEX；行视图点击不触发复制
- 折叠与行展开状态跨重建、跨 tab 保留
- 懒创建首屏计数、滚动回收与占位高度
- 按组刷新原语
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
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tests.favorites_fixture import build_favorites
from ui.palette_tile import (
    FORM_COLLAPSED,
    FORM_GRID,
    FORM_ROW,
    FULL_REBUILD_THRESHOLD,
    GROUP_HEADER_HEIGHT,
    GROUP_SPACING,
    REFRESH_DEBOUNCE_MS,
    ROUTE_ALL,
    ROUTE_COMMON,
    ROW_PREVIEW_COUNT,
    FloatingPaletteTile,
    GroupRow,
    PaletteGroup,
    build_group_model,
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


class _StubConfig(QObject):
    """测试用配置桩：显示磁贴时不读取本机收藏，可手动触发变更信号"""

    favorites_changed = Signal()

    def __init__(self, favorites: list[dict] | None = None) -> None:
        super().__init__()
        self.favorites: list[dict] = favorites or []

    def get_favorites(self, include_deleted: bool = False) -> list[dict]:
        return list(self.favorites)


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


def _build(tile: FloatingPaletteTile, index: int):
    """显式建设指定序号的组内容，返回对应 slot"""
    slot = tile._slots[index]
    tile._ensure_built(slot)
    return slot


@pytest.fixture
def config_stub(qapp):
    """可触发变更信号的配置桩"""
    return _StubConfig()


@pytest.fixture
def tile(qapp, monkeypatch, config_stub):
    """已显示、不读取真实配置的磁贴（懒创建需要真实视口高度）"""
    monkeypatch.setattr('ui.palette_tile.get_config_manager', lambda: config_stub)
    widget = FloatingPaletteTile()
    widget.show()
    QApplication.processEvents()
    yield widget
    widget.hide()
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

    assert len(tile._slots) == 3
    expected = sum(len(extract_swatch_data(favorite)) for favorite in favorites)
    actual = 0
    for index in range(len(favorites)):
        actual += len(_build(tile, index).content.swatches)
    assert actual == expected


def test_group_titles_use_palette_management_index(tile):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}]),
        _favorite('b', '配色二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}]),
        {'id': 'c', 'colors': [{'hex': '#0000FF', 'rgb': (0, 0, 255)}]},
    ]

    tile._apply_favorites(favorites)

    unnamed = tr('palette_management.unnamed')
    assert _build(tile, 0).content._header._name_label.text() == '1.配色一'
    assert _build(tile, 1).content._header._name_label.text() == '2.配色二'
    assert _build(tile, 2).content._header._name_label.text() == f'3.{unnamed}'


def test_common_tab_keeps_global_index(tile):
    favorites = [
        _favorite('a', '第一组', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}]),
        _favorite('b', '常用组', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
        _favorite('c', '第三组', [{'hex': '#0000FF', 'rgb': (0, 0, 255)}]),
    ]

    tile._apply_favorites(favorites)

    visible = [slot for slot in tile._slots if not slot.isHidden()]
    assert len(visible) == 1
    tile._ensure_built(visible[0])
    assert visible[0].content._header._name_label.text() == '2.常用组'


def test_common_tab_shows_only_pinned_groups(tile):
    favorites = [
        _favorite('a', '常用一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '常用二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
        _favorite('c', '未常用', [{'hex': '#0000FF', 'rgb': (0, 0, 255)}], pinned=False),
    ]

    tile._apply_favorites(favorites)

    visible = [slot for slot in tile._slots if not slot.isHidden()]
    assert [slot.model.favorite_id for slot in visible] == ['a', 'b']
    assert tile._route == ROUTE_COMMON

    tile._segmented.setCurrentItem(ROUTE_ALL)

    assert all(not slot.isHidden() for slot in tile._slots)


def test_all_tab_uses_row_view(tile):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
    ]

    tile._apply_favorites(favorites)
    tile._segmented.setCurrentItem(ROUTE_ALL)

    slot = _build(tile, 0)
    assert slot.form == FORM_ROW
    assert isinstance(slot.content, GroupRow)

    slot.content.opened.emit('a')

    assert 'a' in tile._row_open_ids
    assert tile._collapsed_ids == set()
    assert slot.form == FORM_GRID
    assert isinstance(slot.content, PaletteGroup)


def test_tab_switch_keeps_collapsed_and_row_open(tile):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '配色二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
    ]

    tile._apply_favorites(favorites)
    tile._segmented.setCurrentItem(ROUTE_ALL)

    slot_a = _build(tile, 0)
    slot_a.content.opened.emit('a')
    slot_b = _build(tile, 1)
    slot_b.content.opened.emit('b')
    slot_b.content._toggle()

    assert tile._row_open_ids == {'a', 'b'}
    assert tile._collapsed_ids == {'b'}
    assert slot_b.form == FORM_ROW

    tile._segmented.setCurrentItem(ROUTE_COMMON)

    slot_b = tile._slots[1]
    assert slot_b.form == FORM_COLLAPSED
    assert _build(tile, 0).form == FORM_GRID

    tile._segmented.setCurrentItem(ROUTE_ALL)

    assert tile._row_open_ids == {'a', 'b'}
    assert tile._collapsed_ids == {'b'}
    assert tile._slots[0].form == FORM_GRID
    assert tile._slots[1].form == FORM_ROW


def test_expanding_row_lays_out_synchronously(tile):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '配色二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
    ]
    tile._apply_favorites(favorites)
    tile._segmented.setCurrentItem(ROUTE_ALL)
    tile._sync_viewport()
    _build(tile, 0).content.opened.emit('a')

    slot = _build(tile, 1)
    slot.content.opened.emit('b')

    assert slot.form == FORM_GRID
    assert slot.content is not None
    assert not slot.content.isHidden()
    assert slot.height() == slot.model.height_for(FORM_GRID)
    assert slot.content.height() == slot.height()
    expected_host_height = sum(item.height() for item in tile._slots) \
        + GROUP_SPACING * (len(tile._slots) - 1)
    assert tile._groups_host.height() == expected_host_height


def test_row_preview_uses_up_to_five_dots(tile):
    colors = [
        {'hex': f'#0000{index:02X}', 'rgb': (0, 0, index)} for index in range(1, 7)
    ]
    many = GroupRow(
        build_group_model(
            _favorite('a', '多色', colors),
            0,
            tile._card_height,
            tile._row_height,
        )
    )
    few = GroupRow(
        build_group_model(
            _favorite('b', '少色', colors[:3]),
            0,
            tile._card_height,
            tile._row_height,
        )
    )

    assert len(many._preview._colors) == ROW_PREVIEW_COUNT
    assert len(few._preview._colors) == 3


def test_header_preview_shows_color_dots_in_common(tile):
    colors = [
        {'hex': f'#0000{index:02X}', 'rgb': (0, 0, index)} for index in range(1, 7)
    ]
    favorites = [_favorite('a', '多色', colors, pinned=True)]

    tile._apply_favorites(favorites)
    slot = _build(tile, 0)

    assert isinstance(slot.content, PaletteGroup)
    assert len(slot.content._header._preview._colors) == ROW_PREVIEW_COUNT

    slot.content._toggle()

    assert slot.content.expanded is False
    assert len(slot.content._header._preview._colors) == ROW_PREVIEW_COUNT


def test_row_click_does_not_copy(tile):
    favorites = [
        _favorite('a', '配色', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
    ]

    tile._apply_favorites(favorites)
    tile._segmented.setCurrentItem(ROUTE_ALL)
    QApplication.clipboard().setText('sentinel')

    slot = _build(tile, 0)
    slot.content.opened.emit('a')

    assert QApplication.clipboard().text() == 'sentinel'


def test_search_without_result_shows_no_match_state(tile):
    favorites = [
        _favorite('a', '春日原野', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True)
    ]

    tile._apply_favorites(favorites)
    tile._apply_search_query('不存在的名称')

    assert all(slot.isHidden() for slot in tile._slots)
    assert not tile._empty_widget.isHidden()
    assert tile._empty_widget._icon_label.text() == '🔍'


def test_search_filters_only_after_enter_or_button(tile):
    """输入过程不过滤；回车（returnPressed）与搜索按钮（searchSignal）触发后才过滤"""
    favorites = [
        _favorite('a', '春日原野', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '冬日暖阳', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
    ]
    tile._apply_favorites(favorites)

    tile._search.textChanged.emit('春日')
    assert tile._query == ''
    assert not tile._slot_by_id['a'].isHidden()
    assert not tile._slot_by_id['b'].isHidden()

    tile._search.searchSignal.emit('春日')
    assert tile._query == '春日'
    assert not tile._slot_by_id['a'].isHidden()
    assert tile._slot_by_id['b'].isHidden()


def test_search_cleared_by_clear_signal_or_empty_text(tile):
    """清空按钮 / 删光文本立即恢复全部，无需再按回车"""
    favorites = [
        _favorite('a', '春日原野', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '冬日暖阳', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
    ]
    tile._apply_favorites(favorites)

    tile._apply_search_query('春日')
    assert tile._slot_by_id['b'].isHidden()

    tile._search.clearSignal.emit()
    assert tile._query == ''
    assert not tile._slot_by_id['b'].isHidden()

    tile._apply_search_query('春日')
    tile._search.textChanged.emit('')
    assert tile._query == ''
    assert not tile._slot_by_id['b'].isHidden()


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
    swatch = _build(tile, 0).content.swatches[0]

    tile._copy_hex(swatch)

    assert QApplication.clipboard().text() == '#FF0000'
    assert swatch._hex_label.text() == tr('palette_tile.copied')


def test_collapsed_state_survives_rebuild(tile):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True)
    ]

    tile._apply_favorites(favorites)
    _build(tile, 0).content._toggle()
    assert tile._collapsed_ids == {'a'}
    assert tile._slots[0].form == FORM_COLLAPSED

    tile._apply_favorites(favorites)

    assert tile._slots[0].form == FORM_COLLAPSED
    assert _build(tile, 0).content.expanded is False


def test_lazy_creation_keeps_widgets_within_viewport(tile):
    tile._apply_favorites(build_favorites(200))

    for route in (ROUTE_COMMON, ROUTE_ALL):
        tile._segmented.setCurrentItem(route)
        tile._sync_viewport()

        spans = tile._slot_spans()
        top = tile._scroll.verticalScrollBar().value()
        bottom = top + tile._scroll.viewport().height()
        visible = [span for span in spans if span[1] > top and span[0] < bottom]
        built = len(tile._group_widgets)

        assert len(tile._slots) == 200
        assert len(visible) <= built <= len(visible) + 2


def test_recycle_outside_window_and_restore(tile):
    tile._apply_favorites(build_favorites(200))
    tile._segmented.setCurrentItem(ROUTE_ALL)
    QApplication.processEvents()
    tile._max_live_groups = 12
    bar = tile._scroll.verticalScrollBar()
    bar.setValue(bar.maximum())
    QApplication.processEvents()

    assert len(tile._group_widgets) <= tile._max_live_groups
    assert tile._slots[0].content is None
    assert bar.value() == bar.maximum()
    maximum = bar.maximum()

    bar.setValue(0)
    QApplication.processEvents()

    assert tile._slots[0].content is not None
    assert bar.value() == 0
    assert bar.maximum() == maximum


def test_scroll_position_survives_sync(tile):
    tile._apply_favorites(build_favorites(200))
    tile._segmented.setCurrentItem(ROUTE_ALL)
    QApplication.processEvents()
    bar = tile._scroll.verticalScrollBar()
    bar.setValue(bar.maximum() // 2)
    value = bar.value()
    maximum = bar.maximum()

    for _ in range(3):
        tile._sync_viewport()

    assert bar.value() == value
    assert bar.maximum() == maximum


def test_model_height_matches_real_widgets(tile, qapp):
    model = build_group_model(
        _favorite('a', '配色', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}]),
        0,
        tile._card_height,
        tile._row_height,
    )
    many_colors = [
        {'hex': f'#0000{index:02X}', 'rgb': (0, 0, index)} for index in range(1, 6)
    ]
    many_model = build_group_model(
        _favorite('b', '多色', many_colors),
        0,
        tile._card_height,
        tile._row_height,
    )

    grid = PaletteGroup(model, expanded=True)
    collapsed = PaletteGroup(model, expanded=False)
    row = GroupRow(model)
    many = PaletteGroup(many_model, expanded=True)
    qapp.processEvents()

    assert grid.sizeHint().height() == model.height_for(FORM_GRID)
    assert collapsed.sizeHint().height() == model.height_for(FORM_COLLAPSED)
    assert row.sizeHint().height() == model.height_for(FORM_ROW)
    assert model.height_for(FORM_COLLAPSED) == GROUP_HEADER_HEIGHT
    # 5 色为两行，覆盖 行间距 与 多行累加
    assert many.sizeHint().height() == many_model.height_for(FORM_GRID)


def test_row_title_elides_within_slot_width(tile):
    name = '这是一个非常非常非常非常非常长的收藏配色名称用于测试省略是否生效'
    tile._apply_favorites([
        _favorite(
            'a',
            name,
            [{'hex': '#FF0000', 'rgb': (255, 0, 0)}, {'hex': '#00FF00', 'rgb': (0, 255, 0)}],
            pinned=True,
        )
    ])
    tile._segmented.setCurrentItem(ROUTE_ALL)

    slot = _build(tile, 0)
    QApplication.processEvents()
    label = slot.content._name_label

    assert label.width() > 0
    assert label.text() != slot.content._full_title
    assert label.fontMetrics().horizontalAdvance(label.text()) <= label.width()


def test_rebuild_group_replaces_only_target(tile):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '配色二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
    ]
    tile._apply_favorites(favorites)
    slot_a = _build(tile, 0)
    slot_b = _build(tile, 1)
    untouched = slot_b.content

    updated = dict(favorites[0], name='新名称')
    assert tile._rebuild_group(updated) is True
    tile._sync_viewport()

    assert tile._favorites[0]['name'] == '新名称'
    assert '新名称' in slot_a.content._header._name_label.text()
    assert slot_b.content is untouched


def test_full_rebuild_without_reset_keeps_scroll(tile):
    favorites = build_favorites(200)
    tile._apply_favorites(favorites)
    tile._segmented.setCurrentItem(ROUTE_ALL)
    QApplication.processEvents()
    bar = tile._scroll.verticalScrollBar()
    bar.setValue(bar.maximum() // 2)
    value = bar.value()

    tile._apply_favorites(favorites, reset_scroll=False)
    QApplication.processEvents()

    assert bar.value() == value

    tile._apply_favorites(favorites, reset_scroll=True)

    assert bar.value() == 0


def test_favorites_changed_debounces_to_single_flush(tile, config_stub, monkeypatch):
    favorites = [
        _favorite('a', '配色', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True)
    ]
    tile._apply_favorites(favorites)
    config_stub.favorites = favorites

    rebuilds: list[str] = []
    original = tile._rebuild_group

    def record(favorite: dict) -> bool:
        rebuilds.append(favorite.get('name', ''))
        return original(favorite)

    monkeypatch.setattr(tile, '_rebuild_group', record)

    for index in range(10):
        config_stub.favorites = [dict(favorites[0], name=f'配色{index}')]
        config_stub.favorites_changed.emit()

    assert tile.isVisible()
    assert tile._refresh_timer.isActive()
    QTest.qWait(REFRESH_DEBOUNCE_MS + 300)
    assert rebuilds == ['配色9']
    assert tile._slot_by_id['a'].model.favorite['name'] == '配色9'


def test_flush_refresh_rebuilds_only_changed_group(tile, config_stub):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '配色二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
    ]
    tile._collapsed_ids.add('b')
    tile._apply_favorites(favorites)
    config_stub.favorites = favorites
    slot_b = _build(tile, 1)
    untouched = slot_b.content
    tile._apply_search_query('配色')
    assert slot_b.content is untouched

    config_stub.favorites = [dict(favorites[0], name='配色一改'), favorites[1]]
    config_stub.favorites_changed.emit()
    QTest.qWait(REFRESH_DEBOUNCE_MS + 300)

    assert '配色一改' in tile._slot_by_id['a'].content._header._name_label.text()
    assert slot_b.content is untouched
    assert tile._query == '配色'
    assert tile._route == ROUTE_COMMON
    assert tile._collapsed_ids == {'b'}


def test_flush_refresh_adds_and_removes_groups(tile, config_stub):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True),
        _favorite('b', '配色二', [{'hex': '#00FF00', 'rgb': (0, 255, 0)}], pinned=True),
        _favorite('c', '配色三', [{'hex': '#0000FF', 'rgb': (0, 0, 255)}], pinned=True),
    ]
    tile._apply_favorites(favorites)
    config_stub.favorites = favorites
    slot_a = _build(tile, 0)
    slot_b = _build(tile, 1)
    content_a = slot_a.content
    content_b = slot_b.content

    config_stub.favorites = [
        favorites[0],
        favorites[1],
        _favorite('d', '配色四', [{'hex': '#123456', 'rgb': (18, 52, 86)}], pinned=True),
    ]
    config_stub.favorites_changed.emit()
    QTest.qWait(REFRESH_DEBOUNCE_MS + 300)

    assert [slot.model.favorite_id for slot in tile._slots] == ['a', 'b', 'd']
    assert _build(tile, 0).content is content_a
    assert _build(tile, 1).content is content_b
    added = _build(tile, 2)
    assert added.model.card_index == 2
    assert '3.配色四' in added.content._header._name_label.text()


def test_hidden_changes_do_not_rebuild_until_show(tile, config_stub):
    favorites = [
        _favorite('a', '配色一', [{'hex': '#FF0000', 'rgb': (255, 0, 0)}], pinned=True)
    ]
    tile._apply_favorites(favorites)
    config_stub.favorites = favorites
    content = _build(tile, 0).content

    tile.hide()
    tile.show()
    QApplication.processEvents()
    assert _build(tile, 0).content is content

    tile.hide()
    config_stub.favorites = [dict(favorites[0], name='隐藏后改名')]
    config_stub.favorites_changed.emit()
    QTest.qWait(REFRESH_DEBOUNCE_MS + 300)
    assert tile._slot_by_id['a'].content is content

    tile.show()
    QApplication.processEvents()
    rebuilt = _build(tile, 0).content
    assert rebuilt is not content
    assert '隐藏后改名' in rebuilt._header._name_label.text()


def test_built_change_threshold_uses_full_rebuild(tile, config_stub, monkeypatch):
    favorites = build_favorites(20)
    tile._apply_favorites(favorites)
    config_stub.favorites = favorites
    for slot in tile._slots[:FULL_REBUILD_THRESHOLD]:
        tile._ensure_built(slot)

    calls: list[bool] = []
    original = tile._apply_favorites

    def record(favorites_data: list[dict], reset_scroll: bool = True) -> None:
        calls.append(reset_scroll)
        original(favorites_data, reset_scroll)

    monkeypatch.setattr(tile, '_apply_favorites', record)

    config_stub.favorites = [dict(favorite, name=favorite['name'] + '改') for favorite in favorites]
    config_stub.favorites_changed.emit()
    QTest.qWait(REFRESH_DEBOUNCE_MS + 300)

    assert calls == [False]


def test_locale_palette_tile_keys_complete():
    for filename in sorted(os.listdir(LOCALES_DIR)):
        if not filename.endswith('.toml'):
            continue
        with open(os.path.join(LOCALES_DIR, filename), 'rb') as file:
            translations = tomllib.load(file)
        missing = PALETTE_TILE_KEYS - set(translations['palette_tile'])
        assert not missing, f'{filename} 缺少键: {missing}'
