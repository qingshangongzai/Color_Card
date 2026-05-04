"""数据管理模块

管理标注数据的保存、加载和导出。
"""

import csv
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class LabelRecord:
    """标注记录"""
    image_path: str
    image_hash: str
    timestamp: str
    features: Dict[str, Any]
    algorithm_result: Dict[str, Any]
    human_label: str
    is_correct: bool

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class DataManager:
    """数据管理器"""

    TONE_TYPES = [
        "高长调", "高中调", "高短调",
        "中长调", "中中调", "中短调",
        "低长调", "低中调", "低短调",
        "全长调"
    ]

    def __init__(self, save_dir: Optional[Path] = None):
        """初始化数据管理器

        Args:
            save_dir: 数据保存目录，默认为工具目录下的 data 文件夹
        """
        if save_dir is None:
            save_dir = Path(__file__).parent / "data"

        self._save_dir = Path(save_dir)
        self._save_dir.mkdir(parents=True, exist_ok=True)

        self._records: Dict[str, LabelRecord] = {}
        self._current_file: Optional[Path] = None

        self._load_existing_records()

    def _load_existing_records(self) -> None:
        """加载已有记录"""
        json_files = list(self._save_dir.glob("*.json"))
        if json_files:
            latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
            self.load_from_file(latest_file)

    def _compute_image_hash(self, image_path: str) -> str:
        """计算图片哈希值

        Args:
            image_path: 图片路径

        Returns:
            str: MD5 哈希值
        """
        hasher = hashlib.md5()
        with open(image_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def add_record(
        self,
        image_path: str,
        features: Dict[str, Any],
        algorithm_result: Dict[str, Any],
        human_label: str
    ) -> LabelRecord:
        """添加标注记录

        Args:
            image_path: 图片路径
            features: 特征数据
            algorithm_result: 算法结果
            human_label: 人工标注

        Returns:
            LabelRecord: 创建的记录
        """
        image_hash = self._compute_image_hash(image_path)
        timestamp = datetime.now().isoformat()

        is_correct = algorithm_result.get("tone_name", "") == human_label

        record = LabelRecord(
            image_path=image_path,
            image_hash=image_hash,
            timestamp=timestamp,
            features=features,
            algorithm_result=algorithm_result,
            human_label=human_label,
            is_correct=is_correct
        )

        self._records[image_path] = record
        self._save_records()

        return record

    def get_record(self, image_path: str) -> Optional[LabelRecord]:
        """获取标注记录

        Args:
            image_path: 图片路径

        Returns:
            Optional[LabelRecord]: 标注记录，不存在返回 None
        """
        return self._records.get(image_path)

    def has_record(self, image_path: str) -> bool:
        """检查是否有标注记录

        Args:
            image_path: 图片路径

        Returns:
            bool: 是否有记录
        """
        return image_path in self._records

    def update_record(self, image_path: str, human_label: str) -> Optional[LabelRecord]:
        """更新标注记录

        Args:
            image_path: 图片路径
            human_label: 新的人工标注

        Returns:
            Optional[LabelRecord]: 更新后的记录，不存在返回 None
        """
        record = self._records.get(image_path)
        if record is None:
            return None

        record.human_label = human_label
        record.timestamp = datetime.now().isoformat()
        record.is_correct = record.algorithm_result.get("tone_name", "") == human_label

        self._save_records()

        return record

    def delete_record(self, image_path: str) -> bool:
        """删除标注记录

        Args:
            image_path: 图片路径

        Returns:
            bool: 是否删除成功
        """
        if image_path in self._records:
            del self._records[image_path]
            self._save_records()
            return True
        return False

    def _save_records(self) -> None:
        """保存记录到文件"""
        if self._current_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._current_file = self._save_dir / f"labels_{timestamp}.json"

        data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "total_records": len(self._records),
            "records": [r.to_dict() for r in self._records.values()]
        }

        with open(self._current_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, file_path: Path) -> int:
        """从文件加载记录

        Args:
            file_path: 文件路径

        Returns:
            int: 加载的记录数
        """
        if not file_path.exists():
            return 0

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get("records", [])
        for record_data in records:
            record = LabelRecord(
                image_path=record_data["image_path"],
                image_hash=record_data["image_hash"],
                timestamp=record_data["timestamp"],
                features=record_data["features"],
                algorithm_result=record_data["algorithm_result"],
                human_label=record_data["human_label"],
                is_correct=record_data["is_correct"]
            )
            self._records[record.image_path] = record

        self._current_file = file_path

        return len(records)

    def export_to_csv(self, output_path: Optional[Path] = None) -> Path:
        """导出为 CSV 格式

        Args:
            output_path: 输出路径，默认为保存目录下的 export.csv

        Returns:
            Path: 输出文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self._save_dir / f"export_{timestamp}.csv"

        fieldnames = [
            "image_path", "image_hash", "timestamp",
            "mean", "median", "std", "min_val", "max_val",
            "P10", "P90", "peak", "span",
            "low_ratio", "mid_ratio", "high_ratio",
            "algo_tone_key", "algo_tone_range", "algo_tone_name",
            "key_confidence", "range_confidence",
            "human_label", "is_correct"
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for record in self._records.values():
                row = {
                    "image_path": record.image_path,
                    "image_hash": record.image_hash,
                    "timestamp": record.timestamp,
                    "mean": record.features.get("mean", ""),
                    "median": record.features.get("median", ""),
                    "std": record.features.get("std", ""),
                    "min_val": record.features.get("min_val", ""),
                    "max_val": record.features.get("max_val", ""),
                    "P10": record.features.get("P10", ""),
                    "P90": record.features.get("P90", ""),
                    "peak": record.features.get("peak", ""),
                    "span": record.features.get("span", ""),
                    "low_ratio": record.features.get("low_ratio", ""),
                    "mid_ratio": record.features.get("mid_ratio", ""),
                    "high_ratio": record.features.get("high_ratio", ""),
                    "algo_tone_key": record.algorithm_result.get("tone_key", ""),
                    "algo_tone_range": record.algorithm_result.get("tone_range", ""),
                    "algo_tone_name": record.algorithm_result.get("tone_name", ""),
                    "key_confidence": record.algorithm_result.get("key_confidence", ""),
                    "range_confidence": record.algorithm_result.get("range_confidence", ""),
                    "human_label": record.human_label,
                    "is_correct": record.is_correct
                }
                writer.writerow(row)

        return output_path

    def export_to_json(self, output_path: Optional[Path] = None) -> Path:
        """导出为 JSON 格式

        Args:
            output_path: 输出路径，默认为保存目录下的 export.json

        Returns:
            Path: 输出文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self._save_dir / f"export_{timestamp}.json"

        data = {
            "version": "1.0",
            "exported": datetime.now().isoformat(),
            "total_records": len(self._records),
            "statistics": self.get_statistics(),
            "records": [r.to_dict() for r in self._records.values()]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        total = len(self._records)
        if total == 0:
            return {
                "total": 0,
                "correct": 0,
                "accuracy": 0.0,
                "by_type": {}
            }

        correct = sum(1 for r in self._records.values() if r.is_correct)

        by_type: Dict[str, Dict[str, int]] = {}
        for tone_type in self.TONE_TYPES:
            by_type[tone_type] = {"total": 0, "correct": 0}

        for record in self._records.values():
            human = record.human_label
            if human in by_type:
                by_type[human]["total"] += 1
                if record.is_correct:
                    by_type[human]["correct"] += 1

        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total > 0 else 0.0,
            "by_type": by_type
        }

    @property
    def total_records(self) -> int:
        """总记录数"""
        return len(self._records)

    @property
    def labeled_count(self) -> int:
        """已标注数"""
        return len(self._records)

    def clear(self) -> None:
        """清空所有记录"""
        self._records.clear()
        self._current_file = None
