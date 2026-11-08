"""安装部署流程测试

覆盖载荷选择性解压（app/ 平铺、跳过 .portable 与根启动器）、清空前护栏、
清空重试与部署流程编排。
"""

# 标准库导入
import shutil
import time
import zipfile
from pathlib import Path

# 第三方库导入
import pytest

# 项目模块导入
from installer.core import install_service
from installer.core.file_installer import FileInstaller
from installer.core.install_service import CLEAR_RETRY_TIMES, InstallWorker


def make_payload_zip(zip_path: Path) -> None:
    """构造模拟载荷：根启动器 + app/ 子树 + 布局标记

    Args:
        zip_path: 载荷 zip 输出路径
    """
    entries = {
        "Color Card.exe": b"LAUNCHER",   # 根启动器条目，解压时应排除
        "app/.portable": b"MARKER",      # 布局标记，解压时应排除
        "app/Color Card.exe": b"MAIN-EXE",
        "app/locales/zh.toml": b"LOCALE",
        "app/PySide6/QtCore.pyd": b"PYD",
    }
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


class TestExtractPayload:
    """FileInstaller.extract_payload 测试"""

    @pytest.mark.unit
    def test_extract_flattens_app_entries(self, tmp_path):
        """app/ 前缀条目平铺到目标目录，根启动器与 .portable 被排除"""
        payload = tmp_path / "payload.zip"
        make_payload_zip(payload)
        dst = tmp_path / "install"

        assert FileInstaller.extract_payload(payload, dst) is True

        assert (dst / "Color Card.exe").read_bytes() == b"MAIN-EXE"
        assert (dst / "locales" / "zh.toml").read_bytes() == b"LOCALE"
        assert (dst / "PySide6" / "QtCore.pyd").read_bytes() == b"PYD"
        assert not (dst / ".portable").exists()

    @pytest.mark.unit
    def test_extract_progress_denominator_excludes_skipped_entries(self, tmp_path):
        """进度分母只含实际解压字节，百分比单调不下降且收尾前到 100"""
        payload = tmp_path / "payload.zip"
        make_payload_zip(payload)
        dst = tmp_path / "install"
        calls: list[tuple[int, str]] = []

        FileInstaller.extract_payload(payload, dst, lambda p, m: calls.append((p, m)))

        assert calls[0][0] == 0
        assert calls[-1][0] == 100
        # 实际解压字节 8+6+3=17；若分母混入被跳过条目，最后一个文件解压完到不了 100
        assert calls[-2][0] == 100
        percents = [p for p, _ in calls]
        assert percents == sorted(percents)
        assert all(0 <= p <= 100 for p in percents)

    @pytest.mark.unit
    def test_extract_failure_returns_false(self, tmp_path):
        """载荷缺失、损坏或没有 app/ 条目时返回 False"""
        assert FileInstaller.extract_payload(tmp_path / "missing.zip", tmp_path / "dst") is False

        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"not a zip file")
        assert FileInstaller.extract_payload(bad, tmp_path / "dst") is False

        empty = tmp_path / "empty.zip"
        with zipfile.ZipFile(empty, "w") as zf:
            zf.writestr("Color Card.exe", b"LAUNCHER")
        assert FileInstaller.extract_payload(empty, tmp_path / "dst") is False


