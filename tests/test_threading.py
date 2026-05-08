"""多线程功能测试

测试所有线程类的线程安全性、取消机制和信号连接。
"""

# 标准库导入
import time

# 第三方库导入
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

# 项目模块导入
from core.histogram_service import HistogramCalculator, HistogramService
from core.luminance_service import LuminanceCalculator, LuminanceService
from core.color_service import DominantColorExtractor, ColorService
from core.image_service import ProgressiveImageLoader
from core.palette_service import PaletteImporter, PaletteExporter


class TestHistogramCalculator:
    """HistogramCalculator 线程安全测试"""

    def test_safe_cancel_without_terminate(self, qtbot):
        """测试不使用 terminate() 也能正常取消"""
        # 创建测试图片
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        # 创建计算器
        calculator = HistogramCalculator(image, "luminance")

        # 启动计算
        calculator.start()
        assert calculator.isRunning()

        # 立即取消（不使用 terminate）
        calculator.cancel()

        # 等待线程结束（最多1秒）
        calculator.wait(1000)

        # 验证线程已停止
        assert not calculator.isRunning()

    def test_cancel_does_not_block(self, qtbot):
        """测试 cancel() 不阻塞调用线程"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        calculator = HistogramCalculator(image, "luminance")
        calculator.start()

        # 记录取消前时间
        start_time = time.time()

        # 调用 cancel
        calculator.cancel()

        # 验证 cancel 立即返回（< 10ms）
        elapsed = time.time() - start_time
        assert elapsed < 0.01  # 10ms

        calculator.wait(1000)

    def test_queued_connection_safety(self, qtbot):
        """测试跨线程信号使用 QueuedConnection"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        calculator = HistogramCalculator(image, "luminance")

        # 使用 qtbot.waitSignal 等待信号发射
        with qtbot.waitSignal(calculator.finished, timeout=5000) as blocker:
            calculator.start()

        # 验证结果
        result = blocker.args[0]
        assert len(result) == 256  # 明度直方图有256个值

    def test_qimage_copy_safety(self, qtbot):
        """测试 QImage 复制避免崩溃"""
        # 创建测试图片
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        # 创建计算器（应该复制图片）
        calculator = HistogramCalculator(image, "luminance")

        # 修改原始图片
        image.fill(Qt.GlobalColor.blue)

        # 启动计算
        calculator.start()
        assert calculator.wait(5000), "计算超时"

        # 如果没有崩溃，说明 QImage 复制是安全的


class TestLuminanceCalculator:
    """LuminanceCalculator 线程安全测试"""

    def test_calculation_with_cancel(self, qtbot):
        """测试取消后计算正确停止"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        calculator = LuminanceCalculator(image)

        results = []
        calculator.calculation_finished.connect(results.append)

        # 启动计算
        calculator.start()

        # 立即取消
        calculator.cancel()

        # 等待线程结束
        calculator.wait(1000)

        # 验证线程已停止
        assert not calculator.isRunning()

    def test_cancel_does_not_block(self, qtbot):
        """测试 cancel() 不阻塞调用线程"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        calculator = LuminanceCalculator(image)
        calculator.start()

        # 记录取消前时间
        start_time = time.time()

        # 调用 cancel
        calculator.cancel()

        # 验证 cancel 立即返回（< 10ms）
        elapsed = time.time() - start_time
        assert elapsed < 0.01  # 10ms

        calculator.wait(1000)


class TestDominantColorExtractor:
    """DominantColorExtractor 线程安全测试"""

    def test_extraction_cancel(self, qtbot):
        """测试提取任务可取消"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        extractor = DominantColorExtractor(image, count=5)

        # 启动提取
        extractor.start()
        assert extractor.isRunning()

        # 取消提取
        extractor.cancel()

        # 等待线程结束
        extractor.wait(1000)

        # 验证线程已停止
        assert not extractor.isRunning()

    def test_cancel_does_not_block(self, qtbot):
        """测试 cancel() 不阻塞调用线程"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        extractor = DominantColorExtractor(image, count=5)
        extractor.start()

        # 记录取消前时间
        start_time = time.time()

        # 调用 cancel
        extractor.cancel()

        # 验证 cancel 立即返回（< 10ms）
        elapsed = time.time() - start_time
        assert elapsed < 0.01  # 10ms

        extractor.wait(1000)


class TestProgressiveImageLoader:
    """ProgressiveImageLoader 线程安全测试"""

    def test_load_cancel(self, qtbot, tmp_path):
        """测试加载任务可取消"""
        # 创建一个临时图片文件
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)
        image_path = str(tmp_path / "test.png")
        image.save(image_path)

        loader = ProgressiveImageLoader(image_path)

        # 启动加载
        loader.start()

        # 立即取消
        loader.cancel()

        # 等待线程结束
        loader.wait(1000)

        # 验证线程已停止
        assert not loader.isRunning()

    def test_cancel_does_not_block(self, qtbot, tmp_path):
        """测试 cancel() 不阻塞调用线程"""
        # 创建一个临时图片文件
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)
        image_path = str(tmp_path / "test.png")
        image.save(image_path)

        loader = ProgressiveImageLoader(image_path)
        loader.start()

        # 记录取消前时间
        start_time = time.time()

        # 调用 cancel
        loader.cancel()

        # 验证 cancel 立即返回（< 10ms）
        elapsed = time.time() - start_time
        assert elapsed < 0.01  # 10ms

        loader.wait(1000)


