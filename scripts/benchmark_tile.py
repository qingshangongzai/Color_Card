"""悬浮配色磁贴渲染基准

对指定组数的收藏数据测量「首次显示」耗时与控件数，用于对比两条渲染路径：

- 全量预建基线（懒创建引入前运行一次）
- 懒创建结果（懒创建落地后运行）

在 offscreen 平台运行，不写盘；收藏数据经 ConfigManager 内存注入（不调用 save()）。

运行方式：
    python scripts/benchmark_tile.py --counts 50,100,200 --label full
"""

# 标准库导入
import argparse
import os
import platform
import sys
import time

# offscreen 必须在导入 PySide6 之前设置
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 第三方库导入
from PySide6.QtWidgets import QApplication, QWidget
from qfluentwidgets import Theme, setTheme, setThemeColor

# 项目模块导入
from core import get_config_manager
from tests.favorites_fixture import build_favorites
from ui.palette_tile import FloatingPaletteTile

DEFAULT_COUNTS = (50, 100, 200)
DEFAULT_RUNS = 3


def _measure(count: int, runs: int) -> tuple[float, int, int]:
    """测一组数据：返回（首次显示最小耗时 ms, 组控件数, 总控件数）"""
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

        tile.hide()
        tile.deleteLater()
        QApplication.processEvents()

    return min(durations), group_counts[-1], widget_counts[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description='悬浮配色磁贴渲染基准')
    parser.add_argument(
        '--counts',
        default=','.join(str(count) for count in DEFAULT_COUNTS),
        help='组数，逗号分隔（默认 50,100,200）',
    )
    parser.add_argument('--runs', type=int, default=DEFAULT_RUNS, help='每组数重复次数，取最小值')
    parser.add_argument('--label', default='lazy', help='结果标签，如 lazy / full')
    args = parser.parse_args()

    counts = [int(value) for value in args.counts.split(',') if value.strip()]

    app = QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    setThemeColor('#0078d4')

    print(f'# 悬浮配色磁贴基准（{args.label}）')
    print()
    print(f'- Python: {platform.python_version()}')
    print(f'- 平台: {platform.system()} {platform.release()}')
    print(f'- QT_QPA_PLATFORM: {app.platformName()}')
    print(f'- 每组数重复 {args.runs} 次，取首次显示最小值')
    print()
    print('| 组数 | 首次显示(ms) | 组控件数 | 总控件数 |')
    print('|---|---|---|---|')

    for count in counts:
        duration, group_count, widget_count = _measure(count, args.runs)
        print(f'| {count} | {duration:.1f} | {group_count} | {widget_count} |')


if __name__ == '__main__':
    main()
