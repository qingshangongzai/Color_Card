"""安装器迷你样式层

提供安装向导所需的静态色表与 QSS 生成器，独立于主程序 UI 组件库。
色值取自 PySide6-Fluent-Widgets 1.11.3 实际样式与项目 theme_colors 模块的
对应 getter；安装器仅运行数分钟，深浅色在启动时判定一次后烘焙进 QSS。
"""

# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

ACCENT = '#0078d4'

# 控件字体：原型对按钮/输入框/复选框统一 setFont(14px, 家族栈)，普通 QLabel 保持系统默认字号
_CONTROL_FONT = 'font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC"; font-size: 14px;'

# 指示器绘制区 20px = 内容 18px + 四周各 1px 透明描边。透明描边不是装饰：
# Qt 用它把 SE_CheckBoxIndicator 撑到 20px（实测 18+1px 边框=20，改成 border:none 会缩到 18），
# 自绘对勾的坐标按指示器矩形归一化，删掉这层边框会让对勾与方框一起缩小
_INDICATOR_CONTENT = 18
_INDICATOR_BORDER = 1

# 色表。btn_* / border / pressed_fg / disabled_fg 为 rgba 字符串，只能拼进 QSS，
# 不能传给 QColor 构造。border_edge 对应 button.qss 的底边（浅色）/顶边（深色）。
_LIGHT = {
    'window_bg': '#ffffff',
    'window_fg': '#282828',
    'fg_secondary': '#787878',
    'accent': ACCENT,
    'on_accent': '#ffffff',
    'accent_hover': '#007edf',
    'accent_pressed': '#4ea0df',
    'btn_bg': 'rgba(255,255,255,0.7)',
    'btn_hover': 'rgba(249,249,249,0.5)',
    'btn_pressed': 'rgba(249,249,249,0.3)',
    'btn_disabled': 'rgba(249,249,249,0.3)',
    'border': 'rgba(0,0,0,0.073)',
    'border_edge': 'rgba(0,0,0,0.183)',
    'field_bg': '#ffffff',
    'close_hover_bg': '#e81123',
    'close_hover_fg': '#ffffff',
    'pressed_fg': 'rgba(0,0,0,0.63)',
    'disabled_fg': 'rgba(0,0,0,0.36)',
}

_DARK = {
    'window_bg': '#202020',
    'window_fg': '#ffffff',
    'fg_secondary': '#a0a0a0',
    'accent': ACCENT,
    'on_accent': '#ffffff',
    'accent_hover': '#3aa9ff',
    'accent_pressed': '#74c3ff',
    'btn_bg': 'rgba(255,255,255,0.0605)',
    'btn_hover': 'rgba(255,255,255,0.0837)',
    'btn_pressed': 'rgba(255,255,255,0.0326)',
    'btn_disabled': 'rgba(255,255,255,0.0419)',
    'border': 'rgba(255,255,255,0.053)',
    'border_edge': 'rgba(255,255,255,0.08)',
    'field_bg': '#2d2d2d',
    'close_hover_bg': '#c42b1c',
    'close_hover_fg': '#ffffff',
    'pressed_fg': 'rgba(255,255,255,0.786)',
    'disabled_fg': 'rgba(255,255,255,0.3628)',
}


def detect_scheme() -> str:
    """检测系统深浅色方案

    仅当主屏 colorScheme 为 Dark 时返回 'dark'；无屏幕或 Unknown 均回退 'light'。
    """
    if QGuiApplication.primaryScreen() is None:
        return 'light'
    if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return 'dark'
    return 'light'


def resolve_tokens(scheme: str | None = None) -> dict[str, str]:
    """返回指定方案的色表（每次返回副本，调用方可自行持有）

    Args:
        scheme: 'light' / 'dark'，缺省时检测系统深浅

    Returns:
        dict[str, str]: 色表字典（hex 值可直接 QColor 构造，rgba 值只能拼进 QSS）
    """
    if scheme is None:
        scheme = detect_scheme()
    return dict(_DARK if scheme == 'dark' else _LIGHT)


