"""离线构建 xkcd 感知色名 kNN 模型与独立测试报告

只使用标准库与 NumPy。通过 importlib 按文件路径加载 core/color_space.py，
不执行 core/__init__.py，避免把 PySide6 拉进离线构建。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NAMING_DIR = ROOT / 'color_data' / 'naming'
DATA_PATH = NAMING_DIR / 'xkcd_rgb.txt'
MAPPING_PATH = NAMING_DIR / 'name_mapping.json'
BASELINE_MAPPING_PATH = NAMING_DIR / 'baseline_mapping.json'
MODEL_PATH = NAMING_DIR / 'color_name_model.json'
REPORT_PATH = NAMING_DIR / 'model_report.json'
BASELINE_SCRIPT_PATH = ROOT / 'scripts' / 'baseline_color_naming.py'

DATA_ROWS = 949
SOURCE_URL = 'https://xkcd.com/color/rgb.txt'
LICENSE = 'CC0 1.0'
LICENSE_URL = 'https://creativecommons.org/publicdomain/zero/1.0/'
K_CANDIDATES = (8, 16, 32)
KNN_EPS = 1e-3
KNN_EPS_TEXT = f'{KNN_EPS:.0e}'.replace('e-0', 'e-')
SECONDARY_MARGIN = 0.15
SPLIT_SEED = 0
CV_FOLDS = 5
CV_SEED = 0
BOOTSTRAP_ITERATIONS = 1000
BOOTSTRAP_SEED = 0
SMALL_FAMILY_SUPPORT = 5
TEST_RATIO = 0.2

FAMILIES = (
    'black', 'white', 'gray', 'red', 'orange', 'yellow', 'green',
    'cyan', 'blue', 'purple', 'magenta', 'pink', 'brown',
)
TONES = ('none', 'vivid', 'deep', 'light', 'dark', 'pale', 'muted')
HUE_MODIFIERS = ('red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple')
BASELINE_PNAMES = (
    'red', 'orange_red', 'yellow', 'yellow_green', 'green', 'cyan_green',
    'cyan', 'cyan_blue', 'blue', 'purple', 'magenta', 'purple_red',
    'warm_gray', 'blue_gray', 'gray', 'deep_red', 'maroon', 'brown', 'pink',
)


def _load_module(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f'无法按路径加载模块: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


color_space = _load_module('_color_space', ROOT / 'core' / 'color_space.py')
baseline_rules = _load_module('_baseline_naming', BASELINE_SCRIPT_PATH)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f'构建失败: {message}')


def _sha256(path: Path) -> str:
    """按 LF 归一化后计算 SHA256，避免 Windows 检出把 CRLF 写进数据指纹"""
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def _model_version(data_sha: str, mapping_sha: str, k: int) -> str:
    """由数据、映射和模型参数派生版本，保证重建后缓存键随内容变化"""
    fingerprint = hashlib.sha256(
        f'{data_sha}:{mapping_sha}:{k}:{KNN_EPS:g}:{SECONDARY_MARGIN:g}'.encode()
    ).hexdigest()[:12]
    return f'1.0-{fingerprint}'


def _hex_rgb(value: str) -> tuple[int, int, int]:
    text = value.lstrip('#')
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def load_rows() -> list[tuple[str, tuple[int, int, int]]]:
    """读取官方 xkcd 色表，行尾解析 HEX，断言 949 条数据"""
    lines = DATA_PATH.read_text(encoding='utf-8').splitlines()
    _require(len(lines) == DATA_ROWS + 1,
             f'xkcd 文件应为 1 行许可头 + {DATA_ROWS} 条数据，实际 {len(lines)} 行')
    _require(lines[0].startswith('# License:'), 'xkcd 文件缺少许可头')
    rows: list[tuple[str, tuple[int, int, int]]] = []
    for line in lines[1:]:
        match = re.search(r'#([0-9a-fA-F]{6})\s*$', line)
        _require(match is not None, f'数据行无法解析: {line!r}')
        assert match is not None
        name = line[:match.start()].strip()
        _require(bool(name), f'数据行缺少名称: {line!r}')
        rows.append((name, _hex_rgb(match.group(1))))
    _require(len(rows) == DATA_ROWS, f'数据行数应为 {DATA_ROWS}，实际 {len(rows)}')
    _require(len({name for name, _ in rows}) == DATA_ROWS, '源名称存在重复')
    return rows


def load_mapping() -> tuple[dict[str, dict[str, Any]], dict[str, str],
                            dict[str, list[str]], dict[str, list[str]]]:
    """读取并校验归一化映射与允许组合"""
    data = json.loads(MAPPING_PATH.read_text(encoding='utf-8'))
    _require(data.get('version') == '1.0', 'name_mapping.json 版本应为 1.0')
    names = data.get('names')
    excluded = data.get('excluded')
    allowed_tones = data.get('allowed_tones')
    allowed_modifiers = data.get('allowed_hue_modifiers')
    _require(isinstance(names, dict) and isinstance(excluded, dict), '映射缺少 names/excluded')
    _require(isinstance(allowed_tones, dict), '映射缺少 allowed_tones')
    _require(isinstance(allowed_modifiers, dict), '映射缺少 allowed_hue_modifiers')
    _require(set(allowed_tones) == set(FAMILIES), 'allowed_tones 色系集合不完整')
    _require(set(allowed_modifiers) == set(FAMILIES), 'allowed_hue_modifiers 色系集合不完整')
    for family in FAMILIES:
        _require('none' in allowed_tones[family], f'{family} 必须允许 tone_id=none')
        _require(all(tone in TONES for tone in allowed_tones[family]),
                 f'{family} 含非法 tone_id')
        _require(all(modifier in HUE_MODIFIERS for modifier in allowed_modifiers[family]),
                 f'{family} 含非法 hue_modifier_id')
    for name, entry in names.items():
        _validate_entry(name, entry, allowed_tones, allowed_modifiers)
    for name, reason in excluded.items():
        _require(isinstance(reason, str) and bool(reason.strip()), f'{name} 缺少排除原因')
    return names, excluded, allowed_tones, allowed_modifiers


def _validate_entry(name: str, entry: object,
                    allowed_tones: dict[str, list[str]],
                    allowed_modifiers: dict[str, list[str]]) -> None:
    _require(isinstance(entry, dict), f'{name} 映射项不是对象')
    assert isinstance(entry, dict)
    family = entry.get('family_id')
    tone = entry.get('tone_id')
    modifier = entry.get('hue_modifier_id')
    _require(isinstance(family, str) and family in FAMILIES,
             f'{name} family_id 非法: {family!r}')
    _require(isinstance(tone, str) and tone in TONES, f'{name} tone_id 非法: {tone!r}')
    _require(modifier is None or (isinstance(modifier, str) and modifier in HUE_MODIFIERS),
             f'{name} hue_modifier_id 非法: {modifier!r}')
    assert isinstance(family, str) and isinstance(tone, str)
    _require(tone in allowed_tones[family], f'{name} 组合越界: {family}/{tone}')
    _require(modifier is None or modifier in allowed_modifiers[family],
             f'{name} 组合越界: {family}/{modifier}')
    _require(modifier != family, f'{name} 色系与修饰重复: {family}')
    hex_value = entry.get('hex')
    _require(isinstance(hex_value, str) and re.fullmatch(r'#[0-9a-f]{6}', hex_value) is not None,
             f'{name} hex 字段非法')


def validate_coverage(rows: list[tuple[str, tuple[int, int, int]]],
                      names: dict[str, dict[str, Any]],
                      excluded: dict[str, str]) -> None:
    data_names = {name for name, _ in rows}
    included = set(names)
    excluded_names = set(excluded)
    covered = included | excluded_names
    missing = sorted(data_names - covered)
    extra = sorted(covered - data_names)
    _require(included.isdisjoint(excluded_names), '同一名称同时出现在映射与排除列表')
    _require(not missing and not extra,
             f'映射覆盖不一致: 缺少 {missing[:5]}，多余 {extra[:5]}')
    for name, rgb in rows:
        entry = names.get(name)
        if entry is not None:
            _require(entry['hex'] == f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}',
                     f'{name} 的映射 HEX 与源数据不一致')


def build_samples(rows: list[tuple[str, tuple[int, int, int]]],
                  names: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    samples = []
    for name, rgb in rows:
        entry = names.get(name)
        if entry is None:
            continue
        lab = color_space.srgb255_to_oklab(rgb)
        samples.append({
            'name': name,
            'hex': f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}',
            'rgb': list(rgb),
            'oklab': [_round_float(float(value)) for value in lab],
            'family_id': entry['family_id'],
            'tone_id': entry['tone_id'],
            'hue_modifier_id': entry['hue_modifier_id'],
        })
    samples.sort(key=lambda sample: sample['name'])
    _check_duplicate_hex(samples)
    return samples


def _check_duplicate_hex(samples: list[dict[str, Any]]) -> None:
    labels: dict[tuple[int, ...], set[tuple[Any, Any, Any]]] = defaultdict(set)
    for sample in samples:
        key = tuple(int(value) for value in sample['rgb'])
        labels[key].add((sample['family_id'], sample['tone_id'], sample['hue_modifier_id']))
    conflicts = {key: value for key, value in labels.items() if len(value) > 1}
    _require(not conflicts, f'相同 HEX 存在不同标签: {list(conflicts.items())[:3]}')


def stratified_split(samples: list[dict[str, Any]]
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按色系分层、固定种子 0 划分 80% 训练 / 20% 测试"""
    rng = random.Random(SPLIT_SEED)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        groups[str(sample['family_id'])].append(sample)
    train: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for family in sorted(groups):
        items = sorted(groups[family], key=lambda sample: str(sample['name']))
        rng.shuffle(items)
        n_test = 0 if len(items) < 2 else max(1, round(len(items) * TEST_RATIO))
        n_test = min(n_test, len(items) - 1)
        test.extend(items[:n_test])
        train.extend(items[n_test:])
    train.sort(key=lambda sample: str(sample['name']))
    test.sort(key=lambda sample: str(sample['name']))
    return train, test


