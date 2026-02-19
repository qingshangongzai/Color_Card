"""多语言国际化模块

提供应用程序的多语言支持，包括语言包加载、切换和翻译文本获取。
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal


class LocaleManager(QObject):
    """多语言管理器
    
    负责语言包的加载、切换和翻译文本获取。
    """
    
    language_changed = Signal(str)
    
    SUPPORTED_LANGUAGES = {
        'zh_CN': '简体中文',
        'en_US': 'English'
    }
    
    DEFAULT_LANGUAGE = 'zh_CN'
    
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
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        return project_root / 'locales'
    
    def load_language(self, language_code: str) -> bool:
        """加载指定语言的翻译数据
        
        Args:
            language_code: 语言代码（如 'zh_CN', 'en_US'）
            
        Returns:
            bool: 是否加载成功
        """
        if language_code not in self.SUPPORTED_LANGUAGES:
            language_code = self.DEFAULT_LANGUAGE
            
        locale_file = self._locales_dir / f'{language_code}.json'
        
        if not locale_file.exists():
            if language_code != self.DEFAULT_LANGUAGE:
                return self.load_language(self.DEFAULT_LANGUAGE)
            return False
            
        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
            self._current_language = language_code
            return True
        except (json.JSONDecodeError, IOError, OSError):
            return False
    
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
