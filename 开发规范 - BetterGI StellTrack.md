# BetterGI 星轨开发规范

## 1. 概述

本规范旨在指导BetterGI 星轨项目的后续开发，确保代码的一致性、可维护性和可扩展性。规范基于现有的代码结构和设计文档，包括样式管理、事件处理、代码组织和开发实践等方面，适用于AI辅助开发和传统开发。

### 1.1 开发环境

- 主要使用IDE进行开发
- 支持传统文本编辑器 + 命令行工具组合
- 推荐使用VS Code、PyCharm进行开发
- 可以使用TRAE、Qoder、Curso等AI IDE进行辅助开发

### 1.2 开发协作规范

#### 1.2.1 代码备份规范

- 本地开发时应启用自动备份功能，建议使用**GitHub Desktop进行版本控制**
- 重要修改前应手动创建备份，确保数据安全
- 定期将本地代码推送到远程仓库，避免数据丢失
- 建议使用分支管理，避免直接在主分支上开发
- 定期清理无用分支，保持仓库整洁

#### 1.2.2 协作开发规范

- 无论是AI生成代码还是人工编写代码，都应明确版权归属
- 对所有代码进行充分测试和验证，确保功能正常
- 保持代码的可理解性，避免过度依赖复杂逻辑
- 定期进行代码审查，结合AI和人工审查，提高代码质量
- 利用代码分析工具，识别潜在的性能问题和安全风险
- 尊重其他开发者的工作，避免未经授权修改他人代码
- 及时响应问题和反馈，保持良好的沟通

### 1.3 兼容性要求

- 操作系统：仅兼容Win 10 64bit及以上系统
- Python版本：仅兼容Python 3.11及以上版本

## 2. 代码组织规范

### 2.1 文件命名规范

- 采用小写字母和下划线命名，如 `event_manager.py`
- 核心功能模块使用清晰的描述性名称
- 辅助功能模块使用 `utils.py`、`styles/` 等通用名称

### 2.2 模块划分

|模块类型 |职责 |示例文件 |
|:---:|:---:|:---:|
|核心模块 |应用入口和主流程，包括应用程序生命周期管理、环境配置和监控 |`main.py` |
|样式模块 |样式和字体管理，统一管理应用程序的外观样式 |`styles/` |
|工具模块 |通用工具和资源管理，提供各种辅助功能 |`utils.py` |
|UI模块 |界面组件和布局，包含主窗口和各种功能面板 |`main_window.py`、`ui/` |
|菜单模块 |菜单栏创建和管理，处理菜单项的状态和交互 |`managers/menu_manager.py` |
|对话框模块 |各类事件编辑对话框和调试对话框的实现 |`dialogs/` |
|调试模块 |调试工具和日志系统，用于开发和问题排查 |`dialogs/debug_tools.py` |
|版本模块 |版本信息管理，负责应用程序的版本信息和元数据 |`version.py` |
|事件模块 |事件处理和管理，处理事件的添加、编辑、删除等操作 |`managers/event_manager.py` |
|脚本模块 |脚本生成和管理，将事件序列转换为可执行脚本 |`managers/script_manager.py` |
|状态管理模块 |状态保存、加载、撤销和重做功能，处理事件数据的持久化 |`managers/state_manager.py` |
|时间分析模块 |事件时间分析功能，提供事件时间分布和统计 |`dialogs/time_analysis.py` |
|更新模块 |版本更新检查功能，从云端获取最新版本信息 |`dialogs/update_dialog.py` |
|关于模块 |关于窗口和用户协议相关功能 |`dialogs/about_window.py`、`dialogs/user_agreement.py` |

### 2.3 项目目录结构

```
BetterGI_StellTrack/
├── main.py                 # 应用程序主入口，负责生命周期管理、环境配置、监控和主窗口创建
├── version.py              # 版本管理器模块，负责管理应用程序的版本信息和元数据
├── main_window.py         # 主窗口类，包含界面布局和主要功能
├── ui/                    # UI模块目录，包含界面组件和面板
│   ├── __init__.py        # 统一导出接口
│   ├── widgets.py         # 自定义控件模块，包含现代化表格和标题栏等自定义控件
│   └── panels.py         # 面板组件模块，包含各种功能面板
├── dialogs/               # 对话框模块目录，包含各类对话框
│   ├── __init__.py        # 统一导出接口
│   ├── batch_dialog.py    # 批量编辑对话框模块，包含批量编辑事件功能
│   ├── debug_dialog.py     # 调试对话框模块，包含调试工具入口和彩蛋确认对话框
│   ├── event_dialogs.py   # 事件对话框模块，包含各种事件编辑对话框
│   ├── update_dialog.py   # 更新检查对话框模块，负责版本更新检查和云端数据同步
│   ├── time_analysis.py   # 时间分析对话框模块，提供事件时间分析功能
│   ├── debug_tools.py     # 调试工具对话框模块，包含调试相关功能
│   ├── user_agreement.py  # 用户协议对话框模块，包含用户协议确认和显示功能
│   └── about_window.py    # 关于窗口对话框模块，包含应用程序信息和相关链接
├── managers/              # 管理器模块目录，包含各类管理器
│   ├── __init__.py        # 统一导出接口
│   ├── menu_manager.py    # 菜单管理器模块，负责菜单栏创建和菜单状态管理
│   ├── state_manager.py   # 状态管理器模块，负责状态保存、加载、撤销和重做功能
│   ├── event_manager.py   # 事件管理模块，处理事件的添加、编辑、删除等
│   └── script_manager.py  # 脚本管理模块，负责脚本的生成和保存
├── styles/                 # 样式管理模块，定义应用程序的外观样式
│   ├── __init__.py        # 统一导出接口
│   ├── fonts.py           # 字体管理模块
│   ├── themes.py          # 主题管理模块
│   ├── widgets.py         # 控件和混入模块
│   └── dialogs.py         # 对话框和消息框模块
├── utils.py                # 工具函数模块，提供各种辅助功能
├── requirements.txt        # 项目依赖列表
├── .gitignore              # Git忽略文件配置
├── version_info.txt        # 版本信息文本文件
├── README.md               # 项目说明文档
├── file/                   # 文件资源目录
│   ├── LICENSE.html            # 许可证文件
│   ├── UserAgreement.html      # 用户协议文件
│   └── 使用说明.pdf
├── fonts/                  # 字体文件目录
│   ├── SmileySans-Oblique.ttf
│   └── SourceHanSerifCN-Regular-1.otf
├── logo/                   # Logo资源目录
│   ├── logo.ico
│   └── logo.png
└── 规范/                   # 开发规范目录
    ├── 事件处理逻辑.md
    ├── 开发规范.md
    ├── 设计语言规范.md
    └── 代码审查分析报告.md
```

### 2.4 导入规范

- 按模块类型分组导入，先导入系统模块，再导入第三方模块，最后导入项目模块
- 使用相对导入或绝对导入，保持一致
- 避免循环导入，核心模块应依赖底层模块，而不是相反
- 导入语句应使用 `isort` 工具进行格式化，确保导入顺序一致

#### 2.4.1 导入规范化经验

基于代码规范化重构实践，以下经验可提高导入语句的可维护性：

**导入顺序和分组**：
- 按照"标准库模块 → 第三方模块 → 项目模块"的顺序分组
- 添加清晰的分组注释，如"# 标准库模块导入"、"# 第三方模块导入"、"# 项目模块导入"
- 示例：
```python
# 标准库模块导入
import os
import sys
from datetime import datetime

# 第三方模块导入
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 项目模块导入
from version import version_manager
from styles import UnifiedStyleHelper
```

**导入清理**：
- 移除重复导入，合并同一模块的多次导入
- 将方法内部的导入移到文件顶部
- 删除未使用的导入
- 示例：
```python
# 修改前
from styles import UnifiedStyleHelper
from styles import get_global_font_manager

# 修改后
from styles import UnifiedStyleHelper, get_global_font_manager
```

**导入格式化**：
- 使用 `isort` 工具进行格式化
- 确保导入语句对齐整齐
- 保持导入顺序一致

## 3. 基本开发规范

### 3.1 代码编写规范

- 遵循 PEP 8 代码风格规范
- 使用清晰、有意义的变量和函数命名，避免使用缩写或晦涩的名称
- 保持函数和类的单一职责原则，避免过长或复杂的函数
- 代码应具有良好的可读性，适当的缩进和空格
- 严格避免重复代码，使用函数或类来封装重复逻辑
- 定期检查并清除冗余代码，包括未使用的变量、函数、导入和注释
- 保持代码简洁，删除无用的调试代码和临时测试代码
- **当修改现有代码时，应同步检查并清除相关的重复冗余代码**

#### 3.1.1 代码格式统一经验

基于代码规范化重构实践，以下经验可提高代码格式的一致性：

**空行管理**：
- 统一方法之间的空行（保持2个空行）
- 移除不必要的空行（如方法内部、导入语句后）
- 移除文件末尾的多余空行
- 示例：
```python
# 修改前
def open_url(self, url):

    """打开URL链接"""

    try:

        QDesktopServices.openUrl(QUrl(url))

# 修改后
def open_url(self, url):
    """打开URL链接"""
    try:
        QDesktopServices.openUrl(QUrl(url))
```

**注释风格统一**：
- 统一注释风格，全部使用中文
- 优化代码缩进和格式
- 保持代码格式一致

#### 3.1.2 常量管理经验

基于代码规范化重构实践，以下经验可提高常量管理的可维护性：

**常量提取和命名**：
- 提取常量到文件顶部，便于统一管理和维护
- 将硬编码字符串改为使用常量
- 常量命名应清晰、有意义
- 按功能分组组织常量
- 示例：
```python
# 文件顶部常量区域
DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # Windows DWM API 沉浸式深色模式标志
RESOURCE_DIRS = ["assets", "fonts", "file", "logo"]
ICON_FILES = ["logo.ico", "logo.png"]
LOGO_FILE = "logo.png"
APP_NAME = "BetterGI StellTrack"
SCRIPT_DEFAULT_DIR = "scripts"

def set_window_title_bar_theme(window, is_dark=False):
    # 使用常量
    value = ctypes.c_int(1 if is_dark else 0)
    result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_USE_IMMERSIVE_DARK_MODE,
        ctypes.byref(value),
        ctypes.sizeof(value)
    )
```