class TestEnsureSafeToClear:
    """InstallWorker._ensure_safe_to_clear 护栏测试（注册表读取已打桩）"""

    @pytest.mark.unit
    def test_registry_path_match_passes(self, qtbot, tmp_path, monkeypatch):
        """注册表安装路径与目标一致时通过（Windows 下大小写不敏感）"""
        worker = InstallWorker({"install_path": str(tmp_path)})
        (tmp_path / "unrelated.txt").write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            worker._registry_installer,
            "get_install_path",
            lambda: Path(str(tmp_path).upper())
        )

        assert worker._ensure_safe_to_clear(tmp_path) is True

    @pytest.mark.unit
    def test_app_marker_passes(self, qtbot, tmp_path, monkeypatch):
        """目录内存在应用标记主程序时通过"""
        worker = InstallWorker({"install_path": str(tmp_path)})
        (tmp_path / "Color Card.exe").write_bytes(b"exe")
        monkeypatch.setattr(worker._registry_installer, "get_install_path", lambda: None)

        assert worker._ensure_safe_to_clear(tmp_path) is True

    @pytest.mark.unit
    def test_unrelated_files_rejected(self, qtbot, tmp_path, monkeypatch):
        """目录含无关文件且无注册表匹配、无应用标记时不通过"""
        worker = InstallWorker({"install_path": str(tmp_path)})
        (tmp_path / "readme.txt").write_text("x", encoding="utf-8")
        (tmp_path / "data").mkdir()
        monkeypatch.setattr(worker._registry_installer, "get_install_path", lambda: None)

        assert worker._ensure_safe_to_clear(tmp_path) is False

    @pytest.mark.unit
    def test_missing_or_empty_dir_passes(self, qtbot, tmp_path, monkeypatch):
        """目录不存在或为空时直接通过"""
        worker = InstallWorker({"install_path": str(tmp_path)})
        monkeypatch.setattr(
            worker._registry_installer, "get_install_path", lambda: Path("C:/nowhere")
        )

        assert worker._ensure_safe_to_clear(tmp_path / "not-exist") is True

        empty = tmp_path / "empty"
        empty.mkdir()
        assert worker._ensure_safe_to_clear(empty) is True


class TestClearInstallPath:
    """InstallWorker._clear_install_path 清空与重试测试"""

    @pytest.mark.unit
    def test_clear_removes_existing_dir(self, qtbot, tmp_path):
        """存在的目录被整目录删除"""
        worker = InstallWorker({"install_path": str(tmp_path)})
        target = tmp_path / "install"
        (target / "old").mkdir(parents=True)
        (target / "old" / "file.txt").write_text("x", encoding="utf-8")

        assert worker._clear_install_path(target) is True
        assert not target.exists()

    @pytest.mark.unit
    def test_clear_skips_missing_dir(self, qtbot, tmp_path, monkeypatch):
        """目录不存在时跳过删除"""
        worker = InstallWorker({"install_path": str(tmp_path)})
        called: list[Path] = []
        monkeypatch.setattr(shutil, "rmtree", lambda p: called.append(p))

        assert worker._clear_install_path(tmp_path / "not-exist") is True
        assert called == []

    @pytest.mark.unit
    def test_clear_retries_then_succeeds(self, qtbot, tmp_path, monkeypatch):
        """删除失败时按上限重试，重试内成功即通过"""
        worker = InstallWorker({"install_path": str(tmp_path)})
        target = tmp_path / "install"
        target.mkdir()
        attempts: list[Path] = []

        def flaky_rmtree(path):
            attempts.append(path)
            if len(attempts) < 3:
                raise OSError("handle still open")

        monkeypatch.setattr(shutil, "rmtree", flaky_rmtree)
        monkeypatch.setattr(time, "sleep", lambda *_: None)

        assert worker._clear_install_path(target) is True
        assert len(attempts) == 3

    @pytest.mark.unit
    def test_clear_gives_up_and_emits_failure(self, qtbot, tmp_path, monkeypatch):
        """重试耗尽仍失败时发出失败信号并中止"""
        worker = InstallWorker({"install_path": str(tmp_path)})
        target = tmp_path / "install"
        target.mkdir()
        attempts: list[Path] = []
        results: list[tuple[bool, str]] = []
        worker.install_completed.connect(lambda ok, msg: results.append((ok, msg)))

        def stuck_rmtree(path):
            attempts.append(path)
            raise OSError("locked by antivirus")

        monkeypatch.setattr(shutil, "rmtree", stuck_rmtree)
        monkeypatch.setattr(time, "sleep", lambda *_: None)

        assert worker._clear_install_path(target) is False
        assert len(attempts) == CLEAR_RETRY_TIMES
        assert results == [(False, "无法清空目标目录，请关闭相关程序后重试")]


