from __future__ import annotations
import sys
import unittest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

sys.path.insert(0, '.')


class TestParseVersion(unittest.TestCase):
    """测试版本解析函数"""

    def test_parse_simple_version(self):
        """测试简单版本号解析"""
        from core.update_service import _parse_version

        nums, pre, pre_num = _parse_version("1.0.0")
        self.assertEqual(nums, [1, 0, 0])
        self.assertEqual(pre, 0)
        self.assertEqual(pre_num, 0)

    def test_parse_version_with_v_prefix(self):
        """测试带 v 前缀的版本号"""
        from core.update_service import _parse_version

        nums, pre, pre_num = _parse_version("v2.1.3")
        self.assertEqual(nums, [2, 1, 3])
        self.assertEqual(pre, 0)
        self.assertEqual(pre_num, 0)

    def test_parse_alpha_version(self):
        """测试 Alpha 版本解析"""
        from core.update_service import _parse_version

        nums, pre, pre_num = _parse_version("1.0.0-alpha")
        self.assertEqual(nums, [1, 0, 0])
        self.assertEqual(pre, -3)
        self.assertEqual(pre_num, 0)

    def test_parse_alpha_with_number(self):
        """测试带数字的 Alpha 版本"""
        from core.update_service import _parse_version

        nums, pre, pre_num = _parse_version("1.0.0-alpha2")
        self.assertEqual(nums, [1, 0, 0])
        self.assertEqual(pre, -3)
        self.assertEqual(pre_num, 2)

    def test_parse_beta_version(self):
        """测试 Beta 版本解析"""
        from core.update_service import _parse_version

        nums, pre, pre_num = _parse_version("1.0.0-beta1")
        self.assertEqual(nums, [1, 0, 0])
        self.assertEqual(pre, -2)
        self.assertEqual(pre_num, 1)

    def test_parse_rc_version(self):
        """测试 RC 版本解析"""
        from core.update_service import _parse_version

        nums, pre, pre_num = _parse_version("1.0.0-rc3")
        self.assertEqual(nums, [1, 0, 0])
        self.assertEqual(pre, -1)
        self.assertEqual(pre_num, 3)

    def test_parse_version_with_dot_separator(self):
        """测试使用 · 分隔符的版本号"""
        from core.update_service import _parse_version

        nums, pre, pre_num = _parse_version("1.0.0 · Beta1")
        self.assertEqual(nums, [1, 0, 0])
        self.assertEqual(pre, -2)
        self.assertEqual(pre_num, 1)

    def test_parse_version_with_space_separator(self):
        """测试使用空格分隔符的版本号"""
        from core.update_service import _parse_version

        nums, pre, pre_num = _parse_version("1.0.0 RC2")
        self.assertEqual(nums, [1, 0, 0])
        self.assertEqual(pre, -1)
        self.assertEqual(pre_num, 2)


class TestCompareVersions(unittest.TestCase):
    """测试版本比较函数"""

    def test_same_versions(self):
        """测试相同版本"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0", "1.0.0")
        self.assertEqual(result, 0)

    def test_current_older_major(self):
        """测试主版本号更旧"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0", "2.0.0")
        self.assertEqual(result, -1)

    def test_current_older_minor(self):
        """测试次版本号更旧"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0", "1.1.0")
        self.assertEqual(result, -1)

    def test_current_older_patch(self):
        """测试补丁版本号更旧"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0", "1.0.1")
        self.assertEqual(result, -1)

    def test_current_newer(self):
        """测试当前版本更新"""
        from core.update_service import _compare_versions

        result = _compare_versions("2.0.0", "1.0.0")
        self.assertEqual(result, 1)

    def test_release_vs_alpha(self):
        """测试正式版比 Alpha 新"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0", "1.0.0-alpha")
        self.assertEqual(result, 1)

    def test_alpha_vs_beta(self):
        """测试 Alpha 比 Beta 旧"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0-alpha", "1.0.0-beta")
        self.assertEqual(result, -1)

    def test_beta_vs_rc(self):
        """测试 Beta 比 RC 旧"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0-beta", "1.0.0-rc")
        self.assertEqual(result, -1)

    def test_rc_vs_release(self):
        """测试 RC 比正式版旧"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0-rc", "1.0.0")
        self.assertEqual(result, -1)

    def test_alpha1_vs_alpha2(self):
        """测试 Alpha1 比 Alpha2 旧"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0.0-alpha1", "1.0.0-alpha2")
        self.assertEqual(result, -1)

    def test_different_length_versions(self):
        """测试不同长度的版本号"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.0", "1.0.1")
        self.assertEqual(result, -1)

    def test_complex_version_comparison(self):
        """测试复杂版本比较"""
        from core.update_service import _compare_versions

        result = _compare_versions("1.9.0", "1.10.0")
        self.assertEqual(result, -1)


