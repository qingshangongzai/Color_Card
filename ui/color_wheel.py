# 标准库导入
import math

# 第三方库导入
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QCursor
from PySide6.QtWidgets import QSizePolicy, QWidget
from qfluentwidgets import isDarkTheme

# 项目模块导入
from core import rgb_to_hsb


class HSBColorWheel(QWidget):
    """HSB色环组件 - 显示采样点在HSB色彩空间中的位置（不可编辑）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self.setMaximumSize(300, 300)

        self._sample_colors = []  # 采样点颜色列表 [(r, g, b), ...]
        self._wheel_radius = 0    # 色环半径（动态计算）
        self._center_x = 0        # 中心X坐标
        self._center_y = 0        # 中心Y坐标

        # 缓存
        self._wheel_cache = None  # 色环背景缓存
        self._cache_valid = False  # 缓存是否有效
        self._cached_theme = None  # 缓存时的主题

    def set_sample_colors(self, colors):
        """设置采样点颜色

        Args:
            colors: 颜色列表，每个元素为 (r, g, b) 元组
        """
        self._sample_colors = colors if colors else []
        self.update()

    def update_sample_point(self, index, rgb):
        """更新指定索引的采样点颜色

        Args:
            index: 采样点索引
            rgb: (r, g, b) 元组
        """
        if index < 0:
            return

        # 确保列表足够长
        while len(self._sample_colors) <= index:
            self._sample_colors.append((128, 128, 128))  # 默认灰色

        self._sample_colors[index] = rgb
        self.update()  # 只重绘采样点，背景使用缓存

    def clear_sample_points(self):
        """清除所有采样点"""
        self._sample_colors = []
        self.update()

    def set_sample_count(self, count):
        """设置采样点数量

        Args:
            count: 采样点数量
        """
        # 调整采样点列表长度
        current_count = len(self._sample_colors)
        if count > current_count:
            # 增加采样点，使用默认灰色
            for _ in range(count - current_count):
                self._sample_colors.append((128, 128, 128))
        elif count < current_count:
            # 减少采样点
            self._sample_colors = self._sample_colors[:count]
        self.update()

    def _get_theme_colors(self):
        """获取主题颜色"""
        # 背景统一为 #2a2a2a
        return {
            'bg': QColor(42, 42, 42),
            'border': QColor(80, 80, 80),
            'text': QColor(200, 200, 200),
            'sample_border': QColor(255, 255, 255)
        }

    def _calculate_wheel_geometry(self):
        """计算色环几何参数"""
        # 留边距
        margin = 20
        available_size = min(self.width(), self.height()) - margin * 2
        self._wheel_radius = available_size // 2
        self._center_x = self.width() // 2
        self._center_y = self.height() // 2

    def _hsb_to_position(self, h, s, b):
        """将HSB值转换为色环上的位置

        Args:
            h: 色相 (0-360)
            s: 饱和度 (0-100)
            b: 亮度 (0-100)

        Returns:
            (x, y) 坐标
        """
        import math

        # 色相转换为角度（0°在右侧，逆时针增加）
        # Qt坐标系：0°在右侧，逆时针为正
        angle_rad = (h * math.pi / 180.0)

        # 饱和度转换为半径（0%在中心，100%在边缘）
        # 使用80%的最大半径，留一些边距
        max_radius = self._wheel_radius * 0.85
        radius = (s / 100.0) * max_radius

        # 计算坐标
        x = self._center_x + radius * math.cos(angle_rad)
        y = self._center_y - radius * math.sin(angle_rad)

        return int(x), int(y)

    def _invalidate_cache(self):
        """使缓存失效"""
        self._cache_valid = False
        self._wheel_cache = None

    def _generate_wheel_cache(self):
        """生成真正的HSB色彩空间色环"""
        import math
        from PySide6.QtGui import QImage

        # 计算色环几何参数
        self._calculate_wheel_geometry()

        # 创建QImage用于逐像素绘制
        width = self.width()
        height = self.height()
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(self._get_theme_colors()['bg'].rgb())

        # 逐像素计算HSB颜色
        for y in range(height):
            for x in range(width):
                # 计算相对于中心的距离和角度
                dx = x - self._center_x
                dy = y - self._center_y
                distance = math.sqrt(dx * dx + dy * dy)

                # 只绘制圆形区域内的像素
                if distance <= self._wheel_radius:
                    # 计算角度（色相）
                    angle = math.atan2(-dy, dx)  # 注意Y轴翻转
                    hue = (angle / (2 * math.pi)) % 1.0

                    # 计算饱和度（距离中心的远近）
                    saturation = min(distance / self._wheel_radius, 1.0)

                    # 设置亮度为1.0（最大值）
                    value = 1.0

                    # 计算颜色
                    color = QColor.fromHsvF(hue, saturation, value)
                    image.setPixelColor(x, y, color)

        # 转换为QPixmap
        self._wheel_cache = QPixmap.fromImage(image)

        # 绘制边框
        painter = QPainter(self._wheel_cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self._get_theme_colors()['border'], 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            self._center_x - self._wheel_radius,
            self._center_y - self._wheel_radius,
            self._wheel_radius * 2,
            self._wheel_radius * 2
        )
        painter.end()

        # 标记缓存有效
        self._cache_valid = True
        self._cached_theme = isDarkTheme()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 检查是否需要重新生成缓存
        current_theme = isDarkTheme()
        if not self._cache_valid or self._cached_theme != current_theme:
            self._generate_wheel_cache()

        # 绘制缓存的色环背景
        if self._wheel_cache:
            painter.drawPixmap(0, 0, self._wheel_cache)

        # 绘制采样点
        self._draw_sample_points(painter)

        # 绘制标题
        self._draw_title(painter)

    def _draw_sample_points(self, painter):
        """绘制采样点"""
        if not self._sample_colors:
            return

        sample_border_color = self._get_theme_colors()['sample_border']

        for rgb in self._sample_colors:
            r, g, b = rgb

            # 转换为HSB
            h, s, v = rgb_to_hsb(r, g, b)

            # 计算位置
            x, y = self._hsb_to_position(h, s, v)

            # 绘制采样点（带白色边框的圆点）
            point_radius = 8

            # 白色外边框
            painter.setPen(QPen(sample_border_color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(x - point_radius, y - point_radius,
                              point_radius * 2, point_radius * 2)

            # 填充颜色（使用实际颜色，但确保可见性）
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(r, g, b))
            painter.drawEllipse(x - point_radius + 2, y - point_radius + 2,
                              (point_radius - 2) * 2, (point_radius - 2) * 2)

    def _draw_title(self, painter):
        """绘制标题"""
        colors = self._get_theme_colors()
        painter.setPen(colors['text'])

        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        title = "HSB色环"
        painter.drawText(10, 20, title)

    def resizeEvent(self, event):
        """窗口大小改变时重新计算几何参数"""
        super().resizeEvent(event)
        self._calculate_wheel_geometry()
        self._invalidate_cache()  # 使缓存失效，下次绘制时重新生成


class InteractiveColorWheel(QWidget):
    """可交互的HSB色环组件 - 支持拖动选择基准色并显示配色方案点"""

    base_color_changed = Signal(float, float, float)
    scheme_color_changed = Signal(int, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 200)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self._base_hue = 0.0
        self._base_saturation = 100.0
        self._base_brightness = 100.0
        self._dragging = False

        self._wheel_radius = 0
        self._center_x = 0
        self._center_y = 0

        self._wheel_cache = None
        self._cache_valid = False
        self._cached_theme = None

        # 配色方案颜色点列表 [(h, s, b), ...]
        self._scheme_colors = []

        # 全局明度调整值 (-100 到 +100)
        self._global_brightness = 0

        # 选中和拖动状态
        self._selected_point_index = -1
        self._dragging_point_index = -1

    def set_base_color(self, h: float, s: float, b: float):
        """设置基准颜色

        Args:
            h: 色相 (0-360)
            s: 饱和度 (0-100)
            b: 亮度 (0-100)
        """
        self._base_hue = h % 360
        self._base_saturation = max(0, min(100, s))
        self._base_brightness = max(0, min(100, b))
        self.update()

    def get_base_color(self) -> tuple:
        """获取基准颜色

        Returns:
            tuple: (色相, 饱和度, 亮度)
        """
        return self._base_hue, self._base_saturation, self._base_brightness

    def set_scheme_colors(self, colors: list):
        """设置配色方案颜色点

        Args:
            colors: HSB颜色列表 [(h, s, b), ...]
        """
        self._scheme_colors = colors if colors else []
        self.update()

    def clear_scheme_colors(self):
        """清除配色方案颜色点"""
        self._scheme_colors = []
        self.update()

    def set_global_brightness(self, brightness: int):
        """设置全局明度调整值

        Args:
            brightness: 明度调整值 (-100 到 +100)
        """
        self._global_brightness = max(-100, min(100, brightness))
        self._invalidate_cache()  # 使缓存失效，重新生成色轮
        self.update()

    def _get_theme_colors(self):
        """获取主题颜色"""
        return {
            'bg': QColor(42, 42, 42),
            'border': QColor(80, 80, 80),
            'selector_border': QColor(255, 255, 255),
            'selector_inner': QColor(0, 0, 0),
            'scheme_point_border': QColor(255, 255, 255),
            'scheme_point_inner': QColor(0, 0, 0),
            'line': QColor(255, 255, 255, 128),
            'line_selected': QColor(255, 255, 255, 200)
        }

    def _calculate_wheel_geometry(self):
        """计算色环几何参数"""
        # 使用较小的边距，让色轮占据更多空间
        margin = 10
        available_size = min(self.width(), self.height()) - margin * 2
        # 确保半径至少为10，避免负数或零
        self._wheel_radius = max(10, available_size // 2)
        self._center_x = self.width() // 2
        self._center_y = self.height() // 2

    def _hsb_to_position(self, h: float, s: float, b: float = 100.0) -> tuple:
        """将HSB值转换为色环上的位置

        Args:
            h: 色相 (0-360)
            s: 饱和度 (0-100)
            b: 明度 (0-100)，仅用于颜色显示，不影响位置

        Returns:
            (x, y) 坐标
        """
        angle_rad = (h * math.pi / 180.0)
        max_radius = self._wheel_radius * 0.85

        # 位置仅由饱和度决定
        # 饱和度越高，点越靠近边缘；饱和度越低，点越靠近中心
        radius = max_radius * (s / 100.0)

        x = self._center_x + radius * math.cos(angle_rad)
        y = self._center_y - radius * math.sin(angle_rad)

        return int(x), int(y)

    def _position_to_hsb(self, x: int, y: int) -> tuple:
        """将色环上的位置转换为HSB值

        Args:
            x: X坐标
            y: Y坐标

        Returns:
            (色相, 饱和度)
        """
        dx = x - self._center_x
        dy = y - self._center_y
        distance = math.sqrt(dx * dx + dy * dy)

        max_radius = self._wheel_radius * 0.85
        saturation = min(distance / max_radius, 1.0) * 100

        angle = math.atan2(-dy, dx)
        hue = (angle / (2 * math.pi)) % 1.0 * 360

        return hue, saturation

    def _get_point_position(self, index: int) -> tuple:
        """获取指定索引采样点的位置

        Args:
            index: 采样点索引（0为基准点）

        Returns:
            (x, y) 坐标
        """
        brightness_factor = max(0.1, min(1.0, 1.0 + self._global_brightness / 100.0))

        if index == 0:
            # 基准点
            adjusted_b = max(10, min(100, self._base_brightness * brightness_factor))
            return self._hsb_to_position(self._base_hue, self._base_saturation, adjusted_b)
        elif 0 < index < len(self._scheme_colors):
            # 其他采样点
            h, s, b = self._scheme_colors[index]
            adjusted_b = max(10, min(100, b * brightness_factor))
            return self._hsb_to_position(h, s, adjusted_b)
        return (0, 0)

    def _hit_test_point(self, x: int, y: int) -> int:
        """检测点击位置是否在某个采样点上

        Args:
            x: 点击X坐标
            y: 点击Y坐标

        Returns:
            采样点索引（0为基准点），未命中返回-1
        """
        hit_radius = 15  # 点击检测半径

        # 先检测基准点（索引0）
        px, py = self._get_point_position(0)
        distance = math.sqrt((x - px) ** 2 + (y - py) ** 2)
        if distance <= hit_radius:
            return 0

        # 检测其他采样点
        for i in range(1, len(self._scheme_colors)):
            px, py = self._get_point_position(i)
            distance = math.sqrt((x - px) ** 2 + (y - py) ** 2)
            if distance <= hit_radius:
                return i

        return -1

    def _point_to_saturation(self, index: int, x: int, y: int) -> float:
        """根据鼠标位置计算采样点的新饱和度（沿连线方向）

        Args:
            index: 采样点索引
            x: 鼠标X坐标
            y: 鼠标Y坐标

        Returns:
            新的饱和度值 (0-100)
        """
        # 计算鼠标位置相对于圆心的距离
        dx = x - self._center_x
        dy = y - self._center_y
        distance = math.sqrt(dx * dx + dy * dy)

        # 根据距离直接计算饱和度
        # 距离中心越近，饱和度越低；距离中心越远，饱和度越高
        max_radius = self._wheel_radius * 0.85
        saturation = min(distance / max_radius, 1.0) * 100

        return max(0, min(100, saturation))

    def _invalidate_cache(self):
        """使缓存失效"""
        self._cache_valid = False
        self._wheel_cache = None

    def _generate_wheel_cache(self):
        """生成色环缓存"""
        from PySide6.QtGui import QImage

        self._calculate_wheel_geometry()

        width = self.width()
        height = self.height()
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(self._get_theme_colors()['bg'].rgb())

        # 计算全局明度因子 (0.1 到 1.0)
        brightness_factor = max(0.1, min(1.0, 1.0 + self._global_brightness / 100.0))

        for y in range(height):
            for x in range(width):
                dx = x - self._center_x
                dy = y - self._center_y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance <= self._wheel_radius:
                    angle = math.atan2(-dy, dx)
                    hue = (angle / (2 * math.pi)) % 1.0
                    saturation = min(distance / self._wheel_radius, 1.0)
                    # 应用全局明度调整
                    value = brightness_factor

                    color = QColor.fromHsvF(hue, saturation, value)
                    image.setPixelColor(x, y, color)

        self._wheel_cache = QPixmap.fromImage(image)

        painter = QPainter(self._wheel_cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self._get_theme_colors()['border'], 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            self._center_x - self._wheel_radius,
            self._center_y - self._wheel_radius,
            self._wheel_radius * 2,
            self._wheel_radius * 2
        )
        painter.end()

        self._cache_valid = True
        self._cached_theme = isDarkTheme()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        current_theme = isDarkTheme()
        if not self._cache_valid or self._cached_theme != current_theme:
            self._generate_wheel_cache()

        if self._wheel_cache:
            painter.drawPixmap(0, 0, self._wheel_cache)

        # 先绘制配色方案颜色点
        self._draw_scheme_points(painter)

        # 最后绘制选择器（在最上层）
        self._draw_selector(painter)

    def _draw_scheme_points(self, painter):
        """绘制配色方案颜色点及连线"""
        if not self._scheme_colors:
            return

        colors = self._get_theme_colors()
        base_point_radius = 8

        # 计算全局明度因子
        brightness_factor = max(0.1, min(1.0, 1.0 + self._global_brightness / 100.0))

        for i, (h, s, b) in enumerate(self._scheme_colors):
            # 跳过基准色（第一个点），因为选择器会显示它
            if i == 0:
                continue

            # 应用全局明度调整
            adjusted_b = max(10, min(100, b * brightness_factor))

            # 使用调整后的明度计算位置（明度越低越靠近中心）
            x, y = self._hsb_to_position(h, s, adjusted_b)

            # 判断是否选中
            is_selected = (i == self._selected_point_index)
            point_radius = base_point_radius + 2 if is_selected else base_point_radius

            # 绘制连线（从圆心到采样点）
            line_color = colors['line_selected'] if is_selected else colors['line']
            painter.setPen(QPen(line_color, 2 if is_selected else 1))
            painter.drawLine(self._center_x, self._center_y, x, y)

            # 绘制白色外边框
            painter.setPen(QPen(colors['scheme_point_border'], 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(x - point_radius, y - point_radius,
                              point_radius * 2, point_radius * 2)

            # 绘制内部颜色（使用调整后的明度）
            from core import hsb_to_rgb
            rgb = hsb_to_rgb(h, s, adjusted_b)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(rgb[0], rgb[1], rgb[2]))
            painter.drawEllipse(x - point_radius + 2, y - point_radius + 2,
                              (point_radius - 2) * 2, (point_radius - 2) * 2)

    def _draw_selector(self, painter):
        """绘制选择器（基准色）及连线"""
        colors = self._get_theme_colors()

        # 计算全局明度因子
        brightness_factor = max(0.1, min(1.0, 1.0 + self._global_brightness / 100.0))
        adjusted_brightness = max(10, min(100, self._base_brightness * brightness_factor))

        # 使用调整后的明度计算位置
        x, y = self._hsb_to_position(self._base_hue, self._base_saturation, adjusted_brightness)

        # 判断是否选中（基准点索引为0）
        is_selected = (self._selected_point_index == 0)
        selector_radius = 10

        # 计算连线终点（圆的边缘，而非圆心）
        dx = x - self._center_x
        dy = y - self._center_y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            # 计算指向圆心的单位向量，从圆周边缘开始绘制
            edge_x = x - (dx / distance) * selector_radius
            edge_y = y - (dy / distance) * selector_radius
        else:
            edge_x, edge_y = x, y

        # 绘制连线（从圆心到基准点圆的边缘）
        line_color = colors['line_selected'] if is_selected else colors['line']
        painter.setPen(QPen(line_color, 2 if is_selected else 1))
        painter.drawLine(self._center_x, self._center_y, int(edge_x), int(edge_y))

        # 白色外边框
        painter.setPen(QPen(colors['selector_border'], 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(x - selector_radius, y - selector_radius,
                          selector_radius * 2, selector_radius * 2)

        # 黑色内边框
        painter.setPen(QPen(colors['selector_inner'], 2))
        painter.drawEllipse(x - selector_radius + 3, y - selector_radius + 3,
                          (selector_radius - 3) * 2, (selector_radius - 3) * 2)

    def mousePressEvent(self, event):
        """处理鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            x, y = event.pos().x(), event.pos().y()

            # 检测是否点击在采样点上
            hit_index = self._hit_test_point(x, y)

            if hit_index >= 0:
                # 点击在采样点上，选中该点
                self._selected_point_index = hit_index
                self._dragging_point_index = hit_index
                self._dragging = True
                self.update()
            else:
                # 点击在空白处，拖动基准点（保持原有行为）
                hue, saturation = self._position_to_hsb(x, y)
                self._base_hue = hue
                self._base_saturation = saturation
                self._selected_point_index = 0  # 选中基准点
                self._dragging_point_index = 0
                self._dragging = True
                self.base_color_changed.emit(self._base_hue, self._base_saturation, self._base_brightness)
                self.update()

    def mouseMoveEvent(self, event):
        """处理鼠标移动"""
        if not self._dragging:
            return

        x, y = event.pos().x(), event.pos().y()

        if self._dragging_point_index == 0:
            # 拖动基准点，调整色相和饱和度
            hue, saturation = self._position_to_hsb(x, y)
            self._base_hue = hue
            self._base_saturation = saturation
            self.base_color_changed.emit(self._base_hue, self._base_saturation, self._base_brightness)
        elif self._dragging_point_index > 0 and self._dragging_point_index < len(self._scheme_colors):
            # 拖动其他采样点，沿连线调整饱和度
            new_saturation = self._point_to_saturation(self._dragging_point_index, x, y)
            h, s, b = self._scheme_colors[self._dragging_point_index]
            self._scheme_colors[self._dragging_point_index] = (h, new_saturation, b)
            self.scheme_color_changed.emit(self._dragging_point_index, h, new_saturation, b)

        self.update()

    def mouseReleaseEvent(self, event):
        """处理鼠标释放"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._dragging_point_index = -1

    def resizeEvent(self, event):
        """窗口大小改变"""
        super().resizeEvent(event)
        self._calculate_wheel_geometry()
        self._invalidate_cache()
