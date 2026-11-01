"""多语言模块测试

测试语言检测、加载和翻译功能。
"""

# 标准库导入
from types import SimpleNamespace
from unittest.mock import patch

# 第三方库导入
import pytest

# 项目模块导入
import utils.locale as locale_module
from utils.locale import LocaleManager, get_locale_manager, SYSTEM_LANGUAGE_MAPPING


class TestGetSystemLanguage:
    """测试 get_system_language 方法"""

    def test_exact_match_zh_cn(self, qtbot):
        """测试精确匹配简体中文"""
        manager = LocaleManager()

        with patch.object(manager, '_get_system_locale_name', return_value='zh_CN'):
            result = manager.get_system_language()
            assert result == 'HY_JT'

    def test_exact_match_zh_tw(self, qtbot):
        """测试精确匹配繁体中文"""
        manager = LocaleManager()

        with patch.object(manager, '_get_system_locale_name', return_value='zh_TW'):
            result = manager.get_system_language()
            assert result == 'HY_FT'

    def test_exact_match_en_us(self, qtbot):
        """测试精确匹配英语"""
        manager = LocaleManager()

        with patch.object(manager, '_get_system_locale_name', return_value='en_US'):
            result = manager.get_system_language()
            assert result == 'EN_US'

    def test_base_locale_match(self, qtbot):
        """测试基础语言代码匹配（如 zh_SG -> zh -> HY_JT）"""
        manager = LocaleManager()

        with patch.object(manager, '_get_system_locale_name', return_value='zh_SG'):
            result = manager.get_system_language()
            # zh_SG 不在映射表中，但 zh 在
            assert result == 'HY_JT'

    def test_base_locale_en_gb(self, qtbot):
        """测试英语基础代码匹配（en_GB -> en -> EN_US）"""
        manager = LocaleManager()

        with patch.object(manager, '_get_system_locale_name', return_value='en_GB'):
            result = manager.get_system_language()
            # en_GB 不在映射表中，但 en 在
            assert result == 'EN_US'

    def test_unsupported_locale_fallback(self, qtbot):
        """测试不支持的语言返回默认语言"""
        manager = LocaleManager()

        with patch.object(manager, '_get_system_locale_name', return_value='de_DE'):
            result = manager.get_system_language()
            # de_DE 和 de 都不在映射表中，返回默认语言
            assert result == manager.FALLBACK_LANGUAGE

    def test_empty_locale_fallback(self, qtbot):
        """测试空语言代码返回默认语言"""
        manager = LocaleManager()

        with patch.object(manager, '_get_system_locale_name', return_value=''):
            result = manager.get_system_language()
            assert result == manager.FALLBACK_LANGUAGE


class _FakeSystemLocale:
    """模拟 QLocale.system() 返回值"""

    def __init__(self, ui_languages: list[str], locale_name: str):
        self._ui_languages = ui_languages
        self._locale_name = locale_name

    def uiLanguages(self) -> list[str]:
        """返回首选 UI 语言列表"""
        return self._ui_languages

    def name(self) -> str:
        """返回区域格式 locale 名"""
        return self._locale_name


class _FakeQLocale:
    """模拟 QLocale 的构造、name()、language() 与 system()"""

    class Language:
        C = 'C'

    system_locale: _FakeSystemLocale | None = None

    def __init__(self, name: str):
        # 模拟 Qt 对 BCP-47 标签的规范化结果
        self._name = 'zh_TW' if name == 'zh-Hant-TW' else (name or 'C')

    def name(self) -> str:
        return self._name

    def language(self):
        return self.Language.C if self._name == 'C' else 'zh'

    @classmethod
    def system(cls) -> _FakeSystemLocale:
        return cls.system_locale


