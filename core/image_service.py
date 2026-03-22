"""图片服务模块

管理图片加载相关业务逻辑，包括异步加载、分阶段加载、缩略图生成、色彩空间检测等。
UI层通过ImageService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
import io
import struct
from dataclasses import dataclass
from typing import Optional

# 第三方库导入
from PIL import Image
from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QImage, QPixmap

# 项目模块导入
from .logger import get_logger, log_performance


logger = get_logger("image_service")

# 增加 PIL 图片像素限制，支持超大图片（约 5 亿像素）
Image.MAX_IMAGE_PIXELS = 500_000_000


# ==================== 色彩空间检测 ====================

@dataclass
class ColorSpaceInfo:
    """色彩空间信息
    
    存储图片的色彩空间检测结果，包括色彩空间名称、ICC配置文件信息等。
    """
    name: str
    has_icc_profile: bool
    icc_profile_size: int
    gamma: Optional[float]
    source: str


class ColorSpaceDetector:
    """色彩空间检测器
    
    检测图片的色彩空间信息，支持ICC配置文件和EXIF信息解析。
    """
    
    KNOWN_PROFILES = {
        b'sRGB': 'sRGB',
        b'Adobe RGB': 'Adobe RGB',
        b'ProPhoto': 'ProPhoto RGB',
        b'DCI-P3': 'DCI-P3',
        b'Display P3': 'Display P3',
        b'IEC61966': 'sRGB',
        b'IEC 61966': 'sRGB',
    }
    
    PROFILE_GAMMA = {
        'sRGB': 2.2,
        'Adobe RGB': 2.2,
        'ProPhoto RGB': 1.8,
        'DCI-P3': 2.6,
        'Display P3': 2.2,
    }
    
    @classmethod
    def detect(cls, image: Image.Image) -> ColorSpaceInfo:
        """检测图片的色彩空间
        
        Args:
            image: PIL Image 对象
            
        Returns:
            ColorSpaceInfo: 色彩空间信息
        """
        if 'icc_profile' in image.info:
            return cls._detect_from_icc(image.info['icc_profile'])
        
        exif_colorspace = cls._detect_from_exif(image)
        if exif_colorspace:
            return exif_colorspace
        
        return ColorSpaceInfo(
            name='sRGB',
            has_icc_profile=False,
            icc_profile_size=0,
            gamma=2.2,
            source='default'
        )
    
    @classmethod
    def _detect_from_icc(cls, icc_profile: bytes) -> ColorSpaceInfo:
        """从 ICC 配置文件解析色彩空间
        
        Args:
            icc_profile: ICC 配置文件的原始字节数据
            
        Returns:
            ColorSpaceInfo: 色彩空间信息
        """
        try:
            profile_size = struct.unpack('>I', icc_profile[0:4])[0]
            
            profile_name = cls._identify_profile_name(icc_profile)
            
            gamma = cls.PROFILE_GAMMA.get(profile_name, 2.2)
            
            return ColorSpaceInfo(
                name=profile_name,
                has_icc_profile=True,
                icc_profile_size=profile_size,
                gamma=gamma,
                source='icc'
            )
        except (struct.error, IndexError, UnicodeDecodeError):
            return ColorSpaceInfo(
                name='Unknown',
                has_icc_profile=True,
                icc_profile_size=len(icc_profile),
                gamma=2.2,
                source='icc'
            )
    
    @classmethod
    def _identify_profile_name(cls, icc_profile: bytes) -> str:
        """识别 ICC 配置文件的具体名称
        
        Args:
            icc_profile: ICC 配置文件的原始字节数据
            
        Returns:
            str: 配置文件名称
        """
        try:
            for key, name in cls.KNOWN_PROFILES.items():
                if key in icc_profile:
                    return name
            
            try:
                profile_desc = icc_profile.decode('utf-8', errors='ignore')
                for key, name in cls.KNOWN_PROFILES.items():
                    if key.decode('utf-8', errors='ignore') in profile_desc:
                        return name
            except (UnicodeDecodeError, AttributeError):
                pass
            
            return 'Unknown ICC'
            
        except Exception:
            return 'Unknown ICC'
    
    @classmethod
    def _detect_from_exif(cls, image: Image.Image) -> Optional[ColorSpaceInfo]:
        """从 EXIF 信息检测色彩空间
        
        Args:
            image: PIL Image 对象
            
        Returns:
            Optional[ColorSpaceInfo]: 色彩空间信息，如果无法检测则返回 None
        """
        try:
            exif = image._getexif()
            if not exif:
                return None
            
            colorspace_tag = exif.get(0xA001)
            if colorspace_tag == 1:
                return ColorSpaceInfo(
                    name='sRGB',
                    has_icc_profile=False,
                    icc_profile_size=0,
                    gamma=2.2,
                    source='exif'
                )
            elif colorspace_tag == 0xFFFF:
                return ColorSpaceInfo(
                    name='Uncalibrated',
                    has_icc_profile=False,
                    icc_profile_size=0,
                    gamma=2.2,
                    source='exif'
                )
        except (AttributeError, KeyError, TypeError):
            pass
        return None


# ==================== 图片加载线程 ====================

class ProgressiveImageLoader(QThread):
    """分阶段图片加载工作线程

    实现两阶段加载：
    1. 快速解码显示尺寸图片（用于快速显示）
    2. 后台解码完整图片（用于直方图计算和精确取色）

    线程安全说明：
    - 所有信号都使用 QueuedConnection，确保跨线程安全
    - cancel() 方法设置标志位，不阻塞调用线程
    - 不使用 terminate()，通过标志位优雅退出

    使用示例：
        loader = ProgressiveImageLoader(image_path, display_size=1920, parent=self)
        loader.display_ready.connect(
            self._on_display_ready, Qt.ConnectionType.QueuedConnection
        )
        loader.full_ready.connect(
            self._on_full_ready, Qt.ConnectionType.QueuedConnection
        )
        loader.error.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection
        )
        loader.start()

        # 取消加载
        loader.cancel()

    信号:
        display_ready: 显示尺寸图片就绪，参数为 (image_data, width, height)
        full_ready: 完整图片就绪，参数为 (image_data, width, height, format)
        colorspace_ready: 色彩空间检测完成，参数为 ColorSpaceInfo
        progress: 加载进度 (0-100)
        error: 加载错误，参数为错误信息
    """
    display_ready = Signal(bytes, int, int)
    full_ready = Signal(bytes, int, int, str)
    colorspace_ready = Signal(object)
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, image_path: str, display_size: int = 1920, parent=None) -> None:
        """初始化加载器

        Args:
            image_path: 图片文件路径
            display_size: 显示尺寸上限（默认1920px）
            parent: 父对象
        """
        super().__init__(parent)
        self._image_path: str = image_path
        self._display_size: int = display_size
        self._is_cancelled: bool = False
        self._colorspace_info: Optional[ColorSpaceInfo] = None

    def cancel(self) -> None:
        """取消任务（异步，不阻塞调用线程）

        设置取消标志位，线程会在检查点检测到后自然退出。
        不调用 wait()，避免阻塞 UI 线程。
        """
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消
        
        Returns:
            bool: True表示已取消
        """
        return self._is_cancelled
    
    def get_colorspace_info(self) -> Optional[ColorSpaceInfo]:
        """获取检测到的色彩空间信息
        
        Returns:
            Optional[ColorSpaceInfo]: 色彩空间信息
        """
        return self._colorspace_info

    def run(self) -> None:
        """在子线程中分阶段加载图片"""
        try:
            self.progress.emit(5)

            with log_performance("load_image", {"path": self._image_path}):
                with Image.open(self._image_path) as pil_image:
                    if self._check_cancelled():
                        return
                    
                    self._colorspace_info = ColorSpaceDetector.detect(pil_image)
                    self.colorspace_ready.emit(self._colorspace_info)

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
                logger.error(f"图片加载异常: path={self._image_path}, error={str(e)}")
                self.error.emit(str(e))


