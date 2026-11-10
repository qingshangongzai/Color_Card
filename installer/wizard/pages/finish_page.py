# 第三方库导入
from PySide6.QtWidgets import QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
# 项目模块导入
from installer.wizard.base_page import BasePage
from installer.wizard.mini_widgets import PrimaryPushButton, CheckBox
from installer.wizard.mini_style import resolve_tokens


class FinishPage(BasePage):
    """完成页面"""

    def setup_ui(self):
        layout = self._content_layout
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        icon_label = QLabel("✓")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_font = QFont()
        icon_font.setPointSize(36)
        icon_label.setFont(icon_font)
        icon_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("安装完成！")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        desc_label = QLabel("取色卡已成功安装到您的计算机")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(desc_label)

        layout.addStretch(1)

        self._run_checkbox = CheckBox("立即运行 取色卡")
        self._run_checkbox.setChecked(True)
        layout.addWidget(self._run_checkbox, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        self._finish_button = PrimaryPushButton("完成")
        self._finish_button.setFixedSize(100, 32)
        self._finish_button.clicked.connect(self._finish)
        button_layout.addWidget(self._finish_button)

        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        # 底部留白由弹性空间收住，按钮行按离屏实测对齐 y≈266（其它向导页同高）
        layout.addStretch(1)

    def _finish(self):
        self._config['run_after_install'] = self._run_checkbox.isChecked()
        self.close_requested.emit()

    def _update_styles(self):
        super()._update_styles()

        text_color = resolve_tokens()['window_fg']
        secondary_color = resolve_tokens()['fg_secondary']

        for child in self._content_widget.findChildren(QLabel):
            if "安装完成" in child.text():
                child.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {text_color};")
            elif "取色卡已成功安装" in child.text():
                child.setStyleSheet(f"font-size: 12px; color: {secondary_color};")
