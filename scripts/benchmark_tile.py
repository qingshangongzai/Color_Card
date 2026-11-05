"""悬浮配色磁贴渲染基准

分节测量（`--sections` 可单独运行；默认只跑 display / scroll）：

- display：50 / 100 / 200 组首次显示、已建组控件数、总控件数
- expand：单组展开（行视图点开为完整网格）
- scroll：滚动单步与视口渲染耗时（两个 tab、四个位置）
- rebuild：按 k 个变更组重建（`_rebuild_group`）与全量重建的成本对比，给出全量重建阈值
- memory：已建组体数—工作集/提交内存/视口渲染曲线，校验回收阈值

在 offscreen 平台运行，不写盘；收藏数据经 ConfigManager 内存注入（不调用 save()）。

运行方式：
    python scripts/benchmark_tile.py --counts 50,100,200 --runs 3
    python scripts/benchmark_tile.py --sections display,expand,scroll,rebuild,memory
    python scripts/benchmark_tile.py --sections display --counts 200 --runs 1
"""

# 标准库导入
import argparse
import ctypes
import gc
import os
import platform
import sys
import time
from collections.abc import Callable
from ctypes import wintypes

# offscreen 必须在导入 PySide6 之前设置
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 第三方库导入
from PySide6.QtWidgets import QApplication, QScrollBar, QWidget
from qfluentwidgets import Theme, setTheme, setThemeColor

# 项目模块导入
from core import get_config_manager
from tests.favorites_fixture import build_favorites
from ui.palette_tile import (
    FORM_ROW,
    ROUTE_ALL,
    ROUTE_COMMON,
    FloatingPaletteTile,
)

DEFAULT_COUNTS = (50, 100, 200)
DEFAULT_RUNS = 3
DEFAULT_SECTIONS = ('display', 'scroll')

SCROLL_SAMPLE_RATIOS = (0.25, 0.5, 0.75, 1.0)
REBUILD_COUNTS = (1, 5, 10, 50, 200)
MEMORY_BUILT_COUNTS = (10, 20, 40, 80, 120, 200)
RENDER_SAMPLES = 10

# 阈值判定预算：offscreen 单帧渲染 16.7ms（60Hz）；已建组体提交内存增量 10MB
FRAME_BUDGET_MS = 16.7
MEMORY_BUDGET_MB = 10.0
RECYCLE_MAX = 40
RECYCLE_MIN = 10


class _ProcessMemoryCounters(ctypes.Structure):
    """PROCESS_MEMORY_COUNTERS 结构体，读取工作集与提交内存"""

    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
    ]


def _memory_counters() -> _ProcessMemoryCounters | None:
    """读取当前进程内存计数器；非 Windows 或读取失败时返回 None"""
    if sys.platform != 'win32':
        return None
    gc.collect()
    QApplication.processEvents()
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
    get_info = ctypes.windll.kernel32.K32GetProcessMemoryInfo
    get_info.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    get_info.restype = wintypes.BOOL
    ok = get_info(
        ctypes.windll.kernel32.GetCurrentProcess(),
        ctypes.byref(counters),
        counters.cb,
    )
    return counters if ok else None


def _process_working_set_mb() -> float | None:
    """当前进程工作集（MB）；不可读时返回 None"""
    counters = _memory_counters()
    if counters is None:
        return None
    return counters.WorkingSetSize / (1024 * 1024)


def _process_private_mb() -> float | None:
    """当前进程提交内存（MB，PagefileUsage）；不可读时返回 None"""
    counters = _memory_counters()
    if counters is None:
        return None
    return counters.PagefileUsage / (1024 * 1024)


def _new_tile(favorites: list[dict]) -> FloatingPaletteTile:
    """注入收藏、创建并显示磁贴"""
    get_config_manager().set_favorites(favorites)
    tile = FloatingPaletteTile()
    tile.show()
    QApplication.processEvents()
    return tile


def _dispose_tile(tile: FloatingPaletteTile) -> None:
    """关闭并销毁磁贴，让下一轮从干净状态开始"""
    tile.hide()
    tile.deleteLater()
    QApplication.processEvents()


def _timed_ms(callback: Callable[[], None]) -> float:
    """执行回调并等待事件循环，返回耗时（ms）"""
    start = time.perf_counter()
    callback()
    QApplication.processEvents()
    return (time.perf_counter() - start) * 1000


def _render_ms(tile: FloatingPaletteTile, samples: int = RENDER_SAMPLES) -> float:
    """强制绘制视口若干次，返回平均渲染耗时（ms）"""
    viewport = tile._scroll.viewport()
    start = time.perf_counter()
    for _ in range(samples):
        viewport.grab()
    return (time.perf_counter() - start) * 1000 / samples


