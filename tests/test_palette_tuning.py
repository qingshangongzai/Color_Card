"""动态色彩微调调色板引擎测试

覆盖范围：H 环形、截断钳制、数量钳制、HEX 解析与往返、
模式切换 HEX 不变与 A→B→A 参数往返、锁定/解锁零跳变、JS 舍入边界、
edited 机制、序列化往返、core.color 浮点重构行为保持。
"""

# 标准库导入
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 第三方库导入
import pytest

# 项目模块导入
from core.color import (  # noqa: E402
    _cmyk_to_rgb_float,
    _hsb_to_rgb_float,
    _hsl_to_rgb_float,
    cmyk_to_rgb,
    hsb_to_rgb,
    hsl_to_rgb,
    lab_to_rgb,
    rgb_to_hsb,
    rgb_to_lab,
)
from core.palette_tuning import (  # noqa: E402
    MODES,
    PaletteTuningEngine,
    _mod360,
    _round_prec,
    _shortest_delta,
    from_storage,
    hex_now,
    parse_hex_input,
    to_storage,
)

MODE_KEYS = list(MODES)  # hsb → hsl → rgb → lab → cmyk
REPRESENTATIVE_HEXES = ['#000000', '#FFFFFF', '#FF0000', '#808080']


# ==================== JS 舍入边界 ====================

class TestRoundPrec:
    """roundPrec 复刻 JS Math.round 远离零舍入，区别于 Python 银行家舍入"""

    @pytest.mark.parametrize('value,expected', [
        (2.5, 3.0),    # Python round(2.5)=2，JS=3
        (0.5, 1.0),
        (-0.5, 0.0),
        (-1.5, -1.0),  # Python round(-1.5)=-2，JS=-1
        (-2.5, -2.0),
        (1.4, 1.0),
        (-1.4, -1.0),
    ])
    def test_half_away_from_zero(self, value, expected):
        assert _round_prec(value, 0) == expected

    def test_lab_dec1(self):
        """LAB a/b 保留 1 位小数，且不触发银行家舍入"""
        assert _round_prec(1.25, 1) == 1.3    # round(1.25, 1) = 1.2
        assert _round_prec(-1.25, 1) == -1.2
        assert _round_prec(12.34, 1) == 12.3


# ==================== 环形与差值归一 ====================

class TestCircular:
    """H 环形归一与最短差（含 ±180 / ±360 边界）"""

    @pytest.mark.parametrize('value,expected', [
        (370, 10), (-10, 350), (360, 0), (-90, 270), (720, 0), (-450, 270),
    ])
    def test_mod360(self, value, expected):
        assert _mod360(value) == expected

    @pytest.mark.parametrize('value,expected', [
        (180, -180), (-180, -180),   # ±180 边界：公式归一到 [-180, 180)
        (190, -170), (-190, 170),
        (350, -10), (10, 10),
        (360, 0), (-360, 0),
    ])
    def test_shortest_delta(self, value, expected):
        assert _shortest_delta(value) == expected


# ==================== HEX 解析 ====================

class TestParseHex:
    """parse_hex_input：#RGB / #RRGGBB / RRGGBB，非法返回 None"""

    @pytest.mark.parametrize('raw,expected', [
        ('#408080', '#408080'),
        ('408080', '#408080'),
        ('#abc', '#AABBCC'),
        ('aBc', '#AABBCC'),
        ('  #ff00aa  ', '#FF00AA'),
        ('#000000', '#000000'),
    ])
    def test_valid(self, raw, expected):
        assert parse_hex_input(raw) == expected

    @pytest.mark.parametrize('raw', [
        '#G12345', '#12345', '', '   ', '#1234567', '12345', None, '#40 808', '##408080',
    ])
    def test_invalid_returns_none(self, raw):
        assert parse_hex_input(raw) is None


# ==================== 引擎默认态 ====================