#### 3.1.3 命名规范经验

基于代码规范化重构实践，以下经验可提高命名的一致性：

**类命名规范**：
- 类名应使用驼峰命名（CamelCase），符合 PEP 8 规范
- 避免使用小写命名类
- 示例：
```python
# 修改前
class batch_operation:
    """批量操作上下文管理器"""
    pass

# 修改后
class BatchOperation:
    """批量操作上下文管理器"""
    pass
```

**函数和变量命名规范**：
- 函数和变量使用小写字母和下划线命名
- 使用清晰、有意义的名称，避免使用缩写或晦涩的名称

#### 3.1.4 代码清理经验

基于代码规范化重构实践，以下经验可提高代码的整洁度：

**清理未使用代码**：
- 删除未使用的变量、函数、导入和注释
- 保持代码简洁，删除无用的调试代码和临时测试代码
- 定期检查并清除冗余代码
- 修改现有代码时，应同步检查并清除相关的重复冗余代码
- 示例：
```python
# 修改前
import json
import re

# 修改后（删除未使用的导入）
# import json
# import re
```

**清理冗余代码**：
- 合并重复的逻辑和相似的功能
- 提高代码复用性
- 保持代码简洁

#### 3.1.5 代码结构组织经验

基于代码规范化重构实践，以下经验可提高代码结构的清晰度：

**代码结构分隔**：
- 统一代码结构分隔注释的对齐方式
- 保持清晰的代码结构划分
- 使用注释分隔不同功能的代码块
- 示例：
```python
# =============================================================================
# 事件类型转换和按键名称生成函数
# =============================================================================
```

**代码组织原则**：
- 按功能分组组织代码
- 保持代码逻辑清晰
- 使用合理的缩进和空格

### 3.2 代码审查规范

- 所有代码在合并前必须经过代码审查
- 代码审查应关注代码质量、安全性、可读性和性能
- 审查者应提出具体的改进建议，避免模糊的反馈
- 作者应及时响应审查意见，进行必要的修改

### 3.3 分支管理规范

- 主分支（main）：稳定版本，仅用于发布
- 开发分支（Dev）：用于集成新功能和修复bug
- 功能分支：用于开发新功能，命名格式：`feature/feature-name`
- bug修复分支：用于修复bug，命名格式：`fix/bug-description`
- 分支应定期同步主分支和开发分支的代码

### 3.4 提交信息规范

#### 3.4.1 日常提交格式

- 提交信息应清晰、简洁，描述本次提交的主要内容
- 提交信息标题格式：`[类型] 详细描述`
- 类型包括：
  - `新功能`：新增功能或特性
  - `修复bug`：修复代码中的错误
  - `内容调整`：如替换链接、修改文本等
  - `文档更新`：修改或新增文档
  - `样式修改`：代码样式调整，不影响功能
  - `重构`：代码结构调整，不影响功能
  - `优化`：在不改变功能的前提下，提升代码或系统的性能、效率或用户体验的改进
  - `测试`：新增或修改测试代码
  - `构建变更`：修改依赖、构建脚本等
  - `配置变更`：修改配置文件

#### 3.4.2 Pull Request提交格式

Pull Request提交分为两种情况：日常修改/调整和版本更新。

##### 3.4.2.1 日常修改/调整（提交到Dev分支）

- 适用场景：日常调整、增加新功能、修复bug等
- 所有日常修改和调整都直接提交到Dev分支
- Pull Request标题格式：`[类型] 详细描述`
- Pull Request正文应包含：
  - 修改内容的详细描述
  - 修改的理由和目的
  - 测试情况
  - 相关Issue或参考链接（如果有）
- 无需包含开发者署名，Pull Request会自动记录创建者信息

##### 3.4.2.2 版本更新（合并到主分支）

- 适用场景：一次性合并很多内容到主分支，进行版本发布
- 由项目维护者执行，从Dev分支合并到主分支
- Pull Request标题格式：直接使用版本号，如 `3.5.0`
- Pull Request正文格式：`[类型] 详细描述`
- Pull Request正文应包含：
  - 版本更新的主要内容和变更
  - 新增功能列表
  - 修复的bug列表
- Pull Request需包含开发者署名

#### 3.4.3 提交信息示例


1. **日常提交示例**：
   - `[内容调整] 将关于页面的项目地址按钮从GitHub替换为Gitee`
   - `[修复bug] 修复登录功能的验证逻辑错误`
   - `[新功能] 新增用户管理功能`
   - `[文档更新] 更新README.md中的安装指南`
2. **Pull Request示例**：

   ##### 2.1 日常修改/调整（提交到Dev分支）
   - 标题：`[内容调整] 将关于页面的项目地址按钮从GitHub替换为Gitee`
   - 正文：

     ```
     修改内容：将关于页面的项目地址按钮从GitHub替换为Gitee
     修改理由：考虑到国内用户访问Gitee更稳定
     测试情况：已在本地测试，功能正常
     相关Issue：无
     ```

   ##### 2.2 版本更新（合并到主分支）
   - 标题：`3.5.0`
   - 正文：

     ```
     【修复bug】修复了安装版无法正常创建、读取日志文件的问题，将数据存储目录修改至用户数据目录下；
     【修复bug】修复了大部分情况下打开新窗口、弹窗会闪烁的bug；
     【样式修改】增加了窗口、弹窗的打开、关闭的过渡动画；
     【样式修改】修改了滚动条的样式；
     【样式修改】调整了关于页面文本框内字体的大小；
     【内容调整】将关于页面的项目地址按钮从GitHub替换为Gitee；
     【更新文档】更新了说明文档、设计语言规范和开发规范。
     ```

### 3.5 测试规范

- 为新功能编写单元测试，确保代码的正确性
- 编写集成测试，验证模块间的协作是否正常
- 编写端到端测试，验证整个系统的功能
- 测试覆盖率应达到70%以上
- 定期运行测试套件，确保所有测试通过

### 3.6 性能优化规范

- 关注代码的性能，避免不必要的计算和资源消耗
- 使用适当的数据结构和算法
- 避免在循环中进行复杂的操作
- 定期进行性能测试，识别瓶颈并进行优化
- 优化应基于实际测试数据，避免过早优化

#### 3.6.1 缓存优化经验

基于性能优化实践，以下经验可提高缓存优化的效果：

**缓存应用原则**：
- 缓存计算结果，避免重复计算和I/O操作
- 缓存查找结果，减少重复查找的性能开销
- 缓存应在数据变化时自动失效，确保数据一致性
- 缓存应验证有效性，避免返回过期或无效数据

**缓存实现示例**：
```python
# 文件查找缓存
_file_find_cache = {}

def find_resource_file(filename):
    # 检查缓存
    if filename in _file_find_cache:
        cached_path = _file_find_cache[filename]
        if cached_path and os.path.exists(cached_path):
            return cached_path
        else:
            del _file_find_cache[filename]
    
    # 执行查找
    full_path = _search_file(filename)
    if full_path:
        # 缓存查找结果
        _file_find_cache[filename] = full_path
    
    return full_path
```

**缓存清理策略**：
- 基础环境变化时清空缓存（如工作目录变化）
- 定期清理过期缓存，避免内存占用过大
- 提供手动清理缓存的接口，便于调试

#### 3.6.2 PyQt UI性能优化经验

基于PyQt性能优化实践，以下经验可提高UI响应速度：

**减少UI重绘**：
- 批量更新UI控件时，使用 `setUpdatesEnabled(False/True)` 包裹更新操作
- 避免在循环中频繁更新UI，先收集数据再批量更新
- 使用 `try-finally` 确保 `setUpdatesEnabled(True)` 一定会执行

**示例代码**：
```python
def update_table_data(self):
    """批量更新表格数据 - 优化版本"""
    self.table.setUpdatesEnabled(False)
    
    try:
        for row in range(self.table.rowCount()):
            # 更新表格数据
            self.table.setItem(row, 0, item)
    finally:
        # 确保重新启用更新
        self.table.setUpdatesEnabled(True)
```

**数据结构优化**：
- 将列表转换为集合，将查找时间复杂度从 O(n) 降到 O(1)
- 批量操作时使用集合进行成员判断，避免线性查找

**示例代码**：
```python
# 优化前：列表查找，时间复杂度O(n)
for row in range(table.rowCount()):
    if row in show_rows:  # 每次查找都需要遍历列表
        table.setRowHidden(row, False)

# 优化后：集合查找，时间复杂度O(1)
show_rows_set = set(show_rows)
for row in range(table.rowCount()):
    if row in show_rows_set:  # 直接哈希查找，无需遍历
        table.setRowHidden(row, False)
```

**字典查找优化**：
- 合并多个字典查找为一次查找，减少重复计算
- 预先构建合并映射表，避免运行时重复查找

**示例代码**：
```python
# 优化前：两次字典查找
key_name = VK_MAPPING.get(keycode_int, f"键码:{keycode}")
key_name_cn = KEY_NAME_MAPPING.get(key_name, key_name)

# 优化后：一次查找
_COMBINED_KEY_MAPPING = {
    vk: KEY_NAME_MAPPING.get(name, name)
    for vk, name in VK_MAPPING.items()
}
key_name_cn = _COMBINED_KEY_MAPPING.get(keycode_int, keycode)
```

### 3.7 文档编写规范

- 为所有公共函数和类编写文档字符串
- 文档应包含功能描述、参数说明、返回值说明和示例
- 复杂逻辑应添加注释说明
- 文档应保持最新，与代码同步更新

### 3.8 协作开发规范

- 定期进行团队会议，讨论项目进展和问题
- 使用版本控制工具管理代码变更
- 遵循项目的开发流程和规范
- 尊重其他开发者的工作，避免未经授权修改他人代码
- 及时响应问题和反馈

## 4. AI辅助开发规范

### 4.1 AI代码生成规范

