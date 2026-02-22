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
| 配置存储 | JSON | 简单易用，可读性好 |
| 日志 | logging | Python标准库 |

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      应用层 (Application)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  MainWindow │  │  Dialogs    │  │  Event Handlers     │ │
│  │  主窗口      │  │  对话框      │  │  事件处理器          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      业务逻辑层 (Business)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ SVGParser   │  │ Semantic    │  │ ExportManager       │ │
│  │ SVG解析器    │  │ Analyzer    │  │ 导出管理器           │ │
│  │             │  │ 语义分析器   │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Element     │  │ Conflict    │  │ ConfigManager       │ │
│  │ Manager     │  │ Detector    │  │ 配置管理器           │ │
│  │ 元素管理器   │  │ 冲突检测器   │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      数据层 (Data)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ SVGElement  │  │ Project     │  │ UserConfig          │ │
│  │ 元素对象     │  │ Config      │  │ 用户配置             │ │
│  │             │  │ 项目配置     │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      基础设施层 (Infrastructure)             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Logger      │  │ FileIO      │  │ CanvasRenderer      │ │
│  │ 日志系统     │  │ 文件IO      │  │ 画布渲染器           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 模块依赖关系

```
main.py
  ├── ui/
  │     ├── main_window.py      → 依赖: core, utils
  │     ├── preview_canvas.py   → 依赖: core
  │     ├── element_list.py     → 依赖: core
  │     └── dialogs/
  │           ├── export_dialog.py
  │           ├── settings_dialog.py
  │           └── about_dialog.py
  ├── core/
  │     ├── svg_parser.py       → 依赖: models
  │     ├── semantic_analyzer.py → 依赖: models, rules
  │     ├── element_manager.py  → 依赖: models
  │     ├── export_manager.py   → 依赖: models
  │     └── conflict_detector.py → 依赖: models
  ├── models/
  │     ├── svg_element.py
  │     └── project_config.py
  ├── rules/
  │     ├── recognition_rules.py
  │     └── color_rules.py
  ├── utils/
  │     ├── config_manager.py
  │     ├── logger.py
  │     └── file_utils.py
  └── constants.py
```

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
- **文件历史**: 支持撤销/重做操作历史

#### 2. 预览渲染模块
- **Canvas渲染**: 使用tkinter.Canvas绘制SVG预览
- **缩放功能**: 支持放大/缩小/适应窗口（25%-400%）
- **平移功能**: 支持拖拽移动画布
- **元素高亮**: 鼠标悬停时高亮对应元素
- **选中状态**: 点击元素在列表中选中
- **网格显示**: 可选显示辅助网格

#### 3. 智能识别模块

##### 识别策略

| 策略 | 描述 | 优先级 | 权重 |
|------|------|--------|------|
| 面积排序 | 面积最大的rect → background | 高 | 0.3 |
| 位置分析 | 最外层边框 → frame (primary) | 高 | 0.25 |
| 颜色聚类 | 按颜色分组，识别主次色调 | 中 | 0.2 |
| 形状识别 | 文字→text, 圆形→button | 中 | 0.15 |
| 层级关系 | 父元素优先于子元素 | 低 | 0.1 |

##### 识别规则

```python
RECOGNITION_RULES = {
    "background": {
        "type": ["rect"],
        "max_area": True,
        "position": "back",
        "z_index": "lowest",
        "class": "background",
        "confidence_threshold": 0.8
    },
    "frame": {
        "type": ["rect"],
        "position": "outer",
        "stroke_width": ">2",
        "class": "primary",
        "fixed": "original",
        "confidence_threshold": 0.7
    },
    "primary_element": {
        "type": ["rect", "circle", "ellipse"],
        "area_ratio": "0.1-0.3",
        "color_frequency": "high",
        "class": "primary",
        "confidence_threshold": 0.6
    },
    "secondary_element": {
        "type": ["rect", "circle", "ellipse", "path"],
        "area_ratio": "0.05-0.15",
        "color_frequency": "medium",
        "class": "secondary",
        "confidence_threshold": 0.5
    },
    "accent_element": {
        "color": "brightest",
        "area_ratio": "<0.05",
        "class": "accent",
        "confidence_threshold": 0.6
    },
    "text": {
        "type": ["text"],
        "class": "text",
        "fixed": "black",
        "confidence_threshold": 0.9
    }
}
```