class TestDeployFiles:
    """InstallWorker._deploy_files 部署流程编排测试（进程关闭与载荷定位已打桩）"""

    def _prepare(self, qtbot, tmp_path, monkeypatch):
        """构造工作线程、伪造载荷与打桩

        Returns:
            tuple: (worker, install_dir, 进程关闭记录列表)
        """
        payload_dir = tmp_path / "payload-home"
        payload_dir.mkdir()
        make_payload_zip(payload_dir / "Color Card Payload.zip")

        install_dir = tmp_path / "install"
        install_dir.mkdir()
        (install_dir / "Color Card.exe").write_bytes(b"OLD-EXE")
        (install_dir / "stale_residual.txt").write_text("old", encoding="utf-8")

        worker = InstallWorker({"install_path": str(install_dir)})
        monkeypatch.setattr(worker._registry_installer, "get_install_path", lambda: None)
        # 打桩避免测试误杀真实运行中的应用
        closed: list[str] = []
        monkeypatch.setattr(install_service, "close_app_processes", lambda name: closed.append(name))
        monkeypatch.setattr(install_service, "get_base_path", lambda: str(payload_dir))
        return worker, install_dir, closed

    @pytest.mark.integration
    def test_deploy_flattens_payload_and_clears_old_files(self, qtbot, tmp_path, monkeypatch):
        """覆盖安装：旧版被关闭、目录被清空重铺、残留清除、标记不入安装根"""
        worker, install_dir, closed = self._prepare(qtbot, tmp_path, monkeypatch)

        assert worker._deploy_files(install_dir) is True
        assert closed == ["Color Card.exe"]
        assert (install_dir / "Color Card.exe").read_bytes() == b"MAIN-EXE"
        assert (install_dir / "locales" / "zh.toml").exists()
        assert not (install_dir / "stale_residual.txt").exists()
        assert not (install_dir / ".portable").exists()

    @pytest.mark.integration
    def test_deploy_progress_stays_in_deployment_band(self, qtbot, tmp_path, monkeypatch):
        """铺开段进度映射到 0~80%，单调不下降且终点触达 80"""
        worker, install_dir, _ = self._prepare(qtbot, tmp_path, monkeypatch)
        progress: list[int] = []
        worker.progress_updated.connect(lambda p, m: progress.append(p))

        assert worker._deploy_files(install_dir) is True
        assert progress
        assert all(0 <= p <= 80 for p in progress)
        assert progress == sorted(progress)
        assert progress[-1] == 80

    @pytest.mark.integration
    def test_deploy_aborts_on_unrelated_files(self, qtbot, tmp_path, monkeypatch):
        """护栏拒绝时中止安装、目录未被改动"""
        payload_dir = tmp_path / "payload-home"
        payload_dir.mkdir()
        make_payload_zip(payload_dir / "Color Card Payload.zip")
        install_dir = tmp_path / "install"
        install_dir.mkdir()
        (install_dir / "readme.txt").write_text("x", encoding="utf-8")

        worker = InstallWorker({"install_path": str(install_dir)})
        monkeypatch.setattr(worker._registry_installer, "get_install_path", lambda: None)
        monkeypatch.setattr(install_service, "close_app_processes", lambda name: None)
        monkeypatch.setattr(install_service, "get_base_path", lambda: str(payload_dir))
        results: list[tuple[bool, str]] = []
        worker.install_completed.connect(lambda ok, msg: results.append((ok, msg)))

        assert worker._deploy_files(install_dir) is False
        assert results == [(False, "目标目录包含非应用文件，请确认安装路径")]
        assert (install_dir / "readme.txt").exists()

    @pytest.mark.integration
    def test_deploy_aborts_when_payload_missing(self, qtbot, tmp_path, monkeypatch):
        """载荷缺失时中止安装、旧安装未被清空"""
        install_dir = tmp_path / "install"
        install_dir.mkdir()
        (install_dir / "Color Card.exe").write_bytes(b"OLD-EXE")

        worker = InstallWorker({"install_path": str(install_dir)})
        monkeypatch.setattr(worker._registry_installer, "get_install_path", lambda: None)
        monkeypatch.setattr(install_service, "close_app_processes", lambda name: None)
        monkeypatch.setattr(install_service, "get_base_path", lambda: str(tmp_path))
        results: list[tuple[bool, str]] = []
        worker.install_completed.connect(lambda ok, msg: results.append((ok, msg)))

        assert worker._deploy_files(install_dir) is False
        assert results == [(False, "安装包载荷缺失")]
        assert (install_dir / "Color Card.exe").read_bytes() == b"OLD-EXE"
