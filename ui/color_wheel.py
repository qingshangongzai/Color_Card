# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget
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
        # 背景统一为深灰色
        return {
            'bg': QColor(20, 20, 20),
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
