"""明度服务模块

管理明度计算相关业务逻辑，包括Zone分析、亮度分布统计、高亮区域计算等。
UI层通过LuminanceService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
from typing import Dict, List, Optional, Tuple, Any

# 第三方库导入
from PySide6.QtCore import QObject, QThread, Signal, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

# 项目模块导入
from .color import get_luminance, get_zone, ZONE_WIDTH
from .logger import get_logger, log_performance

logger = get_logger("luminance_service")


class LuminanceCalculator(QThread):
    """明度计算线程

    在后台线程中执行明度分布计算，避免阻塞 UI 线程。
    支持取消操作。

    线程安全说明：
    - 所有信号都使用 QueuedConnection，确保跨线程安全
    - QImage 数据在构造时复制，避免主线程修改
    - cancel() 方法设置标志位，不阻塞调用线程
    - 不使用 terminate()，通过标志位优雅退出

    使用示例：
        calculator = LuminanceCalculator(image, parent=self)
        calculator.calculation_finished.connect(
            self._on_finished, Qt.ConnectionType.QueuedConnection
        )
        calculator.calculation_error.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection
        )
        calculator.start()

        # 取消计算
        calculator.cancel()

    信号:
        calculation_finished: 计算完成时发射，参数为结果字典
        calculation_error: 计算出错时发射，参数为错误信息
    """

    # 信号：计算完成
    calculation_finished = Signal(dict)
    # 信号：计算失败
    calculation_error = Signal(str)

    def __init__(self, image: QImage, parent=None):
        """初始化计算器

        Args:
            image: QImage 对象
            parent: 父对象
        """
        super().__init__(parent)
        # 复制 QImage 数据，避免主线程修改导致的问题
        self._image = image.copy() if image and not image.isNull() else None
        self._is_cancelled = False

    def cancel(self):
        """请求取消计算"""
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._is_cancelled

    def run(self):
        """在子线程中执行明度计算"""
        try:
            if self._check_cancelled() or not self._image or self._image.isNull():
                return

            with log_performance("calculate_luminance_distribution", {
                "width": self._image.width(),
                "height": self._image.height()
            }):
                distribution = self._calculate_distribution()

            if self._check_cancelled():
                return

            result = {
                'distribution': distribution,
                'total_pixels': self._image.width() * self._image.height()
            }
            self.calculation_finished.emit(result)

        except Exception as e:
            if not self._check_cancelled():
                logger.error(f"明度计算失败: {e}", exc_info=True)
                self.calculation_error.emit(str(e))

    def _calculate_distribution(self) -> List[int]:
        """计算明度分布

        Returns:
            list: 每个Zone的像素数量 (Zone 0-7)
        """
        width = self._image.width()
        height = self._image.height()

        # 初始化Zone计数 (Zone 0-7)
        distribution = [0] * 8

        # 采样步长（性能优化）
        sample_step = 4

        for y in range(0, height, sample_step):
            if self._check_cancelled():
                return distribution

            for x in range(0, width, sample_step):
                color = self._image.pixelColor(x, y)
                luminance = get_luminance(color.red(), color.green(), color.blue())
                zone_index = luminance // 32
                zone_index = min(zone_index, 7)  # 确保不越界
                distribution[zone_index] += 1

        return distribution


class LuminanceService(QObject):
    """明度服务，管理明度计算相关业务逻辑

    职责：
    - 明度计算和 Zone 分析
    - 亮度分布统计
    - 高亮区域计算

    线程安全说明：
    - 所有信号连接使用 QueuedConnection，确保跨线程安全
    - 计算器线程在构造时复制 QImage，避免主线程修改
    - 服务析构时会等待线程结束，确保资源安全释放
    - 不使用 terminate()，通过 cancel() 优雅停止线程

    使用示例：
        service = LuminanceService(parent=self)
        service.calculation_finished.connect(
            self._on_calculation_finished, Qt.ConnectionType.QueuedConnection
        )
        service.calculation_error.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection
        )
        service.calculate_luminance_zones(image)

        # 取消计算
        service.cancel_calculation()

    信号：
        calculation_started: 计算开始
        calculation_finished: 计算完成 (result_dict)
        calculation_error: 计算错误 (error_message)
    """

    # 信号
    calculation_started = Signal()
    calculation_finished = Signal(dict)
    calculation_error = Signal(str)

    def __init__(self, parent=None):
        """初始化明度服务

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._calculator: Optional[LuminanceCalculator] = None
        
        self._pending_cleanup: List[LuminanceCalculator] = []
        self._cleanup_timer: Optional[QTimer] = None

    def __del__(self):
        """析构函数：确保线程在对象销毁前停止"""
        if self._calculator is not None and self._calculator.isRunning():
            self._calculator.cancel()
            self._calculator.wait()
        
        for calculator in self._pending_cleanup:
            if calculator.isRunning():
                calculator.wait()

    def calculate_luminance_zones(self, image: QImage) -> None:
        """开始计算明度Zone分布

        异步执行明度计算，通过信号通知结果。
        如果已有计算任务在进行，会先取消旧任务。

        Args:
            image: QImage 对象
        """
        if self._calculator is not None and self._calculator.isRunning():
            try:
                self._calculator.calculation_finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self._calculator.calculation_error.disconnect()
            except (TypeError, RuntimeError):
                pass
            
            self._calculator.cancel()
            if self._calculator.isRunning():
                self._pending_cleanup.append(self._calculator)
                self._start_cleanup_timer()
            self._calculator = None

        self.calculation_started.emit()

        # 创建并启动计算线程
        self._calculator = LuminanceCalculator(image, self)
        self._calculator.calculation_finished.connect(
            self._on_calculation_finished, Qt.ConnectionType.QueuedConnection
        )
        self._calculator.calculation_error.connect(
            self.calculation_error, Qt.ConnectionType.QueuedConnection
        )
        self._calculator.finished.connect(
            self._cleanup_calculator, Qt.ConnectionType.QueuedConnection
        )
        self._calculator.start()

    def cancel_calculation(self) -> None:
        """取消当前计算任务"""
        if self._calculator is not None and self._calculator.isRunning():
            self._calculator.cancel()
            if self._calculator.isRunning():
                self._pending_cleanup.append(self._calculator)
                self._start_cleanup_timer()
            self._calculator = None

    def _start_cleanup_timer(self) -> None:
        """启动清理定时器"""
        if self._cleanup_timer is None:
            self._cleanup_timer = QTimer(self)
            self._cleanup_timer.timeout.connect(self._cleanup_pending_threads)
        
        if not self._cleanup_timer.isActive():
            self._cleanup_timer.start(500)

    def _cleanup_pending_threads(self) -> None:
        """清理已结束的线程"""
        still_running = []
        for calculator in self._pending_cleanup:
            if calculator.isRunning():
                still_running.append(calculator)
        
        self._pending_cleanup = still_running
        
        if not self._pending_cleanup:
            self._cleanup_timer.stop()

    def get_zone_at_position(self, image: QImage, x: int, y: int) -> str:
        """获取指定位置的Zone编号

        Args:
            image: QImage 对象
            x: 像素X坐标
            y: 像素Y坐标

        Returns:
            str: Zone编号 (如 "0-1", "1-2" 等)
        """
        if image is None or image.isNull():
            return "0-1"

        # 边界检查
        x = max(0, min(x, image.width() - 1))
        y = max(0, min(y, image.height() - 1))

        color = image.pixelColor(x, y)
        luminance = get_luminance(color.red(), color.green(), color.blue())
        return get_zone(luminance)

    def get_zone_distribution(self, image: QImage) -> List[int]:
        """获取明度分布统计

        Args:
            image: QImage 对象

        Returns:
            list: 每个Zone的像素数量 (Zone 0-7)
        """
        if image is None or image.isNull():
            return [0] * 8

        width = image.width()
        height = image.height()

        with log_performance("get_zone_distribution", {
            "width": width,
            "height": height
        }):
            distribution = [0] * 8
            sample_step = 4

            for y in range(0, height, sample_step):
                for x in range(0, width, sample_step):
                    color = image.pixelColor(x, y)
                    luminance = get_luminance(color.red(), color.green(), color.blue())
                    zone_index = luminance // 32
                    zone_index = min(zone_index, 7)
                    distribution[zone_index] += 1

        return distribution

    def generate_zone_highlight_pixmap(
        self,
        image: QImage,
        zone: int,
        canvas_size: Tuple[int, int],
        display_rect: Tuple[int, int, int, int],
        zone_color: QColor
    ) -> Optional[QPixmap]:
        """生成Zone高亮遮罩图

        Args:
            image: 原始图片
            zone: Zone编号 (0-8)
            canvas_size: 画布尺寸 (width, height)
            display_rect: 图片显示区域 (x, y, w, h)
            zone_color: 高亮颜色

        Returns:
            QPixmap: 高亮遮罩图，如果失败则返回None
        """
        if image is None or image.isNull():
            return None

        if not (0 <= zone <= 8):
            return None

        canvas_width, canvas_height = canvas_size
        disp_x, disp_y, disp_w, disp_h = display_rect

        with log_performance("generate_zone_highlight_pixmap", {
            "zone": zone,
            "display_size": f"{disp_w}x{disp_h}"
        }):
            highlight_pixmap = QPixmap(canvas_width, canvas_height)
            highlight_pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(highlight_pixmap)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            min_lum = int(zone * ZONE_WIDTH)
            max_lum = int((zone + 1) * ZONE_WIDTH) - 1

            scale_x = image.width() / disp_w
            scale_y = image.height() / disp_h
            sample_step = 4

            for dy in range(0, disp_h, sample_step):
                for dx in range(0, disp_w, sample_step):
                    img_x = int(dx * scale_x)
                    img_y = int(dy * scale_y)

                    img_x = min(img_x, image.width() - 1)
                    img_y = min(img_y, image.height() - 1)

                    color = image.pixelColor(img_x, img_y)
                    luminance = get_luminance(color.red(), color.green(), color.blue())

                    if min_lum <= luminance <= max_lum:
                        painter.fillRect(
                            disp_x + dx,
                            disp_y + dy,
                            sample_step,
                            sample_step,
                            zone_color
                        )

            painter.end()

        return highlight_pixmap

    def _on_calculation_finished(self, result: Dict[str, Any]):
        """计算完成处理

        Args:
            result: 计算结果字典
        """
        self.calculation_finished.emit(result)

    def _cleanup_calculator(self):
        """清理计算器"""
        if self._calculator is not None:
            self._calculator.deleteLater()
            self._calculator = None
