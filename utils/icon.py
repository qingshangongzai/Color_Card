"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: icon
功能描述: 图标工具模块，提供应用程序图标加载支持

本模块提供以下功能：
1. 获取应用程序基础路径
2. 获取图标文件路径
3. 加载应用程序图标（支持开发环境和打包后的环境）
4. 创建后备图标（当找不到图标文件时使用）

参考文档：状态栏图标显示参考文档.md

作者: 青山公仔
创建日期: 2026-02-04
"""

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
    # 开发环境
    return os.path.dirname(os.path.abspath(__file__))


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
        pixmap.fill(QColor("#0078d4"))

        painter = QPainter(pixmap)
        painter.setPen(QColor('white'))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "CC")
        painter.end()

        return QIcon(pixmap)
    except (RuntimeError, ValueError):
        return QIcon()
