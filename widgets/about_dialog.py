from PySide6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit
from PySide6.QtCore import Qt


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(520, 480)
        self.setup_ui()

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 纯文本编辑器显示内容
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(self._get_about_text())
        layout.addWidget(self.text_edit, stretch=1)

    def contextMenuEvent(self, event):
        """屏蔽原生右键菜单"""
        event.ignore()

    def _get_about_text(self):
        """获取关于页面的纯文本内容"""
        return """Color Card 是一款专为摄影师开发的图片分析小工具，旨在帮助摄影爱好者和专业人士快速分析图像的色彩分布、亮度信息等关键数据，辅助后期调色和色彩管理。

主要功能：
  • 图片色彩分析
  • 亮度分布统计
  • 色彩卡片生成
  • 支持多种图片格式

【开发团队】
  • 出品：浮晓 HXiao Studio
  • 开发：青山公仔
  • 代码：Trae
  • 联系邮箱：hxiao_studio@163.com

【开源项目使用说明】
  • 本程序基于 PySide6 架构开发，许可证：LGPL v3
    版权所有：The Qt Company
    项目地址：https://www.qt.io/

  • 本程序 UI 组件使用 PyQt6-Fluent-Widgets，许可证：GPLv3
    项目地址：https://github.com/zhiyiYo/PyQt-Fluent-Widgets
"""
