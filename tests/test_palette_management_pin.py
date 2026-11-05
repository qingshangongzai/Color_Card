"""配色管理卡片钉选入口测试

覆盖：
- 图钉按收藏 pinned 初值显示选中态与提示
- 切换图钉只发 pinned_changed，数据由界面层确认
- set_pinned 回写数据并同步按钮（不回环发信号）
- 长名称按标签宽度省略
"""

import os
import sys
from typing import Any

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from PySide6.QtWidgets import QApplication

from ui.palette_management import PaletteManagementCard


def _favorite(favorite_id: str, name: str, pinned: bool | None = None) -> dict[str, Any]:
    """构造一条最小收藏数据"""
    favorite: dict[str, Any] = {
        'id': favorite_id,
        'name': name,
        'colors': [{'hex': '#FF0000', 'rgb': (255, 0, 0)}],
        'created_at': '2026-01-01T09:00:00',
        'source': 'test',
    }
    if pinned is not None:
        favorite['pinned'] = pinned
    return favorite


@pytest.fixture
def card(qapp):
    """构造一张配色管理卡片并在结束时销毁"""
    cards: list[PaletteManagementCard] = []

    def build(favorite: dict[str, Any]) -> PaletteManagementCard:
        item = PaletteManagementCard(favorite)
        cards.append(item)
        return item

    yield build
    for item in cards:
        item.deleteLater()


def test_pin_button_reflects_favorite_state(card):
    pinned = card(_favorite('a', '配色', pinned=True))
    unpinned = card(_favorite('b', '配色二', pinned=False))

    assert pinned.pin_button.isChecked()
    assert pinned.pin_button.toolTip() == ''
    assert not unpinned.pin_button.isChecked()
    assert unpinned.pin_button.toolTip() == ''


def test_pin_toggle_emits_and_set_pinned_updates_button(card):
    item = card(_favorite('a', '配色', pinned=False))
    received: list[tuple[str, bool]] = []
    item.pinned_changed.connect(lambda favorite_id, pinned: received.append((favorite_id, pinned)))

    item.pin_button.setChecked(True)

    assert received == [('a', True)]
    assert item._favorite_data.get('pinned') is False

    item.set_pinned(True)

    assert item._favorite_data['pinned'] is True
    assert item.pin_button.isChecked()
    assert received == [('a', True)]


def test_long_name_elides_within_label_width(card):
    long_name = '这是一个非常非常非常非常非常长的收藏配色名称用于测试省略是否生效'
    item = card(_favorite('a', long_name, pinned=True))
    item.name_label.setFixedWidth(80)
    QApplication.processEvents()
    item._apply_elided_name()

    text = item.name_label.text()
    assert text != item._full_name
    assert item.name_label.fontMetrics().horizontalAdvance(text) <= 80
