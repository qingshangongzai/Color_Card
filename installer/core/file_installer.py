# 标准库导入
import os
import shutil
from collections.abc import Callable
from pathlib import Path

# 项目模块导入
from core.logger import get_logger

logger = get_logger("installer.file_installer")


class FileInstaller:
    """文件安装器

    负责复制程序文件到安装目录。
    """

    @staticmethod
    def copy_executable(
        src_exe: Path,
        dst_dir: Path,
        dst_name: str = "Color Card.exe",
        progress_callback: Callable[[int, str], None] | None = None
    ) -> bool:
        """复制可执行文件到安装目录

        Args:
            src_exe: 源可执行文件路径
            dst_dir: 目标目录
            dst_name: 目标文件名
            progress_callback: 进度回调函数 (percent, message)

        Returns:
            bool: 是否成功
        """
        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst_file = dst_dir / dst_name

            if progress_callback:
                progress_callback(0, f"正在复制 {src_exe.name}... |")

            shutil.copy2(src_exe, dst_file)

            if progress_callback:
                progress_callback(100, f"复制完成 | {dst_name}")

            logger.info(f"可执行文件复制完成: {src_exe} -> {dst_file}")
            return True

        except (OSError, shutil.Error) as e:
            logger.error(f"可执行文件复制失败: {str(e)}")
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
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, FileNotFoundError):
                        continue
        except (OSError, FileNotFoundError):
            pass

        return total_size // 1024
