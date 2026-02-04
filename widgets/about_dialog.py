# 标准库导入
from pathlib import Path

# 第三方库导入
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFrame,
    QPlainTextEdit, QDialog
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QColor

from qfluentwidgets import (
    PushButton, PrimaryPushButton,
    CaptionLabel, isDarkTheme
)

# 项目模块导入
from version import version_manager
from icon_utils import load_icon_universal, fix_windows_taskbar_icon_for_window


def get_background_color():
    """获取主题背景颜色"""
    return QColor(32, 32, 32) if isDarkTheme() else QColor(255, 255, 255)


def get_text_color():
    """获取主题文本颜色"""
    return QColor(255, 255, 255) if isDarkTheme() else QColor(40, 40, 40)


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
        bg_color = get_background_color()
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color.name()}; }}")

        self.setup_ui()

        # 修复任务栏图标（在窗口显示后调用）
        QTimer.singleShot(100, lambda: fix_windows_taskbar_icon_for_window(self))

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
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(self._get_about_text())
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        # 设置主题感知的样式
        bg_color = get_background_color()
        text_color = get_text_color()
        self.text_edit.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {bg_color.name()}; "
            f"color: {text_color.name()}; border: none; }}"
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
            "基于 LGPL v3 开源，仅供学习交流使用"
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
  • 出品：{app_info['company']}
  • 开发：{app_info['developer']}
  • 代码：Trae
  • 联系邮箱：{app_info['email']}

【开源项目使用说明】
  • 本程序基于 PySide6 架构开发，许可证：LGPL v3
    版权所有：The Qt Company
    项目地址：https://www.qt.io/

  • 本程序 UI 组件使用 PySide6-Fluent-Widgets，许可证：GPLv3
    项目地址：https://github.com/zhiyiYo/PyQt-Fluent-Widgets

【特别鸣谢】
  • 感谢 PySide6 和 PyQt-Fluent-Widgets 开发团队提供的优秀框架
  • 感谢 Trae IDE 提供的 AI 辅助编程支持
"""

    def contextMenuEvent(self, event):
        """屏蔽原生右键菜单"""
        event.ignore()
