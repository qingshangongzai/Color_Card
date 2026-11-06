"""单实例身份与名称的唯一定义，应用与 C 启动器共用"""

# 标准库导入
import sys
from pathlib import Path

# 项目模块导入
from app_mode import get_config_dir

LOCK_NAME_PREFIX = "single_instance_"
SERVER_NAME_PREFIX = "color_card_"
_FNV_OFFSET = 0xcbf29ce484222325
_FNV_PRIME = 0x100000001b3
_UINT64_MASK = 0xFFFFFFFFFFFFFFFF
_ASCII_LOWER_TABLE = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
)


def _normalize_path(text: str) -> str:
    """仅折叠 ASCII 大写，保证与 C 启动器逐字节一致

    启动器同样只处理 ASCII，避免 CharLowerBuffW 的区域设置差异
    与 Python 的 Unicode 大小写映射产生不同实例键。

    Args:
        text: 原始路径文本

    Returns:
        str: 仅 ASCII 大写转小写的路径文本
    """
    return text.translate(_ASCII_LOWER_TABLE)


def compute_instance_key(program_root: Path) -> str:
    """计算单实例身份

    输入是「仅 ASCII 大写折叠后的程序目录」的 UTF-8 字节，C 启动器按同一规则计算，
    两端必须一致。

    Args:
        program_root: 程序所在目录

    Returns:
        str: 16 位十六进制的 FNV-1a 64 哈希
    """
    value = _FNV_OFFSET
    for byte in _normalize_path(str(program_root)).encode("utf-8"):
        value = ((value ^ byte) * _FNV_PRIME) & _UINT64_MASK
    return f"{value:016x}"


def get_key_dir() -> Path:
    """获取锁文件目录

    macOS 的配置目录落在 bundle 内，会随拷贝/升级漂移，锁文件固定放用户目录。

    Returns:
        Path: 锁文件所在目录
    """
    if sys.platform == "darwin":
        return Path.home() / ".color_card"
    return get_config_dir()


def get_lock_path(instance_key: str) -> Path:
    """获取锁文件路径

    Args:
        instance_key: 单实例身份

    Returns:
        Path: 锁文件完整路径
    """
    return get_key_dir() / f"{LOCK_NAME_PREFIX}{instance_key}.lock"


def get_server_name(instance_key: str) -> str:
    """获取本地服务名称

    Args:
        instance_key: 单实例身份

    Returns:
        str: QLocalServer 名称
    """
    return f"{SERVER_NAME_PREFIX}{instance_key}"
