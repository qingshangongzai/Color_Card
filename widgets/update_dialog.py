"""Color Card - 图片颜色提取工具
Copyright (c) 2026 浮晓 HXiao Studio

模块名称: update_dialog
功能描述: 更新检查对话框，检查并显示应用程序更新信息

作者: 青山公仔
创建日期: 2026-02-04
"""

# 标准库导入
import re

# 第三方库导入
from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, PrimaryPushButton, PushButton, isDarkTheme

try:
    import requests
except ImportError:
    requests = None

# 项目模块导入
from icon_utils import fix_windows_taskbar_icon_for_window, load_icon_universal


class UpdateCheckThread(QThread):
    """检查更新的后台线程

    在后台线程中检查 Gitee 仓库的最新版本信息，
    避免阻塞主线程。
    """

    check_finished = Signal(bool, str, str)

    def __init__(self, current_version):
        """初始化检查更新线程

        Args:
            current_version: 当前版本号
        """
        super().__init__()
        self.current_version = current_version

    def run(self):
        """在后台线程中检查更新"""
        try:
            if requests is None:
                self.check_finished.emit(False, "", "缺少 requests 库，无法检查更新")
                return

            api_url = "https://gitee.com/api/v5/repos/qingshangongzai/color_card/releases/latest"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").lstrip("v")

                if latest_version:
                    self.check_finished.emit(True, latest_version, "")
                else:
                    self.check_finished.emit(False, "", "无法解析版本信息")
            else:
                self.check_finished.emit(
                    False, "", f"获取版本信息失败: HTTP {response.status_code}"
                )

        except requests.exceptions.Timeout:
            self.check_finished.emit(False, "", "连接超时，请检查网络连接")
        except requests.exceptions.ConnectionError:
            self.check_finished.emit(False, "", "网络连接失败，请检查网络设置")
        except Exception as e:
            self.check_finished.emit(False, "", f"检查更新时出错: {str(e)}")


def compare_versions(current, latest):
    """比较版本号

    Args:
        current: 当前版本号
        latest: 最新版本号

    Returns:
        int: 0表示版本相同，1表示当前版本更新，-1表示有新版本
    """

    def parse_version(version_str):
        """解析版本号为数字列表"""
        version_str = version_str.lstrip("v")
        parts = re.findall(r"\d+", version_str)
        return [int(p) for p in parts] if parts else [0]

    current_parts = parse_version(current)
    latest_parts = parse_version(latest)

    max_len = max(len(current_parts), len(latest_parts))
    current_parts.extend([0] * (max_len - len(current_parts)))
    latest_parts.extend([0] * (max_len - len(latest_parts)))

    for c, l in zip(current_parts, latest_parts):
        if c > l:
            return 1
        elif c < l:
            return -1

    return 0


class UpdateAvailableDialog(QDialog):
    """新版本可用提示对话框

    当检测到有新版本时弹出，提供跳转到发行页面的功能。
    """

    def __init__(self, parent=None, current_version="", latest_version=""):
        """初始化新版本提示对话框

        Args:
            parent: 父窗口对象
            current_version: 当前版本号
            latest_version: 最新版本号
        """
        super().__init__(parent)
        self.setWindowTitle("发现新版本")
        self.setFixedSize(400, 200)
        self.current_version = current_version
        self.latest_version = latest_version

        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())

        # 设置窗口标志
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.CustomizeWindowHint
        )

        # 设置窗口背景色
        bg_color = QColor(32, 32, 32) if isDarkTheme() else QColor(255, 255, 255)
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color.name()}; }}")

        self.setup_ui()

        # 修复任务栏图标
        QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(self))

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 提示文本
        text_color = QColor(255, 255, 255) if isDarkTheme() else QColor(40, 40, 40)
        info_label = QLabel("有新版本可以更新")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet(
            f"QLabel {{ color: {text_color.name()}; font-size: 16px; font-weight: bold; }}"
        )
        layout.addWidget(info_label)

        # 版本信息
        version_label = QLabel(f"当前版本: {self.current_version} → 最新版本: {self.latest_version}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(f"QLabel {{ color: {text_color.name()}; font-size: 12px; }}")
        layout.addWidget(version_label)

        layout.addStretch()

        # 按钮区域
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        buttons_layout.addStretch()

        # 取消按钮
        cancel_button = PushButton("取消")
        cancel_button.setMinimumWidth(90)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        # 发行页面按钮（主题色）
        release_button = PrimaryPushButton("发行页面")
        release_button.setMinimumWidth(90)
        release_button.clicked.connect(self.open_release_page)
        buttons_layout.addWidget(release_button)

        buttons_layout.addStretch()

        layout.addWidget(buttons_container)

    def open_release_page(self):
        """打开 Gitee 发行版页面"""
        url = "https://gitee.com/qingshangongzai/color_card/releases"
        QDesktopServices.openUrl(QUrl(url))
        self.accept()

    @staticmethod
    def check_update(parent, current_version):
        """检查更新并显示相应提示

        Args:
            parent: 父窗口对象
            current_version: 当前版本号
        """
        if requests is None:
            InfoBar.warning(
                title="提示",
                content="缺少 requests 库，无法检查更新",
                parent=parent,
                duration=3000,
                position=InfoBarPosition.TOP,
            )
            return

        # 创建并启动检查线程
        check_thread = UpdateCheckThread(current_version)

        def on_check_finished(success, latest_version, error_msg):
            if success:
                result = compare_versions(current_version, latest_version)
                if result >= 0:
                    # 当前版本已是最新
                    InfoBar.info(
                        title="提示",
                        content="当前已是最新版本",
                        parent=parent,
                        duration=3000,
                        position=InfoBarPosition.TOP,
                    )
                else:
                    # 有新版本可用，显示对话框
                    dialog = UpdateAvailableDialog(parent, current_version, latest_version)
                    dialog.exec()
            else:
                InfoBar.warning(
                    title="检查更新失败",
                    content=error_msg,
                    parent=parent,
                    duration=5000,
                    position=InfoBarPosition.TOP,
                )

        check_thread.check_finished.connect(on_check_finished)
        check_thread.start()
