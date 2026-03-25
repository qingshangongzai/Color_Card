#!/usr/bin/env python3
"""批量将JSON色卡文件中的Hex颜色值转换为大写

使用方法:
    python scripts/uppercase_hex_colors.py

功能:
    扫描 color_data/ 和 docs/palettes/ 目录下的所有JSON色卡文件，
    将所有形如 #abc123 的Hex颜色值转换为大写形式 #ABC123
"""

import json
import re
from pathlib import Path


def uppercase_hex_in_string(value: str) -> str:
    """将字符串中的Hex颜色值转换为大写
    
    匹配模式: # 后跟3、4、6或8位十六进制字符
    例如: #fff, #ffff, #ffffff, #ffffffff
    """
    if not isinstance(value, str):
        return value
    
    # 匹配Hex颜色值: # 后跟3、4、6或8位十六进制字符
    hex_pattern = r'#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b'
    
    def replace_hex(match):
        hex_value = match.group(0)
        # 转换为大写
        return hex_value.upper()
    
    return re.sub(hex_pattern, replace_hex, value)


def process_json_value(value):
    """递归处理JSON值"""
    if isinstance(value, str):
        return uppercase_hex_in_string(value)
    elif isinstance(value, list):
        return [process_json_value(item) for item in value]
    elif isinstance(value, dict):
        return {key: process_json_value(val) for key, val in value.items()}
    else:
        return value


def process_json_file(file_path: Path) -> bool:
    """处理单个JSON文件
    
    Returns:
        bool: 是否进行了修改
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data = json.loads(content)
        new_data = process_json_value(data)
        
        # 检查是否有变化
        new_content = json.dumps(new_data, ensure_ascii=False, indent=2)
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  ✓ 已更新: {file_path.name}")
            return True
        else:
            print(f"  - 无需修改: {file_path.name}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON解析错误: {file_path.name} - {e}")
        return False
    except Exception as e:
        print(f"  ✗ 处理失败: {file_path.name} - {e}")
        return False


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    
    # 需要处理的目录
    target_dirs = [
        project_root / 'color_data',
        project_root / 'docs' / 'palettes',
        project_root / 'website' / 'public' / 'palettes',
    ]
    
    print("=" * 50)
    print("Hex颜色值大写转换工具")
    print("=" * 50)
    
    total_files = 0
    modified_files = 0
    
    for target_dir in target_dirs:
        if not target_dir.exists():
            print(f"\n跳过不存在的目录: {target_dir.relative_to(project_root)}")
            continue
        
        print(f"\n处理目录: {target_dir.relative_to(project_root)}")
        print("-" * 40)
        
        json_files = sorted(target_dir.glob('*.json'))
        
        for json_file in json_files:
            total_files += 1
            if process_json_file(json_file):
                modified_files += 1
    
    print("\n" + "=" * 50)
    print(f"处理完成: 共 {total_files} 个文件, {modified_files} 个文件已修改")
    print("=" * 50)


if __name__ == '__main__':
    main()
