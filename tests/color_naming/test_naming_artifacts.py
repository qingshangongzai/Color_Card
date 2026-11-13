"""xkcd 感知色名数据、映射、模型与报告的契约测试"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
NAMING_DIR = ROOT / 'color_data' / 'naming'
DATA_PATH = NAMING_DIR / 'xkcd_rgb.txt'
MAPPING_PATH = NAMING_DIR / 'name_mapping.json'
BASELINE_MAPPING_PATH = NAMING_DIR / 'baseline_mapping.json'
MODEL_PATH = NAMING_DIR / 'color_name_model.json'
REPORT_PATH = NAMING_DIR / 'model_report.json'
BASELINE_SCRIPT_PATH = ROOT / 'scripts' / 'baseline_color_naming.py'

FAMILIES = {
    'black', 'white', 'gray', 'red', 'orange', 'yellow', 'green',
    'cyan', 'blue', 'purple', 'magenta', 'pink', 'brown',
}
TONES = {'none', 'vivid', 'deep', 'light', 'dark', 'pale', 'muted'}
HUE_MODIFIERS = {'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple'}
EXPECTED_BASELINE = {
    'blue': 'blue',
    'blue_gray': 'gray',
    'brown': 'brown',
    'cyan': 'cyan',
    'cyan_blue': 'blue',
    'cyan_green': 'cyan',
    'deep_red': 'red',
    'gray': 'gray',
    'green': 'green',
    'magenta': 'magenta',
    'maroon': 'red',
    'orange_red': 'orange',
    'pink': 'pink',
    'purple': 'purple',
    'purple_red': 'magenta',
    'red': 'red',
    'warm_gray': 'gray',
    'yellow': 'yellow',
    'yellow_green': 'green',
}


def _load_module(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _file_sha256(path: Path) -> str:
    """按 LF 归一化后计算 SHA256，与构建脚本的跨平台口径一致"""
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _read_rows() -> list[tuple[str, str]]:
    lines = DATA_PATH.read_text(encoding='utf-8').splitlines()
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        match = re.search(r'#([0-9a-fA-F]{6})\s*$', line)
        assert match is not None
        rows.append((line[:match.start()].strip(), '#' + match.group(1).lower()))
    return rows


@pytest.fixture(scope='module')
def color_space() -> ModuleType:
    return _load_module('_test_color_space', ROOT / 'core' / 'color_space.py')


@pytest.fixture(scope='module')
def baseline_rules() -> ModuleType:
    return _load_module('_test_baseline_rules', BASELINE_SCRIPT_PATH)


def test_xkcd_rows_are_official_shape() -> None:
    lines = DATA_PATH.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 950
    assert lines[0].startswith('# License:')
    rows = _read_rows()
    assert len(rows) == 949
    assert len({name for name, _ in rows}) == 949
    assert all(re.fullmatch(r'#[0-9a-f]{6}', hex_value) for _, hex_value in rows)


def test_mapping_is_explicit_and_covers_every_row() -> None:
    rows = _read_rows()
    data_names = {name for name, _ in rows}
    data_hex = dict(rows)
    mapping = _load_json(MAPPING_PATH)
    names = mapping['names']
    excluded = mapping['excluded']
    assert set(names).isdisjoint(excluded)
    assert data_names == set(names) | set(excluded)
    assert all(reason.strip() for reason in excluded.values())
    for name, entry in names.items():
        assert entry['hex'] == data_hex[name]


def test_mapping_uses_legal_combinations() -> None:
    mapping = _load_json(MAPPING_PATH)
    allowed_tones = mapping['allowed_tones']
    allowed_modifiers = mapping['allowed_hue_modifiers']
    assert set(allowed_tones) == FAMILIES
    assert set(allowed_modifiers) == FAMILIES
    for family in FAMILIES:
        assert 'none' in allowed_tones[family]
        assert set(allowed_tones[family]) <= TONES
        assert set(allowed_modifiers[family]) <= HUE_MODIFIERS
    for name, entry in mapping['names'].items():
        family = entry['family_id']
        tone = entry['tone_id']
        modifier = entry['hue_modifier_id']
        assert family in FAMILIES, name
        assert tone in TONES, name
        assert modifier is None or modifier in HUE_MODIFIERS, name
        assert tone in allowed_tones[family], name
        assert modifier is None or modifier in allowed_modifiers[family], name
        assert modifier != family, name


def test_model_metadata_and_samples(color_space: ModuleType) -> None:
    model = _load_json(MODEL_PATH)
    report = _load_json(REPORT_PATH)
    assert model['version'].startswith('1.0-')
    assert model['model_type'] == 'oklab_knn'
    assert model['k'] in {8, 16, 32}
    assert model['knn_eps'] == 0.001
    assert model['secondary_margin'] == 0.15
    assert model['families'] == report['test']['model']['confusion_labels']
    assert model['split']['train_samples'] == report['split']['train_samples']
    assert model['split']['test_samples'] == report['split']['test_samples']
    assert len(model['samples']) == model['split']['train_samples']

    source = model['source']
    assert source['url'] == 'https://xkcd.com/color/rgb.txt'
    assert source['license'] == 'CC0 1.0'
    assert source['data_rows'] == 949
    assert source['data_sha256'] == _file_sha256(DATA_PATH)
    assert source['mapping_sha256'] == _file_sha256(MAPPING_PATH)
    expected_version = hashlib.sha256(
        f'{source["data_sha256"]}:{source["mapping_sha256"]}:{model["k"]}:'
        f'{model["knn_eps"]:g}:{model["secondary_margin"]:g}'.encode()
    ).hexdigest()[:12]
    assert model['version'] == f'1.0-{expected_version}'

    names = [sample['name'] for sample in model['samples']]
    assert names == sorted(names)
    assert len(set(names)) == len(names)
    for sample in model['samples']:
        assert sample['family_id'] in FAMILIES
        assert sample['tone_id'] in TONES
        assert sample['hue_modifier_id'] is None or sample['hue_modifier_id'] in HUE_MODIFIERS
        assert sample['hue_modifier_id'] != sample['family_id']
        assert all(isinstance(value, int) and 0 <= value <= 255 for value in sample['rgb'])
        assert sample['hex'] == '#{:02x}{:02x}{:02x}'.format(*sample['rgb'])
        expected = color_space.srgb255_to_oklab(tuple(sample['rgb']))
        np.testing.assert_allclose(sample['oklab'], expected, atol=1e-6)


def test_report_metrics_transition_and_small_families() -> None:
    report = _load_json(REPORT_PATH)
    model = _load_json(MODEL_PATH)
    test_count = report['split']['test_samples']
    assert report['data']['excluded'] == _load_json(MAPPING_PATH)['excluded']
    assert len(report['data']['excluded']) == 11
    assert report['data']['small_families'] == ['black']
    assert set(report['data']['evaluated_families']) == FAMILIES - {'black'}

    for name in ('model', 'baseline'):
        metrics = report['test'][name]
        assert metrics['confusion_labels'] == list(model['families'])
        matrix = metrics['confusion_matrix']
        assert len(matrix) == 13 and all(len(row) == 13 for row in matrix)
        assert sum(sum(row) for row in matrix) == test_count
        support = [metrics['per_family'][family]['test_support']
                   for family in metrics['confusion_labels']]
        assert [sum(row) for row in matrix] == support
        assert isinstance(metrics['micro_f1'], float)
        assert isinstance(metrics['macro_f1'], float)
        for family in report['data']['evaluated_families']:
            entry = metrics['per_family'][family]
            assert entry['evaluated'] is True
            assert isinstance(entry['recall'], float)
            assert isinstance(entry['precision'], float)
            assert isinstance(entry['f1'], float)
        for family in report['data']['small_families']:
            entry = metrics['per_family'][family]
            assert entry['evaluated'] is False
            assert entry['recall'] == 'N/A'
            assert entry['f1'] == 'N/A'
            assert isinstance(entry['predicted_count'], int)

    transition = report['transition']
    assert 0.0 <= transition['share'] <= 1.0
    assert transition['hit_rate'] == 'N/A' or 0.0 <= transition['hit_rate'] <= 1.0
    bootstrap = report['bootstrap']
    assert bootstrap['iterations'] == 1000
    assert bootstrap['seed'] == 0
    assert isinstance(bootstrap['ci_lower'], float)
    assert isinstance(bootstrap['ci_upper'], float)
    assert bootstrap['ci_lower'] <= bootstrap['ci_upper']
    assert bootstrap['conclusion'] == ('优于基线' if bootstrap['ci_lower'] > 0
                                        else '未证明优于基线')
    assert any('KNN_EPS = 1e-3' in note for note in report['notes'])


def test_baseline_mapping_and_rules_are_frozen(baseline_rules: ModuleType) -> None:
    baseline = _load_json(BASELINE_MAPPING_PATH)
    assert baseline['version'] == '1.0'
    assert baseline['baseline_commit'] == '666a081'
    assert baseline['mapping'] == EXPECTED_BASELINE
    assert baseline_rules._HUE_NAMES == (
        'red', 'orange_red', 'yellow', 'yellow_green', 'green', 'cyan_green',
        'cyan', 'cyan_blue', 'blue', 'purple', 'magenta', 'purple_red',
    )
    assert baseline_rules.PERCEPT_GRAY_CHROMA == 0.03
    assert baseline_rules.PERCEPT_BROWN_L_MAX == 0.55
    assert baseline_rules.PERCEPT_DEEP_RED_CHROMA_MIN == 0.08
    assert baseline_rules.PERCEPT_PINK_L_MIN == 0.70
    assert baseline_rules.PERCEPT_PINK_CHROMA_MAX == 0.10


def test_naming_files_are_not_palette_sources() -> None:
    color_data = _load_module('_test_color_data', ROOT / 'core' / 'color_data.py')
    registry = color_data.ColorSourceRegistry()
    source_ids = {source.id for source in registry.get_all_sources()}
    assert 'color_name_model' not in source_ids
    assert 'name_mapping' not in source_ids
    assert 'model_report' not in source_ids
    assert 'baseline_mapping' not in source_ids
    root_jsons = {path.name for path in (ROOT / 'color_data').glob('*.json')}
    assert 'color_name_model.json' not in root_jsons
    for filename in ('xkcd_rgb.txt', 'name_mapping.json', 'baseline_mapping.json',
                     'color_name_model.json', 'model_report.json'):
        assert (NAMING_DIR / filename).is_file()
