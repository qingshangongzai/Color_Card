"""主题颜色管理模块

提供统一的颜色获取接口，根据当前主题（暗黑/明亮）返回对应的颜色值。
"""
from PySide6.QtGui import QColor
from qfluentwidgets import isDarkTheme


# ========== 背景颜色 ==========
def get_canvas_background_color():
    """获取画布背景颜色 - 固定灰黑色 #2a2a2a"""
    return QColor(42, 42, 42)


def get_card_background_color():
    """获取卡片背景颜色"""
    return QColor(42, 42, 42) if isDarkTheme() else QColor(255, 255, 255)


def get_interface_background_color():
    """获取界面背景颜色（与FluentWindow一致）"""
    return QColor(32, 32, 32) if isDarkTheme() else QColor(243, 243, 243)


def get_histogram_background_color():
    """获取直方图背景颜色 - 固定灰黑色 #2a2a2a"""
    return QColor(42, 42, 42)


# ========== 文本颜色 ==========
def get_text_color(secondary=False):
    """获取主题文本颜色"""
    if isDarkTheme():
        return QColor(160, 160, 160) if secondary else QColor(255, 255, 255)
    else:
        return QColor(120, 120, 120) if secondary else QColor(40, 40, 40)


def get_title_color():
    """获取标题颜色"""
    return QColor(255, 255, 255) if isDarkTheme() else QColor(40, 40, 40)


def get_secondary_text_color():
    """获取次要文本颜色"""
    return QColor(160, 160, 160) if isDarkTheme() else QColor(120, 120, 120)


# ========== 边框颜色 ==========
def get_border_color():
    """获取边框颜色"""
    return QColor(80, 80, 80) if isDarkTheme() else QColor(221, 221, 221)


def get_border_color_secondary():
    """获取次要边框颜色"""
    return QColor(120, 120, 120) if isDarkTheme() else QColor(200, 200, 200)


# ========== 占位符/空状态颜色 ==========
def get_placeholder_color():
    """获取占位符颜色（空色块背景）"""
    return QColor(60, 60, 60) if isDarkTheme() else QColor(204, 204, 204)


# ========== 控件特定颜色 ==========
def get_picker_border_color():
    """获取取色点边框颜色"""
    return QColor(40, 40, 40)


def get_picker_fill_color():
    """获取取色点填充颜色"""
    return QColor(255, 255, 255)


def get_wheel_bg_color():
    """获取色轮背景颜色"""
    return QColor(42, 42, 42)


def get_wheel_border_color():
    """获取色轮边框颜色"""
    return QColor(80, 80, 80)


def get_wheel_text_color():
    """获取色轮文本颜色"""
    return QColor(200, 200, 200)


def get_wheel_selector_border_color():
    """获取色轮选择器边框颜色"""
    return QColor(255, 255, 255)


def get_wheel_selector_inner_color():
    """获取色轮选择器内部颜色"""
    return QColor(0, 0, 0)


def get_wheel_line_color(selected=False):
    """获取色轮连线颜色"""
    return QColor(255, 255, 255, 200) if selected else QColor(255, 255, 255, 128)


def get_wheel_label_color():
    """获取色轮标签颜色 - 固定灰色 #969696"""
    return QColor(150, 150, 150)


# ========== 直方图颜色 ==========
def get_histogram_grid_color():
    """获取直方图网格颜色"""
    return QColor(80, 80, 80) if isDarkTheme() else QColor(200, 200, 200)


def get_histogram_axis_color():
    """获取直方图坐标轴颜色"""
    return QColor(120, 120, 120) if isDarkTheme() else QColor(150, 150, 150)


def get_histogram_text_color():
    """获取直方图文本颜色"""
    return QColor(150, 150, 150) if isDarkTheme() else QColor(100, 100, 100)


def get_histogram_highlight_color():
    """获取直方图高亮颜色"""
    return QColor(255, 200, 50, 60)


def get_histogram_highlight_border_color():
    """获取直方图高亮边框颜色"""
    return QColor(255, 200, 50, 150)


