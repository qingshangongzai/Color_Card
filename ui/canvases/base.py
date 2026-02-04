# 标准库导入
import io
from typing import List, Optional, Tuple

# 第三方库导入
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget
from qfluentwidgets import Action, FluentIcon, RoundMenu


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


class BaseCanvas(QWidget):
    """画布基类，提供图片加载、显示和取色点管理的公共功能

    功能：
        - 异步图片加载
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
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #2a2a2a; border-radius: 8px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._original_pixmap: Optional[QPixmap] = None
        self._image: Optional[QImage] = None
        self._picker_positions: List[QPoint] = []
        self._picker_rel_positions: List[QPointF] = []
        self._loader: Optional[ImageLoader] = None
        self._pending_image_path: Optional[str] = None
        self._picker_count: int = picker_count

    def set_image(self, image_path: str) -> None:
        """异步加载并显示图片

        Args:
            image_path: 图片文件路径
        """
        # 保存图片路径
        self._pending_image_path = image_path

        # 如果已有加载线程在运行，先停止
        if self._loader is not None and self._loader.isRunning():
            self._loader.quit()
            self._loader.wait()

        # 创建并启动加载线程
        self._loader = ImageLoader(image_path)
        self._loader.loaded.connect(self._on_image_loaded)
        self._loader.error.connect(self._on_image_load_error)
        self._loader.finished.connect(self._cleanup_loader)
        self._loader.start()

    def _cleanup_loader(self) -> None:
        """清理加载线程"""
        if self._loader is not None:
            self._loader.deleteLater()
            self._loader = None

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
        print(f"图片加载失败: {error_msg}")

    def set_image_data(self, pixmap: QPixmap, image: QImage) -> None:
        """直接使用已加载的图片数据（避免重复加载）

        Args:
            pixmap: QPixmap 对象
            image: QImage 对象
        """
        self._original_pixmap = pixmap
        self._image = image
        self._setup_after_load()

    def _setup_after_load(self) -> None:
        """图片加载完成后的设置

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
        painter.fillRect(self.rect(), QColor(42, 42, 42))

        # 绘制图片（使用原始高分辨率图片，实时缩放显示）
        if self._original_pixmap and not self._original_pixmap.isNull():
            display_rect = self.get_display_rect()
            if display_rect:
                x, y, w, h = display_rect
                target_rect = QRect(x, y, w, h)
                painter.drawPixmap(target_rect, self._original_pixmap, self._original_pixmap.rect())

                # 子类可以在此绘制额外的内容
                self._draw_overlay(painter, display_rect)
        else:
            # 没有图片时显示提示文字
            painter.setPen(QColor(150, 150, 150))
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
