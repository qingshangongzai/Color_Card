# 标准库导入
import json
import os


# ===== Open Color 延迟加载 =====
_OPEN_COLOR_DATA = None


def _load_open_color_data():
    """从 JSON 文件加载 Open Color 数据

    Returns:
        dict: Open Color 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'open_color.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Open Color 数据失败: {e}")
        return {}


def _get_open_color_data():
    """获取 Open Color 数据（延迟加载）

    Returns:
        dict: Open Color 颜色数据字典
    """
    global _OPEN_COLOR_DATA
    if _OPEN_COLOR_DATA is None:
        _OPEN_COLOR_DATA = _load_open_color_data()
    return _OPEN_COLOR_DATA


# ===== Tailwind CSS 延迟加载 =====
_TAILWIND_COLOR_DATA = None


def _load_tailwind_data():
    """从 JSON 文件加载 Tailwind CSS 颜色数据

    Returns:
        dict: Tailwind CSS 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'tailwind_colors.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Tailwind CSS 颜色数据失败: {e}")
        return {}


def _get_tailwind_data():
    """获取 Tailwind CSS 颜色数据（延迟加载）

    Returns:
        dict: Tailwind CSS 颜色数据字典
    """
    global _TAILWIND_COLOR_DATA
    if _TAILWIND_COLOR_DATA is None:
        _TAILWIND_COLOR_DATA = _load_tailwind_data()
    return _TAILWIND_COLOR_DATA


# ===== Material Design 延迟加载 =====
_MATERIAL_COLOR_DATA = None


def _load_material_data():
    """从 JSON 文件加载 Material Design 颜色数据

    Returns:
        dict: Material Design 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'material_design.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Material Design 颜色数据失败: {e}")
        return {}


def _get_material_data():
    """获取 Material Design 颜色数据（延迟加载）

    Returns:
        dict: Material Design 颜色数据字典
    """
    global _MATERIAL_COLOR_DATA
    if _MATERIAL_COLOR_DATA is None:
        _MATERIAL_COLOR_DATA = _load_material_data()
    return _MATERIAL_COLOR_DATA


# ===== Nice Color Palettes 延迟加载 =====
_NICE_COLOR_PALETTES_DATA = None


def _load_nice_palettes_data():
    """从 JSON 文件加载 Nice Color Palettes 数据

    Returns:
        list: 配色方案列表，每个元素为包含5个HEX颜色值的列表
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'nice_palettes.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('palettes', [])
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Nice Color Palettes 数据失败: {e}")
        return []


def _get_nice_palettes_data():
    """获取 Nice Color Palettes 数据（延迟加载）

    Returns:
        list: 配色方案列表
    """
    global _NICE_COLOR_PALETTES_DATA
    if _NICE_COLOR_PALETTES_DATA is None:
        _NICE_COLOR_PALETTES_DATA = _load_nice_palettes_data()
    return _NICE_COLOR_PALETTES_DATA


# ===== Nord 延迟加载 =====
_NORD_COLOR_DATA = None


def _load_nord_data():
    """从 JSON 文件加载 Nord 颜色数据

    Returns:
        dict: Nord 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'nord.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Nord 颜色数据失败: {e}")
        return {}


def _get_nord_data():
    """获取 Nord 颜色数据（延迟加载）

    Returns:
        dict: Nord 颜色数据字典
    """
    global _NORD_COLOR_DATA
    if _NORD_COLOR_DATA is None:
        _NORD_COLOR_DATA = _load_nord_data()
    return _NORD_COLOR_DATA


# ===== Dracula 延迟加载 =====
_DRACULA_COLOR_DATA = None


def _load_dracula_data():
    """从 JSON 文件加载 Dracula 颜色数据

    Returns:
        dict: Dracula 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'dracula.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Dracula 颜色数据失败: {e}")
        return {}