class TestDefaults:
    """默认态：#408080、6 配色、全联动、HSB、三通道取滑块中点"""

    def test_default_state(self):
        engine = PaletteTuningEngine()
        assert engine.mode == 'hsb'
        assert hex_now(engine.base_rgb) == '#408080'
        assert len(engine.items) == 6
        assert [item.id for item in engine.items] == [1, 2, 3, 4, 5, 6]
        for item in engine.items:
            assert not item.is_locked
            assert item.absolute is None
            assert all(v == 0.0 for v in item.offset.values())
            assert hex_now(item.final_rgb) == '#408080'

    def test_default_base_channels_at_midpoints(self):
        """基色三通道恰为滑块中点（HSB 180/50/50）"""
        engine = PaletteTuningEngine()
        assert engine.base_channels() == {'h': 180.0, 's': 50.0, 'v': 50.0}


# ==================== HEX 应用与往返 ====================

class TestBaseHex:
    @pytest.mark.parametrize('hex_str', REPRESENTATIVE_HEXES + ['#408080', '#010203'])
    def test_hex_round_trip_lossless(self, hex_str):
        """HEX 往返无损：应用后基色 HEX 与输入一致"""
        engine = PaletteTuningEngine()
        assert engine.set_base_hex(hex_str) == hex_str.upper()
        assert hex_now(engine.base_rgb) == hex_str.upper()

    def test_invalid_hex_rejected_and_state_untouched(self):
        engine = PaletteTuningEngine()
        before = engine.base_rgb
        assert engine.set_base_hex('#G12345') is None
        assert engine.set_base_hex('#12345') is None
        assert engine.set_base_hex('') is None
        assert engine.base_rgb == before

    def test_equivalent_hex_keeps_edited(self):
        """等价 HEX 输入保留 edited；颜色变化才作废"""
        engine = PaletteTuningEngine()
        engine.set_base_channel('h', 360.0)
        assert engine.base_channels()['h'] == 360.0
        current = hex_now(engine.base_rgb)
        assert engine.set_base_hex(current) == current
        assert engine.base_channels()['h'] == 360.0      # edited 保留
        engine.set_base_hex('#123456')                    # 颜色变化
        assert engine.base_channels()['h'] != 360.0       # edited 作废，反算


# ==================== edited 机制 ====================

class TestEditedMechanism:
    def test_cmyk_single_channel_edit_keeps_others(self):
        """CMYK 改单通道其余不跳变（反算会强制 min(C,M,Y)=0）"""
        engine = PaletteTuningEngine()
        engine.set_base_hex('#808080')
        engine.switch_mode('cmyk')
        before = engine.base_channels()
        engine.set_base_channel('c', 50.0)
        after = engine.base_channels()
        assert after['c'] == 50.0
        assert after['m'] == before['m']
        assert after['y'] == before['y']
        assert after['k'] == before['k']

    def test_cmyk_two_edits_accumulate(self):
        """连续编辑在同一 edited 组上累积"""
        engine = PaletteTuningEngine()
        engine.set_base_hex('#808080')
        engine.switch_mode('cmyk')
        engine.set_base_channel('c', 50.0)
        engine.set_base_channel('m', 30.0)
        ch = engine.base_channels()
        assert ch['c'] == 50.0
        assert ch['m'] == 30.0

    def test_h_360_not_snapped_back(self):
        """H 拖到 360 不弹回 0（反算必然归 0）"""
        engine = PaletteTuningEngine()
        engine.set_base_channel('h', 360.0)
        assert engine.base_channels()['h'] == 360.0

    def test_edited_invalidated_by_other_mode_edit(self):
        """在其它模式编辑后原 edited 作废（被新模式编辑值取代）"""
        engine = PaletteTuningEngine()
        engine.set_base_channel('h', 360.0)
        engine.switch_mode('rgb')
        engine.set_base_channel('r', 100.0)
        engine.switch_mode('hsb')
        assert engine.base_channels()['h'] != 360.0

    def test_lab_edit_not_recorded(self):
        """LAB 例外：a/b 可能超色域，不记录 edited，显示截断后的真实值"""
        engine = PaletteTuningEngine()
        engine.switch_mode('lab')
        engine.set_base_channel('a', 127.0)
        assert engine._edited is None
        assert engine.base_channels()['a'] != 127.0


