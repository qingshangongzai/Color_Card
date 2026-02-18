"""明度服务模块

管理明度计算相关业务逻辑，包括Zone分析、亮度分布统计、高亮区域计算等。
UI层通过LuminanceService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
from typing import Dict, List, Optional, Tuple

# 第三方库导入
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

# 项目模块导入
from .color import get_luminance, get_zone


class LuminanceCalculator(QThread):
    """明度计算线程

    在后台线程中执行明度分布计算，避免阻塞UI。
    支持取消操作。
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
        self._image = image
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

            # 计算明度分布
            distribution = self._calculate_distribution()

            if self._check_cancelled():
                return

            # 发送成功信号
            result = {
                'distribution': distribution,
                'total_pixels': self._image.width() * self._image.height()
            }
            self.calculation_finished.emit(result)

        except Exception as e:
            if not self._check_cancelled():
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
    - 明度计算和Zone分析
    - 亮度分布统计
    - 高亮区域计算

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

    def calculate_luminance_zones(self, image: QImage) -> None:
        """开始计算明度Zone分布

        异步执行明度计算，通过信号通知结果。
        如果已有计算任务在进行，会先取消旧任务。

        Args:
            image: QImage 对象
        """
        # 取消之前的计算
        if self._calculator is not None and self._calculator.isRunning():
            self._calculator.cancel()
            self._calculator = None

        self.calculation_started.emit()

        # 创建并启动计算线程
        self._calculator = LuminanceCalculator(image, self)
        self._calculator.calculation_finished.connect(self._on_calculation_finished)
        self._calculator.calculation_error.connect(self.calculation_error)
        self._calculator.finished.connect(self._cleanup_calculator)
        self._calculator.start()

    def cancel_calculation(self) -> None:
        """取消当前计算任务"""
        if self._calculator is not None and self._calculator.isRunning():
            self._calculator.cancel()

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

        # 初始化Zone计数 (Zone 0-7)
        distribution = [0] * 8

        # 采样步长（性能优化）
        sample_step = 4

        for y in range(0, height, sample_step):
            for x in range(0, width, sample_step):
                color = image.pixelColor(x, y)
                luminance = get_luminance(color.red(), color.green(), color.blue())
                zone_index = luminance // 32
                zone_index = min(zone_index, 7)  # 确保不越界
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
            zone: Zone编号 (0-7)
            canvas_size: 画布尺寸 (width, height)
            display_rect: 图片显示区域 (x, y, w, h)
            zone_color: 高亮颜色

        Returns:
            QPixmap: 高亮遮罩图，如果失败则返回None
        """
        if image is None or image.isNull():
            return None

        if not (0 <= zone <= 7):
            return None

        canvas_width, canvas_height = canvas_size
        disp_x, disp_y, disp_w, disp_h = display_rect

        # 创建透明遮罩图
        highlight_pixmap = QPixmap(canvas_width, canvas_height)
        highlight_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(highlight_pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 计算亮度范围
        min_lum = zone * 32
        max_lum = (zone + 1) * 32 - 1

        # 计算缩放比例
        scale_x = image.width() / disp_w
        scale_y = image.height() / disp_h

        # 采样步长（性能优化）
        sample_step = 4

        # 遍历显示区域的像素
        for dy in range(0, disp_h, sample_step):
            for dx in range(0, disp_w, sample_step):
                # 计算对应的原始图片坐标
                img_x = int(dx * scale_x)
                img_y = int(dy * scale_y)

                # 边界检查
                img_x = min(img_x, image.width() - 1)
                img_y = min(img_y, image.height() - 1)

                # 获取像素颜色并计算亮度
                color = image.pixelColor(img_x, img_y)
                luminance = get_luminance(color.red(), color.green(), color.blue())

                # 如果亮度在当前Zone范围内，绘制遮罩
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

    def _on_calculation_finished(self, result: dict):
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


# 导入Qt常量
from PySide6.QtCore import Qt