def get_histogram_highlight_text_color():
    """获取直方图高亮文本颜色"""
    return QColor(255, 220, 100)


def get_zone_colors():
    """获取Zone分区颜色列表（暗黑主题）"""
    return [
        QColor(30, 30, 30),
        QColor(35, 35, 35),
        QColor(40, 40, 40),
        QColor(45, 45, 45),
        QColor(50, 50, 50),
        QColor(55, 55, 55),
        QColor(60, 60, 60),
        QColor(65, 65, 65),
    ]


def get_zone_colors_highlight():
    """获取Zone分区高亮颜色列表（暗黑主题）"""
    return [
        QColor(50, 50, 60),
        QColor(55, 55, 65),
        QColor(60, 60, 70),
        QColor(65, 65, 75),
        QColor(70, 70, 80),
        QColor(75, 75, 85),
        QColor(80, 80, 90),
        QColor(85, 85, 95),
    ]


def get_histogram_blue_color(alpha=180):
    """获取直方图蓝色"""
    return QColor(0, 100, 255, alpha)


def get_histogram_green_color(alpha=180):
    """获取直方图绿色"""
    return QColor(0, 200, 0, alpha)


def get_histogram_red_color(alpha=180):
    """获取直方图红色"""
    return QColor(255, 50, 50, alpha)


def get_accent_color():
    """获取强调色（主题蓝）"""
    return QColor(0, 120, 212)


# ========== 画布特定颜色 ==========
def get_canvas_empty_bg_color():
    """获取画布空状态背景颜色"""
    return QColor(42, 42, 42)


def get_canvas_empty_text_color():
    """获取画布空状态文本颜色"""
    return QColor(150, 150, 150)


def get_picker_colors():
    """获取取色点颜色列表"""
    return [
        QColor(0, 102, 255, 100),
        QColor(0, 128, 255, 100),
        QColor(0, 153, 255, 100),
        QColor(0, 204, 102, 100),
        QColor(102, 255, 102, 100),
        QColor(255, 204, 0, 100),
        QColor(255, 128, 0, 100),
        QColor(255, 51, 102, 100),
    ]


def get_tooltip_bg_color():
    """获取提示框背景颜色"""
    return QColor(0, 0, 0, 180)


def get_tooltip_border_color():
    """获取提示框边框颜色"""
    return QColor(255, 255, 255)


def get_tooltip_text_color():
    """获取提示框文本颜色"""
    return QColor(0, 0, 0)


# ========== 缩放查看器颜色 ==========
def get_zoom_grid_color():
    """获取缩放查看器网格颜色"""
    return QColor(0, 0, 0, 80)


def get_zoom_bg_color():
    """获取缩放查看器背景颜色"""
    return QColor(200, 200, 200) if isDarkTheme() else QColor(40, 40, 40)


# ========== 对话框颜色 ==========
def get_dialog_bg_color():
    """获取对话框背景颜色"""
    return QColor(32, 32, 32) if isDarkTheme() else QColor(255, 255, 255)


# ========== Zone框颜色 ==========
def get_zone_background_color():
    """获取Zone框背景颜色"""
    return QColor(70, 70, 70) if isDarkTheme() else QColor(255, 255, 255)


def get_zone_text_color():
    """获取Zone框文字颜色"""
    return QColor(255, 255, 255) if isDarkTheme() else QColor(0, 0, 0)


# ========== 收藏组件颜色 ==========
def get_favorite_icon_color():
    """获取收藏界面图标颜色"""
    return QColor(153, 153, 153)


# ========== 高饱和度区域高亮颜色 ==========
def get_high_saturation_highlight_color():
    """获取高饱和度区域高亮颜色 - 半透明品红色"""
    return QColor(255, 0, 128, 80)


def get_high_saturation_border_color():
    """获取高饱和度区域边框颜色"""
    return QColor(255, 0, 128, 150)


def get_high_brightness_highlight_color():
    """获取高明度区域高亮颜色 - 半透明青色"""
    return QColor(0, 200, 255, 80)


def get_high_brightness_border_color():
    """获取高明度区域边框颜色"""
    return QColor(0, 200, 255, 150)