# ==================== H 环形合成 ====================

class TestEngineHueRing:
    """H 环形合成：350+20→10、10−20→350、360→0、−90→270"""

    @staticmethod
    def _final_hue(engine: PaletteTuningEngine) -> float:
        return rgb_to_hsb(*engine.items[0].final_rgb)[0]

    def test_offset_wraps_forward(self):
        engine = PaletteTuningEngine()
        engine.set_base_channel('h', 350.0)
        engine.set_param(1, 'h', 20.0)
        assert self._final_hue(engine) == pytest.approx(10.0)

    def test_offset_wraps_backward(self):
        engine = PaletteTuningEngine()
        engine.set_base_channel('h', 10.0)
        engine.set_param(1, 'h', -20.0)
        assert self._final_hue(engine) == pytest.approx(350.0)

    def test_offset_360_is_zero(self):
        engine = PaletteTuningEngine()
        engine.set_base_channel('h', 0.0)
        engine.set_param(1, 'h', 360.0)
        assert self._final_hue(engine) == pytest.approx(0.0)

    def test_negative_offset_wraps(self):
        engine = PaletteTuningEngine()
        engine.set_base_channel('h', 0.0)
        engine.set_param(1, 'h', -90.0)
        assert self._final_hue(engine) == pytest.approx(270.0)


# ==================== 截断钳制 ====================

class TestClampCompose:
    """截断通道合成钳制：−5→0、105→100、300→255、LAB b:200→127"""

    def test_negative_clamps_to_min(self):
        engine = PaletteTuningEngine()
        engine.set_base_channel('s', 0.0)
        engine.set_param(1, 's', -5.0)
        assert rgb_to_hsb(*engine.items[0].final_rgb)[1] == pytest.approx(0.0)

    def test_above_max_clamps(self):
        engine = PaletteTuningEngine()
        engine.set_base_channel('s', 100.0)
        engine.set_param(1, 's', 5.0)
        assert rgb_to_hsb(*engine.items[0].final_rgb)[1] == pytest.approx(100.0)

    def test_rgb_clamps_to_255(self):
        engine = PaletteTuningEngine()
        engine.switch_mode('rgb')
        engine.set_base_channel('r', 255.0)
        engine.set_param(1, 'r', 45.0)
        assert engine.items[0].final_rgb[0] == pytest.approx(255.0)

    def test_lab_absolute_clamps_to_127(self):
        engine = PaletteTuningEngine()
        engine.switch_mode('lab')
        engine.lock_item(1)
        engine.set_param(1, 'b', 200.0)
        assert engine.items[0].absolute['b'] == 127.0

    def test_lab_offset_clamps_to_off_max(self):
        """LAB a/b 偏移上限为 128（非 255）"""
        engine = PaletteTuningEngine()
        engine.switch_mode('lab')
        engine.set_param(1, 'b', 200.0)
        assert engine.items[0].offset['b'] == 128.0

    def test_offset_clamped_to_off_max(self):
        engine = PaletteTuningEngine()
        engine.set_param(1, 's', 150.0)
        assert engine.items[0].offset['s'] == 100.0


# ==================== 数量管理 ====================

class TestCount:
    """数量 3-12 钳制与尾部增删"""

    @pytest.mark.parametrize('raw,expected', [(0, 3), (1, 3), (2, 3), (13, 12), (100, 12), (6, 6)])
    def test_count_clamped(self, raw, expected):
        engine = PaletteTuningEngine()
        engine.set_count(raw)
        assert len(engine.items) == expected

    def test_new_item_unlocked_zero_offset_base_color(self):
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.set_count(8)
        item = engine.items[7]
        assert not item.is_locked
        assert item.absolute is None
        assert all(v == 0.0 for v in item.offset.values())
        assert hex_now(item.final_rgb) == '#336699'

    def test_remove_locked_item_no_compensation(self):
        """减少数量从尾部移除，锁定项独立值一并丢弃、不补偿"""
        engine = PaletteTuningEngine()
        engine.lock_item(6)
        engine.set_count(5)
        assert len(engine.items) == 5
        assert all(not item.is_locked for item in engine.items)

    def test_ids_contiguous_after_shrink_grow(self):
        engine = PaletteTuningEngine()
        engine.set_count(3)
        engine.set_count(6)
        assert [item.id for item in engine.items] == [1, 2, 3, 4, 5, 6]