def _memory_text(value: float | None) -> str:
    """内存列输出；不可读时显示 N/A"""
    return 'N/A' if value is None else f'{value:.1f}'


def _measure_display(count: int, runs: int) -> tuple[float, int, int]:
    """测首次显示：返回（最小耗时 ms, 组控件数, 总控件数）"""
    durations: list[float] = []
    group_counts: list[int] = []
    widget_counts: list[int] = []

    for _ in range(runs):
        favorites = build_favorites(count)
        get_config_manager().set_favorites(favorites)

        tile = FloatingPaletteTile()
        start = time.perf_counter()
        tile.show()
        QApplication.processEvents()
        durations.append((time.perf_counter() - start) * 1000)

        group_counts.append(len(tile._group_widgets))
        widget_counts.append(len(tile.findChildren(QWidget)))

        _dispose_tile(tile)

    return min(durations), group_counts[-1], widget_counts[-1]


def _first_row_slot(tile: FloatingPaletteTile):
    """取当前视口内第一个已建的行视图"""
    window = tile._visible_window(tile._slot_spans())
    for slot in window:
        if slot.form == FORM_ROW and slot.content is not None:
            return slot
    return None


def _measure_expand(count: int, runs: int) -> float:
    """测单组展开：行点击后到完整网格建成的耗时（ms，取最小值）"""
    tile = _new_tile(build_favorites(count))
    tile._segmented.setCurrentItem(ROUTE_ALL)
    QApplication.processEvents()

    durations: list[float] = []
    for _ in range(runs):
        tile._row_open_ids.clear()
        tile._collapsed_ids.clear()
        tile._refresh_visibility(reset_scroll=True)
        tile._sync_viewport()
        QApplication.processEvents()

        slot = _first_row_slot(tile)
        if slot is None:
            raise RuntimeError('视口内没有可展开的行视图')
        favorite_id = slot.model.favorite_id

        def expand_row(fid: str = favorite_id) -> None:
            tile._on_row_clicked(fid)

        durations.append(_timed_ms(expand_row))

    _dispose_tile(tile)
    return min(durations)


def _measure_scroll(count: int) -> list[tuple[str, str, int, int, int, int, float, float]]:
    """测滚动：每个 tab 在 25% / 50% / 75% / 100% 与回顶处取样"""
    favorites = build_favorites(count)
    rows: list[tuple[str, str, int, int, int, int, float, float]] = []

    for route, route_text in ((ROUTE_COMMON, '常用'), (ROUTE_ALL, '全部')):
        tile = _new_tile(favorites)
        tile._segmented.setCurrentItem(route)
        QApplication.processEvents()
        tile._sync_viewport()
        bar = tile._scroll.verticalScrollBar()

        for ratio in SCROLL_SAMPLE_RATIOS:
            target = int(bar.maximum() * ratio)

            def scroll_to(target_value: int = target, scroll_bar: QScrollBar = bar) -> None:
                scroll_bar.setValue(target_value)

            step_ms = _timed_ms(scroll_to)
            render_ms = _render_ms(tile)
            rows.append((
                route_text,
                f'{int(ratio * 100)}%',
                bar.value(),
                bar.maximum(),
                len(tile._group_widgets),
                len(tile.findChildren(QWidget)),
                step_ms,
                render_ms,
            ))

        def scroll_to_top(scroll_bar: QScrollBar = bar) -> None:
            scroll_bar.setValue(0)

        step_ms = _timed_ms(scroll_to_top)
        rows.append((
            route_text,
            '回顶',
            bar.value(),
            bar.maximum(),
            len(tile._group_widgets),
            len(tile.findChildren(QWidget)),
            step_ms,
            _render_ms(tile),
        ))
        _dispose_tile(tile)

    return rows


