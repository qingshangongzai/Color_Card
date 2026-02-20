# 标准库导入
from typing import List, Optional, Tuple

# 第三方库导入
from PySide6.QtCore import QObject, QThread, Signal, QTimer, Qt
from PySide6.QtGui import QImage

# 项目模块导入
from .color import calculate_histogram, calculate_rgb_histogram
from .histogram_cache import get_histogram_cache, generate_image_fingerprint


class HistogramCalculator(QThread):
    """后台直方图计算线程

    在子线程中执行直方图计算，避免阻塞UI线程。
    支持明度直方图、RGB直方图、色相直方图计算。

    信号:
        finished: 计算完成时发射，参数为计算结果
        error: 计算出错时发射，参数为错误信息
    """

    finished = Signal(object)  # 计算完成信号，参数根据计算类型不同
    error = Signal(str)        # 错误信号

    def __init__(self, image: QImage, calc_type: str = "luminance", sample_step: int = 4):
        """初始化直方图计算线程

        Args:
            image: QImage 对象
            calc_type: 计算类型，可选 "luminance", "rgb", "hue"
            sample_step: 采样步长，每隔N个像素采样一次
        """
        super().__init__()
        # 复制图像数据，避免线程访问父对象的图像时被销毁
        self._image = image.copy() if image and not image.isNull() else None
        self._calc_type = calc_type
        self._sample_step = sample_step
        self._is_cancelled = False

    def cancel(self) -> None:
        """请求取消计算"""
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._is_cancelled

    def run(self) -> None:
        """在子线程中执行计算"""
        try:
            if self._check_cancelled() or self._image is None or self._image.isNull():
                return

            if self._calc_type == "luminance":
                result = calculate_histogram(self._image, self._sample_step)
                if not self._check_cancelled():
                    self.finished.emit(result)

            elif self._calc_type == "rgb":
                result = calculate_rgb_histogram(self._image, self._sample_step)
                if not self._check_cancelled():
                    self.finished.emit(result)

            elif self._calc_type == "hue":
                result = self._calculate_hue_histogram()
                if not self._check_cancelled():
                    self.finished.emit(result)

        except Exception as e:
            if not self._check_cancelled():
                self.error.emit(str(e))

    def _calculate_hue_histogram(self) -> List[int]:
        """计算色相直方图

        Returns:
            list: 长度为360的色相分布列表
        """
        import colorsys

        histogram = [0] * 360
        width = self._image.width()
        height = self._image.height()

        for y in range(0, height, self._sample_step):
            if self._check_cancelled():
                return histogram
            for x in range(0, width, self._sample_step):
                color = self._image.pixelColor(x, y)
                r = color.red() / 255.0
                g = color.green() / 255.0
                b = color.blue() / 255.0
                h, s, v = colorsys.rgb_to_hsv(r, g, b)

                # 排除黑白灰（饱和度<10% 或 亮度<10%）
                if s > 0.1 and v > 0.1:
                    hue = int(h * 360) % 360
                    histogram[hue] += 1

        return histogram


