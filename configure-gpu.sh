#!/bin/bash
#
# PanaPiTouch GPU Memory Configuration
# Increases GPU memory for better video performance
#

set -e

echo "=========================================="
echo "  PanaPiTouch GPU Memory Configuration"
echo "=========================================="
echo ""

# Detect config file location
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    CONFIG_FILE="/boot/config.txt"
else
    echo "Error: Could not find Raspberry Pi config file"
    exit 1
fi

echo "Config file: $CONFIG_FILE"
echo ""

# Check current GPU memory
CURRENT_GPU=$(vcgencmd get_mem gpu 2>/dev/null | cut -d= -f2 || echo "unknown")
echo "Current GPU memory: $CURRENT_GPU"
echo ""

# Recommended GPU memory for video processing
GPU_MEM=256

echo "This script will:"
echo "  1. Set GPU memory to ${GPU_MEM}MB (recommended for video)"
echo "  2. Enable hardware acceleration options"
echo ""
read -p "Continue? [y/N]: " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Backing up config file..."
sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

echo "Updating GPU memory allocation..."

# Remove existing gpu_mem settings
sudo sed -i '/^gpu_mem/d' "$CONFIG_FILE"

# Add new GPU memory setting
echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "# PanaPiTouch GPU settings" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "gpu_mem=${GPU_MEM}" | sudo tee -a "$CONFIG_FILE" > /dev/null

# Enable V4L2 for hardware video decoding (if not already enabled)
if ! grep -q "^start_x=1" "$CONFIG_FILE"; then
    echo "start_x=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
fi

# Enable hardware acceleration for camera
if ! grep -q "^camera_auto_detect" "$CONFIG_FILE"; then
    echo "camera_auto_detect=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
fi

echo ""
echo "=========================================="
echo "  Configuration Complete!"
echo "=========================================="
echo ""
echo "GPU memory set to: ${GPU_MEM}MB"
echo ""
echo "You MUST REBOOT for changes to take effect:"
echo "  sudo reboot"
echo ""


