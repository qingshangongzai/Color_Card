# 标准库导入
from typing import List, Optional

# 第三方库导入
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QVBoxLayout, QWidget,
    QMessageBox
)
from qfluentwidgets import (
    PushButton, LineEdit, RadioButton, qconfig,
    PrimaryPushButton, CheckBox, ScrollArea
)

# 项目模块导入
from dialogs import BaseFramelessDialog
from utils import tr


class ExportSettingsDialog(BaseFramelessDialog):
    """导出设置对话框

    用于配置配色预览导出选项，包括选择图片、设置文件名前缀、选择导出格式等。
    """

    def __init__(self, svg_widgets: List[QWidget], parent=None):
        """初始化导出设置对话框

        Args:
            svg_widgets: SVG预览组件列表
            parent: 父窗口
        """
        super().__init__(parent)
        self._svg_widgets = svg_widgets
        self._check_boxes: List[CheckBox] = []
        self._filename_input: Optional[LineEdit] = None
        self._svg_radio: Optional[RadioButton] = None
        self._png_radio: Optional[RadioButton] = None

        self.setWindowTitle(tr('dialogs.export_settings.title'))
        self.setFixedSize(400, 450)

        # 设置界面
        self.setup_ui()

        # 设置标题栏和样式（基类提供）
        self._setup_title_bar()
        self._update_styles()

        # 监听主题变化
        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

        # 样式准备好后允许显示
        self._enable_show()

    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        # 顶部边距40px为标题栏留出空间
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(16)

        # 选择图片区域
        images_label = QLabel(tr('dialogs.export_settings.select_images'))
        layout.addWidget(images_label)

        # 图片选择列表（滚动区域）
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            ScrollArea {
                background-color: transparent;
                border: none;
            }
            ScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 设置滚动条角落为透明（防止出现灰色方块）
        corner_widget = QWidget()
        corner_widget.setStyleSheet("background: transparent;")
        scroll_area.setCornerWidget(corner_widget)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        # 创建图片选择项
        for i, widget in enumerate(self._svg_widgets):
            check_box = CheckBox(tr('dialogs.export_settings.image_item', index=i + 1))
            check_box.setChecked(True)
            self._check_boxes.append(check_box)
            scroll_layout.addWidget(check_box)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setMaximumHeight(200)
        layout.addWidget(scroll_area)

        # 全选/取消全选按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        select_all_btn = PushButton(tr('dialogs.export_settings.select_all'))
        select_all_btn.clicked.connect(self._on_select_all)
        buttons_layout.addWidget(select_all_btn)

        deselect_all_btn = PushButton(tr('dialogs.export_settings.deselect_all'))
        deselect_all_btn.clicked.connect(self._on_deselect_all)
        buttons_layout.addWidget(deselect_all_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # 文件名前缀
        prefix_layout = QVBoxLayout()
        prefix_layout.setSpacing(8)

        prefix_label = QLabel(tr('dialogs.export_settings.filename_prefix'))
        prefix_layout.addWidget(prefix_label)

        self._filename_input = LineEdit()
        self._filename_input.setText(tr('color_preview.export_default_name'))
        self._filename_input.setPlaceholderText(tr('color_preview.export_default_name'))
        prefix_layout.addWidget(self._filename_input)

        layout.addLayout(prefix_layout)

        # 导出格式
        format_layout = QVBoxLayout()
        format_layout.setSpacing(8)

        format_label = QLabel(tr('dialogs.export_settings.export_format'))
        format_layout.addWidget(format_label)

        format_radio_layout = QHBoxLayout()
        format_radio_layout.setSpacing(20)

        self._svg_radio = RadioButton(tr('dialogs.export_settings.format_svg'))
        self._svg_radio.setChecked(True)
        format_radio_layout.addWidget(self._svg_radio)

        self._png_radio = RadioButton(tr('dialogs.export_settings.format_png'))
        format_radio_layout.addWidget(self._png_radio)

        format_radio_layout.addStretch()
        format_layout.addLayout(format_radio_layout)

        layout.addLayout(format_layout)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        bottom_layout.addStretch()

        cancel_btn = PushButton(tr('dialogs.export_settings.cancel'))
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        export_btn = PrimaryPushButton(tr('dialogs.export_settings.export'))
        export_btn.clicked.connect(self._on_export_clicked)
        bottom_layout.addWidget(export_btn)

        layout.addLayout(bottom_layout)

    def _on_select_all(self):
        """全选"""
        for check_box in self._check_boxes:
            check_box.setChecked(True)

    def _on_deselect_all(self):
        """取消全选"""
        for check_box in self._check_boxes:
            check_box.setChecked(False)

    def _on_export_clicked(self):
        """处理导出按钮点击"""
        # 检查是否至少选择了一张图片
        if not self.get_selected_indices():
            QMessageBox.warning(
                self,
                tr('dialogs.export_settings.no_selection_title'),
                tr('dialogs.export_settings.no_selection_content')
            )
            return

        self.accept()

    def get_selected_indices(self) -> List[int]:
        """获取用户选择的图片索引列表

        Returns:
            List[int]: 选中的图片索引列表
        """
        return [i for i, check_box in enumerate(self._check_boxes) if check_box.isChecked()]

    def get_filename_prefix(self) -> str:
        """获取文件名前缀

        Returns:
            str: 文件名前缀，如果为空则返回默认值
        """
        prefix = self._filename_input.text().strip()
        if not prefix:
            prefix = tr('color_preview.export_default_name')
        return prefix

    def get_export_format(self) -> str:
        """获取导出格式

        Returns:
            str: 导出格式，"svg" 或 "png"
        """
        if self._png_radio and self._png_radio.isChecked():
            return "png"
        return "svg"

    def closeEvent(self, event):
        """关闭事件"""
        super().closeEvent(event)  # 基类处理信号断开
