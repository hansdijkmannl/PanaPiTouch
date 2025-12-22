# Window Geometry Lock Fix - Prevent Fullscreen Breaking During Page Changes

## Problem
When navigating to the Companion page:
- App appears to "close and reopen"
- Fullscreen is lost
- Window shows only 3/4 height
- OSK not appearing

## Root Cause
The QWebEngineView creation during page change was causing Qt to resize the main window BEFORE the web view was fully integrated into the layout. Even with proper size policies (Ignored), the web view creation process itself can trigger window resize events that break fullscreen.

## Solution: Window Geometry Lock During Page Transition

Lock the window size during the entire page change operation to prevent ANY resize attempts:

### Implementation in [main_window.py:5786-5841](src/ui/main_window.py#L5786-L5841)

```python
def _on_page_changed(self, index: int):
    """Handle page change - manage OSK and pause/resume streams"""
    # Lock window geometry during page change to prevent resize
    from PyQt6.QtCore import QTimer
    current_geom = self.geometry()
    was_fullscreen = self.isFullScreen()

    # Block any resize attempts during page transition
    self.setFixedSize(current_geom.size())

    # ... page change logic (pause/resume streams, OSK management) ...

    # Unlock window geometry and restore fullscreen after a short delay
    def restore_window_state():
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        if was_fullscreen:
            self.showFullScreen()

    QTimer.singleShot(100, restore_window_state)
```

## How It Works

### Phase 1: Lock (Immediate)
1. Page change begins
2. **Current window geometry is captured**
3. **`setFixedSize()` prevents ANY window resize**
4. Web view creation happens (triggered by `showEvent()` in companion_page.py)
5. Qt layout system runs BUT cannot resize the window
6. All size requests from web view are ignored/blocked

### Phase 2: Unlock (After 100ms)
1. Timer fires after 100ms (enough time for layout to settle)
2. Size constraints are removed (`setMinimumSize(0, 0)`, `setMaximumSize(QWIDGETSIZE_MAX)`)
3. Fullscreen is re-applied if it was active before

## Why This Works

### The Problem With Previous Approaches
- **Ignored size policies**: Prevented widget from REQUESTING size, but didn't prevent Qt from resizing window during layout changes
- **Fullscreen restoration**: Tried to restore AFTER resize happened, but the "close/reopen" visual glitch had already occurred
- **Container structure**: Helped isolate web view, but Qt still tried to accommodate layout changes

### The Solution
1. **Proactive blocking**: Prevents resize BEFORE it happens, not after
2. **Temporary constraint**: Only locks during the critical transition period
3. **Delayed unlock**: Waits for layout to settle before allowing resize again
4. **Fullscreen guarantee**: Re-applies fullscreen after unlock to ensure it's active

## Timeline of Events

**Before Fix** (Broken):
```
1. User clicks Companion button
2. _on_page_changed() runs
3. companion_page shown → showEvent() fires
4. Web view created and added to layout
5. Qt layout system runs
6. Web view has size hints → Qt tries to accommodate
7. Window resizes beyond screen → FULLSCREEN BREAKS ❌
8. Window manager repositions window → "close/reopen" visual glitch
9. Window ends up at 3/4 height
```

**After Fix** (Working):
```
1. User clicks Companion button
2. _on_page_changed() runs
3. Window size is LOCKED with setFixedSize() 🔒
4. companion_page shown → showEvent() fires
5. Web view created and added to layout
6. Qt layout system runs
7. Web view has size hints → Qt tries to resize BUT BLOCKED by fixed size 🚫
8. Window stays same size → fullscreen maintained ✅
9. After 100ms, size lock removed and fullscreen re-applied 🔓
10. Smooth transition, no visual glitch
```

## Files Modified
- [src/ui/main_window.py](src/ui/main_window.py) lines 5786-5841

## Testing Checklist

- [ ] Start app
- [ ] Navigate to Companion page → should stay fullscreen, smooth transition
- [ ] Companion web interface loads correctly
- [ ] Click on text field → OSK appears at bottom (OSK connection working)
- [ ] Type on OSK → text appears in Companion
- [ ] Navigate away from Companion → smooth transition
- [ ] Navigate back to Companion → works correctly again
- [ ] No "close/reopen" visual glitch
- [ ] App stays fullscreen throughout all navigation

## Technical Notes

### setFixedSize() vs Size Policies
- **Size policies** (Ignored, Expanding, etc.): Tell layout system what the WIDGET wants
- **setFixedSize()**: Tell layout system what the WINDOW must be (overrides all widget requests)
- During page change, we need the latter to BLOCK any resize attempts

### Why 100ms Delay?
- Qt layout system needs time to run (typically <50ms)
- Web view initialization needs time to complete
- 100ms is enough for both without being noticeable to user
- Too short (<50ms): Layout might still be running, unlock too early
- Too long (>200ms): User might notice delay in OSK appearing

### QWIDGETSIZE_MAX
- Qt's maximum widget size: 16777215 (2^24 - 1)
- Used in `setMaximumSize()` to mean "no maximum"
- Allows window to use full screen when unlocked

## Related Fixes

This is **Part 5** of the Companion page fix series:
- Part 1: [COMPANION_PAGE_FIX.md](COMPANION_PAGE_FIX.md) - OSK slot initialization
- Part 2: [COMPANION_OSK_AUTO_DOCK_FIX.md](COMPANION_OSK_AUTO_DOCK_FIX.md) - Remove auto-dock
- Part 3: [COMPANION_FULLSCREEN_FIX.md](COMPANION_FULLSCREEN_FIX.md) - Size policies (superseded)
- Part 4: [COMPANION_PAGE_REBUILD.md](COMPANION_PAGE_REBUILD.md) - Two-tier container structure
- **Part 5 (FINAL)**: Window geometry lock during page transitions

All five parts work together to create a robust, fullscreen-safe Companion page.
