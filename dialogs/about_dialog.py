# 标准库导入
from pathlib import Path

# 第三方库导入
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QVBoxLayout, QWidget
)
from qfluentwidgets import CaptionLabel, PlainTextEdit, PrimaryPushButton, PushButton, isDarkTheme, qconfig

# 项目模块导入
from utils import fix_windows_taskbar_icon_for_window, load_icon_universal, set_window_title_bar_theme
from version import version_manager
from ui.theme_colors import get_dialog_bg_color, get_text_color


class AboutDialog(QDialog):
    """关于对话框

    显示应用程序信息、版本信息、开发团队信息、
    相关链接和版权声明。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(600, 550)

        # 设置窗口图标
        self.setWindowIcon(load_icon_universal())

        # 设置窗口标志：只保留关闭按钮（必须在设置窗口标题之后）
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.CustomizeWindowHint
        )

        # 设置窗口背景色（与 FluentWindow 一致）
        bg_color = get_dialog_bg_color()
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color.name()}; }}")

        self.setup_ui()

        # 修复任务栏图标（在窗口显示后调用）
        QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(self))

        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._update_title_bar_theme)

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
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
        # 禁用焦点，去除底部蓝色条
        self.text_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 设置主题感知的样式
        bg_color = get_dialog_bg_color()
        text_color = get_text_color()
        self.text_edit.setStyleSheet(
            f"PlainTextEdit {{ background-color: {bg_color.name()}; "
            f"color: {text_color.name()}; border: none; }}\n"
            f"PlainTextEdit:focus {{ border: none; outline: none; }}\n"
            f"PlainTextEdit::focus {{ border: none; }}\n"
            f"QPlainTextEdit {{ border: none; }}\n"
            f"QPlainTextEdit:focus {{ border: none; outline: none; }}"
        )
        
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
        
        # 个人主页按钮
        self.homepage_button = PushButton("个人主页")
        self.homepage_button.setMinimumWidth(90)
        self.homepage_button.clicked.connect(
            lambda: self._open_url("https://space.bilibili.com/1232406878")
        )
        buttons_layout.addWidget(self.homepage_button)
        
        # 项目地址按钮（主题色）
        self.project_button = PrimaryPushButton("项目地址")
        self.project_button.setMinimumWidth(90)
        self.project_button.clicked.connect(
            lambda: self._open_url("https://gitee.com/qingshangongzai/color_card")
        )
        buttons_layout.addWidget(self.project_button)

        # 开源许可按钮
        self.license_button = PushButton("开源许可")
        self.license_button.setMinimumWidth(90)
        self.license_button.clicked.connect(self._open_license_file)
        buttons_layout.addWidget(self.license_button)
        
        # 用户协议按钮
        self.agreement_button = PushButton("用户协议")
        self.agreement_button.setMinimumWidth(90)
        self.agreement_button.clicked.connect(self._open_agreement_file)
        buttons_layout.addWidget(self.agreement_button)
        
        buttons_layout.addStretch()
        
        parent_layout.addWidget(buttons_container)

    def _create_copyright(self, parent_layout):
        """创建版权信息
        
        Args:
            parent_layout: 父布局对象
        """
        app_info = version_manager.get_app_info()
        
        copyright_label = CaptionLabel(
            f"版权所有 {app_info['copyright']}\n"
            "基于 GPL v3 开源，仅供学习交流使用"
        )
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        parent_layout.addWidget(copyright_label)

    def _open_url(self, url):
        """打开URL链接
        
        Args:
            url: 要打开的URL地址
        """
        QDesktopServices.openUrl(QUrl(url))

    def _open_license_file(self):
        """打开开源许可文件"""
        # 获取许可证文件路径（相对于项目根目录的 file/LICENSE.html）
        license_path = Path(__file__).parent.parent / "file" / "LICENSE.html"
        
        if license_path.exists():
            # 转换为文件URL并打开
            file_url = QUrl.fromLocalFile(str(license_path.absolute()))
            QDesktopServices.openUrl(file_url)
        else:
            # 如果文件不存在，打开项目地址
            self._open_url("https://gitee.com/qingshangongzai/color_card")

    def _open_agreement_file(self):
        """打开用户协议文件"""
        # 获取用户协议文件路径（相对于项目根目录的 file/UserAgreement.html）
        agreement_path = Path(__file__).parent.parent / "file" / "UserAgreement.html"
        
        if agreement_path.exists():
            # 转换为文件URL并打开
            file_url = QUrl.fromLocalFile(str(agreement_path.absolute()))
            QDesktopServices.openUrl(file_url)
        else:
            # 如果文件不存在，打开项目地址
            self._open_url("https://gitee.com/qingshangongzai/color-card")

    def _get_about_text(self):
        """获取关于页面的文本内容"""
        app_info = version_manager.get_app_info()
        version = version_manager.get_version()

        return f"""　　取色卡（Color Card）是一款专为摄影师开发的图片分析小工具，旨在帮助摄影爱好者和专业人士快速分析图像的色彩分布、亮度信息等关键数据，辅助后期调色和色彩管理。

