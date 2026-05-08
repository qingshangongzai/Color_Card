"""安装/卸载业务逻辑模块"""

from __future__ import annotations

from installer.core.install_service import InstallService
from installer.core.file_installer import FileInstaller
from installer.core.registry_installer import RegistryInstaller
from installer.core.shortcut_installer import ShortcutInstaller

__all__ = [
    'InstallService',
    'FileInstaller',
    'RegistryInstaller',
    'ShortcutInstaller'
]