class HistogramService(QObject):
    """直方图计算服务

    管理直方图计算任务生命周期，提供异步计算接口。
    支持取消机制、延迟计算和缓存复用。

    信号:
        luminance_histogram_ready: 明度直方图计算完成
        rgb_histogram_ready: RGB直方图计算完成，参数为 (r_hist, g_hist, b_hist)
        hue_histogram_ready: 色相直方图计算完成
        error: 计算出错时发射
    """

    luminance_histogram_ready = Signal(list)
    rgb_histogram_ready = Signal(list, list, list)  # r_hist, g_hist, b_hist
    hue_histogram_ready = Signal(list)
    error = Signal(str)

    def __init__(self, parent=None, use_cache: bool = True):
        """初始化直方图服务

        Args:
            parent: 父对象
            use_cache: 是否使用缓存（默认True）
        """
        super().__init__(parent)
        self._luminance_calculator: Optional[HistogramCalculator] = None
        self._rgb_calculator: Optional[HistogramCalculator] = None
        self._hue_calculator: Optional[HistogramCalculator] = None
        self._pending_image: Optional[QImage] = None
        self._delay_timer: Optional[QTimer] = None
        self._use_cache = use_cache
        self._current_image_key: str = ""

    def _get_sample_step(self, image: QImage) -> int:
        """根据图片大小确定采样步长

        Args:
            image: QImage 对象

        Returns:
            int: 采样步长
        """
        width = image.width()
        height = image.height()
        pixel_count = width * height

        # 大图片使用更大的采样步长，但保证最低采样率约4%
        if pixel_count > 20000000:  # > 20MP
            return 6
        elif pixel_count > 8000000:  # > 8MP
            return 5
        elif pixel_count > 4000000:  # > 4MP
            return 4
        elif pixel_count > 1000000:  # > 1MP
            return 3
        else:
            return 2

    def calculate_luminance_async(self, image: QImage, delay_ms: int = 100) -> None:
        """异步计算明度直方图

        Args:
            image: QImage 对象
            delay_ms: 延迟计算时间（毫秒），默认500ms
        """
        self._pending_image = image

        # 取消之前的计算
        self._cancel_luminance_calculator()

        # 生成图片指纹
        self._current_image_key = generate_image_fingerprint(image)

        # 尝试从缓存获取
        if self._use_cache:
            cache = get_histogram_cache()
            cached = cache.get(self._current_image_key, "luminance")
            if cached is not None:
                self.luminance_histogram_ready.emit(cached)
                return

        # 使用延迟计算
        if self._delay_timer is None:
            self._delay_timer = QTimer(self)
            self._delay_timer.setSingleShot(True)
            self._delay_timer.timeout.connect(self._start_luminance_calculation)

        self._delay_timer.start(delay_ms)

    def _start_luminance_calculation(self) -> None:
        """开始明度直方图计算"""
        if self._pending_image is None or self._pending_image.isNull():
            return

        sample_step = self._get_sample_step(self._pending_image)

        # 安全地停止并清理旧线程
        self._safe_stop_calculator(self._luminance_calculator)
        self._luminance_calculator = None

        self._luminance_calculator = HistogramCalculator(
            self._pending_image, "luminance", sample_step
        )
        # 使用 QueuedConnection 确保信号在接收者线程中处理
        self._luminance_calculator.finished.connect(
            self._on_luminance_finished, Qt.ConnectionType.QueuedConnection
        )
        self._luminance_calculator.error.connect(
            self.error, Qt.ConnectionType.QueuedConnection
        )
        self._luminance_calculator.start()

    def _on_luminance_finished(self, histogram: List[int]) -> None:
        """明度直方图计算完成回调"""
        # 检查服务是否还有效（没有被销毁）
        if self._luminance_calculator is None:
            return

        # 存入缓存
        if self._use_cache and self._current_image_key:
            cache = get_histogram_cache()
            cache.set(self._current_image_key, "luminance", histogram)

        self.luminance_histogram_ready.emit(histogram)
        self._safe_stop_calculator(self._luminance_calculator)
        self._luminance_calculator = None

    def calculate_rgb_async(self, image: QImage, delay_ms: int = 100) -> None:
        """异步计算RGB直方图

        Args:
            image: QImage 对象
            delay_ms: 延迟计算时间（毫秒），默认500ms
        """
        self._pending_image = image

        # 取消之前的计算
        self._cancel_rgb_calculator()

        # 生成图片指纹
        self._current_image_key = generate_image_fingerprint(image)

        # 尝试从缓存获取
        if self._use_cache:
            cache = get_histogram_cache()
            cached = cache.get(self._current_image_key, "rgb")
            if cached is not None:
                self.rgb_histogram_ready.emit(cached[0], cached[1], cached[2])
                return

        # 使用延迟计算
        if self._delay_timer is None:
            self._delay_timer = QTimer(self)
            self._delay_timer.setSingleShot(True)
            self._delay_timer.timeout.connect(self._start_rgb_calculation)

        self._delay_timer.start(delay_ms)

    def _start_rgb_calculation(self) -> None:
        """开始RGB直方图计算"""
        if self._pending_image is None or self._pending_image.isNull():
            return

        sample_step = self._get_sample_step(self._pending_image)

        # 安全地停止并清理旧线程
        self._safe_stop_calculator(self._rgb_calculator)
        self._rgb_calculator = None

        self._rgb_calculator = HistogramCalculator(
            self._pending_image, "rgb", sample_step
        )
        self._rgb_calculator.finished.connect(
            self._on_rgb_finished, Qt.ConnectionType.QueuedConnection
        )
        self._rgb_calculator.error.connect(
            self.error, Qt.ConnectionType.QueuedConnection
        )
        self._rgb_calculator.start()

    def _on_rgb_finished(self, result: Tuple[List[int], List[int], List[int]]) -> None:
        """RGB直方图计算完成回调"""
        if self._rgb_calculator is None:
            return
        r_hist, g_hist, b_hist = result

        # 存入缓存
        if self._use_cache and self._current_image_key:
            cache = get_histogram_cache()
            cache.set(self._current_image_key, "rgb", [r_hist, g_hist, b_hist])

        self.rgb_histogram_ready.emit(r_hist, g_hist, b_hist)
        self._safe_stop_calculator(self._rgb_calculator)
        self._rgb_calculator = None

    def calculate_hue_async(self, image: QImage, delay_ms: int = 100) -> None:
        """异步计算色相直方图

        Args:
            image: QImage 对象
            delay_ms: 延迟计算时间（毫秒），默认500ms
        """
        self._pending_image = image

        # 取消之前的计算
        self._cancel_hue_calculator()

        # 生成图片指纹
        self._current_image_key = generate_image_fingerprint(image)

        # 尝试从缓存获取
        if self._use_cache:
            cache = get_histogram_cache()
            cached = cache.get(self._current_image_key, "hue")
            if cached is not None:
                self.hue_histogram_ready.emit(cached)
                return

        # 使用延迟计算
        if self._delay_timer is None:
            self._delay_timer = QTimer(self)
            self._delay_timer.setSingleShot(True)
            self._delay_timer.timeout.connect(self._start_hue_calculation)

        self._delay_timer.start(delay_ms)

    def _start_hue_calculation(self) -> None:
        """开始色相直方图计算"""
        if self._pending_image is None or self._pending_image.isNull():
            return

        sample_step = self._get_sample_step(self._pending_image)

        # 安全地停止并清理旧线程
        self._safe_stop_calculator(self._hue_calculator)
        self._hue_calculator = None

        self._hue_calculator = HistogramCalculator(
            self._pending_image, "hue", sample_step
        )
        self._hue_calculator.finished.connect(
            self._on_hue_finished, Qt.ConnectionType.QueuedConnection
        )
        self._hue_calculator.error.connect(
            self.error, Qt.ConnectionType.QueuedConnection
        )
        self._hue_calculator.start()

    def _on_hue_finished(self, histogram: List[int]) -> None:
        """色相直方图计算完成回调"""
        if self._hue_calculator is None:
            return

        # 存入缓存
        if self._use_cache and self._current_image_key:
            cache = get_histogram_cache()
            cache.set(self._current_image_key, "hue", histogram)

        self.hue_histogram_ready.emit(histogram)
        self._safe_stop_calculator(self._hue_calculator)
        self._hue_calculator = None

    def _safe_stop_calculator(self, calculator: Optional[HistogramCalculator]) -> None:
        """安全地停止计算器线程

        Args:
            calculator: 要停止的计算器线程
        """
        if calculator is None:
            return
        
        # 断开所有信号连接
        try:
            calculator.finished.disconnect()
        except:
            pass
        try:
            calculator.error.disconnect()
        except:
            pass
        
        # 请求取消
        calculator.cancel()
        
        # 等待线程结束（非阻塞方式）
        if calculator.isRunning():
            calculator.wait(100)

    def _cancel_luminance_calculator(self) -> None:
        """取消明度直方图计算"""
        self._safe_stop_calculator(self._luminance_calculator)
        self._luminance_calculator = None

    def _cancel_rgb_calculator(self) -> None:
        """取消RGB直方图计算"""
        self._safe_stop_calculator(self._rgb_calculator)
        self._rgb_calculator = None

    def _cancel_hue_calculator(self) -> None:
        """取消色相直方图计算"""
        self._safe_stop_calculator(self._hue_calculator)
        self._hue_calculator = None

    def cancel_all(self) -> None:
        """取消所有计算"""
        self._cancel_luminance_calculator()
        self._cancel_rgb_calculator()
        self._cancel_hue_calculator()

        if self._delay_timer is not None and self._delay_timer.isActive():
            self._delay_timer.stop()

    def clear(self) -> None:
        """清理资源"""
        self.cancel_all()
        self._pending_image = None
