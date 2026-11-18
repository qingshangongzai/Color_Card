"""从矢量源重新生成 logo 位图与图标资源

以 logo/Color Card_logo.svg 为唯一源，生成：
- logo/Color Card_logo.png  1024×1024 透明底主图（官网、文档、关于页共用）
- logo/Color Card_logo.ico  Windows 图标，10 档尺寸（16～256），全部 PNG 编码
- logo/ColorCard.icns       macOS 图标，8 个标准槽位（16pt@2x～512pt@2x）

外框圆角是 G3 连续曲率的超椭圆（见 SVG 内注释），改 SVG 后重跑本脚本即可，
不要手工替换位图，否则圆角与主图会不一致。

运行方式：
    python scripts/build_logo_assets.py
    python scripts/build_logo_assets.py --check   # 只校验现有产物尺寸结构，不重写
"""

# 标准库导入
import argparse
import os
import struct
import sys
from pathlib import Path

# 离屏渲染：本脚本不弹窗，固定用 offscreen 平台
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 第三方库导入
from PySide6.QtCore import QBuffer, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_DIR = PROJECT_ROOT / "logo"
SVG_PATH = LOGO_DIR / "Color Card_logo.svg"
PNG_PATH = LOGO_DIR / "Color Card_logo.png"
ICO_PATH = LOGO_DIR / "Color Card_logo.ico"
ICNS_PATH = LOGO_DIR / "ColorCard.icns"

PNG_SIZE = 1024
ICO_SIZES = (16, 24, 32, 48, 64, 72, 96, 128, 192, 256)
# (ICNS 槽位, 像素边长)；同一尺寸在标准槽位里出现两次，共用同一份 PNG
ICNS_SLOTS = (("ic11", 32), ("ic12", 64), ("ic07", 128), ("ic13", 256),
              ("ic08", 256), ("ic14", 512), ("ic09", 512), ("ic10", 1024))
# 主图的同名副本：官网部署目录与官网开发目录
COPY_TARGETS = (PROJECT_ROOT / "docs" / "logo.png", PROJECT_ROOT / "website" / "public" / "logo.png")

_APP: QGuiApplication | None = None


def render_svg(renderer: QSvgRenderer, size: int) -> QImage:
    """把矢量按目标像素边长等比渲染成透明底 ARGB 图像"""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image.convertToFormat(QImage.Format.Format_ARGB32)


def encode_png(image: QImage) -> bytes:
    """QImage -> PNG 字节"""
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    # PySide6 的类型标注把 format 写成 bytes，运行时只接受 str，故此处忽略该告警
    if not image.save(buffer, "PNG"):  # type: ignore[call-overload]
        raise RuntimeError("PNG 编码失败")
    data = bytes(buffer.data().data())
    buffer.close()
    return data


def build_ico(frames: list[tuple[int, bytes]]) -> bytes:
    """按 ICO 格式打包，所有档位都用 PNG 负载（Windows Vista 起支持）"""
    header = struct.pack("<HHH", 0, 1, len(frames))
    offset = len(header) + 16 * len(frames)
    entries = b""
    payload = b""
    for size, data in frames:
        # 256 用 0 表示，其余写实际边长
        side = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(data), offset)
        payload += data
        offset += len(data)
    return header + entries + payload


def build_icns(chunks: list[tuple[str, bytes]]) -> bytes:
    """按 ICNS 格式打包，每个槽位内嵌 PNG"""
    body = b""
    for slot, data in chunks:
        body += struct.pack(">4sI", slot.encode("ascii"), len(data) + 8) + data
    return struct.pack(">4sI", b"icns", len(body) + 8) + body


def inspect_ico(path: Path) -> list[tuple[int, int]]:
    """读回 ICO 目录，返回 [(边长, 负载字节数)]"""
    raw = path.read_bytes()
    count = struct.unpack("<H", raw[4:6])[0]
    result = []
    for index in range(count):
        entry = raw[6 + 16 * index: 22 + 16 * index]
        side, _side2, _colors, _res, _planes, _bpp, size, _offset = struct.unpack("<BBBBHHII", entry)
        result.append((side or 256, size))
    return result


def inspect_icns(path: Path) -> list[tuple[str, int]]:
    """读回 ICNS 槽位，返回 [(槽位, 负载字节数)]"""
    raw = path.read_bytes()
    cursor = 8
    result = []
    while cursor + 8 <= len(raw):
        slot, length = struct.unpack(">4sI", raw[cursor: cursor + 8])
        result.append((slot.decode("ascii"), length - 8))
        cursor += length
    return result


def write_assets(renderer: QSvgRenderer) -> None:
    """渲染并写出三份产物"""
    png_data = encode_png(render_svg(renderer, PNG_SIZE))
    PNG_PATH.write_bytes(png_data)
    for target in COPY_TARGETS:
        if target.exists():
            target.write_bytes(png_data)
            print(f"同步 {target.relative_to(PROJECT_ROOT)}")

    ico_frames = [(size, encode_png(render_svg(renderer, size))) for size in ICO_SIZES]
    ICO_PATH.write_bytes(build_ico(ico_frames))

    cache: dict[int, bytes] = {}
    icns_chunks = []
    for slot, size in ICNS_SLOTS:
        if size not in cache:
            cache[size] = encode_png(render_svg(renderer, size))
        icns_chunks.append((slot, cache[size]))
    ICNS_PATH.write_bytes(build_icns(icns_chunks))

    print(f"PNG  {PNG_PATH.name}: {PNG_SIZE}x{PNG_SIZE}, {len(png_data)} bytes")
    print(f"ICO  {ICO_PATH.name}: {len(ICO_SIZES)} 档 {', '.join(map(str, ICO_SIZES))}, {ICO_PATH.stat().st_size} bytes")
    slots = ", ".join(f"{slot}={size}" for slot, size in ICNS_SLOTS)
    print(f"ICNS {ICNS_PATH.name}: {len(ICNS_SLOTS)} 槽 {slots}, {ICNS_PATH.stat().st_size} bytes")


def check_assets() -> int:
    """校验现有产物的结构，不重写文件"""
    ok = True
    sizes = inspect_ico(ICO_PATH)
    got = [size for size, _ in sizes]
    if got != list(ICO_SIZES):
        print(f"ICO 尺寸不符: {got}")
        ok = False
    else:
        print(f"ICO 尺寸正确: {got}")

    slots = inspect_icns(ICNS_PATH)
    got_slots = [slot for slot, _ in slots]
    if got_slots != [slot for slot, _ in ICNS_SLOTS]:
        print(f"ICNS 槽位不符: {got_slots}")
        ok = False
    else:
        print(f"ICNS 槽位正确: {got_slots}")

    raw_png = PNG_PATH.read_bytes()
    width, height = struct.unpack(">II", raw_png[16:24])
    if (width, height) != (PNG_SIZE, PNG_SIZE):
        print(f"PNG 尺寸不符: {width}x{height}")
        ok = False
    else:
        print(f"PNG 尺寸正确: {width}x{height}")
    return 0 if ok else 1


def main() -> int:
    global _APP
    parser = argparse.ArgumentParser(description="从 SVG 源生成 logo 位图与图标资源")
    parser.add_argument("--check", action="store_true", help="只校验现有产物结构，不重写")
    args = parser.parse_args()

    # 持有实例引用，避免渲染过程中被回收
    _APP = QGuiApplication([sys.argv[0]])
    if args.check:
        return check_assets()

    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        print(f"SVG 无法解析: {SVG_PATH}")
        return 1
    write_assets(renderer)
    return check_assets()


if __name__ == "__main__":
    sys.exit(main())
