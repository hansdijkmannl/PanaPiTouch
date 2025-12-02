#!/bin/bash
# Script to set Raspberry Pi OS resolution to 1920x1080

CONFIG_FILE="/boot/config.txt"
BACKUP_FILE="/boot/config.txt.backup.$(date +%Y%m%d_%H%M%S)"

echo "Setting Raspberry Pi OS resolution to 1920x1080..."

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

# Add 1920x1080 settings
echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "# 1920x1080 Resolution Settings" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "hdmi_force_hotplug=1" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "hdmi_group=2" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "hdmi_mode=82" | sudo tee -a "$CONFIG_FILE" > /dev/null
echo "hdmi_drive=2" | sudo tee -a "$CONFIG_FILE" > /dev/null

echo ""
echo "Resolution set to 1920x1080!"
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



