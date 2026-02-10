# 取色卡 (Color Card)

## 项目概述

**取色卡（Color Card）是一款专为摄影师和设计师打造的一站式配色工具和图片色彩分析工具**，集成了图片颜色提取、明度分析、智能配色生成、配色管理、配色预览等全方位功能。本工具基于 PySide6 和 PySide6-Fluent-Widgets 开发，提供了现代化的流畅界面，帮助用户快速获取图片的色彩数据并生成专业的配色。

**开发理念**：在摄影后期处理和设计创作中，色彩分析是一个重要环节。取色卡旨在为摄影师和设计师提供一个简单、直观、专业的一站式色彩工具，从图片中提取颜色、分析明度分布、生成和谐配色、管理配色、预览配色效果，满足从色彩分析到配色应用的全流程需求。不同于通用的取色工具，取色卡专注于摄影和设计场景的实际需求，提供专业级的色彩空间转换、明度分析和配色生成功能。

**关于本项目**：取色卡是借助 AI 编程工具（如 Trae 等）辅助开发的**非商业开源项目**。项目功能设计参考了 [Adobe Color](https://color.adobe.com/)、[Canva Palette Generator](https://www.canva.com/colors/color-palette-generator/) 等优秀的在线配色工具，旨在为中文用户提供一个**无需联网、无需注册、隐私安全**的本地替代品。所有代码均为独立实现，与 Adobe、Canva 等公司无任何关联。

**开源协议**：本项目采用 **GNU General Public License v3.0 (GPL 3.0)** 开源协议，所有代码和文档均遵循该协议的条款和条件。

**开源地址**：
- **主仓库（Gitee）**：https://gitee.com/qingshangongzai/color_card
- **镜像仓库（GitHub）**：https://github.com/qingshangongzai/Color_Card

### 核心功能特色

**一站式色彩解决方案**：从图片分析到配色应用，提供完整的色彩工作流

- **可视化色彩提取**：通过直观的可拖动取色点，实时提取图片任意位置的颜色，支持5个取色点同时工作
- **智能配色方案**：提供5种专业配色方案（同色系、邻近色、互补色、分离补色、双补色），支持可交互色环选择和明度调整
- **配色方案收藏**：支持收藏和管理配色方案，可自定义名称，方便后续快速查看和使用
- **内置色彩库**：集成 Open Color、Tailwind CSS、Material Design、Nord、Dracula、Solarized、Gruvbox、Catppuccin、ColorBrewer、Radix Colors、Rose Pine 和 Nice Color Palettes 十二大开源配色方案，提供 13 + 22 + 19 + 16 + 11 + 2 + 2 + 4 + 35 + 31 + 3 种颜色系列 + 500 组精选配色，总计 658 组色卡，支持一键复制颜色值
- **配色预览**：支持在多种场景下预览收藏的配色效果，包括插画风格、排版设计、UI组件、网页布局等，支持拖拽调整颜色顺序
- **场景配置化**：支持通过 JSON 配置文件定义和扩展预览场景，支持场景的导入导出和分享
- **批量导入导出**：支持将收藏的配色导出为JSON文件，或从文件批量导入，便于备份和分享
- **多色彩空间支持**：同时显示 HSB、LAB、HSL、CMYK、RGB 等多种色彩模式，满足不同场景的需求
- **专业明度分析**：将图片按明度分为9个区域，提供直方图可视化，帮助理解图片的明度分布
- **现代化界面**：基于 Fluent Design 设计语言，支持自动深色/浅色主题切换，提供流畅的用户体验
  - 标题栏集成主题切换按钮，一键切换深色/浅色模式
  - 所有界面元素自动适配主题颜色，确保在任何主题下都清晰可见
  - 使用主题颜色管理系统，统一维护所有颜色值
- **高精度显示**：使用原始图片实时缩放，保证显示清晰度，取色点位置使用相对坐标系统，图片缩放时保持不变
- **四面板同步**：色彩提取、明度分析、配色生成和收藏面板数据实时同步，切换面板时自动更新
- **统一配置管理**：16进制颜色值显示和色彩模式设置全局统一，所有界面实时响应设置变更

### 适用场景

**摄影师工作流**
- **摄影后期**：分析照片的色调分布，辅助调色决策，理解图片的色彩构成
- **色彩参考**：从优秀作品中提取配色，获取创作灵感
- **明度分析**：评估照片的明度分布，优化曝光和对比度

**设计师工作流**
- **设计配色**：从参考图中提取配色，快速获取设计灵感
- **配色预览**：在插画、排版、UI等多种场景下预览配色效果
- **色彩管理**：收藏和管理配色方案，建立个人色彩库
- **色彩研究**：学习理解不同图片的色彩构成，提升色彩感知能力

**综合应用**
- **跨场景协作**：摄影师和设计师共享配色方案，统一视觉风格
- **色彩教学**：作为色彩理论和实践的教学工具
- **快速原型**：快速生成配色并预览效果，加速设计迭代

---

## 安装指南

### 面向普通用户（使用安装包）

1. 前往项目的 **Gitee 发布页** 下载最新的安装包（`.exe` 文件）
2. 运行下载的安装程序，跟随向导完成安装
3. 从桌面快捷方式或开始菜单启动 "取色卡"

### 面向开发者（从源码运行）

#### 环境要求

- **操作系统**：Windows 10/11 64位
- **Python 版本**：Python 3.11 及以上 64位版本（推荐使用 3.14）
- **内存**：推荐 4GB 以上
- **硬盘空间**：至少 100MB 可用空间

#### 依赖安装与运行

1. **克隆仓库**：

   ```bash
   # 从 Gitee 克隆（国内推荐）
   git clone https://gitee.com/qingshangongzai/color_card.git
   
   # 或从 GitHub 克隆
   git clone https://github.com/qingshangongzai/Color_Card.git
   
   cd color_card
   ```

2. **创建虚拟环境（推荐）**：

   ```bash
   python -m venv .venv
   # 激活虚拟环境
   .\.venv\Scripts\activate  # Windows
   ```

3. **安装项目依赖**：

   ```bash
   pip install -r requirements.txt
   ```

4. **启动应用程序**：

   ```bash
   python main.py
   ```

---

## 使用说明

### 基本操作

1. **启动应用**：运行 `main.py` 或 exe
2. **导入图片**：点击「打开图片」按钮，支持拖拽导入
3. **色彩提取**：在「色彩提取」标签页，拖动图片上的5个圆形取色点到任意位置，下方色卡会实时显示对应颜色的 HSB、LAB、HSL、CMYK、RGB 值
4. **明度分析**：切换到「明度提取」标签页，查看图片的明度分布直方图，双击图片区域自动提取对应明度的像素

### 功能详解

#### 色彩提取

- **5个可拖动取色点**：圆形设计，带白色边框，可自由拖动到图片任意位置，取色点编号显示
- **实时颜色提取**：拖动时实时更新颜色值，响应迅速
- **多色彩空间显示**：每个色卡显示对应的 HSB、LAB、HSL、CMYK、RGB 值，支持一键复制
- **高分辨率显示**：使用原始图片实时缩放，保证显示清晰度，避免多次缩放导致的画质损失
- **相对坐标系统**：取色点位置使用相对坐标（0.0-1.0）存储，图片缩放时保持不变

#### 明度提取

- **5个明度区域（Adobe标准）**：将图片按明度分为5个标准区域
  - 黑色（Blacks）：0%–10%（黑点区域）
  - 阴影（Shadows）：10%–30%（阴影区域）
  - 中间调（Midtones）：30%–70%（中间亮度区域，由 Exposure/Contrast 负责）
  - 高光（Highlights）：70%–90%（高光区域）
  - 白色（Whites）：90%–100%（白点区域）
- **明度直方图**：实时显示图片明度分布直方图，支持区域选择和高亮
- **区域高亮显示**：选中区域在直方图上高亮显示，方便查看特定明度范围的像素分布
- **双击提取**：双击图片任意区域，自动提取该明度对应的像素，并在色卡中显示

#### 配色生成

- **配色生成**
  - **5种专业配色生成**：同色系、邻近色、互补色、分离补色、双补色
  - **可交互色环**：支持鼠标拖动选择基准色，实时显示配色生成在色环上的分布
  - **明度调整滑块**：调整配色生成的明度，色环和色块实时响应
  - **动态卡片数量**：根据配色生成类型自动调整色块数量（3-5个）
  - **统一显示设置**：使用与色彩提取相同的显示设置（16进制值、色彩模式）

- **收藏管理**
  - **一键收藏**：在色彩提取和配色生成面板均可快速收藏当前颜色方案
  - **自定义名称**：为收藏的配色设置自定义名称，便于识别
  - **列表展示**：以卡片形式展示所有收藏的配色，支持滚动浏览
  - **删除管理**：支持单个删除或一键清空所有收藏
  - **批量导入导出**：支持JSON格式的导入导出，便于备份和分享配色

#### 配色预览

- **多场景预览**：支持在多种场景下预览收藏的配色效果
  - **插画风格**：使用 QPainter 绘制植物风格矢量插画，展示配色在插画中的应用
  - **排版设计**：展示配色在文字排版中的层次效果
  - **手机UI设计**：模拟手机应用界面，展示配色在移动端UI中的应用
  - **网页布局**：模拟网页设计，展示配色在Web设计中的应用
  - **Mixed 模式**：左侧 2x2 插画小图 + 右侧排版大图，综合展示配色效果
  - **场景切换**：支持自定义、混合、UI设计、网页、品牌、插画、排版、海报、图案等多种场景
  - **场景配置化**：通过 JSON 配置文件定义场景，支持导入导出和分享自定义场景

- **颜色管理**
  - **可拖拽排序**：顶部显示当前配色的圆点，支持拖拽调整颜色顺序
  - **实时预览**：颜色顺序调整后，预览区域实时更新
  - **场景选择器**：下拉菜单选择不同的预览场景

- **联动功能**
  - **从配色管理跳转**：在配色管理页面点击"预览"按钮，自动跳转到配色预览页面并加载对应配色
  - **实时刷新**：收藏列表更新后，配色预览页面自动同步

---

## 技术架构与设计理念

### 核心技术栈

| 技术/框架 | 用途 | 版本 |
|:---|:---|:---:|
| Python | 主要开发语言 | 3.11+ |
| PySide6 | GUI 应用程序框架 | 6.0+ |
| PySide6-Fluent-Widgets | 现代化 UI 组件库 | 1.0+ |
| Pillow | 图像处理 | 9.0+ |

### 架构设计原则

1. **模块化设计**：将功能划分为独立的模块，每个模块职责明确
2. **关注点分离**：UI 组件、业务逻辑和数据处理层分离，便于维护和测试
3. **基类抽象**：提取公共基类（BaseCanvas、BaseCard、BaseHistogram），消除代码重复，提高代码复用性
4. **扁平化结构**：采用2级目录结构，避免过度嵌套，提高代码可维护性
5. **相对坐标系统**：取色点位置使用相对坐标存储，图片缩放时自动调整，保持位置不变

### 项目结构

```
color_card/
├── main.py                 # 应用程序主入口
├── version.py              # 版本管理器模块
├── requirements.txt        # 项目依赖列表
├── README.md               # 项目说明文档
├── LICENSE                 # 开源许可证文件
├── 开发规范.md              # 开发规范文档
├── core/                   # 核心功能模块目录
│   ├── __init__.py
│   ├── color.py           # 颜色处理模块（颜色转换、明度计算、配色生成算法、直方图计算）
│   ├── colorblind.py      # 色盲模拟模块（色盲类型定义、LMS色彩空间转换、色盲模拟算法）
│   ├── color_data.py      # 颜色数据管理模块（延迟加载各颜色库数据）
│   ├── config.py          # 配置管理模块（收藏数据管理、场景配置管理、导入导出功能）
│   └── contrast.py        # 对比度检查模块（WCAG对比度计算、等级判断）
├── preview_scenes/        # 场景配置目录
│   ├── scenes.json        # 内置场景配置文件
│   └── user_scenes/       # 用户自定义场景目录
├── ui/                     # UI模块目录
│   ├── __init__.py        # 统一导出接口
│   ├── main_window.py     # 主窗口类
│   ├── canvases.py        # 画布模块（BaseCanvas、ImageCanvas、LuminanceCanvas）
│   ├── cards.py           # 卡片组件模块（ColorCard、LuminanceCard及基类）
│   ├── histograms.py      # 直方图组件模块（LuminanceHistogramWidget、RGBHistogramWidget）
│   ├── color_picker.py    # 颜色选择器模块
│   ├── color_wheel.py     # 颜色轮模块（HSBColorWheel、InteractiveColorWheel）
│   ├── scheme_widgets.py  # 配色方案组件模块（SchemeColorInfoCard、SchemeColorPanel）
│   ├── color_management_widgets.py # 色彩管理组件模块（ColorManagementColorCard、ColorManagementSchemeCard、ColorManagementSchemeList）
│   ├── preset_color_widgets.py # 内置色彩组件模块（PresetColorCard、PresetColorSchemeCard、PresetColorList）
│   ├── preview_widgets.py # 配色预览组件模块（DraggableColorDot、ColorDotBar、BasePreviewScene、PreviewSceneFactory、IllustrationPreview、TypographyPreview、MobileUIPreview、WebPreview、SVGPreviewWidget、PreviewSceneSelector、PreviewToolbar、MixedPreviewPanel）
│   ├── zoom_viewer.py     # 缩放查看器模块
│   ├── interfaces.py      # 界面面板模块（ColorExtractInterface、LuminanceExtractInterface、SettingsInterface、ColorSchemeInterface、ColorManagementInterface、PresetColorInterface、ColorPreviewInterface）
│   └── theme_colors.py    # 主题颜色管理模块（统一颜色管理、主题感知颜色获取）
├── dialogs/               # 对话框模块目录
│   ├── __init__.py
│   ├── about_dialog.py    # 关于对话框
│   ├── colorblind_dialog.py # 色盲模拟预览对话框
│   ├── contrast_dialog.py # 对比度检查对话框
│   └── update_dialog.py   # 更新检查对话框
└── utils/                 # 工具函数模块目录
    ├── __init__.py
    ├── icon.py            # 图标工具模块
    └── platform.py        # 平台相关工具模块
```

### 核心模块详解

#### 1. 颜色处理模块 (core/color.py)

负责所有与颜色相关的计算和转换：

- **颜色空间转换**：RGB ↔ HSB、RGB ↔ LAB、RGB ↔ HSL、RGB ↔ CMYK，支持多种色彩空间
- **配色生成算法**：实现5种专业配色生成（同色系、邻近色、互补色、分离补色、双补色），基于色彩理论生成和谐配色
- **明度计算**：使用 Rec. 709 标准计算亮度值，包含 sRGB Gamma 校正，与 Lightroom、Photoshop 等专业软件使用相同标准
- **直方图计算**：计算图片的明度分布和 RGB 通道分布，支持采样优化

#### 2. 画布模块 (ui/canvases.py)

提供图片显示和交互功能：

- **BaseCanvas**：画布基类，提供图片加载、显示、坐标转换等通用功能
  - 图片加载与显示（保持比例居中）
  - 拖拽打开图片
  - 右键菜单框架
  - 坐标转换（画布坐标 ↔ 图片坐标 ↔ 相对坐标）
- **ImageCanvas**：图片画布，支持5个可拖动取色点
  - 取色点管理（添加、删除、拖动）
  - 相对坐标系统（取色点位置在图片缩放时保持不变）
  - 实时颜色提取和信号发射
- **LuminanceCanvas**：明度画布，支持9级明度分区显示
  - 明度分区覆盖层绘制
  - 区域选择和高亮显示
  - 双击提取像素功能

#### 3. 卡片模块 (ui/cards.py、ui/generation_widgets.py 和 ui/palette_management_widgets.py)

提供颜色信息展示功能：

- **BaseCard / BaseCardPanel**：卡片基类，提供统一的卡片接口
  - setup_ui：设置界面
  - clear：清空卡片
  - set_card_count：动态调整卡片数量
- **ColorCard / ColorCardPanel**：色彩卡片，显示多种色彩空间值
  - 支持 HSB、LAB、HSL、CMYK、RGB 显示
  - 一键复制颜色值
  - 支持16进制颜色值显示开关
- **LuminanceCard / LuminanceCardPanel**：明度卡片，显示明度区域信息
  - 显示区域名称和明度范围
  - 显示像素数量
- **GenerationColorInfoCard / GenerationColorPanel**（ui/generation_widgets.py）：配色生成卡片
  - 与ColorCard保持一致的显示样式
  - 支持动态卡片数量（根据配色生成类型自动调整）
  - 复用ColorModeContainer组件，统一显示逻辑
- **PaletteManagementColorCard / PaletteManagementCard / PaletteManagementList**（ui/palette_management_widgets.py）：配色管理组件
  - PaletteManagementColorCard：单个颜色显示卡片，与ColorCard样式一致
  - PaletteManagementCard：配色卡片，包含名称、颜色列表、操作按钮
  - PaletteManagementList：配色列表容器，管理多个PaletteManagementCard
  - 动态色卡数量：根据保存的颜色数量动态创建色卡
- **DraggableColorDot / ColorDotBar / IllustrationPreview / TypographyPreview / PreviewToolbar / MixedPreviewPanel**（ui/preview_widgets.py）：配色预览组件
  - DraggableColorDot：可拖拽的颜色圆点组件，支持拖拽排序
  - ColorDotBar：颜色圆点工具栏，管理多个颜色圆点并处理拖拽排序逻辑
  - IllustrationPreview：插画风格预览，使用 QPainter 绘制植物风格矢量插画
  - TypographyPreview：排版风格预览，展示配色在文字排版中的层次效果
  - PreviewToolbar：预览工具栏，包含颜色圆点栏和场景选择器
  - MixedPreviewPanel：Mixed 场景预览面板，左侧 2x2 插画小图 + 右侧排版大图

#### 4. 主题颜色管理模块 (ui/theme_colors.py)

统一管理系统中所有颜色值，支持深色/浅色主题自动切换：

- **颜色分类管理**：背景色、文本色、边框色、控件特定颜色、Zone分区颜色等
- **主题感知**：所有颜色函数根据当前主题（深色/浅色）自动返回对应颜色值
- **硬编码消除**：集中管理颜色值，避免散落在各组件中的硬编码颜色
- **使用示例**：
  ```python
  from ui.theme_colors import get_text_color, get_canvas_background_color
  
  # 获取主题文本颜色
  text_color = get_text_color()
  
  # 获取画布背景色（固定灰黑色 #2a2a2a）
  bg_color = get_canvas_background_color()
  ```

#### 5. 直方图模块 (ui/histograms.py)

提供数据可视化功能：

- **BaseHistogram**：直方图基类，提供通用的绘制框架
  - 数据管理（set_data, clear）
  - 绘制框架（paintEvent）
  - 辅助方法（绘制基线、最大值标签）
- **LuminanceHistogramWidget**：明度直方图
  - 9个明度区域显示
  - 区域选择和高亮
  - 鼠标交互
- **RGBHistogramWidget**：RGB通道直方图
  - R、G、B 三通道显示
  - 叠例显示

#### 6. 场景配置管理模块 (core/config.py - SceneConfigManager)

管理配色预览场景的配置，支持动态加载和扩展：

- **SceneConfigManager**：场景配置管理器
  - 加载内置场景配置（`preview_scenes/scenes.json`）
  - 加载用户自定义场景（`preview_scenes/user_scenes/*.json`）
  - 场景的导入导出功能
  - 用户自定义场景的增删改查
- **配置格式**：JSON 格式定义场景属性（id、name、type、description、config 等）
- **场景类型**：支持 svg、composite、mobile、web 等多种类型
- **使用示例**：
  ```python
  from core import get_scene_config_manager
  
  scene_manager = get_scene_config_manager()
  
  # 获取所有场景
  all_scenes = scene_manager.get_all_scenes()
  
  # 导出场景配置
  success, message = scene_manager.export_scene("ui", "ui_config.json")
  
  # 导入场景配置
  success, message = scene_manager.import_scene("my_scene.json")
  ```

#### 7. 预览场景组件模块 (ui/preview_widgets.py)

提供配色预览的多种场景实现：

- **BasePreviewScene**：场景基类，所有预览场景必须继承
  - 统一的配色设置接口
  - 配置驱动的初始化
- **PreviewSceneFactory**：场景工厂，动态创建场景实例
  - 注册场景类型
  - 根据配置创建对应场景
- **MobileUIPreview**：手机UI场景预览
  - 模拟手机应用界面（状态栏、内容区、导航栏）
  - 使用配色填充不同UI元素
- **WebPreview**：网页布局场景预览
  - 模拟网页设计（导航栏、Hero区、内容卡片、页脚）
  - 展示配色在Web设计中的应用
- **SVGPreviewWidget**：SVG自定义预览
  - 加载和显示SVG文件
  - 将配色应用到SVG元素
- **PreviewSceneSelector**：场景选择器
  - 从配置动态加载场景列表
  - 支持场景切换

---

## 技术亮点与创新

**取色卡 (Color Card)** 在技术上具有多项亮点和创新，体现了现代 GUI 应用开发的良好实践：

### 1. 现代化 UI 设计

- **简约设计风格**：采用极简的设计语言，减少不必要的元素，突出核心功能
- **高 DPI 支持**：自动适配不同屏幕分辨率和缩放比例，保证显示清晰
- **平滑动画**：添加了窗口过渡、控件交互等平滑动画效果，提升用户体验
- **响应式设计**：适配不同屏幕尺寸和布局，保证内容完整显示
- **主题切换系统**：
  - 集成系统级深色/浅色主题切换，标题栏一键切换
  - 所有组件自动响应主题变化，实时更新颜色
  - 集中式颜色管理，通过 `theme_colors.py` 统一维护
  - 使用 `qconfig.themeChangedFinished` 信号实现组件级主题响应

### 2. 高效的事件处理机制

- **多线程设计**：耗时操作（如直方图计算）放在后台线程执行，保证 UI 响应流畅
- **批量更新优化**：使用 setUpdatesEnabled(False/True) 包裹批量更新操作，避免频繁重绘
- **相对坐标系统**：取色点位置使用相对坐标存储，图片缩放时自动调整，保持位置不变
- **采样优化**：直方图计算使用采样策略，避免处理所有像素，提高计算效率

### 3. 专业的色彩处理

- **多种色彩空间**：支持 HSB、LAB、HSL、CMYK、RGB 等多种色彩空间，满足不同场景需求
- **Rec. 709 标准**：明度计算使用 Rec. 709 标准，包含 sRGB Gamma 校正，与专业软件保持一致
- **LAB 颜色空间**：支持 LAB 颜色空间，适合颜色差异计算和感知均匀性分析
- **实时转换**：所有色彩空间转换实时计算，拖动取色点时立即更新

### 4. 完善的调试和监控机制

- **详细日志**：提供全面的调试信息，便于调试和问题排查
- **异常处理**：全局异常捕获，防止应用程序意外崩溃
- **配置管理**：支持窗口状态记忆和设置持久化

### 5. 模块化架构设计

- **清晰的模块划分**：功能模块化，便于维护和扩展
- **基类抽象**：提取公共基类（BaseCanvas、BaseCard、BaseHistogram），消除代码重复
- **扁平化结构**：采用2级目录结构，避免过度嵌套，提高代码可维护性
- **高内聚实现**：每个模块专注于特定功能，实现高内聚
- **可扩展性**：设计时考虑了未来功能扩展，便于添加新特性

---

## 开发规范

本项目遵循严格的开发规范，确保代码质量和可维护性。

### 代码风格

- 遵循 **PEP 8** 代码风格规范
- 使用 4 个空格缩进
- 行长度限制在 100 字符以内

### 命名规范

| 类型 | 规范 | 示例 |
|:---|:---|:---:|
| 类名 | 驼峰命名法 | `ColorPicker`, `ImageCanvas` |
| 函数/方法 | 小写+下划线 | `extract_color()` |
| 变量 | 小写+下划线 | `picker_positions` |
| 常量 | 大写+下划线 | `PICKER_RADIUS = 12` |
| 私有属性 | 单下划线前缀 | `_dragging` |

### 导入规范

导入顺序：**标准库 → 第三方库 → 项目模块**

```python
# 标准库导入
import sys
import math
from pathlib import Path

# 第三方库导入
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import FluentWindow

# 项目模块导入
from core import get_color_info, get_config_manager
from ui import MainWindow
```

详细的开发规范请参考 [开发规范.md](./开发规范.md)。

---

## 贡献指南

我们欢迎并感谢所有社区成员对 Color Card 的贡献。

### 提交 Issue

如果你发现了 Bug，或有新的功能建议，请先在 Gitee 的 Issues 页面搜索是否已有相关问题。如果没有，请创建新的 Issue，并尽量详细地描述问题或建议。

### 代码贡献流程

1. Fork 本项目的 Gitee 主仓库或 GitHub 镜像仓库
2. 创建你的特性分支：`git checkout -b feature/你的功能名称`
3. 提交你的更改：`git commit -m '[类型] 添加了某个功能'`
4. 将分支推送到你的 Fork：`git push origin feature/你的功能名称`
5. 在 Gitee 主仓库上对该分支创建一个 Pull Request（推荐）

### 遵循开发规范

所有贡献的代码必须严格遵循项目已有的开发规范：

- [开发规范.md](./开发规范.md) - 涵盖代码组织、样式、命名等全方位规范

---

## 许可证信息

### 主项目许可证

Color Card 采用 **GNU General Public License v3.0 (GPL 3.0)** 许可证发布。这意味着您可以自由地使用、修改和分发本软件，但如果您分发修改后的版本，也必须采用相同的 GPL 3.0 许可证开源您的修改。

### 许可证文件

- **项目完整许可证信息**：[LICENSE](./LICENSE)
- **GPL 3.0 官方文本**：[https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html)

### 第三方库许可证

本项目使用了以下第三方库：

| 库 | 许可证 |
|:---|:---:|
| PySide6 | LGPL-3.0 |
| PySide6-Fluent-Widgets | GPL-3.0 |
| Pillow | MIT License |
| requests | Apache-2.0 |
| numpy | BSD-3-Clause |
| Open Color | MIT License |
| Tailwind CSS Colors | MIT License |
| Material Design Colors | Apache-2.0 |
| ColorBrewer | Apache-2.0 |
| Radix Colors | MIT License |
| Nord | MIT License |
| Dracula | MIT License |
| Solarized | MIT License |
| Gruvbox | MIT License |
| Catppuccin | MIT License |
| Rose Pine | MIT License |
| Nice Color Palettes | MIT License |

---

## 联系方式

- **主仓库（Gitee）**：[https://gitee.com/qingshangongzai/color_card](https://gitee.com/qingshangongzai/color_card)
- **镜像仓库（GitHub）**：[https://github.com/qingshangongzai/Color_Card](https://github.com/qingshangongzai/Color_Card)
- **联系邮箱**：[hxiao_studio@163.com](mailto:hxiao_studio@163.com)

---

**免责声明**：Color Card 仅供学习和研究使用。开发者不对因使用本工具导致的任何后果负责，请谨慎使用。

---

**取色卡 (Color Card)** - 为摄影师和设计师打造的一站式配色工具和图片色彩分析工具  
Copyright © 2026 浮晓 HXiao Studio
