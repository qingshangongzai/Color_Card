"""日志系统测试

测试日志管理器、日志记录器、用户操作日志和性能日志功能。
"""

# 标准库导入
import logging
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

# 第三方库导入
import pytest

# 项目模块导入
from core.logger import (
    LoggerManager,
    get_logger_manager,
    get_logger,
    log_user_action,
    log_performance,
)


class TestLoggerManager:
    """LoggerManager 日志管理器测试"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = get_logger_manager()
        manager2 = get_logger_manager()
        assert manager1 is manager2

    def test_initialize_creates_log_dir(self, tmp_path):
        """测试初始化创建日志目录"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            manager.initialize()

            log_dir = manager.get_log_dir()
            assert log_dir.exists()
            assert log_dir.name == "logs"

    def test_initialize_creates_log_file(self, tmp_path):
        """测试初始化创建日志文件"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            manager.initialize()

            log_path = manager.get_log_path()
            assert log_path.exists()
            assert log_path.name == "color_card.log"

    def test_initialize_idempotent(self, tmp_path):
        """测试重复初始化是幂等的"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            manager.initialize()
            manager.initialize()

            log_path = manager.get_log_path()
            assert log_path.exists()

    def test_get_logger_returns_logger(self, tmp_path):
        """测试获取日志记录器"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            logger = manager.get_logger("test_module")

            assert isinstance(logger, logging.Logger)
            assert logger.name == "color_card.test_module"

    def test_get_log_dir_returns_correct_path(self, tmp_path):
        """测试获取日志目录路径"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            log_dir = manager.get_log_dir()

            expected_path = tmp_path / ".color_card" / "logs"
            assert log_dir == expected_path

    def test_get_log_path_returns_correct_path(self, tmp_path):
        """测试获取日志文件路径"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            log_path = manager.get_log_path()

            expected_path = tmp_path / ".color_card" / "logs" / "color_card.log"
            assert log_path == expected_path


class TestGetLogger:
    """get_logger 函数测试"""

    def test_get_logger_returns_logger(self, tmp_path):
        """测试获取日志记录器"""
        with patch.object(Path, 'home', return_value=tmp_path):
            logger = get_logger("test_module")

            assert isinstance(logger, logging.Logger)
            assert logger.name == "color_card.test_module"

    def test_get_logger_different_names(self, tmp_path):
        """测试不同名称返回不同日志记录器"""
        with patch.object(Path, 'home', return_value=tmp_path):
            logger1 = get_logger("module1")
            logger2 = get_logger("module2")

            assert logger1 is not logger2
            assert logger1.name == "color_card.module1"
            assert logger2.name == "color_card.module2"

    def test_get_logger_same_name_returns_same_logger(self, tmp_path):
        """测试相同名称返回相同日志记录器"""
        with patch.object(Path, 'home', return_value=tmp_path):
            logger1 = get_logger("test_module")
            logger2 = get_logger("test_module")

            assert logger1 is logger2


class TestLogUserAction:
    """log_user_action 函数测试"""

    def test_basic_user_action(self, tmp_path, caplog):
        """测试基本用户操作记录"""
        with patch.object(Path, 'home', return_value=tmp_path):
            get_logger_manager().initialize()

            with caplog.at_level(logging.INFO):
                log_user_action("open_image")

            assert "open_image" in caplog.text

    def test_user_action_with_params(self, tmp_path, caplog):
        """测试带参数的用户操作记录"""
        with patch.object(Path, 'home', return_value=tmp_path):
            get_logger_manager().initialize()

            with caplog.at_level(logging.INFO):
                log_user_action(
                    action="open_image",
                    params={"path": "test.jpg", "size": "1920x1080"}
                )

            assert "open_image" in caplog.text
            assert "path=test.jpg" in caplog.text
            assert "size=1920x1080" in caplog.text

    def test_user_action_with_result(self, tmp_path, caplog):
        """测试带结果的用户操作记录"""
        with patch.object(Path, 'home', return_value=tmp_path):
            get_logger_manager().initialize()

            with caplog.at_level(logging.INFO):
                log_user_action(
                    action="save_config",
                    result="success"
                )

            assert "save_config" in caplog.text
            assert "result=success" in caplog.text

    def test_user_action_with_params_and_result(self, tmp_path, caplog):
        """测试带参数和结果的用户操作记录"""
        with patch.object(Path, 'home', return_value=tmp_path):
            get_logger_manager().initialize()

            with caplog.at_level(logging.INFO):
                log_user_action(
                    action="extract_colors",
                    params={"count": 5, "method": "kmeans"},
                    result="success"
                )

            assert "extract_colors" in caplog.text
            assert "count=5" in caplog.text
            assert "method=kmeans" in caplog.text
            assert "result=success" in caplog.text


class TestLogPerformance:
    """log_performance 函数测试"""

    def test_performance_context_manager(self, tmp_path, caplog):
        """测试性能日志上下文管理器"""
        with patch.object(Path, 'home', return_value=tmp_path):
            get_logger_manager().initialize()

            with caplog.at_level(logging.INFO):
                with log_performance("test_operation"):
                    time.sleep(0.01)

            assert "test_operation" in caplog.text
            assert "elapsed=" in caplog.text
            assert "ms" in caplog.text

    def test_performance_with_params(self, tmp_path, caplog):
        """测试带参数的性能日志"""
        with patch.object(Path, 'home', return_value=tmp_path):
            get_logger_manager().initialize()

            with caplog.at_level(logging.INFO):
                with log_performance("generate_scheme", {"type": "monochromatic"}):
                    time.sleep(0.01)

            assert "generate_scheme" in caplog.text
            assert "type=monochromatic" in caplog.text
            assert "elapsed=" in caplog.text

    def test_performance_elapsed_time_accuracy(self, tmp_path, caplog):
        """测试耗时计算准确性"""
        with patch.object(Path, 'home', return_value=tmp_path):
            get_logger_manager().initialize()

            with caplog.at_level(logging.INFO):
                start = time.time()
                with log_performance("test_operation"):
                    time.sleep(0.05)
                actual_elapsed = (time.time() - start) * 1000

            log_text = caplog.text
            import re
            match = re.search(r'elapsed=(\d+)ms', log_text)
            assert match is not None
            logged_elapsed = int(match.group(1))

            assert abs(logged_elapsed - actual_elapsed) < 50

    def test_performance_handles_exception(self, tmp_path, caplog):
        """测试性能日志处理异常"""
        with patch.object(Path, 'home', return_value=tmp_path):
            get_logger_manager().initialize()

            with caplog.at_level(logging.INFO):
                try:
                    with log_performance("failing_operation"):
                        raise ValueError("Test error")
                except ValueError:
                    pass

            assert "failing_operation" in caplog.text
            assert "elapsed=" in caplog.text


class TestLogFormat:
    """日志格式测试"""

    def test_log_format_contains_timestamp(self, tmp_path):
        """测试日志格式包含时间戳"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            manager._initialized = False
            manager.initialize()
            logger = manager.get_logger("test")

            logger.info("Test message")

            log_path = manager.get_log_path()
            log_content = log_path.read_text(encoding="utf-8")

            assert "[" in log_content
            assert "]" in log_content

    def test_log_format_contains_level(self, tmp_path):
        """测试日志格式包含日志级别"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            manager._initialized = False
            manager.initialize()
            logger = manager.get_logger("test")

            logger.info("Test message")

            log_path = manager.get_log_path()
            log_content = log_path.read_text(encoding="utf-8")

            assert "[INFO]" in log_content

    def test_log_format_contains_module_name(self, tmp_path):
        """测试日志格式包含模块名"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            manager._initialized = False
            manager.initialize()
            logger = manager.get_logger("test_module")

            logger.info("Test message")

            log_path = manager.get_log_path()
            log_content = log_path.read_text(encoding="utf-8")

            assert "[color_card.test_module]" in log_content

    def test_different_log_levels(self, tmp_path):
        """测试不同日志级别"""
        with patch.object(Path, 'home', return_value=tmp_path):
            manager = LoggerManager()
            manager._initialized = False
            manager.initialize(level=logging.DEBUG)
            logger = manager.get_logger("test")

            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            log_path = manager.get_log_path()
            log_content = log_path.read_text(encoding="utf-8")

            assert "[DEBUG]" in log_content
            assert "[INFO]" in log_content
            assert "[WARNING]" in log_content
            assert "[ERROR]" in log_content


class TestLoggerConstants:
    """日志管理器常量测试"""

    def test_config_dir_name(self):
        """测试配置目录名称"""
        assert LoggerManager.CONFIG_DIR_NAME == ".color_card"

    def test_log_dir_name(self):
        """测试日志目录名称"""
        assert LoggerManager.LOG_DIR_NAME == "logs"

    def test_log_file_name(self):
        """测试日志文件名称"""
        assert LoggerManager.LOG_FILE_NAME == "color_card.log"

    def test_max_bytes(self):
        """测试最大文件大小"""
        assert LoggerManager.MAX_BYTES == 10 * 1024 * 1024

    def test_backup_count(self):
        """测试备份数量"""
        assert LoggerManager.BACKUP_COUNT == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
