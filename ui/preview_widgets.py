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
        "custom": "Custom - 自定义",
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
        # 默认选择第一个选项（自定义）
        self.setCurrentIndex(0)
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
    """Mixed场景预览面板 - 2x2小图 + 右侧大图，支持自定义SVG预览"""

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

    def set_scene(self, scene: str):
        """切换预览场景

        Args:
            scene: 场景名称
        """
        self._current_scene = scene

        if scene == "custom":
            # 显示 SVG 预览，隐藏 Mixed 预览
            self._mixed_widget.setVisible(False)
            self._svg_preview.setVisible(True)
        else:
            # 显示 Mixed 预览，隐藏 SVG 预览
            self._mixed_widget.setVisible(True)
            self._svg_preview.setVisible(False)

    def set_colors(self, colors: List[str]):
        """设置配色"""
        self._colors = colors
        for preview in self._small_previews:
            preview.set_colors(colors)
        self._large_preview.set_colors(colors)
        self._svg_preview.set_colors(colors)

    def get_svg_preview(self) -> SVGPreviewWidget:
        """获取 SVG 预览组件"""
        return self._svg_preview


class PreviewToolbar(QWidget):
    """预览工具栏 - 包含圆点栏、场景选择、导入导出按钮"""

    scene_changed = Signal(str)      # 场景变化
    import_svg_requested = Signal()  # 导入SVG请求
    export_svg_requested = Signal()  # 导出SVG请求

    def __init__(self, parent=None):
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

        # 导入导出按钮容器（默认隐藏）
        self._svg_buttons_container = QWidget()
        svg_buttons_layout = QHBoxLayout(self._svg_buttons_container)
        svg_buttons_layout.setContentsMargins(0, 0, 0, 0)
        svg_buttons_layout.setSpacing(8)

        # 导入按钮
        self._import_button = PushButton(FluentIcon.DOWNLOAD, "导入")
        self._import_button.setFixedHeight(32)
        self._import_button.clicked.connect(self.import_svg_requested.emit)
        svg_buttons_layout.addWidget(self._import_button)

        # 导出按钮
        self._export_button = PushButton(FluentIcon.UP, "导出")
        self._export_button.setFixedHeight(32)
        self._export_button.clicked.connect(self.export_svg_requested.emit)
        svg_buttons_layout.addWidget(self._export_button)

        top_layout.addWidget(self._svg_buttons_container)
        self._svg_buttons_container.setVisible(False)

        # 场景选择器
        self._scene_selector = PreviewSceneSelector()
        self._scene_selector.setFixedWidth(180)
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

        # 初始化时同步按钮显示状态（默认选中自定义，需要显示导入导出按钮）
        current_scene = self._scene_selector.get_current_scene()
        self._on_scene_changed(current_scene)

    def _on_scene_changed(self, scene: str):
        """处理场景变化"""
        # 只在自定义场景显示导入导出按钮
        is_custom = (scene == "custom")
        self._svg_buttons_container.setVisible(is_custom)
        # 转发信号
        self.scene_changed.emit(scene)

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
