"""主窗口

整合所有组件，提供完整的标注界面。
"""

from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap, QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QGridLayout, QScrollArea,
    QStatusBar, QToolBar, QFileDialog, QMessageBox,
    QSplitter
)

from tone_labeler.feature_extractor import FeatureExtractor, ToneFeatures
from tone_labeler.data_manager import DataManager
from tone_labeler.histogram_widget import HistogramWidget
from tone_labeler.label_panel import LabelPanel


class MainWindow(QMainWindow):
    """主窗口"""

    IMAGE_FILTERS = "图片文件 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff);;所有文件 (*)"

    def __init__(self):
        super().__init__()

        self._extractor = FeatureExtractor()
        self._data_manager = DataManager()

        self._image_files: List[Path] = []
        self._current_index: int = -1
        self._current_image: Optional[QImage] = None
        self._current_features: Optional[ToneFeatures] = None

        self._setup_ui()
        self._setup_actions()
        self._setup_toolbar()
        self._setup_menu()
        self._setup_statusbar()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        """设置 UI"""
        self.setWindowTitle("影调标注工具")
        self.setMinimumSize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setMinimumSize(400, 300)
        self._image_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
            }
        """)
        self._image_label.setText("请打开图片或文件夹")

        scroll = QScrollArea()
        scroll.setWidget(self._image_label)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(scroll)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._histogram_widget = HistogramWidget()
        right_layout.addWidget(self._histogram_widget)

        self._stats_group = QGroupBox("统计信息")
        stats_layout = QGridLayout(self._stats_group)
        stats_layout.setSpacing(4)

        self._stats_labels = {}
        stats_items = [
            ("mean", "均值:"), ("median", "中位数:"), ("std", "标准差:"),
            ("min_val", "最小值:"), ("max_val", "最大值:")
        ]
        for i, (key, label) in enumerate(stats_items):
            row, col = i // 3, (i % 3) * 2
            stats_layout.addWidget(QLabel(label), row, col)
            value_label = QLabel("-")
            value_label.setStyleSheet("font-weight: bold;")
            stats_layout.addWidget(value_label, row, col + 1)
            self._stats_labels[key] = value_label

        right_layout.addWidget(self._stats_group)

        self._ratio_group = QGroupBox("分区占比")
        ratio_layout = QHBoxLayout(self._ratio_group)
        self._low_ratio_label = QLabel("暗部: -")
        self._mid_ratio_label = QLabel("中间调: -")
        self._high_ratio_label = QLabel("亮部: -")
        for label in [self._low_ratio_label, self._mid_ratio_label, self._high_ratio_label]:
            label.setStyleSheet("font-weight: bold;")
            ratio_layout.addWidget(label)
        right_layout.addWidget(self._ratio_group)

        self._features_group = QGroupBox("关键特征")
        features_layout = QHBoxLayout(self._features_group)
        self._p10_label = QLabel("P10: -")
        self._p90_label = QLabel("P90: -")
        self._peak_label = QLabel("波峰: -")
        self._span_label = QLabel("跨度: -")
        for label in [self._p10_label, self._p90_label, self._peak_label, self._span_label]:
            label.setStyleSheet("font-weight: bold;")
            features_layout.addWidget(label)
        right_layout.addWidget(self._features_group)

        self._result_group = QGroupBox("算法分类")
        result_layout = QVBoxLayout(self._result_group)
        self._result_label = QLabel("-")
        self._result_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #3498db;")
        result_layout.addWidget(self._result_label)
        self._confidence_label = QLabel("-")
        self._confidence_label.setStyleSheet("color: #666;")
        result_layout.addWidget(self._confidence_label)
        right_layout.addWidget(self._result_group)

        self._primary_panel = LabelPanel(panel_type="primary")
        self._primary_panel.label_selected.connect(self._on_primary_label_selected)
        right_layout.addWidget(self._primary_panel)

        self._secondary_panel = LabelPanel(panel_type="secondary")
        self._secondary_panel.label_selected.connect(self._on_secondary_label_selected)
        self._secondary_panel.clear_requested.connect(self._on_secondary_cleared)
        right_layout.addWidget(self._secondary_panel)

        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([700, 500])

    def _setup_actions(self) -> None:
        """设置动作"""
        self._open_image_action = QAction("打开图片", self)
        self._open_image_action.triggered.connect(self._open_image)

        self._open_folder_action = QAction("打开文件夹", self)
        self._open_folder_action.triggered.connect(self._open_folder)

        self._prev_action = QAction("上一张", self)
        self._prev_action.triggered.connect(self._prev_image)

        self._next_action = QAction("下一张", self)
        self._next_action.triggered.connect(self._next_image)

        self._export_csv_action = QAction("导出 CSV", self)
        self._export_csv_action.triggered.connect(self._export_csv)

        self._export_json_action = QAction("导出 JSON", self)
        self._export_json_action.triggered.connect(self._export_json)

    def _setup_toolbar(self) -> None:
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(self._open_image_action)
        toolbar.addAction(self._open_folder_action)
        toolbar.addSeparator()
        toolbar.addAction(self._prev_action)
        toolbar.addAction(self._next_action)
        toolbar.addSeparator()
        toolbar.addAction(self._export_csv_action)
        toolbar.addAction(self._export_json_action)

    def _setup_menu(self) -> None:
        """设置菜单"""
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self._open_image_action)
        file_menu.addAction(self._open_folder_action)
        file_menu.addSeparator()
        file_menu.addAction(self._export_csv_action)
        file_menu.addAction(self._export_json_action)

        nav_menu = self.menuBar().addMenu("导航")
        nav_menu.addAction(self._prev_action)
        nav_menu.addAction(self._next_action)

    def _setup_statusbar(self) -> None:
        """设置状态栏"""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._update_statusbar()

    def _setup_shortcuts(self) -> None:
        """设置快捷键"""
        self._open_image_action.setShortcut(QKeySequence("Ctrl+O"))
        self._open_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self._prev_action.setShortcut(QKeySequence("Left"))
        self._next_action.setShortcut(QKeySequence("Right"))
        self._export_csv_action.setShortcut(QKeySequence("Ctrl+E"))

        for tone_type, shortcut in LabelPanel.TONE_TYPES:
            action = QAction(self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(
                lambda checked, t=tone_type: self._on_primary_label_selected(t)
            )
            self.addAction(action)

        for tone_type, shortcut in LabelPanel.TONE_TYPES:
            action = QAction(self)
            action.setShortcut(QKeySequence(f"Ctrl+{shortcut}"))
            action.triggered.connect(
                lambda checked, t=tone_type: self._on_secondary_label_selected(t)
            )
            self.addAction(action)

    def _open_image(self) -> None:
        """打开单张图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开图片", "", self.IMAGE_FILTERS
        )

        if file_path:
            self._load_images([Path(file_path)])

    def _open_folder(self) -> None:
        """打开文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "打开文件夹")

        if folder_path:
            folder = Path(folder_path)
            extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}
            image_files = [
                f for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in extensions
            ]
            image_files.sort(key=lambda f: f.name.lower())

            if image_files:
                self._load_images(image_files)
            else:
                QMessageBox.warning(self, "提示", "文件夹中没有找到图片文件")

    def _load_images(self, image_files: List[Path]) -> None:
        """加载图片列表"""
        self._image_files = image_files
        self._current_index = 0
        self._load_current_image()

    def _load_current_image(self) -> None:
        """加载当前图片"""
        if not self._image_files or self._current_index < 0:
            return

        image_path = self._image_files[self._current_index]
        self._current_image = QImage(str(image_path))

        if self._current_image.isNull():
            QMessageBox.warning(self, "错误", f"无法加载图片: {image_path}")
            return

        self._display_image()
        self._extract_features()
        self._update_statusbar()

        self._primary_panel.clear()
        self._secondary_panel.clear()

        record = self._data_manager.get_record(str(image_path))
        if record:
            self._primary_panel.set_current_label(record.human_label)
            if record.human_label_secondary:
                self._secondary_panel.set_current_label(record.human_label_secondary)

    def _display_image(self) -> None:
        """显示图片"""
        if self._current_image is None:
            return

        scaled = self._current_image.scaled(
            self._image_label.size() - QSize(20, 20),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self._image_label.setPixmap(QPixmap.fromImage(scaled))

    def _extract_features(self) -> None:
        """提取特征"""
        if self._current_image is None:
            return

        self._current_features = self._extractor.extract_from_image(self._current_image)

        if self._current_features is None:
            return

        self._update_stats_display()
        self._update_histogram()
        self._update_result_display()

    def _update_stats_display(self) -> None:
        """更新统计信息显示"""
        if self._current_features is None:
            return

        f = self._current_features

        self._stats_labels["mean"].setText(f"{f.mean:.1f}")
        self._stats_labels["median"].setText(f"{f.median:.1f}")
        self._stats_labels["std"].setText(f"{f.std:.1f}")
        self._stats_labels["min_val"].setText(str(f.min_val))
        self._stats_labels["max_val"].setText(str(f.max_val))

        self._low_ratio_label.setText(f"暗部: {f.low_ratio * 100:.1f}%")
        self._mid_ratio_label.setText(f"中间调: {f.mid_ratio * 100:.1f}%")
        self._high_ratio_label.setText(f"亮部: {f.high_ratio * 100:.1f}%")

        self._p10_label.setText(f"P10: {f.P10}")
        self._p90_label.setText(f"P90: {f.P90}")
        self._peak_label.setText(f"波峰: {f.peak}")
        self._span_label.setText(f"跨度: {f.span}")

    def _update_histogram(self) -> None:
        """更新直方图"""
        if self._current_features is None:
            return

        self._histogram_widget.set_histogram(
            self._current_features.histogram,
            peak=self._current_features.peak,
            P10=self._current_features.P10,
            P90=self._current_features.P90
        )

    def _update_result_display(self) -> None:
        """更新算法结果显示"""
        if self._current_features is None:
            return

        f = self._current_features

        self._result_label.setText(f"分类: {f.tone_name}")
        self._confidence_label.setText(
            f"基调置信度: {f.key_confidence:.2f} | "
            f"跨度置信度: {f.range_confidence:.2f}"
        )

    def _update_statusbar(self) -> None:
        """更新状态栏"""
        total = len(self._image_files)
        labeled = self._data_manager.labeled_count

        if total > 0:
            current_name = self._image_files[self._current_index].name
            self._statusbar.showMessage(
                f"已标注: {labeled}/{total} | 当前: {current_name} ({self._current_index + 1}/{total})"
            )
        else:
            self._statusbar.showMessage(f"已标注: {labeled}")

    def _prev_image(self) -> None:
        """上一张"""
        if not self._image_files:
            return

        if self._current_index > 0:
            self._current_index -= 1
            self._load_current_image()

    def _next_image(self) -> None:
        """下一张"""
        if not self._image_files:
            return

        if self._current_index < len(self._image_files) - 1:
            self._current_index += 1
            self._load_current_image()

    def _on_primary_label_selected(self, tone_type: str) -> None:
        """首选标注选择处理"""
        if self._current_features is None or self._current_index < 0:
            return

        secondary = self._secondary_panel.get_current_label()
        if secondary == tone_type:
            self._secondary_panel.clear()
            secondary = ""

        self._save_labels(tone_type, secondary)
        self._primary_panel.set_current_label(tone_type)
        self._update_statusbar()

        if self._current_index < len(self._image_files) - 1:
            self._next_image()

    def _on_secondary_label_selected(self, tone_type: str) -> None:
        """次选标注选择处理"""
        if self._current_features is None or self._current_index < 0:
            return

        primary = self._primary_panel.get_current_label()
        if tone_type == primary:
            return

        self._save_labels(primary or "", tone_type)
        self._secondary_panel.set_current_label(tone_type)
        self._update_statusbar()

    def _on_secondary_cleared(self) -> None:
        """次选标注清除处理"""
        if self._current_features is None or self._current_index < 0:
            return

        primary = self._primary_panel.get_current_label()
        if primary:
            self._save_labels(primary, "")
        self._update_statusbar()

    def _save_labels(self, primary: str, secondary: str) -> None:
        """保存标注数据

        Args:
            primary: 首选标注
            secondary: 次选标注
        """
        if self._current_features is None or self._current_index < 0:
            return

        image_path = str(self._image_files[self._current_index])
        features_dict = self._extractor.features_to_dict(self._current_features)
        algo_result = self._extractor.algorithm_result_to_dict(self._current_features)

        if self._data_manager.has_record(image_path):
            self._data_manager.update_record(image_path, primary, secondary)
        else:
            self._data_manager.add_record(
                image_path=image_path,
                features=features_dict,
                algorithm_result=algo_result,
                human_label=primary,
                human_label_secondary=secondary
            )

    def _export_csv(self) -> None:
        """导出 CSV"""
        if self._data_manager.total_records == 0:
            QMessageBox.warning(self, "提示", "没有标注数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", "labels.csv", "CSV 文件 (*.csv)"
        )

        if file_path:
            output_path = self._data_manager.export_to_csv(Path(file_path))
            QMessageBox.information(self, "成功", f"数据已导出到: {output_path}")

    def _export_json(self) -> None:
        """导出 JSON"""
        if self._data_manager.total_records == 0:
            QMessageBox.warning(self, "提示", "没有标注数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 JSON", "labels.json", "JSON 文件 (*.json)"
        )

        if file_path:
            output_path = self._data_manager.export_to_json(Path(file_path))
            QMessageBox.information(self, "成功", f"数据已导出到: {output_path}")

    def resizeEvent(self, event) -> None:
        """窗口大小改变事件"""
        super().resizeEvent(event)
        if self._current_image:
            self._display_image()
