"""对话框模块"""

from .about_dialog import AboutDialog
from .base_frameless_dialog import BaseFramelessDialog
from .colorblind_dialog import ColorblindPreviewDialog
from .confirm_dialogs import ConfirmDialog, DeleteConfirmDialog, ImportModeDialog
from .contrast_dialog import ContrastCheckDialog
from .edit_palette import EditPaletteDialog, ColorPickerDialog
from .export_settings_dialog import ExportSettingsDialog
from .harmony_dialog import HarmonyAnalysisDialog
from .tone_analysis_dialog import ToneAnalysisDialog
from .update_dialog import UpdateAvailableDialog

__all__ = [
    'AboutDialog',
    'BaseFramelessDialog',
    'ColorblindPreviewDialog',
    'ConfirmDialog',
    'ColorPickerDialog',
    'ContrastCheckDialog',
    'DeleteConfirmDialog',
    'EditPaletteDialog',
    'ExportSettingsDialog',
    'HarmonyAnalysisDialog',
    'ImportModeDialog',
    'ToneAnalysisDialog',
    'UpdateAvailableDialog',
]