def build_qss(scheme: str) -> str:
    """生成完整 QSS（app 级与 dialog 级共用同一份单一事实源）

    Args:
        scheme: 'light' / 'dark'

    Returns:
        str: 完整样式表
    """
    # 声明式整表、无分支逻辑，不按控件段拆函数：拆分会打散规则顺序与取值来源，
    # 且 app 级与 dialog 级必须共用同一张表
    tokens = resolve_tokens(scheme)
    # button.qss：浅色加深底边、深色加亮顶边，营造轻微立体感
    edge_side = 'border-top' if scheme == 'dark' else 'border-bottom'
    return f"""
    QWidget {{
        color: {tokens['window_fg']};
        background: transparent;
    }}
    QDialog {{
        background-color: {tokens['window_bg']};
    }}
    QLabel {{
        color: {tokens['window_fg']};
        background-color: transparent;
    }}
    QPushButton {{
        {_CONTROL_FONT}
        color: {tokens['window_fg']};
        background-color: {tokens['btn_bg']};
        border: 1px solid {tokens['border']};
        {edge_side}: 1px solid {tokens['border_edge']};
        border-radius: 5px;
        padding: 5px 12px 6px 12px;
    }}
    QPushButton:hover {{
        background-color: {tokens['btn_hover']};
    }}
    QPushButton:pressed {{
        background-color: {tokens['btn_pressed']};
        color: {tokens['pressed_fg']};
    }}
    QPushButton:disabled {{
        background-color: {tokens['btn_disabled']};
        color: {tokens['disabled_fg']};
    }}
    PrimaryPushButton {{
        color: {tokens['on_accent']};
        background-color: {tokens['accent']};
        border: 1px solid {tokens['accent']};
        border-radius: 5px;
        padding: 5px 12px 6px 12px;
    }}
    PrimaryPushButton:hover {{
        background-color: {tokens['accent_hover']};
        border: 1px solid {tokens['accent_hover']};
    }}
    PrimaryPushButton:pressed {{
        background-color: {tokens['accent_pressed']};
        border: 1px solid {tokens['accent_pressed']};
        color: rgba(255,255,255,0.63);
    }}
    QLineEdit {{
        {_CONTROL_FONT}
        color: {tokens['window_fg']};
        background-color: {tokens['field_bg']};
        border: 1px solid {tokens['border']};
        border-radius: 5px;
        padding: 0px 10px;
        selection-background-color: {tokens['accent']};
    }}
    QLineEdit:focus {{
        border: 1px solid {tokens['accent']};
    }}
    QProgressBar {{
        background-color: {tokens['border']};
        border: none;
        border-radius: 3px;
    }}
    QProgressBar::chunk {{
        background-color: {tokens['accent']};
        border-radius: 3px;
    }}
    QCheckBox {{
        {_CONTROL_FONT}
        color: {tokens['window_fg']};
        background: transparent;
        spacing: 8px;
        min-width: 28px;
        min-height: 22px;
        margin-left: 1px;
        outline: none;
    }}
    QCheckBox::indicator {{
        width: {_INDICATOR_CONTENT}px;
        height: {_INDICATOR_CONTENT}px;
        border: {_INDICATOR_BORDER}px solid transparent;
        background: transparent;
    }}
    QCheckBox:disabled {{
        color: {tokens['disabled_fg']};
    }}
    """


# 复选框指示器配色：与原型 check_box.py 的状态表同值，RGBA 取 0-255
_CHECKBOX_LIGHT = {
    'border': (0, 0, 0, 122),
    'border_hover': (0, 0, 0, 143),
    'border_pressed': (0, 0, 0, 69),
    'border_disabled': (0, 0, 0, 56),
    'bg': (0, 0, 0, 6),
    'bg_hover': (0, 0, 0, 13),
    'bg_pressed': (0, 0, 0, 31),
    'bg_disabled': (0, 0, 0, 0),
    'checked_disabled': (0, 0, 0, 56),
}

_CHECKBOX_DARK = {
    'border': (255, 255, 255, 141),
    'border_hover': (255, 255, 255, 141),
    'border_pressed': (255, 255, 255, 40),
    'border_disabled': (255, 255, 255, 41),
    'bg': (0, 0, 0, 26),
    'bg_hover': (255, 255, 255, 11),
    'bg_pressed': (255, 255, 255, 18),
    'bg_disabled': (0, 0, 0, 0),
    'checked_disabled': (255, 255, 255, 41),
}


def checkbox_colors(scheme: str | None = None) -> dict[str, tuple[int, int, int, int]]:
    """返回复选框指示器的描边/底色 RGBA 表（每次返回副本，调用方可自行持有）

    Args:
        scheme: 'light' / 'dark'，缺省时检测系统深浅

    Returns:
        dict[str, tuple[int, int, int, int]]: 键为 border/bg/checked_disabled 及其状态变体
    """
    if scheme is None:
        scheme = detect_scheme()
    return dict(_CHECKBOX_DARK if scheme == 'dark' else _CHECKBOX_LIGHT)


def apply_mini_style(app: QApplication) -> None:
    """为安装器进程设置应用级缺省样式

    Args:
        app: 当前 QApplication 实例
    """
    app.setStyleSheet(build_qss(detect_scheme()))
