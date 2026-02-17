"""色轮旋转后的RYB交互测试

验证色轮旋转90度后：
1. 色相0°（红色）是否在12点钟方向
2. 鼠标点击位置到色相的转换是否正确
3. RYB模式的配色生成和显示是否一致
"""

import sys
import math
sys.path.insert(0, 'd:\\青山公仔\\应用\\Py测试\\color_card')

from core.color import (
    rgb_hue_to_ryb_hue,
    ryb_hue_to_rgb_hue,
    generate_ryb_split_complementary,
    hsb_to_rgb
)


def test_hue_to_position():
    """测试色相到色轮位置的转换（模拟_hsb_to_position）"""
    print("=" * 60)
    print("测试1: 色相到色轮位置的转换")
    print("=" * 60)
    
    # 模拟色轮参数
    center_x, center_y = 200, 200
    wheel_radius = 150
    max_radius = wheel_radius * 0.85
    
    # 测试关键色相
    test_hues = [
        (0, "红色", "12点钟方向"),
        (90, "黄色", "9点钟方向"),
        (180, "绿色", "6点钟方向"),
        (270, "蓝色", "3点钟方向"),
    ]
    
    print(f"\n色相 → 位置（饱和度100%）")
    print("-" * 50)
    
    for hue, name, expected_pos in test_hues:
        # 使用修改后的公式：加上90度
        angle_rad = ((hue + 90) * math.pi / 180.0)
        radius = max_radius  # 饱和度100%
        
        x = center_x + radius * math.cos(angle_rad)
        y = center_y - radius * math.sin(angle_rad)
        
        # 计算相对于中心的方向
        dx = x - center_x
        dy = center_y - y  # Y轴翻转
        
        # 判断大致方向
        if abs(dx) < 10:
            direction = "上方" if dy > 0 else "下方"
        elif abs(dy) < 10:
            direction = "右方" if dx > 0 else "左方"
        else:
            direction = f"({dx:+.0f}, {dy:+.0f})"
        
        print(f"{hue:>3}° ({name}): 位置=({x:>6.1f}, {y:>6.1f}), 方向={direction}")
        
        # 验证方向
        if hue == 0 and "上方" in direction:
            print(f"  ✓ 红色在上方（12点钟方向）")
        elif hue == 90 and "左方" in direction:
            print(f"  ✓ 黄色在左方（9点钟方向）")
        elif hue == 180 and "下方" in direction:
            print(f"  ✓ 绿色在下方（6点钟方向）")
        elif hue == 270 and "右方" in direction:
            print(f"  ✓ 蓝色在右方（3点钟方向）")
    
    print()


def test_position_to_hue():
    """测试色轮位置到色相的转换（模拟_position_to_hsb）"""
    print("=" * 60)
    print("测试2: 色轮位置到色相的转换")
    print("=" * 60)
    
    center_x, center_y = 200, 200
    wheel_radius = 150
    max_radius = wheel_radius * 0.85
    
    # 测试12点钟方向的位置
    test_positions = [
        (200, 50, "12点钟方向（上方）", 0),
        (50, 200, "9点钟方向（左方）", 90),
        (200, 350, "6点钟方向（下方）", 180),
        (350, 200, "3点钟方向（右方）", 270),
    ]
    
    print(f"\n位置 → 色相")
    print("-" * 60)
    
    for x, y, desc, expected_hue in test_positions:
        dx = x - center_x
        dy = y - center_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # 使用修改后的公式：减去90度
        angle = math.atan2(-dy, dx)
        hue = ((angle - math.pi / 2) / (2 * math.pi)) % 1.0 * 360
        
        error = abs(hue - expected_hue)
        if error > 180:
            error = 360 - error
        
        status = "✓" if error < 1 else "✗"
        print(f"{desc}: 计算色相={hue:>6.1f}°, 预期={expected_hue}°, 误差={error:.1f}° {status}")
    
    print()


def test_roundtrip_conversion():
    """测试色相→位置→色相的往返转换"""
    print("=" * 60)
    print("测试3: 色相往返转换一致性")
    print("=" * 60)
    
    center_x, center_y = 200, 200
    wheel_radius = 150
    max_radius = wheel_radius * 0.85
    
    test_hues = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]
    
    print(f"\n原始色相 → 位置 → 还原色相")
    print("-" * 50)
    
    max_error = 0
    for original_hue in test_hues:
        # 色相 → 位置
        angle_rad = ((original_hue + 90) * math.pi / 180.0)
        radius = max_radius
        x = center_x + radius * math.cos(angle_rad)
        y = center_y - radius * math.sin(angle_rad)
        
        # 位置 → 色相
        dx = x - center_x
        dy = y - center_y
        angle = math.atan2(-dy, dx)
        recovered_hue = ((angle - math.pi / 2) / (2 * math.pi)) % 1.0 * 360
        
        error = abs(recovered_hue - original_hue)
        if error > 180:
            error = 360 - error
        
        max_error = max(max_error, error)
        status = "✓" if error < 0.1 else "✗"
        print(f"{original_hue:>3}° → ({x:>6.1f}, {y:>6.1f}) → {recovered_hue:>6.1f}° 误差={error:.2f}° {status}")
    
    print(f"\n最大误差: {max_error:.2f}°")
    if max_error < 0.1:
        print("✓ 通过: 往返转换一致性良好")
    else:
        print("✗ 失败: 往返转换存在较大误差")
    
    print()


