"""预览组件模块 - 重构版本

提供配色预览相关的UI组件，包括：
- 可拖拽颜色圆点
- 颜色圆点工具栏
- 预览场景基类和工厂
- SVG预览组件
- 布局系统（单图、滚动、网格、混合）
- 预览场景选择器
- 预览面板
- 预览工具栏
"""
# 标准库导入
from typing import List, Optional, Dict, Any

# 第三方库导入
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSizePolicy, QPushButton, QLabel, QApplication
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QMimeData
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QDrag, QPixmap, QFontMetrics
)
from PySide6.QtSvg import QSvgRenderer
from qfluentwidgets import (
    ComboBox, PushButton, SubtitleLabel, FluentIcon, isDarkTheme, qconfig,
    RoundMenu, Action, InfoBar, InfoBarPosition, ScrollArea
)

# 项目模块导入
from ui.theme_colors import get_border_color, get_text_color


# ============================================================================
# 可拖拽颜色圆点组件
# ============================================================================

class DraggableColorDot(QWidget):
    """可拖拽的颜色圆点组件"""

    clicked = Signal(int)                # 点击信号：索引
    delete_requested = Signal(int)       # 删除请求信号：索引

    def __init__(self, color: str, index: int, parent=None):
        """初始化颜色圆点

        Args:
            color: 颜色值（HEX格式）
            index: 圆点索引
            parent: 父控件
        """
        self._color = color
        self._index = index
        self._drag_start_pos = QPoint()
        self._hex_visible = True             # HEX值显示开关
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    @property
    def color(self) -> str:
        """获取颜色值"""
        return self._color

    @color.setter
    def color(self, value: str):
        """设置颜色值"""
        self._color = value
        self.update()

    @property
    def index(self) -> int:
        """获取索引"""
        return self._index

    @index.setter
    def index(self, value: int):
        """设置索引"""
        self._index = value

    def paintEvent(self, event):
        """绘制圆点"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆点背景
        color = QColor(self._color)
        painter.setBrush(QBrush(color))

        # 绘制边框
        border_color = get_border_color()
        painter.setPen(QPen(border_color, 1))

        # 绘制圆形
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawEllipse(rect)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 处理拖拽"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        # 检查移动距离是否超过拖拽阈值
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return

        # 创建拖拽对象
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self._index))
        drag.setMimeData(mime_data)

        # 创建拖拽时的预览图像
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(self.width() // 2, self.height() // 2))

        # 执行拖拽
        drag.exec(Qt.DropAction.MoveAction)

        # 拖拽结束后恢复光标
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            # 检查是否是点击（没有发生拖拽）
            if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
                self.clicked.emit(self._index)

    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        self.clicked.emit(self._index)

    def set_hex_visible(self, visible: bool):
        """设置HEX值显示开关

        Args:
            visible: 是否显示HEX值
        """
        self._hex_visible = visible

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        menu = RoundMenu("", self)

        # 如果开启HEX显示，添加HEX值和复制按钮
        if self._hex_visible:
            # HEX值显示和复制
            hex_value = self._color.upper()
            copy_action = Action(FluentIcon.COPY, f"{hex_value}")
            copy_action.triggered.connect(self._copy_hex_to_clipboard)
            menu.addAction(copy_action)
            menu.addSeparator()

        # 删除选项
        delete_action = Action(FluentIcon.DELETE, "删除")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self._index))
        menu.addAction(delete_action)
        menu.exec(event.globalPos())

    def _copy_hex_to_clipboard(self):
        """复制HEX值到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._color.upper())


# ============================================================================
# 颜色圆点工具栏
# ============================================================================