- 使用AI工具生成代码时，应确保生成的代码符合本项目的代码规范和命名约定
- 对AI生成的代码进行充分审查，确保其质量、安全性和可维护性
- 避免过度依赖AI生成复杂逻辑，关键算法和核心功能应进行人工验证
- 生成代码后，应添加适当的文档字符串和注释，便于后续维护

### 4.2 AI辅助调试与测试

- 使用AI工具的调试功能进行代码调试时，应遵循本项目的调试规范
- 对AI生成的代码进行完整的测试，包括单元测试和集成测试
- 利用AI工具的测试生成功能，为关键功能生成测试用例
- 测试结果应记录，确保功能正常运行

### 4.3 AI辅助协作开发

- 在团队协作中，应明确AI生成代码的归属和责任
- 使用AI工具的版本控制集成功能，确保代码变更的可追溯性
- 定期进行代码审查，结合AI和人工审查，提高代码质量
- 利用AI工具的代码分析功能，识别潜在的性能问题和安全风险

## 5. 样式统一引用规范

### 5.1 样式管理原则

- 统一使用 `UnifiedStyleHelper` 类管理所有控件样式
- 禁止在代码中硬编码样式值，所有样式应从样式管理器获取
- 样式定义应与 `设计语言规范.md` 保持一致

### 5.2 颜色使用规范

- 所有颜色应通过 `UnifiedStyleHelper.get_instance().COLORS` 获取
- 禁止在代码中直接使用颜色值，如 `#ffffff`
- 颜色常量定义在 `styles/themes.py` 的 `COLORS` 字典中

```python
# 正确用法
from styles import UnifiedStyleHelper
style_helper = UnifiedStyleHelper.get_instance()
label.setStyleSheet(f"color: {style_helper.COLORS['primary']};")

# 错误用法
label.setStyleSheet("color: #66ccff;")
```

### 5.3 字体使用规范

- 统一使用 `GlobalFontManager` 管理字体
- 获取得意黑字体：`font_manager.get_smiley_font(size, weight)`
- 获取思源宋体：`font_manager.get_source_han_font(size, weight)`
- 禁止直接创建字体对象，如 `QFont("Arial", 12)`

### 5.4 控件样式规范

- 使用 `UnifiedStyleHelper` 中定义的方法获取控件样式
- 自定义控件样式应遵循设计语言规范
- 新控件应添加到 `styles/` 目录中，与现有控件样式保持一致

### 5.5 图标使用规范

- 统一使用 `utils.py` 中的 `load_icon_universal()` 加载文件图标
- 图标文件应放在项目根目录或 `assets` 目录下
- 禁止在代码中硬编码图标路径

#### 5.5.1 Emoji图标使用规范

- GroupBox标题应使用Emoji图标增强视觉识别性
- Emoji图标选择应遵循功能匹配原则，参考设计语言规范中的分组框图标规范
- 常用Emoji图标包括：📋（信息）、📊（统计）、⚙️（设置）、🔄（循环）、🖥️（窗口）、📍（坐标）、⏱️（时间）、📌（位置）、📁（文件）、📝（编辑）、🧪（测试）等
- 禁止在GroupBox标题中使用不相关或含义模糊的Emoji图标
- 主标题和重要标题应保持简洁，避免使用Emoji图标造成视觉干扰
- Emoji图标应放在标题文本开头，格式为："图标 + 空格 + 标题文本"

## 6. 事件处理规范

### 6.1 事件数据结构

- 严格遵循 `事件处理逻辑.md` 中定义的事件数据结构
- 事件属性包括：序号、事件名称、事件类型、键码、X坐标、Y坐标、相对偏移时间、绝对偏移时间
- 事件类型转换通过 `utils.py` 中的转换函数处理

### 6.2 事件操作规范

- 事件创建、编辑、删除、复制粘贴等操作应通过 `EventManager` 类统一处理
- 时间计算应遵循 `绝对时间(n) = 绝对时间(n-1) + 相对时间(n)` 公式
- 批量操作应使用线程处理，避免UI阻塞
- 事件排序应使用 `SortEventsThread` 线程，避免UI阻塞

### 6.3 事件脚本生成

- 脚本生成通过 `script_manager.py` 处理
- 生成的脚本格式应符合 `事件处理逻辑.md` 中定义的JSON格式
- 脚本生成前应进行事件成对性检查

## 7. 新功能开发规范

### 7.1 需求分析

- 新功能应符合项目的整体定位和架构
- 功能需求应明确，包含详细的业务逻辑和UI设计
- 评估功能对现有代码的影响范围

### 7.2 设计规范

- 遵循单一职责原则，每个类和函数只负责一个功能
- 遵循依赖倒置原则，高层模块依赖抽象，不依赖具体实现
- 设计应考虑扩展性，便于未来功能扩展
- 避免过度设计，保持简单清晰

### 7.3 实现规范

- 新功能应放在合适的模块中，避免代码冗余
- 核心功能应添加到对应的核心模块
- 辅助功能应添加到 `utils.py` 或其他辅助模块
- 新控件应继承自现有基础控件，保持样式一致

### 7.4 测试规范

- 新功能应进行充分测试，包括功能测试和边界测试
- 测试应覆盖正常流程和异常流程
- 性能敏感功能应进行性能测试
- 测试结果应记录，确保功能稳定

## 8. 代码修改规范

### 8.1 代码修改原则

- 小步修改，每次修改应专注于一个功能点
- 保持向后兼容，避免破坏现有功能
- 修改前应备份代码，或使用版本控制
- 修改后应进行测试，确保功能正常
- 修改内容后必须清除相关的重复冗余代码，确保代码整洁
- 检查并删除未使用的导入、变量、函数和类
- 合并重复的逻辑和相似的功能，提高代码复用性

### 8.2 注释规范

- 关键函数和类应添加文档字符串
- 复杂逻辑应添加注释说明
- 注释应清晰、简洁，避免冗余
- 注释应使用中文，保持一致性

#### 8.2.1 文档字符串规范化经验

基于代码规范化重构实践，以下经验可提高文档字符串的质量和一致性：

**文档字符串精简**：
- 精简文档字符串，避免冗余，将多行简化为单行格式
- 模块文档字符串应简洁清晰，说明模块用途和导出内容
- 示例：
```python
# 修改前
class VersionManager:
    """
    应用程序版本管理器
    
    负责管理应用程序的版本信息和应用元数据，提供统一的版本访问接口，
    确保整个应用程序使用一致的版本信息。
    """

# 修改后
class VersionManager:
    """应用程序版本管理器，负责管理应用程序的版本信息和应用元数据"""
```

**文档字符串完整性**：
- 为所有公共类和方法添加完整的文档字符串
- 使用 Google 风格，包含 Args、Returns、Note 等信息
- 保持文档字符串格式统一
- 示例：
```python
def set_delete_logic(self, logic):
    """设置删除事件逻辑
    
    设置删除事件时的处理逻辑，并更新菜单状态和保存设置。
    
    Args:
        logic (str): 删除逻辑，可选值为 'prompt'、'current' 或 'recalculate'
    """
    self.parent_window.delete_logic = logic
```

**模块文档字符串**：
- 模块文档字符串应说明模块的用途和导出内容
- 文档字符串简洁清晰
- 示例：
```python
"""样式模块，统一导出所有样式相关的类和函数

本模块提供了应用程序的样式管理功能，包括字体管理、主题管理、控件样式和对话框样式。
"""
```

### 8.3 异常处理

- 所有异常应被捕获并适当处理
- 异常信息应详细，便于调试
- 关键操作应记录日志
- 避免使用裸 `except` 语句，应指定具体异常类型

#### 8.3.1 异常处理规范化经验

基于代码规范化重构实践，以下经验可提高异常处理的质量和可维护性：

**指定具体异常类型**：
- 避免使用裸 `except:` 语句
- 避免使用裸 `except Exception:` 语句
- 应指定具体异常类型，如 `except (OSError, ValueError):`
- 示例：
```python
# 修改前
try:
    self.last_theme_change_time = time.strftime("%Y-%m-%d %H:%M:%S")
except Exception:
    self.last_theme_change_time = None

# 修改后
try:
    self.last_theme_change_time = time.strftime("%Y-%m-%d %H:%M:%S")
except (OSError, ValueError):
    self.last_theme_change_time = None
```

**异常信息详细化**：
- 异常信息应详细，便于调试
- 记录足够的上下文信息
- 示例：
```python
try:
    QDesktopServices.openUrl(QUrl(url))
except Exception as e:
    error_msg = f"打开链接失败: {str(e)}"
    self.debug_logger.log_error(error_msg)
    ChineseMessageBox.show_error(self, "错误", f"无法打开链接:\n{url}")
```

**异常处理原则**：
- 只捕获能够处理的异常
- 不要捕获所有异常，避免隐藏错误
- 关键操作应记录日志
- 提供合理的错误提示给用户

## 9. 样式开发规范

### 9.1 样式定义

- 所有样式应在 `styles/` 目录中统一定义
- 样式应遵循 `设计语言规范.md` 中的颜色、字体和间距规范
- 新控件样式应与现有控件样式保持一致
- 样式应使用变量，便于主题切换

### 9.2 样式应用

- 控件样式应通过 `UnifiedStyleHelper` 统一应用
- 禁止在代码中硬编码样式
- 样式应考虑不同平台的兼容性
- 复杂样式应进行测试,确保显示正常

### 9.3 对话框按钮宽度规范

- 所有对话框和弹窗底部的操作按钮(如确认、取消、打开等)宽度应统一设置为**100px**
- 应使用 `DialogFactory.create_ok_cancel_buttons` 方法创建按钮,该方法会自动设置按钮宽度
- 如果手动创建按钮,必须调用 `setFixedWidth(100)` 设置宽度
- 所有消息框按钮(确定、是、否等)均需遵守此规范

### 9.4 响应式布局规范

