#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON:-python3}"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
    "$PYTHON_BIN" -m venv .venv
fi

PYTHON_BIN="$ROOT/.venv/bin/python"
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip uninstall -y meikiocr rapidocr rapidocr-onnxruntime opencv-python opencv-python-headless onnxruntime || true
"$PYTHON_BIN" -m pip install -r requirements.txt -r requirements-build.txt

echo "PP-OCRv5 + PaddleOCR CPU is the only OCR engine used by this build."
echo "Preparing bundled PP-OCRv5 models..."
"$PYTHON_BIN" exp_tracker.py --self-test-ocr

"$PYTHON_BIN" -m PyInstaller --clean --noconfirm packaging/macos-app.spec

APP="$ROOT/dist/MapleStar-EXP-Tracker.app"
DMG="$ROOT/dist/MapleStar-EXP-Tracker.dmg"
STAGE="$ROOT/build/dmg-stage"

rm -f "$DMG"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create \
    -volname "MapleStar EXP Tracker" \
    -srcfolder "$STAGE" \
    -ov \
    -format UDZO \
    "$DMG"

echo ""
echo "Built macOS artifacts:"
echo "  $APP"
echo "  $DMG"
