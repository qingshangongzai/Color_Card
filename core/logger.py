# 标准库导入
import logging
import logging.handlers
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional


class LoggerManager:
    """日志管理器，统一管理应用程序日志配置"""

    CONFIG_DIR_NAME: str = ".color_card"
    LOG_DIR_NAME: str = "logs"
    LOG_FILE_NAME: str = "color_card.log"
    MAX_BYTES: int = 10 * 1024 * 1024
    BACKUP_COUNT: int = 7

    def __init__(self) -> None:
        """初始化日志管理器"""
        self._log_dir: Path = self._get_log_dir()
        self._logger: Optional[logging.Logger] = None
        self._initialized: bool = False

    def _get_log_dir(self) -> Path:
        """获取日志目录路径

        Returns:
            Path: 日志目录的完整路径
        """
        home_dir = Path.home()
        config_dir = home_dir / self.CONFIG_DIR_NAME
        return config_dir / self.LOG_DIR_NAME

    def _ensure_log_dir(self) -> None:
        """确保日志目录存在"""
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self, level: int = logging.INFO) -> None:
        """初始化日志系统

        Args:
            level: 日志级别，默认为 INFO
        """
        if self._initialized:
            return

        self._ensure_log_dir()

        self._logger = logging.getLogger("color_card")
        self._logger.setLevel(level)

        self._logger.handlers.clear()

        log_path = self._log_dir / self.LOG_FILE_NAME
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=self.MAX_BYTES,
            backupCount=self.BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setLevel(level)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

        self._initialized = True
        self._logger.info("日志系统初始化完成")

    def get_logger(self, name: str) -> logging.Logger:
        """获取模块级日志记录器

        Args:
            name: 模块名称

        Returns:
            logging.Logger: 配置好的日志记录器
        """
        if not self._initialized:
            self.initialize()
        return logging.getLogger(f"color_card.{name}")

    def get_log_path(self) -> Path:
        """获取当前日志文件路径

        Returns:
            Path: 日志文件路径
        """
        return self._log_dir / self.LOG_FILE_NAME

    def get_log_dir(self) -> Path:
        """获取日志目录路径

        Returns:
            Path: 日志目录路径
        """
        return self._log_dir


_logger_manager: Optional[LoggerManager] = None


def get_logger_manager() -> LoggerManager:
    """获取全局日志管理器实例

    Returns:
        LoggerManager: 日志管理器实例
    """
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager


def get_logger(name: str) -> logging.Logger:
    """获取模块级日志记录器

    Args:
        name: 模块名称

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return get_logger_manager().get_logger(name)


def log_user_action(action: str, params: Optional[Dict[str, Any]] = None, result: str = "") -> None:
    """记录用户操作

    Args:
        action: 操作名称
        params: 操作参数
        result: 操作结果
    """
    logger = get_logger("user_action")
    param_str = ", ".join(f"{k}={v}" for k, v in (params or {}).items())
    result_str = f", result={result}" if result else ""
    logger.info(f"{action}: {param_str}{result_str}")


@contextmanager
def log_performance(operation: str, params: Optional[Dict[str, Any]] = None):
    """性能日志上下文管理器

    Args:
        operation: 操作名称
        params: 操作参数

    用法:
        with log_performance("generate_scheme", {"algorithm": "mono"}):
            pass
    """
    logger = get_logger("performance")
    start_time = time.time()

    try:
        yield
    finally:
        elapsed = int((time.time() - start_time) * 1000)
        param_str = ", ".join(f"{k}={v}" for k, v in (params or {}).items())
        param_prefix = f"{param_str}, " if param_str else ""
        logger.info(f"{operation}: {param_prefix}elapsed={elapsed}ms")
