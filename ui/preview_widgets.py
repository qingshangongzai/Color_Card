# 标准库导入
from typing import List, Optional
import math

# 第三方库导入
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QMimeData
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QDrag, QPixmap, QFontMetrics
)
from qfluentwidgets import (
    ToolButton, ComboBox, PushButton,
    FluentIcon, isDarkTheme, qconfig
)

# 项目模块导入
from ui.theme_colors import get_border_color, get_text_color


class DraggableColorDot(QWidget):
    """可拖拽的颜色圆点组件"""

    drag_started = Signal(int)           # 开始拖拽信号：索引
    drag_ended = Signal(int, QPoint)     # 结束拖拽信号：索引, 结束位置
    clicked = Signal(int)                # 点击信号：索引

    def __init__(self, color: str, index: int, parent=None):
        self._color = color
        self._index = index
        self._dragging = False
        self._drag_start_pos = QPoint()
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

        # 如果是拖拽状态，绘制高亮效果
        if self._dragging:
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawEllipse(rect.adjusted(2, 2, -2, -2))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.drag_started.emit(self._index)
            self.update()

    def mouseMoveEvent(self, event):
        if not self._dragging:
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
        drag.setHotSpot(event.pos())

        # 执行拖拽
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.drag_ended.emit(self._index, event.pos())
            self.update()

    def mouseDoubleClickEvent(self, event):
        self.clicked.emit(self._index)


class ColorDotBar(QWidget):
    """颜色圆点工具栏，支持拖拽排序"""

    order_changed = Signal(list)         # 颜色顺序变化信号：新的颜色列表
    color_clicked = Signal(int)          # 颜色点击信号：索引

    def __init__(self, parent=None):
        self._colors: List[str] = []
        self._dots: List[DraggableColorDot] = []
        self._dragging_index = -1
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
            dot.drag_started.connect(self._on_drag_started)
            dot.drag_ended.connect(self._on_drag_ended)
            dot.clicked.connect(self._on_dot_clicked)
            self._dots.append(dot)
            layout.insertWidget(layout.count() - 1, dot)

    def _on_drag_started(self, index: int):
        """处理拖拽开始"""
        self._dragging_index = index

    def _on_drag_ended(self, index: int, end_pos: QPoint):
        """处理拖拽结束"""
        if self._dragging_index < 0:
            return

        # 计算新位置
        new_index = self._calculate_new_index(end_pos)

        if new_index != self._dragging_index and new_index >= 0:
            # 移动颜色
            color = self._colors.pop(self._dragging_index)
            self._colors.insert(new_index, color)
            # 重建圆点
            self._rebuild_dots()
            # 发射信号
            self.order_changed.emit(self._colors.copy())

        self._dragging_index = -1

    def _calculate_new_index(self, pos: QPoint) -> int:
        """计算拖拽位置对应的新索引"""
        layout = self.layout()
        for i in range(layout.count() - 1):  # 排除最后的 stretch
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget_rect = widget.geometry()
                # 检查位置是否在该 widget 的区域内
                if widget_rect.left() <= pos.x() <= widget_rect.right():
                    # 如果在左半边，插入到当前位置；右半边，插入到下一个位置
                    mid = widget_rect.center().x()
                    if pos.x() < mid:
                        return i
                    else:
                        return min(i + 1, len(self._dots) - 1)
        return len(self._dots) - 1

    def _on_dot_clicked(self, index: int):
        """处理圆点点击"""
        self.color_clicked.emit(index)

    def dragEnterEvent(self, event):
        """接受拖拽进入"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """处理放置"""
        event.acceptProposedAction()


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
    """预览场景选择器"""

    scene_changed = Signal(str)  # 场景变化信号

    SCENES = {
        "mixed": "Mixed - 混合",
        "ui": "UI Design - UI设计",
        "web": "Web - 网页",
        "brand": "Brand - 品牌",
        "illustration": "Illustration - 插画",
        "typography": "Typography - 排版",
        "poster": "Poster - 海报",
        "pattern": "Pattern - 图案"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_items()
        self.currentTextChanged.connect(self._on_selection_changed)

    def _setup_items(self):
        """设置选项"""
        for key, text in self.SCENES.items():
            self.addItem(text)
            self.setItemData(self.count() - 1, key)

    def _on_selection_changed(self, text: str):
        """处理选择变化"""
        index = self.currentIndex()
        key = self.itemData(index)
        if key:
            self.scene_changed.emit(key)

    def get_current_scene(self) -> str:
        """获取当前场景key"""
        return self.itemData(self.currentIndex()) or "mixed"


class MixedPreviewPanel(QWidget):
    """Mixed场景预览面板 - 2x2小图 + 右侧大图"""

    def __init__(self, parent=None):
        self._colors: List[str] = []
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

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

        layout.addWidget(left_widget, stretch=1)

        # 右侧：大预览
        self._large_preview = TypographyPreview()
        layout.addWidget(self._large_preview, stretch=1)

    def set_colors(self, colors: List[str]):
        """设置配色"""
        self._colors = colors
        for preview in self._small_previews:
            preview.set_colors(colors)
        self._large_preview.set_colors(colors)


class PreviewToolbar(QWidget):
    """预览工具栏 - 包含圆点栏、场景选择"""

    scene_changed = Signal(str)      # 场景变化

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(15)

        # 配色圆点栏
        self._dot_bar = ColorDotBar()
        layout.addWidget(self._dot_bar, stretch=1)

        # 场景选择器
        self._scene_selector = PreviewSceneSelector()
        self._scene_selector.setFixedWidth(180)
        self._scene_selector.scene_changed.connect(self.scene_changed.emit)
        layout.addWidget(self._scene_selector)

        self.setFixedHeight(60)

    def _update_styles(self):
        """更新样式以适配主题"""
        # 工具栏背景透明
        self.setStyleSheet("background: transparent;")

    def set_colors(self, colors: List[str]):
        """设置颜色"""
        self._dot_bar.set_colors(colors)

    def get_dot_bar(self) -> ColorDotBar:
        """获取圆点栏（用于连接信号）"""
        return self._dot_bar

    def get_current_scene(self) -> str:
        """获取当前场景"""
        return self._scene_selector.get_current_scene()