def _get_dracula_data():
    """获取 Dracula 颜色数据（延迟加载）

    Returns:
        dict: Dracula 颜色数据字典
    """
    global _DRACULA_COLOR_DATA
    if _DRACULA_COLOR_DATA is None:
        _DRACULA_COLOR_DATA = _load_dracula_data()
    return _DRACULA_COLOR_DATA


# ===== ColorBrewer 延迟加载 =====
_COLORBREWER_DATA = None


def _load_colorbrewer_data():
    """从 JSON 文件加载 ColorBrewer 颜色数据

    Returns:
        dict: ColorBrewer 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'colorbrewer.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 ColorBrewer 颜色数据失败: {e}")
        return {}


def _get_colorbrewer_data():
    """获取 ColorBrewer 颜色数据（延迟加载）

    Returns:
        dict: ColorBrewer 颜色数据字典
    """
    global _COLORBREWER_DATA
    if _COLORBREWER_DATA is None:
        _COLORBREWER_DATA = _load_colorbrewer_data()
    return _COLORBREWER_DATA


# ===== Radix Colors 延迟加载 =====
_RADIX_COLOR_DATA = None


def _load_radix_data():
    """从 JSON 文件加载 Radix Colors 颜色数据

    Returns:
        dict: Radix Colors 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'radix_colors.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Radix Colors 颜色数据失败: {e}")
        return {}


def _get_radix_data():
    """获取 Radix Colors 颜色数据（延迟加载）

    Returns:
        dict: Radix Colors 颜色数据字典
    """
    global _RADIX_COLOR_DATA
    if _RADIX_COLOR_DATA is None:
        _RADIX_COLOR_DATA = _load_radix_data()
    return _RADIX_COLOR_DATA


# ===== Open Color 相关函数 =====

def get_color_series_names():
    """获取所有颜色系列名称列表"""
    return list(_get_open_color_data().keys())


def get_color_series(series_name):
    """获取指定颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'red', 'blue' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_open_color_data().get(series_name, None)


def get_light_shades(series_name):
    """获取指定颜色系列的浅色组 (0-4)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个浅色色值列表
    """
    series = _get_open_color_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5)]


def get_dark_shades(series_name):
    """获取指定颜色系列的深色组 (5-9)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个深色色值列表
    """
    series = _get_open_color_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5, 10)]


def get_selected_shades(series_name):
    """获取指定颜色系列的精选5色 (0, 2, 4, 6, 9)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个精选色值列表
    """
    series = _get_open_color_data().get(series_name)
    if not series:
        return []
    selected_indices = [0, 2, 4, 6, 9]
    return [series["colors"][i] for i in selected_indices]


def get_color_series_name_mapping():
    """获取颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_open_color_data().items()}


# ===== Nice Color Palettes 相关函数 =====

def get_nice_palette_count():
    """获取nice-color-palettes配色方案总数"""
    return len(_get_nice_palettes_data())


def get_nice_palette(index):
    """获取指定索引的配色方案

    Args:
        index: 配色方案索引 (0-based)

    Returns:
        list: 包含5个HEX颜色值的列表
    """
    data = _get_nice_palettes_data()
    if 0 <= index < len(data):
        return data[index]
    return []


def get_nice_palettes_batch(start_index=0, count=10):
    """批量获取配色方案

    Args:
        start_index: 起始索引
        count: 获取数量

    Returns:
        list: 配色方案列表，每个元素为 (index, palette)
    """
    data = _get_nice_palettes_data()
    end_index = min(start_index + count, len(data))
    return [(i, data[i]) for i in range(start_index, end_index)]


# ===== Tailwind Colors 相关函数 =====

def get_tailwind_color_series_names():
    """获取所有 Tailwind 颜色系列名称列表"""
    return list(_get_tailwind_data().keys())


