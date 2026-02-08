# 标准库导入
import os
import sys
from typing import Optional

# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap


def get_base_path() -> str:
    """获取应用程序基础路径

    支持开发环境和 PyInstaller 打包后的环境

    Returns:
        str: 应用程序基础路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    # 开发环境 - 返回项目根目录（utils/ 的父目录）
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_icon_path() -> Optional[str]:
    """获取图标文件路径

    Returns:
        str: 图标文件的完整路径，如果找不到则返回 None
    """
    base_path = get_base_path()

    # 可能的图标路径列表
    possible_paths = [
        os.path.join(base_path, 'logo', 'Color Card_logo.ico'),
        os.path.join(base_path, 'Color Card_logo.ico'),
        os.path.join(base_path, 'logo.ico'),
        os.path.join(base_path, 'logo', 'logo.ico'),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def load_icon_universal() -> QIcon:
    """统一的图标加载函数，适用于所有环境

    Returns:
        QIcon: 应用程序图标对象
    """
    icon_path = get_icon_path()

    if icon_path:
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon

    # 如果找不到图标，创建后备图标
    return create_fallback_icon()


def create_fallback_icon() -> QIcon:
    """创建后备图标（当找不到图标文件时使用）

    Returns:
        QIcon: 后备图标对象
    """
    try:
        # 创建一个简单的蓝色图标
        pixmap = QPixmap(32, 32)
        # 使用主题蓝色作为后备图标颜色
        pixmap.fill(QColor(0, 120, 212))

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "CC")
        painter.end()

        return QIcon(pixmap)
    except (RuntimeError, ValueError):
        return QIcon()
