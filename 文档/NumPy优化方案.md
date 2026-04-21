# NumPy 优化方案

## 概述

本文档记录项目中可使用 NumPy 进行性能优化的场景，供后续开发参考。

## 已完成的优化

### 1. QImage 转 NumPy 数组

**位置**: `ui/canvases.py` - `qimage_to_numpy()`

**优化效果**: 20秒 → 50ms (400倍提升)

**关键代码**:
```python
def qimage_to_numpy(image: QImage) -> np.ndarray:
    """QImage转NumPy数组（使用bits()直接内存访问）"""
    width = image.width()
    height = image.height()

    if image.format() != QImage.Format.Format_RGB888:
        image = image.convertToFormat(QImage.Format.Format_RGB888)

    ptr = image.bits()
    bytes_per_line = image.bytesPerLine()

    if bytes_per_line == width * 3:
        arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 3))
    else:
        arr = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            offset = y * bytes_per_line
            row = np.array(ptr[offset:offset + width * 3], dtype=np.uint8)
            arr[y] = row.reshape((width, 3))

    return arr.copy()
```

### 2. 直方图计算

**位置**: `core/color.py` - `_calculate_histogram_numpy()` / `_calculate_rgb_histogram_numpy()`

**优化效果**: Python逐像素遍历 → NumPy向量化计算 (100+倍提升)

**修复问题**: 原代码使用 `ptr.setsize()` 在 PySide6 中不可用，导致始终回退到慢速版本

**后续改进**: 由于 NumPy 优化后速度大幅提升，采样策略可从四步采样改回全采样，获得更精确的直方图数据

## 待优化场景

### 高优先级

#### 1. 高亮区域计算 (饱和度/明度蒙版)

**位置**: 
- `ui/canvases.py:1132` - `_draw_saturation_highlight()` / `_draw_brightness_highlight()`
- `core/luminance_service.py:307, 368`

**当前实现**: 遍历显示区域像素，逐个计算HSV值

**优化思路**:
```python
# 1. 将显示区域转换为NumPy数组
img_array = qimage_to_numpy(image)

# 2. 提取采样区域
sampled = img_array[::sample_step, ::sample_step]

# 3. 向量化HSV转换
r = sampled[:, :, 0] / 255.0
g = sampled[:, :, 1] / 255.0
b = sampled[:, :, 2] / 255.0
h, s, v = rgb_to_hsv_vectorized(r, g, b)

# 4. 向量化阈值比较
mask = s > threshold if mode == 'saturation' else v > threshold
```

#### 2. 主色调提取

**位置**: `core/color.py:1424` - `extract_dominant_colors()`

**当前实现**: 遍历全图采样像素

**优化思路**:
```python
# 1. 全图转NumPy数组
img_array = qimage_to_numpy(image)

# 2. 均匀采样
sampled = img_array[::sample_step, ::sample_step].reshape(-1, 3)

# 3. 使用K-Means聚类 (scipy或sklearn)
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=n_colors, random_state=42)
kmeans.fit(sampled)
colors = kmeans.cluster_centers_.astype(int)
```

#### 3. Zone 分布统计

**位置**: `core/luminance_service.py:122` - `calculate_zone_distribution()`

**当前实现**: 遍历全图计算明度分布

**优化思路**:
```python
# 1. 全图转NumPy数组
img_array = qimage_to_numpy(image)

# 2. 采样
sampled = img_array[::sample_step, ::sample_step]

# 3. 向量化明度计算
luminance = (0.299 * sampled[:, :, 0] + 
             0.587 * sampled[:, :, 1] + 
             0.114 * sampled[:, :, 2]).astype(np.uint8)

# 4. 向量化Zone统计
zone_indices = luminance // 32
zone_indices = np.clip(zone_indices, 0, 7)
unique, counts = np.unique(zone_indices, return_counts=True)
```

### 中优先级

#### 4. 色相直方图

**位置**: `core/histogram_service.py:133` - `HueHistogramCalculator`

**当前实现**: 已在后台线程，但使用逐像素遍历

**优化思路**: 同直方图计算优化，使用NumPy向量化HSV转换和统计

### 低优先级 (采样点少，优化价值有限)

#### 5. 边缘采样

**位置**: 
- `core/color.py:444-463`
- `core/color.py:539-563`
- `core/color.py:1292-1301`

**说明**: 仅采样边缘少量像素，优化收益不大

## 优化原则

1. **延迟优化**: 只有出现性能瓶颈时才优化
2. **测量优先**: 先用性能测试确认瓶颈位置
3. **保持简单**: 如果当前实现足够快，不要过度优化
4. **注意内存**: NumPy数组会占用较多内存，大图片注意分块处理

## 参考实现

### RGB 转 HSV (向量化)

