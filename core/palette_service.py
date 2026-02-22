"""配色服务模块

管理配色的导入导出业务逻辑，包括文件解析、数据验证、格式转换等。
UI层通过PaletteService调用业务功能，实现UI与业务逻辑分离。
"""

# 标准库导入
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any

# 第三方库导入
from PySide6.QtCore import QObject, QThread, Signal

# 项目模块导入
from .color import hex_to_rgb, get_color_info
from .grouping import generate_groups


class PaletteImporter(QThread):
    """配色导入线程

    在后台线程中执行配色导入，避免阻塞UI。
    支持取消操作。
    """

    # 信号：导入完成
    finished = Signal(list)   # 导入的配色列表
    # 信号：导入失败
    error = Signal(str)       # 错误信息

    def __init__(self, file_path: str, parent=None):
        """初始化导入线程

        Args:
            file_path: 导入文件路径
            parent: 父对象
        """
        super().__init__(parent)
        self._file_path = file_path
        self._is_cancelled = False

    def cancel(self):
        """请求取消导入"""
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._is_cancelled

    def run(self):
        """在子线程中执行配色导入"""
        try:
            if self._check_cancelled():
                return

            # 读取JSON文件
            with open(self._file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            if self._check_cancelled():
                return

            # 验证数据格式
            if not isinstance(import_data, dict):
                self.error.emit("文件格式错误：根对象必须是字典")
                return

            palettes = import_data.get("palettes", [])
            if not isinstance(palettes, list):
                self.error.emit("文件格式错误：palettes 必须是列表")
                return

            if not palettes:
                self.error.emit("文件中没有配色数据")
                return

            if self._check_cancelled():
                return

            # 转换颜色数据
            valid_favorites = []
            for palette in palettes:
                if self._check_cancelled():
                    return

                if not isinstance(palette, dict):
                    continue

                colors_data = palette.get("colors", [])
                if not isinstance(colors_data, list) or not colors_data:
                    continue

                colors = []
                for hex_color in colors_data:
                    if isinstance(hex_color, str) and hex_color.startswith('#'):
                        try:
                            r, g, b = hex_to_rgb(hex_color)
                            color_info = get_color_info(r, g, b)
                            colors.append(color_info)
                        except Exception:
                            # 转换失败时添加基本信息
                            colors.append({"hex": hex_color, "rgb": (0, 0, 0)})

                if colors:
                    favorite_data = {
                        "id": str(uuid.uuid4()),
                        "name": palette.get("name", "未命名"),
                        "colors": colors,
                        "created_at": datetime.now().isoformat(),
                        "source": "import"
                    }
                    valid_favorites.append(favorite_data)

            if self._check_cancelled():
                return

            if not valid_favorites:
                self.error.emit("没有有效的配色数据")
                return

            # 发送成功信号
            self.finished.emit(valid_favorites)

        except json.JSONDecodeError as e:
            if not self._check_cancelled():
                self.error.emit(f"JSON 解析错误: {e}")
        except (IOError, OSError) as e:
            if not self._check_cancelled():
                self.error.emit(f"文件读取错误: {e}")
        except Exception as e:
            if not self._check_cancelled():
                self.error.emit(f"导入失败: {e}")


class PaletteExporter(QThread):
    """配色导出线程

    在后台线程中执行配色导出，避免阻塞UI。
    """

    # 信号：导出完成
    finished = Signal(str)    # 导出文件路径
    # 信号：导出失败
    error = Signal(str)       # 错误信息

    def __init__(self, palettes: List[Dict[str, Any]], file_path: str, parent=None):
        """初始化导出线程

        Args:
            palettes: 配色列表
            file_path: 导出文件路径
            parent: 父对象
        """
        super().__init__(parent)
        self._palettes = palettes
        self._file_path = file_path
        self._is_cancelled = False

    def cancel(self):
        """请求取消导出"""
        self._is_cancelled = True

    def _check_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._is_cancelled

    def run(self):
        """在子线程中执行配色导出"""
        try:
            if self._check_cancelled():
                return

            # 转换配色数据为导出格式
            export_palettes = []
            for fav in self._palettes:
                if self._check_cancelled():
                    return

                colors = fav.get("colors", [])
                hex_colors = []
                for color_info in colors:
                    if isinstance(color_info, dict):
                        hex_color = color_info.get("hex", "")
                        if hex_color:
                            hex_colors.append(hex_color)
                    elif isinstance(color_info, str):
                        hex_colors.append(color_info)

                if hex_colors:
                    export_palettes.append({
                        "name": fav.get("name", "未命名"),
                        "colors": hex_colors
                    })

            if self._check_cancelled():
                return

            # 生成分组配置
            groups = generate_groups(len(export_palettes))

            # 构建导出数据
            now = datetime.now()
            palette_id = f"user_palettes_{now.strftime('%Y%m%d_%H%M%S')}"
            export_data = {
                "version": "1.0",
                "id": palette_id,
                "name": "",
                "name_zh": "",
                "description": "",
                "author": "",
                "created_at": now.isoformat(),
                "category": "user_palette",
                "palettes": export_palettes,
                "groups": groups
            }

            if self._check_cancelled():
                return

            # 写入JSON文件
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)

            # 发送成功信号
            self.finished.emit(self._file_path)

        except (IOError, OSError) as e:
            if not self._check_cancelled():
                self.error.emit(f"文件写入错误: {e}")
        except Exception as e:
            if not self._check_cancelled():
                self.error.emit(f"导出失败: {e}")


