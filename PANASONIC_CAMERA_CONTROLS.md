# Panasonic PTZ Camera Control Capabilities

## Currently Implemented ✅

### Basic Camera Management
- ✅ Camera Discovery (UDP broadcast)
- ✅ Camera Connection/Streaming (MJPEG, RTSP)
- ✅ Camera Configuration (Name, IP, Port, Username, Password)
- ✅ ATEM Input Mapping
- ✅ Identify Camera (LED blink)

### Video Streaming
- ✅ MJPEG streaming (`/cgi-bin/mjpeg`)
- ✅ RTSP streaming (H.264/H.265)
- ✅ Snapshot capture (`/cgi-bin/camera`)

---

## Available for Implementation 📋

### 1. EXPOSURE CONTROL (`aw_cam` endpoint)

#### Iris (Aperture)
- **Iris Mode**: Auto / Manual
- **Iris Value**: F1.6 to F16 (varies by model)
- **Iris Speed**: Fast / Normal / Slow

#### Gain
- **Gain Mode**: Auto / Manual
- **Gain Value**: -3dB to +42dB (typically)
- **Gain Limit**: Set maximum auto gain

#### Shutter Speed
- **Shutter Mode**: Auto / Manual
- **Shutter Speed**: 1/100, 1/250, 1/500, 1/1000, 1/2000, 1/4000, 1/8000, 1/10000
- **Slow Shutter**: 1/30, 1/25, 1/15, 1/12.5, 1/8, 1/6, 1/4, 1/3, 1/2, 1/1.5, 1/1.25

#### ND Filter
- **ND Filter**: Off / 1/4 / 1/16 / 1/64
- **ND Filter Mode**: Auto / Manual

#### Exposure Compensation
- **Exposure Compensation**: -2.0 to +2.0 EV (in 0.1 steps)

---

### 2. COLOR & WHITE BALANCE (`aw_cam` endpoint)

#### White Balance
- **WB Mode**: Auto / Indoor (3200K) / Outdoor (5600K) / Manual / ATW (Auto Tracking White)
- **Color Temperature**: 2000K to 15000K (manual mode)
- **Red Gain**: -99 to +99
- **Blue Gain**: -99 to +99
- **WB Speed**: Fast / Normal / Slow

#### Color Matrix
- **Matrix Type**: Normal / EBU / NTSC / User
- **User Matrix**: Custom RGB matrix adjustments
- **Saturation**: -99 to +99
- **Hue**: -99 to +99

#### Gamma
- **Gamma Mode**: 
  - Standard modes: Off / Normal / Cinema / Wide
  - Advanced (UE150+): HD / FILMLIKE1 / FILMLIKE2 / FILMLIKE3 / FILM-REC / VIDEO-REC / HLG
- **Gamma Level**: Low / Mid / High (when applicable)

#### Black Balance
- **Black Balance**: Auto / Manual
- **Master Black**: -99 to +99
- **Red Black**: -99 to +99
- **Blue Black**: -99 to +99

---

### 3. IMAGE ENHANCEMENT (`aw_cam` endpoint)

#### Detail (Sharpness)
- **Detail Level**: -99 to +99
- **H/V Ratio**: Horizontal/Vertical detail balance
- **Crispening**: Detail threshold adjustment
- **Coring**: Noise reduction threshold for detail

#### Knee (Highlight Compression)
- **Knee Mode**: Off / Auto / Manual
- **Knee Point**: 70% to 105%
- **Knee Slope**: Adjustable curve

#### Noise Reduction
- **DNR (Digital Noise Reduction)**: Off / Low / High
- **2D/3D DNR**: Separate 2D and 3D noise reduction
- **Temporal NR**: Frame-to-frame noise reduction

#### Other Enhancements
- **White Clip**: 100% to 109%
- **Chroma Level**: -99 to +99
- **Color Gain**: R/G/B individual adjustments

---

### 4. PTZ CONTROL (`aw_ptz` endpoint)

#### Pan/Tilt
- **Pan Speed**: 1-24 (varies by model)
- **Tilt Speed**: 1-20 (varies by model)
- **Pan/Tilt Position**: Absolute position control
- **Pan/Tilt Limits**: Set movement boundaries
- **Pan/Tilt Speed Control**: Variable speed joystick control

#### Zoom
- **Zoom Speed**: 1-7
- **Zoom Position**: Absolute zoom value (0-16384 typically)
- **Zoom Ratio**: Display current zoom ratio
- **Digital Zoom**: Enable/disable digital zoom

#### Focus
- **Focus Mode**: Auto / Manual
- **Focus Speed**: 1-7
- **Focus Position**: Absolute focus value
- **AF Sensitivity**: High / Normal / Low
- **AF Area**: Wide / Center / Spot
- **One Push AF**: Trigger single autofocus

---

### 5. PRESETS & SCENE FILES (`aw_ptz` / `aw_cam` endpoints)

#### PTZ Presets
- **Preset Save**: Save current PTZ position (1-100 presets)
- **Preset Recall**: Recall saved PTZ position
- **Preset Name**: Assign names to presets
- **Preset Thumbnail**: Capture/store thumbnail images

#### Scene Files
- **Scene File Save**: Save all camera settings (1-6 scene files)
- **Scene File Recall**: Recall complete camera configuration
- **Scene File Name**: Assign names to scene files

