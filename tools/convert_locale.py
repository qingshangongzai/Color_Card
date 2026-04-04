"""语言包格式转换工具

将 JSON 格式的语言包转换为 TOML 格式。
"""

import json
import os
import sys
from pathlib import Path


def get_locales_dir() -> Path:
    """获取语言包目录路径

    Returns:
        Path: 语言包目录路径
    """
    # 脚本位于 tools/ 目录下，语言包在 locales/ 目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    return project_root / 'locales'


def get_output_dir() -> Path:
    """获取输出目录路径

    Returns:
        Path: 输出目录路径
    """
    script_dir = Path(__file__).parent
    return script_dir / 'output'


def json_to_toml(data: dict, indent: int = 0) -> str:
    """将字典转换为 TOML 格式字符串

    Args:
        data: 要转换的字典
        indent: 当前缩进级别

    Returns:
        str: TOML 格式字符串
    """
    lines = []
    prefix = ''

    for key, value in data.items():
        if isinstance(value, dict):
            # 处理嵌套字典，使用 [section] 格式
            lines.append(f'\n[{key}]')
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    # 更深层的嵌套使用 [section.subsection] 格式
                    lines.append(f'\n[{key}.{sub_key}]')
                    for k, v in sub_value.items():
                        lines.append(format_key_value(k, v))
                else:
                    lines.append(format_key_value(sub_key, sub_value))
        else:
            lines.append(format_key_value(key, value))

    return '\n'.join(lines).strip() + '\n'


def format_key_value(key: str, value) -> str:
    """格式化键值对

    Args:
        key: 键名
        value: 值

    Returns:
        str: 格式化后的键值对字符串
    """
    # 处理键名中的特殊字符
    if ' ' in key or '.' in key or '-' in key or key.startswith('_'):
        key = f'"{key}"'

    if isinstance(value, str):
        # 处理字符串值，如果包含特殊字符则使用三引号
        if '\n' in value or '"' in value:
            return f'{key} = """{value}"""'
        return f'{key} = "{value}"'
    elif isinstance(value, bool):
        return f'{key} = {str(value).lower()}'
    elif isinstance(value, (int, float)):
        return f'{key} = {value}'
    elif isinstance(value, list):
        return f'{key} = {json.dumps(value)}'
    else:
        return f'{key} = "{str(value)}"'


def convert_file(json_path: Path, output_dir: Path) -> bool:
    """转换单个 JSON 文件为 TOML

    Args:
        json_path: JSON 文件路径
        output_dir: 输出目录

    Returns:
        bool: 是否转换成功
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        toml_content = json_to_toml(data)

        # 生成输出文件名
        toml_name = json_path.stem + '.toml'
        toml_path = output_dir / toml_name

        with open(toml_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)

        print(f'✓ 转换成功: {json_path.name} -> {toml_name}')
        return True

    except json.JSONDecodeError as e:
        print(f'✗ 解析失败: {json_path.name} - {e}')
        return False
    except Exception as e:
        print(f'✗ 转换失败: {json_path.name} - {e}')
        return False


def main():
    """主函数"""
    locales_dir = get_locales_dir()
    output_dir = get_output_dir()

    # 检查语言包目录是否存在
    if not locales_dir.exists():
        print(f'错误: 语言包目录不存在: {locales_dir}')
        sys.exit(1)

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 查找所有 JSON 文件
    json_files = list(locales_dir.glob('*.json'))

    if not json_files:
        print(f'警告: 在 {locales_dir} 中未找到 JSON 文件')
        sys.exit(0)

    print(f'找到 {len(json_files)} 个 JSON 文件')
    print(f'输出目录: {output_dir}')
    print('-' * 50)

    # 转换所有文件
    success_count = 0
    for json_file in sorted(json_files):
        if convert_file(json_file, output_dir):
            success_count += 1

    print('-' * 50)
    print(f'转换完成: {success_count}/{len(json_files)} 个文件成功')

    if success_count == len(json_files):
        print('\n所有文件已转换到:')
        print(f'  {output_dir}')
        print('\n你可以检查输出文件，确认无误后手动替换到 locales/ 目录')


if __name__ == '__main__':
    main()
