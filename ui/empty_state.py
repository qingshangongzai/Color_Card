"""空状态组件：图标 + 标题 + 提示，供配色管理与配色磁贴共用"""

# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import qconfig

# 项目模块导入
from utils import tr
from utils.theme_colors import get_text_color

# 图标、标题、提示的字号（与配色管理原有空状态保持一致）
ICON_FONT_SIZE = 48
TITLE_FONT_SIZE = 14
HINT_FONT_SIZE = 12


class EmptyStateWidget(QWidget):
    """空状态：图标 + 标题 + 可选提示，文案键在运行期可切换"""

    def __init__(
        self,
        icon: str,
        title_key: str,
        hint_key: str = '',
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon = icon
        self._title_key = title_key
        self._hint_key = hint_key

        self._setup_ui()
        self.retranslate()
        self._update_styles()
        qconfig.themeChangedFinished.connect(self._update_styles)

    def _setup_ui(self) -> None:
        """居中排列图标、标题与提示"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_label = QLabel(self)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)

        self._title_label = QLabel(self)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        self._hint_label = QLabel(self)
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint_label)

    def set_state(self, icon: str, title_key: str, hint_key: str = '') -> None:
        """切换空状态类型；hint_key 为空时隐藏提示行"""
        self._icon = icon
        self._title_key = title_key
        self._hint_key = hint_key
        self.retranslate()

    def retranslate(self) -> None:
        """按当前文案键刷新文本（语言切换后调用）"""
        self._icon_label.setText(self._icon)
        self._title_label.setText(tr(self._title_key))
        has_hint = bool(self._hint_key)
        self._hint_label.setVisible(has_hint)
        self._hint_label.setText(tr(self._hint_key) if has_hint else '')

    def _update_styles(self) -> None:
        """主题切换后刷新文字颜色"""
        color = get_text_color(secondary=True).name()
        self._icon_label.setStyleSheet(f"font-size: {ICON_FONT_SIZE}px; color: {color};")
        self._title_label.setStyleSheet(f"font-size: {TITLE_FONT_SIZE}px; color: {color};")
        self._hint_label.setStyleSheet(f"font-size: {HINT_FONT_SIZE}px; color: {color};")