---

### 6. CAMERA OPERATIONS (`aw_cam` endpoint)

#### Recording (if supported)
- **SD Recording**: Start/Stop SD card recording
- **Recording Format**: Select recording codec/format
- **Recording Quality**: Set recording resolution/bitrate

#### Streaming
- **Stream Control**: Enable/disable individual streams
- **Stream Resolution**: Change stream resolution
- **Stream Bitrate**: Adjust stream bitrate
- **Stream Codec**: Select H.264/H.265

#### Power & Status
- **Power Control**: Power ON / Standby
- **Status Query**: Get camera status
- **Firmware Version**: Query firmware version
- **Model Information**: Get camera model details

---

### 7. ADVANCED FEATURES (`aw_cam` endpoint)

#### Multi-Matrix
- **Multi-Matrix Mode**: Enable multi-matrix color correction
- **Multi-Matrix Settings**: Adjust for different color temperatures

#### Shading
- **Shading Mode**: Enable/disable shading correction
- **Shading Adjustment**: Fine-tune shading parameters

#### Image Flip/Rotate
- **Image Flip**: Horizontal / Vertical flip
- **Image Rotation**: 90° / 180° / 270° rotation

#### Privacy Masking
- **Privacy Mask**: Enable/disable privacy zones
- **Mask Position**: Set mask area coordinates
- **Multiple Masks**: Support for multiple mask zones

#### Motion Detection
- **Motion Detection**: Enable/disable motion detection
- **Sensitivity**: Adjust motion detection sensitivity
- **Detection Area**: Set motion detection zones

---

### 8. NETWORK & SYSTEM (`aw_cam` / system endpoints)

#### Network Settings
- **IP Configuration**: Static / DHCP
- **Network Speed**: 10/100/1000 Mbps
- **Streaming Ports**: Configure RTSP/HTTP ports

#### Security
- **User Management**: Add/remove users
- **Password Change**: Change admin password
- **Access Control**: IP whitelist/blacklist

#### System
- **Date/Time**: Set camera date and time
- **Time Zone**: Configure timezone
- **Factory Reset**: Reset to factory defaults
- **Firmware Update**: Update camera firmware

---

## Implementation Priority Recommendations 🎯

### High Priority (Most Used)
1. **Exposure Control** (Iris, Gain, Shutter, ND) - Essential for image quality
2. **White Balance** (WB Mode, Color Temp, R/B Gain) - Critical for color accuracy
3. **PTZ Presets** (Save/Recall) - Core PTZ functionality
4. **Focus Control** (Auto/Manual, One Push AF) - Essential for sharp images

### Medium Priority (Professional Features)
5. **Gamma Control** - Important for matching reference monitors
6. **Detail/Sharpness** - Fine-tuning image quality
7. **Knee/Highlight Control** - Dynamic range management
8. **Scene Files** - Save complete camera setups

### Lower Priority (Advanced/Convenience)
9. **Noise Reduction** - Image enhancement
10. **Matrix/Color Correction** - Advanced color grading
11. **Privacy Masks** - Security feature
12. **Recording Control** - If cameras support SD recording

---

## Technical Notes 📝

### Command Format
- **Camera Settings**: `http://<ip>/cgi-bin/aw_cam?cmd=<command>&res=1`
- **PTZ Control**: `http://<ip>/cgi-bin/aw_ptz?cmd=<command>&res=1`
- **Query Status**: `http://<ip>/cgi-bin/aw_cam?cmd=%3C%3E&res=1` (returns XML)

### Model Differences
- **HE120/HE40**: Basic feature set, older API
- **UE70/UE100**: Mid-range, enhanced features
- **UE150/UE160**: Full feature set, latest API, 4K support

### Authentication
- All commands require HTTP Basic Auth (username/password)
- Default: `admin` / `admin` (varies by model)

---

## Example Implementation Structure

```python
# Camera Control Panel Sections:
1. Exposure Tab
   - Iris (Mode, Value, Speed)
   - Gain (Mode, Value, Limit)
   - Shutter (Mode, Speed)
   - ND Filter (Mode, Value)
   - Exposure Compensation

2. Color Tab
   - White Balance (Mode, Temp, R/B Gain)
   - Color Matrix (Type, Saturation, Hue)
   - Gamma (Mode, Level)
   - Black Balance

3. Image Tab
   - Detail (Level, H/V Ratio, Coring)
   - Knee (Mode, Point, Slope)
   - Noise Reduction (DNR Level)
   - White Clip

4. PTZ Tab
   - Pan/Tilt (Position, Speed, Limits)
   - Zoom (Position, Speed, Ratio)
   - Focus (Mode, Position, AF Settings)
   - Presets (Save/Recall 1-100)

5. Advanced Tab
   - Scene Files (Save/Recall 1-6)
   - Privacy Masks
   - Image Flip/Rotate
   - Motion Detection
```

---

## Resources 📚

- **Panasonic Official Docs**: `eww.pass.panasonic.co.jp/pro-av/support/`
- **CGI Command Reference**: "HD Integrated Camera Interface Specifications"
- **PTZ Protocol Docs**: "PTZ Protocol (CGI) / AW Command List"
- **Model-Specific Manuals**: Available on Panasonic support site