def _stack(samples: list[dict[str, Any]]
           ) -> tuple[np.ndarray, list[str], list[str], list[Any]]:
    labs = np.asarray([sample['oklab'] for sample in samples], dtype=np.float64)
    return (labs, [str(sample['family_id']) for sample in samples],
            [str(sample['tone_id']) for sample in samples],
            [sample['hue_modifier_id'] for sample in samples])


def _vote(labels: list, indices: np.ndarray, weights: np.ndarray) -> dict:
    totals: dict[object, float] = defaultdict(float)
    for index, weight in zip(indices, weights):
        totals[labels[index]] += float(weight)
    total = sum(totals.values())
    return {label: value / total for label, value in totals.items()}


def _predict_probs(index: tuple, lab: list[float], k: int) -> dict[str, dict]:
    labs, families, tones, modifiers = index
    distances = np.linalg.norm(labs - np.asarray(lab, dtype=np.float64), axis=1)
    count = min(k, len(distances))
    nearest = np.argsort(distances, kind='stable')[:count]
    weights = 1.0 / (distances[nearest] + KNN_EPS)
    return {
        'family': _vote(families, nearest, weights),
        'tone': _vote(tones, nearest, weights),
        'hue_modifier': _vote(modifiers, nearest, weights),
    }


def _top_label(probabilities: dict) -> str:
    return max(sorted(probabilities), key=lambda label: probabilities[label])