- 界面布局应支持响应式设计，能够适应不同窗口尺寸和屏幕分辨率
- 主窗口和对话框应设置合理的最小尺寸，确保在小屏幕下仍能正常使用
- 使用 `QSizePolicy` 控制控件的大小行为，避免使用固定尺寸
- 对于可调整大小的窗口，应使用 `setMinimumSize()` 和 `setMaximumSize()` 设置合理的尺寸范围
- Splitter 组件应避免使用固定尺寸，改用相对比例或弹性布局
- 长内容区域应使用 `QScrollArea` 包装，确保内容可访问
- 控件布局应使用 `addStretch()` 添加弹性空间，实现自适应排列
- 表格和列表应设置适当的列宽策略，支持内容自适应

#### 响应式布局实现原则


1. **尺寸策略设置**
   - 固定尺寸控件：使用 `setFixedWidth()` 和 `setFixedHeight()`
   - 弹性尺寸控件：使用 `setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)`
   - 最小尺寸约束：使用 `setMinimumWidth()` 和 `setMinimumHeight()`
   - 最大尺寸约束：使用 `setMaximumWidth()` 和 `setMaximumHeight()`
2. **布局管理器使用**
   - 水平布局：使用 `QHBoxLayout` 配合 `addStretch()` 实现居中和自适应
   - 垂直布局：使用 `QVBoxLayout` 配合 `addStretch()` 实现垂直分布
   - 网格布局：使用 `QGridLayout` 实现精确对齐，设置合理的间距
   - 分割器：使用 `QSplitter` 实现可调整大小的面板布局
3. **滚动区域应用**
   - 对话框内容区域应使用 `QScrollArea` 包装
   - 设置 `setWidgetResizable(True)` 使内容自适应
   - 合理设置滚动条策略：`ScrollBarAsNeeded` 或 `ScrollBarAlwaysOff`

#### 响应式布局示例

```python
# 正确的响应式布局示例
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy

# 设置容器尺寸策略
container = QWidget()
container.setMinimumWidth(200)
container.setMaximumWidth(450)
container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

# 创建弹性布局
layout = QVBoxLayout(container)
layout.setSpacing(12)
layout.setContentsMargins(8, 8, 8, 8)

# 添加控件
widget = QWidget()
widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
layout.addWidget(widget)

# 添加弹性空间
layout.addStretch()

# 水平居中布局
button_layout = QHBoxLayout()
button_layout.addStretch()  # 左侧弹性空间
button_layout.addWidget(ok_button)
button_layout.addWidget(cancel_button)
button_layout.addStretch()  # 右侧弹性空间
```

### 9.5 DPI处理规范

- 应用程序应支持动态DPI获取，能够在不重启的情况下适应系统DPI变化
- 推荐使用Windows 8.1+引入的 `GetDpiForMonitor` API获取DPI，替代传统的 `GetDeviceCaps` 方法
- DPI获取应封装为独立方法，便于统一管理和维护
- 动态DPI变化时，应能正确更新相关设置和UI元素
- DPI获取方法应包含适当的错误处理和回退机制

#### DPI获取实现原则


1. **API选择**
   - 优先使用 `GetDpiForMonitor` API获取DPI，支持动态获取
   - 当 `GetDpiForMonitor` 调用失败时，应回退使用 `GetDeviceCaps` 方法
   - 确保API调用的安全性和兼容性
2. **实现方法**
   - 在 `main_window.py` 中使用封装的 `get_system_scale` 方法获取DPI
   - 方法应返回标准的DPI百分比值（如"100%"、"125%"等）
   - 支持四舍五入到最接近的标准DPI值
3. **动态更新**
   - 只有在用户手动触发时才更新DPI设置，避免自动覆盖保存的设置
   - 保存的DPI设置应优先于自动获取的DPI值
   - DPI变化时，通过点击"获取屏幕分辨率和缩放"按钮获取新的DPI值
4. **错误处理**
   - 对API调用可能出现的异常进行捕获和处理
   - 提供合理的默认值（如96 DPI = 100%）
   - 记录详细的日志信息，便于调试和问题追踪

#### DPI获取实现示例

```python
def get_system_scale(self):
    """获取系统缩放比例，支持动态DPI变化"""
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        shcore = ctypes.windll.shcore
        
        # DPI类型
        MDT_EFFECTIVE_DPI = 0
        
        logical_dpi_x = 96  # 默认DPI
        
        # 方法1: 使用GetDpiForMonitor API获取当前DPI
        try:
            # 获取主显示器句柄
            monitor = user32.MonitorFromWindow(0, 1)  # MONITOR_DEFAULTTOPRIMARY
            
            if monitor:
                # 定义输出参数
                dpi_x = ctypes.c_uint()
                dpi_y = ctypes.c_uint()
                
                # 调用GetDpiForMonitor获取DPI
                result = shcore.GetDpiForMonitor(monitor, MDT_EFFECTIVE_DPI, 
                                               ctypes.byref(dpi_x), ctypes.byref(dpi_y))
                
                if result == 0:  # S_OK
                    logical_dpi_x = dpi_x.value
        except Exception as inner_e:
            # API调用失败，使用备用方法
            pass
        
        # 方法2: 备用方法，使用GetDeviceCaps获取DPI
        if logical_dpi_x == 96:
            try:
                hdc = user32.GetDC(0)
                if hdc:
                    logical_dpi_x = gdi32.GetDeviceCaps(hdc, 88)   # LOGPIXELSX
                    user32.ReleaseDC(0, hdc)
            except Exception:
                pass
        
        # 计算缩放比例（基于96 DPI为100%）
        if logical_dpi_x > 0:
            scale_percent = int((logical_dpi_x / 96.0) * 100)
            
            # 四舍五入到最接近的标准值
            standard_scales = [100, 125, 150, 175, 200, 225, 250]
            differences = [abs(scale_percent - standard) for standard in standard_scales]
            closest_index = differences.index(min(differences))
            scale = standard_scales[closest_index]
        else:
            scale = 100
        
        return f"{scale}%"
    except Exception:
        return "100%"
```

### 9.5.1 DPI自适应窗口高度

#### 概述

DPI自适应窗口高度是指根据系统DPI设置和屏幕可用空间自动调整主窗口高度，确保在不同缩放比例下都能提供一致的用户体验。

#### 实现原则

1. **动态高度计算**：窗口高度应根据系统DPI缩放比例进行动态调整
2. **合理高度限制**：设置最大高度为屏幕高度的85%，防止窗口占满整个屏幕
3. **最小高度保证**：保持最小高度为500px，确保UI的可用性
4. **异常处理机制**：在获取DPI失败时提供合理的回退值
5. **日志记录**：记录DPI计算过程，便于调试和问题追踪

#### 实现方法

##### 主窗口初始化

在主窗口初始化时，应使用自适应高度而非固定高度：

```python
# 计算自适应窗口高度
adaptive_height = calculate_adaptive_height(790, self)
self.resize(1200, adaptive_height)
```

##### 窗口高度计算方法

使用 `utils.py` 中的 `calculate_adaptive_height` 公共函数：

```python
def calculate_adaptive_height(base_height, parent_window=None):
    """计算自适应窗口/对话框高度，考虑DPI缩放和屏幕可用空间
    
    Args:
        base_height (int): 基础高度（100% DPI下的理想高度）
        parent_window (QWidget): 父窗口实例，用于获取DPI信息
    
    Returns:
        int: 计算得出的窗口/对话框高度
    """
    try:
        # 获取系统DPI缩放比例
        scale_percent = 100  # 默认值
        
        # 尝试从父窗口获取DPI信息
        if parent_window and hasattr(parent_window, 'settings_panel'):
            try:
                settings_panel = parent_window.settings_panel
                if settings_panel:
                    scale_text = settings_panel.scale_combo.currentText()
                    scale_percent = int(scale_text.strip('%'))
            except Exception:
                scale_percent = 100
        
        # 获取主屏幕信息
        screen = QApplication.primaryScreen()
        if not screen:
            return base_height  # 返回基础高度
        
        # 获取屏幕可用几何尺寸（排除任务栏）
        available_geometry = screen.availableGeometry()
        screen_height = available_geometry.height()
        
        # 根据DPI缩放调整基础高度
        dpi_factor = scale_percent / 100.0
        scaled_height = int(base_height * dpi_factor)
        
        # 设置最大高度为屏幕高度的85%，确保窗口不会占满整个屏幕
        max_height = int(screen_height * 0.85)
        
        # 设置最小高度，确保UI可用性
        min_height = int(base_height * 0.5)
        
        # 计算最终高度
        final_height = min(max(scaled_height, min_height), max_height)
        
        return final_height
        
    except Exception as e:
        # 如果计算失败，返回基础高度
        return base_height
```

##### DPI变化响应

实现 `adjust_window_size_for_dpi_change` 方法，用于在DPI变化时动态调整窗口大小：

```python
def adjust_window_size_for_dpi_change(self):
    """响应DPI变化，调整窗口大小"""
    try:
        # 获取当前窗口大小
        current_size = self.size()
        current_width = current_size.width()
        
        # 计算新的自适应高度
        new_height = self.calculate_adaptive_window_height()
        
        # 调整窗口大小，保持当前宽度
        self.resize(current_width, new_height)
        
        # 记录调试信息
        self.debug_logger.log_debug(
            f"DPI变化后调整窗口大小: 新高度={new_height}"
        )
        
    except Exception as e:
        self.debug_logger.log_error(f"DPI变化后调整窗口大小失败: {e}")
```

#### 注意事项

1. **异常处理**：确保在获取DPI失败时有合理的回退值
2. **日志记录**：记录DPI计算过程，便于调试和问题追踪
3. **性能考虑**：避免频繁计算和调整窗口大小
4. **用户自定义**：尊重用户手动调整的窗口大小，在DPI变化时保持宽度不变
5. **测试覆盖**：在不同DPI设置下测试窗口高度表现，确保一致性

### 9.5.2 事件编辑对话框DPI自适应

#### 概述

事件编辑对话框也应支持DPI自适应高度，确保在不同DPI设置下对话框高度保持合适的比例，避免在高DPI下对话框占满整个屏幕的问题。

#### 实现方法

##### 对话框初始化

在 `EventEditDialog` 初始化时，应使用自适应高度而非固定高度：

