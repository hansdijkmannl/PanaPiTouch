#!/bin/bash
# Script to simulate 10.5" 16:10 screen on 15.4" 16:9 display
# Creates a 1177x736 (16:10) framebuffer centered on 1920x1080 display
# This matches the physical size of a 10.5" screen on the 15.4" display

CONFIG_FILE="/boot/config.txt"
BACKUP_FILE="/boot/config.txt.backup.$(date +%Y%m%d_%H%M%S)"

echo "Setting up 16:10 aspect ratio simulation..."
echo "Simulating 10.5\" screen on 15.4\" display"
echo "Resolution: 1177x736 (16:10) with black bars on sides"
echo ""

# Backup current config
if [ -f "$CONFIG_FILE" ]; then
    echo "Creating backup: $BACKUP_FILE"
    sudo cp "$CONFIG_FILE" "$BACKUP_FILE"
fi

# Remove existing HDMI/display settings
sudo sed -i '/^hdmi_/d' "$CONFIG_FILE"
sudo sed -i '/^display_/d' "$CONFIG_FILE"
sudo sed -i '/^framebuffer_/d' "$CONFIG_FILE"
sudo sed -i '/^max_framebuffer_/d' "$CONFIG_FILE"
sudo sed -i '/^hdmi_cvt=/d' "$CONFIG_FILE"

# Add settings for 16:10 simulation
echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "# 16:10 Aspect Ratio Simulation (10.5\" on 15.4\" display)" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "# Native display: 1920x1080 (16:9)" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "# Framebuffer: 1177x736 (16:10) - matches 10.5\" physical size" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null

# Set HDMI output to 1920x1080 (native resolution)
echo "hdmi_force_hotplug=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "hdmi_group=2" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "hdmi_mode=82" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "hdmi_drive=2" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null

# Disable overscan to ensure proper centering
echo "# Disable overscan for proper centering" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "disable_overscan=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null

# Set framebuffer to 16:10 aspect (1177x736)
# The framebuffer will be centered on the 1920x1080 display, creating black bars
echo "# Framebuffer settings for 16:10 aspect (simulated 10.5\" screen)" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "framebuffer_width=1177" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "framebuffer_height=736" | sudo tee -a "$CONFIG_FILE" > /dev/null

echo ""
echo "=========================================="
echo "  Configuration Complete!"
echo "=========================================="
echo ""
echo "Display: 1920x1080 (16:9) - native"
echo "Framebuffer: 1177x736 (16:10) - simulated 10.5\" screen"
echo "Black bars: 371px on each side"
echo ""
echo "A reboot is required for changes to take effect."
echo ""
read -p "Reboot now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    sudo reboot
else
    echo "Please reboot manually for changes to take effect: sudo reboot"
fi