def get_tailwind_color_series(series_name):
    """获取指定 Tailwind 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'blue', 'red' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_tailwind_data().get(series_name, None)


def get_tailwind_light_shades(series_name):
    """获取指定 Tailwind 颜色系列的浅色组 (0-4)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个浅色色值列表
    """
    series = _get_tailwind_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5)]


def get_tailwind_dark_shades(series_name):
    """获取指定 Tailwind 颜色系列的深色组 (5-9)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个深色色值列表
    """
    series = _get_tailwind_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5, 10)]


def get_tailwind_selected_shades(series_name):
    """获取指定 Tailwind 颜色系列的精选5色 (0, 2, 4, 6, 9)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个精选色值列表
    """
    series = _get_tailwind_data().get(series_name)
    if not series:
        return []
    selected_indices = [0, 2, 4, 6, 9]
    return [series["colors"][i] for i in selected_indices]


def get_tailwind_color_series_name_mapping():
    """获取 Tailwind 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_tailwind_data().items()}


# ===== Material Design Colors 相关函数 =====

def get_material_color_series_names():
    """获取所有 Material Design 颜色系列名称列表"""
    return list(_get_material_data().keys())


def get_material_color_series(series_name):
    """获取指定 Material Design 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'blue', 'red' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_material_data().get(series_name, None)


def get_material_light_shades(series_name):
    """获取指定 Material Design 颜色系列的浅色组 (0-4)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个浅色色值列表
    """
    series = _get_material_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5)]


def get_material_dark_shades(series_name):
    """获取指定 Material Design 颜色系列的深色组 (5-9)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个深色色值列表
    """
    series = _get_material_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5, 10)]


def get_material_selected_shades(series_name):
    """获取指定 Material Design 颜色系列的精选5色 (0, 2, 4, 6, 9)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个精选色值列表
    """
    series = _get_material_data().get(series_name)
    if not series:
        return []
    selected_indices = [0, 2, 4, 6, 9]
    return [series["colors"][i] for i in selected_indices]


def get_material_color_series_name_mapping():
    """获取 Material Design 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_material_data().items()}


# ===== Nord 相关函数 =====

def get_nord_color_series_names():
    """获取所有 Nord 颜色系列名称列表"""
    return list(_get_nord_data().keys())


def get_nord_color_series(series_name):
    """获取指定 Nord 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'nord0', 'nord1' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_nord_data().get(series_name, None)


def get_nord_light_shades(series_name):
    """获取指定 Nord 颜色系列的浅色组 (0-1)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 2个浅色色值列表
    """
    series = _get_nord_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(2)]


def get_nord_dark_shades(series_name):
    """获取指定 Nord 颜色系列的深色组 (2-3)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 2个深色色值列表
    """
    series = _get_nord_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(2, 4)]


def get_nord_color_series_name_mapping():
    """获取 Nord 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_nord_data().items()}


# ===== Dracula 相关函数 =====

def get_dracula_color_series_names():
    """获取所有 Dracula 颜色系列名称列表"""
    return list(_get_dracula_data().keys())


def get_dracula_color_series(series_name):
    """获取指定 Dracula 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'dracula_bg', 'dracula_cyan' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_dracula_data().get(series_name, None)


def get_dracula_light_shades(series_name):
    """获取指定 Dracula 颜色系列的浅色组 (0-1)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 2个浅色色值列表
    """
    series = _get_dracula_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(2)]


def get_dracula_dark_shades(series_name):
    """获取指定 Dracula 颜色系列的深色组 (2-3)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 2个深色色值列表
    """
    series = _get_dracula_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(2, 4)]


def get_dracula_color_series_name_mapping():
    """获取 Dracula 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_dracula_data().items()}


# ===== ColorBrewer 相关函数 =====

def get_colorbrewer_series_names():
    """获取所有 ColorBrewer 颜色系列名称列表"""
    return list(_get_colorbrewer_data().keys())


