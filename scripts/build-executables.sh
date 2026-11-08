#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

mkdir -p dist

echo "===================================================="
echo " Building LiteWin Standalone Executables"
echo "===================================================="

# 1. Build Linux Standalone Executable with PyInstaller
echo "[*] Building Linux standalone binary (dist/litewin-linux)..."
python3 -m PyInstaller \
    --name litewin-linux \
    --onefile \
    --noconfirm \
    --clean \
    --add-data "data:data" \
    litewin/cli.py

chmod +x dist/litewin-linux
echo "[+] Linux executable built: dist/litewin-linux"

# 2. Build Windows Standalone Executable with MinGW-w64
echo "[*] Building Windows standalone executable (dist/litewin-windows.exe)..."
x86_64-w64-mingw32-gcc -O2 -s launcher/litewin.c -o dist/litewin-windows.exe
echo "[+] Windows executable built: dist/litewin-windows.exe"

echo ""
echo "Build Summary:"
ls -lh dist/litewin-linux dist/litewin-windows.exe
echo "All executables built successfully!"
