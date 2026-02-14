# 标准库导入
import colorsys
import io
from typing import List, Optional, Tuple

# 第三方库导入
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget
from qfluentwidgets import Action, FluentIcon, RoundMenu

# 项目模块导入
from core import get_luminance, get_zone
from .color_picker import ColorPicker
from .zoom_viewer import ZoomViewer
from .theme_colors import (
    get_canvas_background_color, get_canvas_empty_text_color, get_picker_colors,
    get_tooltip_bg_color, get_tooltip_text_color
)


class ImageLoader(QThread):
    """图片加载工作线程（使用PIL在子线程读取图片数据）"""
    loaded = Signal(bytes, int, int, str)  # 信号：图片数据(bytes), 宽度, 高度, 格式
    error = Signal(str)  # 信号：错误信息

    def __init__(self, image_path: str) -> None:
        super().__init__()
        self._image_path: str = image_path

    def run(self) -> None:
        """在子线程中使用PIL加载图片"""
        try:
            # 使用PIL打开图片（PIL是线程安全的）
            with Image.open(self._image_path) as pil_image:
                # 转换为RGB模式（处理RGBA、P模式等）
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')

                # 获取图片尺寸
                width, height = pil_image.size

                # 将图片保存为内存中的BMP格式（无压缩，便于快速转换）
                buffer = io.BytesIO()
                pil_image.save(buffer, format='BMP')
                image_data = buffer.getvalue()

                self.loaded.emit(image_data, width, height, 'BMP')
        except (IOError, OSError, ValueError) as e:
            self.error.emit(str(e))


class ProgressiveImageLoader(QThread):
    """分阶段图片加载工作线程

    实现三阶段加载：
    1. 快速加载模糊预览（缩略图）
    2. 加载完整分辨率图片
    3. 发送进度更新

    支持取消操作，避免阻塞UI线程
    """
    # 信号：模糊预览图片数据, 宽度, 高度
    blurry_loaded = Signal(bytes, int, int)
    # 信号：完整图片数据, 宽度, 高度, 格式
    full_loaded = Signal(bytes, int, int, str)
    # 信号：加载进度 (0-100)
    progress = Signal(int)
    # 信号：错误信息
    error = Signal(str)

    def __init__(self, image_path: str, blurry_size: int = 150) -> None:
        super().__init__()
        self._image_path: str = image_path
        self._blurry_size: int = blurry_size  # 模糊预览的最大边长（减小以加快预览）
        self._is_cancelled: bool = False  # 取消标志

    def cancel(self) -> None:
        """请求取消加载

        设置取消标志，run方法会在关键检查点检查此标志
        """
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
            # 阶段1：快速加载模糊预览
            self.progress.emit(10)

            with Image.open(self._image_path) as pil_image:
                # 检查是否被取消
                if self._check_cancelled():
                    return

                # 转换为RGB模式
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')

                width, height = pil_image.size

                # 生成缩略图用于快速预览
                thumb_image = pil_image.copy()
                thumb_image.thumbnail((self._blurry_size, self._blurry_size), Image.Resampling.LANCZOS)

                # 检查是否被取消
                if self._check_cancelled():
                    return

                # 保存缩略图数据
                buffer = io.BytesIO()
                thumb_image.save(buffer, format='BMP')
                blurry_data = buffer.getvalue()

                # 发送模糊预览加载完成信号
                self.blurry_loaded.emit(blurry_data, width, height)
                self.progress.emit(40)

                # 检查是否被取消
                if self._check_cancelled():
                    return

                # 阶段2：加载完整图片
                self.progress.emit(60)

                # 检查是否被取消
                if self._check_cancelled():
                    return

                full_buffer = io.BytesIO()
                pil_image.save(full_buffer, format='BMP')
                full_data = full_buffer.getvalue()

                # 检查是否被取消
                if self._check_cancelled():
                    return

                self.progress.emit(90)

                # 发送完整图片加载完成信号
                self.full_loaded.emit(full_data, width, height, 'BMP')
                self.progress.emit(100)

        except (IOError, OSError, ValueError) as e:
            if not self._check_cancelled():
                self.error.emit(str(e))