def get_colorbrewer_color_series(series_name):
    """获取指定 ColorBrewer 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'brewer_blues', 'brewer_set1' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_colorbrewer_data().get(series_name, None)


def get_colorbrewer_light_shades(series_name):
    """获取指定 ColorBrewer 颜色系列的浅色组 (0-4)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个浅色色值列表
    """
    series = _get_colorbrewer_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5) if i in series["colors"]]


def get_colorbrewer_dark_shades(series_name):
    """获取指定 ColorBrewer 颜色系列的深色组 (4-8)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个深色色值列表
    """
    series = _get_colorbrewer_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(4, 9) if i in series["colors"]]


def get_colorbrewer_selected_shades(series_name):
    """获取指定 ColorBrewer 颜色系列的精选5色

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个精选色值列表
    """
    series = _get_colorbrewer_data().get(series_name)
    if not series:
        return []
    colors = series["colors"]
    indices = [0, 2, 4, 6, 8]
    return [colors[i] for i in indices if i in colors]


def get_colorbrewer_color_series_name_mapping():
    """获取 ColorBrewer 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_colorbrewer_data().items()}


def get_colorbrewer_series_type(series_name):
    """获取指定 ColorBrewer 颜色系列的类型

    Args:
        series_name: 颜色系列名称

    Returns:
        str: 配色类型 ('sequential', 'diverging', 'qualitative') 或 None
    """
    series = _get_colorbrewer_data().get(series_name)
    if not series:
        return None
    return series.get("type", "sequential")


# ===== Radix Colors 相关函数 =====

def get_radix_color_series_names():
    """获取所有 Radix Colors 颜色系列名称列表"""
    return list(_get_radix_data().keys())


def get_radix_color_series(series_name):
    """获取指定 Radix Colors 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'radix_blue', 'radix_red' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_radix_data().get(series_name, None)


def get_radix_light_shades(series_name):
    """获取指定 Radix Colors 颜色系列的浅色组 (0-5)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 6个浅色色值列表
    """
    series = _get_radix_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(6) if i in series["colors"]]


def get_radix_dark_shades(series_name):
    """获取指定 Radix Colors 颜色系列的深色组 (6-11)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 6个深色色值列表
    """
    series = _get_radix_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(6, 12) if i in series["colors"]]


def get_radix_selected_shades(series_name):
    """获取指定 Radix Colors 颜色系列的精选5色 (0, 2, 4, 7, 9)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 5个精选色值列表
    """
    series = _get_radix_data().get(series_name)
    if not series:
        return []
    selected_indices = [0, 2, 4, 7, 9]
    return [series["colors"][i] for i in selected_indices if i in series["colors"]]


def get_radix_color_series_name_mapping():
    """获取 Radix Colors 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_radix_data().items()}


# ===== Rose Pine 延迟加载 =====
_ROSE_PINE_COLOR_DATA = None


def _load_rose_pine_data():
    """从 JSON 文件加载 Rose Pine 颜色数据

    Returns:
        dict: Rose Pine 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'rose_pine.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Rose Pine 颜色数据失败: {e}")
        return {}


def _get_rose_pine_data():
    """获取 Rose Pine 颜色数据（延迟加载）

    Returns:
        dict: Rose Pine 颜色数据字典
    """
    global _ROSE_PINE_COLOR_DATA
    if _ROSE_PINE_COLOR_DATA is None:
        _ROSE_PINE_COLOR_DATA = _load_rose_pine_data()
    return _ROSE_PINE_COLOR_DATA


# ===== Solarized 延迟加载 =====
_SOLARIZED_COLOR_DATA = None


def _load_solarized_data():
    """从 JSON 文件加载 Solarized 颜色数据

    Returns:
        dict: Solarized 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'solarized.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Solarized 颜色数据失败: {e}")
        return {}


def _get_solarized_data():
    """获取 Solarized 颜色数据（延迟加载）

    Returns:
        dict: Solarized 颜色数据字典
    """
    global _SOLARIZED_COLOR_DATA
    if _SOLARIZED_COLOR_DATA is None:
        _SOLARIZED_COLOR_DATA = _load_solarized_data()
    return _SOLARIZED_COLOR_DATA