def _confusion_matrix(y_true: list[str], y_pred: list[str]) -> list[list[int]]:
    positions = {family: index for index, family in enumerate(FAMILIES)}
    matrix = [[0] * len(FAMILIES) for _ in FAMILIES]
    for true, pred in zip(y_true, y_pred):
        matrix[positions[true]][positions[pred]] += 1
    return matrix


def _metrics(y_true: list[str], y_pred: list[str],
             evaluated: list[str]) -> dict[str, Any]:
    matrix = _confusion_matrix(y_true, y_pred)
    positions = {family: index for index, family in enumerate(FAMILIES)}
    support = Counter(y_true)
    predicted = Counter(y_pred)
    per_family: dict[str, dict[str, Any]] = {}
    evaluated_f1: list[float] = []
    for family in FAMILIES:
        column = positions[family]
        tp = matrix[column][column]
        fp = predicted[family] - tp
        fn = support[family] - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        is_evaluated = family in evaluated
        if is_evaluated:
            evaluated_f1.append(f1)
        per_family[family] = {
            'test_support': support[family],
            'predicted_count': predicted[family],
            'precision': _round_float(precision) if is_evaluated else None,
            'recall': _round_float(recall) if is_evaluated else 'N/A',
            'f1': _round_float(f1) if is_evaluated else 'N/A',
            'evaluated': is_evaluated,
        }
    macro_f1 = sum(evaluated_f1) / len(evaluated_f1)
    micro_f1 = sum(matrix[index][index] for index in range(len(FAMILIES))) / len(y_true)
    return {
        'per_family': per_family,
        'macro_f1': _round_float(macro_f1),
        'micro_f1': _round_float(micro_f1),
        'confusion_labels': list(FAMILIES),
        'confusion_matrix': matrix,
    }


