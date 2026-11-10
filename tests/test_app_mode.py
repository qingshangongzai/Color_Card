"""运行模式检测测试

测试 macOS 打包版的模式判定与配置目录，防止 .app 被判为便携版而把配置写进包内。
"""

# 标准库导入
import os
import sys
from pathlib import Path
from unittest.mock import patch

# 第三方库导入
import pytest

# 项目模块导入
from core import AppMode, detect_mode, get_config_dir

# 实现模块的全局命名空间：经公共导入的 detect_mode 反查，Dev/main 布局下是
# core.app_mode 自身，NEXT 布局下是根 app_mode；模式缓存与 __compiled__ 都在那里
_IMPL_GLOBALS = detect_mode.__globals__


@pytest.fixture(autouse=True)
def reset_mode_cache(monkeypatch):
    """重置模式缓存，避免测试间串用判定结果"""
    monkeypatch.setitem(_IMPL_GLOBALS, "_mode_cache", None)


def _fake_app_path(base_dir: Path) -> Path:
    """在指定目录下构造伪造的 .app 内可执行文件路径"""
    exe_path = base_dir / "ColorCard.app" / "Contents" / "MacOS" / "main"
    exe_path.parent.mkdir(parents=True)
    return exe_path


@pytest.mark.unit
def test_macos_packaged_returns_installed(tmp_path, monkeypatch):
    """macOS 打包版即使位于 TEMP 路径（模拟 App Translocation）也判为安装版"""
    translocation = tmp_path / "AppTranslocation"
    exe_path = _fake_app_path(translocation)

    monkeypatch.setattr(sys, "argv", [str(exe_path)])
    monkeypatch.setenv("TEMP", str(translocation))
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    temp_prefix = os.environ["TEMP"].lower()
    assert str(exe_path.resolve()).lower().startswith(temp_prefix)

    assert detect_mode() is AppMode.INSTALLED


@pytest.mark.unit
def test_macos_nuitka_compiled_returns_installed(tmp_path, monkeypatch):
    """Nuitka 打包版（无 sys.frozen，只有 __compiled__）判为安装版"""
    translocation = tmp_path / "AppTranslocation"
    exe_path = _fake_app_path(translocation)

    monkeypatch.setattr(sys, "argv", [str(exe_path)])
    monkeypatch.setenv("TEMP", str(translocation))
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setitem(_IMPL_GLOBALS, "__compiled__", True)

    temp_prefix = os.environ["TEMP"].lower()
    assert str(exe_path.resolve()).lower().startswith(temp_prefix)

    assert detect_mode() is AppMode.INSTALLED


@pytest.mark.unit
def test_macos_packaged_config_dir(tmp_path, monkeypatch):
    """macOS 打包版配置目录为用户目录下的 .color_card"""
    exe_path = _fake_app_path(tmp_path)

    monkeypatch.setattr(sys, "argv", [str(exe_path)])
    monkeypatch.delenv("TEMP", raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    with patch.object(Path, "home", return_value=tmp_path):
        assert detect_mode() is AppMode.INSTALLED
        assert get_config_dir() == tmp_path / ".color_card"


@pytest.mark.unit
def test_macos_source_returns_development(tmp_path, monkeypatch):
    """macOS 源码运行判为开发模式，配置目录为用户目录下的 .color_card"""
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert "__compiled__" not in _IMPL_GLOBALS
    monkeypatch.setattr(sys, "argv", [str(tmp_path / "main.py")])
    monkeypatch.setattr(sys, "platform", "darwin")

    with patch.object(Path, "home", return_value=tmp_path):
        assert detect_mode() is AppMode.DEVELOPMENT
        assert get_config_dir() == tmp_path / ".color_card"


def _prepare_portable_env(monkeypatch, tmp_path: Path) -> None:
    """隔离 Windows 环境变量，避免临时目录被判为安装程序或安装版"""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setitem(_IMPL_GLOBALS, "_check_registry_install", lambda: None)
    for name in ("TEMP", "PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        monkeypatch.setenv(name, str(tmp_path / f"fake_{name.lower().replace('(', '_').replace(')', '')}"))


@pytest.mark.unit
def test_windows_portable_app_layout_config_dir(tmp_path, monkeypatch):
    """便携版 app/ 布局：配置目录落在解压根目录，而不是 app/ 子目录"""
    root = tmp_path / "portable"
    app_dir = root / "app"
    app_dir.mkdir(parents=True)
    (app_dir / _IMPL_GLOBALS["PORTABLE_LAYOUT_MARKER"]).touch()
    exe_path = app_dir / "Color Card.exe"
    exe_path.touch()

    _prepare_portable_env(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", [str(exe_path)])

    assert detect_mode() is AppMode.PORTABLE
    assert get_config_dir() == root / "config"


@pytest.mark.unit
def test_windows_portable_flat_config_dir(tmp_path, monkeypatch):
    """便携版平铺布局：配置目录保持在程序所在目录"""
    root = tmp_path / "portable"
    root.mkdir()
    exe_path = root / "Color Card.exe"
    exe_path.touch()

    _prepare_portable_env(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", [str(exe_path)])

    assert detect_mode() is AppMode.PORTABLE
    assert get_config_dir() == root / "config"
