# Companion Integration Guide

## Overview

PanaPiTouch now supports **hybrid control** integration with Bitfocus Companion, giving you the best of both worlds:

- **Fast direct HTTP control** for touchscreen operations
- **Companion API integration** for Stream Deck button synchronization
- **Automatic fallback** from direct to Companion control if needed

## Control Modes

### 1. Direct Mode (Fastest)
- All commands sent directly to cameras via HTTP/CGI
- No Companion dependency
- Lowest latency for touchscreen controls
- **Use when**: You don't need Stream Deck synchronization

### 2. Companion Mode
- All commands routed through Companion module
- Camera controls triggered by pressing Companion buttons via HTTP API
- Stream Deck LEDs automatically sync
- **Use when**: You want complete Stream Deck integration

### 3. Hybrid Mode (Recommended)
- Commands sent directly to camera (fast)
- Companion buttons also triggered (for Stream Deck sync)
- Falls back to Companion if direct control fails
- **Use when**: You want both fast touchscreen control AND Stream Deck sync

## Configuration

### Settings

Add to your `~/.config/panapitouch/settings.yaml`:

```yaml
# Companion integration
companion_url: "http://localhost:8000"
companion_enabled: true
companion_control_mode: "hybrid"  # "direct", "companion", or "hybrid"
companion_page: 1  # Companion page number for camera controls
```

### API Endpoints Used

The integration uses these Companion HTTP API endpoints:

**New Format (Companion v3+):**
- Press button: `POST /api/location/{page}/{row}/{column}/press`
- Get style: `GET /api/location/{page}/{row}/{column}/style`

**Legacy Format (Companion v2):**
- Press button: `POST /press/bank/{page}/{bank}`

## Usage Example

### Basic Setup

```python
from src.companion import CompanionAPI, CompanionControlMode
from src.camera.panasonic import PanasonicCamera

# Initialize Companion API
companion = CompanionAPI(base_url="http://localhost:8000")

# Check if Companion is available
if companion.check_availability():
    print("Companion is running!")
else:
    print("Companion not available - using direct control only")

# Create camera with Companion integration
camera = PanasonicCamera(
    camera_id=1,
    name="Camera 1",
    ip_address="192.168.1.100",
    companion_api=companion,
    companion_control_mode="hybrid",  # Use hybrid mode
    companion_page=1  # Companion page for this camera
)

# Recall preset - automatically uses hybrid control
camera.recall_preset(1)  # Fast direct + Companion sync
```

### Manual Button Mapping

Map specific actions to Companion button locations:

```python
# Map preset recalls to Companion buttons
# Assuming presets 1-10 are on row 1, columns 1-10
for preset_num in range(1, 11):
    action = f"preset_{preset_num}"
    camera.hybrid_control.map_action_to_button(
        action=action,
        row=1,
        column=preset_num
    )

# Now when you recall a preset, the corresponding Companion button is also triggered
camera.recall_preset(5)  # Triggers button at page 1, row 1, column 5
```

### Changing Control Mode at Runtime

```python
from src.companion import CompanionControlMode

# Switch to direct-only mode (disable Companion sync)
camera.hybrid_control.set_mode(CompanionControlMode.DIRECT)

# Switch back to hybrid
camera.hybrid_control.set_mode(CompanionControlMode.HYBRID)

# Switch to Companion-only mode
camera.hybrid_control.set_mode(CompanionControlMode.COMPANION)
```

### Trigger Companion Buttons Directly

```python
from src.companion import CompanionButton

# Press a specific button
button = CompanionButton(page=1, row=2, column=3)
companion.press_button(button)

# Or use coordinates directly
companion.press_button_by_coords(page=1, row=2, column=3)

# Legacy bank numbering (for Companion v2 compatibility)
companion.press_button_legacy(page=1, bank=15)
```

### Query Button State

```python
button = CompanionButton(page=1, row=1, column=1)
style = companion.get_button_style(button)

if style:
    print(f"Button text: {style.get('text')}")
    print(f"Button color: {style.get('color')}")
    print(f"Background: {style.get('bgcolor')}")
```

## Companion Button Layout

### Recommended Layout for Panasonic Cameras

**Page 1 - Camera 1 Controls:**

| Row/Col | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|---|---|---|---|---|---|---|---|
| **1** | Preset 1 | Preset 2 | Preset 3 | Preset 4 | Preset 5 | Preset 6 | Preset 7 | Preset 8 |
| **2** | Preset 9 | Preset 10 | Iris Auto | Iris Manual | Gain Auto | Gain Manual | Shutter Auto | Shutter Manual |
| **3** | WB Auto | WB Indoor | WB Outdoor | WB Manual | Gamma Std | Gamma Cinema | ND Filter 1 | ND Filter 2 |

### Button Mapping Configuration

Create a mapping file `~/.config/panapitouch/companion_buttons.json`:

