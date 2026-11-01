"""动态色彩微调调色板引擎

移植自原型 D:\\Code\\DeltaPalette\\dist\\index.html 的核心计算逻辑：
基色 + 「联动偏移 / 独立锁定」双模式配色、五种色彩模式（HSB/HSL/RGB/LAB/CMYK）
切换时所有 HEX 不变、H 环形通道、内部唯一事实来源是浮点 RGB（仅显示层取整）。

本模块为纯 Python 计算层，不依赖 Qt，可独立单测；UI 层职责（失焦提交、
刷新、提示等）不在此实现。
"""

# 标准库导入
import math
import re
from dataclasses import dataclass
from typing import Callable

# 项目模块导入
from .color import (
    _cmyk_to_rgb_float,
    _hsl_to_rgb_float,
    _hsb_to_rgb_float,
    _lab_to_rgb_float,
    hex_to_rgb,
    rgb_to_cmyk,
    rgb_to_hsb,
    rgb_to_hsl,
    rgb_to_lab,
)
from .logger import get_logger

logger = get_logger("palette_tuning")


# ==================== 常量 ====================

MIN_COUNT = 3       # 配色数量下限
MAX_COUNT = 12      # 配色数量上限
DEFAULT_COUNT = 6   # 默认配色数量
STEP = 1.0          # 步进幅度（原型 STEP=1）

# 卡片名称中文数字（与原型 NAME_LIST 一致；UI 层显示时用多语言键 palette_tuning.item_name 覆盖）
_NAME_LIST = ('一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二')

# 默认基色：HSB(180, 50, 50) → #408080。三通道取滑块中点，避免纯黑时 H 拖动无效果
_DEFAULT_BASE_RGB: tuple[float, float, float] = _hsb_to_rgb_float(180.0, 50.0, 50.0)


# ==================== 数据结构 ====================

@dataclass(frozen=True)
class ChannelSpec:
    """单通道规格（范围 / 偏移上限 / 环形标记 / 显示精度）"""

    key: str        # 通道键，如 'h' / 's' / 'v'
    label_key: str  # 多语言键，如 'palette_tuning.channel.h'
    min: float      # 通道值下限
    max: float      # 通道值上限
    off_max: float  # 联动偏移量绝对值上限
    circular: bool  # 是否环形通道（H）
    dec: int        # 显示精度（小数位）


@dataclass(frozen=True)
class ModeSpec:
    """色彩模式规格（通道组 + 双向转换函数）"""

    key: str
    label: str  # 'HSB' 等模式名（各语言一致，不翻译）
    channels: tuple[ChannelSpec, ...]
    from_rgb: Callable[..., tuple]                       # 浮点 RGB -> 通道值元组
    to_rgb: Callable[..., tuple[float, float, float]]    # 通道值 -> 浮点 RGB

    def channel_of(self, key: str) -> ChannelSpec:
        """按键查通道规格，未知键抛 KeyError

        Args:
            key: 通道键

        Returns:
            ChannelSpec: 通道规格
        """
        for c in self.channels:
            if c.key == key:
                return c
        raise KeyError(key)


@dataclass
class TuningItem:
    """单个配色条目

    联动模式存 offset（相对基色的逐通道偏移量），锁定模式存 absolute
    （绝对通道值）；final_rgb 为最终颜色的浮点 RGB，是显示层唯一事实来源。
    """

    id: int
    name: str
    is_locked: bool
    offset: dict[str, float]
    absolute: dict[str, float] | None
    final_rgb: tuple[float, float, float]


# ==================== 工具函数 ====================

def _round_prec(v: float, dec: int) -> float:
    """按显示精度取整，复刻 JS Math.round 远离零舍入

    Python round() 是银行家舍入（round(2.5)=2），必须用 floor(x+0.5) 复刻
    JS 语义（Math.round(2.5)=3；对负数同样一致，Math.round(-1.5)=-1）。

    Args:
        v: 数值
        dec: 小数位

    Returns:
        float: 取整后的值
    """
    m = 10 ** dec
    return math.floor(v * m + 0.5) / m


def _mod360(v: float) -> float:
    """H 环形归一：350+20 -> 10；10-20 -> 350；360 -> 0

    Python % 结果非负，与原型 ((v % 360) + 360) % 360 等价。
    """
    return v % 360