class TestChangelogFetcherFormat(unittest.TestCase):
    """测试更新日志格式化"""

    def test_format_filters_old_versions(self):
        """测试过滤旧版本"""
        from core.update_service import _ChangelogFetcher

        fetcher = _ChangelogFetcher()
        changelog_data = {
            "versions": [
                {"version": "1.0.0", "date": "2024-01-01", "changes": []},
                {"version": "1.1.0", "date": "2024-02-01", "changes": []},
                {"version": "1.2.0", "date": "2024-03-01", "changes": []},
            ]
        }

        result = fetcher._format(changelog_data, "1.0.0", "1.2.0")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["version"], "1.1.0")
        self.assertEqual(result[1]["version"], "1.2.0")

    def test_format_filters_pre_release_when_latest_is_release(self):
        """测试正式版发布时过滤预发布版本"""
        from core.update_service import _ChangelogFetcher

        fetcher = _ChangelogFetcher()
        changelog_data = {
            "versions": [
                {"version": "1.0.0", "date": "2024-01-01", "changes": []},
                {"version": "1.1.0-beta1", "date": "2024-02-01", "changes": []},
                {"version": "1.1.0", "date": "2024-03-01", "changes": []},
            ]
        }

        result = fetcher._format(changelog_data, "1.0.0", "1.1.0")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["version"], "1.1.0")

    def test_format_includes_pre_release_when_latest_is_pre_release(self):
        """测试预发布版本时包含预发布版本"""
        from core.update_service import _ChangelogFetcher

        fetcher = _ChangelogFetcher()
        changelog_data = {
            "versions": [
                {"version": "1.0.0", "date": "2024-01-01", "changes": []},
                {"version": "1.1.0-alpha1", "date": "2024-02-01", "changes": []},
                {"version": "1.1.0-beta1", "date": "2024-03-01", "changes": []},
            ]
        }

        result = fetcher._format(changelog_data, "1.0.0", "1.1.0-beta1")

        self.assertEqual(len(result), 2)

    def test_format_empty_changelog(self):
        """测试空更新日志"""
        from core.update_service import _ChangelogFetcher

        fetcher = _ChangelogFetcher()
        changelog_data = {"versions": []}

        result = fetcher._format(changelog_data, "1.0.0", "1.1.0")

        self.assertEqual(result, [])

    def test_format_all_versions_current(self):
        """测试所有版本都是当前版本"""
        from core.update_service import _ChangelogFetcher

        fetcher = _ChangelogFetcher()
        changelog_data = {
            "versions": [
                {"version": "1.0.0", "date": "2024-01-01", "changes": []},
                {"version": "1.1.0", "date": "2024-02-01", "changes": []},
            ]
        }

        result = fetcher._format(changelog_data, "1.1.0", "1.1.0")

        self.assertEqual(result, [])


class TestAssetSelector(unittest.TestCase):
    """测试安装包选择器"""

    def test_select_windows_installed_mode(self):
        """测试 Windows 安装模式选择"""
        from core.update_service import _AssetSelector

        assets = [
            {"name": "color_card_1.0.0_x64.exe", "browser_download_url": "url_portable"},
            {"name": "color_card_1.0.0_setup.exe", "browser_download_url": "url_setup"},
        ]

        with patch('core.update_service.get_app_mode', return_value=MagicMock(INSTALLED=True)):
            with patch('core.update_service.get_platform', return_value=MagicMock(WINDOWS=True, MACOS=False)):
                with patch('core.update_service.AppMode') as mock_mode:
                    with patch('core.update_service.Platform') as mock_platform:
                        mock_mode.INSTALLED = MagicMock()
                        mock_mode.INSTALLED = True
                        mock_platform.WINDOWS = True
                        mock_platform.MACOS = False

                        selector = _AssetSelector()
                        result = selector.select(assets)

        self.assertEqual(result, "url_portable")

    def test_select_empty_assets(self):
        """测试空资源列表"""
        from core.update_service import _AssetSelector

        selector = _AssetSelector()
        result = selector.select([])

        self.assertEqual(result, "")

    def test_select_fallback_to_first(self):
        """测试回退到第一个资源"""
        from core.update_service import _AssetSelector

        assets = [
            {"name": "unknown_file.zip", "browser_download_url": "url_first"},
        ]

        with patch('core.update_service.get_app_mode') as mock_mode:
            with patch('core.update_service.get_platform') as mock_platform:
                with patch('core.update_service.AppMode'):
                    with patch('core.update_service.Platform') as mock_p:
                        mock_p.WINDOWS = False
                        mock_p.MACOS = False

                        selector = _AssetSelector()
                        result = selector.select(assets)

        self.assertEqual(result, "url_first")


class TestDataClasses(unittest.TestCase):
    """测试数据类"""

    def test_update_info_creation(self):
        """测试 UpdateInfo 创建"""
        from core.update_service import UpdateInfo

        info = UpdateInfo(
            latest_version="1.1.0",
            download_url="https://example.com/download",
            changelog=[{"version": "1.1.0"}]
        )

        self.assertEqual(info.latest_version, "1.1.0")
        self.assertEqual(info.download_url, "https://example.com/download")
        self.assertEqual(len(info.changelog), 1)

    def test_check_result_creation(self):
        """测试 CheckResult 创建"""
        from core.update_service import CheckResult, UpdateInfo

        info = UpdateInfo("1.1.0", "url", [])
        result = CheckResult(
            success=True,
            has_update=True,
            info=info,
            current_version="1.0.0"
        )

        self.assertTrue(result.success)
        self.assertTrue(result.has_update)
        self.assertEqual(result.current_version, "1.0.0")
        self.assertIsNotNone(result.info)

    def test_check_result_defaults(self):
        """测试 CheckResult 默认值"""
        from core.update_service import CheckResult

        result = CheckResult(success=False, has_update=False)

        self.assertIsNone(result.info)
        self.assertEqual(result.error_message, "")
        self.assertEqual(result.current_version, "")


