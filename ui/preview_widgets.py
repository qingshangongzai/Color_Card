# 标准库导入
from typing import List, Optional
import math

# 第三方库导入
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSplitter, QSizePolicy, QFileDialog, QApplication
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QMimeData
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QDrag, QPixmap, QFontMetrics
)
from PySide6.QtSvg import QSvgRenderer
from qfluentwidgets import (
    ToolButton, ComboBox, PushButton, SubtitleLabel,
    FluentIcon, isDarkTheme, qconfig, RoundMenu, Action
)

# 项目模块导入
from ui.theme_colors import get_border_color, get_text_color


class DraggableColorDot(QWidget):
    """可拖拽的颜色圆点组件"""

    clicked = Signal(int)                # 点击信号：索引
    delete_requested = Signal(int)       # 删除请求信号：索引

    def __init__(self, color: str, index: int, parent=None):
        self._color = color
        self._index = index
        self._drag_start_pos = QPoint()
        self._hex_visible = True             # HEX值显示开关
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str):
        self._color = value
        self.update()

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value

    def paintEvent(self, event):
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
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
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
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            # 检查是否是点击（没有发生拖拽）
            if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
                self.clicked.emit(self._index)

    def mouseDoubleClickEvent(self, event):
        self.clicked.emit(self._index)

    def set_hex_visible(self, visible: bool):
        """设置HEX值显示开关"""
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


class ColorDotBar(QWidget):
    """颜色圆点工具栏，支持拖拽排序"""

    order_changed = Signal(list)         # 颜色顺序变化信号：新的颜色列表
    color_clicked = Signal(int)          # 颜色点击信号：索引
    color_deleted = Signal(list)         # 颜色删除信号：新的颜色列表

    def __init__(self, parent=None):
        self._colors: List[str] = []
        self._dots: List[DraggableColorDot] = []
        self._insert_indicator_pos = -1    # 插入指示器位置（-1表示不显示）
        self._hex_visible = True             # HEX值显示开关
        super().__init__(parent)
        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        layout.addStretch()
        self.setFixedHeight(50)

    def set_colors(self, colors: List[str]):
        """设置颜色列表"""
        self._colors = colors.copy()
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

        print(f"拖拽排序: 源索引={source_index}, 目标索引={target_index}, 颜色数={len(self._colors)}")

        # 执行排序
        if target_index != source_index and 0 <= target_index <= len(self._colors):
            # 移动颜色
            color = self._colors.pop(source_index)

            # 调整目标索引（如果源在目标之前，pop后索引会变化）
            if source_index < target_index:
                target_index -= 1

            self._colors.insert(target_index, color)
            print(f"排序完成: 新顺序索引={target_index}")

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

        # 获取布局的边距
        layout = self.layout()
        left_margin = layout.contentsMargins().left()
        spacing = layout.spacing()

        # 计算每个圆点的中心位置
        dot_width = self._dots[0].width()

        # 遍历所有圆点，找到最近的插入位置
        for i, dot in enumerate(self._dots):
            dot_rect = dot.geometry()
            dot_left = dot_rect.left()
            dot_right = dot_rect.right()
            dot_center = dot_rect.center().x()

            # 如果位置在当前圆点的左半部分，插入到当前位置
            if pos.x() < dot_center:
                return i

        # 如果位置在所有圆点右侧，插入到最后
        return len(self._dots)


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


