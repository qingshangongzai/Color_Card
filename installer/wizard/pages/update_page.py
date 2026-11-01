# 标准库导入
# 第三方库导入
from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal
from qfluentwidgets import LineEdit, PushButton, PrimaryPushButton

# 项目模块导入
from installer.wizard.base_page import BasePage
from installer.core.permission_checker import is_admin, requires_admin, validate_install_path


class UpdatePage(BasePage):
    """更新页面

    展示旧安装位置，沿用该位置覆盖更新。
    """

    elevation_requested = Signal(str, bool, bool)  # 参数：安装路径, 桌面快捷方式, 开始菜单快捷方式

    def __init__(self, old_install_path: str, parent=None):
        """初始化页面

        Args:
            old_install_path: 旧版本安装路径
            parent: 父窗口
        """
        super().__init__(parent)
        self.setObjectName('updatePage')
        self._old_install_path = old_install_path

    def setup_ui(self) -> None:
        """设置页面UI"""
        layout = self._content_layout
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("检测到已有安装")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        # 安装位置：标签沿用安装页标签字号，路径用只读输入框展示（与安装页输入行一致）
        location_layout = QHBoxLayout()
        location_layout.setSpacing(10)

        location_label = QLabel("安装位置：")
        location_layout.addWidget(location_label)

        self._path_edit = LineEdit()
        self._path_edit.setText(self._old_install_path)
        self._path_edit.setReadOnly(True)
        location_layout.addWidget(self._path_edit, 1)

        # 说明块与路径行的间距对齐安装页第二行信息的节奏
        info_layout = QVBoxLayout()
        info_layout.setSpacing(15)
        info_layout.addLayout(location_layout)

        hint_layout = QVBoxLayout()
        hint_layout.setSpacing(8)

        hint_title = QLabel("更新时将会：")
        hint_title.setStyleSheet("font-size: 13px;")
        hint_layout.addWidget(hint_title)

        for hint_item in ("关闭正在运行的取色卡", "将程序文件覆盖到原安装位置", "保留已保存的配色与设置"):
            item_label = QLabel(f"· {hint_item}")
            item_label.setStyleSheet("font-size: 12px;")
            hint_layout.addWidget(item_label)

        info_layout.addLayout(hint_layout)

        layout.addLayout(info_layout)

        # 内容较少：按钮行按离屏实测的 y≈280 对齐其它向导页，权重按此调校
        layout.addStretch(6)

        # 导航按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch(1)

        self._back_button = PushButton("上一步")
        self._back_button.setFixedSize(100, 32)
        self._back_button.clicked.connect(self.back_requested.emit)
        button_layout.addWidget(self._back_button)

        self._update_button = PrimaryPushButton("立即更新")
        self._update_button.setFixedSize(100, 32)
        self._update_button.clicked.connect(self._start_update)
        button_layout.addWidget(self._update_button)

        # 左右弹性空间使按钮行居中
        button_layout.addStretch(1)

        layout.addLayout(button_layout)

        # 底部留白由弹性空间收住，按钮行不贴底
        layout.addStretch(1)

    def _start_update(self) -> None:
        """开始更新"""
        if not validate_install_path(self._old_install_path):
            return

        # 旧安装位于受保护目录时需提权；重启后经 --skip-to-progress 直跳进度页
        if requires_admin(self._old_install_path) and not is_admin():
            from installer.wizard.elevation_dialog import ElevationDialog
            dialog = ElevationDialog(self.window())
            dialog.set_message(
                "安装到该位置需要管理员权限。\n"
                "点击「确定」后，Windows 将请求您的确认。"
            )
            if dialog.exec():
                # 快捷方式沿用向导默认值（与路径页默认勾选一致）
                self.elevation_requested.emit(self._old_install_path, True, True)
            return

        self._config['install_path'] = self._old_install_path

        self.next_requested.emit()
