# 标准库导入
from pathlib import Path

# 第三方库导入
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, PlainTextEdit, PushButton, isDarkTheme, qconfig

# 项目模块导入
from utils import tr, load_icon_universal, get_base_path
from version import version_manager
from dialogs.base_frameless_dialog import BaseFramelessDialog


class AboutDialog(BaseFramelessDialog):
    """关于对话框

    显示应用程序信息、版本信息、开发团队信息、
    相关链接和版权声明。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('dialogs.about.title'))
        self.setFixedSize(700, 550)

        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())

        # 设置自定义标题栏
        self._setup_title_bar()

        # 初始化样式
        self._update_styles()

        # 设置界面
        self.setup_ui()

        # 监听主题变化
        self._theme_connection = qconfig.themeChangedFinished.connect(
            self._update_styles
        )

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)

        # 内容区域
        self._create_content_area(layout)

        # 按钮区域
        self._create_buttons_area(layout)

        # 版权信息
        self._create_copyright(layout)

    def _create_content_area(self, parent_layout):
        """创建内容显示区域

        Args:
            parent_layout: 父布局对象
        """
        self.text_edit = PlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(self._get_about_text())
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.text_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        # 设置背景和边框透明，文字颜色根据主题变化
        text_color = "#ffffff" if isDarkTheme() else "#333333"
        self.text_edit.setStyleSheet(f"""
            PlainTextEdit {{
                background-color: transparent;
                border: none;
                color: {text_color};
            }}
            QPlainTextEdit {{
                background-color: transparent;
                border: none;
                color: {text_color};
            }}
        """)

        parent_layout.addWidget(self.text_edit, stretch=1)

    def _create_buttons_area(self, parent_layout):
        """创建按钮区域
        
        Args:
            parent_layout: 父布局对象
        """
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        buttons_layout.addStretch()
        
        # 官网按钮
        self.website_button = PushButton(tr('dialogs.about.website'))
        self.website_button.setMinimumWidth(90)
        self.website_button.clicked.connect(
            lambda: self._open_url("https://qingshangongzai.github.io/Color_Card/")
        )
        buttons_layout.addWidget(self.website_button)

        # 个人主页按钮
        self.homepage_button = PushButton(tr('dialogs.about.homepage'))
        self.homepage_button.setMinimumWidth(90)
        self.homepage_button.clicked.connect(
            lambda: self._open_url("https://space.bilibili.com/1232406878")
        )
        buttons_layout.addWidget(self.homepage_button)
        
        # 项目地址按钮
        self.project_button = PushButton(tr('dialogs.about.project'))
        self.project_button.setMinimumWidth(90)
        self.project_button.clicked.connect(
            lambda: self._open_url("https://gitee.com/qingshangongzai/color_card")
        )
        buttons_layout.addWidget(self.project_button)

        # 开源许可按钮
        self.license_button = PushButton(tr('dialogs.about.license'))
        self.license_button.setMinimumWidth(90)
        self.license_button.clicked.connect(self._open_license_file)
        buttons_layout.addWidget(self.license_button)
        
        # 用户协议按钮
        self.agreement_button = PushButton(tr('dialogs.about.agreement'))
        self.agreement_button.setMinimumWidth(90)
        self.agreement_button.clicked.connect(self._open_agreement_file)
        buttons_layout.addWidget(self.agreement_button)

        # 使用说明按钮
        self.tutorial_button = PushButton(tr('dialogs.about.tutorial'))
        self.tutorial_button.setMinimumWidth(90)
        self.tutorial_button.clicked.connect(
            lambda: self._open_url("https://www.bilibili.com/video/BV1vpckzhEH8/")
        )
        buttons_layout.addWidget(self.tutorial_button)

        buttons_layout.addStretch()
        
        parent_layout.addWidget(buttons_container)

    def _create_copyright(self, parent_layout):
        """创建版权信息
        
        Args:
            parent_layout: 父布局对象
        """
        app_info = version_manager.get_app_info()
        
        copyright_text = f"{tr('dialogs.about.copyright')} {app_info['copyright']}\n{tr('dialogs.about.license_note')}"
        copyright_label = CaptionLabel(copyright_text)
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        parent_layout.addWidget(copyright_label)

    def _open_url(self, url):
        """打开URL链接
        
        Args:
            url: 要打开的URL地址
        """
        QDesktopServices.openUrl(QUrl(url))

    def _open_file_or_url(self, filename: str, fallback_url: str) -> None:
        """打开本地文件，不存在则打开URL

        Args:
            filename: 文件名（位于 file/ 目录下）
            fallback_url: 文件不存在时的备用URL
        """
        file_path = Path(get_base_path()) / "file" / filename

        if file_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.absolute())))
        else:
            self._open_url(fallback_url)

    def _open_license_file(self) -> None:
        """打开开源许可文件"""
        self._open_file_or_url("LICENSE.html", "https://gitee.com/qingshangongzai/color_card")

    def _open_agreement_file(self) -> None:
        """打开用户协议文件"""
        self._open_file_or_url("UserAgreement.html", "https://gitee.com/qingshangongzai/color-card")

    def _get_about_text(self):
        """获取关于页面的文本内容"""
        return """　　取色卡（Color Card）是一款专为摄影师和设计师开发的图片分析及配色工具，旨在帮助摄影爱好者和专业人士快速分析图像的色彩分布、亮度信息等关键数据，并提供一站式的本地配色解决方案。

        项目功能设计借鉴参考了Adobe Color、色采、palettemakel等优秀的在线配色工具。

