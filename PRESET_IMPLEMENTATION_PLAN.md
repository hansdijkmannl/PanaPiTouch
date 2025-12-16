# Preset Implementation Plan - Matching Companion Module

## Summary of Changes

### 1. Rename Menu Option
- Change "PTZ" (index 3) → "Presets" in category menu
- Remove old "Presets" menu option (index 4) or merge functionality

### 2. Replace PTZ Advanced Panel with Preset Grid
- **32 buttons in 8×4 grid** (presets 1-32)
- **Button styling**: Match camera bar buttons (`cameraButton` style, 88×80px)
- **Thumbnail display**: Each button shows thumbnail image when preset is saved
- **Visual states**:
  - Empty preset: Grey background, preset number only
  - Saved preset: Thumbnail image + preset number overlay

### 3. Preset Button Behavior (Matching Companion Module)

**Click (Short Press)**:
- Recall preset: Send `R{num:02d}` command via `aw_ptz` endpoint
- Visual feedback: Button highlights briefly

**Long Press**:
- Show context menu/dialog with options:
  - **Save Preset**: 
    - Capture current camera frame as thumbnail
    - Save preset position: Send `M{num:02d}` command
    - Store thumbnail image to disk
    - Update button visual state
  - **Delete Preset**:
    - Remove thumbnail from disk
    - Clear preset on camera (if supported)
    - Update button to empty state

### 4. Thumbnail Management

**Storage**:
- Directory: `~/.config/panapitouch/presets/{camera_id}/`
- Filename: `preset_{num:02d}.jpg` (e.g., `preset_01.jpg`)
- Format: JPEG, ~120×68px (matching camera bar thumbnail size)

**Capture**:
- When saving preset, capture current frame from `preview_widget` or camera stream
- Resize to thumbnail dimensions
- Save to disk
- Update button display immediately

**Display**:
- Load thumbnail on button creation
- Show thumbnail as background/image
- Overlay preset number on top
- Fallback to empty state if thumbnail missing

### 5. Implementation Details

**Custom Preset Button Widget**:
- Inherit from `QPushButton` or create custom widget
- Handle mouse events for long press detection
- Display thumbnail using `setIcon` or custom painting
- Store preset number, camera ID, saved state

**Long Press Detection**:
- Use `QTimer` to detect press duration (e.g., 500ms)
- Show context menu (`QMenu`) or dialog (`QDialog`) on long press
- Cancel if mouse released before threshold

**Preset Storage**:
- Extend `Settings` class or create separate preset manager
- Store preset metadata (camera_id, preset_num, saved_date, etc.)
- Load thumbnails on panel creation

**Camera Frame Capture**:
- Access current frame from `preview_widget.current_frame` or camera stream
- Convert numpy array to QPixmap
- Resize and save as JPEG

### 6. Companion Module Compatibility

Based on Companion module behavior:
- Presets are camera-specific (each camera has its own presets 1-32)
- Thumbnails are captured from live feed when saving
- Preset recall is immediate (no confirmation)
- Save/Delete require explicit action (long press menu)

---

## Implementation Steps

1. Create `PresetButton` custom widget class
2. Implement thumbnail capture and storage system
3. Replace PTZ Advanced panel with preset grid
4. Add long press detection and context menu
5. Integrate with camera frame capture
6. Update menu labels











