# Camera Controls Submenu Structure Summary

## Option 3: Full Feature Set with Category Submenus

---

## UI Structure Overview

### Bottom Panel Menu Bar (Current + New)
```
┌─────────────────────────────────────────────────────────┐
│  🎮 PTZ  │  ⊞ Grid  │  📐 Guides  │  📺 Multiview  │  ⚙️ Camera Control  │
└─────────────────────────────────────────────────────────┘
```

### When "⚙️ Camera Control" is Selected:

**Level 1: Category Selection (Submenu)**
```
┌─────────────────────────────────────────────────────────┐
│  Bottom Panel Content Area                              │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Category Buttons (Horizontal Menu)              │  │
│  │                                                   │  │
│  │  [1. Exposure] [2. Color] [3. Image] [4. PTZ]  │  │
│  │  [5. Presets] [6. Operations] [7. Advanced]    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Control Panel (Scrollable)                      │  │
│  │  (Shows controls for selected category)          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Detailed Category Breakdown

### **1. EXPOSURE CONTROL**
**Controls shown when "1. Exposure" is selected:**

**Iris (Aperture)**
- [Toggle] Iris Mode: Auto / Manual
- [Slider] Iris Value: F1.6 ──────────────── F16
- [Dropdown] Iris Speed: Fast / Normal / Slow

**Gain**
- [Toggle] Gain Mode: Auto / Manual
- [Slider] Gain Value: -3dB ──────────────── +42dB
- [Slider] Gain Limit: 0dB ──────────────── +42dB

**Shutter Speed**
- [Toggle] Shutter Mode: Auto / Manual
- [Dropdown] Shutter Speed: 1/100, 1/250, 1/500, ... 1/10000
- [Dropdown] Slow Shutter: 1/30, 1/15, ... 1/1.25

**ND Filter**
- [Dropdown] ND Filter: Off / 1/4 / 1/16 / 1/64
- [Toggle] ND Filter Mode: Auto / Manual

**Exposure Compensation**
- [Slider] Exposure Compensation: -2.0 EV ──────────────── +2.0 EV

---

### **2. COLOR & WHITE BALANCE**
**Controls shown when "2. Color" is selected:**

**White Balance**
- [Dropdown] WB Mode: Auto / Indoor / Outdoor / Manual / ATW
- [Slider] Color Temperature: 2000K ──────────────── 15000K
- [Slider] Red Gain: -99 ──────────────── +99
- [Slider] Blue Gain: -99 ──────────────── +99
- [Dropdown] WB Speed: Fast / Normal / Slow

**Color Matrix**
- [Dropdown] Matrix Type: Normal / EBU / NTSC / User
- [Slider] Saturation: -99 ──────────────── +99
- [Slider] Hue: -99 ──────────────── +99

**Gamma**
- [Dropdown] Gamma Mode: Standard / Cinema / Wide / HD / FILMLIKE / ...
- [Dropdown] Gamma Level: Low / Mid / High

**Black Balance**
- [Button] Black Balance: Auto / Manual
- [Slider] Master Black: -99 ──────────────── +99
- [Slider] Red/Blue Black: -99 ──────────────── +99

---

### **3. IMAGE ENHANCEMENT**
**Controls shown when "3. Image" is selected:**

**Detail (Sharpness)**
- [Slider] Detail Level: -99 ──────────────── +99
- [Slider] H/V Ratio: 0 ──────────────── 100
- [Slider] Crispening: 0 ──────────────── 100
- [Slider] Coring: 0 ──────────────── 100

**Knee (Highlight Compression)**
- [Toggle] Knee Mode: Off / Auto / Manual
- [Slider] Knee Point: 70% ──────────────── 105%
- [Slider] Knee Slope: 0 ──────────────── 100

**Noise Reduction**
- [Dropdown] DNR Level: Off / Low / High
- [Toggle] 2D/3D DNR: 2D / 3D
- [Slider] Temporal NR: 0 ──────────────── 100

**Other Enhancements**
- [Slider] White Clip: 100% ──────────────── 109%
- [Slider] Chroma Level: -99 ──────────────── +99
- [Slider] Color Gain R: 0 ──────────────── 100
- [Slider] Color Gain G: 0 ──────────────── 100
- [Slider] Color Gain B: 0 ──────────────── 100

---

### **4. PTZ ADVANCED**
**Controls shown when "4. PTZ" is selected:**

**Pan/Tilt Advanced**
- [Slider] Pan/Tilt Speed: 1 ──────────────── 24
- [Input] Pan Position: [____] (absolute)
- [Input] Tilt Position: [____] (absolute)
- [Button] Set Pan/Tilt Limits
- [Button] Clear Pan/Tilt Limits

**Zoom Advanced**
- [Slider] Zoom Speed: 1 ──────────────── 7
- [Slider] Zoom Position: 0 ──────────────── 16384
- [Label] Zoom Ratio: 1.0x (display only)
- [Toggle] Digital Zoom: Enable / Disable

**Focus Advanced**
- [Toggle] Focus Mode: Auto / Manual
- [Slider] Focus Speed: 1 ──────────────── 7
- [Slider] Focus Position: 0 ──────────────── 16384
- [Dropdown] AF Sensitivity: High / Normal / Low
- [Dropdown] AF Area: Wide / Center / Spot
- [Button] One Push AF (trigger)

---

### **5. PRESETS & SCENE FILES**
**Controls shown when "5. Presets" is selected:**

**PTZ Presets**
- [Grid] Preset Buttons (1-100, scrollable grid)
  - Each button shows: [Preset #] [Name]
  - [Button] Save Current Position to Preset #
  - [Button] Recall Preset #
  - [Input] Preset Name: [___________]
  - [Button] Capture Thumbnail

**Scene Files**
- [Grid] Scene File Buttons (1-6)
  - Each button shows: [Scene #] [Name]
  - [Button] Save Current Settings to Scene #
  - [Button] Recall Scene #
  - [Input] Scene Name: [___________]

---

### **6. CAMERA OPERATIONS**
**Controls shown when "6. Operations" is selected:**

**Recording (if supported)**
- [Button] SD Recording: Start / Stop
- [Dropdown] Recording Format: [Codec options]
- [Dropdown] Recording Quality: [Resolution/Bitrate options]

**Streaming**
- [Toggle] Stream Control: Enable / Disable
- [Dropdown] Stream Resolution: [Options]
- [Slider] Stream Bitrate: [Range]
- [Dropdown] Stream Codec: H.264 / H.265

**Power & Status**
- [Button] Power Control: ON / Standby
- [Button] Query Status (refresh camera info)
- [Label] Firmware Version: [Display]
- [Label] Model Information: [Display]

---

### **7. ADVANCED FEATURES**
**Controls shown when "7. Advanced" is selected:**

**Multi-Matrix**
- [Toggle] Multi-Matrix Mode: Enable / Disable
- [Slider] Multi-Matrix Settings: [Color temp adjustments]

**Shading**
- [Toggle] Shading Mode: Enable / Disable
- [Slider] Shading Adjustment: [Fine-tune range]

**Image Transform**
- [Toggle] Image Flip Horizontal: On / Off
- [Toggle] Image Flip Vertical: On / Off
- [Dropdown] Image Rotation: 0° / 90° / 180° / 270°

**Privacy Masking**
- [Toggle] Privacy Mask: Enable / Disable
- [Input] Mask Position X: [____]
- [Input] Mask Position Y: [____]
- [Input] Mask Width: [____]
- [Input] Mask Height: [____]
- [Button] Add Mask Zone
- [Button] Remove Mask Zone

**Motion Detection**
- [Toggle] Motion Detection: Enable / Disable
- [Slider] Sensitivity: 0 ──────────────── 100
- [Button] Set Detection Area
- [Button] Clear Detection Area

---

## Navigation Flow

1. **User clicks "⚙️ Camera Control"** in bottom menu bar
   → Shows category selection submenu + empty control panel

2. **User clicks a category (1-7)**
   → Category button highlights (orange underline, like other menu buttons)
   → Control panel updates to show that category's controls

3. **User interacts with controls**
   → Values update in real-time
   → Changes sent to camera via HTTP/CGI API

4. **User clicks another category**
   → Previous category unhighlights
   → New category highlights
   → Control panel updates

5. **User clicks another main menu item (PTZ, Grid, etc.)**
   → Camera Control panel hides
   → Selected panel shows

---

## Layout Details

### Category Submenu Bar
- **Height**: 60px (matches bottom menu bar)
- **Style**: Same as bottom menu bar (centered buttons, orange underline on active)
- **Buttons**: 7 category buttons, horizontally arranged
- **Spacing**: Equal spacing between buttons

### Control Panel
- **Container**: Scrollable area (TouchScrollArea)
- **Layout**: Vertical layout with grouped controls
- **Groups**: Each control group in a QGroupBox with title
- **Spacing**: 12px padding, 8px spacing between controls
- **Controls**: Mix of sliders, dropdowns, toggles, buttons, inputs

---

## Visual Example

```
┌─────────────────────────────────────────────────────────────┐
│  Bottom Menu Bar                                            │
│  [PTZ] [Grid] [Guides] [Multiview] [⚙️ Camera Control] ←─│
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  Bottom Panel                                               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Category Submenu                                     │ │
│  │  [1. Exposure] [2. Color] [3. Image] [4. PTZ]       │ │
│  │  [5. Presets] [6. Operations] [7. Advanced]         │ │
│  │  ──────────────────────────────────────────────────── │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Control Panel (Scrollable)                          │ │
│  │                                                       │ │
│  │  ┌─ Iris (Aperture) ─────────────────────────────┐  │ │
│  │  │  Mode: [Auto ▼]  [Manual]                    │  │ │
│  │  │  Value: [F1.6] ──────────────── [F16]        │  │ │
│  │  │  Speed: [Fast ▼]                              │  │ │
│  │  └───────────────────────────────────────────────┘  │ │
│  │                                                       │ │
│  │  ┌─ Gain ────────────────────────────────────────┐  │ │
│  │  │  Mode: [Auto ▼]  [Manual]                    │  │ │
│  │  │  Value: [-3dB] ──────────────── [+42dB]       │  │ │
│  │  │  Limit: [0dB] ──────────────── [+42dB]       │  │ │
│  │  └───────────────────────────────────────────────┘  │ │
│  │                                                       │ │
│  │  ... (more controls scroll down) ...                  │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Notes

- **Category buttons**: Use same styling as bottom menu bar buttons (checkable, exclusive group)
- **Control groups**: Use QGroupBox for visual grouping
- **Scrollable**: Use TouchScrollArea for touch-friendly scrolling
- **API calls**: Each control change triggers HTTP request to camera CGI endpoint
- **State management**: Track current category selection and control values
- **Error handling**: Show toast notifications for API errors
- **Loading states**: Disable controls while API request is in progress

---

## Summary

This structure provides:
- ✅ **Organized navigation**: 7 clear categories
- ✅ **Full feature set**: All controls from Option 3
- ✅ **Consistent UI**: Matches existing bottom menu design
- ✅ **Touch-friendly**: Large buttons, scrollable panels
- ✅ **Scalable**: Easy to add/remove controls per category











