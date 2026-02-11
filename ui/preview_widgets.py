# 标准库导入
from typing import List, Optional, Dict, Any
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


class SceneRenderer:
    """通用场景渲染器 - 根据配置绘制各种场景元素"""

    @staticmethod
    def draw_empty_hint(painter: QPainter, width: int, height: int, hint_text: str = None):
        """绘制空配色提示

        Args:
            painter: 绘制器
            width: 宽度
            height: 高度
            hint_text: 提示文本，如果为None则使用默认文本
        """
        from ui.theme_colors import get_text_color

        bg_color = QColor(240, 240, 240) if not isDarkTheme() else QColor(50, 50, 50)
        painter.fillRect(0, 0, width, height, bg_color)

        text_color = get_text_color()
        painter.setPen(QPen(text_color))
        font = QFont("Arial", 11)
        painter.setFont(font)

        if hint_text is None:
            hint_text = "请从配色管理面板导入配色"
        painter.drawText(0, 0, width, height, Qt.AlignmentFlag.AlignCenter, hint_text)

    @staticmethod
    def get_color_by_index(colors: List[str], index: int) -> QColor:
        """根据索引获取颜色

        Args:
            colors: 颜色列表
            index: 颜色索引

        Returns:
            QColor: 颜色对象
        """
        if not colors:
            return QColor(200, 200, 200)
        return QColor(colors[index % len(colors)])

    @staticmethod
    def get_contrast_text_color(bg_color: QColor) -> QColor:
        """根据背景色获取对比文本色

        Args:
            bg_color: 背景色

        Returns:
            QColor: 对比文本色
        """
        luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
        return QColor(255, 255, 255) if luminance < 0.5 else QColor(40, 40, 40)

    @staticmethod
    def draw_rect(painter: QPainter, x: float, y: float, width: float, height: float,
                  color: QColor, border_radius: int = 0):
        """绘制矩形

        Args:
            painter: 绘制器
            x: X坐标
            y: Y坐标
            width: 宽度
            height: 高度
            color: 颜色
            border_radius: 圆角半径
        """
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        if border_radius > 0:
            painter.drawRoundedRect(int(x), int(y), int(width), int(height), border_radius, border_radius)
        else:
            painter.drawRect(int(x), int(y), int(width), int(height))

    @staticmethod
    def draw_circle(painter: QPainter, x: float, y: float, radius: float, color: QColor):
        """绘制圆形

        Args:
            painter: 绘制器
            x: 圆心X坐标
            y: 圆心Y坐标
            radius: 半径
            color: 颜色
        """
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(int(x), int(y)), int(radius), int(radius))

    @staticmethod
    def draw_line(painter: QPainter, x1: float, y1: float, x2: float, y2: float,
                 color: QColor, width: int = 1):
        """绘制线条

        Args:
            painter: 绘制器
            x1: 起点X坐标
            y1: 起点Y坐标
            x2: 终点X坐标
            y2: 终点Y坐标
            color: 颜色
            width: 线宽
        """
        painter.setPen(QPen(color, width))
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    @staticmethod
    def draw_text(painter: QPainter, text: str, x: float, y: float, width: float, height: float,
                  color: QColor, font_size: int = 12, font_weight: QFont.Weight = QFont.Weight.Normal,
                  alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter):
        """绘制文字

        Args:
            painter: 绘制器
            text: 文字内容
            x: X坐标
            y: Y坐标
            width: 宽度
            height: 高度
            color: 颜色
            font_size: 字体大小
            font_weight: 字体粗细
            alignment: 对齐方式
        """
        painter.setPen(QPen(color))
        font = QFont("Arial", font_size, font_weight)
        painter.setFont(font)
        painter.drawText(int(x), int(y), int(width), int(height), alignment, text)


