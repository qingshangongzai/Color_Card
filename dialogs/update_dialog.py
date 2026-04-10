# 标准库导入
import base64
import json
import re
from typing import Dict, List, Tuple

# 第三方库导入
import requests
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, PrimaryPushButton, PushButton, ScrollArea, isDarkTheme, qconfig

# 项目模块导入
from utils import tr, load_icon_universal
from dialogs import BaseFramelessDialog
from core import get_app_mode, get_platform, AppMode, Platform


class UpdateCheckThread(QThread):
    """检查更新的后台线程

    在后台线程中检查 Gitee 仓库的最新版本信息，
    避免阻塞主线程。
    """

    check_finished = Signal(bool, str, str, str, str)

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
            # 获取最新 Release 信息
            api_url = "https://gitee.com/api/v5/repos/qingshangongzai/Color_Card/releases/latest"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").lstrip("v")
                download_url = self._select_asset(data.get("assets", []))

                # 获取 changelog.json 内容
                changelog_content = self._fetch_changelog(self.current_version, latest_version)

                if latest_version:
                    self.check_finished.emit(True, latest_version, "", download_url, changelog_content)
                else:
                    self.check_finished.emit(False, "", tr('dialogs.update.error_parse_version'), "", "")
            else:
                self.check_finished.emit(
                    False, "", tr('dialogs.update.error_http', status_code=response.status_code), "", ""
                )

        except requests.exceptions.Timeout:
            self.check_finished.emit(False, "", tr('dialogs.update.error_timeout'), "", "")
        except requests.exceptions.ConnectionError:
            self.check_finished.emit(False, "", tr('dialogs.update.error_connection'), "", "")
        except Exception as e:
            self.check_finished.emit(False, "", tr('dialogs.update.error_general', error=str(e)), "", "")

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

    def _fetch_changelog(self, current_version: str, latest_version: str) -> str:
        """从 Gitee 获取 changelog.json 并提取更新日志

        Args:
            current_version: 当前版本号
            latest_version: 最新版本号

        Returns:
            str: 格式化后的更新日志内容
        """
        try:
            # 获取 changelog.json 文件内容
            changelog_url = "https://gitee.com/api/v5/repos/qingshangongzai/Color_Card/contents/docs/changelog.json?ref=main"
            response = requests.get(changelog_url, timeout=10)

            if response.status_code != 200:
                return ""

            data = response.json()
            content = data.get("content", "")

            # Base64 解码
            json_content = base64.b64decode(content).decode('utf-8')
            changelog_data = json.loads(json_content)

            return self._format_changelog(changelog_data, current_version)

        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError):
            return ""

    def _format_changelog(self, changelog_data: Dict, current_version: str) -> str:
        """格式化更新日志

        Args:
            changelog_data: changelog.json 解析后的数据
            current_version: 当前版本号

        Returns:
            str: 格式化后的 Markdown 字符串
        """
        versions = changelog_data.get("versions", [])
        if not versions:
            return ""

        # 收集需要显示的版本（从当前版本之后到最新版本）
        versions_to_show = []
        for version_info in versions:
            version_str = version_info.get("version", "").lstrip("v")

            # 只显示比当前版本新的版本
            if compare_versions(current_version, version_str) < 0:
                versions_to_show.append(version_info)

        if not versions_to_show:
            return ""

        # 格式化输出
        lines = []
        for i, version_info in enumerate(versions_to_show):
            version_str = version_info.get("version", "")
            date = version_info.get("date", "")
            changes = version_info.get("changes", [])

            # 版本之间添加分隔线（第一个版本除外）
            if i > 0:
                lines.append("---")

            lines.append(f"## {version_str} ({date})")

            for change in changes:
                category = change.get("category", "")
                items = change.get("items", [])

                lines.append(f"**{category}**")

                for item in items:
                    if isinstance(item, str):
                        lines.append(f"- {item}")
                    elif isinstance(item, dict):
                        title = item.get("title", "")
                        desc = item.get("desc", "")
                        lines.append(f"- **{title}**: {desc}")

        return "\n".join(lines)


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

    # 分离主版本号和预发布部分（处理 · 符号）
    # "1.7.0 · beta 1" -> main_part="1.7.0", pre_part="beta 1"
    if " · " in version_str:
        main_part, pre_part = version_str.split(" · ", 1)
    else:
        main_part = version_str
        pre_part = ""

    # 提取主版本号的数字
    parts = re.findall(r"\d+", main_part)
    nums = [int(p) for p in parts] if parts else [0]

    # 解析预发布标识
    pre_release = 0
    pre_release_num = 0
    for keyword, value in _PRE_RELEASE_ORDER.items():
        if keyword in pre_part:
            pre_release = value
            # 支持 "beta1" 和 "beta 1" 两种格式
            match = re.search(rf"{keyword}\s*(\d+)", pre_part)
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

    def __init__(self, parent=None, current_version="", latest_version="", download_url="", changelog=""):
        """初始化新版本提示对话框

        Args:
            parent: 父窗口对象
            current_version: 当前版本号
            latest_version: 最新版本号
            download_url: 下载链接
            changelog: 更新日志内容
        """
        super().__init__(parent)
        self.setWindowTitle(tr('dialogs.update.title'))
        self.setFixedSize(700, 550)
        self.current_version = current_version
        self.latest_version = latest_version
        self.download_url = download_url
        self.changelog = changelog

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

    def _markdown_to_html(self, markdown_text: str) -> str:
        """将 Markdown 文本转换为 HTML

        Args:
            markdown_text: Markdown 格式的文本

        Returns:
            str: HTML 格式的文本
        """
        text_color = "#ffffff" if isDarkTheme() else "#333333"
        lines = markdown_text.split('\n')
        html_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                html_lines.append('<br>')
                continue

            # 处理分隔线
            if line == '---':
                html_lines.append(f'<hr style="border: none; border-top: 1px solid rgba(128, 128, 128, 0.3); margin: 10px 0;">')
                continue

            # 处理标题 (## 标题)
            if line.startswith('## '):
                title = line[3:]
                html_lines.append(f'<h2 style="margin: 15px 0 10px 0; font-size: 18px; font-weight: bold; color: {text_color};">{title}</h2>')
                continue

            # 处理粗体 (**文本**)
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)

            # 处理列表项 (- 文本)
            if line.startswith('- '):
                item_text = line[2:]
                html_lines.append(f'<div style="margin: 5px 0 5px 20px; color: {text_color};">• {item_text}</div>')
                continue

            # 普通文本
            html_lines.append(f'<div style="margin: 5px 0; color: {text_color};">{line}</div>')

        return ''.join(html_lines)

    def _update_styles(self):
        """更新样式以适配主题"""
        super()._update_styles()

        # 更新更新日志标签样式
        if hasattr(self, 'changelog_label') and self.changelog_label:
            text_color = "#ffffff" if isDarkTheme() else "#333333"
            self.changelog_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {text_color};
                    padding: 5px;
                }}
            """)

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

        # 更新日志区域
        if self.changelog:
            # 创建 ScrollArea 包装 QLabel
            scroll_area = ScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setMinimumHeight(300)
            scroll_area.setStyleSheet("""
                ScrollArea {
                    background-color: transparent;
                    border: none;
                }
                ScrollArea > QWidget > QWidget {
                    background-color: transparent;
                }
            """)

            # 设置滚动条角落为透明（防止出现灰色方块）
            corner_widget = QWidget()
            corner_widget.setStyleSheet("background: transparent;")
            scroll_area.setCornerWidget(corner_widget)

            # 将 Markdown 转换为 HTML
            html_content = self._markdown_to_html(self.changelog)

            # 创建 QLabel 显示 HTML 内容
            self.changelog_label = QLabel()
            self.changelog_label.setTextFormat(Qt.TextFormat.RichText)
            self.changelog_label.setText(html_content)
            self.changelog_label.setWordWrap(True)
            self.changelog_label.setOpenExternalLinks(True)
            self.changelog_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            # 设置透明背景和文字颜色
            text_color = "#ffffff" if isDarkTheme() else "#333333"
            self.changelog_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {text_color};
                    padding: 5px;
                }}
            """)

            scroll_area.setWidget(self.changelog_label)
            layout.addWidget(scroll_area, stretch=1)

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
            url = f"https://gitee.com/qingshangongzai/Color_Card/releases/tag/{self.latest_version}"
        else:
            url = "https://gitee.com/qingshangongzai/Color_Card/releases"
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

        def on_check_finished(success, latest_version, error_msg, download_url, changelog=""):
            if success:
                result = compare_versions(current_version, latest_version)
                if result >= 0:
                    # 当前版本已是最新
                    InfoBar.success(
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
                    dialog = UpdateAvailableDialog(top_parent, current_version, latest_version, download_url, changelog)
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
