"""收藏数据构造夹具

为收藏列表的性能基准（50 / 100 / 200 组）提供可复跑的数据，运行期不写盘。

字段与真实收藏一致（id / name / colors / created_at / source）：

- `pinned` 三态：True / False / 缺省（缺省模拟旧配置，读取方按 False 兜底）
- 残缺颜色 dict 样本：只含 `hex` / `rgb` 两项（模拟导入失败分支写入的数据）
- `rgb` 两种形态：tuple（界面创建收藏时的内存形态）与 list（config.json 加载后的形态）

颜色键与真实收藏一致，取自 `core.color.get_color_info()`。
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from core.color import get_color_info, rgb_to_hex

DEFAULT_SEED = 20261104

_NAME_PREFIXES = (
    "品牌主色",
    "界面配色",
    "插画配色",
    "渐变配色",
    "海报配色",
    "深色主题",
    "浅色主题",
    "网页配色",
    "图表配色",
    "封面配色",
)

_SOURCES = (
    "color_analysis",
    "color_generation",
    "palette_tuning",
    "preset_color",
    "gradient_generation",
    "import",
)

# 残缺 dict 样本的来源：导入失败分支只写 hex / rgb
_RESIDUAL_COLOR_KEYS = ("hex", "rgb")


def build_favorites(count: int, seed: int = DEFAULT_SEED) -> list[dict[str, Any]]:
    """构造指定组数的收藏数据

    Args:
        count: 收藏组数（基准使用 50 / 100 / 200）
        seed: 随机种子，固定种子保证结果可复跑

    Returns:
        list[dict[str, Any]]: 收藏列表，每项含 id / name / colors / created_at / source
    """
    rng = random.Random(seed)
    favorites: list[dict[str, Any]] = []
    base_time = datetime(2026, 1, 1, 9, 0, 0)

    for index in range(count):
        color_count = rng.randint(2, 5)
        colors: list[dict[str, Any]] = []
        for color_index in range(color_count):
            r, g, b = rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)
            if index % 10 == 0 and color_index == 0:
                residual = {"hex": rgb_to_hex(r, g, b), "rgb": (r, g, b)}
                colors.append({key: residual[key] for key in _RESIDUAL_COLOR_KEYS})
            else:
                colors.append(get_color_info(r, g, b))

        name = f"{_NAME_PREFIXES[index % len(_NAME_PREFIXES)]} {index + 1:03d}"
        if index % 20 == 19:
            name += "（含辅助色与状态色完整方案）"

        favorite: dict[str, Any] = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"color-card-favorites/{seed}/{index}")),
            "name": name,
            "colors": colors,
            "created_at": (base_time + timedelta(minutes=index)).isoformat(),
            "source": rng.choice(_SOURCES),
        }

        # 每 10 组留 1 组 rgb 为 list：模拟 config.json 加载后的内存形态（JSON 反序列化结果）
        if index % 10 == 5:
            for color in favorite["colors"]:
                color["rgb"] = list(color["rgb"])

        # pinned 三态：0 → True，1 → False，2/3 → 缺省（旧配置兼容）
        if index % 4 in (0, 1):
            favorite["pinned"] = index % 4 == 0

        favorites.append(favorite)

    return favorites