class TestGetSystemLocaleName:
    """测试 Windows 下优先获取显示语言（uiLanguages）"""

    @staticmethod
    def _resolve(ui_languages: list[str], region_name: str = 'zh_CN') -> str:
        """在模拟 Windows 环境下调用 _get_system_locale_name"""
        manager = LocaleManager()
        _FakeQLocale.system_locale = _FakeSystemLocale(ui_languages, region_name)
        with patch.object(locale_module, 'QLocale', _FakeQLocale), \
                patch.object(locale_module, 'sys', SimpleNamespace(platform='win32')):
            return manager._get_system_locale_name()

    def test_prefer_display_language_over_region(self):
        """显示语言为繁体、区域格式为简体时，返回繁体"""
        assert self._resolve(['zh-Hant-TW'], region_name='zh_CN') == 'zh_TW'

    def test_empty_ui_languages_fallback_to_region(self):
        """首选 UI 语言为空时回退区域格式"""
        assert self._resolve([], region_name='zh_CN') == 'zh_CN'

    def test_c_locale_fallback_to_region(self):
        """首项解析为 C locale 时回退区域格式"""
        assert self._resolve(['C'], region_name='zh_CN') == 'zh_CN'

    def test_non_windows_uses_region_format(self):
        """非 Windows 平台保持原行为，使用区域格式"""
        manager = LocaleManager()
        _FakeQLocale.system_locale = _FakeSystemLocale(['zh-Hant-TW'], 'zh_CN')
        with patch.object(locale_module, 'QLocale', _FakeQLocale), \
                patch.object(locale_module, 'sys', SimpleNamespace(platform='linux')):
            assert manager._get_system_locale_name() == 'zh_CN'


class TestLocaleManager:
    """测试 LocaleManager 类"""

    def test_singleton(self, qtbot):
        """测试单例模式"""
        manager1 = get_locale_manager()
        manager2 = get_locale_manager()
        assert manager1 is manager2

    def test_supported_languages(self, qtbot):
        """测试支持的语言列表"""
        manager = LocaleManager()
        languages = manager.get_supported_languages()

        assert 'auto' in languages
        assert 'HY_JT' in languages
        assert 'EN_US' in languages

    def test_load_language(self, qtbot):
        """测试加载语言"""
        manager = LocaleManager()

        # 加载简体中文
        result = manager.load_language('HY_JT')
        assert result is True
        assert manager.get_current_language() == 'HY_JT'

    def test_load_invalid_language(self, qtbot):
        """测试加载无效语言回退默认语言"""
        manager = LocaleManager()

        manager.load_language('INVALID_LANG')
        # 无效语言回退到默认语言
        assert manager.get_current_language() == manager.FALLBACK_LANGUAGE

    def test_resolve_auto_language(self, qtbot):
        """测试解析 auto 语言代码"""
        manager = LocaleManager()

        with patch.object(manager, '_get_system_locale_name', return_value='en_GB'):
            resolved = manager.resolve_language('auto')
            assert resolved == 'EN_US'

    def test_tr_existing_key(self, qtbot):
        """测试翻译存在的键"""
        manager = LocaleManager()
        manager.load_language('HY_JT')

        # 测试已知的翻译键
        text = manager.tr('app.title')
        assert isinstance(text, str)
        assert len(text) > 0

    def test_tr_missing_key_returns_key(self, qtbot):
        """测试翻译不存在的键返回键名"""
        manager = LocaleManager()
        manager.load_language('HY_JT')

        text = manager.tr('nonexistent.key')
        assert text == 'nonexistent.key'

    def test_tr_with_default(self, qtbot):
        """测试带默认值的翻译"""
        manager = LocaleManager()
        manager.load_language('HY_JT')

        text = manager.translate('nonexistent.key', default='Default Text')
        assert text == 'Default Text'

    def test_tr_with_format(self, qtbot):
        """测试带格式参数的翻译"""
        manager = LocaleManager()
        manager.load_language('HY_JT')

        # 假设有一个带占位符的翻译
        text = manager.translate('test.format', default='Hello {name}', name='World')
        assert 'World' in text


class TestSystemLanguageMapping:
    """测试系统语言映射表"""

    def test_mapping_not_empty(self):
        """测试映射表不为空"""
        assert len(SYSTEM_LANGUAGE_MAPPING) > 0

    def test_chinese_mappings(self):
        """测试中文语言映射"""
        assert SYSTEM_LANGUAGE_MAPPING['zh_CN'] == 'HY_JT'
        assert SYSTEM_LANGUAGE_MAPPING['zh_TW'] == 'HY_FT'
        assert SYSTEM_LANGUAGE_MAPPING['zh'] == 'HY_JT'

    def test_english_mappings(self):
        """测试英语语言映射"""
        assert SYSTEM_LANGUAGE_MAPPING['en'] == 'EN_US'
        assert SYSTEM_LANGUAGE_MAPPING['en_US'] == 'EN_US'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
