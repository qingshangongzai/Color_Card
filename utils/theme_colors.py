"""主题颜色管理模块

提供统一的颜色获取接口，根据当前主题（暗黑/明亮）返回对应的颜色值。
"""
from PySide6.QtGui import QColor
from qfluentwidgets import isDarkTheme


# ========== 背景颜色 ==========
def get_canvas_background_color():
    """获取画布背景颜色 - 固定灰黑色 #2a2a2a"""
    return QColor(42, 42, 42)


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
        QColor(70, 70, 70),
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
        QColor(90, 90, 100),
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


def get_tooltip_bg_color():
    """获取提示框背景颜色"""
    return QColor(0, 0, 0, 180)


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


def get_close_button_hover_bg_color():
    """获取关闭按钮悬停背景颜色"""
    return QColor(196, 43, 28) if isDarkTheme() else QColor(232, 17, 35)


def get_close_button_hover_color():
    """获取关闭按钮悬停图标颜色"""
    return QColor(255, 255, 255)


def get_close_button_pressed_color():
    """获取关闭按钮按下图标颜色"""
    return QColor(255, 255, 255)


# ========== Zone框颜色 ==========
def get_zone_background_color():
    """获取Zone框背景颜色"""
    return QColor(70, 70, 70) if isDarkTheme() else QColor(255, 255, 255)


def get_zone_text_color():
    """获取Zone框文字颜色"""
    return QColor(255, 255, 255) if isDarkTheme() else QColor(0, 0, 0)


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


# ========== Zone遮罩颜色（按类型统一）==========
def get_zone_mask_colors():
    """获取Zone遮罩颜色列表（按类型统一颜色）

    颜色方案：
    - 黑色: 深灰色半透明
    - 阴影: 蓝色半透明
    - 中间调: 绿色半透明
    - 高光: 黄色半透明
    - 白色: 白色半透明
    """
    # 黑色 - 深蓝色
    blacks_color = QColor(0, 80, 160, 140)
    # 阴影 - 蓝色
    shadows_color = QColor(0, 120, 255, 100)
    # 中间调 - 绿色
    midtones_color = QColor(0, 200, 100, 100)
    # 高光 - 黄色
    highlights_color = QColor(255, 200, 0, 100)
    # 白色 - 深黄色
    whites_color = QColor(200, 160, 0, 140)

    return [
        blacks_color,      # Zone 0: 黑色
        shadows_color,     # Zone 1: 阴影
        shadows_color,     # Zone 2: 阴影
        midtones_color,    # Zone 3: 中间调
        midtones_color,    # Zone 4: 中间调
        midtones_color,    # Zone 5: 中间调
        highlights_color,  # Zone 6: 高光
        highlights_color,  # Zone 7: 高光
        whites_color,      # Zone 8: 白色
    ]


def get_zone_label_bg_color():
    """获取Zone标注框背景颜色 - 统一使用深色"""
    return QColor(40, 40, 40, 200)


def get_zone_label_text_color():
    """获取Zone标注框文字颜色 - 统一使用白色"""
    return QColor(255, 255, 255)


def get_zone_info_text_colors():
    """获取Zone信息提示文字颜色列表（与遮罩颜色对应）"""
    # 与 get_zone_mask_colors() 对应，但使用不透明颜色
    blacks_color = QColor(100, 180, 255)  # 黑色区域用蓝色文字
    shadows_color = QColor(100, 180, 255)  # 阴影区域用蓝色
    midtones_color = QColor(100, 255, 150)  # 中间调用绿色
    highlights_color = QColor(255, 220, 100)  # 高光用黄色
    whites_color = QColor(255, 200, 50)  # 白色区域用深黄色

    return [
        blacks_color,      # Zone 0
        shadows_color,     # Zone 1
        shadows_color,     # Zone 2
        midtones_color,    # Zone 3
        midtones_color,    # Zone 4
        midtones_color,    # Zone 5
        highlights_color,  # Zone 6
        highlights_color,  # Zone 7
        whites_color,      # Zone 8
    ]


# ========== 影调分析图表颜色 ==========
def get_tone_chart_bg_color():
    """获取影调分析图表背景颜色"""
    return QColor(30, 30, 30) if isDarkTheme() else QColor(255, 255, 255)


def get_tone_chart_text_color():
    """获取影调分析图表文字颜色"""
    return QColor(255, 255, 255) if isDarkTheme() else QColor(51, 51, 51)


def get_tone_chart_grid_color():
    """获取影调分析图表网格颜色"""
    return QColor(68, 68, 68) if isDarkTheme() else QColor(204, 204, 204)


def get_tone_chart_bar_color():
    """获取影调分析图表柱状图颜色"""
    return QColor(74, 144, 217)


def get_tone_chart_mean_line_color():
    """获取影调分析图表均值线颜色"""
    return QColor(255, 107, 107)


def get_tone_chart_median_line_color():
    """获取影调分析图表中位数线颜色"""
    return QColor(81, 207, 102)
