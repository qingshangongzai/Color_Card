# Open Color 颜色数据
# 来源: https://github.com/yeun/open-color
# 许可证: MIT License
# 作者: Yeun

# Open Color 包含 13 种颜色系列，每种系列有 10 个色阶 (0-9)
# 为了适配5个色卡的界面，我们提供两种分组方式：
# 1. 浅色组 (0-4) 和 深色组 (5-9)
# 2. 精选5色 (0, 2, 4, 6, 9)

OPEN_COLOR_DATA = {
    "gray": {
        "name": "灰色",
        "name_en": "Gray",
        "colors": {
            0: "#F8F9FA",
            1: "#F1F3F5",
            2: "#E9ECEF",
            3: "#DEE2E6",
            4: "#CED4DA",
            5: "#ADB5BD",
            6: "#868E96",
            7: "#495057",
            8: "#343A40",
            9: "#212529"
        }
    },
    "red": {
        "name": "红色",
        "name_en": "Red",
        "colors": {
            0: "#FFF5F5",
            1: "#FFE3E3",
            2: "#FFC9C9",
            3: "#FFA8A8",
            4: "#FF8787",
            5: "#FF6B6B",
            6: "#FA5252",
            7: "#F03E3E",
            8: "#E03131",
            9: "#C92A2A"
        }
    },
    "pink": {
        "name": "粉色",
        "name_en": "Pink",
        "colors": {
            0: "#FFF0F6",
            1: "#FFDEEB",
            2: "#FCC2D7",
            3: "#FAA2C1",
            4: "#F783AC",
            5: "#F06595",
            6: "#E64980",
            7: "#D6336C",
            8: "#C2255C",
            9: "#A61E4D"
        }
    },
    "grape": {
        "name": "葡萄紫",
        "name_en": "Grape",
        "colors": {
            0: "#F8F0FC",
            1: "#F3D9FA",
            2: "#EEBEFA",
            3: "#E599F7",
            4: "#DA77F2",
            5: "#CC5DE8",
            6: "#BE4BDB",
            7: "#AE3EC9",
            8: "#9C36B5",
            9: "#862E9C"
        }
    },
    "violet": {
        "name": "紫罗兰",
        "name_en": "Violet",
        "colors": {
            0: "#F3F0FF",
            1: "#E5DBFF",
            2: "#D0BFFF",
            3: "#B197FC",
            4: "#9775FA",
            5: "#845EF7",
            6: "#7950F2",
            7: "#7048E8",
            8: "#6741D9",
            9: "#5F3DC4"
        }
    },
    "indigo": {
        "name": "靛蓝",
        "name_en": "Indigo",
        "colors": {
            0: "#EDF2FF",
            1: "#DBE4FF",
            2: "#BAC8FF",
            3: "#91A7FF",
            4: "#748FFC",
            5: "#5C7CFA",
            6: "#4C6EF5",
            7: "#4263EB",
            8: "#3B5BDB",
            9: "#364FC7"
        }
    },
    "blue": {
        "name": "蓝色",
        "name_en": "Blue",
        "colors": {
            0: "#E7F5FF",
            1: "#D0EBFF",
            2: "#A5D8FF",
            3: "#74C0FC",
            4: "#4DABF7",
            5: "#339AF0",
            6: "#228BE6",
            7: "#1C7ED6",
            8: "#1971C2",
            9: "#1864AB"
        }
    },
    "cyan": {
        "name": "青色",
        "name_en": "Cyan",
        "colors": {
            0: "#E3FAFC",
            1: "#C5F6FA",
            2: "#99E9F2",
            3: "#66D9E8",
            4: "#3BC9DB",
            5: "#22B8CF",
            6: "#15AABF",
            7: "#1098AD",
            8: "#0C8599",
            9: "#0B7285"
        }
    },
    "teal": {
        "name": "蓝绿",
        "name_en": "Teal",
        "colors": {
            0: "#E6FCF5",
            1: "#C3FAE8",
            2: "#96F2D7",
            3: "#63E6BE",
            4: "#38D9A9",
            5: "#20C997",
            6: "#12B886",
            7: "#0CA678",
            8: "#099268",
            9: "#087F5B"
        }
    },
    "green": {
        "name": "绿色",
        "name_en": "Green",
        "colors": {
            0: "#EBFBEE",
            1: "#D3F9D8",
            2: "#B2F2BB",
            3: "#8CE99A",
            4: "#69DB7C",
            5: "#51CF66",
            6: "#40C057",
            7: "#37B24D",
            8: "#2F9E44",
            9: "#2B8A3E"
        }
    },
    "lime": {
        "name": "柠檬绿",
        "name_en": "Lime",
        "colors": {
            0: "#F4FCE3",
            1: "#E9FAC8",
            2: "#D8F5A2",
            3: "#C0EB75",
            4: "#A9E34B",
            5: "#94D82D",
            6: "#82C91E",
            7: "#74B816",
            8: "#66A80F",
            9: "#5C940D"
        }
    },
    "yellow": {
        "name": "黄色",
        "name_en": "Yellow",
        "colors": {
            0: "#FFF9DB",
            1: "#FFF3BF",
            2: "#FFEC99",
            3: "#FFE066",
            4: "#FFD43B",
            5: "#FCC419",
            6: "#FAB005",
            7: "#F59F00",
            8: "#F08C00",
            9: "#E67700"
        }
    },
    "orange": {
        "name": "橙色",
        "name_en": "Orange",
        "colors": {
            0: "#FFF4E6",
            1: "#FFE8CC",
            2: "#FFD8A8",
            3: "#FFC078",
            4: "#FFA94D",
            5: "#FF922B",
            6: "#FD7E14",
            7: "#F76707",
            8: "#E8590C",
            9: "#D9480F"
        }
    }
}

