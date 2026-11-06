"""DPI 取色保真检查（真机）

在当前显示缩放档位下验证磁贴色块经屏幕合成后的实际像素与标称 HEX 是否一致，
读数等效第三方吸管；并输出色块边缘 0-4 逻辑像素的偏差剖面，检验
「吸管采样距边 ≥ 2px」准则在各缩放档是否仍然充分。

与 scripts/benchmark_tile.py 不同，本脚本必须在真实屏幕上运行（主动移除
offscreen 平台变量），显示真实窗口后用 GetPixel 读取桌面合成像素；收藏数据
经 ConfigManager 内存注入且禁用 save()，不写盘，进程退出即丢弃。

运行方式（每次更改 Windows 显示缩放后重跑一档，建议 100% / 125% / 150% / 200%）：
    python scripts/dpi_fidelity_check.py
    python scripts/dpi_fidelity_check.py --screen 1   # 指定第二台显示器
    python scripts/dpi_fidelity_check.py --manual     # 采样后保留窗口，供吸管人工复核
"""

# 标准库导入
import argparse
import ctypes
import ctypes.wintypes
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

# 真机脚本：必须在导入 PySide6 之前移除 offscreen 平台设置
os.environ.pop('QT_QPA_PLATFORM', None)

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 第三方库导入
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

# 项目模块导入
from core import get_config_manager
from ui.palette_tile import (
    SCREEN_MARGIN,
    ColorBlock,
    FloatingPaletteTile,
)
from utils import set_window_topmost

# 测试收藏：3 组 × 3 色，覆盖极端值、三原色、圆整边界灰与任意中间调
TEST_GROUPS: list[tuple[str, tuple[str, str, str]]] = [
    ('DPI取色-一', ('#000000', '#FF0000', '#A8BFA3')),
    ('DPI取色-二', ('#FFFFFF', '#00FF00', '#7F7F7F')),
    ('DPI取色-三', ('#0000FF', '#808080', '#1E2B3C')),
]

# 每条边向内采样的逻辑像素偏移；前 2 档为边缘区（仅登记现象），其余为验收区
EDGE_OFFSETS = (0, 1, 2, 3, 4)
SIDES = ('左', '右', '上', '下')
CLR_INVALID = 0xFFFFFFFF


