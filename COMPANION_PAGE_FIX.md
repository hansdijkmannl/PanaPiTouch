# Companion Page Vertical Resize Fix

## Issue
When clicking on the Companion page, the app resizes vertically, expanding downward unexpectedly.

## Root Cause
The OSK (On-Screen Keyboard) slot on the Companion page was initialized with a **fixed height of 430px** and was always visible, even when the OSK wasn't docked. This caused the layout to allocate space for the OSK slot even when it was empty.

### Problematic Code (Before Fix)
In [companion_page.py:97-98](src/ui/companion_page.py#L97-L98):
```python
# Default OSK height; MainWindow may override to match OSKWidget's configured height
self.osk_slot.setFixedHeight(430)  # Always 430px!
layout.addWidget(self.osk_slot, 0)  # Always in layout
```

This meant:
- OSK slot takes up 430px of vertical space
- Space is reserved even when OSK is not being used
- Clicking Companion page → layout includes 430px slot → app resizes vertically

## Solution
Set the OSK slot to **height 0 and hidden by default**, only showing it when the OSK is actually docked:

### Fixed Code
1. **Companion Page** - Initialize slot as hidden:
```python
# Start with height 0 - MainWindow will set proper height when OSK is docked
self.osk_slot.setFixedHeight(0)
self.osk_slot.hide()  # Hide by default, show when OSK is docked
layout.addWidget(self.osk_slot, 0)
```

2. **Main Window** - Show slot when docking OSK:
```python
def _dock_osk_to_companion_page(self):
    # ... setup code ...
    slot.setFixedHeight(desired_h)
    slot.show()  # Make slot visible when OSK is docked
    # ... rest of docking code ...
```

3. **Main Window** - Hide slot when undocking OSK:
```python
def _undock_osk_from_companion(self):
    # ... undocking code ...
    slot.setFixedHeight(0)
    slot.hide()  # Hide slot when OSK is removed
```

## Files Modified
- [src/ui/companion_page.py](src/ui/companion_page.py#L97-L98) - Set slot to height 0 and hide by default
- [src/ui/main_window.py](src/ui/main_window.py#L5623) - Show slot when docking OSK
- [src/ui/main_window.py](src/ui/main_window.py#L5660) - Hide slot when undocking OSK from Companion
- [src/ui/main_window.py](src/ui/main_window.py#L5723) - Hide slot when undocking OSK from Camera page
- [src/ui/main_window.py](src/ui/main_window.py#L5685) - Show slot when docking OSK to Camera page
- [src/ui/camera_page.py](src/ui/camera_page.py#L1038) - Also hide camera page OSK slot by default for consistency

## Impact
- ✅ Companion page no longer causes vertical resize when opened
- ✅ OSK slot only takes up space when OSK is actually docked
- ✅ Layout behaves correctly when navigating between pages
- ✅ Same fix applied to Camera page OSK slot for consistency

## Testing
1. Navigate to Companion page → app should NOT resize vertically
2. Click on a text input in Companion → OSK should appear and slot should expand
3. Navigate away from Companion → OSK should hide and slot should collapse
4. Repeat test with Camera page to ensure consistency

---

## Technical Details

The OSK (On-Screen Keyboard) can be docked into special slots on certain pages to avoid covering important UI elements:
- **Companion Page**: OSK is always docked when page is active (for better text input)
- **Camera Page**: OSK is docked when editing camera settings (to keep bottom sheet visible)

The slots must:
- Start hidden (height=0, hide()) to not affect layout
- Show and expand when OSK is docked (setFixedHeight(height), show())
- Hide and collapse when OSK is undocked (setFixedHeight(0), hide())

This ensures smooth page transitions without unexpected layout shifts.
