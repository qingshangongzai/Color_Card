"""几何工具模块 - 提供矩形计算和重叠检测功能"""

# 标准库导入
from dataclasses import dataclass
from typing import Optional


@dataclass
class Rect:
    """矩形区域数据类"""
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        """计算矩形面积"""
        return self.width * self.height

    @property
    def left(self) -> float:
        """左边界"""
        return self.x

    @property
    def right(self) -> float:
        """右边界"""
        return self.x + self.width

    @property
    def top(self) -> float:
        """上边界"""
        return self.y

    @property
    def bottom(self) -> float:
        """下边界"""
        return self.y + self.height

    def contains(self, other: 'Rect') -> bool:
        """判断是否完全包含另一个矩形

        Args:
            other: 另一个矩形

        Returns:
            bool: 是否完全包含
        """
        return (self.left <= other.left and
                self.top <= other.top and
                self.right >= other.right and
                self.bottom >= other.bottom)

    def intersects(self, other: 'Rect') -> bool:
        """判断是否与另一个矩形相交

        Args:
            other: 另一个矩形

        Returns:
            bool: 是否相交
        """
        return (self.left < other.right and
                self.right > other.left and
                self.top < other.bottom and
                self.bottom > other.top)


def calculate_overlap_area(rect1: Rect, rect2: Rect) -> float:
    """计算两个矩形的重叠面积

    Args:
        rect1: 第一个矩形
        rect2: 第二个矩形

    Returns:
        float: 重叠面积，不相交时返回0
    """
    x1 = max(rect1.left, rect2.left)
    y1 = max(rect1.top, rect2.top)
    x2 = min(rect1.right, rect2.right)
    y2 = min(rect1.bottom, rect2.bottom)

    if x2 <= x1 or y2 <= y1:
        return 0.0

    return (x2 - x1) * (y2 - y1)


def is_rect_fully_covered(inner_rect: Rect, outer_rect: Rect,
                          threshold: float = 0.9) -> bool:
    """判断一个矩形是否被另一个矩形完全覆盖

    Args:
        inner_rect: 内部矩形（被检测的矩形）
        outer_rect: 外部矩形（可能覆盖内部矩形的矩形）
        threshold: 覆盖比例阈值（默认0.9，即90%）

    Returns:
        bool: 是否被完全覆盖
    """
    # 首先检查外部矩形是否完全包含内部矩形
    if outer_rect.contains(inner_rect):
        return True

    # 计算重叠面积
    overlap_area = calculate_overlap_area(inner_rect, outer_rect)

    # 如果被覆盖比例超过阈值，认为是被完全覆盖
    if inner_rect.area > 0:
        coverage_ratio = overlap_area / inner_rect.area
        return coverage_ratio >= threshold

    return False


def get_element_bounding_rect(elem_attributes: dict) -> Optional[Rect]:
    """从SVG元素属性中提取边界矩形

    Args:
        elem_attributes: 元素属性字典，包含x, y, width, height等

    Returns:
        Optional[Rect]: 矩形对象，如果无法提取则返回None
    """
    try:
        x = float(elem_attributes.get('x', 0))
        y = float(elem_attributes.get('y', 0))
        width = float(elem_attributes.get('width', 0))
        height = float(elem_attributes.get('height', 0))

        if width <= 0 or height <= 0:
            return None

        return Rect(x, y, width, height)
    except (ValueError, TypeError):
        return None