#### 4. 手动编辑模块
- **修改class**: 下拉选择 background/primary/secondary/accent/text/none
- **设置fixed**: 勾选是否固定颜色(original/black/none)
- **编辑id**: 修改元素id，确保唯一性（自动检测重复）
- **编辑注释**: 为元素添加说明文字
- **批量操作**: 支持多选元素批量修改
- **属性预览**: 实时预览修改效果

#### 5. 导出模块
- **格式验证**: 检查SVG是否符合规范
- **生成报告**: 显示导出摘要（元素统计、冲突列表）
- **保存文件**: 选择保存位置，支持覆盖/重命名
- **导出选项**:
  - 是否保留原始属性
  - 是否添加注释
  - 缩进格式（2/4空格/Tab）
  - 是否压缩（去除多余空格）

## 数据模型

### 元素对象

```python
@dataclass
class SVGElement:
    """SVG元素数据模型"""
    
    # 基础属性
    id: str
    tag: str
    attributes: Dict[str, str]
    
    # 语义属性
    class_name: Optional[str] = None
    fixed_color: Optional[str] = None
    confidence: float = 0.0  # 识别置信度
    
    # 几何属性
    bounds: Tuple[float, float, float, float]  # x, y, width, height
    area: float = 0.0
    center: Tuple[float, float] = (0.0, 0.0)
    
    # 样式属性
    fill_color: Optional[str] = None
    stroke_color: Optional[str] = None
    stroke_width: float = 0.0
    opacity: float = 1.0
    
    # 层级属性
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    z_index: int = 0
    
    # 元数据
    description: str = ""
    is_manual_edited: bool = False
    original_attributes: Dict[str, str] = field(default_factory=dict)
    
    def to_svg_attributes(self) -> Dict[str, str]:
        """转换为SVG属性"""
        attrs = self.original_attributes.copy()
        attrs['id'] = self.id
        if self.class_name:
            attrs['class'] = self.class_name
        if self.fixed_color:
            attrs['data-fixed-color'] = self.fixed_color
        return attrs
```

### 项目配置

```python
@dataclass
class ProjectConfig:
    """项目配置数据模型"""
    
    # 画布设置
    canvas_width: int = 400
    canvas_height: int = 300
    view_box: Tuple[float, float, float, float] = (0, 0, 400, 300)
    
    # 场景类型
    scene_type: str = "ui"  # ui/web/illustration/icon
    
    # 颜色映射
    color_mapping: Dict[str, int] = field(default_factory=lambda: {
        "background": 0,
        "primary": 1,
        "secondary": 2,
        "accent": 3,
        "text": 4
    })
    
    # 识别设置
    recognition_settings: Dict[str, Any] = field(default_factory=lambda: {
        "auto_detect_on_load": True,
        "confidence_threshold": 0.6,
        "use_color_clustering": True,
        "use_position_analysis": True
    })
    
    # 导出设置
    export_settings: Dict[str, Any] = field(default_factory=lambda: {
        "indent_size": 2,
        "use_tabs": False,
        "minify": False,
        "add_comments": True,
        "preserve_original_attrs": False
    })
```

### 用户配置

```python
@dataclass
class UserConfig:
    """用户偏好配置"""
    
    # 界面设置
    theme: str = "system"  # light/dark/system
    language: str = "zh_CN"
    window_size: Tuple[int, int] = (1200, 800)
    window_position: Tuple[int, int] = (100, 100)
    
    # 预览设置
    default_zoom: float = 1.0
    show_grid: bool = True
    grid_size: int = 10
    highlight_on_hover: bool = True
    
    # 文件设置
    recent_files: List[str] = field(default_factory=list)
    max_recent_files: int = 10
    default_export_path: Optional[str] = None
    auto_save: bool = True
    auto_save_interval: int = 300  # 秒
    
    # 高级设置
    log_level: str = "INFO"
    log_file: Optional[str] = None
    backup_before_export: bool = True
```

