#!/bin/bash
# Image Navigator - Mac .app 빌드 스크립트
#
# 사용법:
#   cd sam3/image_navigator
#   bash build.sh
#
# 결과:
#   dist/ImageNavigator.app  (Mac 앱 번들)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Image Navigator Build ==="
echo ""

# 의존성 확인
if ! python3 -c "import PySide6" 2>/dev/null; then
    echo "[*] PySide6 not found. Installing dependencies..."
    pip3 install -r requirements.txt
fi

if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "[*] PyInstaller not found. Installing..."
    pip3 install pyinstaller
fi

echo "[*] Building ImageNavigator..."

pyinstaller \
    --noconfirm \
    --clean \
    --windowed \
    --onedir \
    --name "ImageNavigator" \
    --add-data "canvas.py:." \
    main.py

echo ""
echo "=== Build Complete ==="
echo "App location: $SCRIPT_DIR/dist/ImageNavigator.app"
echo ""
echo "To run:"
echo "  open dist/ImageNavigator.app"
echo ""
echo "To copy to /Applications:"
echo "  cp -r dist/ImageNavigator.app /Applications/"
