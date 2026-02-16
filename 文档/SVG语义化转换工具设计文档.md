# SVG语义化转换工具设计文档

## 项目背景

为配合配色方案和配色预览SVG的开源社区项目，需要一个能够将普通SVG转换为符合规范的语义化格式SVG的工具。该工具将使用Tkinter构建GUI界面，采用MIT协议开源。

## 目标

创建一个用户友好的桌面应用程序，帮助用户：
1. 导入普通SVG文件
2. 自动识别元素语义（background/primary/secondary/accent/text）
3. 手动调整识别结果
4. 导出符合规范的语义化SVG

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| GUI框架 | Tkinter | Python标准库，MIT协议兼容，无需额外依赖 |
| SVG解析 | xml.etree.ElementTree | Python标准库，轻量级 |
| SVG预览 | tkinter.Canvas | 原生支持，无需额外库 |
| 打包 | PyInstaller | 生成独立可执行文件 |

## 界面设计

### 主窗口布局

```
┌─────────────────────────────────────────────────────────────┐
│  SVG语义化转换工具                                    [_][X] │
├─────────────────────────────────────────────────────────────┤
│  文件操作区                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [选择SVG文件...]  /path/to/input.svg            [📁] │  │
│  └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  预览区域 (左)          │  识别结果 (右)                      │
│  ┌──────────────────┐   │  ┌────────────────────────────┐  │
│  │                  │   │  │ 元素列表                    │  │
│  │   SVG预览        │   │  │                            │  │
│  │   (Canvas渲染)   │   │  │ ☑ background (矩形)        │  │
│  │                  │   │  │    id: background           │  │
│  │                  │   │  │    class: background        │  │
│  │                  │   │  │                            │  │
│  │                  │   │  │ ☑ frame (矩形)             │  │
│  │                  │   │  │    id: phone-frame          │  │
│  │                  │   │  │    class: primary           │  │
│  │                  │   │  │    fixed: original          │  │
│  │                  │   │  │                            │  │
│  │                  │   │  │ ☐ card1 (矩形)             │  │
│  │                  │   │  │    [建议: primary] [修改]   │  │
│  │                  │   │  │                            │  │
│  └──────────────────┘   │  └────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  操作按钮区                                                   │
│  [自动识别] [重置] [手动添加] [导出SVG]                        │
├─────────────────────────────────────────────────────────────┤
│  状态栏: 就绪 | 已识别 5 个元素 | 画布: 300x400               │
└─────────────────────────────────────────────────────────────┘
```

### 功能模块

#### 1. 文件操作模块
- **选择文件**: 打开文件对话框，支持.svg格式
- **拖拽支持**: 支持从文件管理器拖拽SVG文件到窗口
- **最近文件**: 记录最近打开的10个文件

#### 2. 预览渲染模块
- **Canvas渲染**: 使用tkinter.Canvas绘制SVG预览
- **缩放功能**: 支持放大/缩小/适应窗口
- **元素高亮**: 鼠标悬停时高亮对应元素
- **选中状态**: 点击元素在列表中选中

#### 3. 智能识别模块

##### 识别策略

| 策略 | 描述 | 优先级 |
|------|------|--------|
| 面积排序 | 面积最大的rect → background | 高 |
| 位置分析 | 最外层边框 → frame (primary) | 高 |
| 颜色聚类 | 按颜色分组，识别主次色调 | 中 |
| 形状识别 | 文字→text, 圆形→button | 中 |
| 层级关系 | 父元素优先于子元素 | 低 |

##### 识别规则

```python
识别规则配置:
{
    "background": {
        "type": ["rect"],
        "max_area": True,  # 面积最大
        "position": "back",  # 最底层
        "class": "background"
    },
    "frame": {
        "type": ["rect"],
        "position": "outer",  # 最外层
        "stroke_width": ">2",
        "class": "primary",
        "fixed": "original"
    },
    "text": {
        "type": ["text"],
        "class": "text",
        "fixed": "black"
    },
    "accent": {
        "color": "brightest",  # 最亮的颜色
        "class": "accent"
    }
}
```

#### 4. 手动编辑模块
- **修改class**: 下拉选择 background/primary/secondary/accent/text
- **设置fixed**: 勾选是否固定颜色(original/black)
- **编辑id**: 修改元素id，确保唯一性
- **添加注释**: 为元素添加说明

#### 5. 导出模块
- **格式验证**: 检查SVG是否符合规范
- **生成报告**: 显示导出摘要
- **保存文件**: 选择保存位置

## 数据模型

### 元素对象

