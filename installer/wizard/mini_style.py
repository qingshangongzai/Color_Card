"""安装器迷你样式层

提供安装向导所需的静态色表与 QSS 生成器，独立于主程序 UI 组件库。
色值取自 PySide6-Fluent-Widgets 1.11.3 的实际样式表与绘制代码；安装器仅运行
数分钟，深浅色在启动时判定一次后烘焙进 QSS 与自绘组件。

安装器为控制体积不复用主程序的组件库与 theme_colors，色值在本模块自持；
主程序主色或控件样式调整时，须同步 ACCENT 与五个派生层，以及本文件其余色值。
"""

# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

# 选用色素。深色下原库把它派生为 hsv(s*0.84, v=1) 即 #29a2ff；
# 改动本常量时五个派生层（accent_l1~l3 / accent_d1~d2）必须同步重算，不能只改 accent
ACCENT = '#0078d4'

# 控件字体：原型对按钮/输入框/复选框统一 setFont(14px, 家族栈)，普通 QLabel 保持系统默认字号
_CONTROL_FONT = 'font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC"; font-size: 14px;'

# 指示器绘制区 20px = 内容 18px + 四周各 1px 透明描边。透明描边不是装饰：
# Qt 用它把 SE_CheckBoxIndicator 撑到 20px（实测 18+1px 边框=20，改成 border:none 会缩到 18），
# 自绘对勾的坐标按指示器矩形归一化，删掉这层边框会让对勾与方框一起缩小
_INDICATOR_CONTENT = 18
_INDICATOR_BORDER = 1

# 色表。hex 值可直接 QColor 构造；rgba(...)/rgb(...) 字符串只能拼进 QSS。
# accent_l1~l3 / accent_d1~d2 是原库 ThemeColor 六层里的五层（LIGHT_1~3 与 DARK_1~2）：
# 浅色直接用这几层的字面值，深色下同名层换用另一套字面值（如深色 LIGHT_1 实测 #3aa9ff）
_LIGHT = {
    'window_bg': '#ffffff',
    'window_fg': '#282828',
    'fg_secondary': '#787878',
    'accent': ACCENT,
    'accent_l1': '#007edf',
    'accent_l2': '#3896df',
    'accent_l3': '#4ea0df',
    'accent_d1': '#005a9f',
    'accent_d2': '#003c6a',
    'on_accent': '#ffffff',
    'on_accent_pressed': 'rgba(255,255,255,0.63)',
    'control_fg': '#000000',
    'btn_bg': 'rgba(255,255,255,0.7)',
    'btn_hover': 'rgba(249,249,249,0.5)',
    'btn_pressed': 'rgba(249,249,249,0.3)',
    'btn_disabled': 'rgba(249,249,249,0.3)',
    'btn_border_disabled': 'rgba(0,0,0,0.06)',
    'primary_disabled_fg': 'rgba(255,255,255,0.9)',
    'primary_disabled_bg': 'rgb(205,205,205)',
    'border': 'rgba(0,0,0,0.073)',
    'border_edge': 'rgba(0,0,0,0.183)',
    'field_bg': 'rgba(255,255,255,0.7)',
    'field_bg_focus': '#ffffff',
    'field_border': 'rgba(0,0,0,13)',
    'field_border_bottom': 'rgba(0,0,0,100)',
    'field_border_disabled': 'rgba(0,0,0,13)',
    'close_hover_bg': '#e81123',
    'close_hover_fg': '#ffffff',
    'pressed_fg': 'rgba(0,0,0,0.63)',
    'disabled_fg': 'rgba(0,0,0,0.36)',
}

