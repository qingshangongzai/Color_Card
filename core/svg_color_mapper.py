"""SVG 配色映射模块 - 智能识别 SVG 中的配色区域并应用配色方案"""

# 标准库导入
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set


class ElementType(Enum):
    """SVG 元素类型分类"""
    BACKGROUND = auto()      # 背景元素
    PRIMARY = auto()         # 主元素
    SECONDARY = auto()       # 次要元素
    ACCENT = auto()          # 强调元素
    TEXT = auto()            # 文字元素
    STROKE = auto()          # 描边元素
    UNKNOWN = auto()         # 未知类型


@dataclass
class SVGElementInfo:
    """SVG 元素信息"""
    element_id: str                          # 元素 ID
    tag: str                                 # 元素标签名
    element_class: Optional[str] = None      # 元素 class
    element_type: ElementType = ElementType.UNKNOWN  # 元素类型
    fill_color: Optional[str] = None         # 原始 fill 颜色
    stroke_color: Optional[str] = None       # 原始 stroke 颜色
    area: float = 0.0                        # 元素面积（用于排序）
    is_visible: bool = True                  # 是否可见
    attributes: Dict[str, str] = field(default_factory=dict)  # 其他属性


@dataclass
class ColorMappingConfig:
    """颜色映射配置"""
    background_color: Optional[str] = None   # 背景色
    primary_color: Optional[str] = None      # 主色
    secondary_color: Optional[str] = None    # 次要色
    accent_color: Optional[str] = None       # 强调色
    text_color: Optional[str] = None         # 文字色
    stroke_color: Optional[str] = None       # 描边统一色

    def get_color_for_type(self, element_type: ElementType) -> Optional[str]:
        """根据元素类型获取对应颜色"""
        mapping = {
            ElementType.BACKGROUND: self.background_color,
            ElementType.PRIMARY: self.primary_color,
            ElementType.SECONDARY: self.secondary_color,
            ElementType.ACCENT: self.accent_color,
            ElementType.TEXT: self.text_color,
            ElementType.STROKE: self.stroke_color,
        }
        return mapping.get(element_type)


class SVGElementClassifier:
    """SVG 元素分类器 - 根据元素特征识别配色区域类型"""

    # Class/ID 关键词映射（优先级最高）
    CLASS_KEYWORDS = {
        'background': ElementType.BACKGROUND,
        'bg': ElementType.BACKGROUND,
        'back': ElementType.BACKGROUND,
        'primary': ElementType.PRIMARY,
        'main': ElementType.PRIMARY,
        'secondary': ElementType.SECONDARY,
        'sub': ElementType.SECONDARY,
        'accent': ElementType.ACCENT,
        'highlight': ElementType.ACCENT,
        'text': ElementType.TEXT,
        'title': ElementType.TEXT,
        'label': ElementType.TEXT,
        'stroke': ElementType.STROKE,
        'border': ElementType.STROKE,
        'line': ElementType.STROKE,
    }

    def classify(self, element: ET.Element, area: float = 0.0, 
                 is_largest_rect: bool = False, total_rect_count: int = 0) -> ElementType:
        """对元素进行分类

        Args:
            element: SVG 元素
            area: 元素面积（用于判断背景）
            is_largest_rect: 是否是面积最大的矩形
            total_rect_count: 矩形总数

        Returns:
            ElementType: 元素类型
        """
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        # 1. 检查 class 属性（最高优先级）
        element_class = element.get('class', '')
        if element_class:
            for keyword, elem_type in self.CLASS_KEYWORDS.items():
                if keyword in element_class.lower():
                    return elem_type

        # 2. 检查 id 属性
        element_id = element.get('id', '')
        if element_id:
            for keyword, elem_type in self.CLASS_KEYWORDS.items():
                if keyword in element_id.lower():
                    return elem_type

        # 3. 根据标签类型和上下文智能判断
        if tag == 'rect':
            # 矩形分类策略：
            # - 如果只有一个矩形或面积最大 -> 可能是背景
            # - 如果有多个矩形且不是最大的 -> 可能是装饰/主元素
            # - 大面积矩形（>10000）-> 背景
            if is_largest_rect and area > 5000:
                return ElementType.BACKGROUND
            elif area > 10000:
                return ElementType.BACKGROUND
            elif total_rect_count > 1:
                # 多个矩形时，小矩形作为装饰元素
                return ElementType.PRIMARY if area < 5000 else ElementType.BACKGROUND
            else:
                return ElementType.BACKGROUND
        
        elif tag in ['path', 'polygon', 'polyline']:
            return ElementType.PRIMARY
            
        elif tag in ['circle', 'ellipse']:
            return ElementType.PRIMARY
            
        elif tag == 'line':
            return ElementType.SECONDARY
            
        elif tag in ['text', 'tspan']:
            return ElementType.TEXT

        return ElementType.UNKNOWN