```python
# 计算自适应对话框高度
adaptive_height = calculate_adaptive_height(830, self.parent())
self.resize(605, adaptive_height)
```

##### 对话框高度计算方法

使用 `utils.py` 中的 `calculate_adaptive_height` 公共函数：

```python
def calculate_adaptive_height(base_height, parent_window=None):
    """计算自适应窗口/对话框高度，考虑DPI缩放和屏幕可用空间
    
    Args:
        base_height (int): 基础高度（100% DPI下的理想高度）
        parent_window (QWidget): 父窗口实例，用于获取DPI信息
    
    Returns:
        int: 计算得出的窗口/对话框高度
    """
    try:
        # 获取系统DPI缩放比例
        scale_percent = 100  # 默认值
        
        # 尝试从父窗口获取DPI信息
        if parent_window and hasattr(parent_window, 'settings_panel'):
            try:
                settings_panel = parent_window.settings_panel
                if settings_panel:
                    scale_text = settings_panel.scale_combo.currentText()
                    scale_percent = int(scale_text.strip('%'))
            except Exception:
                scale_percent = 100
        
        # 获取主屏幕信息
        screen = QApplication.primaryScreen()
        if not screen:
            return base_height  # 返回基础高度
        
        # 获取屏幕可用几何尺寸（排除任务栏）
        available_geometry = screen.availableGeometry()
        screen_height = available_geometry.height()
        
        # 根据DPI缩放调整基础高度
        dpi_factor = scale_percent / 100.0
        scaled_height = int(base_height * dpi_factor)
        
        # 设置最大高度为屏幕高度的85%，确保对话框不会占满整个屏幕
        max_height = int(screen_height * 0.85)
        
        # 设置最小高度，确保UI可用性
        min_height = int(base_height * 0.5)
        
        # 计算最终高度
        final_height = min(max(scaled_height, min_height), max_height)
        
        return final_height
        
    except Exception as e:
        # 如果计算失败，返回基础高度
        return base_height
```

#### 注意事项

1. **使用公共函数**：主窗口和事件编辑对话框都使用 `utils.py` 中的 `calculate_adaptive_height` 公共函数
2. **消除代码重复**：避免在多个地方实现相同的DPI计算逻辑
3. **提高可维护性**：只需维护一个函数，修改时同步更新
4. **增强代码复用**：其他窗口/对话框也可以使用这个公共函数
5. **与主窗口保持一致**：事件编辑对话框的DPI自适应逻辑应与主窗口保持一致
6. **从父窗口获取DPI**：对话框应从父窗口获取DPI信息，确保一致性
7. **固定宽度不变**：对话框宽度保持固定（605px），只调整高度
8. **异常处理**：确保在获取DPI失败时有合理的回退值
9. **测试覆盖**：在不同DPI设置下测试对话框高度表现，确保一致性

## 9.6 动态步长调整规范

### 9.6.1 概述

动态步长调整是一种用户界面优化技术，通过根据输入控件的上下文（如单位、范围等）自动调整步长，提供更合理的用户体验。这种技术特别适用于时间输入、数值输入等场景。

### 9.6.2 适用场景

- **时间输入控件**：根据时间单位动态调整步长
- **数值输入控件**：根据数值范围或单位动态调整步长
- **任何需要根据上下文调整精度的输入控件**

### 9.6.3 实现原则

1. **智能步长**：根据输入单位或范围自动调整步长
2. **即时响应**：单位变化时立即更新步长，无需用户操作
3. **合理默认值**：为最常用的单位设置合理的默认步长
4. **一致性**：相同类型的控件在整个应用中保持一致的行为

### 9.6.4 时间输入控件步长规范

| 时间单位 | 步长值 | 说明 |
|---------|--------|------|
| 毫秒(ms) | 100 | 适合精细调整，100ms是常用的时间间隔 |
| 秒(s) | 1 | 适合较大时间单位的基本调整 |
| 分钟(min) | 1 | 适合大时间单位的基本调整 |
| 小时(h) | 1 | 适合极大时间单位的基本调整 |

### 9.6.5 实现方法

#### 9.6.5.1 基础控件扩展

在输入控件类中实现 `update_step_based_on_unit` 方法：

```python
def update_step_based_on_unit(self, time_unit):
    """根据时间单位更新步长
    
    Args:
        time_unit (str): 时间单位，可以是 'ms', 's', 'min', 'h'
    """
    if time_unit == "ms":
        self.setSingleStep(100)  # 毫秒单位时，步长为100
    else:
        self.setSingleStep(1)    # 其他单位时，步长为1
```

#### 9.6.5.2 信号连接

在单位组合框的 `currentTextChanged` 信号中调用步长更新方法：

```python
# 连接信号，当时间单位改变时更新步长
self.time_unit_combo.currentTextChanged.connect(
    lambda unit: self.time_input.update_step_based_on_unit(unit)
)
```

#### 9.6.5.3 初始化设置

在控件初始化时根据默认单位设置初始步长：

```python
# 初始设置为ms单位，步长为100
self.time_input.update_step_based_on_unit("ms")
```

### 9.6.6 最佳实践

1. **用户体验优先**：步长设置应考虑用户最常用的调整场景
2. **保持一致性**：相同类型的输入控件在整个应用中应保持一致的步长逻辑
3. **文档化**：在控件的文档字符串中明确说明步长调整逻辑
4. **测试覆盖**：为动态步长功能编写测试用例，确保各种单位切换正常工作

### 9.6.7 示例应用

在BetterGI星轨项目中，动态步长调整已应用于以下场景：

1. **事件编辑对话框**：时间输入框根据时间单位自动调整步长
2. **批量编辑对话框**：偏移时间和统一相对时间输入框支持动态步长
3. **设置面板**：循环间隔时间输入框根据时间单位自动调整步长

这些应用显著提升了用户体验，减少了用户在调整时间时的操作步骤。

### 9.7 控件内容居中实现规范

#### 9.7.1 概述

控件内容居中是提升界面美观度和用户体验的重要手段。根据设计语言规范，不同类型的控件有不同的居中要求。本规范提供具体的实现指导，确保开发者在实际编码时能够正确应用这些规范。

#### 9.7.2 需要居中的控件

以下控件的内容必须居中显示：

1. **所有按钮**：主按钮、次要按钮、禁用按钮等
2. **普通文本输入框**：单行文本输入框
3. **下拉框**：包括标准下拉框和现代化下拉框
4. **数字输入框**：整数和浮点数输入框
5. **表格单元格**：表格中的内容
6. **表格标题**：表格的列标题

#### 9.7.3 不需要居中的控件

以下控件的内容不需要居中，应保持左对齐：

1. **文本编辑器**：多行文本编辑区域，如关于对话框内容
2. **文本浏览器**：HTML内容显示区域，如用户协议内容
3. **日志显示区域**：用于显示日志信息的区域

#### 9.7.4 实现方法

##### 9.7.4.1 CSS样式实现

对于支持CSS样式的控件，可以通过设置`text-align: center`属性实现内容居中：

```python
# 按钮居中
button.setStyleSheet("text-align: center;")

# 输入框居中
line_edit.setStyleSheet("text-align: center;")

# 下拉框居中
combo_box.setStyleSheet("text-align: center;")
```

##### 9.7.4.2 统一样式管理器实现

使用`UnifiedStyleHelper`统一管理样式，确保样式一致性：

```python
from styles import UnifiedStyleHelper

helper = UnifiedStyleHelper.get_instance()

# 使用统一样式管理器设置居中样式
button.setStyleSheet(helper.get_button_style() + "text-align: center;")
line_edit.setStyleSheet(helper.get_input_style() + "text-align: center;")
```

##### 9.7.4.3 控件特定方法实现

某些控件提供了特定的方法来实现内容居中：

```python
# 对于QSpinBox，可以使用setAlignment方法
spin_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

# 对于QDoubleSpinBox，同样可以使用setAlignment方法
double_spin_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
```

#### 9.7.5 对话框按钮居中实现

对话框底部的按钮区域需要整体居中显示，而不仅仅是按钮文本居中：

```python
from PyQt6.QtWidgets import QHBoxLayout

# 创建水平布局
button_layout = QHBoxLayout()

# 添加弹性空间实现居中
button_layout.addStretch()  # 左侧弹性空间
button_layout.addWidget(ok_button)
button_layout.addWidget(cancel_button)
button_layout.addStretch()  # 右侧弹性空间

# 将按钮布局添加到主布局
main_layout.addLayout(button_layout)
```

#### 9.7.6 实现检查清单

在实现控件内容居中时，请检查以下项目：

1. **按钮居中**
   - [ ] 所有按钮的文本是否居中显示
   - [ ] 对话框底部的按钮区域是否整体居中
   - [ ] 按钮宽度是否统一设置为100px（参考9.3节）

2. **输入框居中**
   - [ ] 普通文本输入框的内容是否居中
   - [ ] 数字输入框的内容是否居中
   - [ ] 输入框高度是否为30px（参考设计语言规范）

3. **下拉框居中**
   - [ ] 下拉框的显示文本是否居中
   - [ ] 下拉列表项的内容是否居中
   - [ ] 下拉框高度是否为30px（参考设计语言规范）

4. **表格居中**
   - [ ] 表格单元格内容是否居中
   - [ ] 表格标题是否居中
   - [ ] 表格行高是否为30px（参考设计语言规范）

5. **文本区域左对齐**
   - [ ] 文本编辑器内容是否左对齐
   - [ ] 文本浏览器内容是否左对齐
   - [ ] 用户协议和关于对话框内容是否左对齐

#### 9.7.7 常见问题解决

**问题1：按钮文本不居中**
解决：确保在按钮样式表中添加`text-align: center`属性。

**问题2：输入框内容不居中**
解决：对于QLineEdit，使用样式表设置`text-align: center`；对于QSpinBox，使用`setAlignment(Qt.AlignmentFlag.AlignCenter)`方法。

**问题3：下拉框显示文本不居中**
解决：在下拉框样式表中添加`text-align: center`属性。

**问题4：表格单元格内容不居中**
解决：在表格样式表中为单元格添加`text-align: center`属性。

