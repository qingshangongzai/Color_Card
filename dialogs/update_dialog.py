# 标准库导入
import re
from typing import List, Tuple

# 第三方库导入
import requests
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, PrimaryPushButton, PushButton, qconfig

# 项目模块导入
from utils import tr, load_icon_universal
from dialogs import BaseFramelessDialog
from core import get_app_mode, get_platform, AppMode, Platform


class UpdateCheckThread(QThread):
    """检查更新的后台线程

    在后台线程中检查 Gitee 仓库的最新版本信息，
    避免阻塞主线程。
    """

    check_finished = Signal(bool, str, str, str)

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
            api_url = "https://gitee.com/api/v5/repos/qingshangongzai/color_card/releases/latest"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").lstrip("v")
                download_url = self._select_asset(data.get("assets", []))

                if latest_version:
                    self.check_finished.emit(True, latest_version, "", download_url)
                else:
                    self.check_finished.emit(False, "", tr('dialogs.update.error_parse_version'), "")
            else:
                self.check_finished.emit(
                    False, "", tr('dialogs.update.error_http', status_code=response.status_code), ""
                )

        except requests.exceptions.Timeout:
            self.check_finished.emit(False, "", tr('dialogs.update.error_timeout'), "")
        except requests.exceptions.ConnectionError:
            self.check_finished.emit(False, "", tr('dialogs.update.error_connection'), "")
        except Exception as e:
            self.check_finished.emit(False, "", tr('dialogs.update.error_general', error=str(e)), "")

    def _select_asset(self, assets):
        """选择对应安装包

        Args:
            assets: 资源列表

        Returns:
            str: 下载链接，未找到返回空字符串
        """
        if not assets:
            return ""

        mode = get_app_mode()
        platform = get_platform()

        for asset in assets:
            name = asset.get("name", "").lower()
            url = asset.get("browser_download_url", "")

            if not url:
                continue

            # macOS: 匹配 .dmg 文件
            if platform == Platform.MACOS and name.endswith(".dmg"):
                return url

            # Windows: 根据模式匹配
            if platform == Platform.WINDOWS:
                # 安装版: 匹配包含 setup 的 .exe
                if mode == AppMode.INSTALLED and "setup" in name and name.endswith(".exe"):
                    return url
                # 便携版/其他: 匹配以 x64.exe 结尾且不含 setup 的
                if mode != AppMode.INSTALLED and name.endswith("x64.exe") and "setup" not in name:
                    return url

        # 默认返回第一个
        return assets[0].get("browser_download_url", "") if assets else ""


_PRE_RELEASE_ORDER = {"alpha": -3, "beta": -2, "rc": -1}


def _parse_version(version_str: str) -> Tuple[List[int], int, int]:
    """解析版本号为数字列表、预发布标识和预发布版本号

    Args:
        version_str: 版本号字符串

    Returns:
        Tuple[List[int], int, int]: (版本号数字列表, 预发布标识, 预发布版本号)
        预发布标识: 0=正式版, -1=RC, -2=Beta, -3=Alpha
        预发布版本号: Beta1/Beta2等后面的数字，默认0
    """
    version_str = version_str.lstrip("v").lower()
    parts = re.findall(r"\d+", version_str)
    nums = [int(p) for p in parts] if parts else [0]

    pre_release = 0
    pre_release_num = 0
    for keyword, value in _PRE_RELEASE_ORDER.items():
        if keyword in version_str:
            pre_release = value
            match = re.search(rf"{keyword}(\d+)", version_str)
            if match:
                pre_release_num = int(match.group(1))
            break

    return nums, pre_release, pre_release_num


def compare_versions(current: str, latest: str) -> int:
    """比较版本号

    Args:
        current: 当前版本号
        latest: 最新版本号

    Returns:
        int: 0表示版本相同，1表示当前版本更新，-1表示有新版本
    """
    current_parts, current_pre, current_pre_num = _parse_version(current)
    latest_parts, latest_pre, latest_pre_num = _parse_version(latest)

    max_len = max(len(current_parts), len(latest_parts))
    current_parts.extend([0] * (max_len - len(current_parts)))
    latest_parts.extend([0] * (max_len - len(latest_parts)))

    for c, latest_part in zip(current_parts, latest_parts):
        if c > latest_part:
            return 1
        elif c < latest_part:
            return -1

    if current_pre > latest_pre:
        return 1
    elif current_pre < latest_pre:
        return -1

    if current_pre_num > latest_pre_num:
        return 1
    elif current_pre_num < latest_pre_num:
        return -1

    return 0