class SVGColorMapper:
    """SVG 颜色映射器 - 智能分配配色到 SVG 元素"""

    # SVG 命名空间
    SVG_NS = 'http://www.w3.org/2000/svg'
    NSMAP = {'svg': SVG_NS}

    def __init__(self):
        self._classifier = SVGElementClassifier()
        self._elements: List[SVGElementInfo] = []
        self._original_content: str = ""
        self._modified_content: str = ""
        self._element_counter: int = 0
        self._css_styles: Dict[str, Dict[str, str]] = {}  # 存储解析的 CSS 样式

    def load_svg(self, file_path: str) -> bool:
        """加载 SVG 文件

        Args:
            file_path: SVG 文件路径

        Returns:
            bool: 是否加载成功
        """
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"文件不存在: {file_path}")
                return False

            self._original_content = path.read_text(encoding='utf-8')
            self._parse_svg()
            return True
        except Exception as e:
            print(f"加载 SVG 失败: {e}")
            return False

    def load_svg_from_string(self, content: str) -> bool:
        """从字符串加载 SVG

        Args:
            content: SVG 内容字符串

        Returns:
            bool: 是否加载成功
        """
        try:
            self._original_content = content
            self._parse_svg()
            return True
        except Exception as e:
            print(f"解析 SVG 失败: {e}")
            return False

    def _parse_svg(self):
        """解析 SVG 内容，提取元素信息"""
        self._elements = []
        self._element_counter = 0
        self._css_styles = {}

        try:
            # 注册命名空间
            for prefix, uri in self.NSMAP.items():
                ET.register_namespace(prefix, uri)

            root = ET.fromstring(self._original_content)
            
            # 先解析 CSS 样式
            self._extract_css_styles(root)
            
            # 再提取元素（会给无 ID 的元素添加 ID）
            self._extract_elements(root)
            
            # 保存添加了 ID 的 XML
            self._original_content = self._element_tree_to_string(root)

            # 按面积排序，便于识别背景
            self._elements.sort(key=lambda x: x.area, reverse=True)

        except ET.ParseError as e:
            print(f"SVG 解析错误: {e}")

    def _extract_css_styles(self, root: ET.Element):
        """提取 SVG 中的 CSS 样式定义"""
        # 查找 <style> 元素
        for style_elem in root.iter():
            tag = style_elem.tag.split('}')[-1] if '}' in style_elem.tag else style_elem.tag
            if tag == 'style':
                style_text = style_elem.text
                if style_text:
                    self._parse_css(style_text)

    def _parse_css(self, css_text: str):
        """解析 CSS 文本，提取类选择器样式"""
        # 匹配 .class-name { property: value; }
        pattern = r'\.([a-zA-Z0-9_-]+)\s*\{([^}]+)\}'
        matches = re.findall(pattern, css_text)
        
        for class_name, declarations in matches:
            styles = {}
            # 解析每个属性声明
            for decl in declarations.split(';'):
                decl = decl.strip()
                if ':' in decl:
                    prop, value = decl.split(':', 1)
                    styles[prop.strip()] = value.strip()
            
            if styles:
                self._css_styles[class_name] = styles
                
        print(f"解析到 {len(self._css_styles)} 个 CSS 类样式")

    def _get_element_styles(self, elem: ET.Element) -> Dict[str, str]:
        """获取元素的所有样式（包括 CSS 类和内联样式）"""
        styles = {}
        
        # 1. 应用 CSS 类样式
        elem_class = elem.get('class', '')
        if elem_class:
            # 可能有多个 class，如 "cls-1 cls-2"
            for cls in elem_class.split():
                cls = cls.strip()
                if cls in self._css_styles:
                    styles.update(self._css_styles[cls])
        
        # 2. 应用内联样式（覆盖 CSS 类）
        style_attr = elem.get('style', '')
        if style_attr:
            for decl in style_attr.split(';'):
                decl = decl.strip()
                if ':' in decl:
                    prop, value = decl.split(':', 1)
                    styles[prop.strip()] = value.strip()
        
        return styles

    def _extract_elements(self, root: ET.Element):
        """递归提取 SVG 元素"""
        # 可着色标签列表
        colorable_tags = ['rect', 'circle', 'ellipse', 'path', 'polygon', 'polyline', 'line', 'text', 'tspan']
        
        # 第一遍：收集所有矩形信息
        rect_areas = []
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'rect':
                area = self._calculate_element_area(elem)
                rect_areas.append((elem, area))
        
        # 找出最大矩形
        max_rect_area = max([a for _, a in rect_areas]) if rect_areas else 0
        total_rect_count = len(rect_areas)
        
        # 第二遍：提取所有元素
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            # 跳过非图形元素
            if tag in ['svg', 'defs', 'metadata', 'title', 'desc', 'filter', 'g', 'clipPath', 'mask', 'style']:
                continue

            # 生成唯一 ID
            elem_id = elem.get('id', f"__generated_id_{self._element_counter}")
            if not elem.get('id'):
                elem.set('id', elem_id)
                self._element_counter += 1

            # 获取元素的所有样式（包括 CSS 类和内联样式）
            styles = self._get_element_styles(elem)
            
            # 提取颜色信息（优先从样式获取，然后是属性）
            fill = styles.get('fill') or elem.get('fill')
            stroke = styles.get('stroke') or elem.get('stroke')

            # 判断是否是可见图形元素
            has_explicit_fill = fill and fill.lower() not in ('none', 'transparent')
            has_explicit_stroke = stroke and stroke.lower() not in ('none', 'transparent')
            
            # 跳过真正无颜色的元素
            if tag not in colorable_tags and not has_explicit_fill and not has_explicit_stroke:
                continue

            # 计算面积（简化版）
            area = self._calculate_element_area(elem)

            # 创建元素信息 - 修复：只有当确实有颜色时才记录，不使用默认值
            elem_info = SVGElementInfo(
                element_id=elem_id,
                tag=tag,
                element_class=elem.get('class'),
                fill_color=fill if has_explicit_fill else None,
                stroke_color=stroke if has_explicit_stroke else None,
                area=area,
                attributes=dict(elem.attrib)
            )

            # 判断是否是最大矩形
            is_largest_rect = (tag == 'rect' and area == max_rect_area and area > 0)
            
            # 分类元素
            elem_info.element_type = self._classifier.classify(elem, area, is_largest_rect, total_rect_count)

            self._elements.append(elem_info)

    def _calculate_element_area(self, elem: ET.Element) -> float:
        """计算元素面积（简化计算）"""
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        try:
            if tag == 'rect':
                width = float(elem.get('width', 0))
                height = float(elem.get('height', 0))
                return width * height

            elif tag == 'circle':
                r = float(elem.get('r', 0))
                return 3.14159 * r * r

            elif tag == 'ellipse':
                rx = float(elem.get('rx', 0))
                ry = float(elem.get('ry', 0))
                return 3.14159 * rx * ry

            elif tag in ['path', 'polygon', 'polyline']:
                # 简化：根据边界框估算
                return 1000.0  # 默认值

        except (ValueError, TypeError):
            pass

        return 0.0

    def get_elements(self) -> List[SVGElementInfo]:
        """获取所有可着色元素"""
        return self._elements.copy()

    def get_elements_by_type(self, element_type: ElementType) -> List[SVGElementInfo]:
        """按类型获取元素"""
        return [e for e in self._elements if e.element_type == element_type]

    def auto_classify_background(self):
        """自动识别背景元素（面积最大的矩形）"""
        if not self._elements:
            return

        # 找出面积最大的元素
        largest = max(self._elements, key=lambda x: x.area)

        # 如果面积足够大且是矩形，标记为背景
        if largest.area > 5000 and largest.tag in ['rect', 'svg']:
            largest.element_type = ElementType.BACKGROUND

    def apply_color_mapping(self, config: ColorMappingConfig) -> str:
        """应用颜色映射

        Args:
            config: 颜色映射配置

        Returns:
            str: 修改后的 SVG 内容
        """
        if not self._original_content:
            return ""

        # 解析 XML
        root = ET.fromstring(self._original_content)

        # 应用映射
        for elem_info in self._elements:
            elem = self._find_element_by_id(root, elem_info.element_id)
            if elem is None:
                continue

            # 获取对应颜色
            color = config.get_color_for_type(elem_info.element_type)
            if not color:
                continue

            # 应用颜色 - 直接设置内联属性，这会覆盖 CSS 类样式
            # 1. 处理 fill
            should_apply_fill = (
                elem_info.fill_color is not None or  # 有显式 fill
                elem_info.tag in ['text', 'tspan'] or  # 文字元素
                elem_info.element_type in [ElementType.PRIMARY, ElementType.SECONDARY, ElementType.ACCENT, ElementType.BACKGROUND]  # 图形元素
            )
            
            if should_apply_fill:
                elem.set('fill', color)

            # 2. 处理 stroke
            if elem_info.stroke_color is not None:
                elem.set('stroke', color)

        # 转换回字符串
        self._modified_content = self._element_tree_to_string(root)
        return self._modified_content

    def _get_svg_canvas_size(self) -> Tuple[float, float]:
        """获取 SVG 画布大小

        Returns:
            (width, height): 画布宽度和高度
        """
        try:
            root = ET.fromstring(self._original_content)
            # 获取 viewBox
            viewbox = root.get('viewBox', '')
            if viewbox:
                parts = viewbox.split()
                if len(parts) >= 4:
                    width = float(parts[2])
                    height = float(parts[3])
                    return (width, height)

            # 如果没有 viewBox，尝试 width 和 height 属性
            width = root.get('width', '0')
            height = root.get('height', '0')

            # 移除可能的单位（如 px）
            width = re.sub(r'[^\d.]', '', width)
            height = re.sub(r'[^\d.]', '', height)

            return (float(width), float(height))
        except Exception:
            return (0.0, 0.0)

    def _has_background_element(self) -> bool:
        """检测 SVG 是否有背景元素

        判断标准：是否有 fill 元素面积超过画布面积的 50%

        Returns:
            是否有背景元素
        """
        canvas_width, canvas_height = self._get_svg_canvas_size()
        if canvas_width <= 0 or canvas_height <= 0:
            return False

        canvas_area = canvas_width * canvas_height
        if canvas_area <= 0:
            return False

        # 检查每个 fill 元素的面积
        for elem_info in self._elements:
            if elem_info.fill_color and elem_info.area > canvas_area * 0.5:
                print(f"检测到背景元素: {elem_info.element_id}, 面积: {elem_info.area}, 画布面积: {canvas_area}")
                return True

        return False

    def apply_intelligent_mapping(self, colors: List[str]) -> str:
        """智能映射配色

        策略：
        1. 分别收集 fill 和 stroke 的原始颜色
        2. 检测 SVG 是否有背景元素
        3. 如果有背景：背景映射到新配色[0]，主体元素映射到新配色[1..n]
        4. 如果没有背景（透明）：所有元素映射到新配色[1..n]
        5. stroke 颜色保持原色（不替换）
        6. 应用映射到所有元素

        Args:
            colors: 颜色列表

        Returns:
            str: 修改后的 SVG 内容
        """
        if not colors or not self._original_content:
            return self._original_content

        # 1. 分别收集 fill 和 stroke 颜色及其面积
        fill_color_areas: Dict[str, float] = {}
        stroke_color_areas: Dict[str, float] = {}

        for elem_info in self._elements:
            # 收集 fill 颜色
            if elem_info.fill_color:
                normalized_color = self._normalize_color(elem_info.fill_color)
                if normalized_color:
                    fill_color_areas[normalized_color] = fill_color_areas.get(normalized_color, 0) + elem_info.area
            # 收集 stroke 颜色
            if elem_info.stroke_color:
                normalized_color = self._normalize_color(elem_info.stroke_color)
                if normalized_color:
                    stroke_color_areas[normalized_color] = stroke_color_areas.get(normalized_color, 0) + elem_info.area

        if not fill_color_areas and not stroke_color_areas:
            print("未找到任何可替换的颜色")
            return self._original_content

        # 2. 检测是否有背景元素
        has_background = self._has_background_element()
        print(f"SVG 是否有背景元素: {has_background}")

        # 3. 创建 fill 颜色映射表
        fill_color_map: Dict[str, str] = {}

        # 按面积排序 fill 颜色
        sorted_fill_colors = sorted(fill_color_areas.keys(), key=lambda c: fill_color_areas[c], reverse=True)

        print(f"原始 fill 颜色（按面积排序）: {sorted_fill_colors}")
        print(f"新配色: {colors}")

        if len(sorted_fill_colors) > 0 and len(colors) > 0:
            if has_background and len(colors) > 1:
                # 有背景元素：背景映射到新配色[0]，其他映射到新配色[1..n]
                background_color = sorted_fill_colors[0]
                fill_color_map[background_color] = colors[0]
                print(f"背景色 {background_color} -> {colors[0]}")

                # 其他颜色是主体色，映射到新配色[1..n]
                other_colors = sorted_fill_colors[1:]
                for i, orig_color in enumerate(other_colors):
                    # 使用新配色[1..n]，如果不够则循环使用
                    color_index = (i % (len(colors) - 1)) + 1
                    fill_color_map[orig_color] = colors[color_index]
                    print(f"主体色 {orig_color} -> {colors[color_index]}")
            else:
                # 无背景元素（透明背景）：所有元素映射到新配色[1..n]
                # 如果只有一个颜色，则所有元素都映射到该颜色
                start_index = 1 if len(colors) > 1 else 0
                for i, orig_color in enumerate(sorted_fill_colors):
                    if len(colors) > 1:
                        color_index = (i % (len(colors) - 1)) + 1
                    else:
                        color_index = 0
                    fill_color_map[orig_color] = colors[color_index]
                    print(f"元素色 {orig_color} -> {colors[color_index]}")

        # 4. 创建 stroke 颜色映射表（保持原色，不替换）
        stroke_color_map: Dict[str, str] = {}
        # stroke 颜色保持原色，不参与映射

        print(f"fill 颜色映射: {fill_color_map}")
        print(f"stroke 颜色保持原色: {list(stroke_color_areas.keys())}")

        # 5. 合并映射表并应用
        color_map = {**fill_color_map, **stroke_color_map}
        return self._apply_color_map(color_map)

    def _normalize_color(self, color: str) -> Optional[str]:
        """标准化颜色值

        Args:
            color: 原始颜色值

        Returns:
            标准化后的颜色值，如果不是有效颜色则返回 None
        """
        if not color:
            return None

        color = color.strip().lower()

        # 跳过特殊值
        if color in ('none', 'transparent', 'inherit', 'currentcolor'):
            return None

        # 标准化十六进制颜色
        if color.startswith('#'):
            # 确保格式统一（小写）
            return color

        # 处理 rgb() 格式
        if color.startswith('rgb'):
            return color

        # 处理颜色名称（如 "black", "white" 等）
        return color

    def _apply_color_map(self, color_map: Dict[str, str]) -> str:
        """应用颜色映射表

        Args:
            color_map: 原始颜色到新颜色的映射

        Returns:
            str: 修改后的 SVG 内容
        """
        if not self._original_content:
            return ""

        # 解析 XML
        root = ET.fromstring(self._original_content)

        # 创建大小写不敏感的颜色映射查找表
        # color_map 的键已经是小写的（由 _normalize_color 处理）
        # 但 elem_info 中的颜色可能是原始大小写
        color_map_lower = {k.lower(): v for k, v in color_map.items()}

        # 应用映射到元素
        mapped_count = 0
        for elem_info in self._elements:
            elem = self._find_element_by_id(root, elem_info.element_id)
            if elem is None:
                continue

            # 应用 fill 颜色映射
            if elem_info.fill_color:
                fill_lower = elem_info.fill_color.lower()
                if fill_lower in color_map_lower:
                    new_color = color_map_lower[fill_lower]
                    # 检查颜色是否来自 style 属性
                    style_attr = elem.get('style', '')
                    if style_attr and self._color_in_style(style_attr, elem_info.fill_color):
                        # 替换 style 属性中的颜色
                        new_style = self._replace_color_in_style(style_attr, elem_info.fill_color, new_color)
                        elem.set('style', new_style)
                    else:
                        # 设置 fill 属性
                        elem.set('fill', new_color)
                    mapped_count += 1

            # 应用 stroke 颜色映射
            if elem_info.stroke_color:
                stroke_lower = elem_info.stroke_color.lower()
                if stroke_lower in color_map_lower:
                    new_color = color_map_lower[stroke_lower]
                    # 检查颜色是否来自 style 属性
                    style_attr = elem.get('style', '')
                    if style_attr and self._color_in_style(style_attr, elem_info.stroke_color):
                        # 替换 style 属性中的颜色
                        new_style = self._replace_color_in_style(style_attr, elem_info.stroke_color, new_color)
                        elem.set('style', new_style)
                    else:
                        # 设置 stroke 属性
                        elem.set('stroke', new_color)
                    mapped_count += 1

        # 同时修改 CSS 样式定义（如果存在）
        self._update_css_styles(root, color_map)

        # 转换回字符串
        self._modified_content = self._element_tree_to_string(root)
        print(f"成功映射 {mapped_count} 个元素的颜色")
        return self._modified_content

    def _color_in_style(self, style_attr: str, color: str) -> bool:
        """检查颜色是否存在于 style 属性中

        Args:
            style_attr: style 属性值
            color: 颜色值

        Returns:
            是否存在
        """
        import re
        color_lower = color.lower()
        # 匹配 fill:color 或 stroke:color (可能有空格)
        pattern = rf'(fill|stroke)\s*:\s*({re.escape(color_lower)}|{re.escape(color)})'
        return bool(re.search(pattern, style_attr, re.IGNORECASE))

    def _replace_color_in_style(self, style_attr: str, old_color: str, new_color: str) -> str:
        """替换 style 属性中的颜色值

        Args:
            style_attr: 原始 style 属性值
            old_color: 旧颜色
            new_color: 新颜色

        Returns:
            替换后的 style 属性值
        """
        import re

        result = style_attr
        old_color_lower = old_color.lower()

        # 使用正则表达式匹配 fill 和 stroke 属性
        # 匹配模式: fill:#color 或 fill: #color (可能有空格)
        fill_pattern = rf'(fill\s*:\s*)({re.escape(old_color_lower)}|{re.escape(old_color)})'
        stroke_pattern = rf'(stroke\s*:\s*)({re.escape(old_color_lower)}|{re.escape(old_color)})'

        # 替换 fill 颜色
        result = re.sub(fill_pattern, rf'\g<1>{new_color}', result, flags=re.IGNORECASE)

        # 替换 stroke 颜色
        result = re.sub(stroke_pattern, rf'\g<1>{new_color}', result, flags=re.IGNORECASE)

        return result

    def _update_css_styles(self, root: ET.Element, color_map: Dict[str, str]):
        """更新 CSS 样式定义中的颜色

        Args:
            root: SVG 根元素
            color_map: 颜色映射表
        """
        for style_elem in root.iter():
            tag = style_elem.tag.split('}')[-1] if '}' in style_elem.tag else style_elem.tag
            if tag == 'style' and style_elem.text:
                css_text = style_elem.text
                modified_css = css_text

                # 替换 CSS 中的颜色值
                for old_color, new_color in color_map.items():
                    # 匹配 fill:color 和 stroke:color 模式
                    patterns = [
                        (rf'(fill:\s*)({re.escape(old_color)})', rf'\1{new_color}'),
                        (rf'(stroke:\s*)({re.escape(old_color)})', rf'\1{new_color}'),
                        # 也匹配没有空格的版本
                        (rf'(fill:)({re.escape(old_color)})', rf'\1{new_color}'),
                        (rf'(stroke:)({re.escape(old_color)})', rf'\1{new_color}'),
                    ]

                    for pattern, replacement in patterns:
                        modified_css = re.sub(pattern, replacement, modified_css, flags=re.IGNORECASE)

                if modified_css != css_text:
                    style_elem.text = modified_css
                    print(f"已更新 CSS 样式中的颜色映射")

    def set_element_color(self, element_id: str, color: str, color_type: str = 'fill') -> bool:
        """设置单个元素的颜色

        Args:
            element_id: 元素 ID
            color: 颜色值
            color_type: 'fill' 或 'stroke'

        Returns:
            bool: 是否设置成功
        """
        for elem_info in self._elements:
            if elem_info.element_id == element_id:
                if color_type == 'fill':
                    elem_info.fill_color = color
                elif color_type == 'stroke':
                    elem_info.stroke_color = color
                return True
        return False

    def set_element_type(self, element_id: str, element_type: ElementType) -> bool:
        """设置元素类型

        Args:
            element_id: 元素 ID
            element_type: 元素类型

        Returns:
            bool: 是否设置成功
        """
        for elem_info in self._elements:
            if elem_info.element_id == element_id:
                elem_info.element_type = element_type
                return True
        return False

    def _find_element_by_id(self, root: ET.Element, element_id: str) -> Optional[ET.Element]:
        """根据 ID 查找元素"""
        for elem in root.iter():
            if elem.get('id') == element_id:
                return elem
        return None

    def _element_tree_to_string(self, root: ET.Element) -> str:
        """将 ElementTree 转换为字符串"""
        # 注册命名空间
        for prefix, uri in self.NSMAP.items():
            ET.register_namespace(prefix, uri)

        # 转换
        return ET.tostring(root, encoding='unicode')

    def get_modified_content(self) -> str:
        """获取修改后的 SVG 内容"""
        return self._modified_content

    def get_original_content(self) -> str:
        """获取原始 SVG 内容"""
        return self._original_content

    def get_statistics(self) -> Dict[str, int]:
        """获取元素统计信息"""
        stats = {t.name: 0 for t in ElementType}
        for elem in self._elements:
            stats[elem.element_type.name] += 1
        return stats

    def reset(self):
        """重置所有修改"""
        self._modified_content = self._original_content
        self._parse_svg()


