from __future__ import annotations
# 标准库导入
import base64
import json
import re
from dataclasses import dataclass

# 第三方库导入
import requests
from PySide6.QtCore import QThread, Signal

# 项目模块导入
from utils import tr
from core import get_app_mode, get_platform, AppMode, Platform


@dataclass
class UpdateInfo:
    """更新信息"""
    latest_version: str
    download_url: str
    changelog: list[dict]


@dataclass
class CheckResult:
    """更新检查结果"""
    success: bool
    has_update: bool
    info: UpdateInfo | None = None
    error_message: str = ""
    current_version: str = ""


_PRE_RELEASE_ORDER = {"alpha": -3, "beta": -2, "rc": -1}


def _parse_version(version_str: str) -> tuple[list[int], int, int]:
    """解析版本号

    Args:
        version_str: 版本号字符串

    Returns:
        tuple[list[int], int, int]: (版本号数字列表, 预发布标识, 预发布版本号)
        预发布标识: 0=正式版, -1=RC, -2=Beta, -3=Alpha
        预发布版本号: Beta1/Beta2等后面的数字，默认0
    """
    version_str = version_str.lstrip("v").lower()

    if " · " in version_str:
        main_part, pre_part = version_str.split(" · ", 1)
    elif " " in version_str:
        main_part, pre_part = version_str.split(" ", 1)
    else:
        main_part = version_str
        pre_part = ""
        for keyword in _PRE_RELEASE_ORDER:
            if keyword in version_str:
                idx = version_str.find(keyword)
                main_part = version_str[:idx]
                pre_part = version_str[idx:]
                break

    parts = re.findall(r"\d+", main_part)
    nums = [int(p) for p in parts] if parts else [0]

    pre_release = 0
    pre_release_num = 0
    for keyword, value in _PRE_RELEASE_ORDER.items():
        if keyword in pre_part:
            pre_release = value
            match = re.search(rf"{keyword}\s*(\d+)", pre_part)
            if match:
                pre_release_num = int(match.group(1))
            break

    return nums, pre_release, pre_release_num


def _compare_versions(current: str, latest: str) -> int:
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


def _format_changelog(changelog_data: dict, current_version: str, latest_version: str) -> list[dict]:
    """格式化更新日志

    Args:
        changelog_data: changelog.json 解析后的数据
        current_version: 当前版本号
        latest_version: 最新版本号

    Returns:
        list[dict]: 版本信息列表
    """
    versions = changelog_data.get("versions", [])

    _, latest_pre, _ = _parse_version(latest_version)
    latest_is_release = (latest_pre == 0)

    versions_to_show = []
    for version_info in versions:
        version_str = version_info.get("version", "").lstrip("v")
        if _compare_versions(current_version, version_str) >= 0:
            continue

        if latest_is_release:
            _, pre_release, _ = _parse_version(version_str)
            if pre_release != 0:
                continue

        versions_to_show.append(version_info)

    return versions_to_show


class _ReleaseSource:
    """Release 源抽象基类"""

    def fetch_release(self) -> dict:
        """获取最新 Release 数据

        Returns:
            dict: 统一格式的 Release 数据 {"version": str, "assets": list[dict]}
        """
        raise NotImplementedError

    def fetch_changelog(self, current_version: str, latest_version: str) -> list[dict]:
        """获取更新日志

        Args:
            current_version: 当前版本号
            latest_version: 最新版本号

        Returns:
            list[dict]: 版本信息列表
        """
        raise NotImplementedError


class _GiteaSource(_ReleaseSource):
    """Gitea 类平台源（Gitee / GitCode）"""

    def __init__(self, release_url: str, changelog_urls: list[str]):
        self._release_url = release_url
        self._changelog_urls = changelog_urls

    def fetch_release(self) -> dict:
        response = requests.get(self._release_url, timeout=8)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")

        data = response.json()
        return {
            "version": data.get("tag_name", "").lstrip("v"),
            "assets": data.get("assets", []),
        }

    def fetch_changelog(self, current_version: str, latest_version: str) -> list[dict]:
        for url in self._changelog_urls:
            try:
                response = requests.get(url, timeout=8)
                if response.status_code != 200:
                    continue

                data = response.json()
                content = data.get("content", "")
                json_content = base64.b64decode(content).decode("utf-8")
                changelog_data = json.loads(json_content)

                return _format_changelog(changelog_data, current_version, latest_version)

            except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, base64.binascii.Error):
                continue

        return []


