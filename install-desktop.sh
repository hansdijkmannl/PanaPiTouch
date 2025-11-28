#!/bin/bash
#
# PanaPiTouch Desktop & Autostart Installer
# This script installs the desktop icon and autostart service
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME=$(whoami)
DESKTOP_DIR="$HOME/Desktop"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "=========================================="
echo "  PanaPiTouch Desktop & Autostart Setup"
echo "=========================================="
echo ""

# Create Desktop directory if it doesn't exist
mkdir -p "$DESKTOP_DIR"
mkdir -p "$AUTOSTART_DIR"

# Copy desktop file to Desktop
echo "[1/4] Installing desktop shortcut..."
cp "$SCRIPT_DIR/panapitouch.desktop" "$DESKTOP_DIR/panapitouch.desktop"
chmod +x "$DESKTOP_DIR/panapitouch.desktop"

# Mark as trusted (for some desktop environments)
if command -v gio &> /dev/null; then
    gio set "$DESKTOP_DIR/panapitouch.desktop" metadata::trusted true 2>/dev/null || true
fi

echo "      ✓ Desktop shortcut installed"

# Copy to applications menu
echo "[2/4] Installing to applications menu..."
mkdir -p "$HOME/.local/share/applications"
cp "$SCRIPT_DIR/panapitouch.desktop" "$HOME/.local/share/applications/panapitouch.desktop"
echo "      ✓ Applications menu entry installed"

# Setup autostart (user session)
echo "[3/4] Setting up autostart..."
cp "$SCRIPT_DIR/panapitouch.desktop" "$AUTOSTART_DIR/panapitouch.desktop"
echo "      ✓ Autostart enabled (user session)"

# Ask about systemd service
echo "[4/4] Systemd service setup..."
echo ""
echo "Do you want to install the systemd service for autostart?"
echo "This provides more reliable autostart but requires sudo."
echo ""
read -p "Install systemd service? [y/N]: " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing systemd service..."
    sudo cp "$SCRIPT_DIR/panapitouch.service" /etc/systemd/system/panapitouch.service
    sudo systemctl daemon-reload
    sudo systemctl enable panapitouch.service
    echo "      ✓ Systemd service installed and enabled"
    echo ""
    echo "To start the service now, run:"
    echo "  sudo systemctl start panapitouch.service"
    echo ""
    echo "To check status:"
    echo "  sudo systemctl status panapitouch.service"
else
    echo "      → Skipped systemd service installation"
fi

echo ""
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "You can now:"
echo "  • Double-click the PanaPiTouch icon on your desktop"
echo "  • Find PanaPiTouch in the applications menu"
echo "  • The app will autostart on next boot"
echo ""
echo "To manually start the app:"
echo "  cd $SCRIPT_DIR && ./start.sh"
echo ""