## 核心算法

### 1. 元素语义识别算法

```python
class SemanticAnalyzer:
    """语义分析器"""
    
    def analyze(self, elements: List[SVGElement]) -> AnalysisResult:
        """
        分析元素语义并设置class
        
        流程：
        1. 预处理：计算面积、中心点、层级关系
        2. 背景识别：面积最大且在最底层
        3. 边框识别：最外层，有描边
        4. 文字识别：text标签
        5. 颜色聚类：按颜色分类剩余元素
        6. 主次色调分配
        7. 冲突检测与解决
        """
        result = AnalysisResult()
        
        # 1. 预处理
        self._preprocess(elements)
        
        # 2. 识别背景
        background = self._find_background(elements)
        if background:
            background.class_name = "background"
            background.confidence = 0.9
            result.identified.append(background)
        
        # 3. 识别边框
        frame = self._find_frame(elements)
        if frame:
            frame.class_name = "primary"
            frame.fixed_color = "original"
            frame.confidence = 0.85
            result.identified.append(frame)
        
        # 4. 识别文字
        text_elements = self._find_text_elements(elements)
        for elem in text_elements:
            elem.class_name = "text"
            elem.fixed_color = "black"
            elem.confidence = 0.95
            result.identified.append(elem)
        
        # 5. 颜色聚类
        remaining = [e for e in elements if not e.class_name]
        color_groups = self._group_by_color(remaining)
        
        # 6. 分配主次色调
        self._assign_classes_by_color_hierarchy(color_groups, result)
        
        # 7. 冲突检测
        result.conflicts = self._detect_conflicts(elements)
        
        return result
    
    def _preprocess(self, elements: List[SVGElement]) -> None:
        """预处理：计算辅助属性"""
        for elem in elements:
            # 计算面积
            elem.area = elem.bounds[2] * elem.bounds[3]
            # 计算中心点
            elem.center = (
                elem.bounds[0] + elem.bounds[2] / 2,
                elem.bounds[1] + elem.bounds[3] / 2
            )
    
    def _find_background(self, elements: List[SVGElement]) -> Optional[SVGElement]:
        """查找背景元素（面积最大且在最底层）"""
        candidates = [e for e in elements if e.tag == "rect"]
        if not candidates:
            return None
        
        # 按面积排序，取最大的
        candidates.sort(key=lambda e: e.area, reverse=True)
        largest = candidates[0]
        
        # 检查是否在最底层（z_index最小）
        min_z = min(e.z_index for e in elements)
        if largest.z_index == min_z:
            return largest
        
        return None
    
    def _find_frame(self, elements: List[SVGElement]) -> Optional[SVGElement]:
        """查找边框元素（最外层，有描边）"""
        candidates = [
            e for e in elements 
            if e.tag == "rect" and e.stroke_width > 2
        ]
        if not candidates:
            return None
        
        # 按位置判断（最外层）
        # 简化：选择stroke_width最大的
        candidates.sort(key=lambda e: e.stroke_width, reverse=True)
        return candidates[0]
    
    def _group_by_color(
        self, 
        elements: List[SVGElement]
    ) -> Dict[str, List[SVGElement]]:
        """按颜色分组元素"""
        groups = defaultdict(list)
        for elem in elements:
            color = self._simplify_color(elem.fill_color)
            if color:
                groups[color].append(elem)
        return groups
    
    def _simplify_color(self, color: Optional[str]) -> Optional[str]:
        """简化颜色值，相近颜色归为一组"""
        if not color:
            return None
        
        # 转换为RGB
        rgb = self._parse_color(color)
        if not rgb:
            return None
        
        # 量化到相近的颜色组（每通道8级）
        simplified = tuple(int(c / 32) * 32 for c in rgb)
        return f"#{simplified[0]:02x}{simplified[1]:02x}{simplified[2]:02x}"
    
    def _assign_classes_by_color_hierarchy(
        self,
        color_groups: Dict[str, List[SVGElement]],
        result: AnalysisResult
    ) -> None:
        """根据颜色层次分配class"""
        # 按元素数量排序颜色组
        sorted_groups = sorted(
            color_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        # 分配class
        class_assignment = {
            0: "primary",
            1: "secondary",
            2: "accent"
        }
        
        for idx, (color, elements) in enumerate(sorted_groups[:3]):
            class_name = class_assignment.get(idx)
            if class_name:
                for elem in elements:
                    elem.class_name = class_name
                    elem.confidence = 0.6 - idx * 0.1
                    result.identified.append(elem)
```