class ImageService(QObject):
    """图片服务，管理图片加载相关业务逻辑

    职责：
    - 异步图片加载（支持分阶段加载）
    - 加载任务生命周期管理
    - 缩略图生成
    - 色彩空间检测与管理

    线程安全说明：
    - 所有信号连接使用 QueuedConnection，确保跨线程安全
    - 加载器线程通过文件路径工作，不涉及 QImage 共享
    - 服务析构时会等待线程结束，确保资源安全释放
    - 不使用 terminate()，通过 cancel() 优雅停止线程

    使用示例：
        service = ImageService(parent=self)
        service.image_loaded.connect(
            self._on_image_loaded, Qt.ConnectionType.QueuedConnection
        )
        service.loading_progress.connect(
            self._on_progress, Qt.ConnectionType.QueuedConnection
        )
        service.error.connect(
            self._on_error, Qt.ConnectionType.QueuedConnection
        )
        service.load_image_async(image_path)

        # 取消加载
        service.cancel_loading()

    信号：
        loading_started: 加载开始
        loading_progress: 加载进度 (0-100)
        display_ready: 显示尺寸图片就绪 (image_data, width, height)
        full_ready: 完整图片就绪 (image_data, width, height, format)
        image_loaded: 图片加载完成 (QPixmap, QImage)
        colorspace_detected: 色彩空间检测完成 (ColorSpaceInfo)
        error: 加载错误 (error_message)
    """

    loading_started = Signal()
    loading_progress = Signal(int)
    display_ready = Signal(bytes, int, int)
    full_ready = Signal(bytes, int, int, str)
    image_loaded = Signal(object, object)
    colorspace_detected = Signal(object)
    error = Signal(str)

    def __init__(self, parent=None):
        """初始化图片服务

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._loader: Optional[ProgressiveImageLoader] = None
        self._current_path: Optional[str] = None
        self._colorspace_info: Optional[ColorSpaceInfo] = None
        self._memory_manager = None

    def __del__(self):
        """析构函数：确保线程在对象销毁前停止"""
        if self._loader is not None and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait(1000)  # 等待最多1秒

    def _get_memory_manager(self):
        """延迟获取内存管理器
        
        Returns:
            ImageMemoryManager: 内存管理器实例
        """
        if self._memory_manager is None:
            from .image_memory_manager import get_memory_manager
            self._memory_manager = get_memory_manager()
        return self._memory_manager

    def load_image_async(self, path: str, display_size: int = 1920) -> None:
        """异步加载图片

        使用分阶段加载策略：
        1. 快速解码显示尺寸图片（用于快速显示）
        2. 后台解码完整图片（用于直方图计算和精确取色）

        加载完成后，图片会被添加到内存管理器中。

        Args:
            path: 图片文件路径
            display_size: 显示尺寸上限（默认1920px）
        """
        self._current_path = path
        self._colorspace_info = None

        cached = self._get_memory_manager().get_image(path)
        if cached:
            pixmap, image = cached
            logger.debug(f"从缓存加载图片: path={path}")
            self.image_loaded.emit(pixmap, image)
            return

        if self._loader is not None:
            self._loader.cancel()
            if self._loader.isRunning():
                self._loader.wait(500)
            self._loader = None

        logger.info(f"开始加载图片: path={path}")
        self.loading_started.emit()

        self._loader = ProgressiveImageLoader(path, display_size, self)
        self._loader.display_ready.connect(
            self._on_display_ready, Qt.ConnectionType.QueuedConnection
        )
        self._loader.full_ready.connect(
            self._on_full_ready, Qt.ConnectionType.QueuedConnection
        )
        self._loader.colorspace_ready.connect(
            self._on_colorspace_ready, Qt.ConnectionType.QueuedConnection
        )
        self._loader.progress.connect(
            self.loading_progress, Qt.ConnectionType.QueuedConnection
        )
        self._loader.error.connect(
            self._on_load_error, Qt.ConnectionType.QueuedConnection
        )
        self._loader.finished.connect(
            self._cleanup_loader, Qt.ConnectionType.QueuedConnection
        )
        self._loader.start()

    def cancel_loading(self) -> None:
        """取消当前加载任务"""
        if self._loader is not None:
            self._loader.cancel()
            logger.debug("加载任务已取消")

    def get_colorspace_info(self) -> Optional[ColorSpaceInfo]:
        """获取当前图片的色彩空间信息
        
        Returns:
            Optional[ColorSpaceInfo]: 色彩空间信息，如果未加载图片则返回 None
        """
        return self._colorspace_info

    def generate_thumbnail(self, image: QImage, size: int = 100) -> QPixmap:
        """生成缩略图

        使用QImage进行缩放，然后转换为QPixmap，减少内存占用。

        Args:
            image: 原始图片
            size: 缩略图尺寸（默认100px）

        Returns:
            QPixmap: 缩略图
        """
        if image is None or image.isNull():
            return QPixmap()

        # 使用QImage进行缩放，内存效率更高
        thumbnail_image = image.scaled(
            size, size,
            aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
            transformMode=Qt.TransformationMode.SmoothTransformation
        )

        return QPixmap.fromImage(thumbnail_image)

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

        image = QImage.fromData(image_data, fmt)
        pixmap = QPixmap.fromImage(image)

        if self._current_path:
            self._memory_manager.add_image(self._current_path, pixmap, image)

        colorspace_name = self._colorspace_info.name if self._colorspace_info else "unknown"
        logger.info(f"图片加载完成: size={width}x{height}, colorspace={colorspace_name}")
        self.image_loaded.emit(pixmap, image)

    def _on_colorspace_ready(self, colorspace_info: ColorSpaceInfo) -> None:
        """色彩空间检测完成的回调
        
        Args:
            colorspace_info: 色彩空间信息
        """
        self._colorspace_info = colorspace_info
        self.colorspace_detected.emit(colorspace_info)

    def _on_load_error(self, error_msg: str) -> None:
        """图片加载失败的回调
        
        Args:
            error_msg: 错误信息
        """
        logger.error(f"图片加载失败: path={self._current_path}, error={error_msg}")
        self.error.emit(error_msg)

    def _cleanup_loader(self) -> None:
        """清理加载线程"""
        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None

    def release_current_image(self) -> None:
        """释放当前图片的内存

        从内存管理器中移除当前图片，触发垃圾回收。
        同时取消正在进行的加载任务。
        """
        # 取消正在进行的加载任务
        if self._loader is not None:
            # 断开信号连接，防止回调触发
            try:
                self._loader.display_ready.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self._loader.full_ready.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self._loader.colorspace_ready.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self._loader.progress.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self._loader.error.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self._loader.finished.disconnect()
            except (TypeError, RuntimeError):
                pass

            self._loader.cancel()
            self._loader = None

        if self._current_path:
            self._memory_manager.remove_image(self._current_path)
            self._current_path = None

    def get_memory_stats(self) -> dict:
        """获取内存统计信息

        Returns:
            dict: 内存统计信息
        """
        return self._get_memory_manager().get_memory_stats()
