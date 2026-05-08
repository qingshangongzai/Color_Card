"""启动性能测试脚本

分析 Color Card 应用的启动耗时，找出主要瓶颈。

运行方式：
    python tests/test_startup_performance.py
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field


# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@dataclass
class TimingResult:
    """计时结果"""
    name: str
    duration_ms: float
    children: list['TimingResult'] = field(default_factory=list)
    
    def print_tree(self, indent: int = 0, threshold_ms: float = 0):
        """打印树形结构"""
        prefix = "  " * indent
        marker = "├─ " if indent > 0 else ""
        if self.duration_ms >= threshold_ms:
            print(f"{prefix}{marker}{self.name}: {self.duration_ms:.1f}ms")
        for child in self.children:
            child.print_tree(indent + 1, threshold_ms)


class StartupProfiler:
    """启动性能分析器"""
    
    def __init__(self):
        self.results: list[TimingResult] = []
        self._current_result: TimingResult | None = None
        self._result_stack: list[TimingResult] = []
    
    @contextmanager
    def measure(self, name: str):
        """测量代码块耗时"""
        result = TimingResult(name=name, duration_ms=0)
        
        # 压栈
        if self._result_stack:
            self._result_stack[-1].children.append(result)
        else:
            self.results.append(result)
        
        self._result_stack.append(result)
        
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            result.duration_ms = (end - start) * 1000
            
            # 出栈
            self._result_stack.pop()
    
    def print_report(self, threshold_ms: float = 5):
        """打印报告"""
        total = sum(r.duration_ms for r in self.results)
        
        print("\n" + "=" * 60)
        print("启动性能分析报告")
        print("=" * 60)
        print(f"\n总耗时: {total:.1f}ms\n")
        
        print("详细耗时（仅显示 > {:.0f}ms 的项目）:\n".format(threshold_ms))
        
        for result in self.results:
            result.print_tree(threshold_ms=threshold_ms)
        
        print("\n" + "-" * 60)
        print("主要瓶颈分析:")
        print("-" * 60)
        
        # 收集所有结果并排序
        all_results = self._flatten_results(self.results)
        all_results.sort(key=lambda x: x.duration_ms, reverse=True)
        
        # 显示前10个耗时最长的项目
        for i, result in enumerate(all_results[:10], 1):
            percentage = (result.duration_ms / total) * 100 if total > 0 else 0
            print(f"{i:2}. {result.name}: {result.duration_ms:.1f}ms ({percentage:.1f}%)")
    
    def _flatten_results(self, results: list[TimingResult]) -> list[TimingResult]:
        """扁平化结果列表"""
        flat = []
        for result in results:
            flat.append(result)
            flat.extend(self._flatten_results(result.children))
        return flat


def test_startup_performance():
    """测试启动性能"""
    profiler = StartupProfiler()
    
    print("开始启动性能测试...\n")
    
    # 1. 基础环境设置
    with profiler.measure("基础环境设置"):
        # Windows AppUserModelID
        if os.name == 'nt':
            import ctypes
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    'HXiaoStudio.ColorCard.1.0.0'
                )
            except Exception:
                pass
    
    # 2. PySide6 基础模块
    with profiler.measure("PySide6 基础模块导入"):
        with profiler.measure("PySide6.QtCore"):
            from PySide6.QtCore import Qt, QTimer, QSize
        with profiler.measure("PySide6.QtGui"):
            from PySide6.QtGui import QColor, QIcon, QPixmap
        with profiler.measure("PySide6.QtWidgets"):
            from PySide6.QtWidgets import QApplication, QSplashScreen
    
    # 3. 创建 QApplication
    with profiler.measure("创建 QApplication"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        os.environ['QT_IMAGEIO_MAXALLOC'] = '1024'
        app = QApplication(sys.argv)
    
    # 4. 日志系统
    with profiler.measure("日志系统初始化"):
        from core import get_logger_manager, get_logger
        logger_manager = get_logger_manager()
        logger_manager.initialize()
        logger = get_logger("startup_test")
    
    # 5. PySide6 扩展模块
    with profiler.measure("PySide6 扩展模块导入"):
        with profiler.measure("qInstallMessageHandler"):
            from PySide6.QtCore import qInstallMessageHandler
        with profiler.measure("qfluentwidgets"):
            from qfluentwidgets import setTheme, setThemeColor, Theme
    
    # 6. Core 模块
    with profiler.measure("Core 模块导入"):
        with profiler.measure("get_config_manager"):
            from core import get_config_manager
        with profiler.measure("utils 模块"):
            from utils import fix_windows_taskbar_icon_for_window, load_icon_universal, get_locale_manager, force_window_to_front
        with profiler.measure("ui 模块"):
            from ui import MainWindow
    
    # 7. 配置加载
    with profiler.measure("配置加载"):
        config_manager = get_config_manager()
        config_manager.load()
    
    # 8. 语言设置
    with profiler.measure("语言设置"):
        locale_manager = get_locale_manager()
        language_setting = config_manager.get('settings.language', 'ZW_JT')
        locale_manager.load_language(language_setting)
    
    # 9. 主题设置
    with profiler.measure("主题设置"):
        theme_setting = config_manager.get('settings.theme', 'auto')
        if theme_setting == 'light':
            setTheme(Theme.LIGHT)
        elif theme_setting == 'dark':
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.AUTO)
        setThemeColor('#0078d4')
    
    # 10. 主窗口创建
    with profiler.measure("主窗口创建"):
        window = MainWindow()
    
    # 11. 各界面创建耗时分析
    print("\n分析各界面创建耗时...")
    
    # 获取界面创建信息
    interface_info = []
    for interface_id, interface in window._interfaces.items():
        # 尝试获取界面的创建耗时（如果有记录的话）
        interface_info.append(f"  - {interface_id}: {type(interface).__name__}")
    
    if interface_info:
        print("已创建的界面:")
        for info in interface_info:
            print(info)
    
    # 打印报告
    profiler.print_report(threshold_ms=1)
    
    # 额外分析：模块导入耗时
    print("\n" + "-" * 60)
    print("模块导入耗时测试（独立运行）:")
    print("-" * 60)
    
    # 重新测试各模块导入耗时（在干净环境下）
    module_times = []
    
    modules_to_test = [
        ("numpy", "import numpy"),
        ("PIL", "from PIL import Image"),
        ("PySide6.QtWidgets", "from PySide6.QtWidgets import QWidget"),
        ("qfluentwidgets", "from qfluentwidgets import FluentWindow"),
        ("core.config", "from core.config import get_config_manager"),
        ("core.color", "from core.color import get_color_info"),
        ("core.color_data", "from core.color_data import ColorSourceRegistry"),
        ("core.histogram_service", "from core.histogram_service import HistogramService"),
        ("core.luminance_service", "from core.luminance_service import LuminanceService"),
        ("ui.cards", "from ui.cards import ColorCard"),
        ("ui.histograms", "from ui.histograms import RGBHistogramWidget"),
        ("ui.color_wheel", "from ui.color_wheel import HSBColorWheel"),
    ]
    
    for module_name, import_stmt in modules_to_test:
        # 清理已导入的模块
        module_parts = module_name.split('.')
        for i in range(len(module_parts), 0, -1):
            full_name = '.'.join(module_parts[:i])
            if full_name in sys.modules:
                del sys.modules[full_name]
        
        start = time.perf_counter()
        try:
            exec(import_stmt)
            end = time.perf_counter()
            duration = (end - start) * 1000
            module_times.append((module_name, duration))
        except Exception as e:
            module_times.append((module_name, -1))
    
    # 按耗时排序
    module_times.sort(key=lambda x: x[1], reverse=True)
    
    for name, duration in module_times:
        if duration >= 0:
            print(f"  {name}: {duration:.1f}ms")
        else:
            print(f"  {name}: 导入失败")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return app, window


if __name__ == '__main__':
    app, window = test_startup_performance()
    
    # 不显示窗口，直接退出
    sys.exit(0)