### 2. 颜色聚类算法

```python
class ColorClustering:
    """颜色聚类分析"""
    
    def analyze(self, elements: List[SVGElement]) -> ColorAnalysis:
        """分析颜色分布"""
        analysis = ColorAnalysis()
        
        # 收集所有颜色
        colors = []
        for elem in elements:
            if elem.fill_color:
                colors.append(self._normalize_color(elem.fill_color))
        
        if not colors:
            return analysis
        
        # K-means聚类（K=5）
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=min(5, len(colors)), random_state=42)
        kmeans.fit(colors)
        
        # 分析每个聚类
        for i, center in enumerate(kmeans.cluster_centers_):
            cluster_elements = [
                elements[j] for j, label in enumerate(kmeans.labels_)
                if label == i
            ]
            
            analysis.clusters.append(ColorCluster(
                center_color=self._rgb_to_hex(center),
                elements=cluster_elements,
                count=len(cluster_elements),
                avg_area=sum(e.area for e in cluster_elements) / len(cluster_elements)
            ))
        
        # 排序：按元素数量
        analysis.clusters.sort(key=lambda c: c.count, reverse=True)
        
        return analysis
```

### 3. 冲突检测算法

```python
class ConflictDetector:
    """冲突检测器"""
    
    def detect(self, elements: List[SVGElement]) -> List[Conflict]:
        """检测潜在问题"""
        conflicts = []
        
        # 1. 检查重复ID
        conflicts.extend(self._check_duplicate_ids(elements))
        
        # 2. 检查无class元素
        conflicts.extend(self._check_missing_classes(elements))
        
        # 3. 检查溢出元素
        conflicts.extend(self._check_out_of_bounds(elements))
        
        # 4. 检查重叠元素
        conflicts.extend(self._check_overlapping(elements))
        
        # 5. 检查颜色对比度
        conflicts.extend(self._check_color_contrast(elements))
        
        return conflicts
    
    def _check_duplicate_ids(
        self, 
        elements: List[SVGElement]
    ) -> List[Conflict]:
        """检查重复ID"""
        conflicts = []
        id_counts = defaultdict(list)
        
        for elem in elements:
            id_counts[elem.id].append(elem)
        
        for id_str, elems in id_counts.items():
            if len(elems) > 1:
                conflicts.append(Conflict(
                    type=ConflictType.DUPLICATE_ID,
                    severity=Severity.ERROR,
                    message=f"存在重复ID: {id_str}",
                    elements=elems,
                    suggestion="请为元素设置唯一的ID"
                ))
        
        return conflicts
    
    def _check_missing_classes(
        self, 
        elements: List[SVGElement]
    ) -> List[Conflict]:
        """检查无class元素"""
        conflicts = []
        
        for elem in elements:
            if not elem.class_name:
                conflicts.append(Conflict(
                    type=ConflictType.MISSING_CLASS,
                    severity=Severity.WARNING,
                    message=f"元素 {elem.id} 未设置class",
                    elements=[elem],
                    suggestion="建议设置语义化class"
                ))
        
        return conflicts
    
    def _check_out_of_bounds(
        self, 
        elements: List[SVGElement]
    ) -> List[Conflict]:
        """检查溢出元素"""
        conflicts = []
        
        # 假设画布大小
        canvas_bounds = (0, 0, 400, 300)
        
        for elem in elements:
            if self._is_out_of_bounds(elem.bounds, canvas_bounds):
                conflicts.append(Conflict(
                    type=ConflictType.OUT_OF_BOUNDS,
                    severity=Severity.WARNING,
                    message=f"元素 {elem.id} 可能溢出画布",
                    elements=[elem],
                    suggestion="请检查元素位置和大小"
                ))
        
        return conflicts
```

