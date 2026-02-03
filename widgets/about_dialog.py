from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton
from PySide6.QtCore import Qt

from qfluentwidgets import FluentIcon, PrimaryPushButton


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

        # 文本浏览器显示内容
        self.text_browser = QTextBrowser(self)
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setHtml(self._get_about_html())
        layout.addWidget(self.text_browser, stretch=1)

    def _get_about_html(self):
        """获取关于页面的 HTML 内容"""
        return """
        <html>
        <head>
            <style>
                body {
                    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                    font-size: 13px;
                    line-height: 1.8;
                    color: #333;
                    padding: 10px;
                }
                h3 {
                    font-size: 14px;
                    font-weight: bold;
                    margin-top: 20px;
                    margin-bottom: 10px;
                    color: #222;
                }
                p {
                    margin: 8px 0;
                }
                ul {
                    margin: 8px 0;
                    padding-left: 20px;
                }
                li {
                    margin: 4px 0;
                }
                a {
                    color: #0078d4;
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
                .indent {
                    margin-left: 20px;
                }
            </style>
        </head>
        <body>
            <p style="text-indent: 2em;">
                Color Card 是一款专为摄影师开发的图片分析小工具，旨在帮助摄影爱好者和专业人士快速分析图像的色彩分布、亮度信息等关键数据，辅助后期调色和色彩管理。
            </p>

            <p>主要功能：</p>
            <ul>
                <li>图片色彩分析</li>
                <li>亮度分布统计</li>
                <li>色彩卡片生成</li>
                <li>支持多种图片格式</li>
            </ul>

            <h3>【开发团队】</h3>
            <ul>
                <li>出品：浮晓 HXiao Studio</li>
                <li>开发：青山公仔</li>
                <li>代码：Trae</li>
                <li>联系邮箱：<a href="mailto:hxiao_studio@163.com">hxiao_studio@163.com</a></li>
            </ul>

            <h3>【开源项目使用说明】</h3>
            <ul>
                <li>
                    本程序基于 PySide6 架构开发，许可证：LGPL v3<br>
                    <span class="indent">版权所有：The Qt Company</span><br>
                    <span class="indent">项目地址：<a href="https://www.qt.io/">https://www.qt.io/</a></span>
                </li>
                <li style="margin-top: 12px;">
                    本程序 UI 组件使用 PyQt6-Fluent-Widgets，许可证：GPLv3<br>
                    <span class="indent">项目地址：<a href="https://github.com/zhiyiYo/PyQt-Fluent-Widgets">https://github.com/zhiyiYo/PyQt-Fluent-Widgets</a></span>
                </li>
            </ul>
        </body>
        </html>
        """