def _macro_f1(y_true: list[str], y_pred: list[str], evaluated: list[str]) -> float:
    tp: Counter = Counter()
    fp: Counter = Counter()
    fn: Counter = Counter()
    for true, pred in zip(y_true, y_pred):
        if true == pred:
            tp[true] += 1
        else:
            fp[pred] += 1
            fn[true] += 1
    scores = []
    for family in evaluated:
        precision = tp[family] / (tp[family] + fp[family]) if tp[family] + fp[family] else 0.0
        recall = tp[family] / (tp[family] + fn[family]) if tp[family] + fn[family] else 0.0
        scores.append(2 * precision * recall / (precision + recall)
                      if precision + recall else 0.0)
    return sum(scores) / len(scores)


def _folds(samples: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    rng = random.Random(CV_SEED)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        groups[str(sample['family_id'])].append(sample)
    parts: list[list[dict[str, Any]]] = [[] for _ in range(CV_FOLDS)]
    for family in sorted(groups):
        items = sorted(groups[family], key=lambda sample: str(sample['name']))
        rng.shuffle(items)
        for offset, item in enumerate(items):
            parts[offset % CV_FOLDS].append(item)
    return parts


def cross_validate(samples: list[dict[str, Any]], k: int,
                   evaluated: list[str]) -> dict[str, Any]:
    parts = _folds(samples)
    y_true: list[str] = []
    y_pred: list[str] = []
    for fold_index, fold in enumerate(parts):
        train = [item for index, part in enumerate(parts) if index != fold_index for item in part]
        index = _stack(train)
        for sample in fold:
            probabilities = _predict_probs(index, sample['oklab'], k)
            y_true.append(str(sample['family_id']))
            y_pred.append(_top_label(probabilities['family']))
    metrics = _metrics(y_true, y_pred, evaluated)
    recall = {
        family: metrics['per_family'][family]['recall']
        for family in FAMILIES
    }
    return {
        'k': k,
        'macro_f1': metrics['macro_f1'],
        'micro_f1': metrics['micro_f1'],
        'recall': recall,
    }


def baseline_family(sample: dict[str, Any], mapping: dict[str, str]) -> str:
    lightness, a_value, b_value = sample['oklab']
    chroma = math.hypot(a_value, b_value)
    rgb = np.asarray([sample['rgb']], dtype=np.float64) / 255.0
    hue_hsb = float(color_space.srgb_hsb_hue(rgb)[0])
    pname = baseline_rules.perceptual_color_name(lightness, chroma, hue_hsb)
    _require(pname in mapping, f'基线色名未在 baseline_mapping.json 登记: {pname}')
    return mapping[pname]


def load_baseline_mapping() -> dict[str, str]:
    data = json.loads(BASELINE_MAPPING_PATH.read_text(encoding='utf-8'))
    mapping = data.get('mapping')
    _require(isinstance(mapping, dict), 'baseline_mapping.json 缺少 mapping')
    _require(set(mapping) == set(BASELINE_PNAMES), '基线映射的色名集合不完整')
    _require(all(family in FAMILIES for family in mapping.values()), '基线映射含非法色系')
    return mapping


def _transition(rows: list[tuple[dict[str, Any], dict[str, float]]],
                margin: float) -> dict[str, Any]:
    count = 0
    hits = 0
    for sample, probabilities in rows:
        ranked = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))
        if len(ranked) < 2 or ranked[0][1] - ranked[1][1] >= margin:
            continue
        count += 1
        if sample['family_id'] in (ranked[0][0], ranked[1][0]):
            hits += 1
    return {
        'count': count,
        'share': _round_float(count / len(rows)),
        'hit_rate': _round_float(hits / count) if count else 'N/A',
    }


