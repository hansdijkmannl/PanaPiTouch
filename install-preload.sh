#!/bin/bash
# Install PanaPiTouch Preload Service
# This service preloads modules at boot time to speed up app startup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/panapitouch-preload.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "Installing PanaPiTouch preload service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Copy service file
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
echo "Copied service file to $SYSTEMD_DIR"

# Reload systemd
systemctl daemon-reload
echo "Reloaded systemd daemon"

# Enable service to start at boot
systemctl enable panapitouch-preload.service
echo "Enabled panapitouch-preload.service"

# Start the service now (don't wait for reboot)
systemctl start panapitouch-preload.service
echo "Started panapitouch-preload.service"

echo ""
echo "Preload service installed successfully!"
echo ""
echo "The service will:"
echo "  - Run at boot time before the main app"
echo "  - Compile all Python modules to bytecode"
echo "  - Preload heavy modules (PyQt6, OpenCV, etc.)"
echo "  - Warm up OS file cache for faster app startup"
echo ""
echo "Check status with: sudo systemctl status panapitouch-preload.service"
echo "View logs with: sudo journalctl -u panapitouch-preload.service -f"


