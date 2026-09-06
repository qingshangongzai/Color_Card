# 取色卡 (Color Card) — AI 协作入口

图片颜色分析桌面应用：Python 3.11+ / PySide6 / PySide6-Fluent-Widgets，支持 Nuitka / PyInstaller 打包。

## 规则真源（动手前先读）

- **编码规则唯一真源**：`文档/开发规范.md` —— 开始任何编码 / 审查 / 提交任务前，先读它；任何 skill 的规则与它冲突时，以它为准。
- **专项规范**：领域细节按需阅读，见下方文档路由表。
- 本文下方的「核心原则」为常驻速查规则，与《开发规范》冲突时以《开发规范》为准。

## 文档路由（按任务类型选读）

| 任务类型 | 阅读 |
|---|---|
| 画布/卡片/直方图组件开发 | 文档/专项规范/基类设计规范.md |
| 颜色转换、明度计算、Zone 分区 | 文档/专项规范/颜色处理规范.md |
| 图片加载、坐标映射、性能、内存 | 文档/专项规范/图片处理规范.md |
| color_data/ 配色数据 | 文档/专项规范/配色数据格式规范.md |
| 配色预览、SVG 模板、场景管理 | 文档/专项规范/场景配置化规范.md |
| 界面布局、控件尺寸 | 文档/专项规范/界面布局规范.md |
| 配置项新增/修改 | 文档/专项规范/配置管理规范.md |
| 界面文本国际化、语言包 | 文档/专项规范/多语言国际化规范.md |
| 日志记录 | 文档/专项规范/日志系统规范.md |
| 版本发布、更新日志、官网同步 | 文档/专项规范/发布与官网维护规范.md |
| 新增第三方库、LICENSE 维护 | 文档/专项规范/开源许可证管理规范.md |

## Skill 触发对照（用户说关键词时自动用）

| 用户意图 | Skill | 触发词 |
|---|---|---|
| 审查代码 | `code-review` | 检查代码、代码审查、review、核对修改 |
| 生成提交信息 | `commit-message-generator` | 提交信息、commit、合并分支、merge |
| 创建分支 | `create-branch` | 创建分支、开个分支、分支名 |
| 写/更新方案、思路文档 | `plan-doc` | 写方案、实施计划、落地记录、写思路 |
| 只分析不修改 | `question-mode` | 提问、提问模式 |

## 约定

- skill 以根目录 `skills/`（已提交仓库）为唯一维护源；各工具目录（`.trae/skills/` 等，均已在 `.gitignore` 中）下的副本从它同步，不单独维护。同步命令：`Copy-Item skills\* .trae\skills\ -Recurse -Force`。
- 版本号唯一来源：`version.py`（`VersionManager`），禁止在其他文件手改版本号。CI 打包版本读 `version.txt`，发版时需与 `version.py` 同步更新。
- 依赖版本唯一来源：`requirements.txt`。
- 跨会话方案/思路文档放 `文档/过程性文档/`（已 gitignore），写作与接力规则见 `plan-doc` skill。

---

## 核心原则（常驻速查）

### 技术栈

- Python 3.11+
- GUI: PySide6 + PySide6-Fluent-Widgets
- 注释语言: 中文

### 目录结构

```
color_card/
├── main.py              # 程序入口
├── core/                # 核心功能（业务层）
├── ui/                  # UI模块（展示层）
├── dialogs/             # 对话框
├── utils/               # 工具函数
├── locales/             # 语言包
└── color_data/          # 颜色数据
```

**核心理念：UI层和业务层分离，业务逻辑全部下沉到 core 模块**

### 命名规范

| 类型 | 规范 | 示例 |
|:---:|:---|:---|
| 类名 | 驼峰 | `ColorPicker` |
| 函数/变量 | 小写+下划线 | `extract_color()` |
| 常量 | 大写+下划线 | `MAX_SIZE = 1000` |
| 私有属性 | 单下划线前缀 | `_dragging` |

**禁止**：`l`（易与1混淆）、`O`（易与0混淆）

### 导入原则

```python
# 标准库 → 第三方 → 项目模块
import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentWindow

from core import get_color_info
```

- **只导入实际使用的模块**
- 禁止预导入"可能用到"的模块
- 按分组添加注释

### 关键约束

**颜色管理**

```python
# ❌ 禁止硬编码
painter.setPen(QColor(255, 255, 255))

# ✓ 必须使用主题颜色
from utils.theme_colors import get_text_color
painter.setPen(get_text_color())
```

**信号防循环**

```python
def set_image_data(self, pixmap, image, emit_sync=True):
    self._pixmap = pixmap
    if emit_sync:
        self.image_loaded.emit()
```

**异常处理**

```python
# ❌ 禁止裸 except
# ✓ 必须指定具体类型
except (OSError, ValueError) as e:
    logger.error(f"错误: {e}")
```

**QSplitter**

```python
splitter.setHandleWidth(0)  # 必须隐藏分隔条
```

**代码清理**

- 删除未使用的变量、导入
- 禁止复制粘贴后仅做微调
- 重复代码提取公共方法或基类

**设计原则**

- **延迟抽象**：只有一种实现时不用工厂/策略模式
- **适度防御**：边界检查要有实际意义
- **单一职责**：一个类只负责一类功能
- **避免不必要的防御性策略**：对于项目必需依赖（如 requirements.txt 中定义的包），无需编写防御性导入和回退代码

**多线程使用**

耗时操作（复杂计算等场景）应使用多线程，避免阻塞UI主线程。

### 文档字符串

使用中文，避免过度详细：

```python
class ImageCanvas(QWidget):
    """图片显示画布，支持取色点拖动"""
    pass

def get_color_info(self, r, g, b):
    """获取颜色信息
    
    Args:
        r, g, b: RGB通道值 (0-255)
    Returns:
        dict: 颜色信息
    """
    pass
```

### 常用导入

```python
# 主题颜色
from utils.theme_colors import get_text_color, get_canvas_background_color

# 配置管理
from core import get_config_manager

# 国际化
from utils import tr, set_language

# Fluent
from qfluentwidgets import FluentWindow, qconfig, isDarkTheme
```

### 主题切换

```python
qconfig.themeChangedFinished.connect(self._update_styles)

def _update_styles(self):
    if isDarkTheme():
        # 深色主题样式
        pass
```

### 多语言

```python
text = tr('navigation.color_extract')

class MyInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        get_locale_manager().language_changed.connect(self.update_texts)
```

### 日志

日志存储在 `~/.color_card/logs/`（用户主目录，不是项目目录）

```python
# 日志目录自动创建，已存在不会报错
self._log_dir.mkdir(parents=True, exist_ok=True)

# 沙箱环境无法访问日志是环境限制，不是代码问题。不要修改日志系统。
# 业务代码禁止 print()，必须用 get_logger()（详见专项规范/日志系统规范）
```
