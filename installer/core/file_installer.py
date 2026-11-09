# 标准库导入
import os
import shutil
import zipfile
from collections.abc import Callable
from pathlib import Path

# 项目模块导入
from app_mode import PORTABLE_LAYOUT_MARKER

# 载荷内 app/ 子树前缀：与 build-windows.yml 便携打包布局（main.dist 内容置于 app/）一致
PAYLOAD_APP_PREFIX = "app/"
# 便携布局标记条目，仅便携版需要，安装铺开时跳过
PAYLOAD_MARKER_ENTRY = f"app/{PORTABLE_LAYOUT_MARKER}"


def _extract_member(payload: zipfile.ZipFile, info: zipfile.ZipInfo, dst_dir: Path) -> None:
    """解压单个载荷条目并平铺（app/x → dst_dir/x）"""
    target = dst_dir / info.filename[len(PAYLOAD_APP_PREFIX):]
    target.parent.mkdir(parents=True, exist_ok=True)
    with payload.open(info) as src_file, target.open("wb") as dst_file:
        shutil.copyfileobj(src_file, dst_file)


class FileInstaller:
    """文件安装器

    负责解压安装载荷与统计安装目录体积。
    """

    @staticmethod
    def extract_payload(
        src_zip: Path,
        dst_dir: Path,
        progress_callback: Callable[[int, str], None] | None = None
    ) -> bool:
        """解压安装载荷到安装目录

        载荷复用便携包布局（根启动器 + app/ 子树）：只解压 app/ 前缀条目并
        平铺（app/x → dst_dir/x），跳过 .portable 布局标记；根启动器条目不
        在 app/ 前缀内，自然排除。

        Args:
            src_zip: 载荷 zip 路径
            dst_dir: 目标安装目录
            progress_callback: 进度回调函数 (percent, message)，percent 按
                实际解压字节计（0~100）

        Returns:
            bool: 是否成功
        """
        def report_progress(percent: int, message: str) -> None:
            if progress_callback:
                progress_callback(percent, message)

        try:
            with zipfile.ZipFile(src_zip) as payload:
                members = [
                    info for info in payload.infolist()
                    if info.filename.startswith(PAYLOAD_APP_PREFIX)
                    and not info.is_dir()
                    and info.filename != PAYLOAD_MARKER_ENTRY
                ]
                if not members:
                    return False

                total_bytes = sum(info.file_size for info in members)
                extracted_bytes = 0
                report_progress(0, "正在解压程序文件... |")

                for info in members:
                    _extract_member(payload, info, dst_dir)
                    extracted_bytes += info.file_size
                    percent = int(extracted_bytes * 100 / total_bytes) if total_bytes else 100
                    report_progress(percent, f"正在解压程序文件... {percent}%")

                report_progress(100, "解压完成 |")

            return True

        except (OSError, zipfile.BadZipFile, EOFError):
            return False

    @staticmethod
    def calculate_size(path: Path) -> int:
        """计算目录大小

        Args:
            path: 目录路径

        Returns:
            int: 大小（KB）
        """
        total_size = 0
        try:
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, FileNotFoundError):
                        continue
        except (OSError, FileNotFoundError):
            pass

        return total_size // 1024