class ColorDotBar(QWidget):
    """颜色圆点工具栏，支持拖拽排序"""

    order_changed = Signal(list)         # 颜色顺序变化信号：新的颜色列表
    color_clicked = Signal(int)          # 颜色点击信号：索引
    color_deleted = Signal(list)         # 颜色删除信号：新的颜色列表

    def __init__(self, parent=None):
        """初始化颜色圆点工具栏

        Args:
            parent: 父控件
        """
        self._colors: List[str] = []
        self._dots: List[DraggableColorDot] = []
        self._insert_indicator_pos = -1    # 插入指示器位置（-1表示不显示）
        self._hex_visible = True             # HEX值显示开关
        super().__init__(parent)
        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        """创建UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        layout.addStretch()
        self.setFixedHeight(50)

    def set_colors(self, colors: List[str]):
        """设置颜色列表

        Args:
            colors: 颜色值列表（HEX格式）
        """
        self._colors = colors.copy() if colors else []
        self._rebuild_dots()

    def _rebuild_dots(self):
        """重建所有圆点"""
        # 清除现有圆点
        layout = self.layout()
        for dot in self._dots:
            layout.removeWidget(dot)
            dot.deleteLater()
        self._dots.clear()

        # 创建新圆点
        for i, color in enumerate(self._colors):
            dot = DraggableColorDot(color, i)
            dot.clicked.connect(self._on_dot_clicked)
            dot.delete_requested.connect(self._on_dot_delete_requested)
            dot.set_hex_visible(self._hex_visible)
            self._dots.append(dot)
            layout.insertWidget(layout.count() - 1, dot)

    def set_hex_visible(self, visible: bool):
        """设置HEX值显示开关

        Args:
            visible: 是否显示HEX值
        """
        self._hex_visible = visible
        for dot in self._dots:
            dot.set_hex_visible(visible)

    def _on_dot_clicked(self, index: int):
        """处理圆点点击"""
        self.color_clicked.emit(index)

    def _on_dot_delete_requested(self, index: int):
        """处理圆点删除请求"""
        self.delete_color(index)

    def delete_color(self, index: int):
        """删除指定索引的颜色

        Args:
            index: 要删除的颜色索引
        """
        if 0 <= index < len(self._colors):
            self._colors.pop(index)
            self._rebuild_dots()
            self.color_deleted.emit(self._colors.copy())

    def paintEvent(self, event):
        """绘制插入指示器"""
        super().paintEvent(event)

        if self._insert_indicator_pos >= 0 and self._dots:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 计算指示线位置
            if self._insert_indicator_pos < len(self._dots):
                target_widget = self._dots[self._insert_indicator_pos]
                x = target_widget.geometry().left() - 4
            else:
                target_widget = self._dots[-1]
                x = target_widget.geometry().right() + 4

            x = max(10, min(x, self.width() - 10))

            # 定义颜色和尺寸
            indicator_color = QColor(0, 120, 215) if not isDarkTheme() else QColor(0, 150, 255)
            dot_radius = 4
            line_width = 2
            y_center = self.height() // 2

            # 绘制发光效果（外圈）
            glow_color = QColor(indicator_color)
            glow_color.setAlpha(60)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(x, y_center), dot_radius + 3, dot_radius + 3)

            # 绘制中心圆点
            painter.setBrush(QBrush(indicator_color))
            painter.drawEllipse(QPoint(x, y_center), dot_radius, dot_radius)

            # 绘制上下延伸的细线
            painter.setPen(QPen(indicator_color, line_width))
            line_length = (self.height() - 20) // 2 - dot_radius - 2
            if line_length > 0:
                painter.drawLine(x, y_center - dot_radius - 2, x, y_center - dot_radius - 2 - line_length)
                painter.drawLine(x, y_center + dot_radius + 2, x, y_center + dot_radius + 2 + line_length)

    def dragEnterEvent(self, event):
        """接受拖拽进入"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self._insert_indicator_pos = -1
            self.update()

    def dragMoveEvent(self, event):
        """处理拖拽移动，更新插入指示器位置"""
        if not event.mimeData().hasText():
            return

        event.acceptProposedAction()

        # 计算插入位置
        drop_pos = event.position().toPoint()
        target_index = self._calculate_insert_index(drop_pos)

        # 更新指示器位置
        if target_index != self._insert_indicator_pos:
            self._insert_indicator_pos = target_index
            self.update()

    def dragLeaveEvent(self, event):
        """拖拽离开，隐藏指示器"""
        self._insert_indicator_pos = -1
        self.update()

    def dropEvent(self, event):
        """处理放置，完成排序"""
        event.acceptProposedAction()

        # 隐藏指示器
        self._insert_indicator_pos = -1
        self.update()

        # 获取拖拽的源索引
        mime_data = event.mimeData()
        if not mime_data.hasText():
            return

        try:
            source_index = int(mime_data.text())
        except ValueError:
            return

        # 计算放置的目标位置
        drop_pos = event.position().toPoint()
        target_index = self._calculate_insert_index(drop_pos)

        # 执行排序
        if target_index != source_index and 0 <= target_index <= len(self._colors):
            # 移动颜色
            color = self._colors.pop(source_index)

            # 调整目标索引（如果源在目标之前，pop后索引会变化）
            if source_index < target_index:
                target_index -= 1

            self._colors.insert(target_index, color)

            # 重建圆点
            self._rebuild_dots()
            # 发射信号
            self.order_changed.emit(self._colors.copy())

    def _calculate_insert_index(self, pos: QPoint) -> int:
        """计算插入位置索引

        Args:
            pos: 放置位置（相对于 ColorDotBar 的局部坐标）

        Returns:
            int: 插入位置索引（0 到 len(self._dots)）
        """
        if not self._dots:
            return 0

        # 遍历所有圆点，找到最近的插入位置
        for i, dot in enumerate(self._dots):
            dot_rect = dot.geometry()
            dot_center = dot_rect.center().x()

            # 如果位置在当前圆点的左半部分，插入到当前位置
            if pos.x() < dot_center:
                return i

        # 如果位置在所有圆点右侧，插入到最后
        return len(self._dots)


# ============================================================================
# 预览场景基类
# ============================================================================

class BasePreviewScene(QWidget):
    """预览场景基类 - 所有预览场景必须继承此类"""

    def __init__(self, scene_config: dict, parent=None):
        """初始化基类

        Args:
            scene_config: 场景配置字典
            parent: 父控件
        """
        self._config = scene_config
        self._colors: List[str] = []
        self._scene_id = scene_config.get("id", "unknown")
        self._scene_type = scene_config.get("type", "unknown")
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_colors(self, colors: List[str]):
        """设置配色 - 子类必须重写此方法

        Args:
            colors: 颜色值列表（HEX格式）
        """
        if colors:
            self._colors = colors.copy()
            while len(self._colors) < 5:
                self._colors.extend(colors)
            self._colors = self._colors[:5]
        self.update()

    def get_scene_id(self) -> str:
        """获取场景ID"""
        return self._scene_id

    def get_scene_type(self) -> str:
        """获取场景类型"""
        return self._scene_type

    def get_scene_config(self) -> dict:
        """获取场景配置"""
        return self._config.copy()

    @classmethod
    def from_config(cls, config: dict, parent=None):
        """从配置创建实例 - 工厂方法

        Args:
            config: 场景配置字典
            parent: 父控件

        Returns:
            BasePreviewScene: 场景实例
        """
        return cls(config, parent)


# ============================================================================
# 预览场景工厂
# ============================================================================

class PreviewSceneFactory:
    """预览场景工厂 - 根据配置动态创建场景实例"""

    _registry: dict = {}

    @classmethod
    def register(cls, scene_type: str, scene_class: type):
        """注册场景类型

        Args:
            scene_type: 场景类型标识
            scene_class: 场景类（必须继承 BasePreviewScene）
        """
        if not issubclass(scene_class, BasePreviewScene):
            raise ValueError(f"场景类必须继承 BasePreviewScene: {scene_class}")
        cls._registry[scene_type] = scene_class
        print(f"已注册场景类型: {scene_type} -> {scene_class.__name__}")

    @classmethod
    def create(cls, scene_config: dict, parent=None) -> BasePreviewScene:
        """根据配置创建场景实例

        Args:
            scene_config: 场景配置字典
            parent: 父控件

        Returns:
            BasePreviewScene: 场景实例

        Raises:
            ValueError: 如果场景类型未注册
        """
        scene_type = scene_config.get("type", "unknown")
        scene_class = cls._registry.get(scene_type)

        if scene_class is None:
            raise ValueError(f"未知的场景类型: {scene_type}，请先注册")

        return scene_class.from_config(scene_config, parent)

    @classmethod
    def is_registered(cls, scene_type: str) -> bool:
        """检查场景类型是否已注册

        Args:
            scene_type: 场景类型标识

        Returns:
            bool: 是否已注册
        """
        return scene_type in cls._registry

    @classmethod
    def get_registered_types(cls) -> List[str]:
        """获取所有已注册的场景类型

        Returns:
            List[str]: 场景类型列表
        """
        return list(cls._registry.keys())