**问题5：对话框按钮区域不居中**
解决：使用QHBoxLayout并添加弹性空间（addStretch()）实现按钮区域整体居中。

#### 9.7.8 示例代码

完整的对话框按钮居中实现示例：

```python
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from styles import UnifiedStyleHelper

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取样式管理器实例
        self.style_helper = UnifiedStyleHelper.get_instance()
        
        # 设置对话框布局
        self._setup_ui()
        
    def _setup_ui(self):
        """设置对话框UI"""
        main_layout = QVBoxLayout(self)
        
        # 添加内容区域...
        # content_widget = ...
        # main_layout.addWidget(content_widget)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 创建按钮
        ok_button = QPushButton("确定")
        ok_button.setFixedWidth(100)  # 统一按钮宽度
        ok_button.setStyleSheet(self.style_helper.get_primary_button_style() + "text-align: center;")
        
        cancel_button = QPushButton("取消")
        cancel_button.setFixedWidth(100)  # 统一按钮宽度
        cancel_button.setStyleSheet(self.style_helper.get_secondary_button_style() + "text-align: center;")
        
        # 添加弹性空间实现按钮居中
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        
        # 将按钮布局添加到主布局
        main_layout.addLayout(button_layout)
```

## 10. 事件处理开发规范

### 10.1 事件类型管理

- 事件类型应在 `utils.py` 的 `EVENT_TYPE_MAP` 中统一定义
- 新增事件类型应更新所有相关映射和转换函数
- 事件类型名称应清晰，便于理解和使用
- 鼠标移动大类包含两种事件类型：
  - 指针移动（类型2）：常规的鼠标移动事件
  - 平行移动（类型3）：特殊类型的鼠标移动事件，与指针移动规则相同
- 两种鼠标移动事件在时间分析中都应被排除，在统计中应统一显示为"鼠标移动"

### 10.2 事件时间管理

- 严格遵循 `事件处理逻辑.md` 中的时间管理规则
- 时间计算应使用整数，单位为毫秒
- 禁止出现负数时间，出现时应提示用户使用排序功能
- 批量操作时应考虑时间的一致性

### 10.3 事件数据持久化

- 事件数据应使用JSON格式存储
- 存储格式应符合 `事件处理逻辑.md` 中的定义
- 应支持版本兼容，便于未来格式升级

## 11. 调试和日志规范

### 11.1 日志管理

- 统一使用 `debug_tools.py` 中的 `SafeDebugLogger` 记录日志
- 日志应同时输出到文件和控制台，确保开发调试时能在终端看到实时日志
- 日志级别应合理使用：INFO、WARNING、ERROR、DEBUG
- 日志内容应包含足够的上下文信息
- 关键操作应记录日志，便于调试和问题追踪

### 11.2 日志文件存储规范

- **日志文件存储位置**：`C:\Users\{用户名}\AppData\Local\BetterGI StellTrack\logs`
- 日志文件应按日期自动创建，格式为：`app_YYYY-MM-DD.log`
- 日志文件应自动轮转，避免单个文件过大
- 日志文件应包含时间戳、日志级别、模块名和具体信息
- 应保留最近30天的日志文件，自动删除过期日志

### 11.3 AI辅助开发日志查看规范

- **自动日志查看**：使用AI开发时，应自动查看最新的日志文件，根据报错信息进行修复
- **日志查看时机**：
  - 应用程序启动失败时
  - 功能执行出现异常时
  - 用户反馈问题时
  - 代码修改后测试时
- **日志分析方法**：
  - 优先查看ERROR和WARNING级别的日志
  - 分析异常堆栈信息，定位问题根源
  - 结合代码上下文，理解错误原因
  - 根据日志信息制定修复方案
- **AI修复流程**：

  
  1. 自动读取最新日志文件
  2. 识别错误类型和位置
  3. 分析错误原因和上下文
  4. 提供修复建议或直接修复代码
  5. 验证修复效果，确保问题解决

### 11.4 虚拟环境调试规范

- **虚拟环境创建**：直接在项目目录创建.venv虚拟环境即可
- **创建命令**：`python -m venv .venv`
- **激活命令**：`.\.venv\Scripts\activate`（Windows）
- **依赖安装**：激活虚拟环境后，使用`pip install -r requirements.txt`安装项目依赖
- **依赖更新**：新增依赖后，使用`pip freeze > requirements.txt`更新依赖列表

### 11.5 AI IDE虚拟环境使用规范

- **AI IDE环境配置**：使用AI IDE（如TRAE、Qoder、Cursor等）进行开发时，应确保IDE已切换到项目虚拟环境
- **环境切换步骤**：
  1. 在AI IDE中打开项目终端
  2. 执行激活命令：`.\.venv\Scripts\activate`
  3. 验证环境：执行`python --version`确认Python版本
  4. 让AI直接在激活的虚拟环境中启动Python应用
- **AI启动命令**：AI应使用`python main.py`直接启动应用，而非使用IDE的运行按钮
- **环境验证**：AI在启动应用前应检查虚拟环境是否正确激活，确保使用正确的Python解释器和依赖包
- **依赖问题处理**：若AI启动时遇到依赖问题，应先在虚拟环境中执行`pip install -r requirements.txt`安装缺失依赖

### 11.6 调试工具使用

- 调试工具应通过 `on_open_debug_tool` 方法打开
- 调试工具应仅用于开发和调试，避免在生产环境使用
- 调试信息应清晰，便于定位问题

## 12. 版本管理规范

### 12.1 版本号管理

- 版本号格式：主版本.次版本.修订版本，如 `3.5.0`
- 主版本：重大功能更新或架构变更
- 次版本：新增功能或重要改进
- 修订版本：bug修复和小改进

### 12.2 版本信息存储

- 版本信息应在 `version.py` 中统一管理
- 版本信息应包含：应用名称、版本号、公司信息、版权信息等
- 版本信息应同步到 `version_info.txt` 文件

## 13. 文档规范

### 13.1 代码文档

- 核心功能应添加详细的文档字符串
- 文档应包含功能描述、参数说明、返回值说明
- 文档应使用中文，保持一致性

### 13.2 设计文档

- 新增功能应更新相应的设计文档
- 设计文档应包含功能需求、设计思路、实现方案
- 文档应清晰，便于其他开发者理解

### 13.3 使用文档

- 功能变更应更新使用文档
- 使用文档应包含功能说明、使用方法、注意事项
- 文档应面向用户，便于用户理解和使用

## 14. 开源许可证合规性规范

### 14.1 许可证选择原则

- 主项目许可证应基于核心依赖库的许可证选择
- 对于使用GPL系列许可证的核心依赖（如PyQt6），主项目应选择GPL或兼容许可证
- 优先选择与现有项目生态兼容的许可证
- 考虑项目的长期发展和商业化潜力

### 14.2 第三方库许可证检查规范

- 在添加任何第三方库之前，必须检查其许可证类型
- 使用`pip show <库名>`命令或查看库的官方文档获取许可证信息
- 记录所有第三方库的许可证信息，包括：
  - 库名称和版本
  - 许可证类型
  - 许可证URL（如有）

### 14.3 许可证声明规范

- 在项目根目录的`LICENSE.html`文件中完整声明所有第三方库的许可证信息
- 在应用程序的"关于"窗口中展示主要第三方库的许可证信息
- 确保许可证声明清晰易读，便于用户查阅
- 定期更新许可证声明，确保与实际依赖一致

### 14.4 许可证兼容性管理

- 确保所有第三方库的许可证与主项目许可证兼容
- 建立许可证兼容性矩阵，定期检查
- 避免使用与主项目许可证冲突的第三方库
- 对于双许可证或特殊许可证的库，确保正确使用符合要求的许可证

### 14.5 开发流程中的许可证检查

- 在代码审查过程中，包括许可证合规性检查
- 在版本发布前，进行全面的许可证合规性审计
- 建立依赖库许可证变更监控机制
- 对于许可证变更的依赖库，及时评估影响并采取相应措施

### 14.6 许可证合规性最佳实践

- 保持源代码可用，符合GPL等copyleft许可证的要求
- 明确声明所有代码的版权归属
- 尊重开源社区的贡献，遵循许可证条款
- 定期学习和更新开源许可证知识

## 15. 深色模式切换开发规范

### 15.1 深色模式切换机制

应用程序支持浅色和深色两种主题模式，用户可以在设置中切换主题。主题切换后，所有UI组件应立即更新为对应主题，无需重启应用。

**主题切换实现原则：**


1. 使用 `UnifiedStyleHelper` 单例管理主题颜色
2. 所有自定义控件类必须实现 `refresh_theme_styles()` 方法
3. 主题切换时触发全局样式刷新，确保所有组件同步更新
4. 主题设置通过 `QSettings` 持久化存储

### 15.2 refresh_theme_styles方法实现规范

所有自定义控件类必须实现 `refresh_theme_styles()` 方法，该方法负责在主题切换时更新控件样式。

#### 15.2.1 方法签名

```python
def refresh_theme_styles(self):
    """刷新控件的样式，应用当前主题"""
    helper = UnifiedStyleHelper.get_instance()
    # 更新控件样式
```

#### 15.2.2 实现规范

**基本实现：**

```python
def refresh_theme_styles(self):
    """刷新控件的样式，应用当前主题"""
    helper = UnifiedStyleHelper.get_instance()
    self.setStyleSheet(helper.get_xxx_style())
```

**复杂控件实现：**
对于包含多个子控件的复杂控件，需要递归刷新所有子控件：

```python
def refresh_theme_styles(self):
    """刷新控件的样式，应用当前主题"""
    helper = UnifiedStyleHelper.get_instance()
    
    # 更新自身样式
    self.setStyleSheet(helper.get_xxx_style())
    
    # 递归刷新所有子控件
    for child in self.findChildren(QWidget):
        if hasattr(child, 'refresh_theme_styles'):
            child.refresh_theme_styles()
```

**直接样式创建：**
对于某些特殊控件，可以直接创建样式字符串：