# ===== Rose Pine 相关函数 =====

def get_rose_pine_color_series_names():
    """获取所有 Rose Pine 颜色系列名称列表"""
    return list(_get_rose_pine_data().keys())


def get_rose_pine_color_series(series_name):
    """获取指定 Rose Pine 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'rose_pine_main', 'rose_pine_moon' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_rose_pine_data().get(series_name, None)


def get_rose_pine_light_shades(series_name):
    """获取指定 Rose Pine 颜色系列的浅色组 (0-5)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 6个浅色色值列表
    """
    series = _get_rose_pine_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(6) if i in series["colors"]]


def get_rose_pine_dark_shades(series_name):
    """获取指定 Rose Pine 颜色系列的深色组 (6-11)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 6个深色色值列表
    """
    series = _get_rose_pine_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(6, 12) if i in series["colors"]]


def get_rose_pine_color_series_name_mapping():
    """获取 Rose Pine 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_rose_pine_data().items()}


# ===== Solarized 相关函数 =====

def get_solarized_color_series_names():
    """获取所有 Solarized 颜色系列名称列表"""
    return list(_get_solarized_data().keys())


def get_solarized_color_series(series_name):
    """获取指定 Solarized 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'solarized_dark', 'solarized_light' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_solarized_data().get(series_name, None)


def get_solarized_light_shades(series_name):
    """获取指定 Solarized 颜色系列的浅色组 (0-7)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 8个浅色色值列表
    """
    series = _get_solarized_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(8) if i in series["colors"]]


def get_solarized_dark_shades(series_name):
    """获取指定 Solarized 颜色系列的深色组 (8-15)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 8个深色色值列表
    """
    series = _get_solarized_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(8, 16) if i in series["colors"]]


def get_solarized_color_series_name_mapping():
    """获取 Solarized 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_solarized_data().items()}


# ===== Catppuccin 延迟加载 =====
_CATPPUCCIN_COLOR_DATA = None


def _load_catppuccin_data():
    """从 JSON 文件加载 Catppuccin 颜色数据

    Returns:
        dict: Catppuccin 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'catppuccin.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Catppuccin 颜色数据失败: {e}")
        return {}


def _get_catppuccin_data():
    """获取 Catppuccin 颜色数据（延迟加载）

    Returns:
        dict: Catppuccin 颜色数据字典
    """
    global _CATPPUCCIN_COLOR_DATA
    if _CATPPUCCIN_COLOR_DATA is None:
        _CATPPUCCIN_COLOR_DATA = _load_catppuccin_data()
    return _CATPPUCCIN_COLOR_DATA


# ===== Gruvbox 延迟加载 =====
_GRUVBOX_COLOR_DATA = None


def _load_gruvbox_data():
    """从 JSON 文件加载 Gruvbox 颜色数据

    Returns:
        dict: Gruvbox 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'gruvbox.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Gruvbox 颜色数据失败: {e}")
        return {}


def _get_gruvbox_data():
    """获取 Gruvbox 颜色数据（延迟加载）

    Returns:
        dict: Gruvbox 颜色数据字典
    """
    global _GRUVBOX_COLOR_DATA
    if _GRUVBOX_COLOR_DATA is None:
        _GRUVBOX_COLOR_DATA = _load_gruvbox_data()
    return _GRUVBOX_COLOR_DATA


# ===== Catppuccin 相关函数 =====

def get_catppuccin_color_series_names():
    """获取所有 Catppuccin 颜色系列名称列表"""
    return list(_get_catppuccin_data().keys())