# ============================================================================
# SVG预览组件（增强版）
# ============================================================================

class SVGPreviewWidget(BasePreviewScene):
    """SVG 预览组件 - 加载和显示 SVG 文件，支持智能配色应用

    增强功能：
    - 支持从 scenes_data 加载内置SVG
    - 支持模板模式
    - 支持右键删除用户模板
    """

    # 信号：删除模板请求
    delete_requested = Signal(str)

    def __init__(self, scene_config: dict = None, parent=None):
        """初始化SVG预览组件

        Args:
            scene_config: 场景配置字典（可选）
            parent: 父控件
        """
        # 如果没有传入配置，使用默认配置
        if scene_config is None:
            scene_config = {"id": "svg", "type": "svg", "name": "SVG预览"}

        super().__init__(scene_config, parent)

        self._svg_renderer: Optional[QSvgRenderer] = None
        self._svg_content: str = ""
        self._original_svg_content: str = ""
        self._color_mapper: Optional[Any] = None  # SVGColorMapper 实例
        self._template_mode: bool = False  # 模板模式标志

        # 模板信息
        self._is_builtin: bool = False  # 是否为内置模板
        self._template_path: Optional[str] = None  # 模板路径

        # 设置无边框样式
        self.setStyleSheet("border: none; background: transparent;")

    def set_template_info(self, is_builtin: bool, path: str = None):
        """设置模板信息

        Args:
            is_builtin: 是否为内置模板
            path: 模板路径
        """
        self._is_builtin = is_builtin
        self._template_path = path

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        # 创建菜单（title="", parent=self）
        menu = RoundMenu("", self)

        # 统一显示"删除模板"
        delete_action = Action(FluentIcon.DELETE, "删除模板")
        delete_action.triggered.connect(self._on_delete_template)
        menu.addAction(delete_action)

        # 显示菜单
        menu.exec(event.globalPos())

        # 接受事件
        event.accept()

    def _on_delete_template(self):
        """删除模板"""
        if self._is_builtin:
            # 内置模板，显示提示
            InfoBar.warning(
                title="无法删除",
                content="内置场景，不可删除",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
        elif self._template_path:
            # 用户模板，发射删除信号
            self.delete_requested.emit(self._template_path)

    def load_svg(self, file_path: str) -> bool:
        """加载 SVG 文件

        Args:
            file_path: SVG 文件路径

        Returns:
            bool: 是否加载成功
        """
        try:
            # 使用新的 SVGColorMapper
            from core import SVGColorMapper
            self._color_mapper = SVGColorMapper()

            if not self._color_mapper.load_svg(file_path):
                return False

            self._original_svg_content = self._color_mapper.get_original_content()

            # 应用当前配色
            self._apply_colors_to_svg()

            # 创建渲染器
            self._svg_renderer = QSvgRenderer()
            self._svg_renderer.load(self._svg_content.encode('utf-8'))

            self.update()
            return True
        except Exception as e:
            print(f"加载 SVG 文件失败: {e}")
            return False

    def load_svg_from_string(self, content: str) -> bool:
        """从字符串加载 SVG

        Args:
            content: SVG 内容字符串

        Returns:
            bool: 是否加载成功
        """
        try:
            from core import SVGColorMapper
            self._color_mapper = SVGColorMapper()

            if not self._color_mapper.load_svg_from_string(content):
                return False

            self._original_svg_content = content

            # 应用当前配色
            self._apply_colors_to_svg()

            # 创建渲染器
            self._svg_renderer = QSvgRenderer()
            self._svg_renderer.load(self._svg_content.encode('utf-8'))

            self.update()
            return True
        except Exception as e:
            print(f"加载 SVG 字符串失败: {e}")
            return False

    def load_svg_from_resource(self, scene_type: str) -> bool:
        """从 scenes_data 加载内置SVG

        Args:
            scene_type: 场景类型ID（如 'ui', 'web'）

        Returns:
            bool: 是否加载成功
        """
        try:
            from core import get_scene_type_manager

            manager = get_scene_type_manager()
            svg_path = manager.get_builtin_svg_path(scene_type)

            if svg_path is None:
                print(f"未找到内置SVG: {scene_type}")
                return False

            self._template_mode = True
            return self.load_svg(svg_path)

        except Exception as e:
            print(f"加载内置SVG失败: {e}")
            return False

    def set_colors(self, colors: List[str]):
        """设置配色并应用到 SVG

        Args:
            colors: 颜色值列表（HEX格式）
        """
        if colors:
            self._colors = colors.copy()
            while len(self._colors) < 5:
                self._colors.extend(colors)
            self._colors = self._colors[:5]
        else:
            self._colors = []

        # 如果有已加载的 SVG，重新应用配色
        if self._original_svg_content:
            self._apply_colors_to_svg()
            # 确保渲染器已创建并加载新内容
            if not self._svg_renderer:
                self._svg_renderer = QSvgRenderer()
            self._svg_renderer.load(self._svg_content.encode('utf-8'))
            self.update()

    def _apply_colors_to_svg(self):
        """将配色应用到 SVG 内容（使用智能映射）"""
        if not self._original_svg_content or not self._colors:
            return

        # 使用智能映射
        if self._color_mapper:
            self._svg_content = self._color_mapper.apply_intelligent_mapping(self._colors)
        else:
            self._svg_content = self._original_svg_content

    def paintEvent(self, event):
        """绘制 SVG"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 如果没有配色，显示提示信息
        if not self._colors:
            self._draw_empty_hint(painter)
            return

        # 检查SVG是否有固定颜色的背景元素
        has_fixed_background = self._has_fixed_background_element()

        # 绘制背景（只有没有固定背景时才使用配色）
        if has_fixed_background:
            # SVG有固定背景，使用白色作为容器背景
            bg_color = QColor("#ffffff")
        else:
            # 使用配色的第一个颜色作为背景
            bg_color = QColor(self._colors[0])
        painter.fillRect(self.rect(), bg_color)

        # 如果有 SVG 渲染器，绘制 SVG
        if self._svg_renderer and self._svg_renderer.isValid():
            # 计算缩放比例，保持宽高比
            view_box = self._svg_renderer.viewBox()
            if view_box.isValid():
                svg_width = view_box.width()
                svg_height = view_box.height()
            else:
                svg_width = self._svg_renderer.defaultSize().width()
                svg_height = self._svg_renderer.defaultSize().height()

            if svg_width > 0 and svg_height > 0:
                # 计算缩放比例，保持宽高比完整显示
                widget_rect = self.rect()
                scale_x = widget_rect.width() / svg_width
                scale_y = widget_rect.height() / svg_height
                scale = min(scale_x, scale_y)  # 使用min保持完整显示

                # 计算居中位置
                new_width = svg_width * scale
                new_height = svg_height * scale
                x = (widget_rect.width() - new_width) / 2
                y = (widget_rect.height() - new_height) / 2

                target_rect = QRect(int(x), int(y), int(new_width), int(new_height))
                self._svg_renderer.render(painter, target_rect)

    def get_svg_content(self) -> str:
        """获取当前 SVG 内容（用于导出）

        如果 SVG 没有背景元素，会自动添加背景矩形
        """
        if not self._svg_content or not self._colors:
            return self._svg_content

        # 检查是否需要添加背景
        if self._color_mapper and not self._color_mapper._has_background_element():
            # 需要添加背景矩形
            return self._add_background_to_svg(self._svg_content, self._colors[0])

        return self._svg_content

    def _add_background_to_svg(self, svg_content: str, bg_color: str) -> str:
        """为 SVG 添加背景矩形

        Args:
            svg_content: 原始 SVG 内容
            bg_color: 背景颜色

        Returns:
            添加背景后的 SVG 内容
        """
        try:
            import xml.etree.ElementTree as ET
            import re

            root = ET.fromstring(svg_content)

            # 获取 SVG 命名空间
            svg_ns = 'http://www.w3.org/2000/svg'

            # 检查根元素是否有命名空间
            has_namespace = root.tag.startswith('{')

            # 获取画布大小
            viewbox = root.get('viewBox', '')
            width = root.get('width', '0')
            height = root.get('height', '0')

            # 解析 viewBox 或 width/height
            if viewbox:
                parts = viewbox.split()
                if len(parts) >= 4:
                    x, y, w, h = parts[0], parts[1], parts[2], parts[3]
                else:
                    return svg_content
            elif width and height:
                # 移除单位
                w = re.sub(r'[^\d.]', '', width)
                h = re.sub(r'[^\d.]', '', height)
                x, y = '0', '0'
            else:
                return svg_content

            # 创建背景矩形元素（使用正确的命名空间）
            if has_namespace:
                bg_rect = ET.Element(f'{{{svg_ns}}}rect')
            else:
                bg_rect = ET.Element('rect')

            bg_rect.set('x', x)
            bg_rect.set('y', y)
            bg_rect.set('width', w)
            bg_rect.set('height', h)
            bg_rect.set('fill', bg_color)

            # 将背景矩形插入到第一个位置
            root.insert(0, bg_rect)

            # 转换回字符串
            return ET.tostring(root, encoding='unicode')

        except Exception as e:
            print(f"添加背景失败: {e}")
            return svg_content

    def has_svg(self) -> bool:
        """是否已加载 SVG"""
        return self._svg_renderer is not None and self._svg_renderer.isValid()

    def is_template_mode(self) -> bool:
        """是否处于模板模式"""
        return self._template_mode

    def _has_fixed_background_element(self) -> bool:
        """检查SVG是否有固定颜色的背景元素

        通过检查SVG内容中是否有 data-fixed-color="original" 的背景元素

        Returns:
            bool: 是否有固定背景元素
        """
        if not self._svg_content:
            return False

        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(self._svg_content)

            # 查找所有带有 data-fixed-color="original" 的rect元素
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'rect':
                    fixed_color = elem.get('data-fixed-color')
                    if fixed_color == 'original':
                        return True

            return False
        except Exception:
            return False

    def _draw_empty_hint(self, painter: QPainter):
        """绘制空配色提示"""
        # 绘制背景
        bg_color = QColor(240, 240, 240) if not isDarkTheme() else QColor(50, 50, 50)
        painter.fillRect(self.rect(), bg_color)

        # 绘制提示文字
        text_color = get_text_color()
        painter.setPen(QPen(text_color))
        font = QFont("Arial", 11)
        painter.setFont(font)

        hint_text = "请从配色管理面板导入配色"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, hint_text)


# ============================================================================
# 布局系统
# ============================================================================

class BaseLayout(QWidget):
    """布局基类 - 所有布局必须继承此类"""

    current_index_changed = Signal(int)
    template_deleted = Signal(str)  # 模板删除信号，参数为模板路径

    def __init__(self, templates: list, config: dict, parent=None):
        super().__init__(parent)
        self._templates: List[str] = templates if templates else []
        self._config: Dict[str, Any] = config if config else {}
        self._svg_widgets: List[Any] = []
        self._colors: List[str] = []

        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_colors(self, colors: list):
        self._colors = colors.copy() if colors else []
        for svg_widget in self._svg_widgets:
            if svg_widget and hasattr(svg_widget, 'set_colors'):
                svg_widget.set_colors(self._colors)

    def get_svg_widgets(self) -> list:
        return self._svg_widgets

    def clear(self):
        for svg_widget in self._svg_widgets:
            if svg_widget:
                svg_widget.deleteLater()
        self._svg_widgets.clear()

    def load_templates(self):
        raise NotImplementedError("子类必须重写 load_templates 方法")

    def _create_svg_widget(self, template_path: str = None, is_builtin: bool = False) -> Any:
        """创建SVG预览组件

        Args:
            template_path: 模板文件路径
            is_builtin: 是否为内置模板

        Returns:
            SVGPreviewWidget: SVG预览组件实例
        """
        svg_widget = SVGPreviewWidget(parent=self)

        # 设置模板信息
        svg_widget.set_template_info(is_builtin, template_path)

        # 连接删除信号
        svg_widget.delete_requested.connect(self._on_template_deleted)

        if template_path:
            svg_widget.load_svg(template_path)

        if self._colors:
            svg_widget.set_colors(self._colors)

        return svg_widget

    def _on_template_deleted(self, template_path: str):
        """处理模板删除请求

        Args:
            template_path: 被删除的模板路径
        """
        # 转发删除信号到父组件
        self.template_deleted.emit(template_path)


class SingleLayout(BaseLayout):
    """单图布局 - 一次显示一个SVG，支持左右切换"""

    def __init__(self, templates: list, config: dict, parent=None):
        super().__init__(templates, config, parent)
        self._current_index: int = 0
        self.setup_ui()
        self.load_templates()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        self._svg_container = QWidget()
        self._svg_container.setStyleSheet("border: none; background: transparent;")
        self._svg_layout = QVBoxLayout(self._svg_container)
        self._svg_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._svg_container, stretch=1)

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(10, 5, 10, 5)
        nav_layout.setSpacing(20)

        self._prev_button = QPushButton("< 上一个")
        self._prev_button.setFixedSize(100, 32)
        self._prev_button.clicked.connect(self.prev_svg)
        nav_layout.addWidget(self._prev_button)

        self._index_label = QLabel("0 / 0")
        self._index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._index_label.setFixedHeight(32)
        nav_layout.addWidget(self._index_label, stretch=1)

        self._next_button = QPushButton("下一个 >")
        self._next_button.setFixedSize(100, 32)
        self._next_button.clicked.connect(self.next_svg)
        nav_layout.addWidget(self._next_button)

        main_layout.addWidget(nav_widget)
        self.update_navigation()

    def load_templates(self):
        self.clear()

        for template_info in self._templates:
            if isinstance(template_info, dict):
                path = template_info.get("path")
                is_builtin = template_info.get("is_builtin", False)
            else:
                path = template_info
                is_builtin = False

            svg_widget = self._create_svg_widget(path, is_builtin)
            self._svg_widgets.append(svg_widget)

        self._show_current_svg()
        self.update_navigation()

    def _show_current_svg(self):
        while self._svg_layout.count():
            item = self._svg_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if 0 <= self._current_index < len(self._svg_widgets):
            svg_widget = self._svg_widgets[self._current_index]
            self._svg_layout.addWidget(svg_widget)

    def prev_svg(self):
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current_svg()
            self.update_navigation()
            self.current_index_changed.emit(self._current_index)

    def next_svg(self):
        if self._current_index < len(self._svg_widgets) - 1:
            self._current_index += 1
            self._show_current_svg()
            self.update_navigation()
            self.current_index_changed.emit(self._current_index)

    def update_navigation(self):
        total = len(self._svg_widgets)
        current = self._current_index + 1 if total > 0 else 0

        self._index_label.setText(f"{current} / {total}")

        self._prev_button.setEnabled(self._current_index > 0)
        self._next_button.setEnabled(self._current_index < total - 1)

        self._update_button_styles()

    def _update_button_styles(self):
        text_color = get_text_color()
        border_color = get_border_color()

        style = f"""
            QPushButton {{
                background-color: transparent;
                color: rgba({text_color.red()}, {text_color.green()}, {text_color.blue()}, 200);
                border: 1px solid rgba({border_color.red()}, {border_color.green()}, {border_color.blue()}, 150);
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: rgba({text_color.red()}, {text_color.green()}, {text_color.blue()}, 30);
            }}
            QPushButton:disabled {{
                color: rgba({text_color.red()}, {text_color.green()}, {text_color.blue()}, 80);
                border-color: rgba({border_color.red()}, {border_color.green()}, {border_color.blue()}, 50);
            }}
        """
        self._prev_button.setStyleSheet(style)
        self._next_button.setStyleSheet(style)

        label_style = f"""
            QLabel {{
                color: rgba({text_color.red()}, {text_color.green()}, {text_color.blue()}, 200);
                font-size: 13px;
            }}
        """
        self._index_label.setStyleSheet(label_style)

    def set_current_index(self, index: int):
        if 0 <= index < len(self._svg_widgets):
            self._current_index = index
            self._show_current_svg()
            self.update_navigation()
            self.current_index_changed.emit(self._current_index)

    def get_current_index(self) -> int:
        return self._current_index


class ScrollVLayout(BaseLayout):
    """垂直滚动布局 - 多个SVG垂直排列，可滚动"""

    def __init__(self, templates: list, config: dict, parent=None):
        super().__init__(templates, config, parent)
        self.setup_ui()
        self.load_templates()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # 设置滚动条角落为透明（防止出现灰色方块）
        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        self._scroll_area.setCornerWidget(corner_widget)

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(10, 10, 10, 10)
        self._content_layout.setSpacing(15)
        self._content_layout.addStretch()

        self._scroll_area.setWidget(self._content_widget)
        main_layout.addWidget(self._scroll_area)

    def load_templates(self):
        self.clear()

        viewport_height = self._scroll_area.viewport().height()

        for template_info in self._templates:
            if isinstance(template_info, dict):
                path = template_info.get("path")
                is_builtin = template_info.get("is_builtin", False)
            else:
                path = template_info
                is_builtin = False

            svg_widget = self._create_svg_widget(path, is_builtin)
            svg_widget.setMinimumHeight(viewport_height)
            self._svg_widgets.append(svg_widget)
            self._content_layout.insertWidget(self._content_layout.count() - 1, svg_widget)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_scroll_area'):
            viewport_height = self._scroll_area.viewport().height()
            for svg_widget in self._svg_widgets:
                svg_widget.setMinimumHeight(viewport_height)
                svg_widget.update()


class ScrollHLayout(BaseLayout):
    """水平滚动布局 - 多个SVG水平排列，可滚动"""

    def __init__(self, templates: list, config: dict, parent=None):
        super().__init__(templates, config, parent)
        self.setup_ui()
        self.load_templates()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # 设置滚动条角落为透明（防止出现灰色方块）
        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        self._scroll_area.setCornerWidget(corner_widget)

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        self._content_layout = QHBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(10, 10, 10, 10)
        self._content_layout.setSpacing(15)
        self._content_layout.addStretch()

        self._scroll_area.setWidget(self._content_widget)
        main_layout.addWidget(self._scroll_area)

    def load_templates(self):
        self.clear()

        for template_info in self._templates:
            if isinstance(template_info, dict):
                path = template_info.get("path")
                is_builtin = template_info.get("is_builtin", False)
            else:
                path = template_info
                is_builtin = False

            svg_widget = self._create_svg_widget(path, is_builtin)
            svg_widget.setMinimumWidth(200)
            self._svg_widgets.append(svg_widget)
            self._content_layout.insertWidget(self._content_layout.count() - 1, svg_widget)


class GridLayout(BaseLayout):
    """网格布局 - 根据columns参数决定列数"""

    def __init__(self, templates: list, config: dict, parent=None):
        super().__init__(templates, config, parent)
        self._columns: int = config.get('columns', 2)
        self.setup_ui()
        self.load_templates()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # 设置滚动条角落为透明（防止出现灰色方块）
        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        self._scroll_area.setCornerWidget(corner_widget)

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        self._content_layout = QGridLayout(self._content_widget)
        self._content_layout.setContentsMargins(10, 10, 10, 10)
        self._content_layout.setSpacing(15)

        self._scroll_area.setWidget(self._content_widget)
        main_layout.addWidget(self._scroll_area)

    def load_templates(self):
        self.clear()

        for index, template_info in enumerate(self._templates):
            if isinstance(template_info, dict):
                path = template_info.get("path")
                is_builtin = template_info.get("is_builtin", False)
            else:
                path = template_info
                is_builtin = False

            svg_widget = self._create_svg_widget(path, is_builtin)
            svg_widget.setMinimumSize(150, 150)
            self._svg_widgets.append(svg_widget)

            row = index // self._columns
            col = index % self._columns
            self._content_layout.addWidget(svg_widget, row, col)

        for col in range(self._columns):
            self._content_layout.setColumnStretch(col, 1)


class MixedLayout(BaseLayout):
    """混合布局 - 左侧2x2网格 + 右侧大图"""

    def __init__(self, templates: list, config: dict, parent=None):
        super().__init__(templates, config, parent)
        self.setup_ui()
        self.load_templates()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        self._left_widget = QWidget()
        self._left_widget.setStyleSheet("border: none; background: transparent;")
        self._left_layout = QGridLayout(self._left_widget)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(10)

        self._right_widget = QWidget()
        self._right_widget.setStyleSheet("border: none; background: transparent;")
        self._right_layout = QVBoxLayout(self._right_widget)
        self._right_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self._left_widget, stretch=1)
        main_layout.addWidget(self._right_widget, stretch=1)

    def load_templates(self):
        self.clear()

        def get_template_info(template_info):
            if isinstance(template_info, dict):
                return template_info.get("path"), template_info.get("is_builtin", False)
            return template_info, False

        grid_templates = self._templates[:4]
        for index, template_info in enumerate(grid_templates):
            path, is_builtin = get_template_info(template_info)
            svg_widget = self._create_svg_widget(path, is_builtin)
            self._svg_widgets.append(svg_widget)

            row = index // 2
            col = index % 2
            self._left_layout.addWidget(svg_widget, row, col)

        self._left_layout.setColumnStretch(0, 1)
        self._left_layout.setColumnStretch(1, 1)
        self._left_layout.setRowStretch(0, 1)
        self._left_layout.setRowStretch(1, 1)

        if len(self._templates) > 4:
            right_template_info = self._templates[4]
        elif self._templates:
            right_template_info = self._templates[0]
        else:
            right_template_info = None

        if right_template_info:
            path, is_builtin = get_template_info(right_template_info)
            svg_widget = self._create_svg_widget(path, is_builtin)
            self._svg_widgets.append(svg_widget)
            self._right_layout.addWidget(svg_widget)


class LayoutFactory:
    """布局工厂类 - 根据类型创建布局实例"""

    _layout_registry: Dict[str, type] = {
        'single': SingleLayout,
        'scroll_v': ScrollVLayout,
        'scroll_h': ScrollHLayout,
        'grid_2x2': GridLayout,
        'grid_3x2': GridLayout,
        'mixed': MixedLayout,
    }

    @classmethod
    def create(cls, layout_type: str, templates: list, config: dict, parent=None) -> Optional[BaseLayout]:
        layout_class = cls._layout_registry.get(layout_type)

        if layout_class is None:
            print(f"未知的布局类型: {layout_type}")
            return None

        if layout_type == 'grid_2x2':
            config = config.copy() if config else {}
            config['columns'] = 2
        elif layout_type == 'grid_3x2':
            config = config.copy() if config else {}
            config['columns'] = 3

        return layout_class(templates, config, parent)

    @classmethod
    def register(cls, layout_type: str, layout_class: type):
        if not issubclass(layout_class, BaseLayout):
            raise ValueError(f"布局类必须继承 BaseLayout: {layout_class}")
        cls._layout_registry[layout_type] = layout_class
        print(f"已注册布局类型: {layout_type} -> {layout_class.__name__}")

    @classmethod
    def get_available_types(cls) -> List[str]:
        return list(cls._layout_registry.keys())

    @classmethod
    def is_valid_type(cls, layout_type: str) -> bool:
        return layout_type in cls._layout_registry


# ============================================================================
# 预览场景选择器
# ============================================================================

class PreviewSceneSelector(ComboBox):
    """预览场景选择器 - 从 scene_types.json 加载场景列表"""

    scene_changed = Signal(str)  # 场景变化信号

    def __init__(self, parent=None):
        """初始化场景选择器

        Args:
            parent: 父控件
        """
        self._scene_types: List[dict] = []
        super().__init__(parent)
        self._load_scene_types()
        self._setup_items()
        self.currentTextChanged.connect(self._on_selection_changed)

    def _load_scene_types(self):
        """从 SceneTypeManager 加载场景类型"""
        try:
            from core import get_scene_type_manager
            manager = get_scene_type_manager()
            self._scene_types = manager.get_all_scene_types()
        except Exception as e:
            print(f"加载场景类型失败: {e}")
            # 使用默认场景列表
            self._scene_types = [
                {"id": "mobile_ui", "name": "手机UI"},
                {"id": "web", "name": "网页"},
                {"id": "custom", "name": "自定义"},
            ]

    def _setup_items(self):
        """设置选项"""
        self.clear()
        for scene_type in self._scene_types:
            scene_id = scene_type.get("id", "")
            scene_name = scene_type.get("name", scene_id)
            self.addItem(scene_name)
            self.setItemData(self.count() - 1, scene_id)

    def _on_selection_changed(self, text: str):
        """处理选择变化"""
        index = self.currentIndex()
        key = self.itemData(index)
        if key:
            self.scene_changed.emit(key)

    def get_current_scene(self) -> str:
        """获取当前场景ID"""
        return self.itemData(self.currentIndex()) or "mobile_ui"

    def reload_scenes(self):
        """重新加载场景列表"""
        self._load_scene_types()
        self._setup_items()

    def get_scene_type_config(self, scene_id: str) -> Optional[dict]:
        """获取场景类型配置

        Args:
            scene_id: 场景ID

        Returns:
            Optional[dict]: 场景配置，如果不存在则返回None
        """
        for scene_type in self._scene_types:
            if scene_type.get("id") == scene_id:
                return scene_type.copy()
        return None


# ============================================================================
# 预览面板
# ============================================================================

class MixedPreviewPanel(QWidget):
    """预览面板 - 使用布局工厂展示SVG预览"""

    def __init__(self, parent=None):
        """初始化混合预览面板

        Args:
            parent: 父控件
        """
        self._colors: List[str] = []
        self._current_scene: str = "mobile_ui"
        self._current_layout: Optional[BaseLayout] = None
        self._svg_preview: Optional[SVGPreviewWidget] = None  # 用于 custom 场景
        self._custom_svg_path: Optional[str] = None  # 保存 custom 场景导入的 SVG 路径
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """创建UI"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("border: none; background: transparent;")

    def set_scene(self, scene: str):
        """切换预览场景

        Args:
            scene: 场景ID
        """
        self._current_scene = scene

        # 清除现有布局
        if self._current_layout:
            self._current_layout.deleteLater()
            self._current_layout = None
        
        # 清除 custom 场景的 SVG 预览
        if self._svg_preview is not None:
            self._svg_preview.deleteLater()
            self._svg_preview = None

        # 使用 SceneTypeManager 和 LayoutFactory 创建布局
        try:
            from core import get_scene_type_manager

            manager = get_scene_type_manager()
            scene_config = manager.get_scene_type_by_id(scene)

            if scene_config is None:
                print(f"未找到场景配置: {scene}")
                return

            # 获取模板列表
            templates = manager.get_all_templates(scene)

            # 获取布局配置
            layout_config = manager.get_layout_config(scene)
            layout_type = layout_config.get("layout", {}).get("type", "scroll_v")

            # custom 场景固定使用 single 布局
            if scene == "custom":
                layout_type = "single"

            # 如果没有模板，创建一个空的SVG预览
            if not templates:
                self._create_empty_preview()
                # 如果之前导入过 SVG，重新加载
                if self._custom_svg_path and self._svg_preview:
                    self._svg_preview.load_svg(self._custom_svg_path)
                return

            # 创建布局
            self._current_layout = LayoutFactory.create(
                layout_type, templates, layout_config.get("layout", {}), self
            )

            if self._current_layout:
                self._main_layout.addWidget(self._current_layout)
                self._current_layout.set_colors(self._colors)
                # 连接删除信号
                self._current_layout.template_deleted.connect(self._on_template_deleted)
                # 延迟更新布局大小，确保视口高度正确
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self._update_layout_sizes)

        except Exception as e:
            print(f"创建布局失败: {e}")
            self._create_empty_preview()

    def _on_template_deleted(self, template_path: str):
        """处理模板删除

        Args:
            template_path: 被删除的模板路径
        """
        # 从 ConfigManager 中删除
        from core import get_config_manager
        config_manager = get_config_manager()
        config_manager.remove_scene_template(self._current_scene, template_path)
        config_manager.save()

        # 重新加载当前场景
        self.set_scene(self._current_scene)

    def _create_empty_preview(self):
        """创建空的SVG预览（用于 custom 场景）"""
        self._svg_preview = SVGPreviewWidget(parent=self)
        self._svg_preview.set_colors(self._colors)
        self._main_layout.addWidget(self._svg_preview)
        self._current_layout = None

    def _update_layout_sizes(self):
        """更新布局中所有SVG控件的大小"""
        if self._current_layout and hasattr(self._current_layout, '_scroll_area'):
            viewport_height = self._current_layout._scroll_area.viewport().height()
            for svg_widget in self._current_layout.get_svg_widgets():
                svg_widget.setMinimumHeight(viewport_height)
                svg_widget.update()

    def set_colors(self, colors: List[str]):
        """设置配色

        Args:
            colors: 颜色值列表（HEX格式）
        """
        self._colors = colors if colors else []
        if self._current_layout:
            self._current_layout.set_colors(self._colors)
        # 更新 custom 场景的 SVG 预览
        if self._svg_preview is not None:
            self._svg_preview.set_colors(self._colors)

    def get_svg_preview(self) -> Optional[SVGPreviewWidget]:
        """获取 SVG 预览组件（用于 custom 场景）

        Returns:
            Optional[SVGPreviewWidget]: SVG预览组件，如果不存在则返回None
        """
        # 优先返回 custom 场景的 SVG 预览
        if self._svg_preview is not None:
            return self._svg_preview
        
        # 否则从当前布局中获取第一个
        if self._current_layout:
            widgets = self._current_layout.get_svg_widgets()
            if widgets:
                return widgets[0]
        return None

    def set_custom_svg_path(self, path: str):
        """设置 custom 场景的 SVG 路径

        Args:
            path: SVG 文件路径
        """
        self._custom_svg_path = path


