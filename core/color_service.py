"""颜色服务模块

管理颜色提取相关业务逻辑，包括主色调提取、颜色位置查找等。
UI层通过ColorService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
from typing import List, Tuple

# 第三方库导入
from PySide6.QtCore import QObject, QThread, Signal

# 项目模块导入
from .color import extract_dominant_colors, find_dominant_color_positions


class DominantColorExtractor(QThread):
    """主色调提取线程

    在后台线程中执行主色调提取，避免阻塞UI。
    支持取消操作。
    """

    # 信号：提取完成
    extraction_finished = Signal(list, list)  # dominant_colors, positions
    # 信号：提取失败
    extraction_error = Signal(str)  # error_message
    # 信号：提取进度（可选）
    extraction_progress = Signal(int)  # progress_percent

    def __init__(self, image, count: int = 5, parent=None):
        """
        Args:
            image: QImage 对象
            count: 提取颜色数量
            parent: 父对象
        """
        super().__init__(parent)
        self._image = image
        self._count = count
        self._is_cancelled = False

    def cancel(self):
        """请求取消提取"""
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._is_cancelled

    def run(self):
        """在子线程中执行主色调提取"""
        try:
            if self._check_cancelled() or not self._image or self._image.isNull():
                return

            # 提取主色调
            dominant_colors = extract_dominant_colors(self._image, count=self._count)

            if self._check_cancelled():
                return

            if not dominant_colors:
                self.extraction_error.emit("无法从图片中提取主色调")
                return

            # 找到每种主色调在图片中的位置
            positions = find_dominant_color_positions(self._image, dominant_colors)

            if self._check_cancelled():
                return

            # 发送成功信号
            self.extraction_finished.emit(dominant_colors, positions)

        except Exception as e:
            if not self._check_cancelled():
                self.extraction_error.emit(str(e))


class ColorService(QObject):
    """颜色服务，管理颜色提取相关业务逻辑

    职责：
    - 主色调提取
    - 颜色位置查找
    - 提取任务管理

    信号：
        extraction_started: 提取开始
        extraction_progress: 提取进度 (0-100)
        extraction_finished: 提取完成 (dominant_colors, positions)
        extraction_error: 提取错误 (error_message)
    """

    # 信号
    extraction_started = Signal()
    extraction_progress = Signal(int)
    extraction_finished = Signal(list, list)
    extraction_error = Signal(str)

    def __init__(self, parent=None):
        """初始化颜色服务

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._extractor = None

    def extract_dominant_colors(self, image, count: int = 5):
        """开始提取主色调

        异步执行主色调提取，通过信号通知结果。
        如果已有提取任务在进行，会先取消旧任务。

        Args:
            image: QImage 对象
            count: 提取颜色数量 (3-8，默认5)
        """
        # 取消之前的提取
        if self._extractor is not None and self._extractor.isRunning():
            self._extractor.cancel()
            self._extractor = None

        self.extraction_started.emit()

        # 创建并启动提取线程
        self._extractor = DominantColorExtractor(image, count, self)
        self._extractor.extraction_finished.connect(self._on_extraction_finished)
        self._extractor.extraction_error.connect(self.extraction_error)
        self._extractor.finished.connect(self._cleanup_extractor)
        self._extractor.start()

    def cancel_extraction(self):
        """取消当前提取任务"""
        if self._extractor is not None and self._extractor.isRunning():
            self._extractor.cancel()

    def _on_extraction_finished(self, dominant_colors: List[Tuple[int, int, int]],
                                positions: List[Tuple[float, float]]):
        """提取完成处理

        Args:
            dominant_colors: 主色调列表 [(r, g, b), ...]
            positions: 颜色位置列表 [(rel_x, rel_y), ...]
        """
        self.extraction_finished.emit(dominant_colors, positions)

    def _cleanup_extractor(self):
        """清理提取器"""
        if self._extractor is not None:
            self._extractor.deleteLater()
            self._extractor = None