class _GitHubSource(_ReleaseSource):
    """GitHub 平台源"""

    _RELEASE_URL = "https://api.github.com/repos/qingshangongzai/Color_Card/releases/latest"
    _CHANGELOG_URLS = [
        "https://raw.githubusercontent.com/qingshangongzai/Color_Card/main/app_log/changelog.json",
        "https://raw.githubusercontent.com/qingshangongzai/Color_Card/main/docs/changelog.json",
    ]

    def fetch_release(self) -> dict:
        response = requests.get(self._RELEASE_URL, timeout=8)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")

        data = response.json()
        return {
            "version": data.get("tag_name", "").lstrip("v"),
            "assets": data.get("assets", []),
        }

    def fetch_changelog(self, current_version: str, latest_version: str) -> list[dict]:
        for url in self._CHANGELOG_URLS:
            try:
                response = requests.get(url, timeout=8)
                if response.status_code != 200:
                    continue

                changelog_data = response.json()
                return _format_changelog(changelog_data, current_version, latest_version)

            except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError):
                continue

        return []


_SOURCES: list[_ReleaseSource] = [
    _GiteaSource(
        "https://gitee.com/api/v5/repos/HxiaoStudio/Color_Card/releases/latest",
        [
            "https://gitee.com/api/v5/repos/HxiaoStudio/Color_Card/contents/app_log/changelog.json?ref=main",
            "https://gitee.com/api/v5/repos/HxiaoStudio/Color_Card/contents/docs/changelog.json?ref=main",
        ],
    ),
    _GiteaSource(
        "https://gitcode.com/api/v5/repos/HxiaoStudio/Color_Card/releases/latest",
        [
            "https://gitcode.com/api/v5/repos/HxiaoStudio/Color_Card/contents/app_log/changelog.json?ref=main",
            "https://gitcode.com/api/v5/repos/HxiaoStudio/Color_Card/contents/docs/changelog.json?ref=main",
        ],
    ),
    _GitHubSource(),
]


class _AssetSelector:
    """安装包选择器"""

    def select(self, assets: list[dict]) -> str:
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

            if platform == Platform.MACOS and name.endswith(".dmg"):
                return url

            if platform == Platform.WINDOWS:
                if mode == AppMode.INSTALLED and "setup" in name and name.endswith(".exe"):
                    return url
                if mode != AppMode.INSTALLED and name.endswith("x64.exe") and "setup" not in name:
                    return url

        return assets[0].get("browser_download_url", "") if assets else ""


class UpdateChecker(QThread):
    """检查更新的后台线程"""

    check_finished = Signal(CheckResult)

    def __init__(self, current_version: str):
        super().__init__()
        self._current_version = current_version

    def run(self):
        """在后台线程中检查更新"""
        last_error = ""

        for source in _SOURCES:
            try:
                release = source.fetch_release()
                latest_version = release.get("version", "")

                if not latest_version:
                    last_error = tr("dialogs.update.error_parse_version")
                    continue

                download_url = _AssetSelector().select(release.get("assets", []))
                changelog = source.fetch_changelog(self._current_version, latest_version)

                has_update = _compare_versions(self._current_version, latest_version) < 0
                info = UpdateInfo(latest_version, download_url, changelog)

                self.check_finished.emit(
                    CheckResult(True, has_update, info=info, current_version=self._current_version)
                )
                return

            except requests.exceptions.Timeout:
                last_error = tr("dialogs.update.error_timeout")
            except requests.exceptions.ConnectionError:
                last_error = tr("dialogs.update.error_connection")
            except requests.exceptions.HTTPError:
                last_error = tr("dialogs.update.error_http", status_code="")
            except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
                last_error = tr("dialogs.update.error_general", error=str(e))

        self.check_finished.emit(CheckResult(False, False, error_message=last_error))


class UpdateService:
    """更新服务，协调检查更新流程"""

    def __init__(self):
        self._checker: UpdateChecker | None = None

    def check_update(self, parent, current_version: str):
        """检查更新并显示相应提示

        Args:
            parent: 父窗口对象
            current_version: 当前版本号
        """
        self._checker = UpdateChecker(current_version)
        self._checker.check_finished.connect(
            lambda result: self._on_check_finished(result, parent)
        )
        self._checker.start()

    def _on_check_finished(self, result: CheckResult, parent):
        """处理检查结果

        Args:
            result: 检查结果
            parent: 父窗口对象
        """
        from qfluentwidgets import InfoBar, InfoBarPosition
        from dialogs import UpdateAvailableDialog

        if not result.success:
            InfoBar.warning(
                title=tr("dialogs.update.check_failed"),
                content=result.error_message,
                parent=parent,
                duration=5000,
                position=InfoBarPosition.TOP,
            )
            return

        if not result.has_update:
            InfoBar.success(
                title=tr("dialogs.update.info"),
                content=tr("dialogs.update.latest_version"),
                parent=parent,
                duration=3000,
                position=InfoBarPosition.TOP,
            )
            return

        info = result.info
        if info is None:
            return

        top_parent = parent.window() if parent else None
        dialog = UpdateAvailableDialog(
            top_parent,
            current_version=result.current_version,
            latest_version=info.latest_version,
            download_url=info.download_url,
            changelog=info.changelog,
        )
        dialog.exec()