def test_ryb_wheel_integration():
    """测试RYB配色在旋转后的色轮上的显示"""
    print("=" * 60)
    print("测试4: RYB配色在旋转色轮上的集成测试")
    print("=" * 60)
    
    center_x, center_y = 200, 200
    wheel_radius = 150
    max_radius = wheel_radius * 0.85
    
    # 使用分离补色方案
    base_hue = 220  # RYB蓝色
    colors = generate_ryb_split_complementary(base_hue, angle=30, count=3)
    
    print(f"\n基准色相: {base_hue}° (RYB蓝色)")
    print(f"配色方案: 分离补色 (±30°)")
    print("-" * 60)
    
    print(f"{'点':<8} {'RYB色相':<10} {'RGB色相':<10} {'色轮位置':<20} {'方向':<10}")
    print("-" * 60)
    
    for i, (rgb_h, s, b) in enumerate(colors):
        ryb_h = rgb_hue_to_ryb_hue(rgb_h)
        
        # 计算在色轮上的位置（使用旋转后的公式）
        angle_rad = ((rgb_h + 90) * math.pi / 180.0)
        radius = max_radius * (s / 100.0)
        x = center_x + radius * math.cos(angle_rad)
        y = center_y - radius * math.sin(angle_rad)
        
        # 判断方向
        dx = x - center_x
        dy = center_y - y
        
        if abs(dx) < 10 and dy > 0:
            direction = "上方"
        elif abs(dx) < 10 and dy < 0:
            direction = "下方"
        elif abs(dy) < 10 and dx > 0:
            direction = "右方"
        elif abs(dy) < 10 and dx < 0:
            direction = "左方"
        else:
            angle_deg = math.degrees(math.atan2(dy, dx))
            direction = f"{angle_deg:.0f}°"
        
        point_name = ["基准", "左补色", "右补色"][i]
        print(f"{point_name:<8} {ryb_h:<10.1f} {rgb_h:<10.1f} ({x:>6.1f}, {y:>6.1f})   {direction:<10}")
    
    # 验证相对角度
    base_rgb = colors[0][0]
    left_rgb = colors[1][0]
    right_rgb = colors[2][0]
    
    base_ryb = rgb_hue_to_ryb_hue(base_rgb)
    left_ryb = rgb_hue_to_ryb_hue(left_rgb)
    right_ryb = rgb_hue_to_ryb_hue(right_rgb)
    
    left_rel = (left_ryb - base_ryb + 360) % 360
    right_rel = (right_ryb - base_ryb + 360) % 360
    
    print(f"\n相对角度验证:")
    print(f"  左补色相对角度: {left_rel:.1f}° (预期: 150°)")
    print(f"  右补色相对角度: {right_rel:.1f}° (预期: 210°)")
    
    if abs(left_rel - 150) < 1 and abs(right_rel - 210) < 1:
        print("✓ 通过: RYB配色在旋转色轮上显示正确")
    else:
        print("✗ 失败: RYB配色相对角度不正确")
    
    print()


def test_mouse_interaction():
    """测试鼠标交互的一致性"""
    print("=" * 60)
    print("测试5: 鼠标交互一致性测试")
    print("=" * 60)
    
    center_x, center_y = 200, 200
    wheel_radius = 150
    max_radius = wheel_radius * 0.85
    
    print(f"\n模拟用户点击色轮不同位置")
    print("-" * 60)
    
    # 模拟用户点击12点钟方向（应该选中红色附近）
    click_positions = [
        (200, 80, "12点钟方向（上方）"),
        (80, 200, "9点钟方向（左方）"),
        (200, 320, "6点钟方向（下方）"),
        (320, 200, "3点钟方向（右方）"),
    ]
    
    print(f"{'点击位置':<20} {'计算色相':<12} {'预期附近':<12} {'状态':<6}")
    print("-" * 60)
    
    for x, y, desc in click_positions:
        dx = x - center_x
        dy = y - center_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # 计算色相（使用旋转后的公式）
        angle = math.atan2(-dy, dx)
        hue = ((angle - math.pi / 2) / (2 * math.pi)) % 1.0 * 360
        
        # 预期色相
        if "12点" in desc:
            expected = 0
        elif "9点" in desc:
            expected = 90
        elif "6点" in desc:
            expected = 180
        elif "3点" in desc:
            expected = 270
        else:
            expected = -1
        
        error = abs(hue - expected)
        if error > 180:
            error = 360 - error
        
        status = "✓" if error < 5 else "✗"
        print(f"{desc:<20} {hue:>6.1f}°     {expected}°         {status}")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("色轮旋转后的RYB交互测试")
    print("=" * 60 + "\n")
    
    test_hue_to_position()
    test_position_to_hue()
    test_roundtrip_conversion()
    test_ryb_wheel_integration()
    test_mouse_interaction()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