```python
def refresh_theme_styles(self):
    """刷新控件的样式，应用当前主题"""
    helper = UnifiedStyleHelper.get_instance()
    
    # 直接创建样式字符串
    style = f"""
    QLineEdit {{
        border: 1px solid {helper.COLORS['border']};
        border-radius: 8px;
        padding: 6px 8px;
        background-color: {helper.COLORS['card_bg']};
        color: {helper.COLORS['text']};
        font-size: 11px;
        selection-background-color: {helper.COLORS['primary']};
    }}
    """
    self.setStyleSheet(style)
```

### 15.3 样式刷新调用时机

样式刷新应在以下时机调用：


1. **主题切换时**：用户在设置中切换主题后立即调用
2. **窗口显示时**：窗口首次显示时调用，确保应用当前主题
3. **控件创建后**：动态创建控件后调用，确保样式正确

**主题切换实现示例：**

```python
def on_theme_changed(self, theme):
    """主题切换处理"""
    helper = UnifiedStyleHelper.get_instance()
    
    # 避免重复应用相同模式
    current_mode = getattr(helper, "theme_mode", "system")
    if theme == current_mode:
        return
    
    # 直接应用新主题（无动画，快速切换）
    helper.setup_global_style(theme_mode=theme, persist=True)
    
    # 刷新所有控件样式
    self.refresh_theme_styles()
```

### 15.4 各组件样式刷新实现

#### 15.4.1 主窗口样式刷新

主窗口需要刷新中央部件、分割器和所有子控件：

```python
def _refresh_theme_styles(self):
    """刷新主窗口样式"""
    helper = UnifiedStyleHelper.get_instance()
    
    # 中央部件样式
    central_widget = self.centralWidget()
    if central_widget:
        central_widget.setStyleSheet(f"background-color: {helper.COLORS['bg']};")
        
        # 刷新分割器中的所有子部件
        for i in range(central_widget.layout().count()):
            item = central_widget.layout().itemAt(i)
            if item.widget():
                widget = item.widget()
                # 分割器样式
                if hasattr(widget, "childrenCollapsible"):
                    widget.setStyleSheet(helper.get_splitter_style())
                    
                    # 刷新分割器中的所有子部件
                    for j in range(widget.count()):
                        splitter_widget = widget.widget(j)
                        if splitter_widget:
                            # 刷新滚动区域
                            if hasattr(splitter_widget, "widgetResizable"):
                                splitter_widget.setStyleSheet(
                                    f"QScrollArea {{ background-color: {helper.COLORS['bg']}; border: none; }}"
                                )
                                scroll_widget = splitter_widget.widget()
                                if scroll_widget:
                                    scroll_widget.setStyleSheet(helper.get_container_bg_style())
                            # 刷新普通部件
                            else:
                                splitter_widget.setStyleSheet(helper.get_container_bg_style())
    
    # 菜单栏样式刷新
    if hasattr(self, 'menuBar'):
        menu_bar = self.menuBar()
        if hasattr(menu_bar, 'refresh_theme_styles'):
            menu_bar.refresh_theme_styles()
```

#### 15.4.2 面板样式刷新

面板需要刷新所有子控件和布局：

```python
def refresh_theme_styles(self):
    """刷新面板样式"""
    helper = UnifiedStyleHelper.get_instance()
    
    # 更新面板背景色
    self.setStyleSheet(f"background-color: {helper.COLORS['bg']};")
    
    # 刷新所有子控件
    for child in self.findChildren(QWidget):
        if hasattr(child, 'refresh_theme_styles'):
            child.refresh_theme_styles()
```

#### 15.4.3 菜单栏样式刷新

菜单栏需要递归刷新所有菜单和子菜单：

```python
def refresh_theme_styles(self):
    """刷新菜单栏样式"""
    helper = UnifiedStyleHelper.get_instance()
    
    # 更新菜单栏样式
    self.setStyleSheet(helper.get_menu_bar_style())
    
    # 递归刷新所有菜单和子菜单
    for action in self.actions():
        menu = action.menu()
        if menu and hasattr(menu, 'refresh_theme_styles'):
            menu.refresh_theme_styles()
```

#### 15.4.4 HTML内容样式刷新

对于HTML内容（如用户协议），需要完全替换HTML中的样式块：

```python
def refresh_theme_styles(self):
    """刷新HTML内容样式"""
    helper = UnifiedStyleHelper.get_instance()
    
    # 读取HTML文件
    html_file = os.path.join(os.path.dirname(__file__), "file", "UserAgreement.html")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 完全替换HTML中的样式块
    import re
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
    
    # 创建完整的样式块
    custom_style = f"""
    <style>
        body {{
            font-family: 'Source Han Serif CN', '思源宋体', 'Microsoft YaHei', 'SimSun', serif;
            font-size: 12px;
            line-height: 1.8;
            margin: 0;
            padding: 0;
            background-color: {helper.COLORS['bg']};
            color: {helper.COLORS['text']};
        }}
        /* 其他样式规则... */
    </style>
    """
    
    # 插入新的样式块
    html_content = html_content.replace('</head>', custom_style + '</head>')
    
    # 更新文本浏览器内容
    self.text_browser.setHtml(html_content)
```

### 15.5 样式刷新注意事项


1. **避免重复刷新**：确保样式刷新方法不会重复调用，避免性能问题
2. **保持样式一致性**：所有控件应使用统一的样式管理器获取颜色和样式
3. **递归刷新**：对于包含子控件的控件，必须递归刷新所有子控件
4. **HTML样式替换**：对于HTML内容，必须完全替换样式块，避免样式冲突
5. **主题持久化**：主题切换后应立即保存到QSettings，确保下次启动时应用正确主题
6. **实例变量保存**：对于需要刷新的控件，应保存为实例变量，便于后续刷新

### 15.6 常见问题解决

**问题1：某些控件主题切换后未更新**
解决：确保该控件类实现了 `refresh_theme_styles()` 方法，并在主题切换时被调用。

**问题2：HTML内容主题切换后未更新**
解决：使用正则表达式完全替换HTML中的样式块，而不是追加新样式。

**问题3：菜单栏子菜单主题切换后未更新**
解决：在菜单栏的 `refresh_theme_styles()` 方法中递归刷新所有菜单和子菜单。

**问题4：分割器区域主题切换后未更新**
解决：在主窗口的样式刷新方法中，遍历分割器中的所有子部件并刷新样式。

**问题5：Windows 标题栏主题切换后未更新**
解决：使用 `TitleBarThemeMixin` 混入类，该类会自动处理 Windows 10+ 系统的标题栏深色/浅色模式切换。所有继承 `StyledDialog` 或 `StyledMainWindow` 的窗口都会自动支持标题栏主题切换，无需手动实现。

**实现原理：**

- `TitleBarThemeMixin` 在窗口初始化时自动注册回调到 `UnifiedStyleHelper`
- 主题切换时，`UnifiedStyleHelper` 通知所有注册的窗口更新标题栏
- 使用 Windows DWM API 的 `DwmSetWindowAttribute` 函数设置标题栏主题
- 非 Windows 系统会静默跳过，不影响程序运行

## 16. 右键菜单处理规范

### 16.1 基本原则

- 仅在必要时保留右键菜单，避免不必要的右键菜单干扰用户体验
- 保持右键菜单的一致性和简洁性
- 禁用所有非必要的PyQt6原生右键菜单

### 16.2 需要保留右键菜单的组件

- 主窗口的菜单栏
- 事件列表（ModernTableWidget）
- 其他明确需要右键菜单的交互组件

### 16.3 需要禁用右键菜单的组件

- 用户协议窗口中的文本浏览器（QTextBrowser）
- 关于窗口中的文本编辑框（QPlainTextEdit）
- 用户协议对话框中的文本浏览器（QTextBrowser）
- 所有只读文本框和浏览器组件
- 其他非交互性文本显示组件

### 16.4 实现方法

- 使用 `setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)` 禁用右键菜单
- 在组件创建时立即设置，确保始终禁用
- 对于动态创建的组件，在创建后立即设置

### 16.5 菜单项显示逻辑

- **条件显示菜单项**：某些菜单项应仅在特定条件下显示，提高用户体验
  - 编辑事件、批量编辑、删除事件等操作，**仅在有选中事件时才显示**
  - 复制、剪切等操作，**仅在有选中事件时才显示**
  - 粘贴操作，**仅在有复制的事件数据时才显示**
- **始终显示菜单项**：以下菜单项应始终显示，不受选择状态影响
  - 添加事件
  - 全选事件

### 16.6 示例代码

```python
# 禁用右键菜单示例
text_browser = QTextBrowser()
text_browser.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

plain_text_edit = QPlainTextEdit()
plain_text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

# 条件显示右键菜单项示例
def show_context_menu(self, position):
    context_menu = QMenu(self)
    
    # 获取选中的行
    selected_rows = self.get_selected_rows()
    
    # 添加始终显示的菜单项
    add_action = QAction("➕ 添加事件", self)
    context_menu.addAction(add_action)
    
    # 添加条件显示的菜单项
    if selected_rows:
        edit_action = QAction("✏️ 编辑事件", self)
        context_menu.addAction(edit_action)
        
        delete_action = QAction("🗑️ 删除事件", self)
        context_menu.addAction(delete_action)
    
    context_menu.exec(self.viewport().mapToGlobal(position))
```

## 17. 组件导入检查规范

### 17.1 组件默认行为检查原则

在导入和使用PyQt6或其他UI框架的组件时，必须检查并评估该组件的默认行为，确保所有默认行为都符合项目的需求。对于不符合需求的默认行为，必须明确禁用或修改。

#### 17.1.1 检查清单

导入任何新组件时，必须检查以下方面：


1. **交互行为检查**
   - 双击/单击行为（如表格的编辑模式）
   - 键盘快捷键响应
   - 拖拽行为
   - 右键菜单
2. **视觉表现检查**
   - 默认样式
   - 边框和背景
   - 选中状态
   - 禁用状态
3. **数据处理检查**
   - 默认数据验证
   - 自动完成行为
   - 数据格式化

#### 17.1.2 常见需要禁用的默认行为

