"""色卡组件测试

测试色卡关闭事件等功能。
"""

# 第三方库导入
import pytest
from PySide6.QtCore import Qt
from qfluentwidgets import qconfig

# 项目模块导入
from ui.cards import ColorCard


class TestColorCardCloseEvent:
    """测试 ColorCard 的 closeEvent 方法（简化后）"""

    def test_close_event_disconnects_signal(self, qtbot):
        """测试关闭事件正确断开信号"""
        card = ColorCard(0)
        qtbot.addWidget(card)

        # 验证信号已连接
        assert hasattr(card, '_theme_connection')

        # 模拟关闭事件
        card.close()

        # 验证信号已断开且属性已删除
        assert not hasattr(card, '_theme_connection')

    def test_close_event_without_theme_connection(self, qtbot):
        """测试没有主题连接时关闭不报错"""
        card = ColorCard(0)
        qtbot.addWidget(card)

        # 手动删除主题连接（模拟异常情况）
        if hasattr(card, '_theme_connection'):
            delattr(card, '_theme_connection')

        # 关闭不应报错
        card.close()

        # 验证正常关闭
        assert not card.isVisible()

    def test_multiple_close_calls(self, qtbot):
        """测试多次调用关闭不会报错"""
        card = ColorCard(0)
        qtbot.addWidget(card)

        # 第一次关闭
        card.close()
        assert not hasattr(card, '_theme_connection')

        # 第二次关闭（不应报错）
        card.close()

    def test_theme_signal_works_before_close(self, qtbot):
        """测试关闭前主题信号正常工作"""
        card = ColorCard(0)
        qtbot.addWidget(card)

        # 验证信号连接存在
        assert hasattr(card, '_theme_connection')

        # 触发主题变化信号（不应报错）
        qconfig.themeChangedFinished.emit()

        # 关闭后
        card.close()
        assert not hasattr(card, '_theme_connection')

    def test_close_event_simplified_code(self, qtbot):
        """测试简化后的 closeEvent 代码逻辑"""
        card = ColorCard(0)
        qtbot.addWidget(card)

        # 验证初始状态：有主题连接
        assert hasattr(card, '_theme_connection')

        # 执行关闭
        card.close()

        # 验证最终状态：无主题连接
        assert not hasattr(card, '_theme_connection')

        # 验证可以安全地再次关闭（不会抛出异常）
        try:
            card.close()
        except Exception as e:
            pytest.fail(f"第二次关闭不应抛出异常: {e}")


class TestColorCardBasic:
    """测试 ColorCard 基本功能"""

    def test_card_creation(self, qtbot):
        """测试色卡创建"""
        card = ColorCard(0)
        qtbot.addWidget(card)

        # 验证创建成功
        assert card.index == 0
        assert hasattr(card, '_theme_connection')

    def test_card_creation_with_index(self, qtbot):
        """测试使用不同索引创建色卡"""
        card = ColorCard(5)
        qtbot.addWidget(card)

        assert card.index == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
