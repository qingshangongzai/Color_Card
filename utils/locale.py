"""多语言国际化模块

提供应用程序的多语言支持，包括语言包加载、切换和翻译文本获取。
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QLocale, QObject, Signal


SYSTEM_LANGUAGE_MAPPING: Dict[str, str] = {
    'zh_CN': 'ZW_JT',
    'zh_Hans': 'ZW_JT',
    'zh': 'ZW_JT',
    'zh_TW': 'ZW_FT',
    'zh_HK': 'ZW_FT',
    'zh_Hant': 'ZW_FT',
    'en': 'EN_US',
    'en_US': 'EN_US',
    'en_GB': 'EN_US',
    'ja': 'JA_JP',
    'ja_JP': 'JA_JP',
    'fr': 'FR_FR',
    'fr_FR': 'FR_FR',
    'ru': 'RU_RU',
    'ru_RU': 'RU_RU',
}


def _get_base_path() -> str:
    """获取应用程序基础路径

    支持开发环境和 PyInstaller 打包后的环境

    Returns:
        str: 应用程序基础路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    # 开发环境 - 返回项目根目录（utils/ 的父目录）
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LocaleManager(QObject):
    """多语言管理器
    
    负责语言包的加载、切换和翻译文本获取。
    """
    
    language_changed = Signal(str)
    
    SUPPORTED_LANGUAGES = {
        'auto': '跟随系统',
        'ZW_JT': '简体中文',
        'ZW_FT': '繁體中文',
        'EN_US': 'English',
        'JA_JP': '日本語',
        'FR_FR': 'Français',
        'RU_RU': 'Русский'
    }
    
    DEFAULT_LANGUAGE = 'auto'
    FALLBACK_LANGUAGE = 'ZW_JT'
    
    def __init__(self):
        """初始化多语言管理器"""
        super().__init__()
        self._current_language: str = self.DEFAULT_LANGUAGE
        self._translations: Dict[str, str] = {}
        self._locales_dir: Path = self._get_locales_dir()
        
    def _get_locales_dir(self) -> Path:
        """获取语言包目录路径
        
        Returns:
            Path: 语言包目录路径
        """
        base_path = _get_base_path()
        return Path(base_path) / 'locales'
    
    def load_language(self, language_code: str) -> bool:
        """加载指定语言的翻译数据
        
        Args:
            language_code: 语言代码（如 'ZW_JT', 'EN_US', 'auto'）
            
        Returns:
            bool: 是否加载成功
        """
        resolved_code = self.resolve_language(language_code)
        
        if resolved_code not in self.SUPPORTED_LANGUAGES:
            resolved_code = self.FALLBACK_LANGUAGE
            
        locale_file = self._locales_dir / f'{resolved_code}.json'
        
        if not locale_file.exists():
            if resolved_code != self.FALLBACK_LANGUAGE:
                return self.load_language(self.FALLBACK_LANGUAGE)
            return False
            
        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
            self._current_language = language_code
            return True
        except (json.JSONDecodeError, IOError, OSError):
            return False
    
    def resolve_language(self, language_code: str) -> str:
        """解析语言代码，如果是 'auto' 则返回系统语言
        
        Args:
            language_code: 语言代码（如 'auto', 'ZW_JT', 'EN_US'）
            
        Returns:
            str: 实际的语言代码
        """
        if language_code == 'auto':
            return self.get_system_language()
        return language_code
    
    def get_system_language(self) -> str:
        """获取系统语言并映射到项目支持的语言代码
        
        Returns:
            str: 映射后的语言代码，未匹配则返回默认语言
        """
        try:
            system_locale = QLocale.system().name()
            if system_locale in SYSTEM_LANGUAGE_MAPPING:
                return SYSTEM_LANGUAGE_MAPPING[system_locale]
            base_locale = system_locale.split('_')[0]
            if base_locale in SYSTEM_LANGUAGE_MAPPING:
                return SYSTEM_LANGUAGE_MAPPING[base_locale]
        except (AttributeError, ValueError):
            pass
        return self.FALLBACK_LANGUAGE
    
    def set_language(self, language_code: str) -> bool:
        """设置当前语言
        
        Args:
            language_code: 语言代码
            
        Returns:
            bool: 是否设置成功
        """
        if language_code == self._current_language:
            return True
            
        if self.load_language(language_code):
            self.language_changed.emit(language_code)
            return True
        return False
    
    def get_current_language(self) -> str:
        """获取当前语言代码
        
        Returns:
            str: 当前语言代码
        """
        return self._current_language
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表
        
        Returns:
            Dict[str, str]: 语言代码到语言名称的映射
        """
        return self.SUPPORTED_LANGUAGES.copy()
    
    def tr(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """获取翻译文本
        
        Args:
            key: 翻译键（支持点号分隔的嵌套路径）
            default: 默认文本，如果未提供则返回key
            **kwargs: 用于格式化翻译文本的参数
            
        Returns:
            str: 翻译后的文本
        """
        keys = key.split('.')
        value: Any = self._translations
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                text = default if default is not None else key
                if kwargs:
                    try:
                        return text.format(**kwargs)
                    except (KeyError, ValueError):
                        return text
                return text
                
        text = str(value) if isinstance(value, str) else key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text
    
    def get_translations(self) -> Dict[str, str]:
        """获取当前所有翻译数据
        
        Returns:
            Dict[str, str]: 翻译数据字典
        """
        return self._translations.copy()


_locale_manager: Optional[LocaleManager] = None


def get_locale_manager() -> LocaleManager:
    """获取全局多语言管理器实例
    
    Returns:
        LocaleManager: 多语言管理器实例
    """
    global _locale_manager
    if _locale_manager is None:
        _locale_manager = LocaleManager()
    return _locale_manager


def tr(key: str, default: Optional[str] = None, **kwargs) -> str:
    """获取翻译文本的便捷函数
    
    Args:
        key: 翻译键
        default: 默认文本
        **kwargs: 用于格式化翻译文本的参数
        
    Returns:
        str: 翻译后的文本
    """
    return get_locale_manager().tr(key, default, **kwargs)


def set_language(language_code: str) -> bool:
    """设置当前语言的便捷函数
    
    Args:
        language_code: 语言代码
        
    Returns:
        bool: 是否设置成功
    """
    return get_locale_manager().set_language(language_code)


def get_current_language() -> str:
    """获取当前语言代码的便捷函数
    
    Returns:
        str: 当前语言代码
    """
    return get_locale_manager().get_current_language()


def get_supported_languages() -> Dict[str, str]:
    """获取支持的语言列表的便捷函数
    
    Returns:
        Dict[str, str]: 语言代码到语言名称的映射
    """
    return get_locale_manager().get_supported_languages()
