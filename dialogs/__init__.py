"""对话框模块"""

from .about_dialog import AboutDialog
from .base_frameless_dialog import BaseFramelessDialog
from .colorblind_dialog import ColorblindPreviewDialog
from .contrast_dialog import ContrastCheckDialog
from .edit_palette import EditPaletteDialog, ColorPickerDialog
from .export_settings_dialog import ExportSettingsDialog
from .update_dialog import UpdateAvailableDialog

__all__ = [
    'AboutDialog',
    'BaseFramelessDialog',
    'ColorblindPreviewDialog',
    'ColorPickerDialog',
    'ContrastCheckDialog',
    'EditPaletteDialog',
    'ExportSettingsDialog',
    'UpdateAvailableDialog',
]