def _shortest_delta(d: float) -> float:
    """环形通道差值归一到最短方向 [-180, 180)

    Args:
        d: 原始差值

    Returns:
        float: 归一后的差值
    """
    return ((d % 360) + 540) % 360 - 180


def _clamp(v: float, lo: float, hi: float) -> float:
    """数值钳制"""
    return max(lo, min(hi, v))


def hex_now(rgb: tuple[float, float, float]) -> str:
    """浮点 RGB 转 HEX（显示层取整：单通道 round + cl255，大写补零）

    Args:
        rgb: 浮点 RGB (0-255)

    Returns:
        str: '#RRGGBB'
    """
    parts = []
    for v in rgb:
        n = int(_clamp(_round_prec(v, 0), 0, 255))
        parts.append(f'{n:02X}')
    return '#' + ''.join(parts)


_HEX3_RE = re.compile(r'^[0-9a-fA-F]{3}$')
_HEX6_RE = re.compile(r'^[0-9a-fA-F]{6}$')


def parse_hex_input(text: str | None) -> str | None:
    """解析用户输入的 HEX

    支持 #RGB / #RRGGBB / RRGGBB（大小写不限），3 位自动展开。

    Args:
        text: 用户输入文本

    Returns:
        str | None: 合法返回规范化大写 '#RRGGBB'；非法返回 None（回退与提示由 UI 负责）
    """
    if text is None:
        return None
    s = str(text).strip()
    if s.startswith('#'):
        s = s[1:]
    if _HEX3_RE.match(s):
        s = ''.join(ch * 2 for ch in s)
    if not _HEX6_RE.match(s):
        return None
    return '#' + s.upper()


# ==================== 模式注册表 ====================

def _rgb_from_rgb(r: float, g: float, b: float) -> tuple[float, float, float]:
    """RGB 模式 fromRgb：恒等直通"""
    return (r, g, b)


def _rgb_to_rgb_clamped(r: float, g: float, b: float) -> tuple[float, float, float]:
    """RGB 模式 toRgb：cl255 直通（仅钳制，不取整）"""
    return (_clamp(r, 0.0, 255.0), _clamp(g, 0.0, 255.0), _clamp(b, 0.0, 255.0))


def _channel(
    key: str,
    min_v: float,
    max_v: float,
    off_max: float,
    circular: bool,
    dec: int,
) -> ChannelSpec:
    """构建通道规格（label_key 统一按 palette_tuning.channel.<key> 约定）"""
    return ChannelSpec(
        key=key,
        label_key=f'palette_tuning.channel.{key}',
        min=min_v,
        max=max_v,
        off_max=off_max,
        circular=circular,
        dec=dec,
    )


# 通道定义与原型 MODES 逐项一致（index.html 642-694 行）
MODES: dict[str, ModeSpec] = {
    'hsb': ModeSpec(
        key='hsb',
        label='HSB',
        channels=(
            _channel('h', 0, 360, 360, True, 0),
            _channel('s', 0, 100, 100, False, 0),
            _channel('v', 0, 100, 100, False, 0),
        ),
        from_rgb=rgb_to_hsb,
        to_rgb=_hsb_to_rgb_float,
    ),
    'hsl': ModeSpec(
        key='hsl',
        label='HSL',
        channels=(
            _channel('h', 0, 360, 360, True, 0),
            _channel('s', 0, 100, 100, False, 0),
            _channel('l', 0, 100, 100, False, 0),
        ),
        from_rgb=rgb_to_hsl,
        to_rgb=_hsl_to_rgb_float,
    ),
    'rgb': ModeSpec(
        key='rgb',
        label='RGB',
        channels=(
            _channel('r', 0, 255, 255, False, 0),
            _channel('g', 0, 255, 255, False, 0),
            _channel('b', 0, 255, 255, False, 0),
        ),
        from_rgb=_rgb_from_rgb,
        to_rgb=_rgb_to_rgb_clamped,
    ),
    'lab': ModeSpec(
        key='lab',
        label='LAB',
        channels=(
            _channel('l', 0, 100, 100, False, 0),
            _channel('a', -128, 127, 128, False, 1),
            _channel('b', -128, 127, 128, False, 1),
        ),
        from_rgb=rgb_to_lab,
        to_rgb=_lab_to_rgb_float,
    ),
    'cmyk': ModeSpec(
        key='cmyk',
        label='CMYK',
        channels=(
            _channel('c', 0, 100, 100, False, 0),
            _channel('m', 0, 100, 100, False, 0),
            _channel('y', 0, 100, 100, False, 0),
            _channel('k', 0, 100, 100, False, 0),
        ),
        from_rgb=rgb_to_cmyk,
        to_rgb=_cmyk_to_rgb_float,
    ),
}


