#!/usr/bin/env python3
"""调试脚本：分析SVG的元素提取和映射情况"""

import sys
sys.path.insert(0, 'd:\\青山公仔\\应用\\Py测试\\color_card')

from core.svg_color_mapper import SVGColorMapper

def test_svg(svg_path, colors, name):
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    
    mapper = SVGColorMapper()
    
    # 加载SVG
    with open(svg_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not mapper.load_svg_from_string(content):
        print("加载SVG失败")
        return
    
    # 获取所有元素
    elements = mapper.get_elements()
    
    # 统计信息
    fill_elements = [e for e in elements if e.fill_color and not e.is_transparent]
    transparent_elements = [e for e in elements if e.is_transparent]
    
    print(f"总元素数: {len(elements)}")
    print(f"有fill元素: {len(fill_elements)}")
    print(f"透明元素: {len(transparent_elements)}")
    
    # 计算总面积和背景占比
    if fill_elements:
        total_area = sum(e.area for e in fill_elements)
        
        # 使用与实际代码相同的排序逻辑
        def sort_key(elem):
            x = float(elem.attributes.get('x', 0))
            y = float(elem.attributes.get('y', 0))
            fill = elem.fill_color or ''
            is_bw = fill.lower() in ('#000000', '#ffffff', 'black', 'white')
            priority = 0 if is_bw else 1
            return (-elem.area, -priority, y, x)
        
        fill_elements.sort(key=sort_key)
        largest = fill_elements[0]
        bg_ratio = largest.area / total_area if total_area > 0 else 0
        print(f"总面积: {total_area:.2f}")
        print(f"最大元素面积: {largest.area:.2f} ({bg_ratio:.1%})")
        print(f"最大元素颜色: {largest.fill_color}")
        
        # 显示前5个元素
        print("\n前5个元素（按面积+颜色优先级排序）:")
        for i, e in enumerate(fill_elements[:5]):
            print(f"  {i}: fill={e.fill_color}, area={e.area:.2f}")
        
        # 判断是否有明显背景
        has_obvious_bg = bg_ratio > 0.5
        print(f"\n是否有明显背景元素: {has_obvious_bg}")
    
    # 应用颜色映射
    print("\n--- 颜色映射 ---")
    result = mapper.apply_intelligent_mapping(colors)
    print(f"结果长度: {len(result)}")
    
    # 检查结果中是否包含背景色
    if 'auto-background' in result:
        print("✓ 添加了背景矩形")
    else:
        print("✗ 没有添加背景矩形")

def main():
    colors = ['#678d6c', '#fc7d23', '#fa3c08', '#bd0a41', '#772a53']
    
    # 测试马年万事如意.svg
    test_svg(
        'd:\\青山公仔\\应用\\Py测试\\color_card\\测试图片\\马年万事如意.svg',
        colors,
        "马年万事如意.svg"
    )
    
    # 测试测试1.svg
    test_svg(
        'd:\\青山公仔\\应用\\Py测试\\color_card\\测试图片\\测试1.svg',
        colors,
        "测试1.svg"
    )
    
    # 测试Color Card_logo.svg
    test_svg(
        'd:\\青山公仔\\应用\\Py测试\\color_card\\测试图片\\Color Card_logo.svg',
        colors,
        "Color Card_logo.svg"
    )

if __name__ == '__main__':
    main()
