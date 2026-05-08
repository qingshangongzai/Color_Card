"""颜色服务模块

管理颜色提取相关业务逻辑，包括主色调提取、颜色位置查找等。
UI层通过ColorService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
from typing import List, Optional, Tuple

# 第三方库导入
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Qt

# 项目模块导入
from .color import extract_dominant_colors, find_dominant_color_positions
from .logger import get_logger, log_performance


logger = get_logger("color_service")


class DominantColorExtractor(QThread):
    """主色调提取线程"""

    extraction_finished = Signal(list, list)
    extraction_error = Signal(str)
    extraction_progress = Signal(int)

    def __init__(self, image, count: int = 5, original_pixels: Optional[np.ndarray] = None,
                 parent=None):
        """
        Args:
            image: QImage 对象
            count: 提取颜色数量
            original_pixels: 原始色彩空间像素数组 (H,W,3)
            parent: 父对象
        """
        super().__init__(parent)
        self._image = image
        self._count = count
        self._original_pixels = original_pixels
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

            with log_performance("extract_dominant_colors", {"count": self._count}):
                dominant_colors = extract_dominant_colors(
                    self._image, count=self._count, original_pixels=self._original_pixels
                )

            if not dominant_colors:
                logger.error("主色调提取失败: error=无法从图片中提取主色调")
                self.extraction_error.emit("无法从图片中提取主色调")
                return

            positions = find_dominant_color_positions(
                self._image, dominant_colors, original_pixels=self._original_pixels
            )

            if self._check_cancelled():
                return

            self.extraction_finished.emit(dominant_colors, positions)

        except (RuntimeError, ValueError, TypeError) as e:
            if not self._check_cancelled():
                logger.error(f"主色调提取异常: error={str(e)}")
                self.extraction_error.emit(str(e))


class ColorService(QObject):
    """颜色服务，管理颜色提取相关业务逻辑"""

    extraction_started = Signal()
    extraction_progress = Signal(int)
    extraction_finished = Signal(list, list)
    extraction_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._extractor = None

    def __del__(self):
        """析构函数：确保线程在对象销毁前停止"""
        if self._extractor is not None and self._extractor.isRunning():
            self._extractor.cancel()
            self._extractor.wait(1000)

    def extract_dominant_colors(self, image, count: int = 5,
                                original_pixels: Optional[np.ndarray] = None):
        """开始提取主色调

        Args:
            image: QImage 对象
            count: 提取颜色数量 (3-8，默认5)
            original_pixels: 原始色彩空间像素数组 (H,W,3)
        """
        if self._extractor is not None and self._extractor.isRunning():
            self._extractor.cancel()
            self._extractor = None

        logger.info(f"开始提取主色调: count={count}")
        self.extraction_started.emit()

        self._extractor = DominantColorExtractor(
            image, count, original_pixels, self
        )
        self._extractor.extraction_finished.connect(
            self._on_extraction_finished, Qt.ConnectionType.QueuedConnection
        )
        self._extractor.extraction_error.connect(
            self.extraction_error, Qt.ConnectionType.QueuedConnection
        )
        self._extractor.finished.connect(
            self._cleanup_extractor, Qt.ConnectionType.QueuedConnection
        )
        self._extractor.start()

    def cancel_extraction(self):
        """取消当前提取任务"""
        if self._extractor is not None and self._extractor.isRunning():
            self._extractor.cancel()
            logger.debug("提取任务已取消")

    def _on_extraction_finished(self, dominant_colors: List[Tuple[int, int, int]],
                                positions: List[Tuple[float, float]]):
        """提取完成处理"""
        logger.info(f"主色调提取完成: 颜色数量={len(dominant_colors)}")
        self.extraction_finished.emit(dominant_colors, positions)

    def _cleanup_extractor(self):
        """清理提取器"""
        if self._extractor is not None:
            self._extractor.deleteLater()
            self._extractor = None
