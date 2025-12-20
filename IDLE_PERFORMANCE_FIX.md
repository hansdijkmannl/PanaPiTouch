# Idle Performance Optimization - Unreachable Cameras

## Problem

When cameras are configured but unreachable (e.g., on a test bed without network), the app consumed excessive CPU while idle due to continuous connection retry attempts.

### Root Causes

1. **Tight Retry Loops**: Connection failures retried every 2 seconds
2. **No Exponential Backoff**: Failed connections retried at constant rate forever
3. **OpenCV Timeout Blocking**: `cv2.VideoCapture()` blocking for several seconds per attempt
4. **Multiple Threads**: 5 unreachable cameras = 5 threads all hammering connections simultaneously

## Solution

Implemented exponential backoff and connection timeouts across all camera streaming components.

### Changes Made

#### 1. Camera Stream ([src/camera/stream.py](src/camera/stream.py))

**Added Exponential Backoff:**
- Initial retry: immediate
- Subsequent retries: 2s, 4s, 8s, 16s, 30s, 30s... (capped at 30 seconds)
- Dramatically reduces CPU usage when cameras persistently unreachable

**Key Methods:**
```python
def _calculate_backoff_delay(self) -> float:
    """Returns: 2, 4, 8, 16, 30, 30, ..."""
    if self._connection_failures == 0:
        return 0
    return min(2 ** self._connection_failures, self._max_backoff)

def _wait_with_backoff(self):
    """Sleeps in 500ms increments to allow quick shutdown"""
    # Allows thread to exit quickly even during long backoff

def _reset_backoff(self):
    """Called on successful connection"""

def _increment_backoff(self):
    """Called on connection failure"""
```

**Added OpenCV Timeouts:**
```python
cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)  # 3 second timeout for open
cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)  # 3 second timeout for read
```

**Applied to:**
- `_capture_mjpeg()` - MJPEG streaming
- `_capture_rtsp()` - RTSP/H.264 streaming
- `_capture_snapshot()` - Snapshot fallback

#### 2. Multiview Stream ([src/camera/multiview.py](src/camera/multiview.py))

**Same exponential backoff pattern:**
- Added `_calculate_backoff_delay()`, `_wait_with_backoff()` methods
- Applied to `_capture_loop()` main stream capture
- Applied to `_capture_snapshot_loop()` fallback mode
- After 3 consecutive snapshot failures, exits snapshot mode with backoff

**Added OpenCV Timeouts:**
```python
cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
```

## Performance Impact

### Before
- **Unreachable cameras**: Constant CPU usage from retry attempts every 2 seconds
- **5 cameras**: 5 threads × retries = significant idle CPU load
- **OpenCV blocking**: Each attempt could block for 5-10 seconds

### After
- **First failure**: Waits 2 seconds
- **Second failure**: Waits 4 seconds
- **Third failure**: Waits 8 seconds
- **Fourth+ failures**: Waits 16-30 seconds between attempts
- **Result**: CPU usage drops to near-zero when cameras persistently unreachable

### Example Timeline

```
Time    Event                     Next Retry In
-----   ----------------------    -------------
0:00    Initial connection fail   2s
0:02    Retry #1 fails            4s
0:06    Retry #2 fails            8s
0:14    Retry #3 fails            16s
0:30    Retry #4 fails            30s
1:00    Retry #5 fails            30s
1:30    Retry #6 fails            30s
...     (continues at 30s)
```

## Benefits

1. **Reduced CPU Usage**: Near-zero idle CPU when cameras unreachable
2. **Quick Recovery**: Successful connection immediately resets backoff
3. **Graceful Shutdown**: Backoff sleeps in 500ms increments, allowing threads to exit quickly
4. **Network Friendly**: Reduces network traffic from repeated failed connection attempts
5. **Battery Friendly**: On laptops/portables, reduces power consumption

## Testing

To test with unreachable cameras:
1. Configure cameras with unreachable IP addresses
2. Monitor CPU usage - should drop to near-zero after first minute
3. Check logs - should see "Connection failed. Will retry in Xs" messages with increasing delays
4. When cameras become reachable, connection should recover within 30 seconds max

## Technical Notes

- Backoff is per-stream, not global (each camera has independent retry schedule)
- Timeout values are conservative (3 seconds) to balance responsiveness vs. resource usage
- Maximum backoff capped at 30 seconds (not infinite) to ensure periodic retry
- Backoff resets immediately on successful connection
- Thread-safe implementation with proper cleanup
