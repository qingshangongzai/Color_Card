#!/bin/bash

# 创建美观的 macOS DMG 安装包

set -e

# 参数
VERSION="${VERSION:-1.4.1}"
APP_NAME="ColorCard"
DMG_NAME="Color_Card_${VERSION}_mac.dmg"
SOURCE_APP="dist/ColorCard.app"
OUTPUT_DMG="dist/${DMG_NAME}"
TEMP_DIR="dist/dmg_temp"

echo "Creating DMG for ${APP_NAME}..."

# 清理临时目录
rm -rf "${TEMP_DIR}"
mkdir -p "${TEMP_DIR}"

# 复制应用
cp -R "${SOURCE_APP}" "${TEMP_DIR}/"

# 创建 Applications 文件夹快捷方式
ln -s /Applications "${TEMP_DIR}/Applications"

# 创建背景图片目录
mkdir -p "${TEMP_DIR}/.background"

# 创建背景图片
cat > "${TEMP_DIR}/create_background.py" << 'PYTHON'
from PIL import Image, ImageDraw, ImageFont
import os

# 创建背景图片
width, height = 500, 350
img = Image.new('RGB', (width, height), color='#f0f0f0')
draw = ImageDraw.Draw(img)

# 添加文字提示
try:
    # 尝试使用系统字体
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 20)
        font_small = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 14)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 中文提示
    draw.text((width//2, 80), "拖拽应用到 Applications 文件夹", fill='#333333', anchor='mm', font=font_large)
    # 英文提示
    draw.text((width//2, 110), "Drag app to Applications folder", fill='#666666', anchor='mm', font=font_small)
except Exception as e:
    print(f"Text rendering skipped: {e}")

# 保存背景图片
img.save(os.path.join('dist', 'dmg_temp', '.background', 'background.png'))
print("Background image created successfully")
PYTHON

# 运行 Python 脚本创建背景
python3 "${TEMP_DIR}/create_background.py"

# 创建 DMG（临时，可读写）
echo "Creating temporary DMG..."
hdiutil create \
    -srcfolder "${TEMP_DIR}" \
    -volname "ColorCard" \
    -fs HFS+ \
    -format UDRW \
    -size 200m \
    "dist/temp.dmg"

# 挂载 DMG
echo "Mounting DMG..."
MOUNT_INFO=$(hdiutil attach -readwrite -noverify -noautoopen "dist/temp.dmg")
MOUNT_POINT=$(echo "${MOUNT_INFO}" | grep "Apple_HFS" | awk '{print $3}')

if [ -n "${MOUNT_POINT}" ]; then
    echo "Mounted at: ${MOUNT_POINT}"
    
    # 等待挂载完成
    sleep 2
    
    # 使用 AppleScript 设置窗口布局（如果在本地运行）
    if command -v osascript &> /dev/null && [ -n "${CI}" ]; then
        echo "Setting window layout..."
        osascript << EOF
tell application "Finder"
    tell disk "ColorCard"
        open
        delay 2
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set bounds of container window to {100, 100, 600, 450}
        set icon size of icon view options of container window to 128
        set arrangement of icon view options of container window to not arranged
        set position of item "ColorCard.app" to {150, 200}
        set position of item "Applications" to {450, 200}
        close
    end tell
end tell
EOF
    fi
    
    # 卸载 DMG
    echo "Unmounting DMG..."
    hdiutil detach "${MOUNT_POINT}" || hdiutil detach -force "${MOUNT_POINT}"
fi

# 压缩 DMG
echo "Compressing DMG..."
hdiutil convert "dist/temp.dmg" -format UDZO -imagekey zlib-level=9 -o "${OUTPUT_DMG}"

# 清理临时文件
rm -f "dist/temp.dmg"
rm -rf "${TEMP_DIR}"

echo "DMG created successfully: ${OUTPUT_DMG}"
