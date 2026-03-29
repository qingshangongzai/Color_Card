"""HSB色环组件测试

测试采样点更新、数量调整等功能。
"""

# 第三方库导入
import pytest
from PySide6.QtCore import Qt

# 项目模块导入
from ui.color_wheel import HSBColorWheel


class TestUpdateSamplePoint:
    """测试 update_sample_point 方法"""

    def test_update_valid_index(self, qtbot):
        """测试更新有效索引的采样点"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        # 先设置3个采样点
        wheel.set_sample_count(3)
        assert len(wheel._sample_colors) == 3

        # 更新索引1的采样点
        wheel.update_sample_point(1, (255, 0, 0))

        # 验证更新成功
        assert wheel._sample_colors[1] == (255, 0, 0)
        # 其他采样点保持不变
        assert wheel._sample_colors[0] == (128, 128, 128)
        assert wheel._sample_colors[2] == (128, 128, 128)

    def test_update_first_index(self, qtbot):
        """测试更新第一个采样点"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(2)
        wheel.update_sample_point(0, (0, 255, 0))

        assert wheel._sample_colors[0] == (0, 255, 0)

    def test_update_last_index(self, qtbot):
        """测试更新最后一个采样点"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(3)
        wheel.update_sample_point(2, (0, 0, 255))

        assert wheel._sample_colors[2] == (0, 0, 255)

    def test_negative_index_ignored(self, qtbot):
        """测试负索引被忽略"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(2)
        original_colors = wheel._sample_colors.copy()

        # 尝试用负索引更新
        wheel.update_sample_point(-1, (255, 0, 0))

        # 采样点应保持不变
        assert wheel._sample_colors == original_colors

    def test_out_of_range_index_ignored(self, qtbot):
        """测试超出范围的索引被忽略"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(2)
        original_colors = wheel._sample_colors.copy()

        # 尝试用超出范围的索引更新
        wheel.update_sample_point(5, (255, 0, 0))

        # 采样点应保持不变
        assert wheel._sample_colors == original_colors

    def test_empty_list_ignored(self, qtbot):
        """测试空列表时任何索引都被忽略"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        # 确保列表为空
        wheel.clear_sample_points()
        assert len(wheel._sample_colors) == 0

        # 尝试更新索引0
        wheel.update_sample_point(0, (255, 0, 0))

        # 列表仍应为空
        assert len(wheel._sample_colors) == 0

    def test_boundary_index_exact(self, qtbot):
        """测试边界索引（刚好在范围内）"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(3)

        # 索引2是最后一个有效索引
        wheel.update_sample_point(2, (255, 255, 0))
        assert wheel._sample_colors[2] == (255, 255, 0)

        # 索引3超出范围
        original_colors = wheel._sample_colors.copy()
        wheel.update_sample_point(3, (0, 255, 255))
        assert wheel._sample_colors == original_colors


class TestSetSampleCount:
    """测试 set_sample_count 方法"""

    def test_increase_count(self, qtbot):
        """测试增加采样点数量"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(2)
        assert len(wheel._sample_colors) == 2

        wheel.set_sample_count(5)
        assert len(wheel._sample_colors) == 5
        # 新增采样点应为默认灰色
        assert wheel._sample_colors[2] == (128, 128, 128)
        assert wheel._sample_colors[4] == (128, 128, 128)

    def test_decrease_count(self, qtbot):
        """测试减少采样点数量"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(5)
        wheel.update_sample_point(4, (255, 0, 0))

        wheel.set_sample_count(3)
        assert len(wheel._sample_colors) == 3
        # 超出新范围的采样点被移除
        assert (255, 0, 0) not in wheel._sample_colors

    def test_same_count(self, qtbot):
        """测试设置相同数量"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(3)
        wheel.update_sample_point(1, (255, 0, 0))

        wheel.set_sample_count(3)
        assert len(wheel._sample_colors) == 3
        assert wheel._sample_colors[1] == (255, 0, 0)

    def test_zero_count(self, qtbot):
        """测试设置数量为0"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(3)
        wheel.set_sample_count(0)
        assert len(wheel._sample_colors) == 0


class TestClearSamplePoints:
    """测试 clear_sample_points 方法"""

    def test_clear_removes_all(self, qtbot):
        """测试清除所有采样点"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(3)
        wheel.clear_sample_points()

        assert len(wheel._sample_colors) == 0

    def test_clear_allows_readd(self, qtbot):
        """测试清除后可以重新添加"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_count(3)
        wheel.clear_sample_points()
        wheel.set_sample_count(2)

        assert len(wheel._sample_colors) == 2
        wheel.update_sample_point(0, (255, 0, 0))
        assert wheel._sample_colors[0] == (255, 0, 0)


class TestSetSampleColors:
    """测试 set_sample_colors 方法"""

    def test_set_colors(self, qtbot):
        """测试设置采样点颜色列表"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        wheel.set_sample_colors(colors)

        assert wheel._sample_colors == colors

    def test_set_empty_list(self, qtbot):
        """测试设置空列表"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_colors([])
        assert wheel._sample_colors == []

    def test_set_none(self, qtbot):
        """测试设置 None"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        wheel.set_sample_colors(None)
        assert wheel._sample_colors == []


class TestIntegration:
    """集成测试"""

    def test_typical_workflow(self, qtbot):
        """测试典型工作流程"""
        wheel = HSBColorWheel()
        qtbot.addWidget(wheel)

        # 1. 设置5个采样点
        wheel.set_sample_count(5)
        assert len(wheel._sample_colors) == 5

        # 2. 更新其中几个
        wheel.update_sample_point(0, (255, 0, 0))
        wheel.update_sample_point(2, (0, 255, 0))
        wheel.update_sample_point(4, (0, 0, 255))

        assert wheel._sample_colors[0] == (255, 0, 0)
        assert wheel._sample_colors[2] == (0, 255, 0)
        assert wheel._sample_colors[4] == (0, 0, 255)

        # 3. 减少采样点
        wheel.set_sample_count(3)
        assert len(wheel._sample_colors) == 3
        # 保留前3个
        assert wheel._sample_colors[0] == (255, 0, 0)
        assert wheel._sample_colors[2] == (0, 255, 0)

        # 4. 尝试更新超出范围的索引（应被忽略）
        wheel.update_sample_point(5, (255, 255, 255))
        assert len(wheel._sample_colors) == 3

        # 5. 清除所有
        wheel.clear_sample_points()
        assert len(wheel._sample_colors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