_DARK = {
    'window_bg': '#202020',
    'window_fg': '#ffffff',
    'fg_secondary': '#a0a0a0',
    'accent': '#29a2ff',
    'accent_l1': '#3aa9ff',
    'accent_l2': '#58b6ff',
    'accent_l3': '#74c3ff',
    'accent_d1': '#2592e6',
    'accent_d2': '#2587d1',
    'on_accent': '#000000',
    'on_accent_pressed': 'rgba(0,0,0,0.63)',
    'control_fg': '#ffffff',
    'btn_bg': 'rgba(255,255,255,0.0605)',
    'btn_hover': 'rgba(255,255,255,0.0837)',
    'btn_pressed': 'rgba(255,255,255,0.0326)',
    'btn_disabled': 'rgba(255,255,255,0.0419)',
    'btn_border_disabled': 'rgba(255,255,255,0.053)',
    'primary_disabled_fg': 'rgba(255,255,255,0.43)',
    'primary_disabled_bg': 'rgb(52,52,52)',
    'border': 'rgba(255,255,255,0.053)',
    'border_edge': 'rgba(255,255,255,0.08)',
    'field_bg': 'rgba(255,255,255,0.0605)',
    'field_bg_focus': 'rgba(30,30,30,0.7)',
    'field_border': 'rgba(255,255,255,0.08)',
    'field_border_bottom': 'rgba(255,255,255,0.5442)',
    # 深色禁用态四边比常态暗一级（0.0698 vs 0.08），浅色两者同值
    'field_border_disabled': 'rgba(255,255,255,0.0698)',
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
        dict[str, str]: 色表字典（hex 值可直接 QColor 构造；rgba/rgb 字符串只能拼进 QSS，
        传给 QColor 会得到无效颜色）
    """
    if scheme is None:
        scheme = detect_scheme()
    return dict(_DARK if scheme == 'dark' else _LIGHT)


def build_qss(scheme: str) -> str:
    """生成完整 QSS（app 级与 dialog 级共用同一份单一事实源）

    整表声明式数据、无分支（圈复杂度 1）；体量超 50 行按「说明为何不可拆」豁免——拆分只会
    打散规则顺序与取值来源，且 app 级与 dialog 级必须共用同一张表。

    Args:
        scheme: 'light' / 'dark'

    Returns:
        str: 完整样式表
    """
    # 深浅色差异集中在下方的派生变量里
    tokens = resolve_tokens(scheme)
    dark = scheme == 'dark'
    # button.qss：浅色加深底边、深色加亮顶边，营造轻微立体感
    edge_side = 'border-top' if dark else 'border-bottom'
    # 主按钮下沿取更深一级：浅色 Dark1、深色 Light2
    primary_edge = tokens['accent_l2' if dark else 'accent_d1']
    # hover / pressed 的底色在深浅色下各走一套层级（浅色从 Light1 起、深色从 Dark1 起）
    primary_hover_bg = tokens['accent_d1' if dark else 'accent_l1']
    primary_hover_border = tokens['accent_l1' if dark else 'accent_l2']
    primary_pressed_bg = tokens['accent_d2' if dark else 'accent_l3']
    # 输入框选中底色：浅色用 Light1、深色用主色；选中文字两色下均取 on_accent
    selection_bg = tokens['accent' if dark else 'accent_l1']
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
        color: {tokens['control_fg']};
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
        {edge_side}: 1px solid {tokens['border']};
    }}
    QPushButton:disabled {{
        background-color: {tokens['btn_disabled']};
        color: {tokens['disabled_fg']};
        border: 1px solid {tokens['btn_border_disabled']};
        {edge_side}: 1px solid {tokens['btn_border_disabled']};
    }}
    PrimaryPushButton {{
        color: {tokens['on_accent']};
        background-color: {tokens['accent']};
        border: 1px solid {tokens['accent_l1']};
        border-bottom: 1px solid {primary_edge};
    }}
    PrimaryPushButton:hover {{
        background-color: {primary_hover_bg};
        border: 1px solid {primary_hover_border};
        border-bottom: 1px solid {primary_edge};
    }}
    PrimaryPushButton:pressed {{
        background-color: {primary_pressed_bg};
        border: 1px solid {primary_pressed_bg};
        color: {tokens['on_accent_pressed']};
    }}
    PrimaryPushButton:disabled {{
        background-color: {tokens['primary_disabled_bg']};
        border: 1px solid {tokens['primary_disabled_bg']};
        color: {tokens['primary_disabled_fg']};
    }}
    QLineEdit {{
        {_CONTROL_FONT}
        color: {tokens['control_fg']};
        background-color: {tokens['field_bg']};
        border: 1px solid {tokens['field_border']};
        border-bottom: 1px solid {tokens['field_border_bottom']};
        border-radius: 5px;
        padding: 0px 10px;
        selection-background-color: {selection_bg};
        selection-color: {tokens['on_accent']};
    }}
    QLineEdit:hover {{
        background-color: {tokens['btn_hover']};
    }}
    QLineEdit:focus {{
        background-color: {tokens['field_bg_focus']};
        border-bottom: 1px solid {tokens['field_border']};
    }}
    QLineEdit:disabled {{
        color: {tokens['disabled_fg']};
        background-color: {tokens['btn_disabled']};
        border: 1px solid {tokens['field_border_disabled']};
        border-bottom: 1px solid {tokens['field_border_disabled']};
    }}
    QCheckBox {{
        {_CONTROL_FONT}
        color: {tokens['control_fg']};
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


# 选中态填充色：深浅色各取一套派生层（原型 check_box.py 的 CHECKED_HOVER/PRESSED 分别取
# ThemeColor 的 LIGHT_1/2 与 DARK_1/2，与按钮的 hover/pressed 不同源）
_CHECKED_FILL = {
    'light': {'normal': 'accent', 'hover': 'accent_l1', 'pressed': 'accent_l2'},
    'dark': {'normal': 'accent', 'hover': 'accent_d1', 'pressed': 'accent_d2'},
}


def checked_fill_colors(scheme: str | None = None) -> dict[str, str]:
    """返回复选框选中态的填充色（每次返回副本，自绘专用）

    Args:
        scheme: 'light' / 'dark'，缺省时检测系统深浅

    Returns:
        dict[str, str]: 键为 normal/hover/pressed，值为 hex 色值（可直接 QColor 构造）
    """
    if scheme is None:
        scheme = detect_scheme()
    tokens = resolve_tokens(scheme)
    fill_keys = _CHECKED_FILL['dark' if scheme == 'dark' else 'light']
    return {state: tokens[key] for state, key in fill_keys.items()}


# 进度条轨道：原型 progress_bar.py 用 QColor(0,0,0,155) / QColor(255,255,255,155) 画一条
# 1px 居中横线。QSS 表达不出「1px 横线 + 其余透明」，故轨道色不进制色表，只供自绘取用
_PROGRESS_TRACK = {'light': (0, 0, 0, 155), 'dark': (255, 255, 255, 155)}


def progress_track_rgba(scheme: str | None = None) -> tuple[int, int, int, int]:
    """返回进度条轨道线的 RGBA（自绘专用，不能用于 QSS）

    Args:
        scheme: 'light' / 'dark'，缺省时检测系统深浅

    Returns:
        tuple[int, int, int, int]: RGBA 分量，0-255
    """
    if scheme is None:
        scheme = detect_scheme()
    return _PROGRESS_TRACK['dark' if scheme == 'dark' else 'light']


def apply_mini_style(app: QApplication) -> None:
    """为安装器进程设置应用级缺省样式

    Args:
        app: 当前 QApplication 实例
    """
    app.setStyleSheet(build_qss(detect_scheme()))