# ==================== 锁定 / 解锁 ====================

class TestLockUnlock:
    def test_lock_zero_jump(self):
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.set_param(1, 'h', 25.0)
        engine.set_param(1, 's', -10.0)
        before = engine.items[0].final_rgb
        engine.lock_item(1)
        assert engine.items[0].is_locked
        assert engine.items[0].absolute is not None
        assert engine.items[0].final_rgb == before

    def test_unlock_zero_jump_and_offset_recompute(self):
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.set_param(1, 'h', 25.0)
        engine.set_param(1, 's', -10.0)
        before = engine.items[0].final_rgb
        engine.lock_item(1)
        engine.unlock_item(1)
        assert not engine.items[0].is_locked
        assert engine.items[0].absolute is None
        assert engine.items[0].final_rgb == before
        assert engine.items[0].offset['h'] == 25.0
        assert engine.items[0].offset['s'] == -10.0

    def test_lock_unlock_lock_round_trip(self):
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.set_param(1, 'h', 25.0)
        engine.lock_item(1)
        first = dict(engine.items[0].absolute or {})
        engine.unlock_item(1)
        engine.lock_item(1)
        assert engine.items[0].absolute == first

    def test_locked_item_immune_to_base_change(self):
        """锁定项不随基色变化；联动项跟随基色"""
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.lock_item(1)
        locked_hex = hex_now(engine.items[0].final_rgb)
        engine.set_base_hex('#FF0000')
        assert hex_now(engine.items[0].final_rgb) == locked_hex
        assert hex_now(engine.items[1].final_rgb) == '#FF0000'

    def test_lock_unlock_guards(self):
        """重复锁定 / 未锁定解锁均为无操作"""
        engine = PaletteTuningEngine()
        engine.lock_item(1)
        absolute = dict(engine.items[0].absolute or {})
        engine.lock_item(1)
        assert engine.items[0].absolute == absolute
        engine.unlock_item(2)
        engine.unlock_item(2)
        assert not engine.items[1].is_locked

    def test_reset_unlocked_zero_offset_back_to_base(self):
        """联动项重置：偏移归零，颜色回到基色"""
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.set_param(1, 'h', 25.0)
        engine.set_param(1, 's', -10.0)
        engine.reset_item(1)
        assert not engine.items[0].is_locked
        assert all(v == 0.0 for v in engine.items[0].offset.values())
        assert hex_now(engine.items[0].final_rgb) == '#336699'

    def test_reset_locked_keeps_lock_back_to_base(self):
        """锁定项重置：保持锁定，颜色回到基色，之后仍不跟随基色"""
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.set_param(1, 'h', 25.0)
        engine.lock_item(1)
        engine.reset_item(1)
        assert engine.items[0].is_locked
        assert engine.items[0].absolute is not None
        assert hex_now(engine.items[0].final_rgb) == '#336699'
        engine.set_base_hex('#FF0000')
        assert hex_now(engine.items[0].final_rgb) == '#336699'

    def test_reset_unknown_id_noop(self):
        """未知 id 重置为无操作"""
        engine = PaletteTuningEngine()
        before = [hex_now(item.final_rgb) for item in engine.items]
        engine.reset_item(99)
        assert [hex_now(item.final_rgb) for item in engine.items] == before


# ==================== 步进 ====================

