"""收藏数据层测试：变更信号、pinned 字段与 set() 拦截

覆盖：
- ConfigManager 是 QObject 且提供 favorites_changed
- 7 个收藏写方法 emit，3 个排除方法不 emit
- pinned 为可选字段，旧配置缺省时按 False 读取，无需迁移
- set('favorites.0.pinned', …) 被拦截（拦截前会抛 TypeError）
"""

import json
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from PySide6.QtCore import QObject

from core.config import ConfigManager


def _favorite(favorite_id: str, name: str = "配色") -> dict:
    """构造一条最小收藏数据"""
    return {
        "id": favorite_id,
        "name": name,
        "colors": [{"hex": "#FF0000", "rgb": (255, 0, 0)}],
        "created_at": "2026-01-01T09:00:00",
        "source": "color_analysis",
    }


@pytest.fixture
def manager(qapp):
    """独立的配置管理器，只读写内存"""
    return ConfigManager()


@pytest.fixture
def emissions(manager):
    """favorites_changed 的发射计数"""
    counter = []
    manager.favorites_changed.connect(lambda: counter.append(1))
    return counter


def test_manager_is_qobject_with_favorites_changed(manager):
    assert isinstance(manager, QObject)
    assert hasattr(manager, "favorites_changed")


def test_add_favorite_emits_on_append_and_overwrite(manager, emissions):
    manager.add_favorite(_favorite("a"))
    assert len(emissions) == 1
    manager.add_favorite(_favorite("a", "覆盖"))
    assert len(emissions) == 2


def test_update_methods_emit_only_on_success(manager, emissions):
    manager.add_favorite(_favorite("a"))
    assert len(emissions) == 1

    assert manager.update_favorite_color("a", 0, {"hex": "#00FF00", "rgb": (0, 255, 0)}) is True
    assert len(emissions) == 2

    assert manager.update_favorite_color("a", 5, {"hex": "#0000FF", "rgb": (0, 0, 255)}) is False
    assert len(emissions) == 2

    assert manager.update_favorite("a", {"name": "新名称"}) is True
    assert len(emissions) == 3

    assert manager.update_favorite("missing", {"name": "不存在"}) is False
    assert len(emissions) == 3


def test_delete_and_clear_emit(manager, emissions):
    manager.add_favorite(_favorite("a"))
    assert len(emissions) == 1

    assert manager.delete_favorite("a") is True
    assert len(emissions) == 2

    assert manager.delete_favorite("missing") is False
    assert len(emissions) == 2

    manager.clear_favorites()
    assert len(emissions) == 3


def test_pinned_methods_emit_and_skip_deleted(manager, emissions):
    manager.add_favorite(_favorite("a"))
    manager.add_favorite(_favorite("b"))
    manager.add_favorite(_favorite("c"))
    assert len(emissions) == 3

    assert manager.set_favorite_pinned("a", True) is True
    assert manager.get_favorite("a")["pinned"] is True
    assert len(emissions) == 4

    assert manager.set_favorite_pinned("missing", True) is False
    assert len(emissions) == 4

    assert manager.delete_favorite("b") is True
    assert len(emissions) == 5
    assert manager.set_favorite_pinned("b", True) is False
    assert len(emissions) == 5

    assert manager.set_favorites_pinned({"a", "b", "c"}, True) == 2
    assert len(emissions) == 6
    assert manager.get_favorite("c")["pinned"] is True

    assert manager.set_favorites_pinned({"missing"}, False) == 0
    assert len(emissions) == 6


def test_excluded_methods_do_not_emit(manager, emissions):
    manager.add_favorite(_favorite("a"))
    manager.delete_favorite("a")
    assert len(emissions) == 2

    manager.cleanup_deleted_favorites()
    manager.set_favorites([_favorite("b")])
    manager.set("settings.hex_visible", False)

    assert len(emissions) == 2


def test_set_rejects_favorites_prefix(manager, emissions):
    with pytest.raises(ValueError):
        manager.set("favorites.0.pinned", True)
    with pytest.raises(ValueError):
        manager.set("favorites", [])

    assert manager.get_favorites() == []
    assert len(emissions) == 0


def test_add_favorite_same_id_preserves_workspace_state(manager):
    original = _favorite("a")
    original["pinned"] = True
    original["_deleted"] = True
    manager.add_favorite(original)

    manager.add_favorite(_favorite("a", "覆盖"))

    stored = manager.get_favorite("a", include_deleted=True)
    assert stored["name"] == "覆盖"
    assert stored["pinned"] is True
    assert stored["_deleted"] is True


def test_legacy_config_without_pinned_reads_false(tmp_path):
    config_file = tmp_path / "config.json"
    legacy = {
        "version": "1.0",
        "favorites": [
            {
                "id": "legacy-1",
                "name": "旧收藏",
                "colors": [{"hex": "#112233", "rgb": [17, 34, 51]}],
                "created_at": "2025-12-01T10:00:00",
                "source": "color_analysis",
            }
        ],
    }
    config_file.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
    original_text = config_file.read_text(encoding="utf-8")

    manager = ConfigManager()
    manager._config_path = config_file
    manager.load()

    favorites = manager.get_favorites()
    assert len(favorites) == 1
    assert "pinned" not in favorites[0]
    assert favorites[0].get("pinned", False) is False
    # 只读加载，不迁移、不回写
    assert config_file.read_text(encoding="utf-8") == original_text
