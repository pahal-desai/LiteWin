#!/usr/bin/env bash
set -e

# Always resolve repository root directory regardless of where script is called from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

echo "===================================================="
echo " LiteWin - Windows, without the baggage."
echo " Linux Native Launcher"
echo "===================================================="
echo ""

# 1. Check if python3 is installed
if ! command -v python3 &>/dev/null; then
    echo "[LiteWin] Python 3 is not installed. Attempting automatic installation..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv python3-tk
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

# 3. Create and activate a dedicated virtual environment (.venv)
VENV_DIR="$ROOT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[LiteWin] Creating dedicated virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "[LiteWin] Activating virtual environment..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# 4. Ensure dependencies and package are installed in venv
echo "[LiteWin] Ensuring dependencies are installed..."
pip install -e . --quiet

# 5. Launch LiteWin GUI
echo "[LiteWin] Launching LiteWin GUI..."
exec python -m litewin.cli gui "$@"