【开发团队】
  • 出品：浮晓 HXiao Studio
  • 开发：青山公仔
  • 代码：Trae、Qoder
  • logo绘制：智谱清言
  • 联系邮箱：hxiao_studio@163.com

【第三方开源库使用说明】
  • 本程序基于 PySide6 架构开发
    版权所有：The Qt Company
    Qt官网：https://www.qt.io/
    许可证：LGPL v3

  • 本程序 UI 组件使用 PySide6-Fluent-Widgets
    版权所有：zhiyiYo
    许可证：GPLv3
    项目地址：https://github.com/zhiyiYo/PyQt-Fluent-Widgets

  • 本程序使用 requests 库进行网络请求
    版权所有：Kenneth Reitz
    许可证：Apache-2.0
    项目地址：https://github.com/psf/requests

  • 本程序使用 Pillow 库处理图像
    版权所有：Python Imaging Library Team
    许可证：MIT-CMU License
    项目地址：https://github.com/python-pillow/Pillow
    官网：https://python-pillow.github.io/

  • 本程序使用 numpy 库进行数值计算
    版权所有：NumPy Developers
    许可证：BSD-3-Clause
    项目地址：https://github.com/numpy/numpy
    官网：https://numpy.org/

  • 本程序使用 PySideSix-Frameless-Window 实现对话框无边框窗口
    版权所有：zhiyiYo
    许可证：LGPLv3
    项目地址：https://github.com/zhiyiYo/PyQt-Frameless-Window

【开源配色方案使用说明】
  • Open Color 配色方案
    版权所有：heeyeun (Yeun)
    许可证：MIT License
    项目地址：https://github.com/yeun/open-color
    官网：https://yeun.github.io/open-color/

  • Nice Color Palettes 配色方案
    版权所有：Jam3
    许可证：MIT License
    项目地址：https://github.com/Experience-Monks/nice-color-palettes

  • Tailwind CSS Colors 配色方案
    版权所有：Tailwind Labs, Inc.
    许可证：MIT License
    项目地址：https://github.com/tailwindlabs/tailwindcss
    官网：https://tailwindcss.com

  • Material Design Colors 配色方案
    版权所有：Google LLC
    许可证：Apache License 2.0
    项目地址：https://m3.material.io/styles/color/system/overview

  • ColorBrewer 配色方案
    版权所有：Cynthia Brewer
    许可证：Apache License 2.0
    项目地址：https://colorbrewer2.org/
    官网：https://colorbrewer2.org/

  • Radix UI Colors 配色方案
    版权所有：WorkOS
    许可证：MIT License
    项目地址：https://www.radix-ui.com/colors

  • Nord 配色方案
    版权所有：Sven Greb
    许可证：MIT License
    项目地址：https://github.com/arcticicestudio/nord

  • Dracula 配色方案
    版权所有：Dracula Theme contributors
    许可证：MIT License
    项目地址：https://draculatheme.com/

  • Rosé Pine 配色方案
    版权所有：Rosé Pine 团队
    许可证：MIT License
    项目地址：https://github.com/rose-pine/rose-pine-theme

  • Solarized 配色方案
    版权所有：Ethan Schoonover
    许可证：MIT License
    项目地址：https://github.com/altercation/solarized

  • Catppuccin 配色方案
    版权所有：Catppuccin 团队
    许可证：MIT License
    项目地址：https://github.com/catppuccin/catppuccin
    官网：https://catppuccin.com/

  • Gruvbox 配色方案
    版权所有：Pavel Pertsev
    许可证：MIT License
    项目地址：https://github.com/morhetz/gruvbox

  • Tokyo Night 配色方案
    版权所有：enkia
    许可证：MIT License
    项目地址：https://github.com/enkia/tokyo-night-vscode-theme

【开发工具链】
  • 本程序使用 GitHub Actions 进行自动化构建
    服务提供：GitHub, Inc.
    官网：https://github.com/features/actions

  • 本程序使用 Nuitka 进行打包
    版权所有：Kay Hayen
    许可证：AGPLv3
    项目地址：https://github.com/Nuitka/Nuitka
    官网：https://nuitka.net/

  • 本程序 Windows 版本使用 Inno Setup 工具将独立的可执行文件打包为安装程序
    版权所有：Jordan Russell
    许可证：Modified BSD
    官网：https://jrsoftware.org/isinfo.php

【字体使用说明】
  • 本程序 LOGO 的标题使用了「得意黑」字体
    版权所有：© atelier-anchor
    设计师：oooooohmygosh
    许可证：SIL Open Font License 1.1
    项目地址：https://github.com/atelier-anchor/smiley-sans
    官方网站：https://atelier-anchor.com/typefaces/smiley-sans/

【特别鸣谢】
  • 感谢 PySide6 和 PyQt-Fluent-Widgets 开发团队提供的优秀框架
  • 感谢 Trae IDE 提供的 AI 辅助编程支持
  • 感谢Adobe Color、色采、palettemakel等优秀产品为我们提供的灵感和参考
  • 感谢Github 提供GitHub Actions 自动化构建服务
"""

    def closeEvent(self, event):
        """关闭事件"""
        super().closeEvent(event)  # 基类处理信号断开

    def contextMenuEvent(self, event):
        """屏蔽原生右键菜单"""
        event.ignore()