def _measure_rebuild(
    count: int, runs: int
) -> tuple[float, list[tuple[int, float, float, float]]]:
    """测全量重建与 k 个变更组的增量重建成本

    Returns:
        tuple[float, list[tuple[int, float, float, float]]]:
            全量重建最小值 ms、[(k, 增量 ms, 每组均摊 ms, 增量/全量)]
    """
    favorites = build_favorites(count)
    tile = _new_tile(favorites)
    # 放大回收上限，隔离 LRU 回收对重建成本的干扰
    tile._max_live_groups = len(favorites) + len(MEMORY_BUILT_COUNTS)

    full_times: list[float] = []
    for _ in range(runs):
        full_times.append(
            _timed_ms(lambda: tile._apply_favorites(favorites, reset_scroll=False))
        )

    rows: list[tuple[int, float, float, float]] = []
    for k in REBUILD_COUNTS:
        incremental: list[float] = []
        for _ in range(runs):
            tile._apply_favorites(favorites, reset_scroll=False)
            for slot in tile._slots[:k]:
                tile._ensure_built(slot)
            QApplication.processEvents()

            def rebuild_groups(group_count: int = k) -> None:
                for index in range(group_count):
                    tile._rebuild_group(dict(favorites[index], name=f'基准重建-{index}'))
                # 批量重建后只同步一次视口，避免逐组重复的全表布局
                tile._sync_viewport()

            incremental.append(_timed_ms(rebuild_groups))
        best = min(incremental)
        rows.append((k, best, best / k, best / min(full_times)))

    _dispose_tile(tile)
    return min(full_times), rows


def _measure_memory(
    count: int,
) -> tuple[int, list[tuple[int, float | None, float | None, float | None, float | None, float]]]:
    """测已建组体数—工作集/提交内存/视口渲染曲线

    每个采样档独立创建磁贴，避免滚动测渲染时额外建组污染下一档；
    表格记录实际已建组数，不用名义 target。

    Returns:
        tuple[int, list[tuple[int, float | None, float | None, float | None, float | None, float]]]:
            基线已建组数、[(实际已建组数, 工作集增量 MB, 每组 MB, 提交增量 MB, 每组 MB, 视口渲染 ms)]
    """
    favorites = build_favorites(count)
    baseline_built = 0
    rows: list[tuple[int, float | None, float | None, float | None, float | None, float]] = []

    for target in MEMORY_BUILT_COUNTS:
        tile = _new_tile(favorites)
        tile._max_live_groups = len(favorites) + len(MEMORY_BUILT_COUNTS)
        tile._segmented.setCurrentItem(ROUTE_COMMON)
        QApplication.processEvents()
        tile._sync_viewport()

        baseline_working = _process_working_set_mb()
        baseline_private = _process_private_mb()
        current_baseline_built = len(tile._group_widgets)
        if baseline_built == 0:
            baseline_built = current_baseline_built

        for slot in tile._slots[:target]:
            tile._ensure_built(slot)
        QApplication.processEvents()

        actual_built = len(tile._group_widgets)
        extra_groups = max(actual_built - current_baseline_built, 1)
        working = _process_working_set_mb()
        private = _process_private_mb()
        working_delta = None
        working_per_group = None
        private_delta = None
        private_per_group = None
        if baseline_working is not None and working is not None:
            working_delta = working - baseline_working
            working_per_group = working_delta / extra_groups
        if baseline_private is not None and private is not None:
            private_delta = private - baseline_private
            private_per_group = private_delta / extra_groups

        rows.append((actual_built, working_delta, working_per_group, private_delta,
                     private_per_group, _render_ms(tile)))
        _dispose_tile(tile)

    return baseline_built, rows


def _rebuild_threshold(full_ms: float, rows: list[tuple[int, float, float, float]]) -> int | None:
    """第一个「增量重建 ≥ 全量重建」的 k；未出现返回 None"""
    for k, incremental, _, _ in rows:
        if incremental >= full_ms:
            return k
    return None


def _recycle_threshold(
    rows: list[tuple[int, float | None, float | None, float | None, float | None, float]],
) -> int | None:
    """按帧预算与提交内存预算筛可用采样点，再套 10–40 的缓存上下限"""
    eligible: list[int] = []
    for built, _, _, private_delta, _, render_ms in rows:
        if private_delta is None:
            return None
        if private_delta <= MEMORY_BUDGET_MB and render_ms <= FRAME_BUDGET_MS:
            eligible.append(built)
    if not eligible:
        return RECYCLE_MIN
    return max(min(max(eligible), RECYCLE_MAX), RECYCLE_MIN)


def _print_header(args: argparse.Namespace, sections: list[str]) -> None:
    print(f'# 悬浮配色磁贴基准（{args.label}）')
    print()
    print(f'- Python: {platform.python_version()}')
    print(f'- 平台: {platform.system()} {platform.release()}')
    print(f'- QT_QPA_PLATFORM: {QApplication.platformName()}')
    print(f'- 分节: {", ".join(sections)}')
    print(f'- 每组数重复 {args.runs} 次，耗时取最小值')
    print()