```json
{
  "camera_1": {
    "page": 1,
    "buttons": {
      "preset_1": {"row": 1, "column": 1},
      "preset_2": {"row": 1, "column": 2},
      "preset_3": {"row": 1, "column": 3},
      "preset_4": {"row": 1, "column": 4},
      "preset_5": {"row": 1, "column": 5},
      "preset_6": {"row": 1, "column": 6},
      "preset_7": {"row": 1, "column": 7},
      "preset_8": {"row": 1, "column": 8},
      "preset_9": {"row": 2, "column": 1},
      "preset_10": {"row": 2, "column": 2},
      "iris_auto": {"row": 2, "column": 3},
      "iris_manual": {"row": 2, "column": 4},
      "gain_auto": {"row": 2, "column": 5},
      "wb_auto": {"row": 3, "column": 1},
      "wb_indoor": {"row": 3, "column": 2},
      "wb_outdoor": {"row": 3, "column": 3}
    }
  }
}
```

## Troubleshooting

### Companion Not Detected

```python
companion = CompanionAPI("http://localhost:8000")
if not companion.check_availability():
    print("Companion not running or not accessible")
    print("Check:")
    print("  1. Companion service is running")
    print("  2. Listening on port 8000")
    print("  3. No firewall blocking access")
```

**Solutions:**
- Verify Companion is running: `systemctl status companion`
- Check Companion web interface: `http://localhost:8000`
- Try alternative port if configured differently
- Ensure no firewall rules blocking localhost connections

### Button Presses Not Working

```python
# Try legacy API format
success = companion.press_button_legacy(page=1, bank=1)
if success:
    print("Legacy API works - you may be using Companion v2")
else:
    print("Button press failed - check Companion logs")
```

**Solutions:**
- Check Companion version (v2 vs v3+ API differences)
- Verify button exists at that location in Companion
- Check Companion logs for errors
- Ensure button is configured with actions

### Stream Deck Not Syncing

1. **Verify button mapping** matches your Companion layout
2. **Enable hybrid mode** instead of direct mode
3. **Check Companion connection** is configured for Stream Deck
4. **Test button manually** in Companion interface first

## Performance Considerations

### Latency Comparison

| Mode | Average Latency | Use Case |
|------|----------------|----------|
| **Direct** | 10-20ms | Fastest, no sync |
| **Hybrid** | 15-25ms | Fast + sync (recommended) |
| **Companion** | 30-50ms | Full Companion control |

### Optimization Tips

1. **Use Hybrid Mode by default** - best balance of speed and sync
2. **Map only frequently-used buttons** - reduces overhead
3. **Use Direct Mode for joystick control** - PTZ movements need low latency
4. **Keep Companion on same machine** - avoid network latency

## Integration with PanaPiTouch UI

The settings page now includes Companion integration options:

1. **Enable/Disable Companion Integration**
2. **Select Control Mode** (Direct/Companion/Hybrid)
3. **Set Companion URL** (default: http://localhost:8000)
4. **Configure Companion Page** for each camera
5. **Test Connection** button to verify Companion is running

## API Reference

### CompanionAPI

```python
class CompanionAPI:
    def __init__(self, base_url: str = "http://localhost:8000")
    def check_availability(self) -> bool
    def press_button(self, button: CompanionButton, use_legacy: bool = False) -> bool
    def press_button_by_coords(self, page: int, row: int, column: int) -> bool
    def press_button_legacy(self, page: int, bank: int) -> bool
    def get_button_style(self, button: CompanionButton) -> Optional[Dict]
    def set_button_text(self, button: CompanionButton, text: str) -> bool
```

### HybridCameraControl

```python
class HybridCameraControl:
    def __init__(self, camera_http_sender, companion_api, mode, companion_page)
    def set_mode(self, mode: CompanionControlMode)
    def map_action_to_button(self, action: str, row: int, column: int)
    def execute_action(self, action: str, camera_command: str) -> Tuple[bool, str]
    def recall_preset(self, preset_num: int) -> Tuple[bool, str]
```

### CompanionControlMode

```python
class CompanionControlMode(Enum):
    DIRECT = "direct"      # Direct HTTP to camera only
    COMPANION = "companion"  # Via Companion only
    HYBRID = "hybrid"      # Direct + Companion sync
```

## Sources

- [Bitfocus Companion](https://bitfocus.io/companion)
- [Satellite API Documentation](https://github.com/bitfocus/companion/wiki/Satellite-API)
- [Companion Module Base](https://bitfocus.github.io/companion-module-base/)
- [Panasonic Camera Controller Module](https://github.com/bitfocus/companion-module-panasonic-cameras)

## Future Enhancements

Potential future additions to Companion integration:

1. **Bi-directional sync** - Update PanaPiTouch UI when Stream Deck buttons are pressed
2. **Automatic button discovery** - Scan Companion config and auto-map buttons
3. **Preset thumbnail sync** - Share preset thumbnails with Companion buttons
4. **WebSocket connection** - Real-time state updates instead of HTTP polling
5. **Multi-camera layouts** - Automatic page switching in Companion when changing cameras
