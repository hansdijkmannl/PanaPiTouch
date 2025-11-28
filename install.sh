#!/bin/bash
# PanaPiTouch Installation Script

set -e

echo "=========================================="
echo "PanaPiTouch Installation"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run without sudo. The script will ask for sudo when needed."
    exit 1
fi

# Update system
echo "[1/5] Updating system packages..."
sudo apt update

# Install system dependencies
echo "[2/5] Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-cursor0 \
    libegl1 \
    libgles2

# Create virtual environment
echo "[3/5] Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "[4/5] Installing Python dependencies..."
pip install -r requirements.txt

# Make scripts executable
echo "[5/5] Setting permissions..."
chmod +x start.sh
chmod +x main.py

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "To start PanaPiTouch:"
echo "  ./start.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "For auto-start on boot, see README.md"
echo ""