def create_mapping_from_palette(colors: List[str]) -> ColorMappingConfig:
    """从配色方案创建映射配置

    Args:
        colors: 配色方案颜色列表

    Returns:
        ColorMappingConfig: 颜色映射配置
    """
    config = ColorMappingConfig()

    if not colors:
        return config

    # 按数量分配
    if len(colors) >= 1:
        config.background_color = colors[0]
    if len(colors) >= 2:
        config.primary_color = colors[1]
    if len(colors) >= 3:
        config.secondary_color = colors[2]
    if len(colors) >= 4:
        config.accent_color = colors[3]
    if len(colors) >= 5:
        config.text_color = colors[4]
        config.stroke_color = colors[4]

    return config


def suggest_mapping_strategy(elements: List[SVGElementInfo]) -> Dict[str, Any]:
    """根据 SVG 元素组成建议映射策略

    Args:
        elements: SVG 元素列表

    Returns:
        Dict: 建议策略信息
    """
    stats = {}
    for elem in elements:
        elem_type = elem.element_type.name
        stats[elem_type] = stats.get(elem_type, 0) + 1

    # 分析建议
    suggestions = {
        'has_background': stats.get('BACKGROUND', 0) > 0,
        'has_text': stats.get('TEXT', 0) > 0,
        'primary_count': stats.get('PRIMARY', 0),
        'total_elements': len(elements),
        'recommended_colors': min(5, len(elements)),
    }

    # 建议颜色分配
    color_allocation = []
    if suggestions['has_background']:
        color_allocation.append(('BACKGROUND', '背景'))
    if suggestions['primary_count'] > 0:
        color_allocation.append(('PRIMARY', '主元素'))
    if stats.get('SECONDARY', 0) > 0:
        color_allocation.append(('SECONDARY', '次要元素'))
    if stats.get('ACCENT', 0) > 0:
        color_allocation.append(('ACCENT', '强调元素'))
    if suggestions['has_text'] or stats.get('STROKE', 0) > 0:
        color_allocation.append(('TEXT/STROKE', '文字/描边'))

    suggestions['color_allocation'] = color_allocation

    return suggestions
