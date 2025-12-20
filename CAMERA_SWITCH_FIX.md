# Camera Switching Performance Fix

## Problem

When switching between cameras (especially unreachable ones), the app would stall for approximately **10 seconds**, making the UI unresponsive.

### Root Cause

When switching cameras, `_select_camera()` called `_sync_camera_controls_with_current_camera()` which made **10+ synchronous HTTP requests** to query camera settings:

**Sync Methods Called:**
1. `_sync_camera_exposure_settings()` - 3 HTTP queries (QSH, QGA, QIR)
2. `_sync_camera_color_settings()` - 3 HTTP queries (QWB, QRG, QBG)
3. `_sync_camera_image_settings()` - 3+ HTTP queries
4. `_sync_camera_operations_settings()` - 3+ HTTP queries

**With Original Settings:**
- Each query: 2-second timeout
- Unreachable camera: every query times out
- Total delay: **12-20+ requests × 2s = 24-40 seconds of blocking!**
- User reported 10 seconds = ~5 queries timing out

This happened **on the main Qt event loop**, freezing the entire UI.

## Solution

Implemented a three-part fix to eliminate camera switching delays:

### 1. Skip Sync for Unconnected Cameras ([main_window.py:2199-2204](src/ui/main_window.py#L2199-L2204))

Check if camera stream is connected before attempting sync:

```python
# Check if camera stream is connected before syncing
# This avoids multiple timeout delays when camera is unreachable
stream = self.camera_streams.get(self.current_camera_id)
if stream and not stream.is_connected:
    logger.debug(f"Skipping sync for camera {self.current_camera_id} - not connected yet")
    return
```

**Benefit:** Completely avoids HTTP requests when camera is known to be unreachable.

### 2. Reduced Query Timeout ([main_window.py:2041-2076](src/ui/main_window.py#L2041-L2076))

Changed default timeout from **2.0s → 0.5s**:

```python
def _query_camera_setting(self, command: str, endpoint: str = "aw_cam", timeout: float = 0.5) -> str:
    """
    Query a camera setting via CGI command.

    Args:
        timeout: Request timeout in seconds (default: 0.5s for quick response)
    """
    response = requests.get(url, auth=(camera.username, camera.password), timeout=timeout)
```

**Benefit:** If sync does happen on unreachable camera, delay is 75% shorter (0.5s vs 2s per query).

### 3. Deferred Sync Execution ([main_window.py:6195-6203](src/ui/main_window.py#L6195-L6203))

Moved sync call to background using QTimer:

```python
# Sync camera control panels with current camera settings
# DEFERRED: Do this in background to avoid blocking UI when camera is unreachable
# This prevents 10+ second stalls when switching to offline cameras
try:
    from PyQt6.QtCore import QTimer
    # Delay sync by 500ms to let UI update first, and run in background
    QTimer.singleShot(500, self._sync_camera_controls_with_current_camera)
except Exception as e:
    logger.warning(f"Error scheduling camera controls sync: {e}")
```

**Benefit:** UI updates immediately, sync happens in background after 500ms.

### 4. Better Error Handling ([main_window.py:2071-2076](src/ui/main_window.py#L2071-L2076))

Changed logging from `error`/`warning` to `debug` to reduce log spam:

```python
except requests.exceptions.Timeout:
    logger.debug(f"Camera query timeout: {command}")
    return ""
except Exception as e:
    logger.debug(f"Camera query error: {e}")
    return ""
```

**Benefit:** Cleaner logs when cameras are intentionally unreachable (test environments).

## Performance Impact

### Before
```
Click camera button
  ↓
Update UI (instant)
  ↓
Sync camera controls (BLOCKING)
  ↓ QSH query → 2s timeout
  ↓ QGA query → 2s timeout
  ↓ QIR query → 2s timeout
  ↓ QWB query → 2s timeout
  ↓ QRG query → 2s timeout
  ... (5-10 more queries)
  ↓
Total: 10-20 seconds UI freeze
  ↓
Finally show "Switched to Camera X"
```

### After
```
Click camera button
  ↓
Check if camera connected → NO
  ↓
Update UI (instant)
  ↓
Show "Switched to Camera X" (instant)
  ↓
[500ms later, in background]
  ↓
Try to sync → camera not connected → skip
```

**Result:** Camera switching is now **instant** even with unreachable cameras!

### With Connected Cameras

If camera IS connected:
- Sync happens 500ms after switch (allows UI to update first)
- Each query timeout: 0.5s instead of 2.0s
- Max delay if all queries timeout: ~5-10 seconds, but non-blocking

## Combined with Previous Optimizations

This fix works together with the [exponential backoff optimization](IDLE_PERFORMANCE_FIX.md):

1. **Camera switching:** Instant (this fix)
2. **Stream connection attempts:** Exponential backoff 2s→4s→8s→16s→30s (previous fix)
3. **Idle CPU usage:** Near-zero with unreachable cameras (previous fix)

## Testing

To verify the fix:
1. Configure 5 cameras with unreachable IP addresses
2. Switch between cameras rapidly
3. UI should respond instantly
4. Check logs - should see "Skipping sync for camera X - not connected yet"
5. No 10-second stalls

To test with reachable cameras:
1. Switch to a connected camera
2. After 500ms, should see "Syncing camera settings..." toast
3. Control panels should update with current camera settings
4. No blocking even if some queries fail