# ==================== 引擎 ====================

class PaletteTuningEngine:
    """动态色彩微调调色板引擎（状态 + 全部写入口）

    写入口语义与原型 JS 一一对应：
    - set_base_channel / set_base_hex / set_param / step_param 写后重算 final_rgb；
    - switch_mode / lock_item / unlock_item 不重算 final_rgb
      （零跳变由构造保证：只重算 offset / absolute）。
    """

    def __init__(self) -> None:
        """初始化默认态：基色 #408080、6 个全联动配色、HSB 模式"""
        self._mode: str = 'hsb'
        self._base_rgb: tuple[float, float, float] = _DEFAULT_BASE_RGB
        # 用户亲手编辑的基色通道值 (mode_key, 通道值字典)；None 表示由 RGB 反算
        self._edited: tuple[str, dict[str, float]] | None = None
        self._items: list[TuningItem] = []
        for idx in range(DEFAULT_COUNT):
            item = self._make_item(idx)
            self._items.append(item)
            self._compose_final(item)

    # ---- 只读状态 ----

    @property
    def mode(self) -> str:
        """当前色彩模式键（hsb/hsl/rgb/lab/cmyk）"""
        return self._mode

    @property
    def base_rgb(self) -> tuple[float, float, float]:
        """基色浮点 RGB（内部事实来源）"""
        return self._base_rgb

    @property
    def items(self) -> list[TuningItem]:
        """配色条目列表（按显示顺序；结构由引擎维护，外部不得增删）"""
        return self._items

    # ---- 基色读 ----

    def base_channels(self, mode_key: str | None = None) -> dict[str, float]:
        """基色通道向量（唯一取用入口）

        同模式优先返回用户亲手编辑的那组通道值（edited 机制，避免两类
        可感知 bug：CMYK 反算强制 min(C,M,Y)=0、H=360 反算必然归 0），
        否则由基色 RGB 按指定模式反算。

        Args:
            mode_key: 目标模式键，None 表示当前模式

        Returns:
            dict: 通道键 -> 通道值（浮点）
        """
        mode = MODES[mode_key if mode_key is not None else self._mode]
        if self._edited is not None and self._edited[0] == mode.key:
            return dict(self._edited[1])
        return self._channels_from_rgb(mode, self._base_rgb)

    # ---- 基色写 ----

    def set_base_channel(self, key: str, value: float) -> None:
        """编辑基色单通道（滑块 / 数值框入口），写后重算全部联动配色

        Args:
            key: 通道键（当前模式的通道）
            value: 新通道值（超界按通道范围钳制）
        """
        mode = MODES[self._mode]
        spec = mode.channel_of(key)
        ch = self.base_channels()
        ch[key] = _clamp(float(value), spec.min, spec.max)
        self._base_rgb = self._channels_to_rgb(mode, ch)
        # 记住这组编辑值；LAB 例外——a/b 可能超 sRGB 色域，显示截断后的真实值
        self._edited = None if mode.key == 'lab' else (mode.key, ch)
        self._recompose_unlocked()

    def set_base_hex(self, hex_str: str) -> str | None:
        """将合法 HEX 应用为基色

        颜色未变（等价 HEX 输入）时保留 edited，显示数字不因等价输入被归一化。

        Args:
            hex_str: 用户输入的 HEX 文本

        Returns:
            str | None: 合法返回规范化大写 HEX；非法返回 None（状态不变）
        """
        parsed = parse_hex_input(hex_str)
        if parsed is None:
            return None
        r, g, b = hex_to_rgb(parsed)
        rgb = (float(r), float(g), float(b))
        if hex_now(rgb) != hex_now(self._base_rgb):
            self._edited = None
        self._base_rgb = rgb
        self._recompose_unlocked()
        return parsed

    # ---- 配色写 ----

    def set_param(self, item_id: int, key: str, value: float) -> None:
        """统一写入口：设置偏移量（联动）或绝对值（独立），写后重算该卡片

        Args:
            item_id: 配色条目 id
            key: 通道键（当前模式的通道）
            value: 原始输入值（按显示精度取整后写入）
        """
        item = self._item_by_id(item_id)
        if item is None:
            return
        spec = MODES[self._mode].channel_of(key)
        v = _round_prec(float(value), spec.dec)
        if item.is_locked:
            item.absolute[key] = _clamp(v, spec.min, spec.max)
        else:
            item.offset[key] = _clamp(v, -spec.off_max, spec.off_max)
        self._compose_final(item)

    def step_param(self, item_id: int, key: str, direction: int) -> None:
        """步进 ±1：联动改偏移量（±off_max），独立改绝对值，到边界无操作

        Args:
            item_id: 配色条目 id
            key: 通道键（当前模式的通道）
            direction: 步进方向（+1 / -1）
        """
        item = self._item_by_id(item_id)
        if item is None:
            return
        spec = MODES[self._mode].channel_of(key)
        if item.is_locked:
            store = item.absolute
            assert store is not None, "锁定项必须已有绝对值（lock_item 保证）"
            lo, hi = spec.min, spec.max
        else:
            store = item.offset
            lo, hi = -spec.off_max, spec.off_max
        current = store[key]
        nxt = _clamp(_round_prec(current + direction * STEP, spec.dec), lo, hi)
        if abs(nxt - current) < 1e-9:
            return
        store[key] = nxt
        self._compose_final(item)

    def lock_item(self, item_id: int) -> None:
        """锁定：将当前最终颜色固化为绝对通道值（final_rgb 不动，颜色零跳变）"""
        item = self._item_by_id(item_id)
        if item is None or item.is_locked:
            return
        mode = MODES[self._mode]
        final_ch = self._channels_from_rgb(mode, item.final_rgb)
        item.absolute = {
            c.key: _clamp(_round_prec(final_ch[c.key], c.dec), c.min, c.max)
            for c in mode.channels
        }
        item.is_locked = True

    def unlock_item(self, item_id: int) -> None:
        """解锁：按当前最终颜色反算偏移量（final_rgb 不动，颜色零跳变）"""
        item = self._item_by_id(item_id)
        if item is None or not item.is_locked:
            return
        mode = MODES[self._mode]
        final_ch = self._channels_from_rgb(mode, item.final_rgb)
        item.offset = self._offset_from(final_ch, mode)
        item.is_locked = False
        item.absolute = None

    def switch_mode(self, mode_key: str) -> None:
        """切换色彩模式：所有 HEX 不变，联动偏移 / 锁定绝对值按新模式重算

        「先对焦点输入做失焦提交 / 回退」属 UI 职责，须在调用本方法前完成。

        Args:
            mode_key: 目标模式键（非法键或同模式为无操作）
        """
        if mode_key not in MODES or mode_key == self._mode:
            return
        mode = MODES[mode_key]
        base_ch = self.base_channels(mode_key)
        for item in self._items:
            final_ch = self._channels_from_rgb(mode, item.final_rgb)
            if item.is_locked:
                item.absolute = {
                    c.key: _clamp(_round_prec(final_ch[c.key], c.dec), c.min, c.max)
                    for c in mode.channels
                }
                # 锁定项的偏移量无语义，统一为新模式全 0（保证键集合与当前模式一致）
                item.offset = {c.key: 0.0 for c in mode.channels}
            else:
                item.offset = self._offset_from(final_ch, mode, base_ch)
        self._mode = mode_key

    def set_count(self, count: int) -> None:
        """设置配色数量（3-12 钳制）：新增项偏移量全 0，减少时从尾部移除

        Args:
            count: 目标数量（越界自动钳制）
        """
        target = _clamp(int(_round_prec(float(count), 0)), MIN_COUNT, MAX_COUNT)
        while len(self._items) < target:
            item = self._make_item(len(self._items))
            self._items.append(item)
            self._compose_final(item)
        while len(self._items) > target:
            self._items.pop()

    # ---- 内部实现 ----

    @staticmethod
    def _channels_from_rgb(mode: ModeSpec, rgb: tuple[float, float, float]) -> dict[str, float]:
        """浮点 RGB 反算为通道值字典（fromRgb 方向）"""
        values = mode.from_rgb(*rgb)
        return {c.key: float(v) for c, v in zip(mode.channels, values)}

    @staticmethod
    def _channels_to_rgb(mode: ModeSpec, ch: dict[str, float]) -> tuple[float, float, float]:
        """通道值字典合成为浮点 RGB（toRgb 方向）"""
        result = mode.to_rgb(*(ch[c.key] for c in mode.channels))
        return (float(result[0]), float(result[1]), float(result[2]))

    def _item_by_id(self, item_id: int) -> TuningItem | None:
        """按 id 查找条目；不存在返回 None"""
        for item in self._items:
            if item.id == item_id:
                return item
        return None

    def _make_item(self, idx: int) -> TuningItem:
        """创建新配色条目：全联动、偏移量全 0、最终色 = 当前基色"""
        return TuningItem(
            id=idx + 1,
            name=f'配色{_NAME_LIST[idx]}',
            is_locked=False,
            offset={c.key: 0.0 for c in MODES[self._mode].channels},
            absolute=None,
            final_rgb=self._base_rgb,
        )

    def _offset_from(
        self,
        final_ch: dict[str, float],
        mode: ModeSpec,
        base_ch: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """由最终通道值反算联动偏移量（H 走环形最短差，其余截断）"""
        if base_ch is None:
            base_ch = self.base_channels(mode.key)
        offset: dict[str, float] = {}
        for c in mode.channels:
            d = final_ch[c.key] - base_ch[c.key]
            if c.circular:
                d = _shortest_delta(d)
            offset[c.key] = _clamp(_round_prec(d, c.dec), -c.off_max, c.off_max)
        return offset

    def _compose_final(self, item: TuningItem, base_ch: dict[str, float] | None = None) -> None:
        """合成最终颜色写入 item.final_rgb（内部保浮点，HEX 生成时才取整）

        联动：final_通道 = base_通道 + offset_通道（H 环形，其余截断）；
        独立：final_rgb = toRgb(absolute)。
        """
        mode = MODES[self._mode]
        if item.is_locked:
            item.final_rgb = self._channels_to_rgb(mode, item.absolute or {})
            return
        if base_ch is None:
            base_ch = self.base_channels()
        ch: dict[str, float] = {}
        for c in mode.channels:
            v = base_ch[c.key] + item.offset[c.key]
            ch[c.key] = _mod360(v) if c.circular else _clamp(v, c.min, c.max)
        item.final_rgb = self._channels_to_rgb(mode, ch)

    def _recompose_unlocked(self) -> None:
        """基色变化后重算全部联动配色（锁定项不受影响）"""
        base_ch = self.base_channels()
        for item in self._items:
            if not item.is_locked:
                self._compose_final(item, base_ch)


# ==================== 序列化 ====================

def _is_finite_number(v: object) -> bool:
    """判断是否为可用于计算的有限数值（排除 bool / NaN / inf）"""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def to_storage(engine: PaletteTuningEngine) -> dict:
    """将引擎状态导出为可 JSON 序列化的存储结构

    不含 edited（重启后从 base_rgb 反算可接受，仅影响显示细节）。

    Args:
        engine: 调色板引擎

    Returns:
        dict: {'mode': str, 'base_rgb': [r, g, b],
               'items': [{'locked': bool, 'offset': {…}, 'absolute': {…} | None}]}
    """
    return {
        'mode': engine.mode,
        'base_rgb': list(engine.base_rgb),
        'items': [
            {
                'locked': item.is_locked,
                'offset': dict(item.offset),
                'absolute': dict(item.absolute) if item.absolute is not None else None,
            }
            for item in engine.items
        ],
    }


def _parse_storage_base_rgb(raw_rgb: object) -> tuple[float, float, float] | None:
    """解析并校验存储的基色 RGB

    Args:
        raw_rgb: 存储中的 base_rgb 原始值

    Returns:
        tuple[float, float, float] | None: 钳制到 0-255 的浮点 RGB；校验失败返回 None
    """
    if (
        not isinstance(raw_rgb, (list, tuple))
        or len(raw_rgb) != 3
        or not all(_is_finite_number(v) for v in raw_rgb)
    ):
        return None
    return (
        _clamp(float(raw_rgb[0]), 0.0, 255.0),
        _clamp(float(raw_rgb[1]), 0.0, 255.0),
        _clamp(float(raw_rgb[2]), 0.0, 255.0),
    )


def _parse_storage_items(
    raw_items: list,
    mode: ModeSpec,
) -> list[tuple[bool, dict[str, float], dict[str, float] | None]]:
    """解析并校验存储的配色项列表

    Args:
        raw_items: 存储中的 items 原始列表
        mode: 当前模式规格（通道键集合与取值范围的校验依据）

    Returns:
        list: [(locked, offset, absolute), ...]，offset / absolute 值已钳制到合法范围

    Raises:
        ValueError: 配色项结构、通道键或数值类型非法（由调用方统一回退默认态）
    """
    channel_keys = {c.key for c in mode.channels}
    parsed: list[tuple[bool, dict[str, float], dict[str, float] | None]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("配色项类型非法")
        locked = raw.get('locked')
        offset = raw.get('offset')
        if not isinstance(locked, bool) or not isinstance(offset, dict):
            raise ValueError("配色项字段类型非法")
        if set(offset.keys()) != channel_keys:
            raise ValueError(f"偏移通道键与模式 {mode.key} 不符: {sorted(map(str, offset.keys()))}")
        if not all(_is_finite_number(offset[k]) for k in channel_keys):
            raise ValueError("偏移值类型非法")
        absolute: dict[str, float] | None = None
        if locked:
            absolute = raw.get('absolute')
            if not isinstance(absolute, dict) or set(absolute.keys()) != channel_keys:
                raise ValueError("锁定项绝对值缺失或通道键不符")
            if not all(_is_finite_number(absolute[k]) for k in channel_keys):
                raise ValueError("锁定项绝对值类型非法")
            absolute = {
                c.key: _clamp(float(absolute[c.key]), c.min, c.max) for c in mode.channels
            }
        parsed.append((
            locked,
            {c.key: _clamp(float(offset[c.key]), -c.off_max, c.off_max) for c in mode.channels},
            absolute,
        ))
    return parsed


def from_storage(data: dict) -> PaletteTuningEngine:
    """从存储数据重建引擎，重建后全部 final_rgb 重算

    config.json 是用户可手改的外部输入：缺键 / 通道键与当前模式不符 /
    类型非法等校验失败时回退默认态并记录警告日志。

    Args:
        data: to_storage 产出的存储结构；items 为空时可选 'count' 键生效
              （对应默认配置「全联动偏移 0」的持久化形态）

    Returns:
        PaletteTuningEngine: 重建后的引擎
    """

    def fallback(reason: str) -> PaletteTuningEngine:
        logger.warning(f"调色板配置校验失败，回退默认态: {reason}")
        return PaletteTuningEngine()

    if not isinstance(data, dict):
        return fallback(f"数据类型非法: {type(data).__name__}")

    mode_key = data.get('mode')
    if not isinstance(mode_key, str) or mode_key not in MODES:
        return fallback(f"模式非法: {mode_key!r}")

    raw_rgb = data.get('base_rgb')
    base_rgb = _parse_storage_base_rgb(raw_rgb)
    if base_rgb is None:
        return fallback(f"基色 RGB 非法: {raw_rgb!r}")

    raw_items = data.get('items')
    if raw_items is None:
        raw_items = []
    if not isinstance(raw_items, list):
        return fallback("items 类型非法")
    try:
        parsed = _parse_storage_items(raw_items, MODES[mode_key])
    except ValueError as e:
        return fallback(f"配色项校验失败: {e}")
    if parsed and not (MIN_COUNT <= len(parsed) <= MAX_COUNT):
        return fallback(f"配色数量越界: {len(parsed)}")

    engine = PaletteTuningEngine()
    engine._mode = mode_key
    engine._base_rgb = base_rgb
    if parsed:
        engine._items = [
            TuningItem(
                id=i + 1,
                name=f'配色{_NAME_LIST[i]}',
                is_locked=locked,
                offset=offset,
                absolute=absolute,
                final_rgb=base_rgb,
            )
            for i, (locked, offset, absolute) in enumerate(parsed)
        ]
        base_ch = engine.base_channels()
        for item in engine._items:
            engine._compose_final(item, base_ch)
    else:
        # items 为空 = 全联动偏移 0 的持久化形态，count 键仅在此时生效
        count = data.get('count', DEFAULT_COUNT)
        if not _is_finite_number(count):
            logger.warning(f"调色板配置 count 非法，使用默认值 {DEFAULT_COUNT}: {count!r}")
            count = DEFAULT_COUNT
        engine._items = []
        engine.set_count(int(count))
    return engine
