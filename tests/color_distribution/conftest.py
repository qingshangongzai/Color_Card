"""色彩分布分析测试共享工具

图片 golden 用例的加载辅助：主程序运行时由图片加载层完成 ICC→sRGB 归一，
测试侧用本模块等价复现（引擎本身不做 ICC，见 core/color_distribution.py）。
"""

import io
import os

import numpy as np
from PIL import Image, ImageCms

# 项目根目录（验证集素材相对此路径）
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def materials_missing(*dirs: str) -> bool:
    """验证集素材目录是否缺失（不随仓库分发，其他机器整模块跳过）"""
    return not all(os.path.isdir(os.path.join(ROOT, d)) for d in dirs)


def load_image_rgb(path: str) -> np.ndarray:
    """加载图片并做 ICC→sRGB 归一，返回 (H, W, 3) uint8"""
    with Image.open(path) as img:
        img.load()
        icc_data = img.info.get('icc_profile')
        if icc_data:
            try:
                srgb_profile = ImageCms.createProfile('sRGB')
                source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_data))
                converted = ImageCms.profileToProfile(
                    img,
                    inputProfile=source_profile,
                    outputProfile=srgb_profile,
                    outputMode='RGB',
                )
                if converted is not None:
                    img = converted
            except ImageCms.PyCMSError:
                # ICC 转换失败时退化为直接模式转换，不影响后续统计
                pass
        return np.asarray(img.convert('RGB'), dtype=np.uint8)
