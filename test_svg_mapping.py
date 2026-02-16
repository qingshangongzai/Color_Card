"""
SVG颜色映射验证测试脚本

验证目标：
1. 加载内置SVG模板
2. 应用测试配色
3. 验证颜色映射结果
4. 导出着色后的SVG
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.svg_color_mapper import SVGColorMapper, ColorMappingConfig, create_mapping_from_palette


def test_type_based_mapping():
    """测试基于元素类型的映射"""
    print("\n" + "=" * 60)
    print("测试: 基于元素类型的映射（使用 class 名称）")
    print("=" * 60)
    
    test_colors = ["#E8D5B7", "#1F628D", "#2E8B57", "#FF6B6B", "#333333"]
    print(f"\n测试配色: {test_colors}")
    print(f"  配色[0] → 背景 (background)")
    print(f"  配色[1] → 主元素 (primary)")
    print(f"  配色[2] → 次要元素 (secondary)")
    print(f"  配色[3] → 强调元素 (accent)")
    print(f"  配色[4] → 文字/描边 (text/stroke)")
    
    scenes_dir = project_root / "scenes_data"
    
    test_files = [
        ("ui/default.svg", "手机UI"),
        ("web/default.svg", "网页"),
        ("illustration/default.svg", "插画"),
        ("typography/default.svg", "排版"),
        ("brand/default.svg", "品牌"),
        ("poster/default.svg", "海报"),
        ("pattern/default.svg", "图案"),
        ("magazine/default.svg", "杂志")
    ]
    
    for svg_file, scene_name in test_files:
        svg_path = scenes_dir / svg_file
        
        if not svg_path.exists():
            print(f"\n❌ 文件不存在: {svg_path}")
            continue
        
        print(f"\n{'─' * 40}")
        print(f"测试场景: {scene_name}")
        print(f"文件: {svg_file}")
        print(f"{'─' * 40}")
        
        mapper = SVGColorMapper()
        
        if not mapper.load_svg(str(svg_path)):
            print(f"❌ 加载失败")
            continue
        
        print(f"✅ 加载成功")
        
        elements = mapper.get_elements()
        print(f"\n元素分类 (共 {len(elements)} 个):")
        for elem in elements:
            print(f"  - {elem.element_id:20} | class: {(elem.element_class or 'None'):15} | 类型: {elem.element_type.name}")
        
        config = create_mapping_from_palette(test_colors)
        
        print(f"\n映射配置:")
        print(f"  background_color: {config.background_color}")
        print(f"  primary_color: {config.primary_color}")
        print(f"  secondary_color: {config.secondary_color}")
        print(f"  accent_color: {config.accent_color}")
        print(f"  text_color: {config.text_color}")
        
        print("\n应用类型映射...")
        result = mapper.apply_color_mapping(config)
        
        if result:
            print("✅ 映射成功")
            
            output_dir = project_root / "测试图片" / "mapping_test"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_filename = svg_file.replace('/', '_').replace('.svg', '_colored.svg')
            output_path = output_dir / output_filename
            
            output_path.write_text(result, encoding='utf-8')
            print(f"✅ 已导出到: {output_path}")
            
            print("\n验证颜色替换:")
            for color in test_colors:
                if color.lower() in result.lower():
                    print(f"  ✅ {color} 已应用")
                else:
                    print(f"  ⚠️ {color} 未找到")
        else:
            print("❌ 映射失败")


def main():
    print("=" * 60)
    print("SVG颜色映射验证测试")
    print("=" * 60)
    
    test_type_based_mapping()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
