"""颜色服务模块

管理颜色提取相关业务逻辑，包括主色调提取、颜色位置查找等。
UI层通过ColorService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
from typing import List, Tuple

# 第三方库导入
from PySide6.QtCore import QObject, QThread, Signal, Qt

# 项目模块导入
from .color import extract_dominant_colors, find_dominant_color_positions
from .logger import get_logger, log_performance


logger = get_logger("color_service")


class DominantColorExtractor(QThread):
    """主色调提取线程

    在后台线程中执行主色调提取，避免阻塞 UI 线程。
    支持取消操作。

    线程安全说明：
    - 所有信号都使用 QueuedConnection，确保跨线程安全
    - QImage 数据在构造时复制，避免主线程修改
    - cancel() 方法设置标志位，不阻塞调用线程
    - 不使用 terminate()，通过标志位优雅退出

    使用示例：
        extractor = DominantColorExtractor(image, count=5, parent=self)
        extractor.extraction_finished.connect(
            self._on_extraction_finished, Qt.ConnectionType.QueuedConnection
        )
        extractor.extraction_error.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection
        )
        extractor.start()

        # 取消提取
        extractor.cancel()

    信号:
        extraction_finished: 提取完成时发射，参数为 (dominant_colors, positions)
        extraction_error: 提取出错时发射，参数为错误信息
        extraction_progress: 提取进度（可选），参数为进度百分比
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

            with log_performance("extract_dominant_colors", {"count": self._count}):
                dominant_colors = extract_dominant_colors(self._image, count=self._count)

            if self._check_cancelled():
                return

            if not dominant_colors:
                logger.error("主色调提取失败: error=无法从图片中提取主色调")
                self.extraction_error.emit("无法从图片中提取主色调")
                return

            positions = find_dominant_color_positions(self._image, dominant_colors)

            if self._check_cancelled():
                return

            self.extraction_finished.emit(dominant_colors, positions)

        except Exception as e:
            if not self._check_cancelled():
                logger.error(f"主色调提取异常: error={str(e)}")
                self.extraction_error.emit(str(e))


class ColorService(QObject):
    """颜色服务，管理颜色提取相关业务逻辑

    职责：
    - 主色调提取
    - 颜色位置查找
    - 提取任务管理

    线程安全说明：
    - 所有信号连接使用 QueuedConnection，确保跨线程安全
    - 提取器线程在构造时复制 QImage，避免主线程修改
    - 服务析构时会等待线程结束，确保资源安全释放
    - 不使用 terminate()，通过 cancel() 优雅停止线程

    使用示例：
        service = ColorService(parent=self)
        service.extraction_finished.connect(
            self._on_extraction_finished, Qt.ConnectionType.QueuedConnection
        )
        service.extraction_error.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection
        )
        service.extract_dominant_colors(image, count=5)

        # 取消提取
        service.cancel_extraction()

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

    def __del__(self):
        """析构函数：确保线程在对象销毁前停止"""
        if self._extractor is not None and self._extractor.isRunning():
            self._extractor.cancel()
            self._extractor.wait(1000)  # 等待最多1秒

    def extract_dominant_colors(self, image, count: int = 5):
        """开始提取主色调

        异步执行主色调提取，通过信号通知结果。
        如果已有提取任务在进行，会先取消旧任务。

        Args:
            image: QImage 对象
            count: 提取颜色数量 (3-8，默认5)
        """
        if self._extractor is not None and self._extractor.isRunning():
            self._extractor.cancel()
            self._extractor = None

        logger.info(f"开始提取主色调: count={count}")
        self.extraction_started.emit()

        self._extractor = DominantColorExtractor(image, count, self)
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
        """提取完成处理

        Args:
            dominant_colors: 主色调列表 [(r, g, b), ...]
            positions: 颜色位置列表 [(rel_x, rel_y), ...]
        """
        logger.info(f"主色调提取完成: 颜色数量={len(dominant_colors)}")
        self.extraction_finished.emit(dominant_colors, positions)

    def _cleanup_extractor(self):
        """清理提取器"""
        if self._extractor is not None:
            self._extractor.deleteLater()
            self._extractor = None