class PaletteService(QObject):
    """配色服务，管理配色的导入导出业务逻辑

    职责：
    - 配色导入（文件解析、数据验证、格式转换）
    - 配色导出（数据转换、文件生成）
    - 配色数据验证

    信号：
        import_started: 导入开始
        import_finished: 导入完成 (palettes)
        import_error: 导入错误 (error_message)
        export_started: 导出开始
        export_finished: 导出完成 (file_path)
        export_error: 导出错误 (error_message)
    """

    # 信号
    import_started = Signal()
    import_finished = Signal(list)  # 导入的配色列表
    import_error = Signal(str)      # 错误信息
    export_started = Signal()
    export_finished = Signal(str)   # 导出文件路径
    export_error = Signal(str)      # 错误信息

    def __init__(self, parent=None):
        """初始化配色服务

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._importer = None
        self._exporter = None

    def import_from_file(self, file_path: str) -> None:
        """从文件导入配色（异步）

        异步执行配色导入，通过信号通知结果。
        如果已有导入任务在进行，会先取消旧任务。

        Args:
            file_path: 导入文件路径
        """
        # 取消之前的导入
        if self._importer is not None and self._importer.isRunning():
            self._importer.cancel()
            self._importer = None

        self.import_started.emit()

        # 创建并启动导入线程
        self._importer = PaletteImporter(file_path, self)
        self._importer.finished.connect(self._on_import_finished)
        self._importer.error.connect(self.import_error)
        self._importer.finished.connect(self._cleanup_importer)
        self._importer.error.connect(self._cleanup_importer)
        self._importer.start()

    def cancel_import(self) -> None:
        """取消当前导入任务"""
        if self._importer is not None and self._importer.isRunning():
            self._importer.cancel()

    def _on_import_finished(self, palettes: List[Dict[str, Any]]):
        """导入完成处理

        Args:
            palettes: 导入的配色列表
        """
        self.import_finished.emit(palettes)

    def _cleanup_importer(self):
        """清理导入器"""
        if self._importer is not None:
            self._importer.deleteLater()
            self._importer = None

    def export_to_file(self, palettes: list, file_path: str) -> None:
        """导出配色到文件（异步）

        异步执行配色导出，通过信号通知结果。
        如果已有导出任务在进行，会先取消旧任务。

        Args:
            palettes: 配色列表
            file_path: 导出文件路径
        """
        # 取消之前的导出
        if self._exporter is not None and self._exporter.isRunning():
            self._exporter.cancel()
            self._exporter = None

        self.export_started.emit()

        # 创建并启动导出线程
        self._exporter = PaletteExporter(palettes, file_path, self)
        self._exporter.finished.connect(self._on_export_finished)
        self._exporter.error.connect(self.export_error)
        self._exporter.finished.connect(self._cleanup_exporter)
        self._exporter.error.connect(self._cleanup_exporter)
        self._exporter.start()

    def cancel_export(self) -> None:
        """取消当前导出任务"""
        if self._exporter is not None and self._exporter.isRunning():
            self._exporter.cancel()

    def _on_export_finished(self, file_path: str):
        """导出完成处理

        Args:
            file_path: 导出文件路径
        """
        self.export_finished.emit(file_path)

    def _cleanup_exporter(self):
        """清理导出器"""
        if self._exporter is not None:
            self._exporter.deleteLater()
            self._exporter = None

    @staticmethod
    def validate_palette(palette: Dict[str, Any]) -> Tuple[bool, str]:
        """验证配色数据格式

        Args:
            palette: 配色数据字典

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not isinstance(palette, dict):
            return False, "配色数据必须是字典"

        # 检查必需字段
        if "name" not in palette:
            return False, "配色缺少名称字段"

        colors = palette.get("colors", [])
        if not isinstance(colors, list):
            return False, "colors 必须是列表"

        if not colors:
            return False, "配色中没有颜色数据"

        # 验证颜色格式
        for i, color in enumerate(colors):
            if isinstance(color, dict):
                hex_color = color.get("hex", "")
                if not hex_color:
                    return False, f"第 {i+1} 个颜色缺少 hex 值"
                if not isinstance(hex_color, str) or not hex_color.startswith('#'):
                    return False, f"第 {i+1} 个颜色格式无效"
            elif isinstance(color, str):
                if not color.startswith('#'):
                    return False, f"第 {i+1} 个颜色格式无效"
            else:
                return False, f"第 {i+1} 个颜色格式无效"

        return True, ""

    @staticmethod
    def validate_import_file(file_path: str) -> Tuple[bool, str]:
        """验证导入文件

        Args:
            file_path: 文件路径

        Returns:
            tuple: (是否有效, 错误信息)
        """
        path = Path(file_path)

        if not path.exists():
            return False, f"文件不存在: {file_path}"

        if not path.is_file():
            return False, f"路径不是文件: {file_path}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            if not isinstance(import_data, dict):
                return False, "文件格式错误：根对象必须是字典"

            palettes = import_data.get("palettes", [])
            if not isinstance(palettes, list):
                return False, "文件格式错误：palettes 必须是列表"

            if not palettes:
                return False, "文件中没有配色数据"

            return True, ""

        except json.JSONDecodeError as e:
            return False, f"JSON 解析错误: {e}"
        except (IOError, OSError) as e:
            return False, f"文件读取错误: {e}"
        except Exception as e:
            return False, f"验证失败: {e}"