class TestStepParam:
    def test_step_offset(self):
        engine = PaletteTuningEngine()
        engine.step_param(1, 's', 1)
        engine.step_param(1, 's', 1)
        engine.step_param(1, 's', -1)
        assert engine.items[0].offset['s'] == 1.0

    def test_step_boundary_no_op(self):
        """到边界无操作（|next − cur| < 1e-9）"""
        engine = PaletteTuningEngine()
        engine.set_param(1, 's', 100.0)
        engine.step_param(1, 's', 1)
        assert engine.items[0].offset['s'] == 100.0

    def test_step_absolute_boundary(self):
        engine = PaletteTuningEngine()
        engine.switch_mode('rgb')
        engine.lock_item(1)
        engine.set_param(1, 'r', 255.0)
        engine.step_param(1, 'r', 1)
        assert engine.items[0].absolute['r'] == 255.0

    def test_step_unknown_item_no_op(self):
        engine = PaletteTuningEngine()
        engine.step_param(999, 's', 1)
        assert engine.items[0].offset['s'] == 0.0


class TestStepBaseChannel:
    def test_step_increments_and_decrements(self):
        """基色通道步进 ±1"""
        engine = PaletteTuningEngine()
        engine.step_base_channel('h', 1)
        engine.step_base_channel('s', -1)
        ch = engine.base_channels()
        assert ch['h'] == 181.0
        assert ch['s'] == 49.0

    def test_step_boundary_no_op(self):
        """基色通道到上下界无操作"""
        engine = PaletteTuningEngine()
        engine.set_base_channel('s', 100.0)
        engine.step_base_channel('s', 1)
        assert engine.base_channels()['s'] == 100.0
        engine.set_base_channel('s', 0.0)
        engine.step_base_channel('s', -1)
        assert engine.base_channels()['s'] == 0.0

    def test_step_recomposes_unlocked_cards(self):
        """基色步进后联动卡片跟随变化"""
        engine = PaletteTuningEngine()
        before = hex_now(engine.items[0].final_rgb)
        engine.step_base_channel('h', 1)
        assert hex_now(engine.items[0].final_rgb) != before


# ==================== 写后重算契约 ====================

class TestRecomposeContract:
    """通道/HEX 写入口重算 final_rgb；switch_mode / lock / unlock 不重算"""

    def test_set_param_recomposes_target_only(self):
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        base_hue = rgb_to_hsb(*engine.base_rgb)[0]
        others = [item.final_rgb for item in engine.items[1:]]
        engine.set_param(1, 'h', 30.0)
        assert [item.final_rgb for item in engine.items[1:]] == others
        expected = base_hue + 30.0
        if expected >= 360:
            expected -= 360
        assert rgb_to_hsb(*engine.items[0].final_rgb)[0] == pytest.approx(expected)

    def test_base_write_recomposes_unlocked_only(self):
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.lock_item(2)
        locked_before = engine.items[1].final_rgb
        engine.set_base_hex('#FF0000')
        assert engine.items[1].final_rgb == locked_before
        assert hex_now(engine.items[0].final_rgb) == '#FF0000'

    def test_switch_lock_unlock_keep_final_rgb(self):
        engine = PaletteTuningEngine()
        engine.set_param(1, 'h', 25.0)
        finals = [item.final_rgb for item in engine.items]
        engine.switch_mode('rgb')
        assert [item.final_rgb for item in engine.items] == finals
        engine.lock_item(1)
        assert [item.final_rgb for item in engine.items] == finals
        engine.unlock_item(1)
        assert [item.final_rgb for item in engine.items] == finals


# ==================== 模式切换 ====================

def _build_nontrivial_state(engine: PaletteTuningEngine, mode_key: str, edit_locked: bool) -> None:
    """构建非平凡状态：1 号有偏移，2 号锁定（可选编辑绝对值）"""
    engine.switch_mode(mode_key)
    for i, c in enumerate(MODES[mode_key].channels):
        engine.set_param(1, c.key, (i + 1) * 7.0)
    engine.lock_item(2)
    if edit_locked:
        for i, c in enumerate(MODES[mode_key].channels):
            engine.set_param(2, c.key, 40.0 + i * 5.0)


