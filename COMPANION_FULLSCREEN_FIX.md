# Companion Page Fullscreen Breaking Fix

## Issue
When clicking on the Companion page menu item:
1. App appears to close and reopen
2. Fullscreen mode is lost
3. Bottom quarter of app is missing/cut off
4. OSK is gone (not appearing when expected)

## Root Causes

### Cause 1: Automatic OSK Docking on Page Load
When navigating to Companion page, OSK was automatically docked, expanding the window by 430px.

### Cause 2: Web View Size Requests
`QWebEngineView` has its own preferred size hints. When added to layout, it can request more space than available, causing Qt to resize the parent window and breaking fullscreen mode.

### Cause 3: OSK Not Connected to Web View
The web view is created lazily (on first page visit), but the OSK connection happens during app initialization before the web view exists.

## Solutions

### Fix 1: Size Policy Constraints (Prevents Resize)
Set proper size policies on both the Companion page and its web view to prevent them from breaking fullscreen:

**In [companion_page.py:63-64](src/ui/companion_page.py#L63-L64)**:
```python
# Ensure page doesn't try to expand beyond parent
self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
```

**In [companion_page.py:122-125](src/ui/companion_page.py#L122-L125)**:
```python
# Ensure web view doesn't cause parent to resize
self.web_view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
# Prevent web view from requesting preferred size that might break fullscreen
self.web_view.setMinimumSize(0, 0)
self.web_view.setMaximumSize(16777215, 16777215)  # Qt's QWIDGETSIZE_MAX
```

### Fix 2: Lazy OSK Connection (Makes OSK Work Again)
Connect the web view to OSK when it's created, not during app initialization:

**In [companion_page.py:151-156](src/ui/companion_page.py#L151-L156)**:
```python
# Connect web view to OSK if main window has the connection method
try:
    if hasattr(self.parent(), '_connect_companion_webview_to_osk'):
        self.parent()._connect_companion_webview_to_osk(self.web_view)
except Exception as e:
    print(f"Could not connect companion web view to OSK: {e}")
```

### Fix 3: No Auto-Dock on Page Load (Already Done)
Don't automatically dock OSK when navigating to Companion - only when user clicks a text field.

## How It Works Now

### Page Navigation
1. User clicks Companion button
2. Page switches, web view created if needed
3. Web view uses `Ignored` size policy → doesn't request extra space
4. Window stays fullscreen
5. No resize, no visual glitch

### Text Field Interaction
1. User taps on a text field in Companion web interface
2. Web view event handler detects tap
3. `_show_osk_for_companion()` is called
4. OSK is docked to companion page slot
5. Slot expands from 0px to 430px (within existing window)
6. OSK appears at bottom, user can type

### Leaving Companion
1. User navigates away
2. OSK is undocked and hidden
3. Slot collapses to 0px
4. Window stays fullscreen throughout

## Files Modified
- [src/ui/companion_page.py](src/ui/companion_page.py)
  - Lines 63-64: Page size policy
  - Lines 122-125: Web view size constraints
  - Lines 151-156: Lazy OSK connection

## Related Fixes
This is part 3 of the Companion page resize fix series:
- Part 1: [COMPANION_PAGE_FIX.md](COMPANION_PAGE_FIX.md) - OSK slot initialization
- Part 2: [COMPANION_OSK_AUTO_DOCK_FIX.md](COMPANION_OSK_AUTO_DOCK_FIX.md) - Remove auto-dock
- Part 3: This fix - Size policies and lazy OSK connection

## Technical Notes

### QSizePolicy Explained
- **Expanding**: Widget can grow, will use extra space if available
- **Ignored**: Widget takes whatever space is given, doesn't request preferred size
- Using `Ignored` for web view prevents it from trying to resize parent window

### Why setMinimumSize(0, 0)?
Ensures web view doesn't have a minimum size requirement that could force window resize.

### Why setMaximumSize(16777215, 16777215)?
This is Qt's `QWIDGETSIZE_MAX` - essentially "no maximum", allows web view to use all available space.

## Testing Checklist
- [ ] Navigate to Companion page → should stay fullscreen
- [ ] Companion page loads smoothly → no resize/glitch
- [ ] Click on text field in Companion → OSK appears at bottom
- [ ] Type on OSK → text appears in Companion
- [ ] Navigate away from Companion → OSK disappears
- [ ] Return to Companion → process repeats correctly
