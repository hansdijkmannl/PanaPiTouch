# Blank Space Summary - Portrait Layout

## Main Layout Structure (Top to Bottom)
All elements are stacked vertically with **0 spacing** between them in the main layout.

---

## 1. Top Navigation Bar (`nav_bar`)
- **Height**: 70px (fixed)
- **Layout Margins**: `20px left, 0px top, 20px right, 0px bottom`
- **Layout Spacing**: 0px
- **Internal Structure**:
  - Uses `addStretch()` before and after buttons (centers buttons, creates flexible space)
  - Button container has `0px margins` and `0px spacing`

**Blank Space Sources**:
- 20px left margin
- 20px right margin
- Stretch areas on left/right of buttons (flexible, fills available space)

---

## 2. Preview Container (`preview_container`)
- **Height**: Dynamic (16:9 aspect ratio maintained)
- **Layout Margins**: `0px all sides`
- **Layout Spacing**: 0px
- **Internal Structure**:
  - `preview_inner_layout`: 0px margins, 0px spacing
  - `preview_wrapper_layout`: 0px margins, 0px spacing

**Blank Space Sources**:
- None (fully utilized for preview)

---

## 3. Overlay Buttons Bar (`overlay_buttons_bar`)
- **Height**: 50px (fixed)
- **Layout Margins**: `0px all sides`
- **Layout Spacing**: 0px
- **Internal Structure**:
  - Uses `addStretch()` before and after buttons (centers buttons)
  - `buttons_container` has `20px left, 0px top, 20px right, 0px bottom` margins
  - Button spacing: 0px

**Blank Space Sources**:
- 20px left padding inside buttons_container
- 20px right padding inside buttons_container
- Stretch areas on left/right of buttons (flexible, fills available space)

---

## 4. Camera Selection Bar (`camera_bar`)
- **Height**: 120px (fixed)
- **Layout Margins** (portrait mode): `0px left, 10px top, 0px right, 0px bottom`
- **Layout Spacing**: 12px between camera buttons
- **Internal Structure**:
  - Uses `addStretch()` before buttons (centers buttons)
  - Button size: 88x80px (demo), 80x80px (cameras)

**Blank Space Sources**:
- 10px top margin (positions buttons higher)
- 12px spacing between each camera button
- Stretch area on left side (centers buttons, creates flexible space)
- ~40px vertical space (120px height - 80px button = 40px, but 10px top margin means ~30px bottom space)

---

## 5. Bottom Menu Bar (`bottom_menu_bar`)
- **Height**: 60px (fixed)
- **Layout Margins**: `20px left, 0px top, 20px right, 0px bottom`
- **Layout Spacing**: 0px
- **Internal Structure**:
  - Uses `addStretch()` before and after buttons (centers buttons)
  - `menu_buttons_container`: 0px margins, 0px spacing
  - Button spacing: 0px

**Blank Space Sources**:
- 20px left margin
- 20px right margin
- Stretch areas on left/right of buttons (flexible, fills available space)

---

## 6. Bottom Panel (`bottom_panel`)
- **Height**: 300px (fixed)
- **Layout Margins**: `0px all sides`
- **Layout Spacing**: 0px
- **Internal Structure**: Depends on which panel is active (PTZ, Grid, Guides, Multiview)

**Blank Space Sources**:
- Varies by panel content (check individual panel layouts)

---

## Summary of All Blank Spaces

### Fixed Margins:
- **Top Nav Bar**: 20px left, 20px right
- **Overlay Buttons Bar**: 20px left, 20px right (inside container)
- **Camera Bar**: 10px top (portrait mode)
- **Bottom Menu Bar**: 20px left, 20px right

### Fixed Spacing:
- **Camera Bar**: 12px between camera buttons

### Flexible Spaces (Stretch):
- **Top Nav Bar**: Left/right stretch areas (centers buttons)
- **Overlay Buttons Bar**: Left/right stretch areas (centers buttons)
- **Camera Bar**: Left stretch area (centers buttons)
- **Bottom Menu Bar**: Left/right stretch areas (centers buttons)

### Vertical Gaps:
- **Camera Bar**: ~30px bottom space (120px height - 80px button - 10px top margin)
- **Between Elements**: 0px (elements touch each other)

---

## Recommendations to Reduce Blank Space:

1. **Remove horizontal margins** from nav bar, overlay buttons bar, and bottom menu bar (currently 20px each side)
2. **Reduce camera bar top margin** from 10px to 0px or smaller
3. **Reduce camera button spacing** from 12px to 6-8px
4. **Remove stretch areas** if buttons don't need to be centered (or use fixed spacing instead)
5. **Reduce camera bar height** if buttons don't need 120px (could be 100px or less)











