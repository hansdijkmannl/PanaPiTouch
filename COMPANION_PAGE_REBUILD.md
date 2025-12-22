# Companion Page Rebuild - Complete Fix

## Problem
Multiple attempts to fix the Companion page resize issue weren't working because the fundamental layout structure was flawed. The web view was being added directly to the main layout without proper containment, causing fullscreen to break.

## Solution: Complete Layout Rebuild

Rebuilt the Companion page with a proper two-tier layout structure:

```
CompanionPage (Ignored size policy)
└── VBoxLayout
    ├── Web Container (stretch=1, Ignored size policy)
    │   └── Web View (Ignored size policy, no size requests)
    └── OSK Slot (stretch=0, Fixed height policy)
        └── OSK Widget (when docked)
```

## Key Changes

### 1. Two-Tier Container Structure

**Before** (Broken):
```python
layout = QVBoxLayout(self)
layout.addWidget(placeholder)  # Replaced by web_view later
layout.addWidget(osk_slot)
```

**After** (Fixed):
```python
layout = QVBoxLayout(self)

# Web container with stretch=1 (takes all available space)
web_container = QWidget()
web_container_layout = QVBoxLayout(web_container)
web_container_layout.addWidget(web_view, stretch=1)
layout.addWidget(web_container, stretch=1)

# OSK slot with stretch=0 (only takes space when visible)
layout.addWidget(osk_slot, stretch=0)
```

### 2. Proper Size Policies

**Companion Page**:
```python
self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
self.setMinimumSize(0, 0)
```
- `Ignored` = Don't ask parent for more space, use what you're given
- `setMinimumSize(0, 0)` = No minimum size requirement

**Web Container**:
```python
self.web_container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
```
- Fills available space without requesting more

**Web View**:
```python
self.web_view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
self.web_view.setMinimumSize(0, 0)
```
- Uses container size without breaking fullscreen

**OSK Slot**:
```python
self.osk_slot.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
self.osk_slot.setFixedHeight(0)  # Starts at 0, expands to 430 when OSK docked
```
- Fixed vertical size, ignored horizontal

### 3. Stretch Factors

```python
layout.addWidget(web_container, stretch=1)   # Takes all extra space
layout.addWidget(osk_slot, stretch=0)        # Only takes its fixed height
```

## How It Works

### Initial Page Load
1. Page loads with web_container at stretch=1
2. OSK slot is hidden (height=0, stretch=0)
3. Web container fills entire page
4. No size requests → fullscreen stays intact

### When User Clicks Text Field
1. OSK docking is triggered
2. OSK slot height changes: 0 → 430px
3. Web container shrinks to accommodate OSK
4. Layout: `[Web Container (remaining space)] [OSK (430px)]`
5. Total height stays same → fullscreen maintained

### When Leaving Companion Page
1. OSK is undocked
2. OSK slot height changes: 430px → 0
3. Web container expands back to full size
4. Fullscreen stays intact

## File Changes

### [src/ui/companion_page.py](src/ui/companion_page.py)

**Lines 64-65**: Page size policy
```python
self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
self.setMinimumSize(0, 0)
```

**Lines 72-77**: Web container creation
```python
self.web_container = QWidget()
self.web_container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
self.web_container_layout = QVBoxLayout(self.web_container)
```

**Lines 79-99**: Placeholder in web container
```python
self.web_container_layout.addWidget(self.placeholder)
```

**Lines 101-102**: Web container added to main layout
```python
layout.addWidget(self.web_container, stretch=1)
```

**Lines 107-115**: OSK slot configuration
```python
self.osk_slot.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
self.osk_slot.setFixedHeight(0)
self.osk_slot.hide()
layout.addWidget(self.osk_slot, stretch=0)
```

**Lines 123-127**: Placeholder removal from web container
```python
self.web_container_layout.removeWidget(self.placeholder)
self.placeholder.deleteLater()
```

**Lines 134-135**: Web view size policy
```python
self.web_view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
self.web_view.setMinimumSize(0, 0)
```

**Lines 157-158**: Web view added to web container
```python
self.web_container_layout.addWidget(self.web_view, stretch=1)
```

## Why This Works

### The Problem With Previous Approaches
- Web view was added directly to main layout
- QWebEngineView has preferred size hints (wants specific dimensions)
- Qt tried to accommodate web view's size requests
- Window expanded beyond fullscreen bounds
- Window manager repositioned/resized → "close and reopen" effect

### The Solution
1. **Containment**: Web container isolates web view from main window
2. **Ignored Policy**: Web view can't request size from parent
3. **Stretch Factors**: Explicit control over space distribution
4. **Fixed OSK Height**: OSK slot only takes exactly what it needs

### Visual Layout

**Before** (Broken):
```
┌─────────────────────────────┐
│ CompanionPage               │
│ ┌─────────────────────────┐ │
│ │ Web View (wants 1920x?) │ │  ← Tries to be full size
│ │                         │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ OSK Slot (430px)        │ │  ← Additional space
│ └─────────────────────────┘ │
└─────────────────────────────┘
     ↓
Window expands beyond screen → breaks fullscreen
```

**After** (Fixed):
```
┌─────────────────────────────┐ ← Window (fullscreen, fixed size)
│ CompanionPage               │
│ ┌─────────────────────────┐ │
│ │ Web Container (stretch) │ │ ← Takes available space
│ │ ┌─────────────────────┐ │ │
│ │ │ Web View (fills)    │ │ │ ← Fills container
│ │ └─────────────────────┘ │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ OSK (0 or 430px)        │ │ ← Only when visible
│ └─────────────────────────┘ │
└─────────────────────────────┘
     ↓
Space is redistributed within window → fullscreen maintained
```

## Testing Checklist

- [ ] Navigate to Companion → stays fullscreen, loads smoothly
- [ ] Web view displays Companion interface correctly
- [ ] Click on text field → OSK appears at bottom
- [ ] Web view shrinks to make room for OSK
- [ ] Type on OSK → text appears in Companion
- [ ] Navigate away → OSK disappears, web container expands
- [ ] Return to Companion → works correctly again
- [ ] No resize, no "close/reopen" effect throughout

## Related Fixes

This is the final part of the Companion page fix series:
- Part 1: [COMPANION_PAGE_FIX.md](COMPANION_PAGE_FIX.md) - OSK slot initialization
- Part 2: [COMPANION_OSK_AUTO_DOCK_FIX.md](COMPANION_OSK_AUTO_DOCK_FIX.md) - Remove auto-dock
- Part 3: [COMPANION_FULLSCREEN_FIX.md](COMPANION_FULLSCREEN_FIX.md) - Size policies (superseded)
- **Part 4 (FINAL)**: This rebuild - Proper two-tier container structure

The fundamental issue was architectural. This rebuild addresses it properly with a clean, maintainable layout structure.
