"""布局工具函数模块"""


def calculate_grid_columns(color_count: int) -> int:
    """计算网格布局的列数

    根据颜色数量计算最合适的每行列数，遵循以下规则：
    - 能被5整除 → 每行5个
    - 能被6整除 → 每行6个
    - 其他情况 → 根据数量选择最接近的

    Args:
        color_count: 颜色数量

    Returns:
        int: 每行列数（至少为1）
    """
    if color_count <= 0:
        return 1

    # 能被5整除 → 每行5个
    if color_count % 5 == 0:
        return 5

    # 能被6整除 → 每行6个
    if color_count % 6 == 0:
        return 6

    # 其他情况：根据数量选择
    if color_count <= 5:
        return color_count
    elif color_count <= 10:
        return 5
    else:
        return 6
