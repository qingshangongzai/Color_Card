# 标准库导入
import os
import shutil
import sys
from pathlib import Path
from typing import Callable

# 项目模块导入
from core import get_logger

logger = get_logger("installer.file_installer")


class FileInstaller:
    """文件安装器

    负责复制程序文件到安装目录。
    """

    @staticmethod
    def copy_files(
        src_dir: Path,
        dst_dir: Path,
        progress_callback: Callable[[int, str], None] | None = None
    ) -> bool:
        """复制文件到安装目录

        Args:
            src_dir: 源目录
            dst_dir: 目标目录
            progress_callback: 进度回调函数 (percent, message)

        Returns:
            bool: 是否成功
        """
        try:
            # 确保目标目录存在
            dst_dir.mkdir(parents=True, exist_ok=True)

            # 获取所有文件列表
            all_files = []
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    src_file = Path(root) / file
                    rel_path = src_file.relative_to(src_dir)
                    all_files.append((src_file, rel_path))

            total_files = len(all_files)
            if total_files == 0:
                logger.warning(f"源目录为空: {src_dir}")
                return True

            # 复制文件
            for i, (src_file, rel_path) in enumerate(all_files):
                dst_file = dst_dir / rel_path

                # 创建目标目录
                dst_file.parent.mkdir(parents=True, exist_ok=True)

                # 复制文件
                shutil.copy2(src_file, dst_file)

                # 更新进度
                if progress_callback:
                    percent = int((i + 1) / total_files * 100)
                    message = f"正在复制文件... | {rel_path}"
                    progress_callback(percent, message)

            logger.info(f"文件复制完成: {total_files} 个文件")
            return True

        except (OSError, shutil.Error) as e:
            logger.error(f"文件复制失败: {str(e)}")
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

    @staticmethod
    def get_source_dir() -> Path:
        """获取源文件目录

        在打包后的环境中，返回可执行文件所在目录。
        在开发环境中，返回 test_dist/ 目录（模拟已打包的程序文件）。

        Returns:
            Path: 源文件目录
        """
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        else:
            project_root = Path(__file__).parent.parent.parent
            test_dist = project_root / 'test_dist'
            if test_dist.exists():
                return test_dist
            return project_root