```python
def rgb_to_hsv_vectorized(r, g, b):
    """向量化RGB转HSV"""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    
    max_val = np.maximum(np.maximum(r, g), b)
    min_val = np.minimum(np.minimum(r, g), b)
    diff = max_val - min_val
    
    # 计算H
    h = np.zeros_like(r)
    mask = diff != 0
    
    # R is max
    mask_r = mask & (max_val == r)
    h[mask_r] = (60 * ((g[mask_r] - b[mask_r]) / diff[mask_r]) + 360) % 360
    
    # G is max
    mask_g = mask & (max_val == g)
    h[mask_g] = (60 * ((b[mask_g] - r[mask_g]) / diff[mask_g]) + 120) % 360
    
    # B is max
    mask_b = mask & (max_val == b)
    h[mask_b] = (60 * ((r[mask_b] - g[mask_b]) / diff[mask_b]) + 240) % 360
    
    # 计算S
    s = np.zeros_like(r)
    s[max_val != 0] = diff[max_val != 0] / max_val[max_val != 0]
    
    # 计算V
    v = max_val
    
    return h, s, v
```

## 直方图采样设置方案

### 需求背景

全采样虽然精度更高，但在大图片上性能下降明显。实际测试表明，采样模式对直方图精度的提升有限，而速度下降较多。因此计划在设置中提供采样模式选项。

### 设计方案

#### 1. 设置项

**位置**: `ui/settings.py` - 在「直方图」分组下添加

**配置键**: `settings.histogram_sampling_mode`

**选项**:
- `fast` - 快速模式（默认）: 使用动态采样步长
- `fine` - 精细模式: 使用全采样(sample_step=1)

#### 2. UI 实现

使用 `ComboBoxSettingCard` 提供下拉选择:

```python
self.histogram_sampling_card = self._create_combo_card(
    FluentIcon.SPEED,
    tr('settings.histogram_sampling'),
    tr('settings.histogram_sampling_desc'),
    [
        ('fast', tr('settings.histogram_sampling_fast')),
        ('fine', tr('settings.histogram_sampling_fine'))
    ],
    self._histogram_sampling_mode,
    self._on_histogram_sampling_changed
)
```

#### 3. 信号与配置

**新增信号**:
```python
histogram_sampling_mode_changed = Signal(str)
```

**初始化**:
```python
self._histogram_sampling_mode = self._config_manager.get('settings.histogram_sampling_mode', 'fast')
```

**变更处理**:
```python
def _on_histogram_sampling_changed(self, value):
    self._histogram_sampling_mode = value
    self._config_manager.set('settings.histogram_sampling_mode', value)
    self.histogram_sampling_mode_changed.emit(value)
```

#### 4. histogram_service 修改

`_get_sample_step()` 方法需要根据设置返回不同采样策略:

```python
def _get_sample_step(self, image: QImage, mode: str = "fast") -> int:
    """根据图片大小和采样模式确定采样步长

    Args:
        image: QImage 对象
        mode: 采样模式 ('fast' 或 'fine')

    Returns:
        int: 采样步长
    """
    if mode == "fine":
        return 1

    # 快速模式：根据图片大小动态调整
    width = image.width()
    height = image.height()
    pixel_count = width * height

    if pixel_count > 20000000:  # > 20MP
        return 6
    elif pixel_count > 8000000:  # > 8MP
        return 5
    elif pixel_count > 4000000:  # > 4MP
        return 4
    elif pixel_count > 1000000:  # > 1MP
        return 3
    else:
        return 2
```

#### 5. 语言包条目

**en_US.toml**:
```toml
settings.histogram_sampling = "Histogram Sampling"
settings.histogram_sampling_desc = "Choose between fast or fine sampling for histogram calculation"
settings.histogram_sampling_fast = "Fast"
settings.histogram_sampling_fine = "Fine"
```

**ZW_JT.toml**:
```toml
settings.histogram_sampling = "直方圖採樣"
settings.histogram_sampling_desc = "選擇直方圖計算的採樣模式"
settings.histogram_sampling_fast = "快速"
settings.histogram_sampling_fine = "精細"
```

**ZW_FT.toml**:
```toml
settings.histogram_sampling = "直方图采样"
settings.histogram_sampling_desc = "选择直方图计算的采样模式"
settings.histogram_sampling_fast = "快速"
settings.histogram_sampling_fine = "精细"
```

**JA_JP.toml**:
```toml
settings.histogram_sampling = "ヒストグラムサンプリング"
settings.histogram_sampling_desc = "ヒストグラム計算のサンプリングモードを選択"
settings.histogram_sampling_fast = "高速"
settings.histogram_sampling_fine = "高精細"
```

### 实施步骤

1. **添加设置项**: 在 `settings.py` 中添加 UI 和信号
2. **修改 histogram_service**: 支持根据设置选择采样模式
3. **更新语言包**: 添加所有语言的翻译条目
4. **测试验证**: 对比两种模式的速度和精度差异

## 注意事项

1. **行对齐**: QImage 可能有行对齐，使用 `bytesPerLine()` 处理
2. **内存复制**: `np.array(ptr)` 后需要 `.copy()` 避免内存问题
3. **异常处理**: 保持原有异常处理逻辑，确保失败时回退到安全实现