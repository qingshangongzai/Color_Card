#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试四段式显示"""

import sys
sys.path.insert(0, '.')

from ui.preset_color_widgets import PresetColorSchemeCard
from core.color_data import get_catppuccin_color_series, get_gruvbox_color_series
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

# 测试 Catppuccin
print("=== 测试 Catppuccin Mocha ===")
series_data = get_catppuccin_color_series('catppuccin_mocha')
if series_data:
    card = PresetColorSchemeCard('catppuccin_mocha', series_data)
    print(f"系列类型: {card._series_type}")
    print(f"当前显示模式: {card._shade_mode}")
    
    # 模拟切换
    print("\n切换测试:")
    modes = []
    for i in range(5):
        modes.append(card._shade_mode)
        card._on_toggle_shade_mode()
    print(f"模式循环: {' -> '.join(modes)}")
    card.deleteLater()

# 测试 Gruvbox
print("\n=== 测试 Gruvbox Dark ===")
series_data = get_gruvbox_color_series('gruvbox_dark')
if series_data:
    card = PresetColorSchemeCard('gruvbox_dark', series_data)
    print(f"系列类型: {card._series_type}")
    print(f"当前显示模式: {card._shade_mode}")
    
    # 模拟切换
    print("\n切换测试:")
    modes = []
    for i in range(5):
        modes.append(card._shade_mode)
        card._on_toggle_shade_mode()
    print(f"模式