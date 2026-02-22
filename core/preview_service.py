"""预览服务模块

管理配色预览相关的业务逻辑，包括场景配置加载、模板管理、SVG配色应用等。
UI层通过PreviewService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# 第三方库导入
from PySide6.QtCore import QObject, Signal

# 项目模块导入
from .config import get_scene_type_manager, get_config_manager


class PreviewService(QObject):
    """预览服务，管理配色预览相关业务逻辑

    职责：
    - 场景配置加载和管理
    - 模板管理（获取、添加、删除）
    - SVG配色映射调用

    信号：
        scenes_loaded: 场景列表加载完成 (scene_types)
        scene_applied: 配色应用到场景完成 (result_data)
        error: 错误发生 (error_message)
    """

    # 信号
    scenes_loaded = Signal(list)           # 场景类型列表
    scene_applied = Signal(dict)           # 配色应用结果
    error = Signal(str)                    # 错误信息

    def __init__(self, parent=None):
        """初始化预览服务

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._scene_type_manager = get_scene_type_manager()
        self._config_manager = get_config_manager()

    def load_scene_types(self) -> List[Dict[str, Any]]:
        """加载所有场景类型

        Returns:
            List[Dict[str, Any]]: 场景类型配置列表
        """
        try:
            scene_types = self._scene_type_manager.get_all_scene_types()
            self.scenes_loaded.emit(scene_types)
            return scene_types
        except Exception as e:
            self.error.emit(f"加载场景类型失败: {e}")
            return []

    def get_scene_config(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """获取场景类型配置

        Args:
            scene_id: 场景类型ID

        Returns:
            Optional[Dict[str, Any]]: 场景配置，如果不存在则返回None
        """
        try:
            return self._scene_type_manager.get_scene_type_by_id(scene_id)
        except Exception as e:
            self.error.emit(f"获取场景配置失败: {e}")
            return None

    def get_scene_templates(self, scene_id: str) -> List[Dict[str, Any]]:
        """获取场景的所有模板（内置 + 用户）

        Args:
            scene_id: 场景类型ID

        Returns:
            List[Dict[str, Any]]: 模板列表
        """
        try:
            return self._scene_type_manager.get_all_templates(scene_id)
        except Exception as e:
            self.error.emit(f"获取场景模板失败: {e}")
            return []

    def get_layout_config(self, scene_id: str) -> Dict[str, Any]:
        """获取场景的布局配置

        Args:
            scene_id: 场景类型ID

        Returns:
            Dict[str, Any]: 布局配置字典
        """
        try:
            return self._scene_type_manager.get_layout_config(scene_id)
        except Exception as e:
            self.error.emit(f"获取布局配置失败: {e}")
            return {}

    def add_user_template(self, scene_id: str, template_path: str) -> Tuple[bool, str]:
        """添加用户模板到场景

        Args:
            scene_id: 场景类型ID
            template_path: 模板文件路径

        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            template_data = {
                "path": template_path,
                "name": Path(template_path).stem,
                "added_at": datetime.now().strftime("%Y-%m-%d")
            }

            success = self._config_manager.add_scene_template(scene_id, template_data)
            self._config_manager.save()

            if success:
                return True, f"已添加模板到 {scene_id} 场景"
            else:
                return False, "该模板已存在"

        except Exception as e:
            return False, f"添加模板失败: {e}"

    def remove_user_template(self, scene_id: str, template_path: str) -> Tuple[bool, str]:
        """移除用户模板

        Args:
            scene_id: 场景类型ID
            template_path: 模板文件路径

        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            success = self._config_manager.remove_scene_template(scene_id, template_path)
            self._config_manager.save()

            if success:
                return True, "模板已删除"
            else:
                return False, "模板不存在"

        except Exception as e:
            return False, f"删除模板失败: {e}"

    def get_builtin_svg_path(self, scene_type: str) -> Optional[str]:
        """获取内置SVG模板路径

        Args:
            scene_type: 场景类型ID

        Returns:
            Optional[str]: SVG文件路径，如果不存在则返回None
        """
        try:
            return self._scene_type_manager.get_builtin_svg_path(scene_type)
        except Exception as e:
            self.error.emit(f"获取内置SVG路径失败: {e}")
            return None

    def apply_colors_to_svg(self, svg_content: str, colors: List[str]) -> Tuple[bool, str]:
        """将配色应用到SVG内容

        Args:
            svg_content: 原始SVG内容
            colors: 颜色值列表（HEX格式）

        Returns:
            Tuple[bool, str]: (是否成功, 处理后的SVG内容或错误信息)
        """
        try:
            from .svg_color_mapper import SVGColorMapper

            mapper = SVGColorMapper()
            if not mapper.load_svg_from_string(svg_content):
                return False, "无法加载SVG内容"

            result = mapper.apply_intelligent_mapping(colors)
            return True, result

        except Exception as e:
            return False, f"应用配色失败: {e}"

    def validate_svg_file(self, file_path: str) -> Tuple[bool, str]:
        """验证SVG文件是否有效

        Args:
            file_path: SVG文件路径

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        path = Path(file_path)

        if not path.exists():
            return False, f"文件不存在: {file_path}"

        if not path.is_file():
            return False, f"路径不是文件: {file_path}"

        if path.suffix.lower() != '.svg':
            return False, f"文件不是SVG格式: {file_path}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                return False, "SVG文件为空"

            if '<svg' not in content.lower():
                return False, "文件内容不是有效的SVG"

            return True, ""

        except (IOError, OSError) as e:
            return False, f"文件读取错误: {e}"
        except Exception as e:
            return False, f"验证失败: {e}"

    def add_background_to_svg(self, svg_content: str, bg_color: str) -> str:
        """为 SVG 添加背景矩形

        Args:
            svg_content: 原始 SVG 内容
            bg_color: 背景颜色

        Returns:
            str: 添加背景后的 SVG 内容
        """
        try:
            import xml.etree.ElementTree as ET
            import re

            root = ET.fromstring(svg_content)
            svg_ns = 'http://www.w3.org/2000/svg'
            has_namespace = root.tag.startswith('{')

            viewbox = root.get('viewBox', '')
            width = root.get('width', '0')
            height = root.get('height', '0')

            if viewbox:
                parts = viewbox.split()
                if len(parts) >= 4:
                    x, y, w, h = parts[0], parts[1], parts[2], parts[3]
                else:
                    return svg_content
            elif width and height:
                w = re.sub(r'[^\d.]', '', width)
                h = re.sub(r'[^\d.]', '', height)
                x, y = '0', '0'
            else:
                return svg_content

            if has_namespace:
                bg_rect = ET.Element(f'{{{svg_ns}}}rect')
            else:
                bg_rect = ET.Element('rect')

            bg_rect.set('x', x)
            bg_rect.set('y', y)
            bg_rect.set('width', w)
            bg_rect.set('height', h)
            bg_rect.set('fill', bg_color)

            root.insert(0, bg_rect)
            return ET.tostring(root, encoding='unicode')

        except Exception as e:
            print(f"添加背景失败: {e}")
            return svg_content

    def has_fixed_background_element(self, svg_content: str) -> bool:
        """检查SVG是否有固定颜色的背景元素

        Args:
            svg_content: SVG 内容

        Returns:
            bool: 是否有固定背景元素
        """
        if not svg_content:
            return False

        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(svg_content)

            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'rect':
                    fixed_color = elem.get('data-fixed-color')
                    if fixed_color == 'original':
                        return True
            return False
        except Exception:
            return False

    def extract_hex_colors_from_favorite(self, favorite: Dict[str, Any]) -> List[str]:
        """从收藏数据中提取 HEX 颜色列表

        Args:
            favorite: 收藏数据字典

        Returns:
            List[str]: HEX 颜色列表
        """
        colors_data = favorite.get('colors', [])
        hex_colors = []

        for color_info in colors_data:
            hex_value = color_info.get('hex', '') if isinstance(color_info, dict) else color_info
            if hex_value:
                if not hex_value.startswith('#'):
                    hex_value = '#' + hex_value
                hex_colors.append(hex_value)

        return hex_colors if hex_colors else ["#E8E8E8"]

    def save_svg_to_file(self, svg_content: str, file_path: str) -> Tuple[bool, str]:
        """保存 SVG 内容到文件

        Args:
            svg_content: SVG 内容
            file_path: 文件路径

        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            return True, f"已保存到: {file_path}"
        except (IOError, OSError) as e:
            return False, f"文件写入错误: {e}"
        except Exception as e:
            return False, f"保存失败: {e}"

    def generate_export_filename(self, prefix: str = "color_card") -> str:
        """生成导出文件名

        Args:
            prefix: 文件名前缀

        Returns:
            str: 生成的文件名
        """
        return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
