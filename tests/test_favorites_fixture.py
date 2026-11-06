"""收藏构造夹具测试：50/100/200 组可复跑、字段齐全

覆盖：
- 50/100/200 组可复跑
- 数据与真实收藏字段一致，含 pinned 三态、残缺颜色 dict 与两种 rgb 形态
"""

import os
import sys
import uuid

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

from tests.favorites_fixture import DEFAULT_SEED, build_favorites


@pytest.mark.parametrize("count", [50, 100, 200])
def test_build_counts(count):
    assert len(build_favorites(count)) == count


def test_reproducible_with_same_seed():
    assert build_favorites(50) == build_favorites(50)


def test_different_seed_changes_data():
    first = build_favorites(50, seed=DEFAULT_SEED)
    second = build_favorites(50, seed=DEFAULT_SEED + 1)

    assert [fav["id"] for fav in first] != [fav["id"] for fav in second]
    assert [fav["colors"][0]["hex"] for fav in first] != [fav["colors"][0]["hex"] for fav in second]


@pytest.mark.parametrize("count", [50, 200])
def test_favorite_fields_match_real_data(count):
    favorites = build_favorites(count)
    ids = set()

    for favorite in favorites:
        assert {"id", "name", "colors", "created_at", "source"} <= set(favorite)
        assert set(favorite) <= {"id", "name", "colors", "created_at", "source", "pinned"}
        uuid.UUID(favorite["id"])
        assert len(favorite["colors"]) >= 2

        for color in favorite["colors"]:
            r, g, b = color["rgb"]
            assert color["hex"] == f"#{r:02X}{g:02X}{b:02X}"

        ids.add(favorite["id"])

    assert len(ids) == count


def test_rgb_covers_tuple_and_list_forms():
    favorites = build_favorites(100)
    shapes = {type(color["rgb"]) for favorite in favorites for color in favorite["colors"]}
    assert shapes == {tuple, list}


def test_pinned_states_cover_true_false_and_missing():
    favorites = build_favorites(100)

    assert sum(1 for fav in favorites if fav.get("pinned") is True) == 25
    assert sum(1 for fav in favorites if fav.get("pinned") is False) == 25
    assert sum(1 for fav in favorites if "pinned" not in fav) == 50


def test_residual_color_dicts_present():
    favorites = build_favorites(50)
    residual = [
        color
        for favorite in favorites
        for color in favorite["colors"]
        if set(color) == {"hex", "rgb"}
    ]
    assert len(residual) == 5
