"""安装器产物命名约定

同一取值在其他语言/配置中各有一份，改动时须同步：
- `Color Card.exe`：`build-windows.yml`（便携 job 的 --output-filename 为 "Color Card"，Nuitka 自动补 .exe）与 `launcher/launcher.c`（APP_EXE_NAME）
- `Color Card Payload.zip`：`build-windows.yml`（Prepare installer payload 的输出名与内嵌数据文件名）
载荷内 `app/` 前缀与 `.portable` 标记见 `installer/core/file_installer.py`、`app_mode.PORTABLE_LAYOUT_MARKER`。
"""

APP_EXE_NAME = "Color Card.exe"
PAYLOAD_ZIP_NAME = "Color Card Payload.zip"
