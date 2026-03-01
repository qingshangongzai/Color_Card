"""通用分组逻辑模块

提供配色数据分组的通用逻辑，用于配色管理和内置色彩面板等场景。
"""

from typing import List, Dict, Any


def _get_group_name(start: int, end: int) -> str:
    """获取分组名称（支持多语言）
    
    Args:
        start: 起始索引（从1开始）
        end: 结束索引
        
    Returns:
        str: 本地化的分组名称
    """
    try:
        from utils import tr
        return tr('common.group_range', default='{start}-{end}').format(start=start, end=end)
    except Exception:
        return f"{start}-{end}"


def _get_all_group_name(total: int) -> str:
    """获取"全部"分组名称（支持多语言）
    
    Args:
        total: 总数
        
    Returns:
        str: 本地化的"全部"分组名称
    """
    try:
        from utils import tr
        return tr('common.group_all', default='All ({total})').format(total=total)
    except Exception:
        return f"All ({total})"


GROUPING_THRESHOLDS = {
    "min_for_groups": 20,
    "group_size": 20,
    "batch_threshold": 50,
    "batch_size": 10
}


def generate_groups(total: int) -> List[Dict[str, Any]]:
    """生成分组配置（始终返回至少一个分组）
    
    Args:
        total: 配色总数
        
    Returns:
        list: 分组配置列表，每个分组包含 name 和 indices 字段
    """
    group_size = GROUPING_THRESHOLDS["group_size"]
    min_for_groups = GROUPING_THRESHOLDS["min_for_groups"]
    
    if total < min_for_groups:
        return [{
            "name": _get_all_group_name(total),
            "indices": list(range(total))
        }]

    groups = []
    num_groups = (total + group_size - 1) // group_size

    for i in range(num_groups):
        start = i * group_size
        end = min((i + 1) * group_size, total)

        groups.append({
            "name": _get_group_name(start + 1, end),
            "indices": list(range(start, end))
        })
    
    return groups


def should_use_batch_loading(total: int) -> bool:
    """判断是否应该使用分批加载
    
    Args:
        total: 数据总量
        
    Returns:
        bool: 当数据量超过阈值时返回 True，否则返回 False
    """
    return total >= GROUPING_THRESHOLDS["batch_threshold"]