# 获取所有颜色系列名称
def get_color_series_names():
    """获取所有颜色系列名称列表"""
    return list(OPEN_COLOR_DATA.keys())

# 获取指定颜色系列的数据
def get_color_series(series_name):
    """获取指定颜色系列的数据
    
    Args:
        series_name: 颜色系列名称 (如 'red', 'blue' 等)
    
    Returns:
        dict: 颜色系列数据，包含 name, name_en, colors
    """
    return OPEN_COLOR_DATA.get(series_name, None)

# 获取指定颜色系列的浅色组 (0-4)
def get_light_shades(series_name):
    """获取指定颜色系列的浅色组 (0-4)
    
    Args:
        series_name: 颜色系列名称
    
    Returns:
        list: 5个浅色色值列表
    """
    series = OPEN_COLOR_DATA.get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5)]

# 获取指定颜色系列的深色组 (5-9)
def get_dark_shades(series_name):
    """获取指定颜色系列的深色组 (5-9)
    
    Args:
        series_name: 颜色系列名称
    
    Returns:
        list: 5个深色色值列表
    """
    series = OPEN_COLOR_DATA.get(series_name)
    if not series:
        return []
    return [series["colors"][i] for i in range(5, 10)]

# 获取指定颜色系列的精选5色 (0, 2, 4, 6, 9)
def get_selected_shades(series_name):
    """获取指定颜色系列的精选5色 (0, 2, 4, 6, 9)
    
    Args:
        series_name: 颜色系列名称
    
    Returns:
        list: 5个精选色值列表
    """
    series = OPEN_COLOR_DATA.get(series_name)
    if not series:
        return []
    selected_indices = [0, 2, 4, 6, 9]
    return [series["colors"][i] for i in selected_indices]

# 获取所有颜色系列的中文名称映射
def get_color_series_name_mapping():
    """获取颜色系列名称的中英文映射"""
    return {key: value["name"] for key, value in OPEN_COLOR_DATA.items()}

# Open Color 许可证信息
OPEN_COLOR_LICENSE = """
MIT License

Copyright (c) 2016 heeyeun

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