def _all_hexes(engine: PaletteTuningEngine) -> list[str]:
    return [hex_now(engine.base_rgb)] + [hex_now(item.final_rgb) for item in engine.items]


class TestModeSwitch:
    @pytest.mark.parametrize('mode_key', MODE_KEYS)
    @pytest.mark.parametrize('hex_str', REPRESENTATIVE_HEXES)
    def test_switch_preserves_all_hex(self, mode_key, hex_str):
        """5 模式 × 代表色（纯黑/纯白/红/中灰）切换后所有 HEX 不变"""
        engine = PaletteTuningEngine()
        engine.set_base_hex(hex_str)
        _build_nontrivial_state(engine, mode_key, edit_locked=True)
        before_hexes = _all_hexes(engine)
        finals = [item.final_rgb for item in engine.items]
        for other in MODE_KEYS:
            if other == mode_key:
                continue
            engine.switch_mode(other)
            assert _all_hexes(engine) == before_hexes, f"切换到 {other} 后 HEX 变化"
        engine.switch_mode(mode_key)
        assert _all_hexes(engine) == before_hexes
        assert [item.final_rgb for item in engine.items] == finals

    @pytest.mark.parametrize('mode_key', ['hsb', 'hsl', 'rgb', 'lab'])
    def test_round_trip_restores_params(self, mode_key):
        """A→B→A 模式往返后 offset / absolute 与切换前一致

        仅覆盖反算无损的模式；CMYK 因通道冗余（反算强制最大通道分量为 0、
        K 吸收差值）偏移必然按颜色重推导，见 test_cmyk_round_trip_rederives_offsets。
        """
        engine = PaletteTuningEngine()
        engine.set_base_hex('#808080')  # 中间灰：偏移量不触界，反算无截断干扰
        _build_nontrivial_state(engine, mode_key, edit_locked=False)
        offset_before = dict(engine.items[0].offset)
        absolute_before = dict(engine.items[1].absolute or {})
        other = next(k for k in MODE_KEYS if k != mode_key)
        engine.switch_mode(other)
        engine.switch_mode(mode_key)
        assert engine.items[0].offset == offset_before
        assert engine.items[1].absolute == absolute_before

    def test_cmyk_round_trip_rederives_offsets(self):
        """CMYK 往返：颜色不变，偏移量按实际颜色重推导（CMYK 通道冗余语义）

        原型同语义：cmykFromRgb 强制最大 RGB 通道对应分量归 0、K 吸收差值，
        故 c 偏移重推导后归 0，其余通道按比例变化。
        """
        engine = PaletteTuningEngine()
        engine.set_base_hex('#808080')
        _build_nontrivial_state(engine, 'cmyk', edit_locked=False)
        before_hexes = _all_hexes(engine)
        other = next(k for k in MODE_KEYS if k != 'cmyk')
        engine.switch_mode(other)
        engine.switch_mode('cmyk')
        assert _all_hexes(engine) == before_hexes
        assert engine.items[0].offset['c'] == 0.0

    def test_switch_mode_guards(self):
        """同模式 / 非法键为无操作"""
        engine = PaletteTuningEngine()
        engine.switch_mode('hsb')
        engine.switch_mode('xxx')
        assert engine.mode == 'hsb'

    def test_switch_rebuilds_channel_keys(self):
        """切换后通道键集合随模式重建（CMYK 4 通道，其余 3 通道）"""
        engine = PaletteTuningEngine()
        engine.switch_mode('cmyk')
        assert set(engine.items[0].offset) == {'c', 'm', 'y', 'k'}
        engine.switch_mode('hsb')
        assert set(engine.items[0].offset) == {'h', 's', 'v'}


# ==================== 序列化 ====================