以下是一些常见组件的默认行为，通常需要根据项目需求进行禁用：


1. **QTableWidget/QTableView**
   - 双击编辑：使用 `setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)` 禁用
   - 拖拽选择：根据需求使用 `setDragDropMode()` 控制
   - 默认排序：使用 `setSortingEnabled(False)` 禁用
2. **QTextEdit/QPlainTextEdit**
   - 右键菜单：使用 `setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)` 禁用
   - 拖拽放：使用 `setAcceptDrops(False)` 禁用
3. **QComboBox**
   - 可编辑状态：使用 `setEditable(False)` 禁用
   - 自动完成：根据需求控制

#### 17.1.3 实施规范


1. **导入时检查**

   ```python
   # 导入组件时立即检查并设置所需属性
   from PyQt6.QtWidgets import QTableWidget
   
   # 创建表格后立即禁用不需要的默认行为
   table = QTableWidget()
   table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 禁用双击编辑
   ```
2. **文档记录**
   - 在组件初始化代码旁添加注释，说明禁用特定默认行为的原因
   - 在组件类的文档字符串中记录所有修改的默认行为
3. **测试验证**
   - 为每个禁用的默认行为编写测试用例
   - 确保禁用后的行为符合项目需求

#### 17.1.4 示例：事件列表双击编辑禁用

```python
# 创建表格
self.events_table = ModernTableWidget(0, 8)

# 禁用表格的双击编辑功能
# 原因：避免用户意外双击开启编辑导致错误
self.events_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
```

#### 17.1.5 检查流程


1. **导入阶段**：在导入新组件时，查阅官方文档了解其默认行为
2. **实现阶段**：在创建组件实例后立即设置所需属性
3. **测试阶段**：验证所有默认行为已被正确修改
4. **审查阶段**：代码审查时特别关注组件默认行为的处理

通过遵循此规范，可以确保所有UI组件的行为都符合项目需求，避免因意外的默认行为导致用户操作错误。

## 18. 总结

本规范基于BetterGI 星轨项目的现有代码结构和设计文档，旨在指导后续开发，确保代码的一致性、可维护性和可扩展性。所有开发者应严格遵循本规范，确保项目的高质量开发和开源许可证合规性。

规范将根据项目的发展和需求变化进行定期更新，以适应新的技术和业务需求。

## 版本历史

|版本 |日期 |变更内容 |
|---|---|---|
|1.0 |2025-12-13 |初始版本，基于现有代码结构和设计文档制定 |
|1.1 |2025-12-17 |添加AI辅助开发规范，更新项目目录结构 |
|1.2 |2025-12-17 |增强基本开发规范，调整文档结构 |
|1.3 |2025-12-18 |添加开源许可证合规性规范，完善项目合规要求 |
|1.4 |2025-12-20 |新增对话框按钮宽度规范(9.3)，统一所有对话框底部按钮宽度为100px |
|1.5 |2025-12-25 |添加代码整洁规范，要求修改内容后清除重复冗余代码 |
|1.6 |2025-12-25 |新增响应式布局规范(9.4)，包含响应式设计原则、实现原则和布局示例 |
|1.7 |2025-12-26 |新增Emoji图标使用规范(5.5.1)，规范GroupBox标题中Emoji图标的选择和使用原则 |
|1.8 |2025-12-28 |新增深色模式切换开发规范(第15章)，包含refresh_theme_styles方法实现规范、样式刷新调用时机、各组件样式刷新实现和常见问题解决 |
|1.9 |2025-12-28 |新增Windows标题栏深色模式支持说明，在常见问题解决中添加问题5，说明TitleBarThemeMixin的使用方法和实现原理 |
|2.0 |2025-12-28 |优化主题切换性能，添加样式表缓存机制、批量标题栏更新，移除不自然的淡入淡出动画，实现快速直接切换 |
|2.1 |2025-12-28 |修复弹窗标题栏主题切换问题，确保所有QDialog子类都继承TitleBarThemeMixin以支持Windows标题栏深色/浅色模式自动切换；将SimpleCoordinateCapture由QDialog改为继承StyledDialog，将AnimatedDialog添加TitleBarThemeMixin混入类 |
|2.2 |2025-12-28 |新增右键菜单处理规范(第16章)，明确规定哪些组件需要禁用右键菜单，哪些需要保留，以及实现方法 |
|2.3 |2025-12-29 |更新右键菜单处理规范，新增菜单项显示逻辑(16.5)，明确规定条件显示菜单项的规则，特别是编辑、批量编辑、删除事件等操作仅在有选中事件时才显示 |
|2.4 |2025-12-29 |新增兼容性要求(1.3)，明确仅兼容Win 10 64bit及以上系统，Python 3.11及以上版本 |
|2.5 |2025-12-29 |新增DPI处理规范(9.5)，包含动态DPI获取、API选择、实现原则和示例，支持动态获取DPI变化，无需重启应用 |
|2.6 |2026-01-01 |新增组件导入检查规范(18.1)，要求在导入新组件时检查并屏蔽不需要的默认行为，避免意外操作 |
|2.7 |2026-01-10 |重构样式模块，将 styles.py 拆分为 styles/ 目录结构，包含 fonts.py、themes.py、widgets.py、dialogs.py、__init__.py，保持向后兼容性，提高代码可维护性 |
|2.8 |2026-01-10 |新增日志文件存储规范(11.2)和AI辅助开发日志查看规范(11.3)，明确日志文件存储位置为C:\Users\{用户名}\AppData\Local\BetterGI StellTrack\logs，并规定AI开发时应自动查看最新日志文件并根据报错进行修复 |
|2.9 |2026-01-10 |更新项目目录结构(2.3)，记录第一阶段的代码拆分状态和第二阶段的拆分决策；添加代码拆分状态说明(2.4)，详细记录拆分效果和决策原因 |
|2.10 |2026-01-10 |新增虚拟环境调试规范(11.4)，规定所有开发和调试工作应优先在虚拟环境中进行，包含虚拟环境创建、依赖管理、调试环境配置和虚拟环境共享等规范 |
|2.11 |2026-01-11 |新增批量编辑对话框模块，将BatchEditDialog类从main_window.py分离到batch_dialog.py，提高代码模块化程度 |
|2.12 |2026-01-11 |更新模块划分规范(2.2)和项目目录结构(2.3)，添加debug_dialog.py文件，反映CustomInputDialog类从main_window.py拆分到debug_dialog.py的实际代码结构 |
|2.13 |2026-01-11 |更新模块划分规范(2.2)和项目目录结构(2.3)，添加widgets.py文件，反映ModernTableWidget和HeaderWidget类从main_window.py拆分到widgets.py的实际代码结构，进一步提高代码模块化程度 |
|2.14 |2026-01-11 |新增菜单管理模块，将菜单栏创建和管理功能从main_window.py分离到menu_manager.py，包括时间逻辑设置和主题管理功能，实现菜单顺序调整，将工具菜单放在主题菜单之前 |
|2.15 |2026-01-11 |新增AI IDE虚拟环境使用规范(11.5)，规定使用AI IDE开发时应切换到项目虚拟环境，让AI直接在虚拟环境中启动Python应用 |
|2.16 |2026-01-12 |新增状态管理模块，将StateManager类从main_window.py分离到state_manager.py，提高代码模块化程度 |
|2.17 |2026-01-12 |重构代码组织结构，将拆分出的模块按功能分类组织到子目录中：ui/、dialogs/、managers/，参考styles/目录结构，提高代码组织性和可维护性 |
|2.18 |2026-01-13 |新增动态步长调整规范(9.6)，为时间输入控件提供智能步长调整功能，根据时间单位自动调整步长，提高用户体验 |
|2.19 |2026-01-18 |新增导入规范化经验(2.4.1)，包含导入顺序和分组、导入清理、导入格式化等经验；新增文档字符串规范化经验(8.2.1)，包含文档字符串精简、完整性、模块文档字符串等经验；新增代码格式统一经验(3.1.1)，包含空行管理、注释风格统一等经验；新增异常处理规范化经验(8.3.1)，包含指定具体异常类型、异常信息详细化、异常处理原则等经验；新增常量管理经验(3.1.2)，包含常量提取和命名等经验；新增命名规范经验(3.1.3)，包含类命名规范、函数和变量命名规范等经验；新增代码清理经验(3.1.4)，包含清理未使用代码、清理冗余代码等经验；新增代码结构组织经验(3.1.5)，包含代码结构分隔、代码组织原则等经验；新增控件内容居中实现规范(9.7)，包含需要居中和不需要居中的控件列表、实现方法、检查清单、常见问题解决和示例代码 |
|2.20 |2026-01-19 |新增"优化"提交类型(3.4.1)，定义为在不改变功能的前提下，提升代码或系统的性能、效率或用户体验的改进 |
|2.21 |2026-01-20 |新增性能优化经验(3.6.1和3.6.2)，包含缓存优化经验和PyQt UI性能优化经验，提供缓存应用原则、缓存清理策略、减少UI重绘、数据结构优化、字典查找优化等具体实现示例 |
|2.22 |2026-01-23 |新增DPI自适应窗口高度规范(9.5.1)，包含实现原则、主窗口初始化方法、窗口高度计算方法、DPI变化响应机制和注意事项，确保在不同DPI设置下窗口高度保持合适的比例 |
|2.23 |2026-01-23 |新增事件编辑对话框DPI自适应规范(9.5.2)，包含实现方法、对话框初始化代码、对话框高度计算方法和注意事项，确保事件编辑对话框在不同DPI设置下高度保持合适的比例 |
|2.24 |2026-01-23 |重构DPI自适应窗口高度计算，提取为公共函数calculate_adaptive_height到utils.py；更新main_window.py和event_dialogs.py使用公共函数；更新开发规范说明使用公共函数的优势 |
|2.25 |2026-01-29 |修复日志管理器终端输出问题，修改SafeDebugLogger的SafeOutputCapture.write()方法，使日志同时输出到文件和控制台，确保开发调试时能在终端看到实时日志；更新日志管理规范(11.1)，明确日志应同时输出到文件和控制台 |