```python
class SVGElement:
    def __init__(self):
        self.id: str           # 元素ID
        self.tag: str          # SVG标签名 (rect, circle, text等)
        self.class_name: str   # 语义class (background/primary/secondary/accent/text)
        self.fixed_color: str  # 固定颜色 (original/black/None)
        self.attributes: dict  # 原始属性
        self.bounds: tuple     # 边界框 (x, y, width, height)
        self.color: str        # 填充颜色
        self.area: float       # 面积
        self.parent: str       # 父元素ID
        self.children: list    # 子元素ID列表
```

### 项目配置

```python
class ProjectConfig:
    def __init__(self):
        self.canvas_width: int = 400
        self.canvas_height: int = 300
        self.scene_type: str = "ui"  # ui/web/illustration
        self.color_mapping: dict = {
            "background": 0,
            "primary": 1,
            "secondary": 2,
            "accent": 3,
            "text": 4
        }
```

## 核心算法

### 1. 元素语义识别算法

```python
def analyze_semantics(elements: List[SVGElement]) -> None:
    """分析元素语义并设置class"""
    
    # 1. 识别背景（面积最大且在最底层）
    background = find_largest_element(elements)
    background.class_name = "background"
    
    # 2. 识别边框（最外层，有描边）
    frame = find_outer_frame(elements)
    frame.class_name = "primary"
    frame.fixed_color = "original"
    
    # 3. 识别文字
    for elem in elements:
        if elem.tag == "text":
            elem.class_name = "text"
            elem.fixed_color = "black"
    
    # 4. 按颜色分类剩余元素
    color_groups = group_by_color(remaining_elements)
    assign_classes_by_color_hierarchy(color_groups)
```

### 2. 颜色聚类算法

```python
def group_by_color(elements: List[SVGElement]) -> Dict[str, List[SVGElement]]:
    """按颜色分组元素"""
    groups = defaultdict(list)
    for elem in elements:
        # 简化颜色值，相近颜色归为一组
        simplified_color = simplify_color(elem.color)
        groups[simplified_color].append(elem)
    return groups
```

### 3. 冲突检测算法

```python
def detect_conflicts(elements: List[SVGElement]) -> List[str]:
    """检测潜在问题"""
    conflicts = []
    
    # 检查重复ID
    ids = [e.id for e in elements]
    if len(ids) != len(set(ids)):
        conflicts.append("存在重复ID")
    
    # 检查无class元素
    for elem in elements:
        if not elem.class_name:
            conflicts.append(f"元素 {elem.id} 未设置class")
    
    # 检查溢出元素
    for elem in elements:
        if is_out_of_bounds(elem):
            conflicts.append(f"元素 {elem.id} 可能溢出画布")
    
    return conflicts
```

## 文件格式

### 输入格式
- 标准SVG文件 (.svg)
- 支持基本形状: rect, circle, ellipse, path, text

### 输出格式
符合Color Card项目规范的语义化SVG:

```xml
<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
  <!-- 背景 -->
  <rect id="background" class="background" .../>
  
  <!-- 固定颜色元素 -->
  <rect id="frame" class="primary" data-fixed-color="original" .../>
  
  <!-- 可映射元素 -->
  <rect id="card1" class="accent" .../>
  
  <!-- 文字 -->
  <text id="title" class="text" data-fixed-color="black" .../>
</svg>
```

## 扩展功能（未来版本）

### V1.1
- [ ] 批量处理多个SVG文件
- [ ] 预设模板库（手机UI、网页、插画）
- [ ] 快捷键支持

### V1.2
- [ ] 插件系统，支持自定义识别规则
- [ ] 与配色方案库联动
- [ ] 实时预览配色效果

### V2.0
- [ ] Web版本（使用PyScript或转译为JS）
- [ ] 云端协作功能
- [ ] AI辅助识别

## 开发计划

### 第一阶段（MVP）
- [ ] 基础GUI框架搭建
- [ ] SVG文件加载和预览
- [ ] 基础识别算法（面积+位置）
- [ ] 手动编辑功能
- [ ] 导出功能

### 第二阶段
- [ ] 优化识别算法（颜色聚类）
- [ ] 冲突检测和提示
- [ ] 批量处理
- [ ] 完善文档

### 第三阶段
- [ ] 开源发布
- [ ] 社区反馈收集
- [ ] 持续迭代优化

## 参考资源

- [Color Card 项目SVG规范](./开发规范.md)
- [SVG 1.1 规范](https://www.w3.org/TR/SVG11/)
- [Tkinter 文档](https://docs.python.org/3/library/tkinter.html)

## 许可证

MIT License - 与开源社区项目保持一致