def get_catppuccin_color_series(series_name):
    """获取指定 Catppuccin 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'catppuccin_latte', 'catppuccin_mocha' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_catppuccin_data().get(series_name, None)


def get_catppuccin_light_shades(series_name):
    """获取指定 Catppuccin 颜色系列的浅色组 (0-11)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 12个浅色色值列表
    """
    series = _get_catppuccin_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(12) if i in series["colors"]]


def get_catppuccin_dark_shades(series_name):
    """获取指定 Catppuccin 颜色系列的深色组 (12-23)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 12个深色色值列表
    """
    series = _get_catppuccin_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(12, 24) if i in series["colors"]]


def get_catppuccin_color_series_name_mapping():
    """获取 Catppuccin 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_catppuccin_data().items()}


# ===== Gruvbox 相关函数 =====

def get_gruvbox_color_series_names():
    """获取所有 Gruvbox 颜色系列名称列表"""
    return list(_get_gruvbox_data().keys())


def get_gruvbox_color_series(series_name):
    """获取指定 Gruvbox 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'gruvbox_dark', 'gruvbox_light' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_gruvbox_data().get(series_name, None)


def get_gruvbox_light_shades(series_name):
    """获取指定 Gruvbox 颜色系列的浅色组 (0-11)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 12个浅色色值列表
    """
    series = _get_gruvbox_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(12) if i in series["colors"]]


def get_gruvbox_dark_shades(series_name):
    """获取指定 Gruvbox 颜色系列的深色组 (12-23)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 12个深色色值列表
    """
    series = _get_gruvbox_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(12, 24) if i in series["colors"]]


def get_gruvbox_color_series_name_mapping():
    """获取 Gruvbox 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_gruvbox_data().items()}


# ===== Tokyo Night 延迟加载 =====
_TOKYO_NIGHT_COLOR_DATA = None


def _load_tokyo_night_data():
    """从 JSON 文件加载 Tokyo Night 颜色数据

    Returns:
        dict: Tokyo Night 颜色数据字典
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        json_path = os.path.join(project_root, 'color_data', 'tokyo_night.json')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 将字符串键转换为整数键
            colors_data = data.get('colors', {})
            for series in colors_data.values():
                if 'colors' in series:
                    series['colors'] = {int(k): v for k, v in series['colors'].items()}
            return colors_data
    except (OSError, json.JSONDecodeError) as e:
        print(f"加载 Tokyo Night 颜色数据失败: {e}")
        return {}


def _get_tokyo_night_data():
    """获取 Tokyo Night 颜色数据（延迟加载）

    Returns:
        dict: Tokyo Night 颜色数据字典
    """
    global _TOKYO_NIGHT_COLOR_DATA
    if _TOKYO_NIGHT_COLOR_DATA is None:
        _TOKYO_NIGHT_COLOR_DATA = _load_tokyo_night_data()
    return _TOKYO_NIGHT_COLOR_DATA


# ===== Tokyo Night 相关函数 =====

def get_tokyo_night_color_series_names():
    """获取所有 Tokyo Night 颜色系列名称列表"""
    return list(_get_tokyo_night_data().keys())


def get_tokyo_night_color_series(series_name):
    """获取指定 Tokyo Night 颜色系列的数据

    Args:
        series_name: 颜色系列名称 (如 'tokyo_night', 'tokyo_storm', 'tokyo_day' 等)

    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return _get_tokyo_night_data().get(series_name, None)


def get_tokyo_night_light_shades(series_name):
    """获取指定 Tokyo Night 颜色系列的浅色组 (0-9)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 10个浅色色值列表
    """
    series = _get_tokyo_night_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(10) if i in series["colors"]]


def get_tokyo_night_dark_shades(series_name):
    """获取指定 Tokyo Night 颜色系列的深色组 (10-18)

    Args:
        series_name: 颜色系列名称

    Returns:
        list: 9个深色色值列表
    """
    series = _get_tokyo_night_data().get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(10, 19) if i in series["colors"]]