## 文件格式

### 输入格式
- 标准SVG文件 (.svg)
- 支持基本形状: rect, circle, ellipse, path, text
- 支持分组: g 标签
- 支持变换: transform 属性（需要解析）

### 输出格式
符合Color Card项目规范的语义化SVG:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
  <!-- 背景 -->
  <rect id="background" class="background" x="0" y="0" width="400" height="300" fill="#f5f5f5"/>
  
  <!-- 固定颜色元素 -->
  <rect id="frame" class="primary" data-fixed-color="original" x="10" y="10" width="380" height="280" fill="none" stroke="#333" stroke-width="3"/>
  
  <!-- 可映射元素 -->
  <rect id="card1" class="accent" x="30" y="50" width="160" height="100" rx="8" fill="#ff6b6b"/>
  <rect id="card2" class="secondary" x="210" y="50" width="160" height="100" rx="8" fill="#4ecdc4"/>
  
  <!-- 文字 -->
  <text id="title" class="text" data-fixed-color="black" x="200" y="200" text-anchor="middle" font-size="24" fill="#000">Hello World</text>
</svg>
```

### 配置文件格式

```json
{
  "version": "1.0.0",
  "user_config": {
    "theme": "system",
    "language": "zh_CN",
    "window_size": [1200, 800],
    "recent_files": [
      "C:/Projects/example.svg"
    ],
    "preview": {
      "default_zoom": 1.0,
      "show_grid": true,
      "grid_size": 10
    }
  },
  "project_defaults": {
    "canvas_width": 400,
    "canvas_height": 300,
    "scene_type": "ui",
    "recognition": {
      "auto_detect_on_load": true,
      "confidence_threshold": 0.6
    },
    "export": {
      "indent_size": 2,
      "add_comments": true
    }
  }
}
```

## 错误处理与日志系统

### 错误分类

| 错误级别 | 描述 | 处理方式 |
|---------|------|---------|
| CRITICAL | 程序崩溃 | 记录日志，显示错误对话框，尝试恢复 |
| ERROR | 功能失败 | 记录日志，显示错误提示，回滚操作 |
| WARNING | 潜在问题 | 记录日志，显示警告，继续执行 |
| INFO | 普通信息 | 记录日志，状态栏显示 |
| DEBUG | 调试信息 | 仅记录到日志文件 |

### 日志配置

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """配置日志系统"""
    
    # 创建logger
    logger = logging.getLogger("svg_converter")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger
```

### 异常处理策略

```python
class SVGConverterError(Exception):
    """基础异常类"""
    pass

class ParseError(SVGConverterError):
    """解析错误"""
    pass

class ExportError(SVGConverterError):
    """导出错误"""
    pass

class ValidationError(SVGConverterError):
    """验证错误"""
    pass

def handle_error(error: Exception, context: str = "") -> None:
    """统一错误处理"""
    logger = logging.getLogger("svg_converter")
    
    if isinstance(error, SVGConverterError):
        logger.error(f"{context}: {error}")
        messagebox.showerror("错误", str(error))
    elif isinstance(error, FileNotFoundError):
        logger.error(f"{context}: 文件未找到 - {error}")
        messagebox.showerror("错误", f"文件未找到: {error.filename}")
    else:
        logger.exception(f"{context}: 未预期的错误")
        messagebox.showerror(
            "错误", 
            f"发生未预期的错误:\n{str(error)}\n\n请查看日志文件获取详细信息。"
        )
```