class TestUpdateChecker(unittest.TestCase):
    """测试更新检查线程"""

    def test_check_success(self):
        """测试成功检查更新"""
        from PySide6.QtCore import QCoreApplication, QEventLoop
        from core.update_service import UpdateChecker, CheckResult

        app = QCoreApplication.instance() or QCoreApplication([])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v1.1.0",
            "assets": [
                {"name": "app_1.1.0_x64.exe", "browser_download_url": "https://example.com/download"}
            ]
        }

        results = []

        def on_finished(result: CheckResult):
            results.append(result)

        with patch('requests.get', return_value=mock_response):
            with patch('core.update_service._ChangelogFetcher.fetch', return_value=[]):
                with patch('core.update_service._AssetSelector.select', return_value="https://example.com/download"):
                    checker = UpdateChecker("1.0.0")
                    checker.check_finished.connect(on_finished)
                    checker.run()

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertTrue(results[0].has_update)
        self.assertEqual(results[0].current_version, "1.0.0")

    def test_check_no_update(self):
        """测试无更新"""
        from PySide6.QtCore import QCoreApplication
        from core.update_service import UpdateChecker, CheckResult

        app = QCoreApplication.instance() or QCoreApplication([])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v1.0.0",
            "assets": []
        }

        results = []

        def on_finished(result: CheckResult):
            results.append(result)

        with patch('requests.get', return_value=mock_response):
            with patch('core.update_service._ChangelogFetcher.fetch', return_value=[]):
                checker = UpdateChecker("1.0.0")
                checker.check_finished.connect(on_finished)
                checker.run()

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertFalse(results[0].has_update)

    def test_check_http_error(self):
        """测试 HTTP 错误"""
        from PySide6.QtCore import QCoreApplication
        from core.update_service import UpdateChecker, CheckResult

        app = QCoreApplication.instance() or QCoreApplication([])

        mock_response = MagicMock()
        mock_response.status_code = 404

        results = []

        def on_finished(result: CheckResult):
            results.append(result)

        with patch('requests.get', return_value=mock_response):
            checker = UpdateChecker("1.0.0")
            checker.check_finished.connect(on_finished)
            checker.run()

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertFalse(results[0].has_update)
        self.assertIn("error_http", results[0].error_message)

    def test_check_timeout(self):
        """测试超时错误"""
        from PySide6.QtCore import QCoreApplication
        from core.update_service import UpdateChecker, CheckResult
        import requests

        app = QCoreApplication.instance() or QCoreApplication([])

        results = []

        def on_finished(result: CheckResult):
            results.append(result)

        with patch('requests.get', side_effect=requests.exceptions.Timeout()):
            checker = UpdateChecker("1.0.0")
            checker.check_finished.connect(on_finished)
            checker.run()

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertFalse(results[0].has_update)

    def test_check_connection_error(self):
        """测试连接错误"""
        from PySide6.QtCore import QCoreApplication
        from core.update_service import UpdateChecker, CheckResult
        import requests

        app = QCoreApplication.instance() or QCoreApplication([])

        results = []

        def on_finished(result: CheckResult):
            results.append(result)

        with patch('requests.get', side_effect=requests.exceptions.ConnectionError()):
            checker = UpdateChecker("1.0.0")
            checker.check_finished.connect(on_finished)
            checker.run()

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)


class TestUpdateService(unittest.TestCase):
    """测试更新服务"""

    def test_service_creation(self):
        """测试服务创建"""
        from core.update_service import UpdateService

        service = UpdateService()
        self.assertIsNone(service._checker)

    def test_check_update_creates_checker(self):
        """测试检查更新创建检查器"""
        from PySide6.QtCore import QCoreApplication
        from core.update_service import UpdateService

        app = QCoreApplication.instance() or QCoreApplication([])

        mock_parent = MagicMock()

        with patch('core.update_service.UpdateChecker') as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker_class.return_value = mock_checker

            service = UpdateService()
            service.check_update(mock_parent, "1.0.0")

            mock_checker_class.assert_called_once_with("1.0.0")
            mock_checker.start.assert_called_once()
            self.assertEqual(service._checker, mock_checker)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestParseVersion))
    suite.addTests(loader.loadTestsFromTestCase(TestCompareVersions))
    suite.addTests(loader.loadTestsFromTestCase(TestChangelogFetcherFormat))
    suite.addTests(loader.loadTestsFromTestCase(TestAssetSelector))
    suite.addTests(loader.loadTestsFromTestCase(TestDataClasses))
    suite.addTests(loader.loadTestsFromTestCase(TestUpdateChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestUpdateService))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    run_tests()