def get_tokyo_night_color_series_name_mapping():
    """获取 Tokyo Night 颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in _get_tokyo_night_data().items()}


# ===== 统一配色组数据接口 =====

def get_all_palettes():
    """获取所有配色方案（统一格式）

    将所有配色源（nice_palettes、open_color、tailwind、material等）
    转换为统一的配色组格式，便于随机选择和展示。

    Returns:
        list: 配色组列表，每个元素为字典：
            {
                "id": 唯一标识,
                "name": 显示名称,
                "source": 来源（nice_palette/open_color/tailwind等）,
                "colors": 颜色值列表,
                "color_count": 颜色数量
            }
    """
    all_palettes = []

    # 1. Nice Color Palettes (500组，每组5色)
    nice_data = _get_nice_palettes_data()
    for index, colors in enumerate(nice_data):
        if colors:
            all_palettes.append({
                "id": f"nice_{index}",
                "name": f"配色 #{index + 1}",
                "source": "nice_palette",
                "colors": colors,
                "color_count": len(colors)
            })

    # 2. Open Color (13个系列，每组10色)
    open_color_data = _get_open_color_data()
    for series_key, series_data in open_color_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in range(len(colors_dict))]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"open_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "open_color",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 3. Tailwind Colors (22个系列，每组10色)
    tailwind_data = _get_tailwind_data()
    for series_key, series_data in tailwind_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in range(len(colors_dict))]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"tailwind_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "tailwind",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 4. Material Design (19个系列，每组10色)
    material_data = _get_material_data()
    for series_key, series_data in material_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in range(len(colors_dict))]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"material_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "material",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 5. ColorBrewer (~35个系列，每组3-9色)
    colorbrewer_data = _get_colorbrewer_data()
    for series_key, series_data in colorbrewer_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"brewer_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "colorbrewer",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 6. Radix Colors (~30个系列，每组12色)
    radix_data = _get_radix_data()
    for series_key, series_data in radix_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"radix_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "radix",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 7. Nord (4个系列，每组4色)
    nord_data = _get_nord_data()
    for series_key, series_data in nord_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"nord_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "nord",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 8. Dracula (14个系列，每组4色)
    dracula_data = _get_dracula_data()
    for series_key, series_data in dracula_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"dracula_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "dracula",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 9. Rose Pine (3个变体，每组12色)
    rose_pine_data = _get_rose_pine_data()
    for series_key, series_data in rose_pine_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"rosepine_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "rose_pine",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 10. Solarized (2个变体，每组16色)
    solarized_data = _get_solarized_data()
    for series_key, series_data in solarized_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"solarized_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "solarized",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 11. Catppuccin (4个变体，每组24色)
    catppuccin_data = _get_catppuccin_data()
    for series_key, series_data in catppuccin_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"catppuccin_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "catppuccin",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 12. Gruvbox (2个变体，每组24色)
    gruvbox_data = _get_gruvbox_data()
    for series_key, series_data in gruvbox_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"gruvbox_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "gruvbox",
                    "colors": colors,
                    "color_count": len(colors)
                })

    # 13. Tokyo Night (3个变体，每组19色)
    tokyo_night_data = _get_tokyo_night_data()
    for series_key, series_data in tokyo_night_data.items():
        colors_dict = series_data.get("colors", {})
        if colors_dict:
            colors = [colors_dict.get(i, "") for i in sorted(colors_dict.keys())]
            colors = [c for c in colors if c]
            if colors:
                all_palettes.append({
                    "id": f"tokyonight_{series_key}",
                    "name": series_data.get("name", series_key),
                    "source": "tokyo_night",
                    "colors": colors,
                    "color_count": len(colors)
                })

    return all_palettes


def get_random_palettes(count=10):
    """随机获取指定数量的配色方案

    Args:
        count: 需要返回的配色组数量（默认10）

    Returns:
        list: 随机选择的配色组列表
    """
    import random

    all_palettes = get_all_palettes()
    total = len(all_palettes)

    if total == 0:
        return []

    # 如果请求数量大于总数，返回全部
    if count >= total:
        return all_palettes

    # 随机选择指定数量
    return random.sample(all_palettes, count)