def _print_display(counts: list[int], runs: int) -> None:
    print('## 首次显示')
    print()
    print('| 组数 | 首次显示(ms) | 已建组控件数 | 总控件数 |')
    print('|---|---|---|---|')
    for count in counts:
        duration, group_count, widget_count = _measure_display(count, runs)
        print(f'| {count} | {duration:.1f} | {group_count} | {widget_count} |')
    print()


def _print_expand(count: int, runs: int) -> None:
    print(f'## 单组展开（{count} 组）')
    print()
    print('| 操作 | 最小耗时(ms) |')
    print('|---|---|')
    print(f'| 行视图点开为完整网格 | {_measure_expand(count, runs):.1f} |')
    print()


def _print_scroll(count: int) -> None:
    print(f'## 滚动（{count} 组）')
    print()
    print('| tab | 位置 | value | maximum | 已建组控件 | 总控件 | 单步(ms) | 视口渲染(ms) |')
    print('|---|---|---|---|---|---|---|---|')
    for row in _measure_scroll(count):
        route, ratio, value, maximum, built, widgets, step_ms, render_ms = row
        print(f'| {route} | {ratio} | {value} | {maximum} | {built} | {widgets} | '
              f'{step_ms:.2f} | {render_ms:.2f} |')
    print()


def _print_rebuild(count: int, runs: int) -> None:
    full_ms, rows = _measure_rebuild(count, runs)
    print(f'## 按组重建（{count} 组）')
    print()
    print(f'全量重建（`_apply_favorites(..., reset_scroll=False)`）最小耗时：{full_ms:.1f} ms')
    print()
    print('| 已建变更组数 k | 增量重建(ms) | 每组均摊(ms) | 增量/全量 |')
    print('|---|---|---|---|')
    for k, incremental, per_group, ratio in rows:
        print(f'| {k} | {incremental:.1f} | {per_group:.2f} | {ratio:.2f} |')
    print()
    threshold = _rebuild_threshold(full_ms, rows)
    if threshold is None:
        print(f'- 全量重建阈值：≥{REBUILD_COUNTS[-1]} 个已建变更组'
              '（采样范围内增量始终低于全量）')
    else:
        print(f'- 全量重建阈值：{threshold} 个已建变更组（此后增量重建已不优于全量重建）')
    print()


def _print_memory(count: int) -> None:
    baseline_built, rows = _measure_memory(count)
    print(f'## 已建组体—内存/渲染（{count} 组，基线已建 {baseline_built} 组）')
    print()
    print('| 已建组体数 | 工作集增量(MB) | 每组(MB) | 提交增量(MB) | 每组(MB) | 视口渲染(ms) |')
    print('|---|---|---|---|---|---|')
    for built, working, working_per, private, private_per, render_ms in rows:
        print(f'| {built} | {_memory_text(working)} | {_memory_text(working_per)} | '
              f'{_memory_text(private)} | {_memory_text(private_per)} | {render_ms:.2f} |')
    print()
    threshold = _recycle_threshold(rows)
    if threshold is None:
        print('- 回收阈值：无法推导（进程内存不可读）')
    else:
        print(f'- 回收阈值：{threshold} 个已建组体'
              f'（帧预算 {FRAME_BUDGET_MS}ms、提交内存预算 {MEMORY_BUDGET_MB}MB、缓存上限 {RECYCLE_MAX}）')
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description='悬浮配色磁贴渲染基准')
    parser.add_argument(
        '--counts',
        default=','.join(str(count) for count in DEFAULT_COUNTS),
        help='组数，逗号分隔（默认 50,100,200）',
    )
    parser.add_argument('--runs', type=int, default=DEFAULT_RUNS, help='每组数重复次数，取最小值')
    parser.add_argument('--label', default='lazy', help='结果标签，如 lazy')
    parser.add_argument(
        '--sections',
        default=','.join(DEFAULT_SECTIONS),
        help=f'分节，逗号分隔（默认 {",".join(DEFAULT_SECTIONS)}）',
    )
    args = parser.parse_args()

    counts = [int(value) for value in args.counts.split(',') if value.strip()]
    sections = [value.strip() for value in args.sections.split(',') if value.strip()]
    scenario_count = max(counts)

    _app = QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    setThemeColor('#0078d4')
    _print_header(args, sections)

    if 'display' in sections:
        _print_display(counts, args.runs)
    if 'expand' in sections:
        _print_expand(scenario_count, args.runs)
    if 'scroll' in sections:
        _print_scroll(scenario_count)
    if 'rebuild' in sections:
        _print_rebuild(scenario_count, args.runs)
    if 'memory' in sections:
        _print_memory(scenario_count)


if __name__ == '__main__':
    main()