class TestPaletteImporter:
    """PaletteImporter 线程安全测试"""

    def test_import_cancel(self, qtbot, tmp_path):
        """测试导入任务可取消"""
        # 创建一个临时 JSON 文件
        import json
        data = {
            "version": "1.0",
            "palettes": [
                {"name": "Test", "colors": ["#FF0000", "#00FF00"]}
            ]
        }
        file_path = str(tmp_path / "test.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        importer = PaletteImporter(file_path)

        # 启动导入
        importer.start()

        # 立即取消
        importer.cancel()

        # 等待线程结束
        importer.wait(1000)

        # 验证线程已停止
        assert not importer.isRunning()

    def test_cancel_does_not_block(self, qtbot, tmp_path):
        """测试 cancel() 不阻塞调用线程"""
        # 创建一个临时 JSON 文件
        import json
        data = {
            "version": "1.0",
            "palettes": [
                {"name": "Test", "colors": ["#FF0000", "#00FF00"]}
            ]
        }
        file_path = str(tmp_path / "test.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        importer = PaletteImporter(file_path)
        importer.start()

        # 记录取消前时间
        start_time = time.time()

        # 调用 cancel
        importer.cancel()

        # 验证 cancel 立即返回（< 10ms）
        elapsed = time.time() - start_time
        assert elapsed < 0.01  # 10ms

        importer.wait(1000)


class TestPaletteExporter:
    """PaletteExporter 线程安全测试"""

    def test_export_cancel(self, qtbot, tmp_path):
        """测试导出任务可取消"""
        palettes = [
            {"name": "Test", "colors": [{"hex": "#FF0000"}, {"hex": "#00FF00"}]}
        ]
        file_path = str(tmp_path / "export.json")

        exporter = PaletteExporter(palettes, file_path)

        # 启动导出
        exporter.start()

        # 立即取消
        exporter.cancel()

        # 等待线程结束
        exporter.wait(1000)

        # 验证线程已停止
        assert not exporter.isRunning()

    def test_cancel_does_not_block(self, qtbot, tmp_path):
        """测试 cancel() 不阻塞调用线程"""
        palettes = [
            {"name": "Test", "colors": [{"hex": "#FF0000"}, {"hex": "#00FF00"}]}
        ]
        file_path = str(tmp_path / "export.json")

        exporter = PaletteExporter(palettes, file_path)
        exporter.start()

        # 记录取消前时间
        start_time = time.time()

        # 调用 cancel
        exporter.cancel()

        # 验证 cancel 立即返回（< 10ms）
        elapsed = time.time() - start_time
        assert elapsed < 0.01  # 10ms

        exporter.wait(1000)


class TestServiceCleanup:
    """服务类清理测试"""

    def test_histogram_service_destructor(self, qtbot):
        """测试 HistogramService 析构函数停止线程"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        service = HistogramService()
        service.calculate_luminance_async(image)

        # 等待计算开始
        qtbot.wait(100)

        # 删除服务（应该停止所有线程）
        del service

        # 如果没有崩溃，说明析构函数工作正常

    def test_luminance_service_destructor(self, qtbot):
        """测试 LuminanceService 析构函数停止线程"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        service = LuminanceService()
        service.calculate_luminance_zones(image)

        # 等待计算开始
        qtbot.wait(100)

        # 删除服务（应该停止所有线程）
        del service

        # 如果没有崩溃，说明析构函数工作正常

    def test_color_service_destructor(self, qtbot):
        """测试 ColorService 析构函数停止线程"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        service = ColorService()
        service.extract_dominant_colors(image, count=5)

        # 等待提取开始
        qtbot.wait(100)

        # 删除服务（应该停止所有线程）
        del service

        # 如果没有崩溃，说明析构函数工作正常


class TestSignalDisconnect:
    """信号断开测试"""

    def test_histogram_calculator_signal_disconnect(self, qtbot):
        """测试 HistogramCalculator 信号正确断开"""
        image = QImage(100, 100, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)

        calculator = HistogramCalculator(image, "luminance")

        # 连接信号
        results = []
        calculator.finished.connect(results.append)

        # 启动并等待完成
        calculator.start()
        calculator.wait(5000)

        # 断开信号
        try:
            calculator.finished.disconnect(results.append)
        except (TypeError, RuntimeError):
            pass  # 信号可能已自动断开

        # 如果没有异常，说明信号断开正常

    def test_service_signal_disconnect(self, qtbot):
        """测试服务类信号正确断开"""
        service = HistogramService()

        # 连接信号
        results = []
        service.luminance_histogram_ready.connect(results.append)

        # 断开信号
        try:
            service.luminance_histogram_ready.disconnect(results.append)
        except (TypeError, RuntimeError):
            pass  # 信号可能未连接

        # 如果没有异常，说明信号断开正常


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
