#!/usr/bin/env bash
set -e

echo "===================================================="
echo " LiteWin - Windows, without the baggage."
echo " Linux Native Launcher"
echo "===================================================="
echo ""

# 1. Check if python3 is installed
if ! command -v python3 &>/dev/null; then
    echo "[LiteWin] Python 3 is not installed. Attempting automatic installation..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-tk
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-pip python3-tkinter
    elif command -v pacman &>/dev/null; then
        sudo pacman -Sy --noconfirm python python-pip tk
    else
        echo "[LiteWin] Error: Package manager not recognized. Please install Python 3."
        exit 1
    fi
fi

# 2. Check and ensure supporting tools (7zz, xorriso, wimtools)
mkdir -p "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"

if ! command -v 7zz &>/dev/null && ! command -v 7z &>/dev/null; then
    echo "[LiteWin] Downloading 7-Zip standalone binary..."
    curl -sL https://www.7-zip.org/a/7z2301-linux-x64.tar.xz | tar -xJ -C "$HOME/.local/bin" 7zz
    chmod +x "$HOME/.local/bin/7zz"
fi

# 3. Install LiteWin in user / local environment
echo "[LiteWin] Ensuring dependencies are installed..."
python3 -m pip install -e . --quiet --break-system-packages 2>/dev/null || python3 -m pip install -e . --quiet

# 4. Launch LiteWin GUI
echo "[LiteWin] Launching LiteWin GUI..."
exec python3 -m litewin.cli gui "$@"
