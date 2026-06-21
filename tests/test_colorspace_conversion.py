# 标准库导入
import sys
from pathlib import Path
# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 项目模块导入
from core.color import rgb_to_lab, lab_to_rgb, _COLORSPACE_MATRICES  # noqa: E402


def test_colorspace(colorspace_name: str, expected_gamma: float, expected_wp: tuple):
    """测试色彩空间转 LAB 的准确性"""
    print(f"\n{'=' * 60}")
    print(f"{colorspace_name} 转 LAB 测试")
    print("=" * 60)
    
    cs = _COLORSPACE_MATRICES[colorspace_name]
    
    if cs['gamma'] != expected_gamma:
        print(f"  [X] gamma 应为 {expected_gamma}，实际为 {cs['gamma']}")
        return False
    
    if cs['white_point'] != expected_wp:
        print(f"  [X] 白点应为 {expected_wp}，实际为 {cs['white_point']}")
        return False
    
    if colorspace_name == 'Adobe RGB' and cs['use_srgb_curve']:
        print("  [X] Adobe RGB 不应使用 sRGB 曲线")
        return False
    
    test_cases = [
        ((255, 255, 255), "白色", 100.0, 0.0, 0.0),
        ((0, 0, 0), "黑色", 0.0, 0.0, 0.0),
        ((255, 0, 0), "红色", None, None, None),
        ((0, 255, 0), "绿色", None, None, None),
        ((0, 0, 255), "蓝色", None, None, None),
        ((128, 128, 128), "中灰", None, None, None),
    ]
    
    print("\n测试结果:")
    all_ok = True
    for (r, g, b), name, exp_L, exp_A, exp_B in test_cases:
        L, A, B = rgb_to_lab(r, g, b, colorspace_name)
        print(f"  {name:8s} RGB({r:3d}, {g:3d}, {b:3d}) -> LAB({L:7.2f}, {A:7.2f}, {B:7.2f})")
        
        if exp_L is not None and abs(L - exp_L) > 0.5:
            print(f"           [!] L 值偏差 {abs(L - exp_L):.2f}")
            all_ok = False
    
    return all_ok


def test_roundtrip():
    """测试往返转换的准确性"""
    print(f"\n{'=' * 60}")
    print("往返转换测试 (RGB -> LAB -> RGB)")
    print("=" * 60)
    
    test_colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 255), (0, 0, 0), (128, 128, 128), (255, 128, 64),
    ]
    
    all_ok = True
    for colorspace in ['Adobe RGB', 'ProPhoto RGB']:
        print(f"\n{colorspace}:")
        for r, g, b in test_colors:
            L, A, B = rgb_to_lab(r, g, b, colorspace)
            r2, g2, b2 = lab_to_rgb(L, A, B, colorspace)
            error = max(abs(r - r2), abs(g - g2), abs(b - b2))
            
            if error > 1:
                print(f"  [X] ({r:3d},{g:3d},{b:3d}) 误差:{error}")
                all_ok = False
    
    if all_ok:
        print("\n  [OK] 所有往返转换误差 <= 1")
    
    return all_ok


def main():
    print("\n" + "=" * 60)
    print("色彩空间转换验证测试")
    print("=" * 60)
    
    results = []
    results.append(('Adobe RGB', test_colorspace('Adobe RGB', 2.2, (0.95047, 1.00000, 1.08883))))
    results.append(('ProPhoto RGB', test_colorspace('ProPhoto RGB', 1.8, (0.96422, 1.00000, 0.82521))))
    results.append(('往返转换', test_roundtrip()))
    
    print(f"\n{'=' * 60}")
    print("测试结果")
    print("=" * 60)
    
    for name, ok in results:
        status = "[OK]" if ok else "[X]"
        print(f"  {status} {name}")
    
    return all(r[1] for r in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