class ConfigurablePreviewScene(BasePreviewScene):
    """配置化预览场景 - 从配置加载场景定义并渲染"""

    def __init__(self, scene_config: dict, parent=None):
        """初始化配置化场景

        Args:
            scene_config: 场景配置字典
            parent: 父控件
        """
        super().__init__(scene_config, parent)
        self._renderer = SceneRenderer()

    def paintEvent(self, event):
        """绘制场景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        if not self._colors:
            self._renderer.draw_empty_hint(painter, width, height)
            return

        scene_id = self.get_scene_id()

        if scene_id == "ui":
            self._draw_ui_scene(painter, width, height)
        elif scene_id == "web":
            self._draw_web_scene(painter, width, height)
        elif scene_id == "illustration":
            self._draw_illustration_scene(painter, width, height)
        elif scene_id == "typography":
            self._draw_typography_scene(painter, width, height)
        elif scene_id == "brand":
            self._draw_brand_scene(painter, width, height)
        elif scene_id == "poster":
            self._draw_poster_scene(painter, width, height)
        elif scene_id == "pattern":
            self._draw_pattern_scene(painter, width, height)
        elif scene_id == "magazine":
            self._draw_magazine_scene(painter, width, height)
        else:
            self._renderer.draw_empty_hint(painter, width, height)

    def _draw_ui_scene(self, painter: QPainter, width: int, height: int):
        """绘制UI场景"""
        config = self._config.get("config", {})

        frame_config = config.get("frame", {})
        screen_config = config.get("screen", {})
        status_bar_config = config.get("status_bar", {})
        content_config = config.get("content", {})
        bottom_nav_config = config.get("bottom_nav", {})

        phone_width = min(width * frame_config.get("width_ratio", 0.6), height * frame_config.get("height_ratio", 0.5))
        phone_height = phone_width * 2.0

        x = (width - phone_width) / 2
        y = (height - phone_height) / 2

        screen_margin = screen_config.get("margin", 6)
        screen_x = x + screen_margin
        screen_y = y + screen_margin
        screen_width = phone_width - screen_margin * 2
        screen_height = phone_height - screen_margin * 2

        self._draw_phone_frame(painter, x, y, phone_width, phone_height, frame_config, screen_config)

        status_bar_height = status_bar_config.get("height", 30)
        nav_bar_height = bottom_nav_config.get("height", 50)
        content_y = screen_y + status_bar_height
        content_height = screen_height - status_bar_height - nav_bar_height

        self._draw_status_bar(painter, screen_x, screen_y, screen_width, status_bar_height, status_bar_config)
        self._draw_content(painter, screen_x, content_y, screen_width, content_height, content_config)
        self._draw_bottom_nav(painter, screen_x, screen_y + screen_height - nav_bar_height, screen_width, nav_bar_height, bottom_nav_config)

    def _draw_phone_frame(self, painter: QPainter, x: float, y: float, width: float, height: float,
                         frame_config: dict, screen_config: dict):
        """绘制手机外框"""
        border_radius = frame_config.get("border_radius", 20)
        screen_margin = screen_config.get("margin", 6)
        screen_border_radius = screen_config.get("border_radius", 16)

        shadow_rect = QRect(int(x) + 3, int(y) + 3, int(width), int(height))
        shadow_color = QColor(0, 0, 0, 40)
        self._renderer.draw_rect(painter, shadow_rect.x(), shadow_rect.y(), shadow_rect.width(), shadow_rect.height(), shadow_color, border_radius)

        frame_color = QColor(30, 30, 30) if not isDarkTheme() else QColor(20, 20, 20)
        self._renderer.draw_rect(painter, x, y, width, height, frame_color, border_radius)

        screen_rect = QRect(int(x) + screen_margin, int(y) + screen_margin, int(width) - screen_margin * 2, int(height) - screen_margin * 2)
        screen_color = self._renderer.get_color_by_index(self._colors, 0)
        self._renderer.draw_rect(painter, screen_rect.x(), screen_rect.y(), screen_rect.width(), screen_rect.height(), screen_color, screen_border_radius)

    def _draw_status_bar(self, painter: QPainter, x: float, y: float, width: float, height: float, config: dict):
        """绘制状态栏"""
        border_radius = config.get("border_radius", 12)
        color_idx = config.get("color_idx", 1)
        text = config.get("text", "9:41")

        status_color = self._renderer.get_color_by_index(self._colors, color_idx)
        self._renderer.draw_rect(painter, x, y, width, height, status_color, border_radius)

        text_color = self._renderer.get_contrast_text_color(status_color)
        self._renderer.draw_text(painter, text, x, y, width, height, text_color, 10, QFont.Weight.Bold, Qt.AlignmentFlag.AlignCenter)

    def _draw_content(self, painter: QPainter, x: float, y: float, width: float, height: float, config: dict):
        """绘制内容区域"""
        margin = config.get("margin", 12)
        card_height = config.get("card_height", 60)
        spacing = config.get("spacing", 10)
        texts_config = config.get("texts", {})

        title_rect = QRect(int(x) + margin, int(y) + margin, int(width) - margin * 2, card_height)
        title_color = self._renderer.get_color_by_index(self._colors, 2)
        self._renderer.draw_rect(painter, title_rect.x(), title_rect.y(), title_rect.width(), title_rect.height(), title_color, 12)

        text_color = self._renderer.get_contrast_text_color(title_color)
        title_card_text = texts_config.get("title_card", "首页")
        self._renderer.draw_text(painter, title_card_text, title_rect.x(), title_rect.y(), title_rect.width(), title_rect.height(), text_color, 14, QFont.Weight.Bold, Qt.AlignmentFlag.AlignCenter)

        list_y = y + margin + card_height + spacing
        list_item_prefix = texts_config.get("list_item_prefix", "项目")
        list_item_count = texts_config.get("list_item_count", 3)
        for i in range(list_item_count):
            item_rect = QRect(int(x) + margin, int(list_y) + i * (45 + spacing), int(width) - margin * 2, 45)
            color_idx = 3 if i % 2 == 0 else 4
            item_color = self._renderer.get_color_by_index(self._colors, color_idx)
            self._renderer.draw_rect(painter, item_rect.x(), item_rect.y(), item_rect.width(), item_rect.height(), item_color, 8)

            text_color = self._renderer.get_contrast_text_color(item_color)
            item_text = f"  {list_item_prefix} {i + 1}"
            self._renderer.draw_text(painter, item_text, item_rect.x(), item_rect.y(), item_rect.width(), item_rect.height(), text_color, 11, QFont.Weight.Normal, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        fab_size = 50
        fab_x = x + width - margin - fab_size - 5
        fab_y = y + height - fab_size - 20
        fab_color = self._renderer.get_color_by_index(self._colors, 1)
        self._renderer.draw_circle(painter, fab_x + fab_size / 2, fab_y + fab_size / 2, fab_size / 2, fab_color)

        text_color = self._renderer.get_contrast_text_color(fab_color)
        center_x = int(fab_x + fab_size / 2)
        center_y = int(fab_y + fab_size / 2)
        self._renderer.draw_line(painter, center_x, center_y - 8, center_x, center_y + 8, text_color, 2)
        self._renderer.draw_line(painter, center_x - 8, center_y, center_x + 8, center_y, text_color, 2)

    def _draw_bottom_nav(self, painter: QPainter, x: float, y: float, width: float, height: float, config: dict):
        """绘制底部导航栏"""
        border_radius = config.get("border_radius", 10)
        color_idx = config.get("color_idx", 1)
        icon_count = config.get("icon_count", 4)

        nav_color = self._renderer.get_color_by_index(self._colors, color_idx)
        self._renderer.draw_rect(painter, x, y, width, height, nav_color, border_radius)

        icon_spacing = width / (icon_count + 1)
        icon_y = y + height / 2

        for i in range(icon_count):
            icon_x = x + icon_spacing * (i + 1)
            icon_color_idx = 2 if i == 0 else 3
            icon_color = self._renderer.get_color_by_index(self._colors, icon_color_idx)
            self._renderer.draw_circle(painter, icon_x, icon_y, 6, icon_color)

    def _draw_web_scene(self, painter: QPainter, width: int, height: int):
        """绘制Web场景"""
        config = self._config.get("config", {})

        bg_color = self._renderer.get_color_by_index(self._colors, 0)
        painter.fillRect(0, 0, width, height, bg_color)

        navbar_config = config.get("navbar", {})
        hero_config = config.get("hero", {})
        card_grid_config = config.get("card_grid", {})
        footer_config = config.get("footer", {})

        card_texts_config = card_grid_config.get("texts", {})
        self._draw_navbar(painter, width, navbar_config, card_texts_config)
        self._draw_hero(painter, width, height, hero_config)
        self._draw_card_grid(painter, width, height, card_grid_config)
        self._draw_footer(painter, width, height, footer_config)

    def _draw_navbar(self, painter: QPainter, width: int, config: dict, texts_config: dict = None):
        """绘制导航栏"""
        nav_height = config.get("height", 50)
        color_idx = config.get("color_idx", 1)
        logo_width = config.get("logo_width", 80)
        logo_height = config.get("logo_height", 20)
        logo_color_idx = config.get("logo_color_idx", 2)

        nav_color = self._renderer.get_color_by_index(self._colors, color_idx)
        self._renderer.draw_rect(painter, 0, 0, width, nav_height, nav_color, 0)

        logo_rect = QRect(20, 15, logo_width, logo_height)
        logo_color = self._renderer.get_color_by_index(self._colors, logo_color_idx)
        self._renderer.draw_rect(painter, logo_rect.x(), logo_rect.y(), logo_rect.width(), logo_rect.height(), logo_color, 4)

        menu_items = texts_config.get("menu_items", ["首页", "产品", "关于"]) if texts_config else ["首页", "产品", "关于"]
        item_x = width - 150
        text_color = self._renderer.get_contrast_text_color(nav_color)

        for i, item in enumerate(menu_items):
            item_rect = QRect(int(item_x) + i * 50, 15, 45, 20)
            self._renderer.draw_text(painter, item, item_rect.x(), item_rect.y(), item_rect.width(), item_rect.height(), text_color, 11, QFont.Weight.Normal, Qt.AlignmentFlag.AlignCenter)

    def _draw_hero(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制Hero区域"""
        height_ratio = config.get("height_ratio", 0.35)
        color_idx = config.get("color_idx", 2)
        title = config.get("title", "欢迎来到我们的网站")
        subtitle = config.get("subtitle", "探索无限可能，创造美好未来")
        button_config = config.get("button", {})

        hero_height = int(height * height_ratio)
        hero_color = self._renderer.get_color_by_index(self._colors, color_idx)
        self._renderer.draw_rect(painter, 0, 50, width, hero_height, hero_color, 0)

        text_color = self._renderer.get_contrast_text_color(hero_color)
        self._renderer.draw_text(painter, title, 0, 80, width, 40, text_color, 24, QFont.Weight.Bold, Qt.AlignmentFlag.AlignCenter)
        self._renderer.draw_text(painter, subtitle, 0, 130, width, 25, text_color, 12, QFont.Weight.Normal, Qt.AlignmentFlag.AlignCenter)

        button_width = button_config.get("width", 120)
        button_height = button_config.get("height", 35)
        button_text = button_config.get("text", "立即开始")
        button_color_idx = button_config.get("color_idx", 3)
        button_border_radius = button_config.get("border_radius", 6)

        button_x = (width - button_width) / 2
        button_y = 170
        button_color = self._renderer.get_color_by_index(self._colors, button_color_idx)
        self._renderer.draw_rect(painter, button_x, button_y, button_width, button_height, button_color, button_border_radius)

        btn_text_color = self._renderer.get_contrast_text_color(button_color)
        self._renderer.draw_text(painter, button_text, button_x, button_y, button_width, button_height, btn_text_color, 11, QFont.Weight.Bold, Qt.AlignmentFlag.AlignCenter)

    def _draw_card_grid(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制卡片网格"""
        columns = config.get("columns", 3)
        height_ratio = config.get("height_ratio", 0.25)
        card_spacing = config.get("card_spacing", 20)
        icon_size = config.get("icon_size", 40)
        color_idx_1 = config.get("color_idx_1", 3)
        color_idx_2 = config.get("color_idx_2", 4)
        icon_color_idx = config.get("icon_color_idx", 1)
        texts_config = config.get("texts", {})

        card_y = 50 + int(height * height_ratio) + 20
        card_width = (width - 80) / 3
        card_height = int(height * height_ratio)

        card_title_prefix = texts_config.get("card_title_prefix", "功能")
        card_description = texts_config.get("card_description", "这里是功能描述文本")

        for i in range(3):
            card_x = 20 + i * (card_width + card_spacing)
            card_color_idx = color_idx_1 if i % 2 == 0 else color_idx_2
            card_color = self._renderer.get_color_by_index(self._colors, card_color_idx)
            self._renderer.draw_rect(painter, card_x, card_y, card_width, card_height, card_color, 8)

            icon_x = card_x + (card_width - icon_size) / 2
            icon_y = card_y + 20
            icon_color = self._renderer.get_color_by_index(self._colors, icon_color_idx)
            self._renderer.draw_circle(painter, icon_x + icon_size / 2, icon_y + icon_size / 2, icon_size / 2, icon_color)

            text_color = self._renderer.get_contrast_text_color(card_color)
            title_rect = QRect(int(card_x), int(icon_y) + icon_size + 10, int(card_width), 20)
            card_title = f"{card_title_prefix} {i + 1}"
            self._renderer.draw_text(painter, card_title, title_rect.x(), title_rect.y(), title_rect.width(), title_rect.height(), text_color, 12, QFont.Weight.Bold, Qt.AlignmentFlag.AlignCenter)

            desc_rect = QRect(int(card_x) + 10, int(icon_y) + icon_size + 35, int(card_width) - 20, 40)
            self._renderer.draw_text(painter, card_description, desc_rect.x(), desc_rect.y(), desc_rect.width(), desc_rect.height(), text_color, 10, QFont.Weight.Normal, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap)

    def _draw_footer(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制页脚"""
        footer_height = config.get("height", 40)
        color_idx = config.get("color_idx", 1)
        text = config.get("text", "© 2026 Color Card. All rights reserved.")

        footer_y = height - footer_height
        footer_color = self._renderer.get_color_by_index(self._colors, color_idx)
        self._renderer.draw_rect(painter, 0, footer_y, width, footer_height, footer_color, 0)

        text_color = self._renderer.get_contrast_text_color(footer_color)
        self._renderer.draw_text(painter, text, 0, footer_y, width, footer_height, text_color, 10, QFont.Weight.Normal, Qt.AlignmentFlag.AlignCenter)

    def _draw_illustration_scene(self, painter: QPainter, width: int, height: int):
        """绘制插画场景"""
        config = self._config.get("config", {})

        bg_color = self._renderer.get_color_by_index(self._colors, 0)
        painter.fillRect(0, 0, width, height, bg_color)

        circles_config = config.get("circles", [])
        for circle in circles_config:
            x = int(circle["x"] * width)
            y = int(circle["y"] * height)
            r = int(circle["r"] * min(width, height))
            color_idx = circle.get("color_idx", 1)
            color = self._renderer.get_color_by_index(self._colors, color_idx)
            color.setAlpha(180)
            self._renderer.draw_circle(painter, x, y, r, color)

        plant_config = config.get("plant", {})
        stem_segments = plant_config.get("stem_segments", 8)
        leaf_positions = plant_config.get("leaf_positions", [0.3, 0.5, 0.7])

        line_color = QColor(40, 40, 40) if not isDarkTheme() else QColor(220, 220, 220)
        painter.setPen(QPen(line_color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        stem_x = int(width * 0.5)
        stem_bottom = int(height * 0.85)
        stem_top = int(height * 0.25)

        path_points = []
        for i in range(stem_segments + 1):
            t = i / stem_segments
            x = stem_x + int(math.sin(t * 3) * width * 0.08)
            y = stem_bottom - int(t * (stem_bottom - stem_top))
            path_points.append(QPoint(x, y))

        for i in range(len(path_points) - 1):
            painter.drawLine(path_points[i], path_points[i + 1])

        for pos in leaf_positions:
            idx = int(pos * (len(path_points) - 1))
            if idx < len(path_points):
                leaf_size = 25
                angle = 0.3
                left_leaf = QPoint(path_points[idx].x() - int(leaf_size * math.cos(angle)), path_points[idx].y() - int(leaf_size * math.sin(angle)))
                right_leaf = QPoint(path_points[idx].x() + int(leaf_size * math.cos(angle)), path_points[idx].y() - int(leaf_size * math.sin(angle)))
                painter.drawLine(path_points[idx], left_leaf)
                painter.drawLine(path_points[idx], right_leaf)

    def _draw_typography_scene(self, painter: QPainter, width: int, height: int):
        """绘制排版场景"""
        config = self._config.get("config", {})

        bg_color = self._renderer.get_color_by_index(self._colors, 0)
        painter.fillRect(0, 0, width, height, bg_color)

        decorations_config = config.get("decorations", {})
        top_line_config = decorations_config.get("top_line", {})
        bottom_line_config = decorations_config.get("bottom_line", {})
        side_block_config = decorations_config.get("side_block", {})

        top_line_color = self._renderer.get_color_by_index(self._colors, top_line_config.get("color_idx", 1))
        self._renderer.draw_line(painter, 20, top_line_config.get("y", 30), width - 20, top_line_config.get("y", 30), top_line_color, top_line_config.get("width", 3))

        bottom_line_color = self._renderer.get_color_by_index(self._colors, bottom_line_config.get("color_idx", 2))
        self._renderer.draw_line(painter, 20, height - bottom_line_config.get("y_offset", 30), width - 20, height - bottom_line_config.get("y_offset", 30), bottom_line_color, bottom_line_config.get("width", 2))

        side_block_height = height * side_block_config.get("height_ratio", 0.33)
        side_block_color = self._renderer.get_color_by_index(self._colors, side_block_config.get("color_idx", 3))
        self._renderer.draw_rect(painter, side_block_config.get("x", 10), height // 3, side_block_config.get("width", 8), side_block_height, side_block_color, 0)

        text = config.get("text", "All\nBodies\nAre\nGood\nBodies")
        text_colors = config.get("text_colors", [1, 2, 3, 4])
        lines = text.split('\n')

        available_height = height * 0.6
        font_size = int(available_height / len(lines) * 0.8)
        font_size = min(font_size, 48)

        total_text_height = font_size * len(lines) * 1.2
        start_y = (height - total_text_height) // 2 + font_size

        for i, line in enumerate(lines):
            color_idx = text_colors[i % len(text_colors)]
            color = self._renderer.get_color_by_index(self._colors, color_idx)
            painter.setPen(color)
            font = QFont("Arial", font_size, QFont.Weight.Bold)
            painter.setFont(font)

            metrics = QFontMetrics(font)
            text_width = metrics.horizontalAdvance(line)
            x = (width - text_width) // 2
            y = int(start_y + i * font_size * 1.2)

            painter.drawText(x, y, line)

    def _draw_brand_scene(self, painter: QPainter, width: int, height: int):
        """绘制品牌场景"""
        config = self._config.get("config", {})

        bg_color = self._renderer.get_color_by_index(self._colors, 0)
        painter.fillRect(0, 0, width, height, bg_color)

        logo_config = config.get("logo_section", {})
        card_config = config.get("business_card", {})
        strip_config = config.get("color_strip", {})

        self._draw_logo_section(painter, width, height, logo_config)
        self._draw_business_card(painter, width, height, card_config)
        self._draw_color_strip(painter, width, height, strip_config)

    def _draw_logo_section(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制Logo区域"""
        y_offset = int(height * config.get("y_offset", 0.08))
        circle_size = config.get("circle_size", 80)
        circle_color_idx = config.get("circle_color_idx", 1)
        icon_color_idx = config.get("icon_color_idx", 2)
        brand_name = config.get("brand_name", "BRAND")
        brand_name_color_idx = config.get("brand_name_color_idx", 1)
        tagline = config.get("tagline", "Your Tagline Here")
        tagline_color_idx = config.get("tagline_color_idx", 3)

        center_x = width // 2
        circle_y = y_offset + circle_size // 2

        circle_color = self._renderer.get_color_by_index(self._colors, circle_color_idx)
        self._renderer.draw_circle(painter, center_x, circle_y, circle_size // 2, circle_color)

        icon_color = self._renderer.get_color_by_index(self._colors, icon_color_idx)
        icon_size = circle_size // 3
        self._renderer.draw_rect(painter, center_x - icon_size // 2, circle_y - icon_size // 2, icon_size, icon_size, icon_color, 4)

        brand_color = self._renderer.get_color_by_index(self._colors, brand_name_color_idx)
        self._renderer.draw_text(painter, brand_name, 0, y_offset + circle_size + 10, width, 30, brand_color, 20, QFont.Weight.Bold, Qt.AlignmentFlag.AlignCenter)

        tagline_color = self._renderer.get_color_by_index(self._colors, tagline_color_idx)
        self._renderer.draw_text(painter, tagline, 0, y_offset + circle_size + 45, width, 20, tagline_color, 12, QFont.Weight.Normal, Qt.AlignmentFlag.AlignCenter)

    def _draw_business_card(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制名片"""
        y_offset = int(height * config.get("y_offset", 0.45))
        card_width = int(width * config.get("width_ratio", 0.85))
        card_height = config.get("height", 100)
        border_radius = config.get("border_radius", 8)
        bg_color_idx = config.get("bg_color_idx", 0)
        left_bar_width = config.get("left_bar_width", 12)
        left_bar_color_idx = config.get("left_bar_color_idx", 1)
        name = config.get("name", "John Doe")
        name_color_idx = config.get("name_color_idx", 1)
        title = config.get("title", "Creative Director")
        title_color_idx = config.get("title_color_idx", 3)
        contact = config.get("contact", "hello@brand.com")
        contact_color_idx = config.get("contact_color_idx", 2)

        card_x = (width - card_width) // 2
        card_y = y_offset

        shadow_color = QColor(0, 0, 0, 30)
        self._renderer.draw_rect(painter, card_x + 2, card_y + 2, card_width, card_height, shadow_color, border_radius)

        card_bg_color = self._renderer.get_color_by_index(self._colors, bg_color_idx)
        self._renderer.draw_rect(painter, card_x, card_y, card_width, card_height, card_bg_color, border_radius)

        left_bar_color = self._renderer.get_color_by_index(self._colors, left_bar_color_idx)
        self._renderer.draw_rect(painter, card_x, card_y, left_bar_width, card_height, left_bar_color, border_radius)

        name_color = self._renderer.get_color_by_index(self._colors, name_color_idx)
        self._renderer.draw_text(painter, name, card_x + left_bar_width + 15, card_y + 20, card_width - left_bar_width - 30, 25, name_color, 16, QFont.Weight.Bold, Qt.AlignmentFlag.AlignLeft)

        title_color = self._renderer.get_color_by_index(self._colors, title_color_idx)
        self._renderer.draw_text(painter, title, card_x + left_bar_width + 15, card_y + 48, card_width - left_bar_width - 30, 18, title_color, 12, QFont.Weight.Normal, Qt.AlignmentFlag.AlignLeft)

        contact_color = self._renderer.get_color_by_index(self._colors, contact_color_idx)
        self._renderer.draw_text(painter, contact, card_x + left_bar_width + 15, card_y + 70, card_width - left_bar_width - 30, 16, contact_color, 11, QFont.Weight.Normal, Qt.AlignmentFlag.AlignLeft)

    def _draw_color_strip(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制品牌色带"""
        y_offset = int(height * config.get("y_offset", 0.82))
        strip_height = config.get("height", 40)
        strip_count = config.get("strip_count", 5)
        strip_spacing = config.get("strip_spacing", 4)

        total_spacing = (strip_count - 1) * strip_spacing
        strip_width = (width - 40 - total_spacing) // strip_count
        start_x = 20

        for i in range(strip_count):
            color_idx = (i % len(self._colors)) if self._colors else 0
            color = self._renderer.get_color_by_index(self._colors, color_idx)
            x = start_x + i * (strip_width + strip_spacing)
            self._renderer.draw_rect(painter, x, y_offset, strip_width, strip_height, color, 4)

    def _draw_poster_scene(self, painter: QPainter, width: int, height: int):
        """绘制海报场景"""
        config = self._config.get("config", {})

        bg_config = config.get("background", {})
        bg_color = self._renderer.get_color_by_index(self._colors, bg_config.get("color_idx", 0))
        painter.fillRect(0, 0, width, height, bg_color)

        self._draw_poster_decorations(painter, width, height, config.get("top_decorations", {}))
        self._draw_poster_title(painter, width, height, config.get("main_title", {}))
        self._draw_poster_subtitle(painter, width, height, config.get("subtitle", {}))
        self._draw_poster_decoration_line(painter, width, height, config.get("decoration_line", {}))
        self._draw_poster_info(painter, width, height, config.get("info_section", {}))
        self._draw_poster_bottom_shapes(painter, width, height, config.get("bottom_shapes", []))

    def _draw_poster_decorations(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制海报顶部装饰"""
        shapes = config.get("shapes", [])
        for shape in shapes:
            shape_type = shape.get("type", "circle")
            x = int(shape.get("x", 0) * width)
            y = int(shape.get("y", 0) * height)
            color_idx = shape.get("color_idx", 1)
            color = self._renderer.get_color_by_index(self._colors, color_idx)

            if shape_type == "circle":
                size = int(shape.get("size", 0.05) * min(width, height))
                self._renderer.draw_circle(painter, x, y, size, color)
            elif shape_type == "rect":
                w = int(shape.get("width", 0.1) * width)
                h = int(shape.get("height", 0.05) * height)
                border_radius = shape.get("border_radius", 0)
                self._renderer.draw_rect(painter, x - w // 2, y - h // 2, w, h, color, border_radius)

    def _draw_poster_title(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制海报主标题"""
        text = config.get("text", "DESIGN")
        y_offset = int(height * config.get("y_offset", 0.28))
        font_size = config.get("font_size", 48)
        color_idx = config.get("color_idx", 1)
        letter_spacing = config.get("letter_spacing", 8)

        color = self._renderer.get_color_by_index(self._colors, color_idx)
        painter.setPen(color)
        font = QFont("Arial", font_size, QFont.Weight.Bold)
        painter.setFont(font)

        spaced_text = text
        if letter_spacing > 0:
            spaced_text = (" " * (letter_spacing // 4)).join(text)

        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(spaced_text)
        x = (width - text_width) // 2

        painter.drawText(x, y_offset, spaced_text)

    def _draw_poster_subtitle(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制海报副标题"""
        text = config.get("text", "")
        y_offset = int(height * config.get("y_offset", 0.42))
        font_size = config.get("font_size", 18)
        color_idx = config.get("color_idx", 2)

        color = self._renderer.get_color_by_index(self._colors, color_idx)
        self._renderer.draw_text(painter, text, 0, y_offset, width, 30, color, font_size, QFont.Weight.Normal, Qt.AlignmentFlag.AlignCenter)

    def _draw_poster_decoration_line(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制海报装饰线"""
        y_offset = int(height * config.get("y_offset", 0.52))
        line_width = int(width * config.get("width_ratio", 0.6))
        line_height = config.get("height", 3)
        color_idx = config.get("color_idx", 3)

        color = self._renderer.get_color_by_index(self._colors, color_idx)
        x = (width - line_width) // 2
        self._renderer.draw_rect(painter, x, y_offset, line_width, line_height, color, 0)

    def _draw_poster_info(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制海报信息区域"""
        y_offset = int(height * config.get("y_offset", 0.62))
        date_text = config.get("date", "")
        date_color_idx = config.get("date_color_idx", 1)
        location_text = config.get("location", "")
        location_color_idx = config.get("location_color_idx", 2)
        font_size = config.get("font_size", 12)

        date_color = self._renderer.get_color_by_index(self._colors, date_color_idx)
        location_color = self._renderer.get_color_by_index(self._colors, location_color_idx)

        self._renderer.draw_text(painter, date_text, 0, y_offset, width // 2, 20, date_color, font_size, QFont.Weight.Normal, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._renderer.draw_text(painter, location_text, width // 2, y_offset, width // 2, 20, location_color, font_size, QFont.Weight.Normal, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _draw_poster_bottom_shapes(self, painter: QPainter, width: int, height: int, shapes: list):
        """绘制海报底部装饰形状"""
        for shape in shapes:
            shape_type = shape.get("type", "rect")
            x = int(shape.get("x", 0) * width)
            y = int(shape.get("y", 0) * height)
            color_idx = shape.get("color_idx", 1)
            color = self._renderer.get_color_by_index(self._colors, color_idx)

            if shape_type == "circle":
                size = int(shape.get("size", 0.05) * min(width, height))
                self._renderer.draw_circle(painter, x, y, size, color)
            elif shape_type == "rect":
                w = int(shape.get("width", 0.2) * width)
                h = int(shape.get("height", 0.06) * height)
                border_radius = shape.get("border_radius", 0)
                self._renderer.draw_rect(painter, x, y, w, h, color, border_radius)

    def _draw_pattern_scene(self, painter: QPainter, width: int, height: int):
        """绘制图案场景"""
        config = self._config.get("config", {})

        bg_config = config.get("background", {})
        bg_color = self._renderer.get_color_by_index(self._colors, bg_config.get("color_idx", 0))
        painter.fillRect(0, 0, width, height, bg_color)

        self._draw_geometric_pattern(painter, width, height, config.get("geometric_pattern", {}))
        self._draw_wave_pattern(painter, width, height, config.get("wave_pattern", {}))
        self._draw_grid_overlay(painter, width, height, config.get("grid_overlay", {}))

    def _draw_geometric_pattern(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制几何图案"""
        rows = config.get("rows", 4)
        cols = config.get("cols", 6)
        shape_size = int(min(width, height) * config.get("shape_size", 0.08))
        spacing = int(min(width, height) * config.get("spacing", 0.02))
        shapes = config.get("shapes", [])

        total_width = cols * shape_size + (cols - 1) * spacing
        total_height = rows * shape_size + (rows - 1) * spacing
        start_x = (width - total_width) // 2
        start_y = int(height * 0.1)

        for row in range(rows):
            for col in range(cols):
                shape_idx = (row * cols + col) % len(shapes) if shapes else 0
                shape_config = shapes[shape_idx] if shapes else {"type": "circle", "color_idx": 1}
                shape_type = shape_config.get("type", "circle")
                color_idx = shape_config.get("color_idx", 1)
                color = self._renderer.get_color_by_index(self._colors, color_idx)

                x = start_x + col * (shape_size + spacing)
                y = start_y + row * (shape_size + spacing)
                center_x = x + shape_size // 2
                center_y = y + shape_size // 2

                if shape_type == "circle":
                    self._renderer.draw_circle(painter, center_x, center_y, shape_size // 2, color)
                elif shape_type == "square":
                    self._renderer.draw_rect(painter, x, y, shape_size, shape_size, color, 0)
                elif shape_type == "diamond":
                    self._draw_diamond(painter, center_x, center_y, shape_size // 2, color)
                elif shape_type == "triangle":
                    self._draw_triangle(painter, center_x, center_y, shape_size // 2, color)

    def _draw_diamond(self, painter: QPainter, x: int, y: int, size: int, color: QColor):
        """绘制菱形"""
        from PySide6.QtGui import QPolygon
        points = [
            QPoint(x, y - size),
            QPoint(x + size, y),
            QPoint(x, y + size),
            QPoint(x - size, y)
        ]
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygon(points))

    def _draw_triangle(self, painter: QPainter, x: int, y: int, size: int, color: QColor):
        """绘制三角形"""
        from PySide6.QtGui import QPolygon
        points = [
            QPoint(x, y - size),
            QPoint(x + size, y + size),
            QPoint(x - size, y + size)
        ]
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygon(points))

    def _draw_wave_pattern(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制波浪图案"""
        y_start = int(height * config.get("y_start", 0.55))
        wave_count = config.get("wave_count", 3)
        amplitude = int(height * config.get("amplitude", 0.06))
        frequency = config.get("frequency", 2)
        line_width = config.get("line_width", 3)
        colors = config.get("colors", [1, 2, 3])

        for i in range(wave_count):
            color_idx = colors[i % len(colors)] if colors else 1
            color = self._renderer.get_color_by_index(self._colors, color_idx)
            y_offset = y_start + i * (amplitude + 10)

            painter.setPen(QPen(color, line_width))
            points = []
            for x in range(0, width, 5):
                t = x / width * frequency * 3.14159 * 2
                y = y_offset + int(math.sin(t + i) * amplitude)
                points.append(QPoint(x, y))

            for j in range(len(points) - 1):
                painter.drawLine(points[j], points[j + 1])

    def _draw_grid_overlay(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制网格覆盖层"""
        if not config.get("enabled", True):
            return

        line_width = config.get("line_width", 1)
        color_idx = config.get("color_idx", 4)
        opacity = config.get("opacity", 0.3)

        color = self._renderer.get_color_by_index(self._colors, color_idx)
        color.setAlpha(int(255 * opacity))
        painter.setPen(QPen(color, line_width))

        grid_size = 40
        for x in range(0, width, grid_size):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, grid_size):
            painter.drawLine(0, y, width, y)

    def _draw_magazine_scene(self, painter: QPainter, width: int, height: int):
        """绘制杂志排版场景"""
        config = self._config.get("config", {})

        bg_config = config.get("background", {})
        bg_color = self._renderer.get_color_by_index(self._colors, bg_config.get("color_idx", 0))
        painter.fillRect(0, 0, width, height, bg_color)

        self._draw_magazine_header(painter, width, height, config.get("header", {}))
        self._draw_magazine_title(painter, width, height, config.get("main_title", {}))
        self._draw_magazine_feature_box(painter, width, height, config.get("feature_box", {}))
        self._draw_magazine_content(painter, width, height, config.get("article_content", {}))
        self._draw_magazine_quote(painter, width, height, config.get("quote_block", {}))
        self._draw_magazine_footer(painter, width, height, config.get("footer", {}))

    def _draw_magazine_header(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制杂志页眉"""
        header_height = config.get("height", 30)
        color_idx = config.get("color_idx", 1)
        text = config.get("text", "")
        text_color_idx = config.get("text_color_idx", 0)

        color = self._renderer.get_color_by_index(self._colors, color_idx)
        self._renderer.draw_rect(painter, 0, 0, width, header_height, color, 0)

        if text:
            text_color = self._renderer.get_color_by_index(self._colors, text_color_idx)
            self._renderer.draw_text(painter, text, 0, 5, width, header_height - 10, text_color, 12, QFont.Weight.Bold, Qt.AlignmentFlag.AlignCenter)

    def _draw_magazine_title(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制杂志主标题"""
        title = config.get("text", "")
        subtitle = config.get("subtitle", "")
        y_offset = int(height * config.get("y_offset", 0.15))
        title_color_idx = config.get("title_color_idx", 1)
        subtitle_color_idx = config.get("subtitle_color_idx", 2)
        title_size = config.get("title_size", 36)
        subtitle_size = config.get("subtitle_size", 48)

        title_color = self._renderer.get_color_by_index(self._colors, title_color_idx)
        painter.setPen(title_color)
        font = QFont("Arial", title_size, QFont.Weight.Normal)
        painter.setFont(font)

        metrics = QFontMetrics(font)
        title_width = metrics.horizontalAdvance(title)
        x = (width - title_width) // 2
        painter.drawText(x, y_offset, title)

        subtitle_color = self._renderer.get_color_by_index(self._colors, subtitle_color_idx)
        painter.setPen(subtitle_color)
        font = QFont("Arial", subtitle_size, QFont.Weight.Bold)
        painter.setFont(font)

        metrics = QFontMetrics(font)
        subtitle_width = metrics.horizontalAdvance(subtitle)
        x = (width - subtitle_width) // 2
        painter.drawText(x, y_offset + title_size + 10, subtitle)

    def _draw_magazine_feature_box(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制杂志特色框"""
        x = int(width * config.get("x", 0.05))
        y_offset = int(height * config.get("y_offset", 0.45))
        box_width = int(width * config.get("width", 0.25))
        box_height = int(height * config.get("height", 0.35))
        color_idx = config.get("color_idx", 3)
        text = config.get("text", "")
        text_color_idx = config.get("text_color_idx", 0)
        text_size = config.get("text_size", 14)

        color = self._renderer.get_color_by_index(self._colors, color_idx)
        self._renderer.draw_rect(painter, x, y_offset, box_width, box_height, color, 0)

        if text:
            text_color = self._renderer.get_color_by_index(self._colors, text_color_idx)
            self._renderer.draw_text(painter, text, x, y_offset + box_height // 2 - 10, box_width, 30, text_color, text_size, QFont.Weight.Bold, Qt.AlignmentFlag.AlignCenter)

    def _draw_magazine_content(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制杂志文章内容"""
        x = int(width * config.get("x", 0.35))
        y_offset = int(height * config.get("y_offset", 0.45))
        content_width = int(width * config.get("width", 0.6))
        headline = config.get("headline", "")
        headline_color_idx = config.get("headline_color_idx", 1)
        headline_size = config.get("headline_size", 16)
        paragraphs = config.get("paragraphs", [])
        paragraph_size = config.get("paragraph_size", 11)
        line_height = config.get("line_height", 1.6)

        current_y = y_offset

        if headline:
            headline_color = self._renderer.get_color_by_index(self._colors, headline_color_idx)
            self._renderer.draw_text(painter, headline, x, current_y, content_width, 25, headline_color, headline_size, QFont.Weight.Bold, Qt.AlignmentFlag.AlignLeft)
            current_y += 35

        for para in paragraphs:
            text = para.get("text", "")
            color_idx = para.get("color_idx", 2)
            color = self._renderer.get_color_by_index(self._colors, color_idx)

            if text:
                self._renderer.draw_text(painter, text, x, current_y, content_width, int(paragraph_size * line_height * 2), color, paragraph_size, QFont.Weight.Normal, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap)
                current_y += int(paragraph_size * line_height * 2.5)

    def _draw_magazine_quote(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制杂志引用块"""
        y_offset = int(height * config.get("y_offset", 0.78))
        quote_height = int(height * config.get("height", 0.15))
        bar_width = config.get("bar_width", 4)
        bar_color_idx = config.get("bar_color_idx", 2)
        text = config.get("text", "")
        text_color_idx = config.get("text_color_idx", 1)
        text_size = config.get("text_size", 12)

        bar_color = self._renderer.get_color_by_index(self._colors, bar_color_idx)
        self._renderer.draw_rect(painter, 20, y_offset, bar_width, quote_height, bar_color, 0)

        if text:
            text_color = self._renderer.get_color_by_index(self._colors, text_color_idx)
            self._renderer.draw_text(painter, text, 30 + bar_width, y_offset + 10, width - 50 - bar_width, quote_height - 20, text_color, text_size, QFont.Weight.Normal, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap)

    def _draw_magazine_footer(self, painter: QPainter, width: int, height: int, config: dict):
        """绘制杂志页脚"""
        y_offset = int(height * config.get("y_offset", 0.95))
        text = config.get("text", "")
        text_color_idx = config.get("text_color_idx", 4)
        text_size = config.get("text_size", 10)

        if text:
            text_color = self._renderer.get_color_by_index(self._colors, text_color_idx)
            self._renderer.draw_text(painter, text, 0, y_offset, width, 20, text_color, text_size, QFont.Weight.Normal, Qt.AlignmentFlag.AlignCenter)


class IllustrationPreview(QWidget):
    """插画风格配色预览 - 绘制植物风格矢量插画"""

    def __init__(self, parent=None):
        self._colors: List[str] = []
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
        else:
            self._colors = []
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

        # 如果没有配色，显示提示信息
        if not self._colors:
            self._draw_empty_hint(painter, width, height)
            return

        # 1. 绘制背景
        bg_color = QColor(self._colors[0])
        painter.fillRect(self.rect(), bg_color)

        # 2. 绘制装饰色块（圆形/椭圆形）
        self._draw_decorative_circles(painter, width, height)

        # 3. 绘制植物线条
        self._draw_plant(painter, width, height)

    def _draw_empty_hint(self, painter: QPainter, width: int, height: int):
        """绘制空配色提示"""
        from ui.theme_colors import get_text_color

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
        self._colors: List[str] = []
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
        else:
            self._colors = []
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

        # 如果没有配色，显示提示信息
        if not self._colors:
            self._draw_empty_hint(painter, width, height)
            return

        # 绘制背景
        bg_color = QColor(self._colors[0])
        painter.fillRect(self.rect(), bg_color)

        # 绘制装饰元素
        self._draw_decorations(painter, width, height)

        # 绘制文字
        self._draw_text(painter, width, height)

    def _draw_empty_hint(self, painter: QPainter, width: int, height: int):
        """绘制空配色提示"""
        from ui.theme_colors import get_text_color

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
        self._configurable_scenes: Dict[str, BasePreviewScene] = {}
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
            preview.set_seed(i)
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

    def set_scene(self, scene: str):
        """切换预览场景

        Args:
            scene: 场景名称
        """
        self._current_scene = scene

        # 隐藏所有场景
        self._mixed_widget.setVisible(False)
        self._svg_preview.setVisible(False)

        # 隐藏所有配置化场景
        for scene_widget in self._configurable_scenes.values():
            scene_widget.setVisible(False)

        # 显示对应场景
        if scene == "custom":
            self._svg_preview.setVisible(True)
        elif scene in ["ui", "web", "illustration", "typography", "brand", "poster", "pattern", "magazine"]:
            # 使用配置化场景
            self._show_configurable_scene(scene)
        else:
            # mixed 和其他场景显示 Mixed 预览
            self._mixed_widget.setVisible(True)

    def _show_configurable_scene(self, scene_id: str):
        """显示配置化场景

        Args:
            scene_id: 场景ID
        """
        # 如果场景已创建，直接显示
        if scene_id in self._configurable_scenes:
            self._configurable_scenes[scene_id].setVisible(True)
            return

        # 从配置管理器获取场景配置
        try:
            from core import get_scene_config_manager
            scene_manager = get_scene_config_manager()
            scene_config = scene_manager.get_scene_by_id(scene_id)

            if scene_config is None:
                print(f"未找到场景配置: {scene_id}")
                return

            # 使用工厂创建场景实例
            scene_widget = PreviewSceneFactory.create(scene_config, self)
            scene_widget.set_colors(self._colors)
            self._configurable_scenes[scene_id] = scene_widget
            self._main_layout.addWidget(scene_widget)
            scene_widget.setVisible(True)

        except Exception as e:
            print(f"创建配置化场景失败: {e}")

    def set_colors(self, colors: List[str]):
        """设置配色"""
        self._colors = colors if colors else []
        for preview in self._small_previews:
            preview.set_colors(self._colors)
        self._large_preview.set_colors(self._colors)
        self._svg_preview.set_colors(self._colors)

        # 更新配置化场景
        for scene_widget in self._configurable_scenes.values():
            scene_widget.set_colors(self._colors)

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

    def set_mapping_mode_visible(self, visible: bool):
        """设置映射模式选择器可见性（已废弃，保留方法以兼容旧代码）

        Args:
            visible: 是否可见
        """
        self._mapping_mode_selector.setVisible(visible)


class SVGPreviewWidget(QWidget):
    """SVG 预览组件 - 加载和显示 SVG 文件，支持智能配色应用"""

    def __init__(self, parent=None):
        self._colors: List[str] = []
        self._svg_renderer: Optional[QSvgRenderer] = None
        self._svg_content: str = ""
        self._original_svg_content: str = ""
        self._color_mapper: Optional[Any] = None  # SVGColorMapper 实例
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

            root = ET.fromstring(svg_content)

            # 获取 SVG 命名空间
            svg_ns = 'http://www.w3.org/2000/svg'
            nsmap = {'svg': svg_ns}

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
                import re
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

    def _draw_empty_hint(self, painter: QPainter):
        """绘制空配色提示"""
        from ui.theme_colors import get_text_color

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


def register_preview_scenes():
    """注册所有预览场景类型到工厂"""
    PreviewSceneFactory.register("configurable", ConfigurablePreviewScene)


register_preview_scenes()



