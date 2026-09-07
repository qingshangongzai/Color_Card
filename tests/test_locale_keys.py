"""语言包 key 齐全性测试：6 个 TOML 的嵌套 key 路径与占位符必须完全一致

背景：peak_minor/peaks_minor 键名不一致曾导致 UI 显示裸键名，
此前无任何校验、靠目检才发现。本测试对全部表做嵌套 key 路径集合比对，
并校验带参词条的 {占位符}（如 area = "面积 {pct}%"）；value 文案不校验，
只校验 key 与占位符。

与 tests/test_locale.py 的分工：后者校验翻译运行时行为（tr 调用链），
本文件只做语言包静态一致性校验，不导入 PySide6。
"""

import re
import tomllib
from pathlib import Path

LOCALES = ('EN_US', 'FR_FR', 'HY_FT', 'HY_JT', 'JA_JP', 'RU_RU')
ROOT = Path(__file__).resolve().parents[1]
_PLACEHOLDER = re.compile(r'\{(\w+)\}')


def _flat(data: dict, prefix: str = '') -> dict[str, object]:
    """展平嵌套 dict 为 {'表名.key': 叶子值}"""
    flat: dict[str, object] = {}
    for key, value in data.items():
        path = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            flat |= _flat(value, path)
        else:
            flat[path] = value
    return flat


def _load(lang: str) -> dict[str, object]:
    with open(ROOT / 'locales' / f'{lang}.toml', 'rb') as f:
        return _flat(tomllib.load(f))


def test_locale_files_share_same_keys():
    base = _load(LOCALES[0])
    for lang in LOCALES[1:]:
        other = _load(lang)
        missing = base.keys() - other.keys()
        extra = other.keys() - base.keys()
        assert not missing, f'{lang} 缺失词条: {sorted(missing)}'
        assert not extra, f'{lang} 多余词条: {sorted(extra)}'


def test_locale_files_share_same_placeholders():
    """同名词条的 {占位符} 必须一致（缺失会显示裸 {pct}）"""
    base = _load(LOCALES[0])
    for lang in LOCALES[1:]:
        other = _load(lang)
        for key, value in base.items():
            if not isinstance(value, str):
                continue
            expected = set(_PLACEHOLDER.findall(value))
            got = set(_PLACEHOLDER.findall(str(other.get(key, ''))))
            assert expected == got, (
                f'{lang} 词条 {key} 占位符 {sorted(got)} != {sorted(expected)}')
