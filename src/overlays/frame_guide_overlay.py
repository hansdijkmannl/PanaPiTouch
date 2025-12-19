"""
Frame Guide Overlay

Provides aspect ratio markers with template library, custom ratios, and drag-resize functionality.
"""
import cv2
import numpy as np
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
import json
from pathlib import Path
from .base import Overlay


@dataclass
class FrameGuide:
    """A frame guide definition"""
    name: str
    aspect_ratio: Tuple[float, float]  # width:height
    color: Tuple[int, int, int] = (255, 255, 255)  # BGR
    is_custom: bool = False
    custom_rect: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h (normalized 0-1000) for drag-created frames


class FrameGuideOverlay(Overlay):
    """
    Frame guide overlay for aspect ratio markers.
    
    Features:
    - Template library with preset aspect ratios
    - Custom aspect ratio input
    - Drag and resize functionality
    - Save/load custom guides
    """
    
    # Preset template library
    TEMPLATES: Dict[str, List[FrameGuide]] = {
        "Social": [
            FrameGuide("9:16 (Stories/Reels)", (9, 16)),
            FrameGuide("1:1 (Square)", (1, 1)),
            FrameGuide("4:5 (Instagram)", (4, 5)),
        ],
        "Cinema": [
            FrameGuide("2.35:1 (Scope)", (2.35, 1)),
            FrameGuide("2.39:1 (Anamorphic)", (2.39, 1)),
            FrameGuide("1.85:1 (Flat)", (1.85, 1)),
            FrameGuide("1.66:1 (European)", (1.66, 1)),
            FrameGuide("2.00:1 (Univisium)", (2.00, 1)),
        ],
        "TV/Broadcast": [
            FrameGuide("16:9 (HD)", (16, 9)),
            FrameGuide("4:3 (SD)", (4, 3)),
            FrameGuide("14:9 (Compromise)", (14, 9)),
            FrameGuide("21:9 (Ultrawide)", (21, 9)),
        ],
    }
    
    def __init__(self):
        super().__init__()
        self.active_guide: Optional[FrameGuide] = None
        self.custom_guides: List[FrameGuide] = []
        
        # Styling - thicker lines for visibility
        self.line_color = (0, 200, 255)  # Orange/yellow (BGR)
        self.line_thickness = 4  # Doubled from 2
        self.line_opacity = 0.8
        self.fill_opacity = 0.3  # Darken outside areas
        self.show_label = False  # Don't show label text
        
        # Drag/resize state
        self.drag_mode = False
        self.custom_rect: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h (normalized 0-1000)
        self._drag_start = None
        self._resize_handle = None  # 'tl', 'tr', 'bl', 'br', 'move'
        
        # Load saved custom guides
        self._load_custom_guides()
    
    def _get_config_path(self) -> Path:
        """Get path to custom guides config file"""
        config_dir = Path.home() / ".config" / "panapitouch"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "frame_guides.json"
    
    def _load_custom_guides(self):
        """Load custom guides from config"""
        try:
            config_path = self._get_config_path()
            if config_path.exists():
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    self.custom_guides = [
                        FrameGuide(
                            name=g['name'],
                            aspect_ratio=tuple(g['aspect_ratio']),
                            color=tuple(g.get('color', (255, 255, 255))),
                            is_custom=True,
                            custom_rect=tuple(g['custom_rect']) if g.get('custom_rect') else None
                        )
                        for g in data.get('guides', [])
                    ]
        except Exception as e:
            print(f"Failed to load custom guides: {e}")
            self.custom_guides = []
    
    def _save_custom_guides(self):
        """Save custom guides to config"""
        try:
            config_path = self._get_config_path()
            data = {
                'guides': [
                    {
                        'name': g.name,
                        'aspect_ratio': list(g.aspect_ratio),
                        'color': list(g.color),
                        'custom_rect': list(g.custom_rect) if g.custom_rect else None,
                    }
                    for g in self.custom_guides
                ]
            }
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save custom guides: {e}")
    
    def get_all_templates(self) -> Dict[str, List[FrameGuide]]:
        """Get all templates including custom guides"""
        templates = dict(self.TEMPLATES)
        if self.custom_guides:
            templates["Custom"] = self.custom_guides
        return templates
    
    def set_guide_by_name(self, category: str, name: str) -> bool:
        """Set active guide by category and name"""
        templates = self.get_all_templates()
        if category in templates:
            for guide in templates[category]:
                if guide.name == name:
                    self.active_guide = guide
                    # If guide has a custom_rect, restore it but DON'T enable drag mode
                    # (user wants to view it, not resize it)
                    if guide.custom_rect is not None:
                        self.custom_rect = guide.custom_rect
                    else:
                        self.custom_rect = None
                    # Always disable drag mode when recalling a guide
                    self.drag_mode = False
                    return True
        return False
    
    def set_custom_ratio(self, width: float, height: float, name: str = None) -> bool:
        """Set a custom aspect ratio"""
        if width <= 0 or height <= 0:
            return False
        
        ratio_str = f"{width}:{height}" if width >= height else f"{width}:{height}"
        guide_name = name or f"Custom {ratio_str}"
        
        self.active_guide = FrameGuide(
            name=guide_name,
            aspect_ratio=(width, height),
            is_custom=True
        )
        self.drag_mode = False
        self.custom_rect = None
        return True
    
    def save_current_as_custom(self, name: str) -> bool:
        """Save current guide as a custom preset"""
        # Priority: Save custom_rect if it exists (even if drag_mode is off)
        # This ensures we save the actual dragged frame, not a default
        if self.custom_rect is not None:
            # Save the normalized custom_rect for exact positioning
            custom_rect = self.custom_rect
            # Calculate aspect ratio from custom rect (normalized values represent relative size)
            w, h = self.custom_rect[2], self.custom_rect[3]
            if h <= 0:
                return False
            aspect_ratio = (float(w), float(h))
        elif self.active_guide is not None:
            # Fallback to active guide's aspect ratio if no custom_rect
            aspect_ratio = self.active_guide.aspect_ratio
            custom_rect = None
        else:
            return False
        
        new_guide = FrameGuide(
            name=name,
            aspect_ratio=aspect_ratio,
            color=self.line_color,
            is_custom=True,
            custom_rect=custom_rect
        )
        
        # Check if name already exists - update it
        for i, guide in enumerate(self.custom_guides):
            if guide.name == name:
                self.custom_guides[i] = new_guide
                self._save_custom_guides()
                return True
        
        # Add new custom guide
        self.custom_guides.append(new_guide)
        self._save_custom_guides()
        return True
    
    def delete_custom_guide(self, name: str) -> bool:
        """Delete a custom guide"""
        for i, guide in enumerate(self.custom_guides):
            if guide.name == name:
                del self.custom_guides[i]
                self._save_custom_guides()
                return True
        return False
    
    def enable_drag_mode(self):
        """Enable drag/resize mode for custom rectangle"""
        self.drag_mode = True
        if self.custom_rect is None:
            # Start with centered rectangle
            self.custom_rect = (250, 250, 500, 500)  # Normalized to 0-1000
    
    def disable_drag_mode(self):
        """Disable drag/resize mode"""
        self.drag_mode = False
    
    def _calculate_frame_rect(self, frame_w: int, frame_h: int) -> Tuple[int, int, int, int]:
        """Calculate the frame guide rectangle based on aspect ratio"""
        # First priority: Use custom_rect if it exists (for dragged or recalled custom frames)
        # Check custom_rect on the active_guide first (for recalled guides)
        if self.active_guide is not None and self.active_guide.custom_rect is not None:
            rect = self.active_guide.custom_rect
            x = int(rect[0] * frame_w / 1000)
            y = int(rect[1] * frame_h / 1000)
            w = int(rect[2] * frame_w / 1000)
            h = int(rect[3] * frame_h / 1000)
            return (x, y, w, h)
        
        # Second priority: Use instance custom_rect (for currently being dragged frames)
        if self.custom_rect is not None:
            x = int(self.custom_rect[0] * frame_w / 1000)
            y = int(self.custom_rect[1] * frame_h / 1000)
            w = int(self.custom_rect[2] * frame_w / 1000)
            h = int(self.custom_rect[3] * frame_h / 1000)
            return (x, y, w, h)
        
        if self.active_guide is None:
            return (0, 0, frame_w, frame_h)
        
        # Fall back to aspect ratio calculation for preset guides
        guide_w, guide_h = self.active_guide.aspect_ratio
        guide_ratio = guide_w / guide_h
        frame_ratio = frame_w / frame_h
        
        if guide_ratio > frame_ratio:
            # Guide is wider than frame - fit to width
            new_w = frame_w
            new_h = int(frame_w / guide_ratio)
        else:
            # Guide is taller than frame - fit to height
            new_h = frame_h
            new_w = int(frame_h * guide_ratio)
        
        # Center the rectangle
        x = (frame_w - new_w) // 2
        y = (frame_h - new_h) // 2
        
        return (x, y, new_w, new_h)
    
    def handle_touch_start(self, x: int, y: int, frame_w: int, frame_h: int) -> str:
        """Handle touch/mouse start for drag/resize. Returns handle type."""
        if not self.drag_mode or self.custom_rect is None:
            return ""
        
        # Denormalize current rect
        rx = int(self.custom_rect[0] * frame_w / 1000)
        ry = int(self.custom_rect[1] * frame_h / 1000)
        rw = int(self.custom_rect[2] * frame_w / 1000)
        rh = int(self.custom_rect[3] * frame_h / 1000)
        
        handle_size = 40  # Touch target size
        
        # Check corners first
        corners = {
            'tl': (rx, ry),
            'tr': (rx + rw, ry),
            'bl': (rx, ry + rh),
            'br': (rx + rw, ry + rh),
        }
        
        for handle, (cx, cy) in corners.items():
            if abs(x - cx) < handle_size and abs(y - cy) < handle_size:
                self._drag_start = (x, y)
                self._resize_handle = handle
                return handle
        
        # Check if inside rectangle (move)
        if rx < x < rx + rw and ry < y < ry + rh:
            self._drag_start = (x, y)
            self._resize_handle = 'move'
            return 'move'
        
        return ""
    
    def handle_touch_move(self, x: int, y: int, frame_w: int, frame_h: int):
        """Handle touch/mouse move for drag/resize"""
        if not self.drag_mode or self._drag_start is None or self.custom_rect is None:
            return
        
        dx = x - self._drag_start[0]
        dy = y - self._drag_start[1]
        
        # Normalize delta to 0-1000 scale
        dx_norm = int(dx * 1000 / frame_w)
        dy_norm = int(dy * 1000 / frame_h)
        
        rx, ry, rw, rh = self.custom_rect
        
        if self._resize_handle == 'move':
            # Move entire rectangle
            new_x = max(0, min(1000 - rw, rx + dx_norm))
            new_y = max(0, min(1000 - rh, ry + dy_norm))
            self.custom_rect = (new_x, new_y, rw, rh)
        
        elif self._resize_handle == 'tl':
            # Top-left corner
            new_x = max(0, min(rx + rw - 50, rx + dx_norm))
            new_y = max(0, min(ry + rh - 50, ry + dy_norm))
            new_w = rw - (new_x - rx)
            new_h = rh - (new_y - ry)
            self.custom_rect = (new_x, new_y, new_w, new_h)
        
        elif self._resize_handle == 'tr':
            # Top-right corner
            new_y = max(0, min(ry + rh - 50, ry + dy_norm))
            new_w = max(50, min(1000 - rx, rw + dx_norm))
            new_h = rh - (new_y - ry)
            self.custom_rect = (rx, new_y, new_w, new_h)
        
        elif self._resize_handle == 'bl':
            # Bottom-left corner
            new_x = max(0, min(rx + rw - 50, rx + dx_norm))
            new_w = rw - (new_x - rx)
            new_h = max(50, min(1000 - ry, rh + dy_norm))
            self.custom_rect = (new_x, ry, new_w, new_h)
        
        elif self._resize_handle == 'br':
            # Bottom-right corner
            new_w = max(50, min(1000 - rx, rw + dx_norm))
            new_h = max(50, min(1000 - ry, rh + dy_norm))
            self.custom_rect = (rx, ry, new_w, new_h)
        
        self._drag_start = (x, y)
    
    def handle_touch_end(self):
        """Handle touch/mouse end"""
        self._drag_start = None
        self._resize_handle = None
    
    def get_custom_rect_aspect_ratio(self) -> Optional[Tuple[float, float]]:
        """Get the aspect ratio of the current custom rectangle"""
        if self.custom_rect is None:
            return None
        w, h = self.custom_rect[2], self.custom_rect[3]
        if h == 0:
            return None
        return (w / h, 1.0)
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply frame guide overlay to frame.

        Args:
            frame: BGR image (may be read-only)

        Returns:
            Frame with frame guide overlay (always a new writable array)
        """
        if not self._enabled:
            return frame

        if self.active_guide is None and not self.drag_mode:
            return frame

        h, w = frame.shape[:2]

        # Calculate frame rectangle
        rx, ry, rw, rh = self._calculate_frame_rect(w, h)

        # Create writable result frame
        result = np.array(frame, copy=True)

        # Darken areas outside the frame guide - vectorized operation
        if self.fill_opacity > 0:
            # Create boolean mask for outside region
            mask = np.ones((h, w), dtype=bool)
            mask[ry:ry+rh, rx:rx+rw] = False

            # Vectorized darkening (much faster than element-wise)
            result[mask] = (frame[mask] * (1 - self.fill_opacity)).astype(np.uint8)

        # Draw frame guide rectangle
        cv2.rectangle(result, (rx, ry), (rx + rw, ry + rh), self.line_color, self.line_thickness)
        
        # Draw corner markers
        corner_size = 20
        corners = [
            ((rx, ry), (rx + corner_size, ry), (rx, ry + corner_size)),  # TL
            ((rx + rw, ry), (rx + rw - corner_size, ry), (rx + rw, ry + corner_size)),  # TR
            ((rx, ry + rh), (rx + corner_size, ry + rh), (rx, ry + rh - corner_size)),  # BL
            ((rx + rw, ry + rh), (rx + rw - corner_size, ry + rh), (rx + rw, ry + rh - corner_size)),  # BR
        ]
        
        for corner, h_end, v_end in corners:
            cv2.line(result, corner, h_end, self.line_color, self.line_thickness + 1)
            cv2.line(result, corner, v_end, self.line_color, self.line_thickness + 1)
        
        # Draw resize handles if in drag mode
        if self.drag_mode:
            handle_size = 12
            handle_color = (0, 255, 255)  # Yellow
            for corner, _, _ in corners:
                cv2.rectangle(
                    result,
                    (corner[0] - handle_size, corner[1] - handle_size),
                    (corner[0] + handle_size, corner[1] + handle_size),
                    handle_color, -1
                )
        
        # Draw label
        if self.show_label and self.active_guide:
            label = self.active_guide.name
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 1
            
            text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
            text_x = rx + 10
            text_y = ry + text_size[1] + 10
            
            # Background for text
            cv2.rectangle(
                result,
                (text_x - 5, text_y - text_size[1] - 5),
                (text_x + text_size[0] + 5, text_y + 5),
                (0, 0, 0), -1
            )
            cv2.putText(result, label, (text_x, text_y), font, font_scale, self.line_color, thickness)
        
        return result
    
    def toggle(self):
        """Toggle frame guide overlay"""
        super().toggle()
    
    def clear(self):
        """Clear the active guide"""
        self.active_guide = None
        self.drag_mode = False
        self.custom_rect = None

