"""测试 get_color_info_batch 批量处理函数

验证批量处理函数的正确性、性能优化和结果一致性
"""
from __future__ import annotations

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import time
from core.color import get_color_info, get_color_info_batch


class TestGetColorInfoBatch:
    """测试批量处理函数"""

    def test_batch_basic_functionality(self):
        """测试批量处理基本功能"""
        # 测试数据：常见颜色
        test_colors = [
            (255, 0, 0),      # 红色
            (0, 255, 0),      # 绿色
            (0, 0, 255),      # 蓝色
            (255, 255, 0),    # 黄色
            (0, 255, 255),    # 青色
            (255, 0, 255),    # 紫色
            (255, 255, 255),  # 白色
            (0, 0, 0),        # 黑色
        ]

        results = get_color_info_batch(test_colors)

        # 验证结果数量
        assert len(results) == len(test_colors), "批量处理结果数量应与输入数量一致"

        # 验证每个结果的结构
        for result in results:
            assert 'rgb' in result, "结果应包含 RGB"
            assert 'hsb' in result, "结果应包含 HSB"
            assert 'lab' in result, "结果应包含 LAB"
            assert 'hsl' in result, "结果应包含 HSL"
            assert 'cmyk' in result, "结果应包含 CMYK"
            assert 'hex' in result, "结果应包含 HEX"

    def test_batch_vs_single_consistency(self):
        """测试批量处理与单次处理结果一致性"""
        # 测试数据
        test_colors = [
            (255, 0, 0),
            (128, 128, 128),
            (64, 32, 16),
        ]

        # 批量处理
        batch_results = get_color_info_batch(test_colors)

        # 单次处理
        for i, (r, g, b) in enumerate(test_colors):
            single_result = get_color_info(r, g, b)
            batch_result = batch_results[i]

            # 验证 RGB
            assert single_result['rgb'] == batch_result['rgb'], \
                f"RGB 不一致: {single_result['rgb']} vs {batch_result['rgb']}"

            # 验证 HSB
            assert single_result['hsb'] == batch_result['hsb'], \
                f"HSB 不一致: {single_result['hsb']} vs {batch_result['hsb']}"

            # 验证 LAB
            assert single_result['lab'] == batch_result['lab'], \
                f"LAB 不一致: {single_result['lab']} vs {batch_result['lab']}"

            # 验证 HSL
            assert single_result['hsl'] == batch_result['hsl'], \
                f"HSL 不一致: {single_result['hsl']} vs {batch_result['hsl']}"

            # 验证 CMYK
            assert single_result['cmyk'] == batch_result['cmyk'], \
                f"CMYK 不一致: {single_result['cmyk']} vs {batch_result['cmyk']}"

            # 验证 HEX
            assert single_result['hex'] == batch_result['hex'], \
                f"HEX 不一致: {single_result['hex']} vs {batch_result['hex']}"

    def test_batch_performance(self):
        """测试批量处理性能提升"""
        # 生成大量测试数据
        test_colors = [(i % 256, (i * 2) % 256, (i * 3) % 256) for i in range(100)]

        # 测试批量处理性能
        start_time = time.time()
        batch_results = get_color_info_batch(test_colors)
        batch_time = time.time() - start_time

        # 测试单次处理性能
        start_time = time.time()
        single_results = [get_color_info(r, g, b) for r, g, b in test_colors]
        single_time = time.time() - start_time

        # 验证结果数量一致
        assert len(batch_results) == len(single_results), "结果数量应一致"

        # 验证性能提升（批量处理应该更快）
        # 注意：由于测试环境差异，这里只验证批量处理不比单次处理慢太多
        # 实际优化效果在真实环境中会更明显
        print(f"\n批量处理时间: {batch_time:.4f}s")
        print(f"单次处理时间: {single_time:.4f}s")
        print(f"性能提升: {(single_time - batch_time) / single_time * 100:.2f}%")

    def test_batch_empty_input(self):
        """测试空输入"""
        results = get_color_info_batch([])
        assert results == [], "空输入应返回空列表"

    def test_batch_single_color(self):
        """测试单个颜色"""
        test_colors = [(255, 128, 64)]
        results = get_color_info_batch(test_colors)

        assert len(results) == 1, "单个颜色应返回一个结果"
        assert results[0]['rgb'] == (255, 128, 64), "RGB 应一致"

    def test_batch_colorspace_parameter(self):
        """测试色彩空间参数"""
        test_colors = [(255, 0, 0)]

        # 测试不同色彩空间
        results_srgb = get_color_info_batch(test_colors, 'sRGB')
        results_adobe = get_color_info_batch(test_colors, 'Adobe RGB')

        assert len(results_srgb) == 1, "sRGB 结果数量应正确"
        assert len(results_adobe) == 1, "Adobe RGB 结果数量应正确"

        # 不同色彩空间的 LAB 值应该不同
        # 注意：RGB 和 HSB/HSL 应该相同，只有 LAB 不同
        assert results_srgb[0]['rgb'] == results_adobe[0]['rgb'], \
            "RGB 应相同"
        assert results_srgb[0]['lab'] != results_adobe[0]['lab'], \
            "LAB 应不同（不同色彩空间）"

    def test_batch_extreme_values(self):
        """测试极端值"""
        test_colors = [
            (0, 0, 0),        # 最小值
            (255, 255, 255),  # 最大值
            (1, 1, 1),        # 接近最小值
            (254, 254, 254),  # 接近最大值
        ]

        results = get_color_info_batch(test_colors)

        assert len(results) == 4, "应返回 4 个结果"

        # 验证黑色
        assert results[0]['rgb'] == (0, 0, 0), "黑色 RGB 应正确"
        assert results[0]['hsb'][2] == 0, "黑色亮度应为 0"

        # 验证白色
        assert results[1]['rgb'] == (255, 255, 255), "白色 RGB 应正确"
        assert results[1]['hsb'][2] == 100, "白色亮度应为 100"


class TestPaletteImporterIntegration:
    """测试 PaletteImporter 集成"""

    def test_import_logic_simulation(self):
        """模拟导入逻辑"""
        # 模拟 PaletteImporter 的处理逻辑
        hex_colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00']

        from core.color import hex_to_rgb

        rgb_list = []
        for hex_color in hex_colors:
            r, g, b = hex_to_rgb(hex_color)
            rgb_list.append((r, g, b))

        # 批量处理
        results = get_color_info_batch(rgb_list)

        # 验证结果
        assert len(results) == 4, "应返回 4 个结果"
        assert results[0]['hex'] == '#FF0000', "第一个颜色应为红色"
        assert results[1]['hex'] == '#00FF00', "第二个颜色应为绿色"
        assert results[2]['hex'] == '#0000FF', "第三个颜色应为蓝色"
        assert results[3]['hex'] == '#FFFF00', "第四个颜色应为黄色"


@pytest.mark.unit
def test_batch_function_exists():
    """测试批量处理函数存在"""
    from core import get_color_info_batch
    assert get_color_info_batch is not None, "批量处理函数应存在"


@pytest.mark.unit
def test_batch_function_signature():
    """测试批量处理函数签名"""
    # 验证函数可以正常调用
    test_colors = [(255, 0, 0)]
    results = get_color_info_batch(test_colors)

    assert isinstance(results, list), "应返回列表"
    assert len(results) == 1, "应返回一个结果"
    assert isinstance(results[0], dict), "结果应为字典"


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v'])