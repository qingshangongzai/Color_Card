"""版本管理测试

测试 VersionManager 的构建信息解析回退链（build_info → git → dev）与展示版本号格式。
"""

# 标准库导入
import sys
import types
from unittest.mock import patch

# 第三方库导入
import pytest

# 项目模块导入
from version import VersionManager


class TestResolveBuildInfo:
    """构建信息解析回退链测试"""

    def test_build_info_file_precedence(self):
        """build_info.py 存在时优先使用固化值，不查询 git"""
        fake = types.ModuleType("build_info")
        fake.BUILD_NUMBER = "1260"
        fake.COMMIT_SHA = "deadbeef"
        with patch.dict(sys.modules, {"build_info": fake}):
            vm = VersionManager()

        assert vm.build_number == "1260"
        assert vm.commit_sha == "deadbeef"

    def test_build_info_incomplete_falls_back_to_git(self):
        """build_info.py 缺少字段时回退 git 查询"""
        fake = types.ModuleType("build_info")
        fake.BUILD_NUMBER = "1"

        def fake_run(args, **kwargs):
            if "rev-list" in args:
                return types.SimpleNamespace(stdout="1258\n")
            return types.SimpleNamespace(stdout="0f01bca2\n")

        with patch.dict(sys.modules, {"build_info": fake}), \
             patch("version.subprocess.run", side_effect=fake_run):
            vm = VersionManager()

        assert vm.build_number == "1258"
        assert vm.commit_sha == "0f01bca2"

    def test_git_unavailable_falls_back_to_dev(self):
        """git 不可用时回退 ("dev", "")"""
        with patch.dict(sys.modules, {"build_info": None}), \
             patch("version.subprocess.run", side_effect=OSError("git not found")):
            vm = VersionManager()

        assert vm.build_number == "dev"
        assert vm.commit_sha == ""


class TestDisplayVersion:
    """展示版本号格式测试"""

    def test_display_version_stable_release(self):
        """正式版展示格式为 X.Y.Z.构建号"""
        vm = VersionManager()
        vm.build_number = "526"
        assert vm.get_display_version() == "1.11.0.526"

    def test_display_version_prerelease(self):
        """预发布版展示格式为 X.Y.Z-betaN.构建号"""
        vm = VersionManager()
        vm.version = "1.11.0-beta1"
        vm.build_number = "526"
        assert vm.get_display_version() == "1.11.0-beta1.526"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