# ============================================================================
# 预览工具栏
# ============================================================================

class PreviewToolbar(QWidget):
    """预览工具栏 - 包含圆点栏、场景选择、导入导出按钮"""

    scene_changed = Signal(str)              # 场景变化
    import_svg_requested = Signal()          # 导入SVG请求（custom场景）
    export_svg_requested = Signal()          # 导出SVG请求（custom场景）
    import_config_requested = Signal()       # 导入配置请求（所有场景）
    export_config_requested = Signal()       # 导出配置请求（所有场景）

    def __init__(self, parent=None):
        """初始化预览工具栏

        Args:
            parent: 父控件
        """
        self._current_scene = "mobile_ui"
        super().__init__(parent)
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        """创建UI"""
        # 使用垂直布局，两行
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # 第一行：标题 + 导入导出按钮 + 场景选择器
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)

        # 标题（使用 SubtitleLabel 保持一致性）
        self._title_label = SubtitleLabel("配色预览")
        top_layout.addWidget(self._title_label)

        # 添加说明标签
        self._desc_label = QLabel("还在持续完善中")
        self._desc_label.setStyleSheet("font-size: 12px; color: gray;")
        top_layout.addWidget(self._desc_label)

        top_layout.addStretch()  # 弹性空间，使右侧内容右对齐

        # 导入导出按钮容器（对所有场景可见）
        self._buttons_container = QWidget()
        buttons_layout = QHBoxLayout(self._buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        # 导入按钮
        self._import_button = PushButton(FluentIcon.DOWN, "导入")
        self._import_button.setFixedHeight(32)
        self._import_button.clicked.connect(self._on_import_clicked)
        buttons_layout.addWidget(self._import_button)

        # 导出按钮
        self._export_button = PushButton(FluentIcon.UP, "导出")
        self._export_button.setFixedHeight(32)
        self._export_button.clicked.connect(self._on_export_clicked)
        buttons_layout.addWidget(self._export_button)

        top_layout.addWidget(self._buttons_container)

        # 场景选择器
        self._scene_selector = PreviewSceneSelector()
        self._scene_selector.setFixedWidth(100)
        self._scene_selector.scene_changed.connect(self._on_scene_changed)
        top_layout.addWidget(self._scene_selector)

        main_layout.addWidget(top_row)

        # 第二行：颜色圆点栏（居中显示）
        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        # 配色圆点栏
        self._dot_bar = ColorDotBar()
        # 设置圆点栏在布局中居中
        self._dot_bar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        bottom_layout.addWidget(self._dot_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(bottom_row, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setFixedHeight(100)  # 增加高度以容纳两行

        # 初始化时同步按钮显示状态
        current_scene = self._scene_selector.get_current_scene()
        self._on_scene_changed(current_scene)

    def _on_scene_changed(self, scene: str):
        """处理场景变化"""
        self._current_scene = scene
        # 转发信号
        self.scene_changed.emit(scene)

    def _on_import_clicked(self):
        """处理导入按钮点击"""
        if self._current_scene == "custom":
            # Custom场景：可以选择导入SVG或JSON配置
            self.import_svg_requested.emit()
        else:
            # 其他场景：导入JSON配置
            self.import_config_requested.emit()

    def _on_export_clicked(self):
        """处理导出按钮点击"""
        if self._current_scene == "custom":
            # Custom场景：导出SVG
            self.export_svg_requested.emit()
        else:
            # 其他场景：导出JSON配置
            self.export_config_requested.emit()

    def _update_styles(self):
        """更新样式以适配主题"""
        # 工具栏背景透明
        self.setStyleSheet("background: transparent;")

    def set_colors(self, colors: List[str]):
        """设置颜色

        Args:
            colors: 颜色值列表（HEX格式）
        """
        self._dot_bar.set_colors(colors)

    def set_hex_visible(self, visible: bool):
        """设置HEX值显示开关

        Args:
            visible: 是否显示HEX值
        """
        self._dot_bar.set_hex_visible(visible)

    def get_dot_bar(self) -> ColorDotBar:
        """获取圆点栏（用于连接信号）

        Returns:
            ColorDotBar: 颜色圆点工具栏
        """
        return self._dot_bar

    def get_scene_selector(self) -> PreviewSceneSelector:
        """获取场景选择器

        Returns:
            PreviewSceneSelector: 场景选择器
        """
        return self._scene_selector

    def get_current_scene(self) -> str:
        """获取当前场景

        Returns:
            str: 当前场景ID
        """
        return self._scene_selector.get_current_scene()


# ============================================================================
# 注册预览场景
# ============================================================================

def register_preview_scenes():
    """注册所有预览场景类型到工厂"""
    # 只保留 svg 类型
    PreviewSceneFactory.register("svg", SVGPreviewWidget)


# 自动注册场景
register_preview_scenes()