class _Point(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


@dataclass
class _SampleSummary:
    """逐块采样的汇总结果"""

    failures: list[str]
    block_count: int = 0
    total: int = 0
    exact_interior: int = 0
    exact_all: int = 0
    edge_max_diff: int = 0


def _enable_per_monitor_dpi_awareness() -> None:
    """进程级 Per-Monitor V2 感知，防止系统虚拟化坐标导致采样错位"""
    try:
        user32 = ctypes.windll.user32
        context = ctypes.c_void_p(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        if user32.SetProcessDpiAwarenessContext(context):
            return
        user32.SetProcessDPIAware()
    except AttributeError:
        pass


class _ScreenReader:
    """GetPixel 读取桌面合成后的物理像素，与吸管读数等效"""

    def __init__(self) -> None:
        self._dc = ctypes.windll.user32.GetDC(None)

    def read(self, x: int, y: int) -> tuple[int, int, int]:
        """返回指定物理像素的 RGB；COLORREF 布局为 0x00BBGGRR"""
        color = ctypes.windll.gdi32.GetPixel(self._dc, x, y) & 0xFFFFFFFF
        if color == CLR_INVALID:
            return (-1, -1, -1)
        return (color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF)

    def close(self) -> None:
        if self._dc:
            ctypes.windll.user32.ReleaseDC(None, self._dc)
            self._dc = 0


def _client_origin_physical(hwnd: int) -> tuple[int, int]:
    """窗口客户区左上角的物理屏幕坐标（无边框窗口无非客户区偏移）"""
    origin = _Point(0, 0)
    ctypes.windll.user32.ClientToScreen(
        ctypes.wintypes.HWND(hwnd), ctypes.byref(origin)
    )
    return origin.x, origin.y


def _to_physical(value: float, dpr: float) -> int:
    """逻辑像素 → 物理像素；与 Windows 的像素映射一致按 floor(x + 0.5) 取整"""
    return int(value * dpr + 0.5)


def _map_physical(
    origin: tuple[int, int], dpr: float, point: QPoint
) -> tuple[int, int]:
    """磁贴局部逻辑坐标 → 物理屏幕坐标"""
    return (
        origin[0] + _to_physical(point.x(), dpr),
        origin[1] + _to_physical(point.y(), dpr),
    )


def _channel_diff(
    sampled: tuple[int, int, int], target: tuple[int, int, int]
) -> int:
    """采样值与标称值的最大通道差"""
    return max(abs(a - b) for a, b in zip(sampled, target))


def _build_test_favorites() -> list[dict[str, Any]]:
    """构造 3 组 9 色的钉选测试收藏，结构与应用内收藏一致"""
    favorites: list[dict[str, Any]] = []
    for index, (name, hexes) in enumerate(TEST_GROUPS):
        swatches: list[dict[str, Any]] = []
        for hex_value in hexes:
            color = QColor(hex_value)
            swatches.append({
                'hex': hex_value,
                'rgb': (color.red(), color.green(), color.blue()),
            })
        favorites.append({
            'id': f'dpi-test-{index}',
            'name': name,
            'colors': swatches,
            'created_at': '2026-01-01T09:00:00',
            'source': 'dpi-check',
            'pinned': True,
        })
    return favorites


def _noop_save(_config: dict[str, Any] | None = None) -> None:
    """替换 ConfigManager.save：脚本进程内禁用写盘，防止覆盖真实配置"""


def _collect_blocks(tile: FloatingPaletteTile) -> list[tuple[str, ColorBlock]]:
    """按显示顺序收集已建组内的全部色块（常用 tab 默认全为网格形态）"""
    blocks: list[tuple[str, ColorBlock]] = []
    for slot in tile._slots:
        content = slot.content
        swatches = getattr(content, 'swatches', None)
        if not swatches:
            continue
        for card in swatches:
            block = card.findChild(ColorBlock)
            if block is not None:
                blocks.append((card._hex, block))
    return blocks


def _sample_points(
    tile: FloatingPaletteTile, block: ColorBlock
) -> list[tuple[str, int | None, QPoint]]:
    """色块中心与四边向内采样点（磁贴局部坐标）；中心点无偏移概念，记 None"""
    width, height = block.width(), block.height()
    middle_y, middle_x = height // 2, width // 2
    points: list[tuple[str, int | None, QPoint]] = [
        ('内部', None, block.mapTo(tile, QPoint(middle_x, middle_y))),
    ]
    for offset in EDGE_OFFSETS:
        points.append(('左', offset, block.mapTo(tile, QPoint(offset, middle_y))))
        points.append(('右', offset, block.mapTo(tile, QPoint(width - 1 - offset, middle_y))))
        points.append(('上', offset, block.mapTo(tile, QPoint(middle_x, offset))))
        points.append(('下', offset, block.mapTo(tile, QPoint(middle_x, height - 1 - offset))))
    return points


def _sample_block(
    reader: _ScreenReader,
    origin: tuple[int, int],
    dpr: float,
    tile: FloatingPaletteTile,
    block: ColorBlock,
    target_rgb: tuple[int, int, int],
) -> tuple[int, dict[str, dict[int, int]]]:
    """采样单个色块，返回（内部偏差，四边各偏移的偏差表）"""
    interior_diff = -1
    by_side: dict[str, dict[int, int]] = {side: {} for side in SIDES}
    for side, offset, point in _sample_points(tile, block):
        px, py = _map_physical(origin, dpr, point)
        diff = _channel_diff(reader.read(px, py), target_rgb)
        if offset is None:
            interior_diff = diff
        else:
            by_side[side][offset] = diff
    return interior_diff, by_side


def _run_sampling(
    tile: FloatingPaletteTile,
    reader: _ScreenReader,
    origin: tuple[int, int],
    dpr: float,
) -> _SampleSummary:
    """逐块采样并打印偏差行，返回汇总结果"""
    summary = _SampleSummary(failures=[])
    acceptance_offsets = EDGE_OFFSETS[2:]
    print(f'== 采样比对（DPR={dpr:g}，diff = 与标称 HEX 的最大通道差） ==')
    for hex_value, block in _collect_blocks(tile):
        summary.block_count += 1
        nominal = QColor(hex_value)
        target_rgb = (nominal.red(), nominal.green(), nominal.blue())
        interior_diff, by_side = _sample_block(
            reader, origin, dpr, tile, block, target_rgb
        )

        summary.total += 1
        if interior_diff == 0:
            summary.exact_interior += 1
        if interior_diff == 0 and all(
            d == 0 for side_diffs in by_side.values() for d in side_diffs.values()
        ):
            summary.exact_all += 1
        # 验收区 = 内部 + 四边距边 ≥ 2px 的采样，由 EDGE_OFFSETS 派生而非硬编码索引
        acceptance_zone = [interior_diff] + [
            by_side[side][offset]
            for side in SIDES
            for offset in acceptance_offsets
        ]
        if any(d != 0 for d in acceptance_zone):
            summary.failures.append(hex_value)
        summary.edge_max_diff = max(
            summary.edge_max_diff,
            max(d for side_diffs in by_side.values() for d in side_diffs.values()),
        )

        sides = '  '.join(
            f"{side}[{' '.join(str(by_side[side][o]) for o in EDGE_OFFSETS)}]"
            for side in SIDES
        )
        print(
            f'  {hex_value} '
            f'块{_to_physical(block.width(), dpr)}x{_to_physical(block.height(), dpr)}物理px '
            f'内部diff={interior_diff}  {sides}'
        )
    return summary


def _print_environment(app: QApplication, tile: FloatingPaletteTile) -> None:
    """打印屏幕、窗口与高度标定信息，便于跨缩放档对比"""
    print('== 环境 ==')
    for index, screen in enumerate(app.screens()):
        ratio = screen.devicePixelRatio()
        print(
            f'  显示器[{index}] {screen.name()} '
            f'逻辑 {screen.geometry().width()}x{screen.geometry().height()} '
            f'DPR={ratio:g}（缩放≈{ratio * 100:.0f}%） '
            f'逻辑DPI={screen.logicalDotsPerInch():.0f}'
        )
    handle = tile.windowHandle()
    print(
        f'  磁贴所在 DPR={handle.devicePixelRatio():g} '
        f'逻辑尺寸 {tile.width()}x{tile.height()}'
    )
    print(
        f'  高度标定：SwatchCard={tile._card_height}px '
        f'GroupRow={tile._row_height}px（逻辑值，应不随 DPR 变化）'
    )


def _print_manual_coords(
    tile: FloatingPaletteTile, origin: tuple[int, int], dpr: float
) -> None:
    """人工吸管复核：打印各色块中心的物理屏幕坐标并等待确认"""
    print('== 人工吸管复核 ==')
    print('  各色块中心的物理屏幕坐标（吸管读数应等于标称 HEX）：')
    for hex_value, block in _collect_blocks(tile):
        center = block.mapTo(tile, QPoint(block.width() // 2, block.height() // 2))
        px, py = _map_physical(origin, dpr, center)
        print(f'    {hex_value}  ({px}, {py})')
    input('  核对完成后按回车退出...')


def _setup_tile(app: QApplication, screen_index: int) -> FloatingPaletteTile:
    """注入测试收藏、显示磁贴，按需移到指定显示器并置顶，等待合成稳定"""
    config = get_config_manager()
    config.set_favorites(_build_test_favorites())
    config.save = _noop_save  # type: ignore[assignment]

    tile = FloatingPaletteTile()
    tile.show()
    app.processEvents()

    screens = app.screens()
    if screen_index != 0:
        # showEvent 固定摆到主屏右下，副屏在此之后移动
        target = screens[screen_index]
        tile.windowHandle().setScreen(target)
        geometry = target.availableGeometry()
        tile.move(
            geometry.right() - tile.width() - SCREEN_MARGIN,
            geometry.bottom() - tile.height() - SCREEN_MARGIN,
        )
    set_window_topmost(tile, True)
    tile.raise_()
    for _ in range(5):
        app.processEvents()
    time.sleep(0.5)  # 等待 DWM 合成稳定
    app.processEvents()
    return tile


def main() -> int:
    parser = argparse.ArgumentParser(description='DPI 取色保真检查（真机）')
    parser.add_argument('--screen', type=int, default=0, help='目标显示器序号（默认 0）')
    parser.add_argument(
        '--manual', action='store_true', help='采样后保留窗口，打印物理坐标供吸管复核'
    )
    args = parser.parse_args()

    _enable_per_monitor_dpi_awareness()

    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)

    screens = app.screens()
    screen_index = max(0, min(args.screen, len(screens) - 1))
    if args.screen != screen_index:
        print(f'警告：--screen {args.screen} 越界，改用 {screen_index}')

    tile = _setup_tile(app, screen_index)
    _print_environment(app, tile)

    dpr = tile.windowHandle().devicePixelRatio()
    origin = _client_origin_physical(int(tile.winId()))
    reader = _ScreenReader()
    try:
        summary = _run_sampling(tile, reader, origin, dpr)
    finally:
        reader.close()

    print('== 结论 ==')
    print(
        f'  色块数 {summary.block_count}；内部采样精确 {summary.exact_interior}/{summary.total}；'
        f'全采样精确 {summary.exact_all}/{summary.total}；'
        f'边缘区最大偏差 {summary.edge_max_diff}'
    )
    if summary.failures:
        print(f'  判定：FAIL——距边 ≥2px 区域与标称不一致：{", ".join(summary.failures)}')
    else:
        print('  判定：PASS——距边 ≥2px 采样全部等于标称 HEX')

    if args.manual and summary.block_count:
        _print_manual_coords(tile, origin, dpr)
    return 1 if summary.failures else 0


if __name__ == '__main__':
    sys.exit(main())