def bootstrap_delta(y_true: list[str], new_pred: list[str],
                    baseline_pred: list[str], evaluated: list[str]) -> dict[str, Any]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    count = len(y_true)
    deltas = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        indices = rng.integers(0, count, size=count)
        sample_true = [y_true[index] for index in indices]
        sample_new = [new_pred[index] for index in indices]
        sample_base = [baseline_pred[index] for index in indices]
        deltas.append(_macro_f1(sample_true, sample_new, evaluated)
                      - _macro_f1(sample_true, sample_base, evaluated))
    lower, upper = np.percentile(deltas, [2.5, 97.5])
    return {
        'iterations': BOOTSTRAP_ITERATIONS,
        'seed': BOOTSTRAP_SEED,
        'delta_mean': _round_float(float(np.mean(deltas))),
        'ci_lower': _round_float(float(lower)),
        'ci_upper': _round_float(float(upper)),
        'conclusion': '优于基线' if lower > 0 else '未证明优于基线',
    }


def _round_float(value: float) -> float:
    rounded = round(float(value), 6)
    return 0.0 if rounded == 0 else rounded


def _clean(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return _round_float(float(value))
    return value


def write_json(path: Path, payload: dict) -> None:
    text = json.dumps(_clean(payload), ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def _support(samples: list[dict[str, Any]]) -> Counter:
    return Counter(str(sample['family_id']) for sample in samples)


def _source_metadata(samples: list[dict[str, Any]], excluded: dict[str, str],
                     data_sha: str, mapping_sha: str) -> dict[str, Any]:
    return {
        'url': SOURCE_URL,
        'license': LICENSE,
        'license_url': LICENSE_URL,
        'data_rows': DATA_ROWS,
        'included_rows': len(samples),
        'excluded_rows': len(excluded),
        'data_sha256': data_sha,
        'mapping_sha256': mapping_sha,
    }


def _support_data(samples: list[dict[str, Any]], train: list[dict[str, Any]],
                  test: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    total = _support(samples)
    train_support = _support(train)
    test_support = _support(test)
    return {
        family: {
            'total': total[family],
            'train': train_support[family],
            'test': test_support[family],
        }
        for family in FAMILIES
    }


def _report_notes() -> list[str]:
    return [
        (f'KNN_EPS = {KNN_EPS_TEXT} 用于避免零距离除零，并匹配 OKLab 距离量级'
         '（约 0.05~0.3）；1e-6 会使权重退化为最近邻。'),
        (f'宏平均 F1 只统计总数 >= {SMALL_FAMILY_SUPPORT} 的色系；'
         '小样本色系仍参与训练，单列支持数、N/A 召回率与预测计数。'),
        (f'过渡名称占比按次高色系概率差 < {SECONDARY_MARGIN:g} 统计；'
         '过渡命中率指真值等于主色系或次色系。'),
        ('xkcd 数据是英文众包屏幕色名，不等同于中文人眼感知真值；'
         '本报告只证明模型相对基线的改进。'),
    ]


def _model_payload(k: int, train: list[dict[str, Any]], test: list[dict[str, Any]],
                   allowed_tones: dict[str, list[str]],
                   allowed_modifiers: dict[str, list[str]],
                   source: dict[str, Any], version: str) -> dict[str, Any]:
    return {
        'version': version,
        'model_type': 'oklab_knn',
        'k': k,
        'knn_eps': KNN_EPS,
        'secondary_margin': SECONDARY_MARGIN,
        'families': list(FAMILIES),
        'tones': list(TONES),
        'hue_modifiers': list(HUE_MODIFIERS),
        'allowed_tones': allowed_tones,
        'allowed_hue_modifiers': allowed_modifiers,
        'samples': [
            {
                'name': sample['name'],
                'hex': sample['hex'],
                'rgb': sample['rgb'],
                'oklab': sample['oklab'],
                'family_id': sample['family_id'],
                'tone_id': sample['tone_id'],
                'hue_modifier_id': sample['hue_modifier_id'],
            }
            for sample in train
        ],
        'split': {
            'seed': SPLIT_SEED,
            'test_ratio': TEST_RATIO,
            'train_samples': len(train),
            'test_samples': len(test),
        },
        'source': source,
    }


def _report_payload(source: dict[str, Any], train: list[dict[str, Any]],
                    test: list[dict[str, Any]],
                    support_data: dict[str, dict[str, int]],
                    excluded: dict[str, str], evaluated: list[str],
                    candidates: list[dict[str, Any]], k: int,
                    test_rows: list[tuple[dict[str, Any], dict[str, dict]]],
                    baseline_mapping: dict[str, str]) -> dict[str, Any]:
    y_true = [str(sample['family_id']) for sample in test]
    new_pred = [_top_label(probabilities['family']) for _, probabilities in test_rows]
    baseline_pred = [baseline_family(sample, baseline_mapping) for sample in test]
    return {
        'version': '1.0',
        'source': source,
        'data': {
            'family_support': support_data,
            'evaluated_families': evaluated,
            'small_families': [family for family in FAMILIES if family not in evaluated],
            'excluded': excluded,
        },
        'split': {
            'method': (f'按 family_id 分层，固定随机种子 {SPLIT_SEED}，'
                       f'{1 - TEST_RATIO:.0%} 训练 / {TEST_RATIO:.0%} 最终测试'),
            'seed': SPLIT_SEED,
            'test_ratio': TEST_RATIO,
            'train_samples': len(train),
            'test_samples': len(test),
        },
        'cv': {
            'folds': CV_FOLDS,
            'seed': CV_SEED,
            'selection_metric': f'macro_f1（仅统计总数 >= {SMALL_FAMILY_SUPPORT} 的色系）',
            'candidates': candidates,
            'selected_k': k,
        },
        'test': {
            'model': _metrics(y_true, new_pred, evaluated),
            'baseline': _metrics(y_true, baseline_pred, evaluated),
        },
        'transition': _transition(
            [(sample, probabilities['family']) for sample, probabilities in test_rows],
            SECONDARY_MARGIN,
        ),
        'bootstrap': bootstrap_delta(y_true, new_pred, baseline_pred, evaluated),
        'baseline': {
            'commit': '666a081',
            'mapping_sha256': _sha256(BASELINE_MAPPING_PATH),
            'pname_to_family': baseline_mapping,
        },
        'notes': _report_notes(),
    }


def build() -> None:
    rows = load_rows()
    names, excluded, allowed_tones, allowed_modifiers = load_mapping()
    validate_coverage(rows, names, excluded)
    baseline_mapping = load_baseline_mapping()
    samples = build_samples(rows, names)
    train, test = stratified_split(samples)
    support_data = _support_data(samples, train, test)
    evaluated = [family for family in FAMILIES
                 if support_data[family]['total'] >= SMALL_FAMILY_SUPPORT]

    candidates = [cross_validate(train, k, evaluated) for k in K_CANDIDATES]
    selected = max(candidates, key=lambda item: (item['macro_f1'], -item['k']))
    k = int(selected['k'])

    index = _stack(train)
    test_rows = [(sample, _predict_probs(index, sample['oklab'], k)) for sample in test]
    data_sha = _sha256(DATA_PATH)
    mapping_sha = _sha256(MAPPING_PATH)
    source = _source_metadata(samples, excluded, data_sha, mapping_sha)
    version = _model_version(data_sha, mapping_sha, k)
    model_payload = _model_payload(k, train, test, allowed_tones, allowed_modifiers,
                                   source, version)
    report_payload = _report_payload(source, train, test, support_data, excluded,
                                     evaluated, candidates, k, test_rows, baseline_mapping)

    write_json(MODEL_PATH, model_payload)
    write_json(REPORT_PATH, report_payload)
    print(f'模型已写入 {MODEL_PATH.name}: version={version}, k={k}, '
          f'train={len(train)}, test={len(test)}')
    print(f'测试宏平均 F1: 新模型 {report_payload["test"]["model"]["macro_f1"]}, '
          f'基线 {report_payload["test"]["baseline"]["macro_f1"]}')
    print(f'bootstrap 95% CI: {report_payload["bootstrap"]}')


if __name__ == '__main__':
    build()
