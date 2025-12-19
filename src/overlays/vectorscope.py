"""
Vectorscope Overlay

Displays color information in a circular vectorscope format.
"""
import cv2
import numpy as np
from typing import Tuple, Optional
import math
from .base import Overlay


class VectorscopeOverlay(Overlay):
    """
    Vectorscope overlay for color analysis.
    
    Displays chrominance (color) information in a circular format,
    similar to professional broadcast monitors.
    """
    
    def __init__(self):
        super().__init__()
        self.size = 200  # Diameter
        self.position = 'bottom-left'
        self._opacity = 0.85
        self.show_graticule = True
        self._graticule: Optional[np.ndarray] = None
    
    def _create_graticule(self) -> np.ndarray:
        """Create vectorscope graticule (reference overlay)"""
        size = self.size
        center = size // 2
        radius = center - 10
        
        graticule = np.zeros((size, size, 3), dtype=np.uint8)
        
        # Background
        graticule[:] = (20, 20, 20)
        
        # Draw circles at 25%, 50%, 75%, 100%
        for pct in [25, 50, 75, 100]:
            r = int(radius * pct / 100)
            cv2.circle(graticule, (center, center), r, (60, 60, 60), 1)
        
        # Draw cross lines
        cv2.line(graticule, (center, 10), (center, size - 10), (60, 60, 60), 1)
        cv2.line(graticule, (10, center), (size - 10, center), (60, 60, 60), 1)
        
        # Draw color targets (standard vectorscope positions)
        # Angles for standard color bars (YUV/YCbCr)
        color_targets = [
            ('R', 103, (0, 0, 200)),    # Red
            ('MG', 61, (200, 0, 200)),   # Magenta
            ('B', 347, (200, 0, 0)),     # Blue
            ('CY', 283, (200, 200, 0)),  # Cyan
            ('G', 241, (0, 200, 0)),     # Green
            ('YL', 167, (0, 200, 200)),  # Yellow
        ]
        
        for name, angle, color in color_targets:
            # Position at 75% radius
            rad = math.radians(angle)
            x = int(center + radius * 0.75 * math.cos(rad))
            y = int(center - radius * 0.75 * math.sin(rad))
            
            # Draw small target box
            cv2.rectangle(graticule, (x-8, y-8), (x+8, y+8), color, 1)
            
            # Draw label
            cv2.putText(graticule, name, (x-10, y-12), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
        
        # Skin tone line (I-line)
        skin_angle = math.radians(123)  # Approximate skin tone angle
        x1 = int(center + radius * 0.3 * math.cos(skin_angle))
        y1 = int(center - radius * 0.3 * math.sin(skin_angle))
        x2 = int(center + radius * 0.9 * math.cos(skin_angle))
        y2 = int(center - radius * 0.9 * math.sin(skin_angle))
        cv2.line(graticule, (x1, y1), (x2, y2), (0, 150, 150), 1)
        
        return graticule
    
    def _generate_vectorscope(self, frame: np.ndarray) -> np.ndarray:
        """Generate vectorscope from frame"""
        size = self.size
        center = size // 2
        radius = center - 10
        
        # Start with graticule
        if self._graticule is None or self._graticule.shape[0] != size:
            self._graticule = self._create_graticule()
        
        vectorscope = self._graticule.copy()
        
        # Convert to YCrCb
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        
        # Aggressive downsampling for performance (process fewer pixels)
        # Sample every Nth pixel based on frame size
        scale = max(2, frame.shape[0] // 150)  # More aggressive downsampling
        ycrcb_small = ycrcb[::scale, ::scale]
        
        # Get Cr (red-diff) and Cb (blue-diff) channels
        cr = ycrcb_small[:, :, 1].flatten().astype(np.float32) - 128
        cb = ycrcb_small[:, :, 2].flatten().astype(np.float32) - 128

        # Normalize to fit in circle
        cr = (cr / 128) * radius
        cb = (cb / 128) * radius

        # Vectorized point plotting - much faster than loop
        # Calculate all x,y positions at once
        x_coords = (center + cb).astype(np.int32)
        y_coords = (center - cr).astype(np.int32)  # Invert Y

        # Filter valid coordinates (within bounds)
        valid_mask = (x_coords >= 0) & (x_coords < size) & (y_coords >= 0) & (y_coords < size)
        x_valid = x_coords[valid_mask]
        y_valid = y_coords[valid_mask]

        # Downsample if too many points (for performance)
        if len(x_valid) > 10000:
            step = len(x_valid) // 10000
            x_valid = x_valid[::step]
            y_valid = y_valid[::step]

        # Batch update pixels using advanced indexing
        # Add intensity to existing pixels (accumulation effect)
        vectorscope[y_valid, x_valid] = np.clip(
            vectorscope[y_valid, x_valid].astype(np.int32) + 30,
            0, 255
        ).astype(np.uint8)
        
        # Draw border
        cv2.rectangle(vectorscope, (0, 0), (size - 1, size - 1), (100, 100, 100), 1)
        
        return vectorscope
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply vectorscope overlay to frame.

        Args:
            frame: BGR image (may be read-only)

        Returns:
            Frame with vectorscope overlay (always a new writable array)
        """
        if not self._enabled:
            return frame

        # Create writable copy only when we need to modify it
        result = np.array(frame, copy=True)
        vectorscope = self._generate_vectorscope(frame)
        vs_size = vectorscope.shape[0]

        if self.position == 'bottom-left':
            x = 20
            y = frame.shape[0] - vs_size - 20
        elif self.position == 'bottom-right':
            x = frame.shape[1] - vs_size - 20
            y = frame.shape[0] - vs_size - 20
        elif self.position == 'top-left':
            x = 20
            y = 20
        else:
            x = frame.shape[1] - vs_size - 20
            y = 20

        # Ensure bounds
        x = max(0, min(x, frame.shape[1] - vs_size))
        y = max(0, min(y, frame.shape[0] - vs_size))

        # Create ROI and blend
        roi = result[y:y+vs_size, x:x+vs_size]
        blended = cv2.addWeighted(roi, 1 - self._opacity, vectorscope, self._opacity, 0)
        result[y:y+vs_size, x:x+vs_size] = blended

        return result
    
    def toggle(self):
        """Toggle vectorscope overlay"""
        super().toggle()
    
    def set_size(self, size: int):
        """Set vectorscope size"""
        self.size = size
        self._graticule = None  # Reset graticule

