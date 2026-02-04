"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: base_card
功能描述: 卡片组件基类，提供统一的卡片面板管理功能

作者: 青山公仔
创建日期: 2026-02-05
"""

# 第三方库导入
from PySide6.QtWidgets import QHBoxLayout, QWidget


class BaseCard(QWidget):
    """卡片基类，提供统一的卡片接口
    
    子类需要实现：
        - setup_ui(): 设置界面
        - clear(): 清空显示
    """
    
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面（子类必须实现）"""
        raise NotImplementedError("子类必须实现 setup_ui 方法")
    
    def clear(self):
        """清空显示（子类必须实现）"""
        raise NotImplementedError("子类必须实现 clear 方法")


class BaseCardPanel(QWidget):
    """卡片面板基类，提供统一的卡片管理功能
    
    功能：
        - 卡片列表管理
        - 卡片数量控制（2-5个）
        - 批量清空卡片
    """
    
    def __init__(self, parent=None, card_count: int = 5):
        super().__init__(parent)
        self._card_count = card_count
        self.cards = []
        self.setup_ui()
        self._create_initial_cards()
    
    def _create_initial_cards(self):
        """创建初始卡片"""
        for i in range(self._card_count):
            card = self._create_card(i)
            self.cards.append(card)
            self.layout().addWidget(card)
    
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
    
    def set_card_count(self, count: int):
        """设置卡片数量
        
        Args:
            count: 卡片数量 (2-5)
        """
        if count < 2 or count > 5:
            return
        
        if count == self._card_count:
            return
        
        old_count = self._card_count
        self._card_count = count
        
        layout = self.layout()
        
        if count > old_count:
            self._add_cards(old_count, count)
        else:
            self._remove_cards(old_count, count)
    
    def _add_cards(self, old_count: int, new_count: int):
        """增加卡片（子类重写）"""
        for i in range(old_count, new_count):
            card = self._create_card(i)
            self.cards.append(card)
            self.layout().addWidget(card)
    
    def _remove_cards(self, old_count: int, new_count: int):
        """减少卡片"""
        for i in range(old_count - 1, new_count - 1, -1):
            card = self.cards.pop()
            self.layout().removeWidget(card)
            card.deleteLater()
    
    def _create_card(self, index: int):
        """创建单个卡片（子类必须实现）
        
        Args:
            index: 卡片索引
            
        Returns:
            BaseCard: 卡片实例
        """
        raise NotImplementedError("子类必须实现 _create_card 方法")
    
    def clear_all(self):
        """清空所有卡片"""
        for card in self.cards:
            card.clear()