class TestStorage:
    def test_to_storage_schema(self):
        engine = PaletteTuningEngine()
        engine.lock_item(1)
        data = to_storage(engine)
        assert set(data) == {'mode', 'base_rgb', 'items'}
        assert data['mode'] == 'hsb'
        assert len(data['base_rgb']) == 3
        assert len(data['items']) == 6
        assert set(data['items'][0]) == {'locked', 'offset', 'absolute'}
        assert data['items'][0]['locked'] is True
        assert isinstance(data['items'][0]['absolute'], dict)
        assert data['items'][1]['locked'] is False
        assert data['items'][1]['absolute'] is None

    def test_storage_round_trip_exact_in_native_mode(self):
        """状态与存储模式一致（无跨模式重推导）时：联动项 final_rgb 逐位一致

        锁定项 lock 时按显示精度取整 absolute（原型语义），重建重算允许
        显示精度内的浮点微差。
        """
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.set_param(1, 'h', 30.0)
        engine.set_param(2, 'v', -20.0)
        engine.lock_item(3)
        restored = from_storage(to_storage(engine))
        assert restored.mode == engine.mode
        assert restored.base_rgb == engine.base_rgb
        for src, dst in zip(engine.items, restored.items):
            assert dst.is_locked == src.is_locked
            assert dst.offset == src.offset
            assert dst.absolute == src.absolute
            if src.is_locked:
                assert max(abs(a - b) for a, b in zip(dst.final_rgb, src.final_rgb)) < 2.0
            else:
                assert dst.final_rgb == src.final_rgb

    def test_storage_round_trip_full_state(self):
        """跨模式状态往返：偏移/绝对值逐位一致，颜色在显示精度内一致

        偏移量按显示精度存储（原型语义）；切换模式后偏移按颜色重推导过，
        重建重算的 final_rgb 与原值存在显示精度内的浮点差（RGB ≤ ~1.3）。
        """
        engine = PaletteTuningEngine()
        engine.set_base_hex('#336699')
        engine.set_param(1, 'h', 30.0)
        engine.set_param(2, 'v', -20.0)
        engine.lock_item(3)
        engine.switch_mode('lab')
        engine.set_param(4, 'a', 12.5)
        restored = from_storage(to_storage(engine))
        assert restored.mode == engine.mode
        assert restored.base_rgb == engine.base_rgb
        for src, dst in zip(engine.items, restored.items):
            assert dst.is_locked == src.is_locked
            assert dst.offset == src.offset
            assert dst.absolute == src.absolute
            assert max(abs(a - b) for a, b in zip(dst.final_rgb, src.final_rgb)) < 2.0

    def test_from_storage_count_key_when_items_empty(self):
        """items 为空 = 全联动偏移 0 形态，count 键此时生效"""
        data = {'mode': 'hsb', 'base_rgb': [64.0, 128.0, 128.0], 'items': [], 'count': 9}
        engine = from_storage(data)
        assert len(engine.items) == 9
        assert hex_now(engine.base_rgb) == '#408080'
        assert all(not item.is_locked for item in engine.items)

    def test_from_storage_invalid_count_uses_default(self):
        data = {'mode': 'hsb', 'base_rgb': [64.0, 128.0, 128.0], 'items': [], 'count': 'many'}
        assert len(from_storage(data).items) == 6

    def test_from_storage_invalid_mode_falls_back(self):
        engine = from_storage({'mode': 'xxx', 'base_rgb': [0, 0, 0], 'items': []})
        assert engine.mode == 'hsb'
        assert hex_now(engine.base_rgb) == '#408080'
        assert len(engine.items) == 6

    def test_from_storage_non_dict_falls_back(self):
        engine = from_storage("not a dict")  # type: ignore[arg-type]
        assert engine.mode == 'hsb'
        assert len(engine.items) == 6

    def test_from_storage_missing_items_uses_default_count(self):
        engine = from_storage({'mode': 'hsb', 'base_rgb': [1.0, 2.0, 3.0]})
        assert len(engine.items) == 6

    def test_from_storage_channel_key_mismatch_falls_back(self):
        """通道键与当前模式不符（如以 rgb 键存储却声明 hsb）→ 回退默认态"""
        data = {
            'mode': 'hsb',
            'base_rgb': [1.0, 2.0, 3.0],
            'items': [
                {'locked': False, 'offset': {'r': 1.0, 'g': 2.0, 'b': 3.0}, 'absolute': None}
            ] * 6,
        }
        engine = from_storage(data)
        assert hex_now(engine.base_rgb) == '#408080'

    def test_from_storage_locked_missing_absolute_falls_back(self):
        data = {
            'mode': 'hsb',
            'base_rgb': [1.0, 2.0, 3.0],
            'items': [{'locked': True, 'offset': {'h': 0.0, 's': 0.0, 'v': 0.0}}],
        }
        engine = from_storage(data)
        assert hex_now(engine.base_rgb) == '#408080'

    def test_from_storage_nan_falls_back(self):
        data = {'mode': 'hsb', 'base_rgb': [float('nan'), 2.0, 3.0], 'items': []}
        engine = from_storage(data)
        assert hex_now(engine.base_rgb) == '#408080'

    def test_from_storage_unlocked_absolute_normalized(self):
        """联动项携带的 absolute 为无语义冗余数据，重建时归一为 None"""
        data = {
            'mode': 'hsb',
            'base_rgb': [64.0, 128.0, 128.0],
            'items': [
                {
                    'locked': False,
                    'offset': {'h': 0.0, 's': 0.0, 'v': 0.0},
                    'absolute': {'h': 9.0, 's': 9.0, 'v': 9.0},
                }
            ] * 6,
        }
        engine = from_storage(data)
        assert all(item.absolute is None for item in engine.items)

    def test_from_storage_out_of_range_values_clamped(self):
        """越界数值归一（手改配置容错），不回退"""
        data = {
            'mode': 'rgb',
            'base_rgb': [-5.0, 300.0, 128.0],
            'items': [
                {'locked': False, 'offset': {'r': 999.0, 'g': -999.0, 'b': 0.0}, 'absolute': None}
            ] * 6,
        }
        engine = from_storage(data)
        assert engine.items[0].offset['r'] == 255.0
        assert engine.items[0].offset['g'] == -255.0
        assert engine.base_rgb[0] == 0.0
        assert engine.base_rgb[1] == 255.0