class UpdateAvailableDialog(BaseFramelessDialog):
    """新版本可用提示对话框

    当检测到有新版本时弹出，提供直接下载或跳转到发行页面的功能。
    """

    _check_thread = None  # 类变量，用于保存检查更新的线程对象

    def __init__(self, parent=None, current_version="", latest_version="", download_url=""):
        """初始化新版本提示对话框

        Args:
            parent: 父窗口对象
            current_version: 当前版本号
            latest_version: 最新版本号
            download_url: 下载链接
        """
        super().__init__(parent)
        self.setWindowTitle(tr('dialogs.update.title'))
        self.setFixedSize(400, 200)
        self.current_version = current_version
        self.latest_version = latest_version
        self.download_url = download_url

        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())

        # 设置界面
        self.setup_ui()

        # 设置标题栏和样式（基类提供）
        self._setup_title_bar()
        self._update_styles()

        # 监听主题变化
        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        # 顶部边距40px为标题栏留出空间
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)

        # 提示文本（基类统一处理文字颜色）
        info_label = QLabel(tr('dialogs.update.new_version'))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        # 版本信息（基类统一处理文字颜色）
        version_label = QLabel(tr('dialogs.update.version_info', current=self.current_version, latest=self.latest_version))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        layout.addStretch()

        # 按钮区域
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        buttons_layout.addStretch()

        # 发行页面按钮
        release_button = PushButton(tr('dialogs.update.release_page'))
        release_button.setMinimumWidth(90)
        release_button.clicked.connect(self.open_release_page)
        buttons_layout.addWidget(release_button)

        # 下载按钮（主题色）
        download_button = PrimaryPushButton(tr('dialogs.update.download'))
        download_button.setMinimumWidth(90)
        download_button.clicked.connect(self.on_download_clicked)
        buttons_layout.addWidget(download_button)

        buttons_layout.addStretch()

        layout.addWidget(buttons_container)

    def on_download_clicked(self):
        """处理下载按钮点击"""
        if self.download_url:
            QDesktopServices.openUrl(QUrl(self.download_url))
        else:
            # 降级到发行页面
            self.open_release_page()
        self.accept()

    def open_release_page(self):
        """打开 Gitee 发行版页面"""
        if self.latest_version:
            url = f"https://gitee.com/qingshangongzai/color_card/releases/tag/{self.latest_version}"
        else:
            url = "https://gitee.com/qingshangongzai/color_card/releases"
        QDesktopServices.openUrl(QUrl(url))
        self.accept()

    def closeEvent(self, event):
        """关闭事件"""
        super().closeEvent(event)  # 基类处理信号断开

    @staticmethod
    def check_update(parent, current_version):
        """检查更新并显示相应提示

        Args:
            parent: 父窗口对象
            current_version: 当前版本号
        """
        # 创建并启动检查线程
        UpdateAvailableDialog._check_thread = UpdateCheckThread(current_version)

        def on_check_finished(success, latest_version, error_msg, download_url):
            if success:
                result = compare_versions(current_version, latest_version)
                if result >= 0:
                    # 当前版本已是最新
                    InfoBar.info(
                        title=tr('dialogs.update.info'),
                        content=tr('dialogs.update.latest_version'),
                        parent=parent,
                        duration=3000,
                        position=InfoBarPosition.TOP,
                    )
                else:
                    # 有新版本可用，显示对话框
                    # 使用 window() 获取顶层窗口，确保无边框对话框正常显示
                    top_parent = parent.window() if parent else None
                    dialog = UpdateAvailableDialog(top_parent, current_version, latest_version, download_url)
                    dialog.exec()
            else:
                InfoBar.warning(
                    title=tr('dialogs.update.check_failed'),
                    content=error_msg,
                    parent=parent,
                    duration=5000,
                    position=InfoBarPosition.TOP,
                )

        UpdateAvailableDialog._check_thread.check_finished.connect(on_check_finished)
        UpdateAvailableDialog._check_thread.start()
