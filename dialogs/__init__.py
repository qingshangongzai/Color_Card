"""对话框模块"""

from .about_dialog import AboutDialog
from .colorblind_dialog import ColorblindPreviewDialog
from .contrast_dialog import ContrastCheckDialog
from .edit_palette import EditPaletteDialog, ColorPickerDialog
from .export_settings_dialog import ExportSettingsDialog
from .update_dialog import UpdateAvailableDialog

__all__ = [
    'AboutDialog',
    'ColorblindPreviewDialog',
    'ColorPickerDialog',
    'ContrastCheckDialog',
    'EditPaletteDialog',
    'ExportSettingsDialog',
    'UpdateAvailableDialog',
]