## 配置管理

### 配置管理器

```python
class ConfigManager:
    """配置管理器"""
    
    CONFIG_FILE = "config.json"
    
    def __init__(self):
        self.config_path = self._get_config_path()
        self.user_config = UserConfig()
        self.project_defaults = ProjectConfig()
        self._load()
    
    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        # Windows: %APPDATA%/SVGConverter/config.json
        # macOS: ~/Library/Application Support/SVGConverter/config.json
        # Linux: ~/.config/SVGConverter/config.json
        
        if sys.platform == "win32":
            base_path = Path(os.environ.get("APPDATA", ""))
        elif sys.platform == "darwin":
            base_path = Path.home() / "Library/Application Support"
        else:
            base_path = Path.home() / ".config"
        
        config_dir = base_path / "SVGConverter"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / self.CONFIG_FILE
    
    def _load(self) -> None:
        """加载配置"""
        if not self.config_path.exists():
            self._save()  # 创建默认配置
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载用户配置
            if 'user_config' in data:
                self.user_config = UserConfig(**data['user_config'])
            
            # 加载项目默认配置
            if 'project_defaults' in data:
                self.project_defaults = ProjectConfig(**data['project_defaults'])
                
        except Exception as e:
            logging.getLogger("svg_converter").error(f"加载配置失败: {e}")
            # 使用默认配置
    
    def save(self) -> None:
        """保存配置"""
        data = {
            "version": "1.0.0",
            "user_config": self.user_config.__dict__,
            "project_defaults": self.project_defaults.__dict__
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.getLogger("svg_converter").error(f"保存配置失败: {e}")
    
    def add_recent_file(self, file_path: str) -> None:
        """添加最近文件"""
        recent = self.user_config.recent_files
        
        # 移除已存在的相同路径
        if file_path in recent:
            recent.remove(file_path)
        
        # 添加到开头
        recent.insert(0, file_path)
        
        # 限制数量
        self.user_config.recent_files = recent[:self.user_config.max_recent_files]
        
        self.save()
```

## 测试策略

### 测试结构

```
tests/
├── unit/                       # 单元测试
│     ├── test_svg_parser.py
│     ├── test_semantic_analyzer.py
│     ├── test_element_manager.py
│     └── test_export_manager.py
├── integration/                # 集成测试
│     ├── test_workflow.py
│     └── test_file_io.py
├── fixtures/                   # 测试数据
│     ├── sample.svg
│     ├── complex_ui.svg
│     └── invalid.svg
└── conftest.py                 # pytest配置
```

### 关键测试用例

```python
# test_semantic_analyzer.py

class TestSemanticAnalyzer:
    """语义分析器测试"""
    
    def test_background_detection(self):
        """测试背景识别"""
        elements = [
            SVGElement(id="bg", tag="rect", bounds=(0, 0, 400, 300), fill_color="#fff"),
            SVGElement(id="btn", tag="rect", bounds=(10, 10, 50, 30), fill_color="#333"),
        ]
        
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(elements)
        
        bg = next(e for e in elements if e.id == "bg")
        assert bg.class_name == "background"
        assert bg.confidence > 0.8
    
    def test_text_detection(self):
        """测试文字识别"""
        elements = [
            SVGElement(id="title", tag="text", bounds=(0, 0, 100, 20)),
        ]
        
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(elements)
        
        text = elements[0]
        assert text.class_name == "text"
        assert text.fixed_color == "black"
    
    def test_conflict_detection(self):
        """测试冲突检测"""
        elements = [
            SVGElement(id="dup", tag="rect", bounds=(0, 0, 10, 10)),
            SVGElement(id="dup", tag="rect", bounds=(20, 20, 10, 10)),
        ]
        
        detector = ConflictDetector()
        conflicts = detector.detect(elements)
        
        assert any(c.type == ConflictType.DUPLICATE_ID for c in conflicts)
```

## 性能优化

### 优化策略

