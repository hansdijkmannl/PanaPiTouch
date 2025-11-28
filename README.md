# PanaPiTouch

A touchscreen application for monitoring Panasonic PTZ cameras with professional video analysis tools.

![PanaPiTouch](https://img.shields.io/badge/Platform-Raspberry%20Pi-red)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

### Camera Monitoring
- **Live Preview**: 1920x1080 preview window for Panasonic PTZ cameras (UE150, HE40, AW-series, etc.)
- **Multi-Camera Support**: Up to 10 cameras with instant switching
- **Network Discovery**: Automatic discovery of Panasonic PTZ cameras on the network (similar to Easy IP)
- **MJPEG Streaming**: Low-latency video streaming from camera web interface

### Video Analysis Overlays
- **False Color**: Exposure analysis with color-coded luminance display
- **Waveform Monitor**: Luminance and RGB parade waveforms
- **Vectorscope**: Chrominance/color vector display
- **Focus Assist**: Focus peaking with edge detection highlighting

### Tally Integration
- **Blackmagic ATEM Support**: Connect to ATEM switchers for tally information
- **Red Tally (Program)**: Red border and button highlight when camera is live
- **Green Tally (Preview)**: Green border and button highlight when camera is in preview
- **Per-Camera Input Mapping**: Map each camera to a specific ATEM input

### Bitfocus Companion Integration
- **Embedded Web View**: Configure Stream Deck XL buttons directly from the app
- **Full Browser Controls**: Navigate the Companion interface with touch

### Touch-Optimized UI
- **Large Touch Targets**: All buttons sized for finger touch (minimum 48px)
- **Dark Theme**: Broadcast monitor-inspired dark interface
- **Page Navigation**: Easy switching between Preview, Companion, and Settings

## Hardware Requirements

- **Display**: Wisecoco 8" 2480x1860 AMOLED (or similar high-resolution touchscreen)
- **Computer**: Raspberry Pi 4/5 (4GB+ RAM recommended)
- **Cameras**: Panasonic PTZ cameras (UE150, UE160, HE40, HE42, AW-UE50, AW-UE100, etc.)
- **Optional**: Blackmagic ATEM switcher for tally
- **Optional**: Elgato Stream Deck XL with Bitfocus Companion

## Installation

### 1. System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-venv python3-pyqt6 \
    python3-opencv libgl1-mesa-glx libglib2.0-0 \
    libxcb-xinerama0 libxkbcommon-x11-0

# For PyQt6 WebEngine
sudo apt install -y python3-pyqt6.qtwebengine
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/PanaPiTouch.git
cd PanaPiTouch
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run Application

```bash
python main.py
```

## Configuration

### Adding Cameras

1. Go to **Settings** page
2. Click **Scan Network** to discover Panasonic cameras automatically
3. Or manually enter camera details:
   - Name: Friendly name for the camera
   - IP Address: Camera's IP address
   - Port: HTTP port (default: 80)
   - Username/Password: Camera credentials (default: admin/admin)
   - ATEM Input: Optional ATEM input number for tally

### ATEM Setup

1. Go to **Settings** page
2. Enter ATEM IP address
3. Click **Test Connection**
4. Save ATEM settings
5. Map cameras to ATEM inputs in the camera settings

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1-9, 0` | Select camera 1-10 |
| `F1` | Toggle False Color |
| `F2` | Toggle Waveform |
| `F3` | Toggle Vectorscope |
| `F4` | Toggle Focus Assist |
| `F11` | Toggle fullscreen |
| `Escape` | Exit fullscreen or quit |

## Auto-Start on Boot

To start PanaPiTouch automatically on boot:

```bash
# Create systemd service
sudo nano /etc/systemd/system/panapitouch.service
```

Add the following content:

```ini
[Unit]
Description=PanaPiTouch Camera Monitor
After=graphical.target

[Service]
Type=simple
User=admin
Environment=DISPLAY=:0
WorkingDirectory=/home/admin/PanaPiTouch
ExecStart=/home/admin/PanaPiTouch/venv/bin/python /home/admin/PanaPiTouch/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```

Enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable panapitouch.service
sudo systemctl start panapitouch.service
```

## Display Configuration

For the Wisecoco 8" 2480x1860 AMOLED display, add to `/boot/config.txt`:

```ini
# HDMI settings for Wisecoco display
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=2480 1860 60 3 0 0 0
max_framebuffer_width=2480
max_framebuffer_height=1860

# Touch screen
dtoverlay=goodix
```

## Troubleshooting

### Camera Not Connecting
- Verify camera IP address and credentials
- Check if camera web interface is accessible in a browser
- Ensure camera and Pi are on the same network
- Try restarting the camera

### ATEM Not Connecting
- Verify ATEM IP address
- Ensure ATEM is on the same network
- Check if another application is connected (only one connection allowed)
- Try power cycling the ATEM

### Display Issues
- For touchscreen calibration issues, run `xinput_calibrator`
- For scaling issues, adjust `QT_AUTO_SCREEN_SCALE_FACTOR`
- For fullscreen issues on EGLFS, set `QT_QPA_PLATFORM=eglfs`

### Performance
- Reduce preview resolution if experiencing lag
- Disable unused overlays
- Ensure adequate cooling for Raspberry Pi

## Project Structure

```
PanaPiTouch/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md
└── src/
    ├── __init__.py
    ├── config/
    │   ├── __init__.py
    │   └── settings.py     # Configuration management
    ├── camera/
    │   ├── __init__.py
    │   ├── discovery.py    # Camera network discovery
    │   └── stream.py       # Camera streaming
    ├── atem/
    │   ├── __init__.py
    │   └── tally.py        # ATEM tally integration
    ├── overlays/
    │   ├── __init__.py
    │   ├── false_color.py  # False color overlay
    │   ├── waveform.py     # Waveform monitor
    │   ├── vectorscope.py  # Vectorscope
    │   └── focus_assist.py # Focus peaking
    └── ui/
        ├── __init__.py
        ├── main_window.py  # Main application window
        ├── preview_widget.py # Video preview widget
        ├── settings_page.py  # Settings configuration
        ├── companion_page.py # Companion web view
        └── styles.py       # UI styling
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Panasonic for excellent PTZ camera APIs
- Blackmagic Design for ATEM protocol
- Bitfocus for Companion
- PyQt6 team for the excellent GUI framework
