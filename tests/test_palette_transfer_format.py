"""收藏导出 / 导入格式测试：交换格式不随 pinned 变动

覆盖：
- 导出 JSON 只含 name + colors
- 导入生成新 uuid，且不迁移 pinned
"""

import json
import os
import sys
import uuid

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.palette_service import PaletteExporter, PaletteImporter
from tests.favorites_fixture import build_favorites


def test_export_writes_name_and_hex_only(tmp_path, qapp):
    favorites = build_favorites(3)
    export_file = tmp_path / "export.json"

    exporter = PaletteExporter(favorites, str(export_file))
    exporter.run()

    data = json.loads(export_file.read_text(encoding="utf-8"))
    assert len(data["palettes"]) == 3
    for palette in data["palettes"]:
        assert set(palette) == {"name", "colors"}
        assert all(isinstance(color, str) and color.startswith("#") for color in palette["colors"])


def test_import_generates_new_uuid_and_drops_pinned(tmp_path, qapp):
    import_file = tmp_path / "import.json"
    import_file.write_text(
        json.dumps(
            {
                "palettes": [
                    {
                        "id": "source-id",
                        "name": "外部配色",
                        "colors": ["#FF0000", "#00FF00"],
                        "pinned": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    imported = []
    importer = PaletteImporter(str(import_file))
    importer.finished.connect(imported.append)
    importer.run()

    assert len(imported) == 1
    favorite = imported[0][0]
    assert favorite["id"] != "source-id"
    uuid.UUID(favorite["id"])
    assert "pinned" not in favorite
    assert [color["hex"] for color in favorite["colors"]] == ["#FF0000", "#00FF00"]