class IllustrationPreview(QWidget):
    """插画风格配色预览 - 绘制植物风格矢量插画"""

    def __init__(self, parent=None):
        self._colors: List[str] = ["#E8E8E8", "#D0D0D0", "#B8B8B8", "#A0A0A0", "#888888"]
        self._seed = 0  # 随机种子，用于生成不同的植物形态
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_colors(self, colors: List[str]):
        """设置配色"""
        if colors:
            self._colors = colors.copy()
            # 如果颜色不足5个，循环使用
            while len(self._colors) < 5:
                self._colors.extend(colors)
            self._colors = self._colors[:5]
        self.update()

    def set_seed(self, seed: int):
        """设置随机种子，改变植物形态"""
        self._seed = seed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 1. 绘制背景
        bg_color = QColor(self._colors[0])
        painter.fillRect(self.rect(), bg_color)

        # 2. 绘制装饰色块（圆形/椭圆形）
        self._draw_decorative_circles(painter, width, height)

        # 3. 绘制植物线条
        self._draw_plant(painter, width, height)

    def _draw_decorative_circles(self, painter: QPainter, width: int, height: int):
        """绘制装饰性圆形色块"""
        import random
        random.seed(self._seed)

        circles = [
            {"x": 0.15, "y": 0.25, "r": 0.12, "color": 1},
            {"x": 0.75, "y": 0.15, "r": 0.15, "color": 2},
            {"x": 0.25, "y": 0.65, "r": 0.10, "color": 3},
            {"x": 0.70, "y": 0.70, "r": 0.13, "color": 1},
            {"x": 0.85, "y": 0.45, "r": 0.08, "color": 2},
        ]

        for circle in circles:
            x = int(circle["x"] * width)
            y = int(circle["y"] * height)
            r = int(circle["r"] * min(width, height))
            color_idx = circle["color"] % len(self._colors)
            color = QColor(self._colors[color_idx])

            # 设置半透明效果
            color.setAlpha(180)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(x, y), r, r)

    def _draw_plant(self, painter: QPainter, width: int, height: int):
        """绘制植物线条"""
        import random
        random.seed(self._seed + 100)

        # 使用深色绘制植物线条
        line_color = QColor(40, 40, 40) if not isDarkTheme() else QColor(220, 220, 220)
        painter.setPen(QPen(line_color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # 绘制主茎
        stem_x = int(width * 0.5)
        stem_bottom = int(height * 0.85)
        stem_top = int(height * 0.25)

        # 绘制弯曲的茎
        path_points = []
        segments = 8
        for i in range(segments + 1):
            t = i / segments
            x = stem_x + int(math.sin(t * 3 + self._seed) * width * 0.08)
            y = stem_bottom - int(t * (stem_bottom - stem_top))
            path_points.append(QPoint(x, y))

        for i in range(len(path_points) - 1):
            painter.drawLine(path_points[i], path_points[i + 1])

        # 绘制叶子
        leaf_positions = [0.3, 0.5, 0.7]
        for pos in leaf_positions:
            idx = int(pos * (len(path_points) - 1))
            if idx < len(path_points):
                self._draw_leaf(painter, path_points[idx], pos)

    def _draw_leaf(self, painter: QPainter, pos: QPoint, t: float):
        """绘制单个叶子"""
        import random
        random.seed(self._seed + int(t * 100))

        leaf_size = 25 + random.randint(-5, 5)
        angle = random.uniform(-0.5, 0.5)

        # 左侧叶子
        left_leaf = QPoint(
            pos.x() - int(leaf_size * math.cos(angle)),
            pos.y() - int(leaf_size * math.sin(angle))
        )

        # 绘制叶子轮廓（简化为曲线）
        painter.drawLine(pos, left_leaf)

        # 右侧叶子
        right_leaf = QPoint(
            pos.x() + int(leaf_size * math.cos(angle)),
            pos.y() - int(leaf_size * math.sin(angle))
        )
        painter.drawLine(pos, right_leaf)


class TypographyPreview(QWidget):
    """排版风格配色预览 - 展示文字排版效果"""

    def __init__(self, parent=None):
        self._colors: List[str] = ["#E8E8E8", "#D0D0D0", "#B8B8B8", "#A0A0A0", "#888888"]
        self._text_content = "All\nBodies\nAre\nGood\nBodies"
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_colors(self, colors: List[str]):
        """设置配色"""
        if colors:
            self._colors = colors.copy()
            while len(self._colors) < 5:
                self._colors.extend(colors)
            self._colors = self._colors[:5]
        self.update()

    def set_text(self, text: str):
        """设置显示文字"""
        self._text_content = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 绘制背景
        bg_color = QColor(self._colors[0])
        painter.fillRect(self.rect(), bg_color)

        # 绘制装饰元素
        self._draw_decorations(painter, width, height)

        # 绘制文字
        self._draw_text(painter, width, height)

    def _draw_decorations(self, painter: QPainter, width: int, height: int):
        """绘制装饰元素"""
        # 绘制一些装饰线条和形状
        color1 = QColor(self._colors[1])
        color2 = QColor(self._colors[2])

        # 顶部装饰线
        painter.setPen(QPen(color1, 3))
        painter.drawLine(20, 30, width - 20, 30)

        # 底部装饰线
        painter.setPen(QPen(color2, 2))
        painter.drawLine(20, height - 30, width - 20, height - 30)

        # 侧边装饰块
        painter.setBrush(QBrush(QColor(self._colors[3])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(10, height // 3, 8, height // 3)

    def _draw_text(self, painter: QPainter, width: int, height: int):
        """绘制文字"""
        lines = self._text_content.split('\n')
        if not lines:
            return

        # 计算字体大小
        available_height = height * 0.6
        font_size = int(available_height / len(lines) * 0.8)
        font_size = min(font_size, 48)  # 最大48像素

        # 设置字体
        font = QFont("Arial", font_size, QFont.Weight.Bold)
        painter.setFont(font)

        # 计算起始Y位置（垂直居中）
        total_text_height = font_size * len(lines) * 1.2
        start_y = (height - total_text_height) // 2 + font_size

        # 绘制每一行文字，使用不同颜色
        for i, line in enumerate(lines):
            color_idx = (i % 4) + 1  # 使用 colors[1] 到 colors[4]
            color = QColor(self._colors[color_idx])
            painter.setPen(color)

            # 计算水平居中
            metrics = QFontMetrics(font)
            text_width = metrics.horizontalAdvance(line)
            x = (width - text_width) // 2
            y = int(start_y + i * font_size * 1.2)

            painter.drawText(x, y, line)


class PreviewSceneSelector(ComboBox):
    """预览场景选择器 - 从配置加载场景列表"""

    scene_changed = Signal(str)  # 场景变化信号

    def __init__(self, parent=None):
        self._scenes: List[dict] = []
        super().__init__(parent)
        self._load_scenes_from_config()
        self._setup_items()
        # 默认选择第一个选项
        if self.count() > 0:
            self.setCurrentIndex(0)
        self.currentTextChanged.connect(self._on_selection_changed)

    def _load_scenes_from_config(self):
        """从配置加载场景列表"""
        try:
            from core import get_scene_config_manager
            scene_manager = get_scene_config_manager()
            self._scenes = scene_manager.get_all_scenes()
        except Exception as e:
            print(f"加载场景配置失败: {e}")
            # 使用默认场景列表
            self._scenes = [
                {"id": "custom", "name": "Custom - 自定义"},
                {"id": "mixed", "name": "Mixed - 混合"},
                {"id": "ui", "name": "UI Design - UI设计"},
                {"id": "web", "name": "Web - 网页"},
            ]

    def _setup_items(self):
        """设置选项"""
        self.clear()
        for scene in self._scenes:
            scene_id = scene.get("id", "")
            scene_name = scene.get("name", scene_id)
            self.addItem(scene_name)
            self.setItemData(self.count() - 1, scene_id)

    def _on_selection_changed(self, text: str):
        """处理选择变化"""
        index = self.currentIndex()
        key = self.itemData(index)
        if key:
            self.scene_changed.emit(key)

    def get_current_scene(self) -> str:
        """获取当前场景key"""
        return self.itemData(self.currentIndex()) or "mixed"

    def reload_scenes(self):
        """重新加载场景列表"""
        self._load_scenes_from_config()
        self._setup_items()

    def get_scene_config(self, scene_id: str) -> Optional[dict]:
        """获取场景配置

        Args:
            scene_id: 场景ID

        Returns:
            Optional[dict]: 场景配置，如果不存在则返回None
        """
        for scene in self._scenes:
            if scene.get("id") == scene_id:
                return scene.copy()
        return None


class MixedPreviewPanel(QWidget):
    """Mixed场景预览面板 - 2x2小图 + 右侧大图，支持自定义SVG预览、手机UI和Web预览"""

    def __init__(self, parent=None):
        self._colors: List[str] = []
        self._current_scene = "mixed"
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(15)

        # 创建 Mixed 场景面板
        self._mixed_widget = QWidget()
        mixed_layout = QHBoxLayout(self._mixed_widget)
        mixed_layout.setContentsMargins(0, 0, 0, 0)
        mixed_layout.setSpacing(15)

        # 左侧：2x2 小预览网格
        left_widget = QWidget()
        grid_layout = QGridLayout(left_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(10)

        self._small_previews: List[IllustrationPreview] = []
        for i in range(4):
            preview = IllustrationPreview()
            preview.set_seed(i)  # 不同的种子产生不同形态
            self._small_previews.append(preview)
            row = i // 2
            col = i % 2
            grid_layout.addWidget(preview, row, col)

        mixed_layout.addWidget(left_widget, stretch=1)

        # 右侧：大预览
        self._large_preview = TypographyPreview()
        mixed_layout.addWidget(self._large_preview, stretch=1)

        self._main_layout.addWidget(self._mixed_widget)

        # 创建自定义SVG预览面板（默认隐藏）
        self._svg_preview = SVGPreviewWidget()
        self._main_layout.addWidget(self._svg_preview)
        self._svg_preview.setVisible(False)

        # 创建手机UI预览面板（默认隐藏）
        self._mobile_preview = MobileUIPreview()
        self._main_layout.addWidget(self._mobile_preview)
        self._mobile_preview.setVisible(False)

        # 创建Web预览面板（默认隐藏）
        self._web_preview = WebPreview()
        self._main_layout.addWidget(self._web_preview)
        self._web_preview.setVisible(False)

    def set_scene(self, scene: str):
        """切换预览场景

        Args:
            scene: 场景名称
        """
        self._current_scene = scene

        # 隐藏所有场景
        self._mixed_widget.setVisible(False)
        self._svg_preview.setVisible(False)
        self._mobile_preview.setVisible(False)
        self._web_preview.setVisible(False)

        # 显示对应场景
        if scene == "custom":
            self._svg_preview.setVisible(True)
        elif scene == "ui":
            self._mobile_preview.setVisible(True)
        elif scene == "web":
            self._web_preview.setVisible(True)
        else:
            # mixed 和其他场景显示 Mixed 预览
            self._mixed_widget.setVisible(True)

    def set_colors(self, colors: List[str]):
        """设置配色"""
        self._colors = colors
        for preview in self._small_previews:
            preview.set_colors(colors)
        self._large_preview.set_colors(colors)
        self._svg_preview.set_colors(colors)
        self._mobile_preview.set_colors(colors)
        self._web_preview.set_colors(colors)

    def get_svg_preview(self) -> SVGPreviewWidget:
        """获取 SVG 预览组件"""
        return self._svg_preview


class PreviewToolbar(QWidget):
    """预览工具栏 - 包含圆点栏、场景选择、导入导出按钮"""

    scene_changed = Signal(str)              # 场景变化
    import_svg_requested = Signal()          # 导入SVG请求（custom场景）
    export_svg_requested = Signal()          # 导出SVG请求（custom场景）
    import_config_requested = Signal()       # 导入配置请求（所有场景）
    export_config_requested = Signal()       # 导出配置请求（所有场景）

    def __init__(self, parent=None):
        self._current_scene = "custom"
        super().__init__(parent)
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
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

        top_layout.addStretch()  # 弹性空间，使右侧内容右对齐

        # 导入导出按钮容器（对所有场景可见）
        self._buttons_container = QWidget()
        buttons_layout = QHBoxLayout(self._buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        # 导入按钮
        self._import_button = PushButton(FluentIcon.DOWNLOAD, "导入")
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
        """设置颜色"""
        self._dot_bar.set_colors(colors)

    def set_hex_visible(self, visible: bool):
        """设置HEX值显示开关

        Args:
            visible: 是否显示HEX值
        """
        self._dot_bar.set_hex_visible(visible)

    def get_dot_bar(self) -> ColorDotBar:
        """获取圆点栏（用于连接信号）"""
        return self._dot_bar

    def get_scene_selector(self) -> PreviewSceneSelector:
        """获取场景选择器"""
        return self._scene_selector

    def get_current_scene(self) -> str:
        """获取当前场景"""
        return self._scene_selector.get_current_scene()


class SVGPreviewWidget(QWidget):
    """SVG 预览组件 - 加载和显示 SVG 文件，支持配色应用"""

    def __init__(self, parent=None):
        self._colors: List[str] = ["#E8E8E8", "#D0D0D0", "#B8B8B8", "#A0A0A0", "#888888"]
        self._svg_renderer: Optional[QSvgRenderer] = None
        self._svg_content: str = ""
        self._original_svg_content: str = ""
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load_svg(self, file_path: str) -> bool:
        """加载 SVG 文件

        Args:
            file_path: SVG 文件路径

        Returns:
            bool: 是否加载成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._original_svg_content = f.read()

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

        # 如果有已加载的 SVG，重新应用配色
        if self._original_svg_content:
            self._apply_colors_to_svg()
            if self._svg_renderer:
                self._svg_renderer.load(self._svg_content.encode('utf-8'))
            self.update()

    def _apply_colors_to_svg(self):
        """将配色应用到 SVG 内容

        策略：
        1. 查找 SVG 中的 fill="..." 和 stroke="..." 属性
        2. 按顺序替换为当前配色
        3. 保留原始 SVG 结构
        """
        import re

        if not self._original_svg_content:
            return

        content = self._original_svg_content
        color_index = 0

        # 匹配 fill 属性（排除 none、transparent 等）
        def replace_fill(match):
            nonlocal color_index
            attr = match.group(1)
            value = match.group(2)

            # 跳过透明和无填充
            if value.lower() in ('none', 'transparent', 'inherit'):
                return match.group(0)

            # 替换为当前配色
            new_color = self._colors[color_index % len(self._colors)]
            color_index += 1
            return f'{attr}="{new_color}"'

        # 替换 fill 属性
        content = re.sub(r'(fill)="([^"]*)"', replace_fill, content)

        # 重置索引用于 stroke
        color_index = 0

        # 替换 stroke 属性
        def replace_stroke(match):
            nonlocal color_index
            attr = match.group(1)
            value = match.group(2)

            if value.lower() in ('none', 'transparent', 'inherit'):
                return match.group(0)

            new_color = self._colors[color_index % len(self._colors)]
            color_index += 1
            return f'{attr}="{new_color}"'

        content = re.sub(r'(stroke)="([^"]*)"', replace_stroke, content)

        self._svg_content = content

    def paintEvent(self, event):
        """绘制 SVG"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景
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
                # 计算缩放比例，保持居中
                widget_rect = self.rect()
                scale_x = widget_rect.width() / svg_width
                scale_y = widget_rect.height() / svg_height
                scale = min(scale_x, scale_y) * 0.9  # 留一些边距

                # 计算居中位置
                new_width = svg_width * scale
                new_height = svg_height * scale
                x = (widget_rect.width() - new_width) / 2
                y = (widget_rect.height() - new_height) / 2

                target_rect = QRect(int(x), int(y), int(new_width), int(new_height))
                self._svg_renderer.render(painter, target_rect)

    def get_svg_content(self) -> str:
        """获取当前 SVG 内容（用于导出）"""
        return self._svg_content

    def has_svg(self) -> bool:
        """是否已加载 SVG"""
        return self._svg_renderer is not None and self._svg_renderer.isValid()


class MobileUIPreview(QWidget):
    """手机UI场景预览 - 模拟移动应用界面"""

    def __init__(self, parent=None):
        self._colors: List[str] = ["#E8E8E8", "#D0D0D0", "#B8B8B8", "#A0A0A0", "#888888"]
        super().__init__(parent)
        self.setMinimumSize(200, 350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_colors(self, colors: List[str]):
        """设置配色"""
        if colors:
            self._colors = colors.copy()
            while len(self._colors) < 5:
                self._colors.extend(colors)
            self._colors = self._colors[:5]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 计算手机外框尺寸（保持宽高比）
        phone_width = min(width * 0.6, height * 0.5)
        phone_height = phone_width * 2.0

        # 居中位置
        x = (width - phone_width) / 2
        y = (height - phone_height) / 2

        # 屏幕边距（与外框中的 screen_margin 一致）
        screen_margin = 6
        screen_x = x + screen_margin
        screen_y = y + screen_margin
        screen_width = phone_width - screen_margin * 2
        screen_height = phone_height - screen_margin * 2

        # 绘制手机外框背景
        self._draw_phone_frame(painter, x, y, phone_width, phone_height)

        # 绘制状态栏（在屏幕区域内）
        self._draw_status_bar(painter, screen_x, screen_y, screen_width)

        # 绘制内容区域（在屏幕区域内，留出状态栏和导航栏空间）
        status_bar_height = 30
        nav_bar_height = 50
        content_y = screen_y + status_bar_height
        content_height = screen_height - status_bar_height - nav_bar_height
        self._draw_content(painter, screen_x, content_y, screen_width, content_height)

        # 绘制底部导航栏（在屏幕区域内）
        nav_y = screen_y + screen_height - nav_bar_height
        self._draw_bottom_nav(painter, screen_x, nav_y, screen_width, nav_bar_height)

    def _draw_phone_frame(self, painter: QPainter, x: float, y: float, width: float, height: float):
        """绘制手机外框"""
        # 外框阴影
        shadow_rect = QRect(int(x) + 3, int(y) + 3, int(width), int(height))
        shadow_color = QColor(0, 0, 0, 40)
        painter.setBrush(QBrush(shadow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(shadow_rect, 20, 20)

        # 外框主体
        frame_rect = QRect(int(x), int(y), int(width), int(height))
        frame_color = QColor(30, 30, 30) if not isDarkTheme() else QColor(20, 20, 20)
        painter.setBrush(QBrush(frame_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(frame_rect, 20, 20)

        # 屏幕区域
        screen_margin = 6
        screen_rect = QRect(
            int(x) + screen_margin,
            int(y) + screen_margin,
            int(width) - screen_margin * 2,
            int(height) - screen_margin * 2
        )
        screen_color = QColor(self._colors[0])
        painter.setBrush(QBrush(screen_color))
        painter.drawRoundedRect(screen_rect, 16, 16)

    def _draw_status_bar(self, painter: QPainter, x: float, y: float, width: float):
        """绘制状态栏"""
        status_height = 30
        status_rect = QRect(int(x), int(y), int(width), status_height)

        # 状态栏背景（使用配色中的颜色1）
        status_color = QColor(self._colors[1])
        painter.setBrush(QBrush(status_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(status_rect, 12, 12)

        # 绘制时间
        text_color = self._get_contrast_text_color(status_color)
        painter.setPen(QPen(text_color))
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, "9:41")

    def _draw_content(self, painter: QPainter, x: float, y: float, width: float, height: float):
        """绘制内容区域"""
        content_margin = 12
        card_height = 60
        spacing = 10

        # 绘制标题卡片
        title_rect = QRect(
            int(x) + content_margin,
            int(y) + content_margin,
            int(width) - content_margin * 2,
            card_height
        )
        title_color = QColor(self._colors[2])
        painter.setBrush(QBrush(title_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(title_rect, 12, 12)

        # 标题文字
        text_color = self._get_contrast_text_color(title_color)
        painter.setPen(QPen(text_color))
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "首页")

        # 绘制列表项
        list_y = y + content_margin + card_height + spacing
        for i in range(3):
            item_rect = QRect(
                int(x) + content_margin,
                int(list_y) + i * (45 + spacing),
                int(width) - content_margin * 2,
                45
            )
            item_color = QColor(self._colors[3] if i % 2 == 0 else self._colors[4])
            painter.setBrush(QBrush(item_color))
            painter.drawRoundedRect(item_rect, 8, 8)

            # 列表项文字
            text_color = self._get_contrast_text_color(item_color)
            painter.setPen(QPen(text_color))
            font = QFont("Arial", 11)
            painter.setFont(font)
            painter.drawText(item_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"  项目 {i + 1}")

        # 绘制浮动按钮
        fab_size = 50
        fab_x = x + width - content_margin - fab_size - 5
        fab_y = y + height - fab_size - 20
        fab_rect = QRect(int(fab_x), int(fab_y), fab_size, fab_size)
        fab_color = QColor(self._colors[1])
        painter.setBrush(QBrush(fab_color))
        painter.drawEllipse(fab_rect)

        # 按钮加号
        text_color = self._get_contrast_text_color(fab_color)
        painter.setPen(QPen(text_color, 2))
        center_x = int(fab_x + fab_size / 2)
        center_y = int(fab_y + fab_size / 2)
        painter.drawLine(center_x, center_y - 8, center_x, center_y + 8)
        painter.drawLine(center_x - 8, center_y, center_x + 8, center_y)

    def _draw_bottom_nav(self, painter: QPainter, x: float, y: float, width: float, height: float):
        """绘制底部导航栏"""
        nav_rect = QRect(int(x), int(y), int(width), int(height))
        nav_color = QColor(self._colors[1])
        painter.setBrush(QBrush(nav_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(nav_rect, 10, 10)

        # 绘制导航图标（简化为圆点）
        icon_count = 4
        icon_spacing = width / (icon_count + 1)
        icon_y = y + height / 2

        for i in range(icon_count):
            icon_x = x + icon_spacing * (i + 1)
            icon_rect = QRect(int(icon_x) - 6, int(icon_y) - 6, 12, 12)
            icon_color = QColor(self._colors[2] if i == 0 else self._colors[3])
            painter.setBrush(QBrush(icon_color))
            painter.drawEllipse(icon_rect)

    def _get_contrast_text_color(self, bg_color: QColor) -> QColor:
        """根据背景色获取对比文本色"""
        luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
        return QColor(255, 255, 255) if luminance < 0.5 else QColor(40, 40, 40)


class WebPreview(QWidget):
    """Web网页场景预览 - 模拟网页布局"""

    def __init__(self, parent=None):
        self._colors: List[str] = ["#E8E8E8", "#D0D0D0", "#B8B8B8", "#A0A0A0", "#888888"]
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_colors(self, colors: List[str]):
        """设置配色"""
        if colors:
            self._colors = colors.copy()
            while len(self._colors) < 5:
                self._colors.extend(colors)
            self._colors = self._colors[:5]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 绘制页面背景
        bg_color = QColor(self._colors[0])
        painter.fillRect(self.rect(), bg_color)

        # 绘制顶部导航栏
        self._draw_navbar(painter, width)

        # 绘制Hero区域
        self._draw_hero(painter, width, height)

        # 绘制内容卡片网格
        self._draw_card_grid(painter, width, height)

        # 绘制页脚
        self._draw_footer(painter, width, height)

    def _draw_navbar(self, painter: QPainter, width: int):
        """绘制顶部导航栏"""
        nav_height = 50
        nav_rect = QRect(0, 0, width, nav_height)
        nav_color = QColor(self._colors[1])
        painter.setBrush(QBrush(nav_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(nav_rect)

        # Logo区域
        logo_rect = QRect(20, 15, 80, 20)
        logo_color = QColor(self._colors[2])
        painter.setBrush(QBrush(logo_color))
        painter.drawRoundedRect(logo_rect, 4, 4)

        # 导航菜单项
        menu_items = ["首页", "产品", "关于"]
        item_x = width - 150
        text_color = self._get_contrast_text_color(nav_color)
        painter.setPen(QPen(text_color))
        font = QFont("Arial", 11)
        painter.setFont(font)

        for i, item in enumerate(menu_items):
            item_rect = QRect(int(item_x) + i * 50, 15, 45, 20)
            painter.drawText(item_rect, Qt.AlignmentFlag.AlignCenter, item)

    def _draw_hero(self, painter: QPainter, width: int, height: int):
        """绘制Hero区域"""
        hero_height = int(height * 0.35)
        hero_rect = QRect(0, 50, width, hero_height)
        hero_color = QColor(self._colors[2])
        painter.setBrush(QBrush(hero_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(hero_rect)

        # 主标题
        text_color = self._get_contrast_text_color(hero_color)
        painter.setPen(QPen(text_color))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        title_rect = QRect(0, 80, width, 40)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "欢迎来到我们的网站")

        # 副标题
        font = QFont("Arial", 12)
        painter.setFont(font)
        subtitle_rect = QRect(0, 130, width, 25)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter, "探索无限可能，创造美好未来")

        # CTA按钮
        button_width = 120
        button_height = 35
        button_x = (width - button_width) / 2
        button_y = 170
        button_rect = QRect(int(button_x), int(button_y), button_width, button_height)
        button_color = QColor(self._colors[3])
        painter.setBrush(QBrush(button_color))
        painter.drawRoundedRect(button_rect, 6, 6)

        # 按钮文字
        btn_text_color = self._get_contrast_text_color(button_color)
        painter.setPen(QPen(btn_text_color))
        font = QFont("Arial", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, "立即开始")

    def _draw_card_grid(self, painter: QPainter, width: int, height: int):
        """绘制内容卡片网格"""
        card_y = 50 + int(height * 0.35) + 20
        card_width = (width - 80) / 3
        card_height = int(height * 0.25)

        for i in range(3):
            card_x = 20 + i * (card_width + 20)
            card_rect = QRect(int(card_x), int(card_y), int(card_width), int(card_height))

            # 卡片背景
            card_color = QColor(self._colors[3] if i % 2 == 0 else self._colors[4])
            painter.setBrush(QBrush(card_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(card_rect, 8, 8)

            # 卡片图标（圆形）
            icon_size = 40
            icon_x = card_x + (card_width - icon_size) / 2
            icon_y = card_y + 20
            icon_rect = QRect(int(icon_x), int(icon_y), icon_size, icon_size)
            icon_color = QColor(self._colors[1])
            painter.setBrush(QBrush(icon_color))
            painter.drawEllipse(icon_rect)

            # 卡片标题
            text_color = self._get_contrast_text_color(card_color)
            painter.setPen(QPen(text_color))
            font = QFont("Arial", 12, QFont.Weight.Bold)
            painter.setFont(font)
            title_rect = QRect(int(card_x), int(icon_y) + icon_size + 10, int(card_width), 20)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, f"功能 {i + 1}")

            # 卡片描述
            font = QFont("Arial", 10)
            painter.setFont(font)
            desc_rect = QRect(int(card_x) + 10, int(icon_y) + icon_size + 35, int(card_width) - 20, 40)
            painter.drawText(desc_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, "这里是功能描述文本")

    def _draw_footer(self, painter: QPainter, width: int, height: int):
        """绘制页脚"""
        footer_height = 40
        footer_y = height - footer_height
        footer_rect = QRect(0, int(footer_y), width, footer_height)
        footer_color = QColor(self._colors[1])
        painter.setBrush(QBrush(footer_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(footer_rect)

        # 版权文字
        text_color = self._get_contrast_text_color(footer_color)
        painter.setPen(QPen(text_color))
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.drawText(footer_rect, Qt.AlignmentFlag.AlignCenter, "© 2026 Color Card. All rights reserved.")

    def _get_contrast_text_color(self, bg_color: QColor) -> QColor:
        """根据背景色获取对比文本色"""
        luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
        return QColor(255, 255, 255) if luminance < 0.5 else QColor(40, 40, 40)