# ==================== core.color 浮点重构行为保持 ====================

class TestColorFloatRefactor:
    """core.color 浮点重构行为保持：公开 *_to_rgb 返回值不变；浮点版返回未取整值"""

    def test_public_values_unchanged(self):
        assert hsb_to_rgb(180, 50, 50) == (64, 128, 128)
        assert hsb_to_rgb(0, 0, 0) == (0, 0, 0)
        assert hsb_to_rgb(0, 100, 100) == (255, 0, 0)
        assert hsl_to_rgb(120, 100, 50) == (0, 255, 0)
        assert cmyk_to_rgb(0, 0, 0, 100) == (0, 0, 0)

    def test_float_version_unrounded(self):
        """浮点版返回未取整值（需求 3.6：仅显示层取整）"""
        r, g, b = _hsb_to_rgb_float(180, 50, 50)
        assert (r, g, b) == (63.75, 127.5, 127.5)

    def test_lab_round_trip_within_tolerance(self):
        r, g, b = lab_to_rgb(*rgb_to_lab(51, 102, 153))
        assert abs(r - 51) <= 1
        assert abs(g - 102) <= 1
        assert abs(b - 153) <= 1

    @pytest.mark.parametrize('c,m,y,k', [(50, 30, 20, 10), (0, 0, 0, 0), (100, 100, 100, 100)])
    def test_cmyk_public_matches_float_rounding(self, c, m, y, k):
        rf, gf, bf = _cmyk_to_rgb_float(c, m, y, k)
        assert cmyk_to_rgb(c, m, y, k) == (round(rf), round(gf), round(bf))

    @pytest.mark.parametrize('h,s,l', [(180, 50, 50), (0, 0, 0), (300, 80, 30)])
    def test_hsl_public_matches_float_rounding(self, h, s, l):
        rf, gf, bf = _hsl_to_rgb_float(h, s, l)
        assert hsl_to_rgb(h, s, l) == (round(rf), round(gf), round(bf))
