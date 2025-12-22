# Companion Page Auto-Dock OSK Fix

## Issue
When clicking on the Companion page, the app appears to close and reopen with the bottom quarter missing. This was caused by automatic OSK (On-Screen Keyboard) docking on page load, which expanded the window height beyond the screen size.

## Root Cause
In [main_window.py:5808-5810](src/ui/main_window.py#L5808-L5810), when switching to the Companion page (index 2), the code automatically:
1. Docked the OSK to the companion page slot
2. Showed the OSK keyboard
3. This caused the OSK slot to expand from 0px to ~430px
4. The window height increased beyond the screen height
5. The window manager tried to resize/reposition the window
6. This created a visual "close and reopen" effect

### Problematic Code (Before Fix)
```python
if index == 2:  # Companion page
    # Always show OSK docked at the bottom of Companion page.
    self._dock_osk_to_companion()  # ← Automatic docking on page load!
    # Target the web view by default
    try:
        self._show_osk_for_companion(getattr(self.companion_page, "web_view", None))
    except Exception:
        pass
```

## Solution
**Don't automatically dock the OSK when navigating to Companion page.** Instead, only dock it when the user actually clicks on a text field (which triggers focus event).

### Fixed Code
```python
if index == 2:  # Companion page
    # Don't automatically dock OSK - wait for user to click a text field
    # This prevents the window from expanding vertically on page load
    # OSK will be docked when text field gets focus (see _show_osk_for_companion)
    pass
```

## How It Works Now

### Page Navigation (No OSK)
1. User clicks Companion page button
2. Page switches to Companion
3. OSK slot remains hidden (height=0)
4. No window resize occurs
5. Companion web view loads normally

### Text Field Focus (OSK Appears)
1. User clicks on a text field in Companion web interface
2. Web view triggers focus event
3. `_show_osk_for_companion()` is called (line 5604-5605)
4. OSK is docked to companion page slot
5. Slot expands to proper height
6. OSK appears smoothly at the bottom

### Leaving Companion Page (OSK Hides)
1. User navigates away from Companion
2. `_undock_osk_from_companion()` is called (line 5825)
3. OSK is removed from slot
4. Slot collapses to height=0 and hides
5. Window returns to normal size

## Files Modified
- [src/ui/main_window.py](src/ui/main_window.py#L5808-L5812) - Removed automatic OSK docking on page load

## Related Fixes
This fix works together with:
- [COMPANION_PAGE_FIX.md](COMPANION_PAGE_FIX.md) - OSK slot initialization fix
- The slot must start hidden (height=0) for this fix to work properly

## Testing
1. Navigate to Companion page → should load smoothly, no resize, no OSK
2. Click on any text field in Companion → OSK should appear at bottom
3. Navigate away from Companion → OSK should disappear, window returns to normal size
4. Repeat navigation → should work consistently without visual glitches

---

## Technical Notes

The key insight is that **docking should be triggered by user interaction (focus event), not by page navigation**. This gives users a clean, predictable experience:

- **Page loads**: Fast, no layout shifts
- **Text input needed**: OSK appears on demand
- **Navigation**: Clean transitions

This pattern is common in mobile UIs where keyboards appear only when needed, not automatically when a page with text fields loads.