| 优化点 | 策略 | 预期效果 |
|-------|------|---------|
| 大文件加载 | 异步解析 + 进度显示 | 避免UI卡顿 |
| Canvas渲染 | 视口裁剪 + 分层渲染 | 提升渲染速度 |
| 颜色聚类 | 采样优化 + 缓存 | 减少计算量 |
| 内存管理 | 懒加载 + 及时释放 | 降低内存占用 |

### 异步处理示例

```python
import threading
from concurrent.futures import ThreadPoolExecutor

class AsyncProcessor:
    """异步处理器"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._callbacks = {}
    
    def process_async(self, task_id: str, func: Callable, callback: Callable):
        """异步执行任务"""
        future = self.executor.submit(func)
        self._callbacks[future] = (task_id, callback)
        future.add_done_callback(self._on_complete)
    
    def _on_complete(self, future):
        """任务完成回调"""
        task_id, callback = self._callbacks.pop(future, (None, None))
        
        try:
            result = future.result()
            if callback:
                callback(task_id, result, None)
        except Exception as e:
            if callback:
                callback(task_id, None, e)
```

## 扩展功能（未来版本）

### V1.1
- [ ] 批量处理多个SVG文件
- [ ] 预设模板库（手机UI、网页、插画）
- [ ] 快捷键支持
- [ ] 撤销/重做功能

### V1.2
- [ ] 插件系统，支持自定义识别规则
- [ ] 与配色方案库联动
- [ ] 实时预览配色效果
- [ ] 命令行模式

### V2.0
- [ ] Web版本（使用PyScript或转译为JS）
- [ ] 云端协作功能
- [ ] AI辅助识别
- [ ] 图片转SVG功能（集成智谱AI）

## 开发计划

### 第一阶段（MVP）- 预计4周
- [ ] 基础GUI框架搭建（1周）
- [ ] SVG文件加载和预览（1周）
- [ ] 基础识别算法（面积+位置）（1周）
- [ ] 手动编辑功能（0.5周）
- [ ] 导出功能（0.5周）

### 第二阶段 - 预计3周
- [ ] 优化识别算法（颜色聚类）（1周）
- [ ] 冲突检测和提示（0.5周）
- [ ] 配置管理系统（0.5周）
- [ ] 批量处理（0.5周）
- [ ] 完善文档和测试（0.5周）

### 第三阶段 - 预计2周
- [ ] 开源发布准备（1周）
- [ ] 社区反馈收集（持续）
- [ ] 持续迭代优化（持续）

## 参考资源

- [Color Card 项目SVG规范](./开发规范.md)
- [SVG 1.1 规范](https://www.w3.org/TR/SVG11/)
- [SVG 2.0 规范](https://www.w3.org/TR/SVG2/)
- [Tkinter 文档](https://docs.python.org/3/library/tkinter.html)
- [智谱AI GLM-4V API文档](https://docs.bigmodel.cn/api-reference/模型-api/对话补全#视觉模型)

## 许可证

MIT License - 与开源社区项目保持一致

---

## 附录

### A. 语义化class规范

| class | 含义 | 用途 | 示例 |
|-------|------|------|------|
| background | 背景 | 页面/画板背景 | 大面积底色 |
| primary | 主色调 | 主要UI元素 | 按钮、标题栏 |
| secondary | 次色调 | 次要UI元素 | 卡片、输入框 |
| accent | 强调色 | 突出显示 | 图标、标签 |
| text | 文字 | 所有文本元素 | 标题、正文 |

### B. data-fixed-color规范

| 值 | 含义 | 使用场景 |
|----|------|---------|
| original | 保持原始颜色 | 品牌色、特殊颜色 |
| black | 固定为黑色 | 文字、图标 |
| none | 跟随主题变化 | 普通UI元素 |

### C. 文件命名规范

- 源代码：snake_case.py
- 类名：PascalCase
- 函数/变量：snake_case
- 常量：UPPER_SNAKE_CASE
- 私有成员：_leading_underscore
