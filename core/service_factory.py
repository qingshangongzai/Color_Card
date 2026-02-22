"""服务工厂模块

提供统一的服务获取入口，实现服务单例化和延迟创建。
"""


class ServiceFactory:
    """服务工厂，管理服务的创建和生命周期
    
    特性：
    - 延迟创建：服务在首次使用时才创建
    - 单例模式：同一服务只创建一个实例
    - 线程安全：使用锁保护实例创建
    """
    
    _instances = {}
    _lock = None
    
    @classmethod
    def _get_lock(cls):
        """延迟获取锁（避免启动时导入 threading）
        
        Returns:
            threading.Lock: 线程锁实例
        """
        if cls._lock is None:
            import threading
            cls._lock = threading.Lock()
        return cls._lock
    
    @classmethod
    def get_color_service(cls, parent=None):
        """获取颜色服务实例
        
        Args:
            parent: 父对象（首次创建时使用）
            
        Returns:
            ColorService: 颜色服务实例
        """
        if 'color' not in cls._instances:
            with cls._get_lock():
                if 'color' not in cls._instances:
                    from .color_service import ColorService
                    cls._instances['color'] = ColorService(parent)
        return cls._instances['color']
    
    @classmethod
    def get_palette_service(cls, parent=None):
        """获取配色服务实例
        
        Args:
            parent: 父对象（首次创建时使用）
            
        Returns:
            PaletteService: 配色服务实例
        """
        if 'palette' not in cls._instances:
            with cls._get_lock():
                if 'palette' not in cls._instances:
                    from .palette_service import PaletteService
                    cls._instances['palette'] = PaletteService(parent)
        return cls._instances['palette']
    
    @classmethod
    def get_image_service(cls, parent=None):
        """获取图片服务实例
        
        Args:
            parent: 父对象（首次创建时使用）
            
        Returns:
            ImageService: 图片服务实例
        """
        if 'image' not in cls._instances:
            with cls._get_lock():
                if 'image' not in cls._instances:
                    from .image_service import ImageService
                    cls._instances['image'] = ImageService(parent)
        return cls._instances['image']
    
    @classmethod
    def get_luminance_service(cls, parent=None):
        """获取明度服务实例
        
        Args:
            parent: 父对象（首次创建时使用）
            
        Returns:
            LuminanceService: 明度服务实例
        """
        if 'luminance' not in cls._instances:
            with cls._get_lock():
                if 'luminance' not in cls._instances:
                    from .luminance_service import LuminanceService
                    cls._instances['luminance'] = LuminanceService(parent)
        return cls._instances['luminance']
    
    @classmethod
    def clear_all(cls):
        """清除所有服务实例（用于测试或重置）"""
        with cls._get_lock():
            cls._instances.clear()
