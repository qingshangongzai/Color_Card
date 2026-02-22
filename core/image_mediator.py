# 标准库导入
from typing import Optional, Tuple

# 第三方库导入
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QPixmap


class ImageMediator(QObject):
    """图片状态中介者，统一管理图片状态，实现面板间的解耦同步
    
    功能：
        - 集中管理图片状态（QPixmap, QImage）
        - 通过信号广播图片更新/清空事件
        - 通过 source_id 参数防止循环同步
    
    使用方式：
        1. 创建中介者实例
        2. 各面板连接 image_updated 和 image_cleared 信号
        3. 面板加载/清空图片时调用 set_image/clear_image 方法
        4. 通过 source_id 标识操作来源，防止循环
    """

    image_updated = Signal(object, object, str)  # QPixmap, QImage, source_id
    image_cleared = Signal(str)  # source_id

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """初始化图片中介者
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self._image: Optional[QImage] = None
        self._current_source_id: str = ""

    def set_image(self, pixmap: QPixmap, image: QImage, source_id: str) -> None:
        """设置图片并广播更新事件
        
        Args:
            pixmap: QPixmap 对象
            image: QImage 对象
            source_id: 操作来源标识（用于防止循环同步）
        """
        self._pixmap = pixmap
        self._image = image
        self._current_source_id = source_id
        self.image_updated.emit(pixmap, image, source_id)

    def clear_image(self, source_id: str) -> None:
        """清空图片并广播清空事件
        
        Args:
            source_id: 操作来源标识（用于防止循环同步）
        """
        self._pixmap = None
        self._image = None
        self._current_source_id = source_id
        self.image_cleared.emit(source_id)

    def get_current_image(self) -> Tuple[Optional[QPixmap], Optional[QImage]]:
        """获取当前图片
        
        Returns:
            tuple: (QPixmap, QImage) 或 (None, None)
        """
        return self._pixmap, self._image

    def get_current_source_id(self) -> str:
        """获取当前操作的来源标识
        
        Returns:
            str: 来源标识
        """
        return self._current_source_id

    def has_image(self) -> bool:
        """检查是否有图片
        
        Returns:
            bool: 是否有图片
        """
        return self._pixmap is not None and self._image is not None


__all__ = ['ImageMediator']
