# 标准库导入
import math
from abc import abstractmethod
from typing import List, Any

# 第三方库导入
from PySide6.QtCore import QThread, Signal


class BaseBatchLoader(QThread):
    """通用分批异步加载基类
    
    提供分批加载数据的通用框架，子类只需实现：
    - get_total_batches(): 返回总批次数
    - load_batch(batch_idx): 加载指定批次的数据
    
    特性：
    - 支持取消机制
    - 支持批次大小配置
    - 提供标准信号通知
    """
    
    batch_ready = Signal(int, list)
    batch_finished = Signal()
    loading_finished = Signal()
    
    def __init__(self, batch_size: int = 10, parent=None):
        """初始化加载器
        
        Args:
            batch_size: 每批加载数量（默认10）
            parent: 父对象
        """
        super().__init__(parent)
        self._batch_size = batch_size
        self._is_cancelled = False
    
    def cancel(self) -> None:
        """请求取消加载（线程安全）"""
        self._is_cancelled = True
    
    def _check_cancelled(self) -> bool:
        """检查是否被取消
        
        Returns:
            bool: True表示已取消
        """
        return self._is_cancelled
    
    def run(self) -> None:
        """分批加载数据（模板方法）"""
        total_batches = self.get_total_batches()
        
        if total_batches == 0:
            self.loading_finished.emit()
            return
        
        for batch_idx in range(total_batches):
            if self._check_cancelled():
                return
            
            batch_data = self.load_batch(batch_idx)
            
            if self._check_cancelled():
                return
            
            self.batch_ready.emit(batch_idx, batch_data)
            self.batch_finished.emit()
            
            self.msleep(10)
        
        self.loading_finished.emit()
    
    @abstractmethod
    def get_total_batches(self) -> int:
        """获取总批次数
        
        Returns:
            int: 总批次数
        """
        pass
    
    @abstractmethod
    def load_batch(self, batch_idx: int) -> List[Any]:
        """加载指定批次的数据
        
        Args:
            batch_idx: 批次索引（从0开始）
            
        Returns:
            list: 批次数据列表
        """
        pass
    
    def calculate_total_batches(self, total_items: int) -> int:
        """计算总批次数（辅助方法）
        
        Args:
            total_items: 总数据项数
            
        Returns:
            int: 总批次数
        """
        if total_items <= 0:
            return 0
        return math.ceil(total_items / self._batch_size)


__all__ = ['BaseBatchLoader']
