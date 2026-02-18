"""图片服务模块

管理图片加载相关业务逻辑，包括异步加载、分阶段加载、缩略图生成等。
UI层通过ImageService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
import io
from typing import Optional

# 第三方库导入
from PIL import Image
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QImage, QPixmap


class ProgressiveImageLoader(QThread):
    """分阶段图片加载工作线程

    实现两阶段加载：
    1. 快速解码显示尺寸图片（用于快速显示）
    2. 后台解码完整图片（用于直方图计算和精确取色）

    支持取消操作，避免阻塞UI线程
    """
    display_ready = Signal(bytes, int, int)
    full_ready = Signal(bytes, int, int, str)
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, image_path: str, display_size: int = 1920) -> None:
        """初始化加载器

        Args:
            image_path: 图片文件路径
            display_size: 显示尺寸上限（默认1920px）
        """
        super().__init__()
        self._image_path: str = image_path
        self._display_size: int = display_size
        self._is_cancelled: bool = False

    def cancel(self) -> None:
        """请求取消加载"""
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消

        Returns:
            bool: True表示已取消
        """
        return self._is_cancelled

    def run(self) -> None:
        """在子线程中分阶段加载图片"""
        try:
            self.progress.emit(5)

            with Image.open(self._image_path) as pil_image:
                if self._check_cancelled():
                    return

                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')

                width, height = pil_image.size
                max_dim = max(width, height)

                if self._check_cancelled():
                    return

                if max_dim > self._display_size:
                    display_img = pil_image.copy()
                    display_img.thumbnail(
                        (self._display_size, self._display_size),
                        Image.Resampling.LANCZOS
                    )

                    if self._check_cancelled():
                        return

                    buffer = io.BytesIO()
                    display_img.save(buffer, format='BMP')
                    display_data = buffer.getvalue()

                    self.display_ready.emit(display_data, width, height)
                    self.progress.emit(50)

                    del display_img
                else:
                    buffer = io.BytesIO()
                    pil_image.save(buffer, format='BMP')
                    display_data = buffer.getvalue()

                    self.display_ready.emit(display_data, width, height)
                    self.progress.emit(50)

                if self._check_cancelled():
                    return

                self.progress.emit(60)

                full_buffer = io.BytesIO()
                pil_image.save(full_buffer, format='BMP')
                full_data = full_buffer.getvalue()

                if self._check_cancelled():
                    return

                self.progress.emit(90)

                self.full_ready.emit(full_data, width, height, 'BMP')
                self.progress.emit(100)

        except (IOError, OSError, ValueError) as e:
            if not self._check_cancelled():
                self.error.emit(str(e))


class ImageService(QObject):
    """图片服务，管理图片加载相关业务逻辑

    职责：
    - 异步图片加载（支持分阶段加载）
    - 加载任务生命周期管理
    - 缩略图生成

    信号：
        loading_started: 加载开始
        loading_progress: 加载进度 (0-100)
        display_ready: 显示尺寸图片就绪 (image_data, width, height)
        full_ready: 完整图片就绪 (image_data, width, height, format)
        image_loaded: 图片加载完成 (QPixmap, QImage)
        thumbnail_ready: 缩略图生成完成 (QPixmap)
        error: 加载错误 (error_message)
    """

    # 信号
    loading_started = Signal()
    loading_progress = Signal(int)
    display_ready = Signal(bytes, int, int)
    full_ready = Signal(bytes, int, int, str)
    image_loaded = Signal(object, object)
    error = Signal(str)

    def __init__(self, parent=None):
        """初始化图片服务

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._loader: Optional[ProgressiveImageLoader] = None
        self._current_path: Optional[str] = None

    def load_image_async(self, path: str, display_size: int = 1920) -> None:
        """异步加载图片

        使用分阶段加载策略：
        1. 快速解码显示尺寸图片（用于快速显示）
        2. 后台解码完整图片（用于直方图计算和精确取色）

        Args:
            path: 图片文件路径
            display_size: 显示尺寸上限（默认1920px）
        """
        # 保存图片路径
        self._current_path = path

        # 如果已有加载线程在运行，请求取消（非阻塞）
        if self._loader is not None:
            self._loader.cancel()
            self._loader = None

        self.loading_started.emit()

        # 创建并启动分阶段加载线程
        self._loader = ProgressiveImageLoader(path, display_size)
        self._loader.display_ready.connect(self._on_display_ready)
        self._loader.full_ready.connect(self._on_full_ready)
        self._loader.progress.connect(self.loading_progress)
        self._loader.error.connect(self._on_load_error)
        self._loader.finished.connect(self._cleanup_loader)
        self._loader.start()

    def cancel_loading(self) -> None:
        """取消当前加载任务"""
        if self._loader is not None:
            self._loader.cancel()

    def generate_thumbnail(self, image: QImage, size: int = 100) -> QPixmap:
        """生成缩略图

        Args:
            image: 原始图片
            size: 缩略图尺寸（默认100px）

        Returns:
            QPixmap: 缩略图
        """
        if image is None or image.isNull():
            return QPixmap()

        return QPixmap.fromImage(image).scaled(
            size, size,
            aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
            transformMode=Qt.TransformationMode.SmoothTransformation
        )

    def _on_display_ready(self, image_data: bytes, width: int, height: int) -> None:
        """显示图片就绪的回调

        Args:
            image_data: 图片字节数据（显示尺寸）
            width: 原始图片宽度
            height: 原始图片高度
        """
        self.display_ready.emit(image_data, width, height)

    def _on_full_ready(self, image_data: bytes, width: int, height: int, fmt: str) -> None:
        """完整图片就绪的回调

        Args:
            image_data: 图片字节数据
            width: 图片宽度
            height: 图片高度
            fmt: 图片格式
        """
        self.full_ready.emit(image_data, width, height, fmt)

        # 从字节数据创建QImage和QPixmap
        image = QImage.fromData(image_data, fmt)
        pixmap = QPixmap.fromImage(image)

        self.image_loaded.emit(pixmap, image)

    def _on_load_error(self, error_msg: str) -> None:
        """图片加载失败的回调

        Args:
            error_msg: 错误信息
        """
        self.error.emit(error_msg)

    def _cleanup_loader(self) -> None:
        """清理加载线程"""
        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None


# 导入Qt常量
from PySide6.QtCore import Qt