【开发团队】
  • 出品：浮晓 HXiao Studio
  • 开发：青山公仔
  • 代码：Trae、Qoder
  • logo绘制：青山公仔
  • 联系邮箱：hxiao_studio@163.com

【开源项目使用说明】
  • 本程序基于 PySide6 架构开发
    版权所有：The Qt Company
    许可证：LGPL v3
    项目地址：https://www.qt.io/

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
    许可证：MIT
    项目地址：https://github.com/python-pillow/Pillow

  • 本程序使用 numpy 库进行数值计算
    版权所有：NumPy Developers
    许可证：BSD-3-Clause
    项目地址：https://github.com/numpy/numpy

  • 本程序内置色彩使用 Open Color 配色方案
    版权所有：heeyeun (Yeun)
    许可证：MIT License
    项目地址：https://github.com/yeun/open-color

  • 本程序内置色彩使用 Nice Color Palettes 配色方案
    版权所有：Experience-Monks
    许可证：MIT License
    项目地址：https://github.com/Experience-Monks/nice-color-palettes

  • 本程序内置色彩使用 Tailwind CSS Colors 配色方案
    版权所有：Tailwind Labs, Inc.
    许可证：MIT License
    项目地址：https://github.com/tailwindlabs/tailwindcss

  • 本程序内置色彩使用 Material Design Colors 配色方案
    版权所有：Google LLC
    许可证：Apache License 2.0
    项目地址：https://m3.material.io/styles/color/system/overview

  • 本程序内置色彩使用 ColorBrewer 配色方案
    版权所有：Cynthia Brewer
    许可证：Apache License 2.0
    项目地址：https://colorbrewer2.org/

  • 本程序内置色彩使用 Radix UI Colors 配色方案
    版权所有：WorkOS
    许可证：MIT License
    项目地址：https://www.radix-ui.com/colors

  • 本程序内置色彩使用 Nord 配色方案
    版权所有：Sven Greb
    许可证：MIT License
    项目地址：https://github.com/arcticicestudio/nord

  • 本程序内置色彩使用 Dracula 配色方案
    版权所有：Dracula Theme contributors
    许可证：MIT License
    项目地址：https://draculatheme.com/

【开发工具链】
  • 本程序使用 auto-py-to-exe 工具打包为独立的可执行文件
    版权所有：Brent Vollebregt
    许可证：MIT
    项目地址：https://github.com/brentvollebregt/auto-py-to-exe

  • 本程序使用 UPX 工具压缩可执行文件体积
    版权所有：UPX Team
    许可证：GPL-2.0+
    官网：https://upx.github.io/

  • 本程序使用 Inno Setup 工具将独立的可执行文件打包为安装程序
    版权所有：Jordan Russell
    许可证：基于修改的 BSD 许可证
    官网：https://jrsoftware.org/isinfo.php

【特别鸣谢】
  • 感谢 PySide6 和 PyQt-Fluent-Widgets 开发团队提供的优秀框架
  • 感谢 Trae IDE 提供的 AI 辅助编程支持
"""

    def _update_title_bar_theme(self):
        """更新标题栏主题以适配当前主题"""
        set_window_title_bar_theme(self, isDarkTheme())

    def showEvent(self, event):
        """窗口显示事件 - 在显示前设置标题栏主题避免闪烁"""
        # 先设置标题栏主题（在父类 showEvent 之前）
        self._update_title_bar_theme()
        # 调用父类的 showEvent
        super().showEvent(event)

    def contextMenuEvent(self, event):
        """屏蔽原生右键菜单"""
        event.ignore()
