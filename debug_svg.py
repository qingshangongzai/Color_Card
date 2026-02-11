"""调试 SVG 替换问题"""
import sys
sys.path.insert(0, 'd:\\青山公仔\\应用\\Py测试\\color_card')

from core.svg_color_mapper import SVGColorMapper

def test_svg_mapping(svg_path, colors, name):
    """测试 SVG 颜色映射"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"文件: {svg_path}")
    print(f"新配色: {colors}")
    print('='*60)

    mapper = SVGColorMapper()

    # 加载 SVG
    if not mapper.load_svg(svg_path):
        print(f"❌ 加载失败")
        return False

    # 获取元素信息
    elements = mapper.get_elements()
    print(f"\n提取到 {len(elements)} 个元素:")

    # 统计颜色
    fill_colors = set()
    stroke_colors = set()
    for elem in elements:
        if elem.fill_color:
            fill_colors.add(elem.fill_color)
        if elem.stroke_color:
            stroke_colors.add(elem.stroke_color)
        print(f"  - {elem.element_id}: tag={elem.tag}, fill={elem.fill_color}, stroke={elem.stroke_color}, area={elem.area:.1f}")

    print(f"\nFill 颜色: {fill_colors}")
    print(f"Stroke 颜色: {stroke_colors}")

    # 应用智能映射
    print("\n应用智能映射...")
    result = mapper.apply_intelligent_mapping(colors)

    if result:
        print(f"✅ 映射成功，结果长度: {len(result)} 字符")
        print(f"\n结果前 500 字符:\n{result[:500]}")

        # 检查是否包含新颜色
        for color in colors:
            if color in result:
                print(f"✅ 新颜色 {color} 已应用到结果中")

        return True
    else:
        print(f"❌ 映射失败")
        return False

if __name__ == '__main__':
    # 测试 Color Card_logo_内联.svg
    test_colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#66c2a5']

    result = test_svg_mapping(
        'd:\\青山公仔\\应用\\Py测试\\color_card\\测试图片\\Color Card_logo_内联.svg',
        test_colors,
        "Color Card_logo_内联.svg (style 属性)"
    )

    print("\n" + "="*60)
    print(f"测试: {'✅ 通过' if result else '❌ 失败'}")