class BaseCanvas(QWidget):
    """画布基类，提供图片加载、显示和取色点管理的公共功能

    功能：
        - 异步图片加载（支持分阶段加载）
        - 图片显示（保持比例）
        - 取色点管理
        - 坐标转换
        - 右键菜单

    子类需要实现：
        - _setup_after_load(): 图片加载完成后的设置
        - _on_image_load_error(): 图片加载失败的处理
        - extract_all(): 提取所有取色点的数据
    """

    image_loaded = Signal(str)  # 信号：图片路径
    image_data_loaded = Signal(object, object)  # 信号：QPixmap, QImage（用于同步到其他面板）
    open_image_requested = Signal()  # 信号：请求打开图片
    change_image_requested = Signal()  # 信号：请求更换图片
    clear_image_requested = Signal()  # 信号：请求清空图片
    image_cleared = Signal()  # 信号：图片已清空（用于同步到其他面板）

    def __init__(self, parent: Optional[QWidget] = None, picker_count: int = 5) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QLabel

        # 设置sizePolicy，允许在水平和垂直方向上都充分扩展和压缩
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 设置合理的最小尺寸，允许画布在压缩时调整大小
        self.setMinimumSize(300, 200)
        bg_color = get_canvas_background_color()
        self.setStyleSheet(f"background-color: {bg_color.name()}; border-radius: 8px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._original_pixmap: Optional[QPixmap] = None
        self._image: Optional[QImage] = None
        self._picker_positions: List[QPoint] = []
        self._picker_rel_positions: List[QPointF] = []
        self._loader: Optional[ImageLoader] = None
        self._progressive_loader: Optional[ProgressiveImageLoader] = None
        self._pending_image_path: Optional[str] = None
        self._picker_count: int = picker_count
        self._is_loading: bool = False  # 是否正在加载

        # 启用文件拖拽接收
        self.setAcceptDrops(True)

        # 创建加载状态显示组件
        self._setup_loading_ui()

    def _setup_loading_ui(self) -> None:
        """设置加载状态UI"""
        from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget
        from PySide6.QtCore import Qt

        # 加载状态容器（居中显示）
        self._loading_widget = QWidget(self)
        self._loading_widget.setStyleSheet("background-color: rgba(42, 42, 42, 180); border-radius: 8px;")
        self._loading_widget.hide()

        layout = QVBoxLayout(self._loading_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        # 加载提示文字
        self._loading_label = QLabel("正在导入图片...", self._loading_widget)
        self._loading_label.setStyleSheet("color: white; font-size: 14px; background: transparent;")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._loading_label)

    def show_loading(self, text: str = "正在导入图片...") -> None:
        """显示加载状态

        Args:
            text: 加载提示文字
        """
        self._is_loading = True
        self._loading_label.setText(text)
        self._loading_widget.setGeometry(self.rect())
        self._loading_widget.show()
        self._loading_widget.raise_()
        self.update()

    def hide_loading(self) -> None:
        """隐藏加载状态"""
        self._is_loading = False
        self._loading_widget.hide()
        self.update()

    def resizeEvent(self, event) -> None:
        """窗口大小改变时更新加载状态组件位置"""
        super().resizeEvent(event)
        if self._is_loading:
            self._loading_widget.setGeometry(self.rect())

    def set_image(self, image_path: str) -> None:
        """异步加载并显示图片（使用分阶段加载，非阻塞）

        Args:
            image_path: 图片文件路径
        """
        # 保存图片路径
        self._pending_image_path = image_path

        # 如果已有加载线程在运行，请求取消（非阻塞）
        if self._progressive_loader is not None:
            self._progressive_loader.cancel()
            # 注意：不调用 wait()，避免阻塞UI线程
            # 旧线程会在检查点发现取消标志后自然结束
            self._progressive_loader = None

        # 显示加载状态
        self.show_loading("正在导入图片...")

        # 创建并启动分阶段加载线程
        self._progressive_loader = ProgressiveImageLoader(image_path)
        self._progressive_loader.blurry_loaded.connect(self._on_blurry_image_loaded)
        self._progressive_loader.full_loaded.connect(self._on_full_image_loaded)
        self._progressive_loader.progress.connect(self._on_loading_progress)
        self._progressive_loader.error.connect(self._on_image_load_error)
        self._progressive_loader.finished.connect(self._cleanup_progressive_loader)
        self._progressive_loader.start()

    def _cleanup_loader(self) -> None:
        """清理加载线程"""
        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None

    def _cleanup_progressive_loader(self) -> None:
        """清理分阶段加载线程"""
        if self._progressive_loader is not None:
            self._progressive_loader.deleteLater()
            self._progressive_loader = None

    def _on_blurry_image_loaded(self, image_data: bytes, width: int, height: int) -> None:
        """模糊预览图片加载完成的回调

        Args:
            image_data: 图片字节数据（缩略图）
            width: 原始图片宽度
            height: 原始图片高度
        """
        # 从字节数据创建QImage和QPixmap
        blurry_image = QImage.fromData(image_data, 'BMP')
        self._original_pixmap = QPixmap.fromImage(blurry_image)

        # 保存原始尺寸信息
        self._pending_image_width = width
        self._pending_image_height = height

        # 显示模糊预览
        self._setup_blurry_preview()
        self.update()

    def _on_full_image_loaded(self, image_data: bytes, width: int, height: int, fmt: str) -> None:
        """完整图片加载完成的回调

        Args:
            image_data: 图片字节数据
            width: 图片宽度
            height: 图片高度
            fmt: 图片格式
        """
        # 从字节数据创建QImage（在主线程中安全执行）
        self._image = QImage.fromData(image_data, fmt)
        self._original_pixmap = QPixmap.fromImage(self._image)

        # 隐藏加载状态
        self.hide_loading()

        # 完成加载后的设置
        self._setup_after_load()

    def _on_loading_progress(self, progress: int) -> None:
        """加载进度更新回调

        Args:
            progress: 加载进度 (0-100)
        """
        if progress < 40:
            self._loading_label.setText(f"正在导入图片... {progress}%")
        elif progress < 90:
            self._loading_label.setText(f"正在加载高清图片... {progress}%")
        else:
            self._loading_label.setText(f"正在完成... {progress}%")

    def _setup_blurry_preview(self) -> None:
        """设置模糊预览（子类可重写）"""
        pass

    def _on_image_loaded(self, image_data: bytes, width: int, height: int, fmt: str) -> None:
        """图片加载完成的回调（在主线程中创建QImage/QPixmap）

        Args:
            image_data: 图片字节数据
            width: 图片宽度
            height: 图片高度
            fmt: 图片格式
        """
        # 从字节数据创建QImage（在主线程中安全执行）
        self._image = QImage.fromData(image_data, fmt)
        self._original_pixmap = QPixmap.fromImage(self._image)
        self._setup_after_load()

    def _on_image_load_error(self, error_msg: str) -> None:
        """图片加载失败的回调

        Args:
            error_msg: 错误信息

        子类应重写此方法以提供特定的错误处理
        """
        self.hide_loading()
        print(f"图片加载失败: {error_msg}")

    def set_image_data(self, pixmap: QPixmap, image: QImage, emit_sync: bool = True) -> None:
        """直接使用已加载的图片数据（避免重复加载）

        Args:
            pixmap: QPixmap 对象
            image: QImage 对象
            emit_sync: 是否发射同步信号（默认True，从其他面板同步时设为False）
        """
        self._original_pixmap = pixmap
        self._image = image
        self._setup_after_load(emit_sync=emit_sync)

    def _setup_after_load(self, emit_sync: bool = True) -> None:
        """图片加载完成后的设置

        Args:
            emit_sync: 是否发射同步信号

        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 _setup_after_load 方法")

    def _init_picker_positions(self) -> None:
        """初始化取色点位置到图片中心区域"""
        center_x = 0.5  # 使用相对坐标，中心为 0.5
        center_y = 0.5

        for i in range(self._picker_count):
            offset_x = (i - 2) * 0.05  # 使用相对偏移（5%）
            self._picker_rel_positions[i] = QPointF(center_x + offset_x, center_y)

    def update_picker_positions(self) -> None:
        """更新所有取色点的位置

        根据相对坐标（0.0-1.0）计算画布坐标，实现取色点位置
        在图片缩放时保持相对位置不变。

        坐标转换算法：
        1. 获取图片显示区域 (disp_x, disp_y, disp_w, disp_h)
        2. 将相对坐标转换为画布坐标：
           canvas_x = disp_x + rel_x * disp_w
           canvas_y = disp_y + rel_y * disp_h
        3. 更新取色点UI位置

        相对坐标的优势：
        - 图片缩放时取色点位置自动调整
        - 图片尺寸变化时保持相对位置不变
        - 便于保存和恢复取色点位置
        """
        # 如果有图片，使用相对坐标计算画布坐标
        if self._image and not self._image.isNull():
            display_rect = self.get_display_rect()
            if display_rect:
                disp_x, disp_y, disp_w, disp_h = display_rect

                for i in range(self._picker_count):
                    rel_pos = self._picker_rel_positions[i]

                    # 将相对坐标转换为画布坐标
                    # 公式：画布坐标 = 显示区域起点 + 相对坐标 × 显示区域尺寸
                    canvas_x = disp_x + rel_pos.x() * disp_w
                    canvas_y = disp_y + rel_pos.y() * disp_h

                    # 更新画布坐标存储
                    self._picker_positions[i] = QPoint(int(canvas_x), int(canvas_y))

                    # 子类应在此更新取色点显示位置
                    self._update_picker_position(i, int(canvas_x), int(canvas_y))
        else:
            # 没有图片时，直接使用存储的画布坐标
            for i in range(self._picker_count):
                pos = self._picker_positions[i]
                self._update_picker_position(i, pos.x(), pos.y())

    def _update_picker_position(self, index: int, canvas_x: int, canvas_y: int) -> None:
        """更新单个取色点的位置

        Args:
            index: 取色点索引
            canvas_x: 画布X坐标
            canvas_y: 画布Y坐标

        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 _update_picker_position 方法")

    def set_picker_count(self, count: int) -> None:
        """设置取色点数量

        Args:
            count: 取色点数量 (2-5)
        """
        if count < 2 or count > 5:
            return

        if count == self._picker_count:
            return

        old_count = self._picker_count
        self._picker_count = count

        if count > old_count:
            # 增加取色点
            for i in range(old_count, count):
                # 新取色点位置在最后一个取色点旁边
                if old_count > 0:
                    last_rel_pos = self._picker_rel_positions[-1]
                    new_rel_pos = QPointF(last_rel_pos.x() + 0.05, last_rel_pos.y())
                else:
                    new_rel_pos = QPointF(0.5, 0.5)  # 默认在中心
                self._picker_positions.append(QPoint(100, 100))  # 临时画布坐标
                self._picker_rel_positions.append(new_rel_pos)
                self._on_picker_added(i)
        else:
            # 减少取色点
            for i in range(old_count - 1, count - 1, -1):
                self._picker_positions.pop()
                self._picker_rel_positions.pop()
                self._on_picker_removed(i)

        self.update_picker_positions()

        # 如果有图片，重新提取数据
        if self._image and not self._image.isNull():
            self.extract_all()

    def _on_picker_added(self, index: int) -> None:
        """添加取色点时的回调

        Args:
            index: 取色点索引

        子类应重写此方法以创建取色点UI
        """
        pass

    def _on_picker_removed(self, index: int) -> None:
        """移除取色点时的回调

        Args:
            index: 取色点索引

        子类应重写此方法以移除取色点UI
        """
        pass

    def on_picker_moved(self, index: int, new_pos: QPoint) -> None:
        """取色点移动时的回调

        将取色点的画布坐标转换为相对坐标并存储，确保在图片缩放时
        取色点位置保持不变。

        坐标转换算法（画布坐标 → 相对坐标）：
        1. 获取图片显示区域 (disp_x, disp_y, disp_w, disp_h)
        2. 计算相对坐标：
           rel_x = (画布X - 显示区域X) / 显示区域宽度
           rel_y = (画布Y - 显示区域Y) / 显示区域高度
        3. 限制相对坐标在 [0.0, 1.0] 范围内

        Args:
            index: 取色点索引
            new_pos: 新的画布坐标位置
        """
        # 更新画布坐标
        self._picker_positions[index] = new_pos

        # 如果有图片，将画布坐标转换为相对坐标并存储
        if self._image and not self._image.isNull():
            display_rect = self.get_display_rect()
            if display_rect:
                disp_x, disp_y, disp_w, disp_h = display_rect

                # 将画布坐标转换为相对坐标
                # 公式：相对坐标 = (画布坐标 - 显示区域起点) / 显示区域尺寸
                rel_x = (new_pos.x() - disp_x) / disp_w
                rel_y = (new_pos.y() - disp_y) / disp_h

                # 限制在图片范围内（防止取色点超出图片边界）
                rel_x = max(0.0, min(1.0, rel_x))
                rel_y = max(0.0, min(1.0, rel_y))

                # 更新相对坐标
                self._picker_rel_positions[index] = QPointF(rel_x, rel_y)

        self.extract_at(index)
        self.update()

    def extract_at(self, index: int) -> None:
        """提取指定取色点的数据

        Args:
            index: 取色点索引

        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 extract_at 方法")

    def extract_all(self) -> None:
        """提取所有取色点的数据

        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 extract_all 方法")

    def canvas_to_image_pos(self, canvas_pos: QPoint) -> Optional[QPoint]:
        """将画布坐标转换为原始图片坐标

        坐标转换算法（画布坐标 → 原始图片坐标）：
        1. 获取图片显示区域 (disp_x, disp_y, disp_w, disp_h)
        2. 计算在显示区域内的相对位置：
           img_x = 画布X - 显示区域X
           img_y = 画布Y - 显示区域Y
        3. 检查是否在显示区域内
        4. 计算缩放比例：
           scale_x = 原始图片宽度 / 显示区域宽度
           scale_y = 原始图片高度 / 显示区域高度
        5. 转换为原始图片坐标：
           orig_x = img_x × scale_x
           orig_y = img_y × scale_y
        6. 边界检查，确保坐标在有效范围内

        Args:
            canvas_pos: 画布坐标

        Returns:
            QPoint: 原始图片坐标，如果不在图片范围内则返回 None
        """
        if self._image is None or self._image.isNull():
            return None

        display_rect = self.get_display_rect()
        if display_rect is None:
            return None

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 将画布坐标转换为图片坐标
        # 首先计算在显示区域内的相对位置
        img_x = canvas_pos.x() - disp_x
        img_y = canvas_pos.y() - disp_y

        # 检查坐标是否在图片显示范围内
        if 0 <= img_x < disp_w and 0 <= img_y < disp_h:
            # 计算在原始图片中的坐标
            # 缩放比例 = 原始图片尺寸 / 显示区域尺寸
            scale_x = self._image.width() / disp_w
            scale_y = self._image.height() / disp_h

            # 应用缩放比例
            orig_x = int(img_x * scale_x)
            orig_y = int(img_y * scale_y)

            # 确保坐标在原始图片范围内（边界检查）
            orig_x = max(0, min(orig_x, self._image.width() - 1))
            orig_y = max(0, min(orig_y, self._image.height() - 1))

            return QPoint(orig_x, orig_y)

        return None

    def get_display_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """计算图片在画布中的显示区域

        使用保持比例的缩放算法，将图片完整显示在画布中心。

        缩放算法：
        1. 获取画布尺寸和原始图片尺寸
        2. 计算宽度和高度的缩放比例：
           scale_w = 画布宽度 / 图片宽度
           scale_h = 画布高度 / 图片高度
        3. 选择较小的缩放比例（确保图片完整显示）
        4. 使用 Qt.KeepAspectRatio 模式缩放图片
        5. 计算居中位置：
           x = (画布宽度 - 缩放后宽度) / 2
           y = (画布高度 - 缩放后高度) / 2

        算法特点：
        - 保持图片宽高比，不会变形
        - 图片完整显示在画布内（不会被裁剪）
        - 居中显示，四周留有空白
        - 缩放比例不会超过1.0（不会放大）

        Returns:
            tuple: (x, y, width, height) 或 None
        """
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return None

        # 计算缩放后的尺寸（保持比例）
        # Qt.KeepAspectRatio 会自动选择合适的缩放比例
        # 确保图片完整显示在画布内，不会被裁剪
        scaled_size = self._original_pixmap.size()
        scaled_size.scale(self.size(), Qt.AspectRatioMode.KeepAspectRatio)

        # 居中显示
        # 计算水平和垂直方向的偏移量，使图片居中
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2

        return x, y, scaled_size.width(), scaled_size.height()

    def get_image_display_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """获取图片在画布中的显示区域（供子组件使用）

        Returns:
            tuple: (x, y, width, height) 或 None
        """
        return self.get_display_rect()

    def paintEvent(self, event) -> None:
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 绘制背景
        painter.fillRect(self.rect(), get_canvas_background_color())

        # 绘制图片（使用原始高分辨率图片，实时缩放显示）
        if self._original_pixmap and not self._original_pixmap.isNull():
            display_rect = self.get_display_rect()
            if display_rect:
                x, y, w, h = display_rect
                target_rect = QRect(x, y, w, h)
                painter.drawPixmap(target_rect, self._original_pixmap, self._original_pixmap.rect())

                # 子类可以在此绘制额外的内容
                self._draw_overlay(painter, display_rect)
        elif not self._is_loading:
            # 没有图片且不在加载状态时显示提示文字
            painter.setPen(get_canvas_empty_text_color())
            font = QFont()
            font.setPointSize(14)
            painter.setFont(font)
            text = "点击导入图片"
            text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_overlay(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制叠加内容

        Args:
            painter: QPainter 对象
            display_rect: 图片显示区域 (x, y, w, h)

        子类可以重写此方法以绘制额外的内容
        """
        pass

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 如果没有图片，点击打开文件对话框
            if self._original_pixmap is None or self._original_pixmap.isNull():
                self.open_image_requested.emit()
            event.accept()

    def resizeEvent(self, event) -> None:
        """窗口大小改变时重新调整图片"""
        super().resizeEvent(event)
        if self._image and not self._image.isNull():
            # 窗口大小改变时，更新取色点位置并重新提取数据
            self.update_picker_positions()
            self.extract_all()
            self.update()

    def contextMenuEvent(self, event) -> None:
        """右键菜单事件"""
        # 只有在有图片时才显示右键菜单
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return

        menu = RoundMenu("")

        change_action = Action(FluentIcon.PHOTO, "更换图片")
        change_action.triggered.connect(self.change_image_requested.emit)
        menu.addAction(change_action)

        clear_action = Action(FluentIcon.DELETE, "清空图片")
        clear_action.triggered.connect(self.clear_image_requested.emit)
        menu.addAction(clear_action)

        menu.exec(event.globalPos())

    def clear_image(self) -> None:
        """清空图片"""
        self._original_pixmap = None
        self._image = None

        # 重置相对坐标到默认位置
        for i in range(len(self._picker_rel_positions)):
            self._picker_rel_positions[i] = QPointF(0.5, 0.5)

        # 恢复光标为手型
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.update()

        # 发送图片已清空信号，用于同步到其他面板
        self.image_cleared.emit()

    def get_image(self) -> Optional[QImage]:
        """获取当前图片

        Returns:
            QImage: 当前图片对象，如果没有则返回 None
        """
        return self._image

    def dragEnterEvent(self, event) -> None:
        """拖拽进入事件 - 检查是否为可接受的文件类型"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and len(urls) > 0:
                file_path = urls[0].toLocalFile()
                valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
                if file_path.lower().endswith(valid_extensions):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """拖拽释放事件 - 加载图片"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and len(urls) > 0:
                file_path = urls[0].toLocalFile()
                valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
                if file_path.lower().endswith(valid_extensions):
                    self.set_image(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()


class ImageCanvas(BaseCanvas):
    """图片显示画布，支持取色点拖动"""

    color_picked = Signal(int, tuple)  # 信号：索引, RGB颜色
    picker_moved = Signal(int, tuple)  # 信号：索引, (rel_x, rel_y)
    picker_dragging = Signal(int, bool)  # 信号：索引, 是否正在拖动

    def __init__(self, parent: Optional[QWidget] = None, picker_count: int = 5) -> None:
        super().__init__(parent, picker_count)
        self.setMouseTracking(True)

        self._pickers: list = []
        self._zoom_viewer: Optional[ZoomViewer] = None
        self._active_picker_index: int = -1

        # 高饱和度区域高亮相关
        self._show_high_saturation = False  # 是否显示高饱和度区域
        self._saturation_threshold = 0.7  # 饱和度阈值 (0.0-1.0)
        self._high_saturation_pixmap: Optional[QPixmap] = None  # 高亮遮罩缓存

        # 高明度区域高亮相关
        self._show_high_brightness = False  # 是否显示高明度区域
        self._brightness_threshold = 0.7  # 明度阈值 (0.0-1.0)
        self._high_brightness_pixmap: Optional[QPixmap] = None  # 高亮遮罩缓存

        # 创建放大视图
        self._zoom_viewer = ZoomViewer(self)

        # 创建取色点（初始隐藏）
        for i in range(self._picker_count):
            picker = ColorPicker(i, self)
            picker.position_changed.connect(self.on_picker_moved)
            picker.drag_started.connect(self._on_picker_drag_started)
            picker.drag_finished.connect(self._on_picker_drag_finished)
            picker.hide()  # 初始隐藏
            self._pickers.append(picker)
            self._picker_positions.append(QPoint(100 + i * 100, 100))
            self._picker_rel_positions.append(QPointF(0.5, 0.5))  # 默认在图片中心

        self.update_picker_positions()

    def set_image(self, image_path: str) -> None:
        """异步加载并显示图片（使用分阶段加载）"""
        super().set_image(image_path)

    def _setup_blurry_preview(self) -> None:
        """设置模糊预览（阶段1：快速显示缩略图）"""
        if self._original_pixmap and not self._original_pixmap.isNull():
            # 改变光标为默认
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # 模糊预览阶段不显示取色点，等待完整图片加载完成
            # 避免用户在预览阶段看到未就绪的采样点，提升用户体验

            # 更新加载提示
            self._loading_label.setText("正在加载高清图片...")

    def _on_image_loaded(self, image_data: bytes, width: int, height: int, fmt: str) -> None:
        """图片加载完成的回调"""
        super()._on_image_loaded(image_data, width, height, fmt)

        # 改变光标为默认
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_image_load_error(self, error_msg: str) -> None:
        """图片加载失败的回调"""
        # 恢复光标
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        print(f"图片加载失败: {error_msg}")

    def _setup_after_load(self, emit_sync: bool = True) -> None:
        """图片加载完成后的设置（阶段3：完整图片加载完成后）

        Args:
            emit_sync: 是否发射同步信号（从其他面板同步时设为False，防止循环）
        """
        if self._original_pixmap and not self._original_pixmap.isNull():
            # 设置放大视图的图片
            if self._zoom_viewer:
                self._zoom_viewer.set_image(self._image)

            # 确保取色点可见
            for picker in self._pickers:
                picker.show()

            # 初始化取色点位置（关键：防止同步时取色点重叠）
            self._init_picker_positions()

            # 更新取色点位置（使用完整图片尺寸）
            self.update_picker_positions()
            self.update()

            # 发送图片加载信号（只在独立导入时发射，防止双向同步循环）
            if emit_sync and self._pending_image_path:
                self.image_loaded.emit(self._pending_image_path)
                # 同时发送图片数据信号，用于同步到其他面板
                self.image_data_loaded.emit(self._original_pixmap, self._image)

            # 延迟提取颜色，让UI先响应，用户可以立即切换面板
            QTimer.singleShot(100, self.extract_all)

    def _update_picker_position(self, index: int, canvas_x: int, canvas_y: int) -> None:
        """更新单个取色点的位置"""
        if index < len(self._pickers):
            picker = self._pickers[index]
            picker.move(canvas_x - picker.radius, canvas_y - picker.radius)

    def _on_picker_drag_started(self, index: int) -> None:
        """取色点开始拖动"""
        self._active_picker_index = index
        if self._zoom_viewer:
            self._zoom_viewer.show()
        self._update_zoom_viewer()
        self.picker_dragging.emit(index, True)

    def _on_picker_drag_finished(self, index: int) -> None:
        """取色点结束拖动"""
        if self._zoom_viewer:
            self._zoom_viewer.hide()
        self._active_picker_index = -1
        self.picker_dragging.emit(index, False)

    def _on_picker_added(self, index: int) -> None:
        """添加取色点时的回调"""
        picker = ColorPicker(index, self)
        picker.position_changed.connect(self.on_picker_moved)
        picker.drag_started.connect(self._on_picker_drag_started)
        picker.drag_finished.connect(self._on_picker_drag_finished)
        # 如果有图片，显示取色点
        if self._image and not self._image.isNull():
            picker.show()
        else:
            picker.hide()
        self._pickers.append(picker)

    def _on_picker_removed(self, index: int) -> None:
        """移除取色点时的回调"""
        if index < len(self._pickers):
            picker = self._pickers.pop()
            picker.deleteLater()

    def _update_zoom_viewer(self) -> None:
        """更新放大视图的位置和内容"""
        if self._active_picker_index < 0 or self._image is None or not self._zoom_viewer:
            return

        picker_pos = self._picker_positions[self._active_picker_index]

        # 更新放大视图位置
        self._zoom_viewer.update_position(picker_pos)

        # 计算原始图片中的坐标
        image_pos = self.canvas_to_image_pos(picker_pos)
        if image_pos:
            self._zoom_viewer.set_center_position(image_pos)

    def extract_at(self, index: int) -> None:
        """提取指定取色点的颜色"""
        if self._image is None or self._image.isNull():
            return

        pos = self._picker_positions[index]
        image_pos = self.canvas_to_image_pos(pos)

        if image_pos:
            # 获取像素颜色
            color = self._image.pixelColor(image_pos.x(), image_pos.y())
            rgb = (color.red(), color.green(), color.blue())

            # 更新取色点显示的颜色
            if index < len(self._pickers):
                self._pickers[index].set_color(color)

            # 发送信号
            self.color_picked.emit(index, rgb)

        # 更新放大视图
        self._update_zoom_viewer()

    def extract_all(self) -> None:
        """提取所有取色点的颜色"""
        for i in range(len(self._pickers)):
            self.extract_at(i)

    def set_picker_positions_by_colors(self, dominant_colors: List[Tuple[int, int, int]], positions: List[Tuple[float, float]]) -> None:
        """根据主色调位置批量设置取色点位置

        将取色点移动到提取的主色调位置，并更新颜色显示。

        Args:
            dominant_colors: 主色调列表 [(r, g, b), ...]
            positions: 相对坐标列表 [(rel_x, rel_y), ...]
        """
        if not self._image or self._image.isNull():
            return

        if not positions or len(positions) == 0:
            return

        # 限制数量不超过取色点数量
        count = min(len(positions), len(self._pickers))

        for i in range(count):
            rel_x, rel_y = positions[i]
            # 限制在有效范围内
            rel_x = max(0.0, min(1.0, rel_x))
            rel_y = max(0.0, min(1.0, rel_y))

            # 更新相对坐标
            self._picker_rel_positions[i] = QPointF(rel_x, rel_y)

        # 更新画布坐标并移动取色点
        self.update_picker_positions()

        # 提取所有取色点的颜色
        self.extract_all()

        # 更新HSB色环上的采样点（如果存在）
        if len(dominant_colors) > 0:
            for i in range(count):
                if i < len(dominant_colors):
                    rgb = dominant_colors[i]
                    # 更新取色点显示的颜色
                    color = QColor(rgb[0], rgb[1], rgb[2])
                    self._pickers[i].set_color(color)

        self.update()

    def get_image(self) -> Optional[QImage]:
        """获取当前图片

        Returns:
            QImage: 当前图片对象，如果没有则返回 None
        """
        return self._image

    def resizeEvent(self, event) -> None:
        """窗口大小改变时重新调整图片"""
        super().resizeEvent(event)
        # 窗口大小改变时清除高亮遮罩缓存，需要重新生成
        if self._high_saturation_pixmap is not None:
            self._high_saturation_pixmap = None
        if self._high_brightness_pixmap is not None:
            self._high_brightness_pixmap = None

    def clear_image(self) -> None:
        """清空图片"""
        super().clear_image()

        # 隐藏取色点和放大视图
        for picker in self._pickers:
            picker.hide()
        if self._zoom_viewer:
            self._zoom_viewer.hide()

        # 清除高饱和度区域高亮
        self._show_high_saturation = False
        self._high_saturation_pixmap = None
        # 清除高明度区域高亮
        self._show_high_brightness = False
        self._high_brightness_pixmap = None

    def set_saturation_threshold(self, value: int) -> None:
        """设置饱和度阈值

        Args:
            value: 阈值百分比 (0-100)
        """
        self._saturation_threshold = value / 100.0
        # 如果当前正在显示高饱和度区域，清除缓存并刷新
        if self._show_high_saturation:
            self._high_saturation_pixmap = None
            self.update()

    def set_brightness_threshold(self, value: int) -> None:
        """设置明度阈值

        Args:
            value: 阈值百分比 (0-100)
        """
        self._brightness_threshold = value / 100.0
        # 如果当前正在显示高明度区域，清除缓存并刷新
        if self._show_high_brightness:
            self._high_brightness_pixmap = None
            self.update()

    def toggle_high_saturation_highlight(self, show: bool) -> None:
        """切换高饱和度区域高亮显示

        Args:
            show: 是否显示高饱和度区域
        """
        self._show_high_saturation = show
        if show:
            self._high_saturation_pixmap = None  # 清除缓存，重新生成
        self.update()

    def _generate_high_saturation_pixmap(self, display_rect: Tuple[int, int, int, int]) -> Optional[QPixmap]:
        """生成高饱和度区域高亮遮罩图

        Args:
            display_rect: 图片显示区域 (x, y, w, h)

        Returns:
            QPixmap: 高亮遮罩图
        """
        if self._image is None or self._image.isNull():
            return None

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 创建透明遮罩图
        highlight_pixmap = QPixmap(self.size())
        highlight_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(highlight_pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 导入颜色函数
        from .theme_colors import get_high_saturation_highlight_color
        highlight_color = get_high_saturation_highlight_color()

        # 计算缩放比例
        scale_x = self._image.width() / disp_w
        scale_y = self._image.height() / disp_h

        # 采样步长（性能优化）
        sample_step = 4

        # 遍历显示区域的像素
        for dy in range(0, disp_h, sample_step):
            for dx in range(0, disp_w, sample_step):
                # 计算对应的原始图片坐标
                img_x = int(dx * scale_x)
                img_y = int(dy * scale_y)

                # 边界检查
                img_x = min(img_x, self._image.width() - 1)
                img_y = min(img_y, self._image.height() - 1)

                # 获取像素颜色并计算饱和度
                color = self._image.pixelColor(img_x, img_y)
                r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0
                h, s, v = colorsys.rgb_to_hsv(r, g, b)

                # 如果饱和度超过阈值，绘制遮罩
                if s >= self._saturation_threshold:
                    painter.fillRect(
                        disp_x + dx,
                        disp_y + dy,
                        sample_step,
                        sample_step,
                        highlight_color
                    )

        painter.end()
        return highlight_pixmap

    def _draw_high_saturation_highlight(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制高饱和度区域高亮遮罩

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        if not self._show_high_saturation:
            return

        # 如果缓存不存在，生成遮罩图
        if self._high_saturation_pixmap is None:
            self._high_saturation_pixmap = self._generate_high_saturation_pixmap(display_rect)

        # 绘制遮罩图
        if self._high_saturation_pixmap:
            painter.drawPixmap(0, 0, self._high_saturation_pixmap)

        # 绘制信息提示
        self._draw_high_saturation_info(painter, display_rect)

    def _draw_high_saturation_info(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制高饱和度区域信息提示

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        if not self._show_high_saturation:
            return

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 准备文字
        threshold_percent = int(self._saturation_threshold * 100)
        text = f"高饱和度区域 (S ≥ {threshold_percent}%)"

        # 设置字体
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)

        # 计算文字尺寸
        text_rect = painter.boundingRect(QRect(), Qt.AlignmentFlag.AlignLeft, text)
        text_width = text_rect.width()
        text_height = text_rect.height()

        # 背景框位置和尺寸
        padding = 10
        box_width = text_width + padding * 2
        box_height = text_height + padding * 2
        box_x = disp_x + (disp_w - box_width) // 2
        box_y = disp_y + 20

        # 绘制半透明背景框
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(get_tooltip_bg_color())
        painter.drawRoundedRect(box_x, box_y, box_width, box_height, 6, 6)

        # 绘制文字
        from .theme_colors import get_high_saturation_border_color
        text_color = get_high_saturation_border_color()
        text_color.setAlpha(255)
        painter.setPen(text_color)
        painter.drawText(
            box_x + padding,
            box_y + padding + text_height - 4,
            text
        )

    def toggle_high_brightness_highlight(self, show: bool) -> None:
        """切换高明度区域高亮显示

        Args:
            show: 是否显示高明度区域
        """
        self._show_high_brightness = show
        if show:
            self._high_brightness_pixmap = None  # 清除缓存，重新生成
        self.update()

    def _generate_high_brightness_pixmap(self, display_rect: Tuple[int, int, int, int]) -> Optional[QPixmap]:
        """生成高明度区域高亮遮罩图

        Args:
            display_rect: 图片显示区域 (x, y, w, h)

        Returns:
            QPixmap: 高亮遮罩图
        """
        if self._image is None or self._image.isNull():
            return None

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 创建透明遮罩图
        highlight_pixmap = QPixmap(self.size())
        highlight_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(highlight_pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 导入颜色函数
        from .theme_colors import get_high_brightness_highlight_color
        highlight_color = get_high_brightness_highlight_color()

        # 计算缩放比例
        scale_x = self._image.width() / disp_w
        scale_y = self._image.height() / disp_h

        # 采样步长（性能优化）
        sample_step = 4

        # 遍历显示区域的像素
        for dy in range(0, disp_h, sample_step):
            for dx in range(0, disp_w, sample_step):
                # 计算对应的原始图片坐标
                img_x = int(dx * scale_x)
                img_y = int(dy * scale_y)

                # 边界检查
                img_x = min(img_x, self._image.width() - 1)
                img_y = min(img_y, self._image.height() - 1)

                # 获取像素颜色并计算明度
                color = self._image.pixelColor(img_x, img_y)
                r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0
                h, s, v = colorsys.rgb_to_hsv(r, g, b)

                # 如果明度超过阈值，绘制遮罩
                if v >= self._brightness_threshold:
                    painter.fillRect(
                        disp_x + dx,
                        disp_y + dy,
                        sample_step,
                        sample_step,
                        highlight_color
                    )

        painter.end()
        return highlight_pixmap

    def _draw_high_brightness_highlight(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制高明度区域高亮遮罩

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        if not self._show_high_brightness:
            return

        # 如果缓存不存在，生成遮罩图
        if self._high_brightness_pixmap is None:
            self._high_brightness_pixmap = self._generate_high_brightness_pixmap(display_rect)

        # 绘制遮罩图
        if self._high_brightness_pixmap:
            painter.drawPixmap(0, 0, self._high_brightness_pixmap)

        # 绘制信息提示
        self._draw_high_brightness_info(painter, display_rect)

    def _draw_high_brightness_info(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制高明度区域信息提示

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        if not self._show_high_brightness:
            return

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 准备文字
        threshold_percent = int(self._brightness_threshold * 100)
        text = f"高明度区域 (B ≥ {threshold_percent}%)"

        # 设置字体
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)

        # 计算文字尺寸
        text_rect = painter.boundingRect(QRect(), Qt.AlignmentFlag.AlignLeft, text)
        text_width = text_rect.width()
        text_height = text_rect.height()

        # 背景框位置和尺寸
        padding = 10
        box_width = text_width + padding * 2
        box_height = text_height + padding * 2
        box_x = disp_x + (disp_w - box_width) // 2
        box_y = disp_y + 20

        # 绘制半透明背景框
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(get_tooltip_bg_color())
        painter.drawRoundedRect(box_x, box_y, box_width, box_height, 6, 6)

        # 绘制文字
        from .theme_colors import get_high_brightness_border_color
        text_color = get_high_brightness_border_color()
        text_color.setAlpha(255)
        painter.setPen(text_color)
        painter.drawText(
            box_x + padding,
            box_y + padding + text_height - 4,
            text
        )

    def _draw_overlay(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制叠加内容

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        # 绘制高饱和度区域高亮遮罩（在图片上方）
        self._draw_high_saturation_highlight(painter, display_rect)
        # 绘制高明度区域高亮遮罩
        self._draw_high_brightness_highlight(painter, display_rect)


class LuminanceCanvas(BaseCanvas):
    """明度提取画布，支持取色点拖动和区域标注"""

    luminance_picked = Signal(int, str)  # 信号：索引, 区域编号
    picker_dragging = Signal(int, bool)  # 信号：索引, 是否正在拖动

    def __init__(self, parent: Optional[QWidget] = None, picker_count: int = 5) -> None:
        super().__init__(parent, picker_count)

        self._pickers: List[ColorPicker] = []
        self._picker_zones: List[str] = []  # 存储每个取色器的区域编号

        # Zone高亮相关
        self._highlighted_zone: int = -1  # 当前高亮显示的Zone (-1表示无)
        self._zone_highlight_pixmap: Optional[QPixmap] = None  # 高亮遮罩缓存

        # Zone高亮颜色配置 (Zone 0-7) - Adobe标准映射
        self._zone_highlight_colors: List[QColor] = get_picker_colors()

        # 创建取色点（初始隐藏）
        for i in range(self._picker_count):
            picker = ColorPicker(i, self)
            picker.position_changed.connect(self.on_picker_moved)
            picker.drag_started.connect(self._on_picker_drag_started)
            picker.drag_finished.connect(self._on_picker_drag_finished)
            picker.hide()  # 初始隐藏
            self._pickers.append(picker)
            self._picker_positions.append(QPoint(100 + i * 100, 100))
            self._picker_rel_positions.append(QPointF(0.5, 0.5))  # 默认在图片中心
            self._picker_zones.append("0-1")

        self.update_picker_positions()

    def _setup_blurry_preview(self) -> None:
        """设置模糊预览（阶段1：快速显示缩略图）"""
        if self._original_pixmap and not self._original_pixmap.isNull():
            # 改变光标为默认
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # 模糊预览阶段不显示取色点，等待完整图片加载完成
            # 避免用户在预览阶段看到未就绪的采样点，提升用户体验

            # 更新加载提示
            self._loading_label.setText("正在加载高清图片...")

    def _on_image_load_error(self, error_msg: str) -> None:
        """图片加载失败的回调"""
        print(f"明度面板图片加载失败: {error_msg}")

    def _setup_after_load(self, emit_sync: bool = True) -> None:
        """图片加载完成后的设置（阶段3：完整图片加载完成后）

        Args:
            emit_sync: 是否发射同步信号（从其他面板同步时设为False，防止循环）
        """
        if self._original_pixmap and not self._original_pixmap.isNull():
            # 确保取色点可见
            for picker in self._pickers:
                picker.show()

            # 改变光标为默认
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # 初始化取色点位置（关键：防止同步时取色点重叠）
            self._init_picker_positions()

            # 更新取色点位置（使用完整图片尺寸）
            self.update_picker_positions()
            self.update()

            # 发送图片加载信号（只在独立导入时发射，防止双向同步循环）
            if emit_sync and self._pending_image_path:
                self.image_loaded.emit(self._pending_image_path)

            # 延迟提取区域，让UI先响应，用户可以立即切换面板
            QTimer.singleShot(100, self.extract_all)

    def _update_picker_position(self, index: int, canvas_x: int, canvas_y: int) -> None:
        """更新单个取色点的位置"""
        if index < len(self._pickers):
            picker = self._pickers[index]
            picker.move(canvas_x - picker.radius, canvas_y - picker.radius)

    def _on_picker_drag_started(self, index: int) -> None:
        """取色点开始拖动"""
        if index < len(self._pickers):
            picker = self._pickers[index]
            picker.set_active(True)
        self.picker_dragging.emit(index, True)

    def _on_picker_drag_finished(self, index: int) -> None:
        """取色点结束拖动"""
        if index < len(self._pickers):
            picker = self._pickers[index]
            picker.set_active(False)
        self.picker_dragging.emit(index, False)

    def _on_picker_added(self, index: int) -> None:
        """添加取色点时的回调"""
        picker = ColorPicker(index, self)
        picker.position_changed.connect(self.on_picker_moved)
        picker.drag_started.connect(self._on_picker_drag_started)
        picker.drag_finished.connect(self._on_picker_drag_finished)
        # 如果有图片，显示取色点
        if self._image and not self._image.isNull():
            picker.show()
        else:
            picker.hide()
        self._pickers.append(picker)
        self._picker_zones.append("0-1")

    def _on_picker_removed(self, index: int) -> None:
        """移除取色点时的回调"""
        if index < len(self._pickers):
            picker = self._pickers.pop()
            picker.deleteLater()
            self._picker_zones.pop()

    def extract_at(self, index: int) -> None:
        """提取指定取色点的区域编号"""
        if self._image is None or self._image.isNull():
            return

        pos = self._picker_positions[index]
        image_pos = self.canvas_to_image_pos(pos)

        if image_pos:
            # 获取像素颜色
            color = self._image.pixelColor(image_pos.x(), image_pos.y())
            luminance = get_luminance(color.red(), color.green(), color.blue())
            zone = get_zone(luminance)

            # 更新区域编号
            self._picker_zones[index] = zone

            # 发送信号
            self.luminance_picked.emit(index, zone)

    def extract_all(self) -> None:
        """提取所有取色点的区域编号"""
        for i in range(len(self._pickers)):
            self.extract_at(i)

    def _draw_overlay(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制叠加内容"""
        # 绘制Zone高亮遮罩（在图片上方）
        self._draw_zone_highlight(painter, display_rect)

        # 绘制区域标注
        self._draw_zone_labels(painter, display_rect)

    def _draw_zone_labels(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制区域标注（白色小方框+黑色文字）"""
        # 如果正在加载中，不显示Zone标签
        if self._is_loading:
            return

        disp_x, disp_y, disp_w, disp_h = display_rect

        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        for i, pos in enumerate(self._picker_positions):
            # 检查取色器是否在图片显示区域内
            img_x = pos.x() - disp_x
            img_y = pos.y() - disp_y

            if 0 <= img_x < disp_w and 0 <= img_y < disp_h:
                zone = self._picker_zones[i]

                # 计算文字尺寸
                text_rect = painter.boundingRect(QRect(), Qt.AlignmentFlag.AlignCenter, zone)
                text_width = text_rect.width()
                text_height = text_rect.height()

                # 方框尺寸（稍大于文字）
                box_width = text_width + 8
                box_height = text_height + 4

                # 方框位置（取色器上方）
                box_x = pos.x() - box_width // 2
                box_y = pos.y() - 35  # 取色器上方35像素

                # 绘制深色填充方框
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(40, 40, 40, 200))
                painter.drawRect(box_x, box_y, box_width, box_height)

                # 绘制白色文字
                painter.setPen(QColor(255, 255, 255))
                text_x = box_x + (box_width - text_width) // 2
                text_y = box_y + (box_height - text_height) // 2
                painter.drawText(text_x, text_y + text_height - 2, zone)

    def clear_image(self) -> None:
        """清空图片"""
        super().clear_image()

        # 隐藏取色点
        for picker in self._pickers:
            picker.hide()

        # 重置区域编号
        self._picker_zones = ["0-1"] * len(self._pickers)

    def get_picker_zones(self) -> List[str]:
        """获取所有取色器的区域编号

        Returns:
            list: 区域编号列表
        """
        return self._picker_zones.copy()

    def highlight_zone(self, zone: int) -> None:
        """高亮显示指定Zone的亮度范围

        Args:
            zone: Zone编号 (0-7)
        """
        if not (0 <= zone <= 7):
            return

        if self._image is None or self._image.isNull():
            return

        self._highlighted_zone = zone
        self._zone_highlight_pixmap = None  # 清除缓存，重新生成
        self.update()

    def clear_zone_highlight(self) -> None:
        """清除Zone高亮显示"""
        self._highlighted_zone = -1
        self._zone_highlight_pixmap = None
        self.update()

    def _generate_zone_highlight_pixmap(self, display_rect: Tuple[int, int, int, int]) -> Optional[QPixmap]:
        """生成Zone高亮遮罩图

        Args:
            display_rect: 图片显示区域 (x, y, w, h)

        Returns:
            QPixmap: 高亮遮罩图
        """
        if self._image is None or self._image.isNull():
            return None

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 创建透明遮罩图
        highlight_pixmap = QPixmap(self.size())
        highlight_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(highlight_pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 获取当前Zone的颜色
        zone_color = self._zone_highlight_colors[self._highlighted_zone]

        # 计算亮度范围
        min_lum = self._highlighted_zone * 32
        max_lum = (self._highlighted_zone + 1) * 32 - 1

        # 计算缩放比例
        scale_x = self._image.width() / disp_w
        scale_y = self._image.height() / disp_h

        # 采样步长（性能优化）
        sample_step = 4

        # 遍历显示区域的像素
        for dy in range(0, disp_h, sample_step):
            for dx in range(0, disp_w, sample_step):
                # 计算对应的原始图片坐标
                img_x = int(dx * scale_x)
                img_y = int(dy * scale_y)

                # 边界检查
                img_x = min(img_x, self._image.width() - 1)
                img_y = min(img_y, self._image.height() - 1)

                # 获取像素颜色并计算亮度
                color = self._image.pixelColor(img_x, img_y)
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

    def _draw_zone_highlight(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制Zone高亮遮罩

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        if self._highlighted_zone < 0:
            return

        # 如果缓存不存在，生成遮罩图
        if self._zone_highlight_pixmap is None:
            self._zone_highlight_pixmap = self._generate_zone_highlight_pixmap(display_rect)

        # 绘制遮罩图
        if self._zone_highlight_pixmap:
            painter.drawPixmap(0, 0, self._zone_highlight_pixmap)

        # 绘制Zone信息提示
        self._draw_zone_highlight_info(painter, display_rect)

    def _draw_zone_highlight_info(self, painter: QPainter, display_rect: Tuple[int, int, int, int]) -> None:
        """绘制Zone高亮信息提示

        Args:
            painter: QPainter对象
            display_rect: 图片显示区域 (x, y, w, h)
        """
        if self._highlighted_zone < 0:
            return

        disp_x, disp_y, disp_w, disp_h = display_rect

        # 准备文字 - Adobe标准: 黑色(0-10%), 阴影(10-30%), 中间调(30-70%), 高光(70-90%), 白色(90-100%)
        zone_labels = ["0-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7", "7-8"]
        zone_names = [
            "黑色", "黑色", "阴影", "中间调",
            "中间调", "中间调", "高光", "白色"
        ]
        label = zone_labels[self._highlighted_zone]
        name = zone_names[self._highlighted_zone]

        # 计算亮度范围
        min_lum = self._highlighted_zone * 32
        max_lum = (self._highlighted_zone + 1) * 32 - 1

        text = f"{label} ({name}) | 亮度: {min_lum}-{max_lum}"

        # 设置字体
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)

        # 计算文字尺寸
        text_rect = painter.boundingRect(QRect(), Qt.AlignmentFlag.AlignLeft, text)
        text_width = text_rect.width()
        text_height = text_rect.height()

        # 背景框位置和尺寸
        padding = 10
        box_width = text_width + padding * 2
        box_height = text_height + padding * 2
        box_x = disp_x + (disp_w - box_width) // 2
        box_y = disp_y + 20

        # 绘制半透明背景框
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(get_tooltip_bg_color())
        painter.drawRoundedRect(box_x, box_y, box_width, box_height, 6, 6)

        # 绘制文字
        text_color = self._zone_highlight_colors[self._highlighted_zone]
        # 使用不透明版本的颜色
        text_color.setAlpha(255)
        painter.setPen(text_color)
        painter.drawText(
            box_x + padding,
            box_y + padding + text_height - 4,
            text
        )


__all__ = [
    'ImageLoader',
    'BaseCanvas',
    'ImageCanvas',
    'LuminanceCanvas',
]