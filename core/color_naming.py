"""感知色名模型与 HSB 十二段技术色名

技术色相名只描述色相轴，不替代感知色名；感知色名由最终 sRGB 三元组
经离线 OKLab kNN 模型计算，保证名称与显示的色块来自同一个数值输入。
模型数据位于 color_data/naming/color_name_model.json，延迟加载且加载后只读。
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Sequence
from typing import TypeVar

import numpy as np

from .color_data import get_base_path
from .color_space import srgb255_to_oklab, srgb_hsb_hue

# ==================== 色名映射（主项目 HSB 12 色环标准） ====================

# HSB 色相角每 30° 一段，色名 id 居中（0°=red、30°=orange_red ... 330°=purple_red），
# 与 locales 既有 color_wheel.hue_* 词条一一对应
_HUE_NAMES = ('red', 'orange_red', 'yellow', 'yellow_green', 'green', 'cyan_green',
              'cyan', 'cyan_blue', 'blue', 'purple', 'magenta', 'purple_red')

# 技术色名冷暖分组（近中性分区冷暖混合提示用，不参与感知命名）
PERCEPT_WARM_NAMES = ('red', 'orange_red', 'yellow', 'magenta', 'purple_red')   # 灰族暖侧 / 冷暖混合暖侧
PERCEPT_COOL_NAMES = ('cyan', 'cyan_blue', 'blue', 'purple')                    # 灰族冷侧 / 冷暖混合冷侧
PERCEPT_ZONE_MIX_MIN_PCT = 20.0  # 近中性分区冷暖双向提示：暖侧与冷侧 chroma 权重占比均超此

MODEL_RELATIVE_PATH = ('color_data', 'naming', 'color_name_model.json')

_LabelT = TypeVar('_LabelT')


def hue_name(hue: float) -> str:
    """HSB 色相角（度）转主项目 12 色名 id"""
    return _HUE_NAMES[int(((hue + 15.0) % 360.0) // 30.0)]


class _KnnModel:
    """只读 kNN 模型：加载时把训练样本转成数组，推理期不再修改共享数据"""

    def __init__(self, payload: dict, version: str) -> None:
        self.version = version
        self.k = int(payload['k'])
        self.eps = float(payload['knn_eps'])
        self.secondary_margin = float(payload['secondary_margin'])
        self.allowed_tones: dict[str, list[str]] = payload['allowed_tones']
        self.allowed_modifiers: dict[str, list[str]] = payload['allowed_hue_modifiers']
        samples = payload['samples']
        self.oklab = np.asarray([sample['oklab'] for sample in samples], dtype=np.float64)
        self.families = [str(sample['family_id']) for sample in samples]
        self.tones = [str(sample['tone_id']) for sample in samples]
        self.modifiers: list[str | None] = [sample['hue_modifier_id'] for sample in samples]


_model_lock = threading.Lock()
_model_cache: tuple[tuple[int, int], _KnnModel] | None = None


def _dump_version(payload: dict, path: str) -> str:
    """模型版本：优先取 JSON 的 version 字段，缺失时取文件 SHA256 前 12 位"""
    version = payload.get('version')
    if isinstance(version, str) and version:
        return version
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()[:12]


def _load_model() -> _KnnModel:
    """按文件修改时间与大小延迟加载模型；文件变化后重新读取"""
    global _model_cache
    path = os.path.join(get_base_path(), *MODEL_RELATIVE_PATH)
    stat = os.stat(path)
    signature = (stat.st_mtime_ns, stat.st_size)
    cached = _model_cache
    if cached is not None and cached[0] == signature:
        return cached[1]

    with _model_lock:
        cached = _model_cache
        if cached is not None and cached[0] == signature:
            return cached[1]
        with open(path, 'r', encoding='utf-8') as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or payload.get('model_type') != 'oklab_knn':
            raise ValueError(f'色名模型格式不支持: {path}')
        model = _KnnModel(payload, _dump_version(payload, path))
        _model_cache = (signature, model)
        return model


def get_naming_model_version() -> str:
    """当前色名模型版本（缓存键用，模型文件更换后随之变化）"""
    return _load_model().version


def _vote(labels: Sequence[_LabelT], indices: np.ndarray,
          weights: np.ndarray) -> dict[_LabelT, float]:
    """近邻标签逆距离加权投票，返回各标签的概率"""
    totals: dict[_LabelT, float] = {}
    for index, weight in zip(indices, weights):
        label = labels[int(index)]
        totals[label] = totals.get(label, 0.0) + float(weight)
    total = sum(totals.values())
    return {label: value / total for label, value in totals.items()}


def _top_label(probabilities: dict[_LabelT, float]) -> _LabelT:
    """概率最高的标签；同概率按标签字典序，None 视为空串"""
    return min(probabilities.items(),
               key=lambda item: (-item[1], '' if item[0] is None else str(item[0])))[0]


def classify_color_name(rgb: tuple[int, int, int]) -> dict:
    """最终 sRGB 0~255 三元组 → 结构化感知色名

    只接受与绘制色块相同的最终 RGB，内部显式除以 255 后转 OKLab 查表。
    返回字段固定为 family_id / secondary_family_id / tone_id /
    hue_modifier_id / confidence / technical_hue_id；越界组合按固定规则
    投影到模型 JSON 的允许集合（构建时由 name_mapping.json 生成），
    不二次搜索、不按概率另选。
    """
    model = _load_model()
    lab = srgb255_to_oklab(rgb)
    distances = np.linalg.norm(model.oklab - lab, axis=1)
    nearest = np.argsort(distances, kind='stable')[:model.k]
    weights = 1.0 / (distances[nearest] + model.eps)

    family_probs = _vote(model.families, nearest, weights)
    ranked = sorted(family_probs.items(), key=lambda item: (-item[1], item[0]))
    family_id, confidence = ranked[0]
    secondary_id = None
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < model.secondary_margin:
        secondary_id = ranked[1][0]

    tone_id = _top_label(_vote(model.tones, nearest, weights))
    modifier_id = _top_label(_vote(model.modifiers, nearest, weights))
    if (modifier_id == family_id
            or modifier_id not in model.allowed_modifiers.get(family_id, ())):
        modifier_id = None
    if tone_id not in model.allowed_tones.get(family_id, ('none',)):
        tone_id = 'none'

    srgb = np.asarray(rgb, dtype=np.float64) / 255.0
    return {
        'family_id': family_id,
        'secondary_family_id': secondary_id,
        'tone_id': tone_id,
        'hue_modifier_id': modifier_id,
        'confidence': float(confidence),
        'technical_hue_id': hue_name(float(srgb_hsb_hue(srgb))),
    }
